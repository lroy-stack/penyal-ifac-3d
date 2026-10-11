"""Tree crowns from the LiDAR (E2.1), the NDVI check against the 2024 orthophoto (E2.2) and the
``vegetation.json`` artefact (with the understory of ``understory``, E2.4).

Method (all steps pure and deterministic; ``docs/research/003-inventario-datos-propios.md`` §4):

1. Points of the LiDAR vegetation classes 3, 4 and 5 become heights above the DEM (bilinear).
2. A canopy height model (CHM) keeps the highest point per 1 m cell. Cells are centred on whole
   local metres (ADR 0004 origin is a whole UTM metre), so the grid is global and independent of
   the area that is processed.
3. A crown is a CHM cell that is the maximum of its 5 x 5 window and at least 3 m high. Equal
   neighbours keep the first one in raster order.
4. The crown radius is the mean reach, over 8 rays, of the cells at least half the crown height,
   crossing gaps up to 1.5 m.
5. The NDVI of the 2024 orthophoto (median over the crown disk) marks crowns whose canopy is no
   longer there: the LiDAR is from 2016.

The area is the nature-reserve relation of OSM (the park the visitor is in) plus 40 m around the
walkable route (the access path starts outside the boundary and the pilot stretch is judged on
that band). Nothing is placed outside it.
"""

import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import laspy
import numpy as np
import numpy.typing as npt
import shapely
import shapely.ops
from rasterio.io import DatasetReader
from rasterio.windows import Window
from shapely.geometry.base import BaseGeometry

from penyal_pipeline import artefacts, dem, ortho, trail, understory
from penyal_pipeline.blender.pine import NOMINAL_HEIGHT, NOMINAL_RADIUS, VARIANT_COUNT
from penyal_pipeline.cellhash import SEED, hash_cells, unit_float
from penyal_pipeline.geo import ORIGIN_E, ORIGIN_N
from penyal_pipeline.paths import GENERATED_DIR, PINE_GENERATED, TRAIL_GENERATED
from penyal_pipeline.rawdata import locate

log = logging.getLogger(__name__)

VEGETATION_JSON = "vegetation.json"
VEGETATION_GENERATED = GENERATED_DIR / VEGETATION_JSON
SCHEMA_VERSION = 1

LIDAR_VEGETATION_CLASSES = (3, 4, 5)  # ASPRS low, medium and high vegetation
CHM_CELL = 1.0  # metres
PEAK_WINDOW = 5  # cells; a crown is the maximum of its 5 x 5 window
MIN_CROWN_HEIGHT = 3.0  # metres above the DEM
MIN_GROUND_HEIGHT = 0.5  # metres a.s.l.; lower points are boats, masts and sea clutter
RADIUS_RAY_STEP = 0.5
RADIUS_HEIGHT_FRACTION = 0.5
RADIUS_MAX_GAP = 1.5  # metres of empty or low cells a ray crosses
MIN_CROWN_RADIUS = 0.75
MAX_CROWN_RADIUS = 6.0
ROUTE_BAND = 40.0  # metres around the route that always belong to the area
RESERVE_RELATION = 2172136  # OSM: Parc Natural del Penyal d'Ifac

# The pilot stretch of the research (section 4): 40 m each side of the first 421 m of route. Its
# figure (186 crowns) pins the algorithm in the tests, which reproduce the prototype's clipping of
# the points to the band; it is not a tuning target.
PILOT_LENGTH = 421.0
PILOT_BAND = 40.0

# Orthophoto 2024: bands R, G, B, then near infrared. The ICV metadata page could not be reached,
# so the NIR band was identified from the data (tech lead, 2026-10-11): 5000 random LiDAR 2016
# points per class in tile 766-4282, ortho pixel at each XY, NDVI = (B4 - R) / (B4 + R); median
# (p10, p90) of high vegetation +0.29 (+0.07, +0.42; mean R 98, B4 163), low vegetation +0.20
# (+0.03, +0.38), ground +0.06 (+0.01, +0.24), building +0.03 (0.00, +0.17), water +0.05
# (-0.21, +0.14; mean B4 47). Vegetation is bright in B4 and water is dark, as for a NIR band.
RED_BAND = 1
NIR_BAND = 4

