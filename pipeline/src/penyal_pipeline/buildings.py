"""The two visitor-centre buildings as low-poly volumes (spec 003, E3).

``way/26330271`` (Centro de Interpretación) and ``way/26330272`` (the building beside it) are
extruded from their OSM footprint. Everything vertical comes from the 2016 ICV LiDAR (class 6,
"building") inside the footprint, in absolute elevation, against the same DEM the terrain uses:

* **Plinth**: the site slopes (ground under one footprint spans 7 m), so the walls start at the
  lowest ground found under the footprint and a stone band follows the local ground up
  (``PLINTH_RISE`` above it); the whitewashed wall stands on the band up to the eave. Nothing
  floats and nothing needs a retaining wall the data does not show.
* **Eave** = the 25th percentile of the roof points, **ridge** = their 95th. The lower quartile
  is where a hip roof starts (its low slopes hold most points near the edge) and the 95th
  percentile is the roof top without the few spikes; the 2 m-cell turrets, which would inflate
  the ridge, are removed first. Both are single absolute levels: the LiDAR roof falls about 2 m
  across each building, which one level cannot follow. The residual of the model against the
  points is reported in ``buildings.json`` (``roof.fit``) instead of hidden.
* **Roof**: one four-pitch (hip) roof with a flat top, as the 2014 photo (``docs/research/
  003-fotos-referencia.md``, photo 1) shows Arab-tile hip roofs of low pitch. The ortophoto and
  the LiDAR also show terraces and a solar-panel area on the centre building's roofs; the points
  are consistent with several levels there, but not precise enough to cut them out, so the
  terraces are *not* modelled (recorded as ``roof.terraces``: ``"not modelled"``). The ridge
  ring is the footprint scaled about its centroid, which keeps the vertices paired with the
  eave ring and works for the centre building's hexagon.
* **Turrets**: local maxima 2 m or more above the surrounding roof (a rank filter over 2 m
  cells). The centre building has one; the second building has none and gets none. The photo
  shows ochre square towers with white stepped crenellations: the model is a square shaft with
  eight white merlons, sized from the points; the real towers are smaller and tapered.
* **Not modelled**: the porch of semicircular arches, doors, windows, chimneys and the roof
  tiles (all in the photo, none in the LiDAR at 1.3 m spacing).

Surfaces are four tiled CC0 Poly Haven albedo maps (:data:`TEXTURES`, UVs in metres), tinted per
vertex towards the colours sampled from photo 1 (:data:`COLOURS`). Every number that is not
read from the data is an approximation listed in ``CREDITS.md``.
"""

import itertools
import json
import logging
import math
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import laspy
import numpy as np
import numpy.typing as npt
import rasterio
import shapely
from shapely.geometry import Polygon

from penyal_pipeline import dem, tiles, trail
from penyal_pipeline.dem import Grid
from penyal_pipeline.geo import ORIGIN_E, ORIGIN_N
from penyal_pipeline.paths import BUILD_DIR, GENERATED_DIR
from penyal_pipeline.rawdata import locate
from penyal_pipeline.trail import OsmData

log = logging.getLogger(__name__)

BUILDINGS_JSON = "buildings.json"
BUILDINGS_GLB = "buildings.glb"
BUILDINGS_BUILD_DIR = BUILD_DIR / "buildings"
LIDAR_SOURCE_ID = "icv-lidar-2016-766-4282"
BUILDING_CLASS = 6  # ASPRS "building"

STATUS = "approximate"

# Photo 1 (data/manual/fotos-referencia/commons/01-Calpe-penon-de-ifach-panoramio.jpg, 1920x1440,
# box = x0, y0, x1, y1 in pixels): median sRGB of the box, 8 bit.
#   whitewash  crenellations (720, 440, 920, 470) = (163, 157, 153); the photo is underexposed
#              (overcast), so the colour keeps its hue and is lifted to a lime-paint white, the
#              brightest channel at 215.
#   roof       lit tiles (1000, 635, 1300, 660), 75th percentile = (140, 112, 89).
#   turret     ochre shaft (730, 500, 920, 580) = (149, 124, 92).
#   plinth     dry-stone wall (150, 1150, 450, 1350) = (106, 77, 42).
COLOURS: dict[str, tuple[int, int, int]] = {
    "whitewash": (215, 207, 202),
    "roof": (140, 112, 89),
    "turret": (149, 124, 92),
    "plinth": (106, 77, 42),
}

