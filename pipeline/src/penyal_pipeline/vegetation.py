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
from penyal_pipeline.blender.pine import VARIANT_COUNT
from penyal_pipeline.cellhash import SEED, hash_cells, unit_float
from penyal_pipeline.geo import ORIGIN_E, ORIGIN_N
from penyal_pipeline.paths import GENERATED_DIR, TRAIL_GENERATED
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

# The pilot stretch of the research (§4): 40 m each side of the first 421 m of route. The figure
# 186 is a reference that pins the algorithm, not a tuning target: it is the count of the same
# method run on the points inside the bounding box of the band, as the prototype did. A run over
# the whole park finds one crown fewer in the band (a crown the clipped window left uncovered).
PILOT_LENGTH = 421.0
PILOT_BAND = 40.0
PILOT_REFERENCE_CROWNS = 186
PILOT_PARK_CROWNS = 185

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
# excludes 128 of the 1441 crowns analysed (2 of the 185 in the pilot band);
# ``penyal vegetation --analyse`` prints the histogram and the counts for any other threshold.
NDVI_ABSENT_THRESHOLD = 0.07
# Crowns taller than this are LiDAR/DEM mismatches on vertical rock (4 crowns, 23-94 m, on slopes
# of 64-88 degrees), not trees: the tallest plausible tree of the park is a pine of ~20 m.
MAX_CROWN_HEIGHT = 25.0
# On a cliff the LiDAR vegetation classes and the 1 m DEM disagree (the DEM smooths the wall), so
# many "crowns" there are rock: of the 182 crowns on slopes >= 60 degrees, 102 had an NDVI under
# 0.20 and most of the minimum-radius ones are single points. A cliff crown stays only if it is
# wider than the minimum radius and green at least like the low vegetation of the park (median
# NDVI 0.20, measured as for NIR_BAND above). Everything else is dropped, not demoted.
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
    lines = [
        shapely.LineString([osm.xz[n] for n in osm.ways[m["ref"]].nodes])
        for m in relation["members"]
        if m["type"] == "way" and m["role"] == "outer"
    ]
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


def sample_slope(slopes: Floats, grid: dem.Grid, x: Floats, z: Floats) -> Floats:
    """DEM slope in degrees at the cell nearest to each position."""
    rows = np.clip(np.rint((z - grid.z0) / grid.cell), 0, grid.height - 1).astype(np.intp)
    cols = np.clip(np.rint((x - grid.x0) / grid.cell), 0, grid.width - 1).astype(np.intp)
    return np.asarray(slopes[rows, cols], dtype=np.float64)


def cliff_keep(crowns: Crowns, slope: Floats, ndvi: Floats) -> npt.NDArray[np.bool_]:
    """False for crowns on a cliff that are not wider than the minimum radius or not green."""
    on_cliff = slope >= CLIFF_SLOPE
    green = (crowns.radius > MIN_CROWN_RADIUS) & (ndvi >= CLIFF_MIN_NDVI)  # NaN is False
    return np.asarray(~on_cliff | green, dtype=np.bool_)


def crowns_in(crowns: Crowns, area: BaseGeometry) -> npt.NDArray[np.bool_]:
    return np.asarray(shapely.contains_xy(area, crowns.x, crowns.z), dtype=np.bool_)


def pilot_reference_crowns(points: VegetationPoints, grid: dem.Grid, band: BaseGeometry) -> Crowns:
    """The research prototype's figure: points clipped to the band's bounding box, then the crowns
    inside the band."""
    x_min, z_min, x_max, z_max = band.bounds
    window = (points.x >= x_min) & (points.x <= x_max) & (points.z >= z_min) & (points.z <= z_max)
    crowns = detect_crowns(select_points(points, window), grid)
    return crowns.select(crowns_in(crowns, band))


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