# The crown NDVI (median over the disk) has no valley to cut at: 1441 crowns, one broad mode at
# 0.25-0.35 and a tail down to 0 (Otsu would cut at 0.225 and drop a third of them). The threshold
# is therefore tied to the measured reference classes above: 0.07 is the 10th percentile of the
# high vegetation of 2016 as seen in 2024, and sits above the medians of ground (0.06) and
# buildings (0.03). A crown median below it looks more like ground or roof than canopy. It
# excludes 54 of the 1441 crowns analysed (1 of the 185 in the pilot band);
# ``penyal vegetation --analyse`` prints the histogram and the counts for any other threshold.
NDVI_ABSENT_THRESHOLD = 0.07
NDVI_MIN_DISK = 1.5  # metres, smallest disk a crown is judged on
NDVI_SHIFT = 1.0  # metres, apex-to-canopy offset the ortho rectification can cause
# Crowns taller than this are LiDAR/DEM mismatches on vertical rock (4 crowns, 23-94 m, on slopes
# of 64-88 degrees), not trees: the tallest plausible tree of the park is a pine of ~20 m.
MAX_CROWN_HEIGHT = 25.0
# On a cliff the LiDAR vegetation classes and the 1 m DEM disagree (the DEM smooths the wall), so
# many "crowns" there are rock: of the 182 crowns on slopes >= 60 degrees, 102 had an NDVI under
# 0.20 and most of the minimum-radius ones are single points. A cliff crown stays only if it is
# wider than the minimum radius and green at least like the low vegetation of the park (median
# NDVI 0.20, measured as for NIR_BAND above). Everything else is dropped, not demoted.
# The LiDAR gives the apex of a crown, not its trunk: a pine that grows beside the path leans
# its crown over it (ten apexes of the pilot stretch were within 0.75 m of the path axis, 24
# within 1.5 m). The trunk foot is therefore moved to the nearest ground outside the ADR 0006
# corridor plus 0.5 m (the width of a trunk foot and its root flare), and the tree leans from
# there to the measured apex. A pine leans at most 0.6 x its height (about 31 degrees from the
# vertical); a crown that would need more is not a tree beside the path but something over it
# (a pergola, a vehicle, a hedge of the forecourt) and is dropped.
FOOT_MARGIN = 0.5  # metres outside the corridor polygon
# Moving the foot changes the ground it stands on, but the apex keeps its measured elevation:
# the crown is re-measured from the new foot (apex elevation - foot elevation) and ``apexY``
# is stored. A foot more than 1.5 m above or below the ground under the apex (a bank, a wall or
# a terrace between the path and the tree: 14 of 48 moved trees were off by more than 1 m and 4
# by more than 2 m before this rule) or on a cliff slope is not a trunk beside the path, and the
# crown is dropped as overPath.
MAX_FOOT_DROP = 1.5  # metres
TUNNEL_STRIP_CUT = 1.5  # metres around the tunnel axis that are not surface corridor
MAX_LEAN_PER_HEIGHT = 0.6
# The pine is modelled 10 m tall with a 3.2 m crown radius. Scaling it to a measured height and
# radius independently stretched it up to 6.9 times (a 0.75 m radius under 5 m of height gives a
# 6 cm trunk and needle cards four times too long), so the horizontal scale may differ from the
# vertical one by this factor at most.
SCALE_RATIO = (0.6, 1.6)
CLIFF_SLOPE = 60.0  # degrees
CLIFF_MIN_NDVI = 0.20

type Floats = npt.NDArray[np.float64]
type Rows = list[list[float]]


class VegetationError(RuntimeError):
    """The vegetation inputs are missing or inconsistent."""


@dataclass(frozen=True)
class VegetationPoints:
    """LiDAR vegetation points in the local frame; ``height`` is above the DEM."""

    x: Floats
    z: Floats
    height: Floats
    lidar_class: npt.NDArray[np.uint8]


@dataclass(frozen=True)
class Chm:
    """Highest point per cell; cell ``(r, c)`` is centred on ``(ix0 + c, iz0 + r)`` whole metres."""

    ix0: int
    iz0: int
    heights: npt.NDArray[np.float32]  # NaN where no point

    def value_at(self, x: Floats, z: Floats) -> Floats:
        """Height of the cell containing each position; NaN outside the model or in empty cells."""
        col = np.floor(x / CHM_CELL + 0.5).astype(np.int64) - self.ix0
        row = np.floor(z / CHM_CELL + 0.5).astype(np.int64) - self.iz0
        inside = (row >= 0) & (row < self.heights.shape[0]) & (col >= 0)
        inside &= col < self.heights.shape[1]
        out = np.full(x.shape, np.nan)
        out[inside] = self.heights[row[inside], col[inside]]
        return out


@dataclass(frozen=True)
class Crowns:
    """Detected crowns: cell-centre position, ground height ``y``, top above ground, radius."""

    x: Floats
    y: Floats
    z: Floats
    height: Floats
    radius: Floats

    def __len__(self) -> int:
        return int(self.x.size)

    def select(self, mask: npt.NDArray[np.bool_]) -> "Crowns":
        return Crowns(
            self.x[mask], self.y[mask], self.z[mask], self.height[mask], self.radius[mask]
        )


# --- area ---------------------------------------------------------------------------------------


def route_line(trail_document: dict[str, Any]) -> shapely.LineString:
    """The route as one 2D polyline: the segments of ``trail.json`` in order, joints merged."""
    points: list[tuple[float, float]] = []
    for segment in trail_document["route"]["segments"]:
        for p in segment["points"]:
            xz = (float(p[0]), float(p[2]))
            if not points or xz != points[-1]:
                points.append(xz)
    return shapely.LineString(points)


def surface_corridor(trail_document: dict[str, Any]) -> BaseGeometry:
    """The ADR 0006 corridor on the surface: the part inside the mountain (the tunnel strip) is
    cut out, because trees stand on the rock above it."""
    corridor = shapely.Polygon(trail_document["corridor"]["polygon"])
    tunnel = [
        shapely.LineString([(float(p[0]), float(p[2])) for p in segment["points"]])
        for segment in trail_document["route"]["segments"]
        if segment["id"] == trail.TUNNEL_SEGMENT
    ]
    return corridor.difference(shapely.unary_union(tunnel).buffer(TUNNEL_STRIP_CUT, quad_segs=4))


def reserve_polygon(osm_json: Path, osm: trail.OsmData) -> BaseGeometry:
    """The nature-reserve relation (outer ways closed into a polygon) in the local frame."""
    raw = json.loads(osm_json.read_text(encoding="utf-8"))
    relation = next(
        (e for e in raw["elements"] if e["type"] == "relation" and e["id"] == RESERVE_RELATION),
        None,
    )
    if relation is None:
        raise VegetationError(
            f"OSM relation {RESERVE_RELATION} (nature reserve) is not in the extract"
        )
    lines = []
    for member in relation["members"]:
        if member["type"] != "way" or member["role"] != "outer":
            continue
        way = osm.ways.get(member["ref"])
        if way is None:
            raise VegetationError(f"reserve way {member['ref']} is not in the OSM extract")
        missing = [n for n in way.nodes if n not in osm.xz]
        if missing:
            raise VegetationError(
                f"reserve way {member['ref']} lists node {missing[0]}, which is not in the OSM "
                "extract: fetch the extract again"
            )
        lines.append(shapely.LineString([osm.xz[n] for n in way.nodes]))
    polygons = list(shapely.ops.polygonize(shapely.unary_union(lines)))
    if len(polygons) != 1:
        raise VegetationError(
            f"nature reserve relation closes into {len(polygons)} polygons, expected 1"
        )
    return polygons[0]