# Material slots, in the order the GLB lists them: one draw call each.
SURFACES = ("whitewash", "turret", "roof", "plinth")
# Tiled albedo per surface: Poly Haven source id and the metres one texture repeat covers (the
# roof texture shows about 25 pantiles across, a pantile being 0.17 m wide).
TEXTURES: dict[str, tuple[str, float]] = {
    "whitewash": ("polyhaven-white-stucco-diff-1k", 3.0),
    "turret": ("polyhaven-yellow-plaster-diff-1k", 3.0),
    "roof": ("polyhaven-roof-tiles-diff-1k", 4.0),
    "plinth": ("polyhaven-stacked-stone-wall-diff-1k", 2.5),
}
TEXTURE_SUFFIX = ".jpg"
TEXTURE_SIZE = (
    1024  # pixels: the 1k maps as downloaded; four ETC1S KTX2 maps cost ~5 MiB on the GPU
)
TEXTURE_ENCODING = "KTX2 ETC1S"
COLOUR_SOURCE = {
    "photo": "data/manual/fotos-referencia/commons/01-Calpe-penon-de-ifach-panoramio.jpg",
    "boxes": {
        "whitewash": [720, 440, 920, 470],
        "roof": [1000, 635, 1300, 660],
        "turret": [730, 500, 920, 580],
        "plinth": [150, 1150, 450, 1350],
    },
    "note": "median sRGB per box (roof: 75th percentile); whitewash lifted to a max channel of 215",
}

# Not in the data (approximations, CREDITS.md).
PLINTH_RISE = 0.5  # metres of stone above the local ground
MIN_WHITE_WALL = 0.5  # the whitewash band is at least this tall
OVERHANG = 0.5  # metres the roof projects past the walls
RIDGE_SCALE = 0.4  # the flat top of the hip roof is the footprint scaled about its centroid
WALL_STEP = 6.0  # metres: walls are split so the plinth follows the slope
PLINTH_EMBED = 0.2  # metres below the lowest ground the walls start
EAVE_PERCENTILE = 25.0
RIDGE_PERCENTILE = 95.0

CELL = 2.0  # metres, the grid the turrets are found on
BASELINE_WINDOW = 4  # cells each way
BASELINE_PERCENTILE = 30.0
TURRET_MIN_EXCESS = 2.0  # metres a cell top stands over its surroundings
TURRET_POINT_EXCESS = 1.0  # metres a point stands over its cell baseline to size the turret
TURRET_MIN_CELLS = 3
TURRET_MIN_POINTS = 8
TURRET_MIN_HALF = 1.0
TURRET_MAX_HALF = 2.5
TURRET_EMBED = 0.3
MERLON_HEIGHT = 0.6
MERLON_THICKNESS = 0.35
MERLON_SPAN = 0.18  # width of a merlon as a fraction of the turret side

type Float1 = npt.NDArray[np.float64]
type Float2 = npt.NDArray[np.float64]


class BuildingsError(RuntimeError):
    """A building cannot be built from the data or violates a contract."""


@dataclass(frozen=True)
class BuildingSpec:
    id: str
    name: str
    way: int


SPECS = (
    BuildingSpec("centre", "Centro de Interpretación Parque Natural del Penyal d'Ifac", 26330271),
    BuildingSpec("annex", "Edificio contiguo al centro (sin nombre en OSM)", 26330272),
)


@dataclass(frozen=True)
class RoofPoints:
    """LiDAR class-6 points in the local frame: x, z, and absolute elevation y."""

    x: Float1
    z: Float1
    y: Float1


@dataclass(frozen=True)
class Turret:
    centre: tuple[float, float]
    half: tuple[float, float]  # half sides along (u, v)
    heading: float  # radians: the u axis in the (x, z) plane
    base_y: float
    top_y: float
    points: int
    cells: int


@dataclass(frozen=True)
class RoofLevels:
    eave: float
    ridge: float
    percentiles: dict[str, float]
    count: int


@dataclass(frozen=True)
class BuildingMesh:
    """Flat-shaded triangle soup (three own vertices per triangle): a linear RGB tint and a glTF
    UV (metres divided by the texture's tile size) per vertex, a surface index per triangle."""

    positions: npt.NDArray[np.float32]
    normals: npt.NDArray[np.float32]
    colours: npt.NDArray[np.float32]
    uvs: npt.NDArray[np.float32]
    triangles: npt.NDArray[np.int32]
    materials: npt.NDArray[np.int32]
    name: str = ""


@dataclass(frozen=True)
class Building:
    spec: BuildingSpec
    ring: Float2  # (n, 2) local (x, z), outward normal of edge d is (-d_z, d_x)
    area: float
    base_y: float
    ground_min: float
    ground_max: float
    levels: RoofLevels
    turrets: list[Turret]
    fit: dict[str, float]
    mesh: BuildingMesh


# --- geometry helpers ---------------------------------------------------------------------------