def crown_ndvi(raster: NdviRaster, crowns: Crowns) -> Floats:
    """Median NDVI over the pixels whose centre is inside each crown disk (NaN if none valid)."""
    out = np.full(len(crowns), np.nan)
    rows, cols = raster.values.shape
    for i in range(len(crowns)):
        cx, cz, radius = float(crowns.x[i]), float(crowns.z[i]), float(crowns.radius[i])
        c0 = max(0, math.floor((cx - radius - raster.x_min) / raster.res))
        c1 = min(cols, math.ceil((cx + radius - raster.x_min) / raster.res))
        r0 = max(0, math.floor((cz - radius - raster.z_min) / raster.res))
        r1 = min(rows, math.ceil((cz + radius - raster.z_min) / raster.res))
        if c1 <= c0 or r1 <= r0:
            continue
        px = raster.x_min + (np.arange(c0, c1) + 0.5) * raster.res - cx
        pz = raster.z_min + (np.arange(r0, r1) + 0.5) * raster.res - cz
        inside = (px[None, :] ** 2 + pz[:, None] ** 2) <= radius**2
        values = raster.values[r0:r1, c0:c1][inside]
        values = values[~np.isnan(values)]
        if values.size:
            out[i] = float(np.median(values))
    return out


def present_mask(ndvi: Floats, threshold: float) -> npt.NDArray[np.bool_]:
    """Crowns kept: NDVI at or above ``threshold``. A crown with no valid pixel cannot be judged
    and stays."""
    return np.asarray(np.isnan(ndvi) | (ndvi >= threshold), dtype=np.bool_)


# --- document -----------------------------------------------------------------------------------


def _column(values: Floats, decimals: int) -> list[float]:
    return [round(float(v), decimals) for v in values]


def crown_columns(
    crowns: Crowns, ndvi: Floats, slope: Floats, reason: list[str] | None = None
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
        "variant": [int(v) for v in variant],
        "yaw": [int(v) for v in yaw],
        "ndvi": [None if math.isnan(v) else round(float(v), 3) for v in ndvi],
        "slope": _column(slope, 1),
    }
    if reason is not None:
        columns["reason"] = reason
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
    kept: npt.NDArray[np.bool_]
    pilot_reference: int
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
    implausible = int((crowns.height > MAX_CROWN_HEIGHT).sum())
    crowns = crowns.select(crowns.height <= MAX_CROWN_HEIGHT)
    with ortho.open_ortho(ortho.locate_ortho().path) as src:
        raster = read_ndvi(src, (x_min, z_min, x_max, z_max))
    ndvi = crown_ndvi(raster, crowns)
    slope = sample_slope(dem.slope_degrees(grid), grid, crowns.x, crowns.z)
    absent = ~present_mask(ndvi, threshold)
    cliff = ~absent & ~cliff_keep(crowns, slope, ndvi)
    kept = ~absent & ~cliff
    band = pilot_band(route)
    in_band = crowns_in(crowns, band)
    return Detection(
        area=area,
        crowns=crowns,
        ndvi=ndvi,
        slope=slope,
        absent=absent,
        cliff=cliff,
        kept=kept,
        pilot_reference=len(pilot_reference_crowns(points, grid, band)),
        pilot_park=int(in_band.sum()),
        pilot_kept=int((in_band & kept).sum()),
        implausible=implausible,
        points=points,
        route=route,
        grid=grid,
        osm=osm,
    )


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
        f"pilot band (421 m + 40 m): {found.pilot_reference} crowns on the clipped window "
        f"(reference {PILOT_REFERENCE_CROWNS}), {int(in_band.sum())} in the park run "
        f"(pinned {PILOT_PARK_CROWNS})",
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
    return "\n".join(lines)


def document(found: Detection, understory_doc: dict[str, Any], threshold: float) -> dict[str, Any]:
    kept = found.crowns.select(found.kept)
    gone = ~found.kept
    reason = ["ndvi" if a else "cliff" for a in found.absent[gone]]
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
            "pilotBandReference": found.pilot_reference,
            "pilotBandPark": found.pilot_park,
            "pilotBandKept": found.pilot_kept,
        },
        "variants": VARIANT_COUNT,
        "crowns": crown_columns(kept, found.ndvi[found.kept], found.slope[found.kept]),
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