def work_area(reserve: BaseGeometry, route: shapely.LineString) -> BaseGeometry:
    return shapely.unary_union([reserve, route.buffer(ROUTE_BAND, quad_segs=16)])


def pilot_band(route: shapely.LineString) -> BaseGeometry:
    """40 m (round caps) around the first 421 m of the route."""
    return shapely.ops.substring(route, 0.0, PILOT_LENGTH).buffer(PILOT_BAND, quad_segs=16)


# --- LiDAR --------------------------------------------------------------------------------------


def read_vegetation_points(
    paths: list[Path], bounds: tuple[float, float, float, float], grid: dem.Grid
) -> VegetationPoints:
    """Vegetation points inside local ``bounds`` (x_min, z_min, x_max, z_max), above the DEM."""
    x_min, z_min, x_max, z_max = bounds
    parts: list[tuple[Floats, Floats, Floats, npt.NDArray[np.uint8]]] = []
    for path in paths:
        las = laspy.read(path)
        classes = np.asarray(las.classification, dtype=np.uint8)
        x = np.asarray(las.x, dtype=np.float64) - ORIGIN_E
        z = -(np.asarray(las.y, dtype=np.float64) - ORIGIN_N)
        y = np.asarray(las.z, dtype=np.float64)
        keep = np.isin(classes, LIDAR_VEGETATION_CLASSES)
        keep &= (x >= x_min) & (x <= x_max) & (z >= z_min) & (z <= z_max)
        keep &= (y >= dem.LIDAR_NOISE_RANGE[0]) & (y <= dem.LIDAR_NOISE_RANGE[1])
        px, pz = x[keep], z[keep]
        ground = grid.sample(px, pz)
        height = y[keep] - ground
        usable = (ground >= MIN_GROUND_HEIGHT) & (height >= 0.0)
        parts.append((px[usable], pz[usable], height[usable], classes[keep][usable]))
    if not parts:
        raise VegetationError("no LiDAR tile given")
    return VegetationPoints(
        np.concatenate([p[0] for p in parts]),
        np.concatenate([p[1] for p in parts]),
        np.concatenate([p[2] for p in parts]),
        np.concatenate([p[3] for p in parts]),
    )


def select_points(points: VegetationPoints, mask: npt.NDArray[np.bool_]) -> VegetationPoints:
    return VegetationPoints(
        points.x[mask], points.z[mask], points.height[mask], points.lidar_class[mask]
    )


# --- crowns -------------------------------------------------------------------------------------


def canopy_height_model(points: VegetationPoints) -> Chm:
    """The highest point above the DEM in each 1 m cell centred on whole local metres."""
    if points.x.size == 0:
        return Chm(0, 0, np.full((1, 1), np.nan, dtype=np.float32))
    col = np.floor(points.x / CHM_CELL + 0.5).astype(np.int64)
    row = np.floor(points.z / CHM_CELL + 0.5).astype(np.int64)
    ix0, iz0 = int(col.min()), int(row.min())
    shape = (int(row.max()) - iz0 + 1, int(col.max()) - ix0 + 1)
    top = np.full(shape, -np.inf)
    np.maximum.at(top, (row - iz0, col - ix0), points.height)
    heights = np.where(np.isfinite(top), top, np.nan).astype(np.float32)
    return Chm(ix0, iz0, heights)


def _window_offsets() -> list[tuple[int, int]]:
    half = PEAK_WINDOW // 2
    return [(dr, dc) for dr in range(-half, half + 1) for dc in range(-half, half + 1)]


def detect_peaks(chm: Chm) -> tuple[npt.NDArray[np.intp], npt.NDArray[np.intp]]:
    """Rows and columns of the crown cells, in raster order."""
    half = PEAK_WINDOW // 2
    filled = np.where(np.isnan(chm.heights), -np.inf, chm.heights.astype(np.float64))
    rows, cols = filled.shape
    padded = np.pad(filled, half, constant_values=-np.inf)
    peak = filled >= MIN_CROWN_HEIGHT
    for dr, dc in _window_offsets():
        shifted = padded[half + dr : half + dr + rows, half + dc : half + dc + cols]
        peak &= filled >= shifted
        earlier = dr < 0 or (dr == 0 and dc < 0)
        if earlier:
            peak &= filled != shifted  # an equal neighbour that comes first wins the tie
    found_rows, found_cols = np.nonzero(peak)
    return found_rows, found_cols


def crown_radii(chm: Chm, x: Floats, z: Floats, height: Floats) -> Floats:
    """Mean reach of 8 rays over cells at least half the crown height (clamped).

    LiDAR at 0.5-1 point/m2 leaves many empty 1 m cells inside a crown, so a ray crosses gaps of up
    to ``RADIUS_MAX_GAP`` metres and ends at the last canopy cell before a longer one.
    """
    steps = int(MAX_CROWN_RADIUS / RADIUS_RAY_STEP)
    max_gap = int(RADIUS_MAX_GAP / RADIUS_RAY_STEP)
    total = np.zeros(x.shape)
    for angle in range(8):
        dx, dz = math.cos(angle * math.pi / 4), math.sin(angle * math.pi / 4)
        misses = np.zeros(x.shape, dtype=np.int64)
        ended = np.zeros(x.shape, dtype=np.bool_)
        reach = np.zeros(x.shape)
        for step in range(1, steps + 1):
            distance = step * RADIUS_RAY_STEP
            value = chm.value_at(x + dx * distance, z + dz * distance)
            canopy = value >= RADIUS_HEIGHT_FRACTION * height
            reach[~ended & canopy] = distance + RADIUS_RAY_STEP / 2.0
            misses = np.where(canopy, 0, misses + 1)
            ended |= misses > max_gap
        total += reach
    return np.clip(total / 8.0, MIN_CROWN_RADIUS, MAX_CROWN_RADIUS)