def srgb_to_linear(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    channels = np.asarray(rgb, dtype=np.float64) / 255.0
    linear = np.where(channels <= 0.04045, channels / 12.92, ((channels + 0.055) / 1.055) ** 2.4)
    return (float(linear[0]), float(linear[1]), float(linear[2]))


def orient_ring(xz: Float2) -> Float2:
    """The footprint without its closing node, wound so the outward normal of an edge ``d`` is
    ``(-d_z, d_x)`` (the convention every wall and roof quad below relies on)."""
    ring = np.asarray(xz, dtype=np.float64)
    if np.allclose(ring[0], ring[-1]):
        ring = ring[:-1]
    if len(ring) < 3:
        raise BuildingsError("a footprint needs at least three nodes")
    polygon = Polygon(ring)
    if not polygon.is_valid or polygon.area <= 0.0:
        raise BuildingsError("the footprint is not a valid polygon")
    d = ring[1] - ring[0]
    probe = (ring[0] + ring[1]) / 2.0 + 0.01 * np.array([-d[1], d[0]]) / np.hypot(*d)
    return ring[::-1].copy() if polygon.contains(shapely.Point(probe)) else ring


def _unit(vector: Float2) -> Float2:
    return np.asarray(
        vector / np.hypot(vector[..., 0], vector[..., 1])[..., None], dtype=np.float64
    )


def outward_normals(ring: Float2) -> Float2:
    """Unit outward normal of each edge ``i -> i + 1`` (see :func:`orient_ring`)."""
    d = np.roll(ring, -1, axis=0) - ring
    return _unit(np.stack([-d[:, 1], d[:, 0]], axis=1))


def offset_ring(ring: Float2, distance: float) -> Float2:
    """The ring moved outward by ``distance`` with mitred corners (vertices stay paired)."""
    n_next = outward_normals(ring)
    n_prev = np.roll(n_next, 1, axis=0)
    cosine = np.sum(n_next * n_prev, axis=1)
    if np.any(cosine < -0.5):
        raise BuildingsError("a footprint corner is too sharp for the eave overhang")
    return np.asarray(
        ring + distance * (n_next + n_prev) / (1.0 + cosine)[:, None], dtype=np.float64
    )


def planar_uv(points: Float2, normal: Float1, tile: float) -> Float2:
    """Metric planar UVs of a triangle: ``u`` runs along the horizontal of its plane and ``v``
    up the slope (``(x, z)`` for horizontal faces), so a texture keeps one density everywhere."""
    up = np.array([0.0, 1.0, 0.0])
    if abs(float(normal[1])) > 0.99:
        u, v = points[:, 0], points[:, 2]
    else:
        along = np.cross(up, normal)
        along /= np.linalg.norm(along)
        slope = np.cross(normal, along)
        u, v = points @ along, points @ slope
    return np.stack([u / tile, -v / tile], axis=1)


class MeshBuilder:
    """Collects triangles; every face is wound so its normal agrees with a given direction."""

    def __init__(self, tints: dict[str, tuple[float, float, float]] | None = None) -> None:
        self.tints = tints if tints is not None else default_tints()
        self.positions: list[Float1] = []
        self.colours: list[tuple[float, float, float]] = []
        self.uvs: list[Float1] = []
        self.materials: list[int] = []

    def triangle(
        self,
        a: Float1,
        b: Float1,
        c: Float1,
        surface: str,
        outward: Float1 | None = None,
    ) -> None:
        normal = np.cross(b - a, c - a)
        if outward is not None and float(np.dot(normal, outward)) < 0.0:
            b, c = c, b
            normal = -normal
        length = float(np.linalg.norm(normal))
        if length < 1e-9:
            return
        corners = np.array([a, b, c], dtype=np.float64)
        uv = planar_uv(corners, normal / length, TEXTURES[surface][1])
        self.positions.extend([a, b, c])
        self.colours.extend([self.tints[surface]] * 3)
        self.uvs.extend(uv)
        self.materials.append(SURFACES.index(surface))

    def quad(self, corners: Float2, surface: str, outward: Float1 | None = None) -> None:
        p = np.asarray(corners, dtype=np.float64)
        hint = outward if outward is not None else np.cross(p[1] - p[0], p[3] - p[0])
        self.triangle(p[0], p[1], p[2], surface, hint)
        self.triangle(p[0], p[2], p[3], surface, hint)

    def box(
        self,
        centre: tuple[float, float],
        half: tuple[float, float],
        heading: float,
        y0: float,
        y1: float,
        surface: str,
    ) -> None:
        """An upright box with its top and four sides (no bottom), turned by ``heading``."""
        u = np.array([math.cos(heading), 0.0, math.sin(heading)])
        v = np.array([-math.sin(heading), 0.0, math.cos(heading)])
        c = np.array([centre[0], 0.0, centre[1]])
        up = np.array([0.0, 1.0, 0.0])
        lo, hi = np.array([0.0, y0, 0.0]), np.array([0.0, y1, 0.0])
        corners = [
            c + sx * half[0] * u + sz * half[1] * v
            for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))
        ]
        for k in range(4):
            a, b = corners[k], corners[(k + 1) % 4]
            outward = np.cross(up, b - a)
            self.quad(np.array([a + lo, b + lo, b + hi, a + hi]), surface, outward)
        self.quad(np.array([p + hi for p in corners]), surface, up)

    def finish(self, name: str) -> BuildingMesh:
        if not self.positions:
            raise BuildingsError(f"{name}: empty mesh")
        positions = np.array(self.positions, dtype=np.float64).reshape(-1, 3)
        faces = positions.reshape(-1, 3, 3)
        normals = np.cross(faces[:, 1] - faces[:, 0], faces[:, 2] - faces[:, 0])
        normals /= np.linalg.norm(normals, axis=1)[:, None]
        return BuildingMesh(
            positions=positions.astype(np.float32),
            normals=np.repeat(normals, 3, axis=0).astype(np.float32),
            colours=np.array(self.colours, dtype=np.float32),
            uvs=np.array(self.uvs, dtype=np.float32),
            triangles=np.arange(len(positions), dtype=np.int32).reshape(-1, 3),
            materials=np.array(self.materials, dtype=np.int32),
            name=name,
        )


def merge_meshes(meshes: list[BuildingMesh], name: str) -> BuildingMesh:
    """One mesh from several: the export draws every surface of both buildings in one call."""
    offsets = np.cumsum([0, *(len(m.positions) for m in meshes[:-1])])
    return BuildingMesh(
        positions=np.concatenate([m.positions for m in meshes]),
        normals=np.concatenate([m.normals for m in meshes]),
        colours=np.concatenate([m.colours for m in meshes]),
        uvs=np.concatenate([m.uvs for m in meshes]),
        triangles=np.concatenate(
            [m.triangles + off for m, off in zip(meshes, offsets, strict=True)]
        ),
        materials=np.concatenate([m.materials for m in meshes]),
        name=name,
    )


def default_tints() -> dict[str, tuple[float, float, float]]:
    """The photo colours, linear: the tint when no texture is known (and in unit tests)."""
    return {name: srgb_to_linear(rgb) for name, rgb in COLOURS.items()}


def texture_means(paths: dict[str, Path]) -> dict[str, tuple[float, float, float]]:
    """Mean linear RGB of each surface's texture."""
    means: dict[str, tuple[float, float, float]] = {}
    for name, path in paths.items():
        with rasterio.open(path) as src:
            pixels = src.read(out_dtype="float64")[:3] / 255.0
        linear = np.where(pixels <= 0.04045, pixels / 12.92, ((pixels + 0.055) / 1.055) ** 2.4)
        mean = linear.reshape(3, -1).mean(axis=1)
        means[name] = (float(mean[0]), float(mean[1]), float(mean[2]))
    return means


def texture_tints(
    means: dict[str, tuple[float, float, float]],
) -> dict[str, tuple[float, float, float]]:
    """Per-vertex tint that pulls each texture towards its photo colour (never brightens it:
    glTF multiplies, and a tint above 1 would clip)."""
    wanted = default_tints()
    tints: dict[str, tuple[float, float, float]] = {}
    for name, mean in means.items():
        ratio = np.clip(np.array(wanted[name]) / np.maximum(np.array(mean), 1e-4), 0.0, 1.0)
        tints[name] = (float(ratio[0]), float(ratio[1]), float(ratio[2]))
    return tints


def texture_paths() -> dict[str, Path]:
    return {
        name: locate(source_id, TEXTURE_SUFFIX).path for name, (source_id, _) in TEXTURES.items()
    }


# --- LiDAR --------------------------------------------------------------------------------------


def lidar_roof_points(path: Path, footprint: Polygon) -> RoofPoints:
    """Class-6 points of the tile inside ``footprint``, noise removed."""
    las = laspy.read(path)
    x = np.asarray(las.x, dtype=np.float64) - ORIGIN_E
    z = -(np.asarray(las.y, dtype=np.float64) - ORIGIN_N)
    y = np.asarray(las.z, dtype=np.float64)
    keep = np.asarray(las.classification) == BUILDING_CLASS
    keep &= shapely.contains_xy(footprint, x, z)
    keep &= (y >= dem.LIDAR_NOISE_RANGE[0]) & (y <= dem.LIDAR_NOISE_RANGE[1])
    return RoofPoints(x[keep], z[keep], y[keep])


def _cell_grid(points: RoofPoints, x0: float, z0: float) -> tuple[npt.NDArray[np.intp], ...]:
    columns = np.floor((points.x - x0) / CELL).astype(np.intp)
    rows = np.floor((points.z - z0) / CELL).astype(np.intp)
    return rows, columns