def detect_crowns(points: VegetationPoints, grid: dem.Grid) -> Crowns:
    """Crowns of ``points``: local maxima of the CHM, with ground height and radius."""
    chm = canopy_height_model(points)
    rows, cols = detect_peaks(chm)
    x = np.asarray((cols + chm.ix0) * CHM_CELL, dtype=np.float64)
    z = np.asarray((rows + chm.iz0) * CHM_CELL, dtype=np.float64)
    height = chm.heights[rows, cols].astype(np.float64)
    radius = crown_radii(chm, x, z, height)
    return Crowns(x, grid.sample(x, z), z, height, radius)


def cliff_keep(crowns: Crowns, slope: Floats, ndvi: Floats) -> npt.NDArray[np.bool_]:
    """False for crowns on a cliff that are not wider than the minimum radius or not green."""
    on_cliff = slope >= CLIFF_SLOPE
    green = (crowns.radius > MIN_CROWN_RADIUS) & (ndvi >= CLIFF_MIN_NDVI)  # NaN is False
    return np.asarray(~on_cliff | green, dtype=np.bool_)


@dataclass(frozen=True)
class Feet:
    """Trunk foot of each crown (apex moved out of the corridor) and whether it could be placed."""

    x: Floats
    z: Floats
    ok: npt.NDArray[np.bool_]


def place_feet(x: Floats, z: Floats, height: Floats, corridor: BaseGeometry) -> Feet:
    """Move apexes inside ``corridor`` (+ ``FOOT_MARGIN``) to its nearest edge, outwards."""
    clear = corridor.buffer(FOOT_MARGIN, quad_segs=8)
    foot_x, foot_z = x.copy(), z.copy()
    ok = np.ones(x.shape, dtype=np.bool_)
    boundary = clear.boundary
    for i in np.nonzero(shapely.contains_xy(clear, x, z))[0]:
        apex = shapely.Point(float(x[i]), float(z[i]))
        edge = shapely.ops.nearest_points(boundary, apex)[0]
        step = np.array([edge.x - apex.x, edge.y - apex.y])
        length = float(np.hypot(*step))
        # a hair beyond the edge so the foot is strictly outside
        beyond = step / length * (length + 1e-3) if length > 0.0 else np.array([1e-3, 0.0])
        foot_x[i], foot_z[i] = x[i] + beyond[0], z[i] + beyond[1]
        ok[i] = float(np.hypot(*beyond)) <= MAX_LEAN_PER_HEIGHT * float(height[i])
    return Feet(foot_x, foot_z, ok)


def plausible(crowns: Crowns) -> npt.NDArray[np.bool_]:
    """False for crowns taller than any tree of the park (LiDAR/DEM mismatches on vertical rock)."""
    return np.asarray(crowns.height <= MAX_CROWN_HEIGHT, dtype=np.bool_)


@dataclass(frozen=True)
class Vertical:
    """Ground under each trunk foot, elevation of each crown apex, and whether the foot is valid."""

    foot_y: Floats
    apex_y: Floats
    ok: npt.NDArray[np.bool_]


def check_vertical(
    feet: Feet,
    crowns: Crowns,
    grid: dem.Grid,
    slopes: Floats,
    max_drop: float = MAX_FOOT_DROP,
) -> Vertical:
    """Foot ground and apex elevation; a moved foot on a cliff slope, further than ``max_drop`` in
    elevation from the ground under the apex, or leaving less than a crown of height is invalid."""
    apex_y = np.asarray(crowns.y + crowns.height, dtype=np.float64)
    moved = (feet.x != crowns.x) | (feet.z != crowns.z)
    foot_y = np.where(moved, grid.sample(feet.x, feet.z), crowns.y)
    foot_slope = dem.slope_at(slopes, grid, feet.x, feet.z)
    valid = ~moved | (
        (foot_slope < CLIFF_SLOPE)
        & (np.abs(foot_y - crowns.y) <= max_drop)
        & (apex_y - foot_y >= MIN_CROWN_HEIGHT)
    )
    return Vertical(np.asarray(foot_y, dtype=np.float64), apex_y, np.asarray(valid, dtype=np.bool_))


def crowns_in(crowns: Crowns, area: BaseGeometry) -> npt.NDArray[np.bool_]:
    return np.asarray(shapely.contains_xy(area, crowns.x, crowns.z), dtype=np.bool_)


# --- NDVI ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class NdviRaster:
    """NDVI of a window of the orthophoto; pixel ``(r, c)`` covers ``x_min + c * res`` east of the
    origin and ``z_min + r * res`` south (row 0 is the north edge)."""

    values: npt.NDArray[np.float32]
    x_min: float
    z_min: float
    res: float