def detect_turrets(
    points: RoofPoints, heading: float
) -> tuple[list[Turret], npt.NDArray[np.bool_]]:
    """Turrets and the mask of the points that belong to them.

    A cell is a turret cell when its highest point stands ``TURRET_MIN_EXCESS`` over the
    ``BASELINE_PERCENTILE`` of the non-empty cells within ``BASELINE_WINDOW`` cells (the roof
    around it); 8-connected turret cells with enough cells and points make one turret.
    """
    none = np.zeros(len(points.x), dtype=np.bool_)
    if len(points.x) == 0:
        return [], none
    x0, z0 = float(points.x.min()), float(points.z.min())
    rows, columns = _cell_grid(points, x0, z0)
    shape = (int(rows.max()) + 1, int(columns.max()) + 1)
    top = np.full(shape, -np.inf)
    np.maximum.at(top, (rows, columns), points.y)
    filled = np.isfinite(top)
    baseline = np.full(shape, np.nan)
    for r, c in zip(*np.nonzero(filled), strict=True):
        window = top[
            max(r - BASELINE_WINDOW, 0) : r + BASELINE_WINDOW + 1,
            max(c - BASELINE_WINDOW, 0) : c + BASELINE_WINDOW + 1,
        ]
        baseline[r, c] = np.percentile(window[np.isfinite(window)], BASELINE_PERCENTILE)
    high = filled & (top - baseline >= TURRET_MIN_EXCESS)
    seen = np.zeros(shape, dtype=np.bool_)
    turrets: list[Turret] = []
    mask = none.copy()
    u = np.array([math.cos(heading), math.sin(heading)])
    v = np.array([-math.sin(heading), math.cos(heading)])
    for start in zip(*np.nonzero(high), strict=True):
        if seen[start]:
            continue
        queue, cells = deque([start]), []
        seen[start] = True
        while queue:
            r, c = queue.popleft()
            cells.append((r, c))
            for dr, dc in itertools.product((-1, 0, 1), repeat=2):
                n = (r + dr, c + dc)
                if 0 <= n[0] < shape[0] and 0 <= n[1] < shape[1] and high[n] and not seen[n]:
                    seen[n] = True
                    queue.append(n)
        in_cluster = np.zeros(shape, dtype=np.bool_)
        for cell in cells:
            in_cluster[cell] = True
        member = in_cluster[rows, columns] & (
            points.y - baseline[rows, columns] >= TURRET_POINT_EXCESS
        )
        if len(cells) < TURRET_MIN_CELLS or int(member.sum()) < TURRET_MIN_POINTS:
            continue
        xz = np.stack([points.x[member], points.z[member]], axis=1)
        along_u, along_v = xz @ u, xz @ v
        centre_u, centre_v = (
            (along_u.min() + along_u.max()) / 2,
            (along_v.min() + along_v.max()) / 2,
        )
        half = tuple(
            float(np.clip((a.max() - a.min()) / 2, TURRET_MIN_HALF, TURRET_MAX_HALF))
            for a in (along_u, along_v)
        )
        centre = centre_u * u + centre_v * v
        turrets.append(
            Turret(
                centre=(float(centre[0]), float(centre[1])),
                half=(half[0], half[1]),
                heading=heading,
                base_y=float("nan"),
                top_y=float(np.percentile(points.y[member], 90.0)),
                points=int(member.sum()),
                cells=len(cells),
            )
        )
        mask |= in_cluster[rows, columns] & (
            points.y - baseline[rows, columns] >= TURRET_POINT_EXCESS
        )
    return turrets, mask


def roof_levels(points: RoofPoints) -> RoofLevels:
    if len(points.y) < 20:
        raise BuildingsError(f"only {len(points.y)} LiDAR roof points: too few to size a roof")
    marks = (0, 5, 25, 50, 75, 95, 100)
    percentiles = {f"p{p}": round(float(np.percentile(points.y, p)), 3) for p in marks}
    return RoofLevels(
        eave=float(np.percentile(points.y, EAVE_PERCENTILE)),
        ridge=float(np.percentile(points.y, RIDGE_PERCENTILE)),
        percentiles=percentiles,
        count=len(points.y),
    )


# --- building -----------------------------------------------------------------------------------


def surface_height(triangles: npt.NDArray[np.float64], x: Float1, z: Float1) -> Float1:
    """Height of the roof triangles ``(m, 3, 3)`` at plan positions; NaN where none covers it."""
    result = np.full(len(x), np.nan)
    for tri in triangles:
        (ax, _, az), (bx, _, bz), (cx, _, cz) = tri
        det = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
        if abs(det) < 1e-12:
            continue
        w1 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / det
        w2 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / det
        w3 = 1.0 - w1 - w2
        inside = (w1 >= -1e-9) & (w2 >= -1e-9) & (w3 >= -1e-9) & np.isnan(result)
        result[inside] = (w1 * tri[0, 1] + w2 * tri[1, 1] + w3 * tri[2, 1])[inside]
    return result