def read_ndvi(src: DatasetReader, bounds: tuple[float, float, float, float]) -> NdviRaster:
    """NDVI = (NIR - R) / (NIR + R) of the pixels covering local ``bounds``; NaN if both are 0."""
    if src.count < max(RED_BAND, NIR_BAND):
        raise VegetationError(f"orthophoto has {src.count} bands, band {NIR_BAND} (NIR) is needed")
    x_min, z_min, x_max, z_max = bounds
    transform = src.transform
    res = float(transform.a)
    col0 = max(0, math.floor((ORIGIN_E + x_min - transform.c) / res))
    col1 = min(src.width, math.ceil((ORIGIN_E + x_max - transform.c) / res))
    row0 = max(0, math.floor((transform.f - (ORIGIN_N - z_min)) / res))
    row1 = min(src.height, math.ceil((transform.f - (ORIGIN_N - z_max)) / res))
    if col1 <= col0 or row1 <= row0:
        raise VegetationError("the orthophoto does not cover the vegetation area")
    window = Window.from_slices((row0, row1), (col0, col1))
    red = src.read(RED_BAND, window=window).astype(np.float32)
    nir = src.read(NIR_BAND, window=window).astype(np.float32)
    total = nir + red
    with np.errstate(invalid="ignore", divide="ignore"):
        values = np.where(total > 0, (nir - red) / total, np.nan).astype(np.float32)
    return NdviRaster(
        values,
        transform.c + col0 * res - ORIGIN_E,
        ORIGIN_N - (transform.f + row0 * transform.e),
        res,
    )


def _disk_median(raster: NdviRaster, cx: float, cz: float, radius: float) -> float:
    rows, cols = raster.values.shape
    c0 = max(0, math.floor((cx - radius - raster.x_min) / raster.res))
    c1 = min(cols, math.ceil((cx + radius - raster.x_min) / raster.res))
    r0 = max(0, math.floor((cz - radius - raster.z_min) / raster.res))
    r1 = min(rows, math.ceil((cz + radius - raster.z_min) / raster.res))
    if c1 <= c0 or r1 <= r0:
        return math.nan
    px = raster.x_min + (np.arange(c0, c1) + 0.5) * raster.res - cx
    pz = raster.z_min + (np.arange(r0, r1) + 0.5) * raster.res - cz
    inside = (px[None, :] ** 2 + pz[:, None] ** 2) <= radius**2
    values = raster.values[r0:r1, c0:c1][inside]
    values = values[~np.isnan(values)]
    return float(np.median(values)) if values.size else math.nan


def crown_ndvi(raster: NdviRaster, crowns: Crowns) -> Floats:
    """NDVI of each crown: the best median over disks of at least ``NDVI_MIN_DISK`` metres around
    the apex and around four points ``NDVI_SHIFT`` metres away (NaN if no pixel is valid).

    The orthophoto is rectified on the terrain, not on the canopy, so the top of a tall crown is
    displaced from its image by about height x tan(view angle), roughly a metre; small crowns
    (minimum radius 0.75 m) were dropped four times as often as wide ones when only the apex disk
    was read.
    """
    offsets = (
        (0.0, 0.0),
        *((s * NDVI_SHIFT, 0.0) for s in (-1, 1)),
        *((0.0, s * NDVI_SHIFT) for s in (-1, 1)),
    )
    out = np.full(len(crowns), np.nan)
    for i in range(len(crowns)):
        cx, cz = float(crowns.x[i]), float(crowns.z[i])
        radius = max(float(crowns.radius[i]), NDVI_MIN_DISK)
        medians = [_disk_median(raster, cx + dx, cz + dz, radius) for dx, dz in offsets]
        valid = [m for m in medians if not math.isnan(m)]
        if valid:
            out[i] = max(valid)
    return out


def present_mask(ndvi: Floats, threshold: float) -> npt.NDArray[np.bool_]:
    """Crowns kept: NDVI at or above ``threshold``. A crown with no valid pixel cannot be judged
    and stays."""
    return np.asarray(np.isnan(ndvi) | (ndvi >= threshold), dtype=np.bool_)


# --- document -----------------------------------------------------------------------------------


def instance_scale(height: Floats, radius: Floats) -> tuple[Floats, Floats]:
    """Vertical and horizontal scale of the pine for each crown: ``height / 10`` and
    ``radius / 3.2`` held within ``SCALE_RATIO`` of the vertical one."""
    vertical = np.asarray(height / NOMINAL_HEIGHT, dtype=np.float64)
    wanted = radius / NOMINAL_RADIUS
    horizontal = np.clip(wanted, SCALE_RATIO[0] * vertical, SCALE_RATIO[1] * vertical)
    return vertical, np.asarray(horizontal, dtype=np.float64)


def _column(values: Floats, decimals: int) -> list[float]:
    return [round(float(v), decimals) for v in values]


def crown_columns(
    crowns: Crowns,
    ndvi: Floats,
    slope: Floats,
    reason: list[str] | None = None,
    lean: tuple[Floats, Floats] | None = None,
    apex_y: Floats | None = None,
) -> dict[str, Any]:
    """Columnar crowns: ``variant`` and ``yaw`` come from the hash of the crown cell."""
    ix = np.rint(crowns.x).astype(np.int64)
    iz = np.rint(crowns.z).astype(np.int64)
    variant = (hash_cells(ix, iz, 1) % np.uint64(VARIANT_COUNT)).astype(np.int64)
    yaw = np.floor(unit_float(hash_cells(ix, iz, 2)) * 360.0)
    columns: dict[str, Any] = {
        "count": len(crowns),
        "x": _column(crowns.x, 2),
        "y": _column(crowns.y, 2),
        "z": _column(crowns.z, 2),
        "height": _column(crowns.height, 2),
        "radius": _column(crowns.radius, 2),
        "scaleXZ": _column(instance_scale(crowns.height, crowns.radius)[1], 3),
        "keep": [int(v) for v in np.floor(unit_float(hash_cells(ix, iz, 3)) * 100.0)],
        "variant": [int(v) for v in variant],
        "yaw": [int(v) for v in yaw],
        "ndvi": [None if math.isnan(v) else round(float(v), 3) for v in ndvi],
        "slope": _column(slope, 1),
    }
    if reason is not None:
        columns["reason"] = reason
    if lean is not None:
        columns["leanX"] = _column(lean[0], 2)
        columns["leanZ"] = _column(lean[1], 2)
    if apex_y is not None:
        columns["apexY"] = _column(apex_y, 2)
    return columns


@dataclass(frozen=True)
class Detection:
    """Everything one run computes before it is written."""

    area: BaseGeometry
    crowns: Crowns  # in the area, before the NDVI check
    ndvi: Floats
    slope: Floats
    absent: npt.NDArray[np.bool_]
    cliff: npt.NDArray[np.bool_]
    over_path: npt.NDArray[np.bool_]
    feet: Feet
    vertical: Vertical
    kept: npt.NDArray[np.bool_]
    pilot_park: int
    pilot_kept: int
    implausible: int
    points: VegetationPoints
    route: shapely.LineString
    grid: dem.Grid
    osm: trail.OsmData


def detect(threshold: float = NDVI_ABSENT_THRESHOLD) -> Detection:
    """Run the crown detection and the NDVI check over the park area."""
    osm_file = locate(trail.OSM_SOURCE_ID, trail.OSM_FILE)
    osm = trail.load_osm(osm_file.path)
    route = route_line(json.loads(TRAIL_GENERATED.read_text(encoding="utf-8")))
    area = work_area(reserve_polygon(osm_file.path, osm), route)
    grid, _ = dem.load_dem()
    x_min, z_min, x_max, z_max = area.bounds
    margin = float(PEAK_WINDOW)
    bounds = (x_min - margin, z_min - margin, x_max + margin, z_max + margin)
    points = read_vegetation_points(dem.lidar_paths(), bounds, grid)
    crowns = detect_crowns(points, grid)
    crowns = crowns.select(crowns_in(crowns, area))
    implausible = int((~plausible(crowns)).sum())
    crowns = crowns.select(plausible(crowns))
    with ortho.open_ortho(ortho.locate_ortho().path) as src:
        raster = read_ndvi(src, (x_min, z_min, x_max, z_max))
    ndvi = crown_ndvi(raster, crowns)
    slope = dem.slope_at(dem.slope_degrees(grid), grid, crowns.x, crowns.z)
    absent = ~present_mask(ndvi, threshold)
    cliff = ~absent & ~cliff_keep(crowns, slope, ndvi)
    corridor = surface_corridor(json.loads(TRAIL_GENERATED.read_text(encoding="utf-8")))
    feet = place_feet(crowns.x, crowns.z, crowns.height, corridor)
    vertical = check_vertical(feet, crowns, grid, dem.slope_degrees(grid))
    over_path = ~absent & ~cliff & ~(feet.ok & vertical.ok)
    kept = ~absent & ~cliff & ~over_path
    band = pilot_band(route)
    in_band = crowns_in(crowns, band)
    return Detection(
        area=area,
        crowns=crowns,
        ndvi=ndvi,
        slope=slope,
        absent=absent,
        cliff=cliff,
        over_path=over_path,
        feet=feet,
        vertical=vertical,
        kept=kept,
        pilot_park=int(in_band.sum()),
        pilot_kept=int((in_band & kept).sum()),
        implausible=implausible,
        points=points,
        route=route,
        grid=grid,
        osm=osm,
    )


@dataclass(frozen=True)
class Group:
    """Instances drawn with one mesh set: positions (x, z), triangles per level (near, mid, far
    card) and the distances at which the near and mid levels end and the far card ends."""

    name: str
    xz: Floats
    triangles: tuple[int, int, int]
    distances: tuple[float, float, float]


@dataclass(frozen=True)
class ViewCost:
    triangles: int
    calls: int  # one instanced draw per (group, level) that has an instance in view


def estimate_view(viewer: tuple[float, float], groups: list[Group]) -> ViewCost:
    """Triangles and draw calls of one colour pass seen from ``viewer`` in every direction."""
    triangles = 0
    calls = 0
    for group in groups:
        distance = np.hypot(group.xz[:, 0] - viewer[0], group.xz[:, 1] - viewer[1])
        near, mid, far = group.distances
        levels = (
            distance < near,
            (distance >= near) & (distance < mid),
            (distance >= mid) & (distance < far),
        )
        for count, cost in zip((int(m.sum()) for m in levels), group.triangles, strict=True):
            triangles += count * cost
            calls += 1 if count else 0
    return ViewCost(triangles, calls)


def worst_view(route: shapely.LineString, groups: list[Group], spacing: float = 25.0) -> ViewCost:
    """The most triangles and the most calls seen from points every ``spacing`` metres of the
    route (an upper bound: it looks all around, the camera sees a fraction)."""
    steps = np.arange(0.0, route.length, spacing)
    costs = [
        estimate_view((p.x, p.y), groups) for p in (route.interpolate(float(s)) for s in steps)
    ]
    return ViewCost(max(c.triangles for c in costs), max(c.calls for c in costs))


TREE_DISTANCES = (30.0, 70.0, 120.0)  # lod0, lod1 and card end (ADR 0010 medium: 120 m)
UNDERSTORY_DISTANCES = (12.0, 30.0, 60.0)
MEDIUM_DENSITY = 0.7  # ADR 0010 medium tier