def _ground_samples(ring: Float2, polygon: Polygon, ground: Grid) -> tuple[float, float]:
    x0, z0, x1, z1 = polygon.bounds
    gx, gz = np.meshgrid(np.arange(x0, x1 + 1.0, 1.0), np.arange(z0, z1 + 1.0, 1.0))
    inside = shapely.contains_xy(polygon, gx.ravel(), gz.ravel())
    px = np.concatenate([gx.ravel()[inside], ring[:, 0]])
    pz = np.concatenate([gz.ravel()[inside], ring[:, 1]])
    heights = ground.sample(px, pz)
    return float(heights.min()), float(heights.max())


def _heading(ring: Float2) -> float:
    """The direction of the longest edge, folded into [0, pi / 2): the building's own axes."""
    edges = np.roll(ring, -1, axis=0) - ring
    longest = edges[int(np.argmax(np.hypot(edges[:, 0], edges[:, 1])))]
    return float(math.atan2(longest[1], longest[0]) % (math.pi / 2.0))


def add_turret(builder: MeshBuilder, turret: Turret) -> None:
    """An ochre square shaft crowned by eight white merlons: four corners and four mid-sides."""
    shaft_top = turret.top_y - MERLON_HEIGHT
    builder.box(turret.centre, turret.half, turret.heading, turret.base_y, shaft_top, "turret")
    u = np.array([math.cos(turret.heading), math.sin(turret.heading)])
    v = np.array([-u[1], u[0]])
    centre = np.array(turret.centre)
    hu, hv = turret.half
    t = MERLON_THICKNESS / 2.0
    merlons: list[tuple[Float1, tuple[float, float]]] = []
    for sx, sz in itertools.product((-1.0, 1.0), repeat=2):
        merlons.append((centre + sx * (hu - t) * u + sz * (hv - t) * v, (t, t)))
    for sign in (-1.0, 1.0):
        merlons.append((centre + sign * (hv - t) * v, (MERLON_SPAN * hu, t)))
        merlons.append((centre + sign * (hu - t) * u, (t, MERLON_SPAN * hv)))
    for position, half in merlons:
        builder.box(
            (float(position[0]), float(position[1])),
            half,
            turret.heading,
            shaft_top,
            turret.top_y,
            "whitewash",
        )


def build_building(
    spec: BuildingSpec,
    footprint_xz: Float2,
    points: RoofPoints,
    ground: Grid,
    tints: dict[str, tuple[float, float, float]] | None = None,
) -> Building:
    """Walls, hip roof and turrets for one footprint, from its LiDAR roof points."""
    ring = orient_ring(footprint_xz)
    polygon = Polygon(ring)
    ground_min, ground_max = _ground_samples(ring, polygon, ground)
    heading = _heading(ring)
    turrets, turret_mask = detect_turrets(points, heading)
    roof_points = RoofPoints(points.x[~turret_mask], points.z[~turret_mask], points.y[~turret_mask])
    levels = roof_levels(roof_points)
    eave, ridge = levels.eave, levels.ridge
    if eave <= ground_max:
        raise BuildingsError(
            f"{spec.id}: the eave ({eave:.2f} m) is not above the highest ground under the "
            f"footprint ({ground_max:.2f} m)"
        )
    if ridge <= eave:
        raise BuildingsError(
            f"{spec.id}: the ridge ({ridge:.2f}) is not above the eave ({eave:.2f})"
        )
    base_y = ground_min - PLINTH_EMBED

    builder = MeshBuilder(tints)
    count = len(ring)
    for i in range(count):
        a, b = ring[i], ring[(i + 1) % count]
        segments = max(1, math.ceil(float(np.hypot(*(b - a))) / WALL_STEP))
        along = a + (b - a) * (np.arange(segments + 1) / segments)[:, None]
        top = np.clip(
            ground.sample(along[:, 0], along[:, 1]) + PLINTH_RISE,
            base_y + 0.1,
            eave - MIN_WHITE_WALL,
        )
        for k in range(segments):
            p, q = along[k], along[k + 1]
            bands = (
                ("plinth", (base_y, base_y), (top[k], top[k + 1])),
                ("whitewash", (top[k], top[k + 1]), (eave, eave)),
            )
            for name, low, high in bands:
                builder.quad(
                    np.array(
                        [
                            [p[0], low[0], p[1]],
                            [q[0], low[1], q[1]],
                            [q[0], high[1], q[1]],
                            [p[0], high[0], p[1]],
                        ]
                    ),
                    name,
                )
    out = offset_ring(ring, OVERHANG)
    centre = np.array(polygon.centroid.coords[0])
    top_ring = centre + RIDGE_SCALE * (ring - centre)
    down, up = np.array([0.0, -1.0, 0.0]), np.array([0.0, 1.0, 0.0])
    roof_triangles: list[Float2] = []
    for i in range(count):
        j = (i + 1) % count
        builder.quad(
            np.array(
                [
                    [ring[i, 0], eave, ring[i, 1]],
                    [ring[j, 0], eave, ring[j, 1]],
                    [out[j, 0], eave, out[j, 1]],
                    [out[i, 0], eave, out[i, 1]],
                ]
            ),
            "whitewash",
            down,
        )
        slope = np.array(
            [
                [out[i, 0], eave, out[i, 1]],
                [out[j, 0], eave, out[j, 1]],
                [top_ring[j, 0], ridge, top_ring[j, 1]],
                [top_ring[i, 0], ridge, top_ring[i, 1]],
            ]
        )
        builder.quad(slope, "roof", None)
        roof_triangles.extend([slope[[0, 1, 2]], slope[[0, 2, 3]]])
        cap = np.array(
            [
                [centre[0], ridge, centre[1]],
                [top_ring[i, 0], ridge, top_ring[i, 1]],
                [top_ring[j, 0], ridge, top_ring[j, 1]],
            ]
        )
        builder.triangle(cap[0], cap[1], cap[2], "roof", up)
        roof_triangles.append(cap)
    surface = np.array(roof_triangles, dtype=np.float64)
    plan_area = sum(
        0.5
        * abs((t[1, 0] - t[0, 0]) * (t[2, 2] - t[0, 2]) - (t[2, 0] - t[0, 0]) * (t[1, 2] - t[0, 2]))
        for t in surface
    )
    if not math.isclose(plan_area, Polygon(out).area, rel_tol=1e-6):
        raise BuildingsError(
            f"{spec.id}: the ridge ring is not star-shaped about the centroid "
            f"(roof plan {plan_area:.1f} m2 vs eave outline {Polygon(out).area:.1f} m2)"
        )

    placed: list[Turret] = []
    for turret in turrets:
        if not polygon.contains(shapely.Point(turret.centre)):
            continue
        u = np.array([math.cos(turret.heading), math.sin(turret.heading)])
        v = np.array([-u[1], u[0]])
        corners = [
            np.array(turret.centre) + sx * turret.half[0] * u + sz * turret.half[1] * v
            for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))
        ]
        under = surface_height(
            surface, np.array([c[0] for c in corners]), np.array([c[1] for c in corners])
        )
        base = float(np.nanmin(under)) - TURRET_EMBED if np.isfinite(under).any() else eave
        placed.append(
            Turret(
                turret.centre,
                turret.half,
                turret.heading,
                base,
                max(turret.top_y, base + 1.5),
                turret.points,
                turret.cells,
            )
        )
    for turret in placed:
        add_turret(builder, turret)

    model = surface_height(surface, roof_points.x, roof_points.z)
    covered = np.isfinite(model)
    residual = roof_points.y[covered] - model[covered]
    fit = {
        "points": float(covered.sum()),
        "meanError": round(float(residual.mean()), 3),
        "rmse": round(float(np.sqrt(np.mean(residual**2))), 3),
        "maxAbsError": round(float(np.abs(residual).max()), 3),
    }
    return Building(
        spec=spec,
        ring=ring,
        area=float(polygon.area),
        base_y=base_y,
        ground_min=ground_min,
        ground_max=ground_max,
        levels=levels,
        turrets=placed,
        fit=fit,
        mesh=builder.finish(f"building_{spec.id}"),
    )


def footprint_of(osm: OsmData, way: int) -> Float2:
    entry = osm.ways.get(way)
    if entry is None:
        raise BuildingsError(f"way {way} is missing from the OSM extract")
    return np.array([osm.xz[n] for n in entry.nodes], dtype=np.float64)


# --- document and run ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BuildingsReport:
    document: dict[str, Any]
    triangles: int
    glb_bytes: int
    json_bytes: int


def _mm(value: float) -> float:
    return round(float(value), 3)