def _triangles(manifest: dict[str, Any], prefix: str) -> tuple[int, int, int]:
    by_name = {m["name"]: int(m["triangles"]) for m in manifest["meshes"]}
    return by_name[f"{prefix}_lod0"], by_name[f"{prefix}_lod1"], by_name[f"{prefix}_card"]


def budget_lines(found: "Detection", shrubs: dict[str, Any]) -> list[str]:
    """Worst triangles and draw calls of the vegetation along the route at the medium tier."""
    pine_json = PINE_GENERATED / "pine.json"
    plants_json = PINE_GENERATED / "plants.json"
    if not (pine_json.is_file() and plants_json.is_file()):
        return ["budget: run `penyal pine` and `penyal plants` first to estimate it"]
    pine_manifest = json.loads(pine_json.read_text(encoding="utf-8"))
    plants_manifest = json.loads(plants_json.read_text(encoding="utf-8"))
    feet, _, _ = kept_at_feet(found)
    foot_x, foot_z = feet.x, feet.z
    columns = crown_columns(feet, found.ndvi[found.kept], found.slope[found.kept])
    keep, variant = np.array(columns["keep"]), np.array(columns["variant"])
    limit = MEDIUM_DENSITY * 100.0
    pine_tris = {m["name"]: int(m["triangles"]) for m in pine_manifest["meshes"]}
    groups = []
    for v in range(VARIANT_COUNT):
        chosen = (variant == v) & (keep < limit)
        groups.append(
            Group(
                f"pine_v{v}",
                np.stack([foot_x[chosen], foot_z[chosen]], axis=1),
                (
                    pine_tris[f"pine_v{v}_lod0"],
                    pine_tris[f"pine_v{v}_lod1"],
                    pine_tris["pine_far_card"],
                ),
                TREE_DISTANCES,
            )
        )
    model = np.array(shrubs["model"])
    shrub_keep = np.array(shrubs["keep"])
    sx, sz = np.array(shrubs["x"]), np.array(shrubs["z"])
    for index, plant in enumerate(understory.MODELS):
        chosen = (model == index) & (shrub_keep < limit)
        groups.append(
            Group(
                plant.id,
                np.stack([sx[chosen], sz[chosen]], axis=1),
                _triangles(plants_manifest, plant.id),
                UNDERSTORY_DISTANCES,
            )
        )
    worst = worst_view(found.route, groups)
    return [
        f"budget at the medium tier (density {MEDIUM_DENSITY}, trees to {TREE_DISTANCES[2]:.0f} m, "
        f"understory to {UNDERSTORY_DISTANCES[2]:.0f} m), worst view along the route, all around:",
        f"  {worst.triangles:,} triangles (ADR 0010 row: 250,000) and {worst.calls} draw calls "
        f"per colour pass (row: 40) with {len(groups)} instanced groups x 3 levels",
    ]


def ndvi_histogram(ndvi: Floats, edges: Floats) -> list[tuple[float, float, int]]:
    counts, _ = np.histogram(ndvi[~np.isnan(ndvi)], bins=edges)
    return [(float(edges[i]), float(edges[i + 1]), int(counts[i])) for i in range(len(counts))]


def analysis_report(found: Detection, threshold: float) -> str:
    """Counts and the crown NDVI histogram, for choosing or checking the threshold."""
    crowns, ndvi = found.crowns, found.ndvi
    band = pilot_band(found.route)
    in_band = crowns_in(crowns, band)
    lines = [
        f"area {found.area.area / 1e4:.1f} ha, {found.points.x.size} LiDAR vegetation points",
        f"crowns: {len(crowns) + found.implausible} detected, {found.implausible} taller than "
        f"{MAX_CROWN_HEIGHT:.0f} m dropped, {len(crowns)} analysed",
        f"height of the analysed crowns: median {np.median(crowns.height):.1f} m, p90 "
        f"{np.percentile(crowns.height, 90):.1f} m, max {crowns.height.max():.1f} m",
        f"pilot band (421 m + 40 m): {int(in_band.sum())} crowns detected, "
        f"{int((in_band & found.kept).sum())} kept",
        f"NDVI (band {NIR_BAND} = NIR): {int(np.isnan(ndvi).sum())} crowns without valid pixels",
        "crown NDVI histogram (all / pilot band):",
    ]
    edges = np.round(np.arange(-0.1, 0.61, 0.05), 2)
    all_bins = ndvi_histogram(ndvi, edges)
    pilot_bins = ndvi_histogram(ndvi[in_band], edges)
    for (lo, hi, n), (_, _, pilot) in zip(all_bins, pilot_bins, strict=True):
        lines.append(f"  {lo:+.2f}..{hi:+.2f} {n:5d} {pilot:4d}")
    absent = int((~present_mask(ndvi, threshold)).sum())
    absent_band = int((~present_mask(ndvi, threshold) & in_band).sum())
    lines.append(
        f"threshold {threshold}: {absent} absent of {len(crowns)} "
        f"({absent_band} of {int(in_band.sum())} in the pilot band)"
    )
    lines.append(
        "slope of the analysed crowns (degrees): n / dropped by NDVI / dropped by cliff rule"
    )
    for low, high in ((0.0, 30.0), (30.0, 50.0), (50.0, 60.0), (60.0, 70.0), (70.0, 91.0)):
        band_mask = (found.slope >= low) & (found.slope < high)
        lines.append(
            f"  {low:3.0f}..{high:3.0f} {int(band_mask.sum()):5d} "
            f"{int((band_mask & found.absent).sum()):5d} {int((band_mask & found.cliff).sum()):5d}"
        )
    exclusion = understory.exclusion_zone(found.osm, TRAIL_GENERATED)
    lines.extend(
        budget_lines(found, understory.place(found.points, found.grid, found.area, exclusion))
    )
    lines.append("crown radius (m): n / dropped by NDVI")
    for low, high in ((0.0, 1.0), (1.0, 2.0), (2.0, 3.0), (3.0, 7.0)):
        band_mask = (found.crowns.radius >= low) & (found.crowns.radius < high)
        lines.append(
            f"  {low:3.0f}..{high:3.0f} {int(band_mask.sum()):5d} "
            f"{int((band_mask & found.absent).sum()):5d}"
        )
    return "\n".join(lines)