def _entry(building: Building, osm: OsmData) -> dict[str, Any]:
    tags = osm.ways[building.spec.way].tags
    levels = building.levels
    return {
        "id": building.spec.id,
        "name": building.spec.name,
        "osmWay": building.spec.way,
        "osmTags": {k: tags[k] for k in ("building", "tourism", "name", "fee") if k in tags},
        "footprint": [[_mm(x), _mm(z)] for x, z in building.ring],
        "footprintArea": _mm(building.area),
        "ground": {"min": _mm(building.ground_min), "max": _mm(building.ground_max)},
        "plinth": {
            "baseY": _mm(building.base_y),
            "rise": PLINTH_RISE,
            "note": "walls start at the lowest ground under the footprint; the stone band follows "
            "the DEM up to `rise` above it",
        },
        "eave": {
            "y": _mm(levels.eave),
            "percentile": EAVE_PERCENTILE,
            "aboveLowestGround": _mm(levels.eave - building.ground_min),
            "aboveHighestGround": _mm(levels.eave - building.ground_max),
        },
        "roof": {
            "kind": "hip",
            "ridgeY": _mm(levels.ridge),
            "ridgePercentile": RIDGE_PERCENTILE,
            "rise": _mm(levels.ridge - levels.eave),
            "ridgeScale": RIDGE_SCALE,
            "overhang": OVERHANG,
            "terraces": "not modelled",
            "lidar": {"class": BUILDING_CLASS, "points": levels.count, "y": levels.percentiles},
            "fit": building.fit,
        },
        "turrets": [
            {
                "centre": [_mm(t.centre[0]), _mm(t.centre[1])],
                "half": [_mm(t.half[0]), _mm(t.half[1])],
                "headingDeg": _mm(math.degrees(t.heading)),
                "baseY": _mm(t.base_y),
                "topY": _mm(t.top_y),
                "lidarPoints": t.points,
            }
            for t in building.turrets
        ],
        "mesh": {
            "name": building.mesh.name,
            "triangles": int(building.mesh.triangles.shape[0]),
        },
    }


def build_document(
    buildings: list[Building], osm: OsmData, osm_sha256: str, provenance: dict[str, Any]
) -> dict[str, Any]:
    return {
        "version": 1,
        "status": STATUS,
        "licence": trail.LICENCE,
        "attribution": trail.ATTRIBUTION,
        "source": {"id": trail.OSM_SOURCE_ID, "sha256": osm_sha256},
        "frame": {"crs": "EPSG:25830", "origin": {"e": int(ORIGIN_E), "n": int(ORIGIN_N)}},
        "glb": BUILDINGS_GLB,
        "node": "buildings",
        "surfaces": list(SURFACES),
        "textures": {
            name: {
                "source": source_id,
                "tileMetres": tile,
                "sizePixels": TEXTURE_SIZE,
                "encoding": TEXTURE_ENCODING,
            }
            for name, (source_id, tile) in TEXTURES.items()
        },
        "textureNote": "albedo only, CC0 Poly Haven, 1k, encoded to KTX2 ETC1S by the optimise",
        "colours": {k: list(v) for k, v in COLOURS.items()},
        "colourSource": COLOUR_SOURCE,
        "approximations": [
            "facades and colours come from one 2014 photo (Commons, Panoramio); the textures are "
            "generic Poly Haven materials, not the real surfaces",
            "heights are single LiDAR percentiles (eave p25, ridge p95) over a hip roof; "
            "terraces and the solar-panel area are not modelled",
            "turrets are square shafts with eight merlons, sized from LiDAR local maxima",
            "the arched porch, doors, windows and chimneys are not modelled",
        ],
        "buildings": [_entry(b, osm) for b in buildings],
        **provenance,
    }


def run_buildings(
    out_dir: Path = GENERATED_DIR,
    build_dir: Path = BUILDINGS_BUILD_DIR,
    provenance: dict[str, Any] | None = None,
) -> BuildingsReport:
    """Write ``buildings.glb`` (optimised) and ``buildings.json`` into ``out_dir``."""
    from penyal_pipeline.blender import buildings as blender_buildings

    raw = locate(trail.OSM_SOURCE_ID, trail.OSM_FILE)
    osm = trail.load_osm(raw.path)
    grid, _ = dem.load_dem()
    lidar = locate(LIDAR_SOURCE_ID, ".laz").path
    paths = texture_paths()
    tints = texture_tints(texture_means(paths))
    result: list[Building] = []
    for spec in SPECS:
        footprint = footprint_of(osm, spec.way)
        points = lidar_roof_points(lidar, Polygon(footprint))
        result.append(build_building(spec, footprint, points, grid, tints))
    build_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    merged = merge_meshes([b.mesh for b in result], "buildings")
    raw_glb = blender_buildings.export_buildings(
        merged, [paths[name] for name in SURFACES], build_dir / BUILDINGS_GLB
    )
    glb_bytes = tiles.optimize_glb(raw_glb, out_dir / BUILDINGS_GLB)
    document = build_document(result, osm, raw.sha256, provenance or {"inputs": [], "tools": {}})
    path = out_dir / BUILDINGS_JSON
    path.write_text(json.dumps(document, separators=(",", ":"), ensure_ascii=False) + "\n", "utf-8")
    log.info("wrote %s (%d bytes)", path, path.stat().st_size)
    return BuildingsReport(
        document=document,
        triangles=sum(int(b.mesh.triangles.shape[0]) for b in result),
        glb_bytes=glb_bytes,
        json_bytes=path.stat().st_size,
    )