def kept_at_feet(found: Detection) -> tuple[Crowns, tuple[Floats, Floats], Floats]:
    """The kept crowns as the app places them: at the trunk foot, with the height above that foot
    (apex elevation - foot elevation), the lean to the apex and the apex elevation."""
    apex = found.crowns.select(found.kept)
    foot_x, foot_z = found.feet.x[found.kept], found.feet.z[found.kept]
    foot_y, apex_y = found.vertical.foot_y[found.kept], found.vertical.apex_y[found.kept]
    at_foot = Crowns(foot_x, foot_y, foot_z, apex_y - foot_y, apex.radius)
    return at_foot, (apex.x - foot_x, apex.z - foot_z), apex_y


def document(found: Detection, understory_doc: dict[str, Any], threshold: float) -> dict[str, Any]:
    gone = ~found.kept
    reasons = np.where(found.absent, "ndvi", np.where(found.cliff, "cliff", "overPath"))
    reason = [str(r) for r in reasons[gone]]
    kept, lean, apex_y = kept_at_feet(found)
    return {
        "licence": trail.LICENCE,
        "attribution": [
            trail.ATTRIBUTION,
            "Conté dades modificades de PNOA-LiDAR 2016 CC BY 4.0 www.scne.es · "
            "Institut Cartogràfic Valencià",
            "Ortofoto 2024 25 cm © Institut Cartogràfic Valencià, Generalitat (CC BY 4.0)",
        ],
        "version": SCHEMA_VERSION,
        "frame": {
            "crs": "EPSG:25830",
            "origin": {"e": int(ORIGIN_E), "n": int(ORIGIN_N)},
            "axes": "x = E - origin.e, y = H, z = -(N - origin.n)",
        },
        "method": {
            "lidarClasses": list(LIDAR_VEGETATION_CLASSES),
            "chmCell": CHM_CELL,
            "peakWindow": PEAK_WINDOW,
            "minCrownHeight": MIN_CROWN_HEIGHT,
            "radius": f"mean reach of 8 rays over cells >= {RADIUS_HEIGHT_FRACTION} of the height, "
            f"crossing gaps up to {RADIUS_MAX_GAP} m",
            "area": f"nature reserve (OSM relation {RESERVE_RELATION}) plus {ROUTE_BAND:.0f} m "
            "around the route",
            "ndviBand": {"red": RED_BAND, "nir": NIR_BAND},
            "ndviAbsentThreshold": threshold,
            "scale": f"scale y by height / {NOMINAL_HEIGHT:g} and x, z by scaleXZ, which is "
            f"radius / {NOMINAL_RADIUS:g} held within {SCALE_RATIO[0]}-{SCALE_RATIO[1]} x the "
            "vertical scale",
            "ground": "y is the height of the uncarved DEM (the 1 m MDT); the app must resample "
            "the ground on the rendered terrain tiles, which differ where ADR 0009 corrected it",
            "trunk": f"x, z, y are the trunk foot: the LiDAR apex moved out of the walkable "
            f"corridor + {FOOT_MARGIN} m when it lies inside it; leanX, leanZ = apex - foot "
            f"(at most {MAX_LEAN_PER_HEIGHT} x height); height is the crown above its foot and "
            "apexY the measured elevation of its top; a foot on a cliff slope or more than "
            f"{MAX_FOOT_DROP} m above or below the ground under the apex drops it (overPath)",
            "cliff": f"on slopes >= {CLIFF_SLOPE:.0f} degrees a crown needs a radius over "
            f"{MIN_CROWN_RADIUS} m and NDVI >= {CLIFF_MIN_NDVI}, else it is dropped",
            "seed": SEED,
            "treeShape": "generated (blender/pine.py), not measured: only position, height and "
            "radius come from the LiDAR",
        },
        "counts": {
            "crownsDetected": len(found.crowns) + found.implausible,
            "crownsTooTall": found.implausible,
            "crownsKept": len(kept),
            "crownsAbsent": int(found.absent.sum()),
            "crownsCliff": int(found.cliff.sum()),
            "crownsOverPath": int(found.over_path.sum()),
            "crownsLeaning": int((np.hypot(*lean) > 0.0).sum()),
            "pilotBandPark": found.pilot_park,
            "pilotBandKept": found.pilot_kept,
        },
        "variants": VARIANT_COUNT,
        "crowns": crown_columns(
            kept, found.ndvi[found.kept], found.slope[found.kept], lean=lean, apex_y=apex_y
        ),
        "droppedCrowns": crown_columns(
            found.crowns.select(gone), found.ndvi[gone], found.slope[gone], reason
        ),
        "understory": understory_doc,
    }


def run_vegetation(
    out: Path = VEGETATION_GENERATED, threshold: float = NDVI_ABSENT_THRESHOLD
) -> dict[str, Any]:
    """Compute and write ``vegetation.json`` with its provenance block."""
    found = detect(threshold)
    exclusion = understory.exclusion_zone(found.osm, TRAIL_GENERATED)
    shrubs = understory.place(found.points, found.grid, found.area, exclusion)
    doc = document(found, shrubs, threshold)
    doc.update(artefacts.provenance("vegetation"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, separators=(",", ":")) + "\n", encoding="utf-8")
    return doc
