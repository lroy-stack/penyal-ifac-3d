"""Terrain tiles: RTIN meshes with skirts, DEM-gradient normals, UVs, and the build driver.

Layout (all in the local frame, ADR 0004; the manifest contract is in the F1 plan):

* **Near box**: 4 x 4 tiles of 256 m, ``i`` in 1..4 and ``j`` in -5..-2 (tile ``t_{i}_{j}``
  nominally covers ``x in [256 i, 256 (i + 1)]`` and ``z in [256 j, 256 (j + 1)]``). Each tile
  has three LODs built from 257 x 257 DEM samples with shared edges.
* **Far mesh**: the work area (the DEM sample extent) minus the near box, from a 4 m sampling of
  the DEM and RTIN at 4 m maximum error.

Half-cell offset: DEM samples sit at cell centres, ``x = x0 + c`` with ``x0 = -599.5``, so a
lattice of 257 samples that starts on an integer metre would need resampled heights, and
resampling a 1 m LiDAR DEM moves cliff crests by tens of metres. The meshes therefore use the
true cell-centre samples and each tile spans ``[256 i - 0.5, 256 (i + 1) - 0.5]`` (and the same
in ``z``): the whole grid is shifted by half a DEM cell. The manifest reports the nominal tile
bounds in ``x``/``z`` (the contract's grid); the mesh and its UVs use the shifted extent.

Vertical error: every DEM sample inside a tile is within the LOD's maximum error of the mesh
(exact RTIN, see ``rtin``). Random points between samples are compared with the bilinear DEM
in the tests; there the unavoidable difference between a triangulated and a bilinear surface
on cliff cells shows up (reported by ``tests/test_terrain_tiles.py``).

Cracks: neighbouring tiles (and the far mesh) triangulate their shared border independently, so
T-junctions of up to twice the LOD error can open; skirts hang below the border of every mesh
to hide them. Normals come from the DEM gradient at each vertex position, not from the
decimated faces, so shading is identical across LODs and seams.
"""

import json
import logging
import re
import shutil
import subprocess
import time
from collections.abc import Callable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from penyal_pipeline import artefacts, dem, ortho, rtin
from penyal_pipeline.blender import terrain as blender_terrain
from penyal_pipeline.geo import ORIGIN_E, ORIGIN_N
from penyal_pipeline.ortho import LocalRect
from penyal_pipeline.paths import (
    REPO_ROOT,
    TERRAIN_BUILD_DIR,
    TERRAIN_GENERATED_DIR,
    TRAIL_GENERATED,
)
from penyal_pipeline.tunnel_geometry import Prism, TerrainFeatures, cut_openings

log = logging.getLogger(__name__)

NEAR_TILE_SIZE = 256
NEAR_COLUMNS = (1, 2, 3, 4)
NEAR_ROWS = (-5, -4, -3, -2)
LATTICE_SHIFT = -0.5  # metres: DEM cell centres, see the module docstring
TILE_SAMPLES = NEAR_TILE_SIZE + 1
CORRIDOR_MARGIN = 30.0

FAR_MAX_ERROR = 4.0
FAR_CELL = 4.0
FAR_SAMPLES = 1025
FAR_TEXTURE = 2048
FAR_SKIRT = 15.0

START_ANCHOR = (549.3, -1024.4)  # turnstile, local frame
START_RADIUS = 300.0
DOWNLOAD_BUDGET_BYTES = 15 * 1000 * 1000
# ETC1S quality (1-255). At gltf-transform's default of 128 the 25 cm orthophoto turns blocky
# (28.0 dB PSNR, 194 KB for a 1024 px tile); 255 gives 30.2 dB for 278 KB and still leaves the
# start-area download far below the budget.
TEXTURE_QUALITY = 255

# The tunnel mouth is a few pixels at the distances where LOD2 is used and the shell is not loaded
# there: LOD2 keeps the rock (the carved approach still shows in its heights).
OPENING_LODS = (0, 1)
OPENING_MARGIN = 2.0  # metres around the carve and the cut volumes that make a tile "affected"

MANIFEST_NAME = "manifest.json"
FAR_NAME = "far.glb"
TILES_DIR = "tiles"
OPTIMIZE_SCRIPT = REPO_ROOT / "scripts" / "optimize.mjs"

type Floats = npt.NDArray[np.float32]
type Floats64 = npt.NDArray[np.float64]
type Ints = npt.NDArray[np.int32]
type TileKey = tuple[int, int]


class TerrainError(RuntimeError):
    """The terrain build cannot proceed or violates a contract."""


@dataclass(frozen=True)
class Lod:
    level: int
    max_error: float
    texture: int
    skirt: float


LODS = (
    Lod(level=0, max_error=0.25, texture=1024, skirt=2.0),
    Lod(level=1, max_error=1.0, texture=512, skirt=5.0),
    Lod(level=2, max_error=3.0, texture=256, skirt=12.0),
)

NEAR_X_MIN = NEAR_COLUMNS[0] * NEAR_TILE_SIZE + LATTICE_SHIFT
NEAR_X_MAX = (NEAR_COLUMNS[-1] + 1) * NEAR_TILE_SIZE + LATTICE_SHIFT
NEAR_Z_MIN = NEAR_ROWS[0] * NEAR_TILE_SIZE + LATTICE_SHIFT
NEAR_Z_MAX = (NEAR_ROWS[-1] + 1) * NEAR_TILE_SIZE + LATTICE_SHIFT
FAR_X0 = NEAR_X_MIN - 4 * NEAR_TILE_SIZE
FAR_Z0 = NEAR_Z_MIN - 4 * NEAR_TILE_SIZE


@dataclass(frozen=True)
class TerrainMesh:
    """A render-ready mesh in the local frame; surface vertices first, then skirt vertices."""

    positions: Floats
    normals: Floats
    uvs: Floats
    triangles: Ints
    extent: LocalRect
    surface_vertices: int
    surface_triangles: int

    @property
    def triangle_count(self) -> int:
        return int(self.triangles.shape[0])

    @property
    def min_y(self) -> float:
        return float(self.positions[:, 1].min())

    @property
    def max_y(self) -> float:
        return float(self.positions[:, 1].max())


def tile_id(i: int, j: int) -> str:
    return f"t_{i}_{j}"


def parse_tile_id(text: str) -> TileKey:
    match = re.fullmatch(r"t_(-?\d+)_(-?\d+)", text)
    if match is None:
        raise TerrainError(f"tile id {text!r} does not look like t_<i>_<j>")
    key = (int(match.group(1)), int(match.group(2)))
    if key[0] not in NEAR_COLUMNS or key[1] not in NEAR_ROWS:
        raise TerrainError(f"tile {text} is outside the near box (i {NEAR_COLUMNS}, j {NEAR_ROWS})")
    return key


def near_tiles() -> list[TileKey]:
    """All near tiles, row-major (north to south, west to east)."""
    return [(i, j) for j in NEAR_ROWS for i in NEAR_COLUMNS]


def dem_normals(grid: dem.Grid, x: Floats64, z: Floats64) -> Floats:
    """Unit normals of the DEM surface by central differences of one cell at ``(x, z)``."""
    step = grid.cell
    slope_x = (grid.sample(x + step, z) - grid.sample(x - step, z)) / (2.0 * step)
    slope_z = (grid.sample(x, z + step) - grid.sample(x, z - step)) / (2.0 * step)
    normals = np.stack([-slope_x, np.ones_like(slope_x), -slope_z], axis=1)
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    return normals.astype(np.float32)


def boundary_edges(triangles: npt.NDArray[np.int64]) -> npt.NDArray[np.int64]:
    """Directed edges ``(u, v)`` used by exactly one triangle, in the triangle's direction."""
    edges = triangles[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2).astype(np.int64)
    base = int(triangles.max()) + 1 if triangles.size else 1
    forward = edges[:, 0] * base + edges[:, 1]
    backward = edges[:, 1] * base + edges[:, 0]
    return edges[~np.isin(forward, backward)]


def add_skirts(
    xyz: Floats64,
    triangles: npt.NDArray[np.int64],
    edges: npt.NDArray[np.int64],
    depth: float,
) -> tuple[Floats64, npt.NDArray[np.int64], npt.NDArray[np.int64]]:
    """Hang a vertical strip of ``depth`` metres below every boundary edge, facing outwards.

    Returns the extended vertices, the extended triangles and, for each added vertex, the
    index of the surface vertex it copies (so normals and UVs can be copied).
    """
    if edges.size == 0:
        return xyz, triangles, np.zeros(0, dtype=np.int64)
    used = np.unique(edges.ravel())
    base = xyz.shape[0]
    lowered = xyz[used].copy()
    lowered[:, 1] -= depth
    lookup = {int(v): base + k for k, v in enumerate(used)}
    first = edges[:, 0]
    second = edges[:, 1]
    first_low = np.array([lookup[int(v)] for v in first], dtype=np.int64)
    second_low = np.array([lookup[int(v)] for v in second], dtype=np.int64)
    strips = np.concatenate(
        [
            np.stack([first, second_low, second], axis=1),
            np.stack([first, first_low, second_low], axis=1),
        ]
    )
    return (
        np.concatenate([xyz, lowered]),
        np.concatenate([triangles, strips]),
        used,
    )


def _assemble(
    grid: dem.Grid,
    xyz: Floats64,
    triangles: npt.NDArray[np.int64],
    extent: LocalRect,
    skirt_depth: float,
    skirt_edge: Callable[[Floats64, npt.NDArray[np.int64]], npt.NDArray[np.bool_]] | None = None,
) -> TerrainMesh:
    """Normals, UVs and skirts for surface vertices ``xyz`` (local frame, float64)."""
    normals = dem_normals(grid, xyz[:, 0], xyz[:, 2])
    u = (xyz[:, 0] - extent.x_min) / (extent.x_max - extent.x_min)
    v = (xyz[:, 2] - extent.z_min) / (extent.z_max - extent.z_min)
    uvs = np.stack([u, v], axis=1).astype(np.float32)
    edges = boundary_edges(triangles)
    if skirt_edge is not None:
        edges = edges[skirt_edge(xyz, edges)]
    surface_vertices = xyz.shape[0]
    surface_triangles = triangles.shape[0]
    full_xyz, full_triangles, copied = add_skirts(xyz, triangles, edges, skirt_depth)
    return TerrainMesh(
        positions=full_xyz.astype(np.float32),
        normals=np.concatenate([normals, normals[copied]]),
        uvs=np.concatenate([uvs, uvs[copied]]),
        triangles=full_triangles.astype(np.int32),
        extent=extent,
        surface_vertices=surface_vertices,
        surface_triangles=surface_triangles,
    )


def tile_lattice(grid: dem.Grid, i: int, j: int) -> tuple[Floats64, float, float]:
    """The 257 x 257 DEM samples of tile ``(i, j)`` and the local ``(x, z)`` of sample [0, 0]."""
    x_min = i * NEAR_TILE_SIZE + LATTICE_SHIFT
    z_min = j * NEAR_TILE_SIZE + LATTICE_SHIFT
    col = (x_min - grid.x0) / grid.cell
    row = (z_min - grid.z0) / grid.cell
    if abs(col - round(col)) > 1e-6 or abs(row - round(row)) > 1e-6:
        raise TerrainError(f"tile {tile_id(i, j)} does not align with the DEM samples")
    col, row = round(col), round(row)
    if col < 0 or row < 0 or col + TILE_SAMPLES > grid.width or row + TILE_SAMPLES > grid.height:
        raise TerrainError(f"tile {tile_id(i, j)} is not fully inside the DEM")
    heights = grid.heights[row : row + TILE_SAMPLES, col : col + TILE_SAMPLES]
    return heights.astype(np.float64), x_min, z_min


def tile_rtin(grid: dem.Grid, i: int, j: int, lod: Lod) -> tuple[Floats64, rtin.Mesh]:
    """The DEM samples and the RTIN of one tile at one LOD (no skirts)."""
    heights, _, _ = tile_lattice(grid, i, j)
    return heights, rtin.build(heights, lod.max_error)


def _on_tile_border(
    extent: LocalRect,
) -> Callable[[Floats64, npt.NDArray[np.int64]], npt.NDArray[np.bool_]]:
    """Boundary edges lying along one side of the tile (not the rim of a cut opening)."""

    def select(xyz: Floats64, edges: npt.NDArray[np.int64]) -> npt.NDArray[np.bool_]:
        first, second = xyz[edges[:, 0]], xyz[edges[:, 1]]
        keep = np.zeros(edges.shape[0], dtype=bool)
        for axis, bounds in ((0, (extent.x_min, extent.x_max)), (2, (extent.z_min, extent.z_max))):
            for bound in bounds:
                keep |= np.isclose(first[:, axis], bound, atol=1e-9) & np.isclose(
                    second[:, axis], bound, atol=1e-9
                )
        return keep

    return select


def build_tile(
    grid: dem.Grid, i: int, j: int, lod: Lod, openings: Sequence[Prism] = ()
) -> TerrainMesh:
    """One near tile at one LOD, with skirts, normals and UVs.

    ``openings`` are volumes (the tunnel) whose inside is cut out of the surface before the
    skirts are added; normals and UVs of the new vertices come from ``grid`` like the others.
    Skirts hang only below the tile border, never along the rim of an opening.
    """
    heights, mesh = tile_rtin(grid, i, j, lod)
    _, x_min, z_min = tile_lattice(grid, i, j)
    xyz = np.stack(
        [
            x_min + mesh.columns.astype(np.float64),
            heights[mesh.rows, mesh.columns],
            z_min + mesh.rows.astype(np.float64),
        ],
        axis=1,
    )
    triangles = mesh.triangles.astype(np.int64)
    extent = LocalRect(x_min, z_min, x_min + NEAR_TILE_SIZE, z_min + NEAR_TILE_SIZE)
    if not openings:
        return _assemble(grid, xyz, triangles, extent, lod.skirt)
    xyz, triangles = cut_openings(xyz, triangles, list(openings))
    return _assemble(grid, xyz, triangles, extent, lod.skirt, _on_tile_border(extent))


def tile_openings(features: TerrainFeatures | None, lod: Lod) -> list[Prism]:
    """The volumes cut out of a tile at ``lod`` (none at LODs that keep the rock)."""
    if features is None or lod.level not in OPENING_LODS:
        return []
    return list(features.openings)


def tiles_touching(
    bounds: tuple[float, float, float, float], margin: float = OPENING_MARGIN
) -> list[TileKey]:
    """Near tiles whose lattice rectangle meets ``bounds`` (local x_min, z_min, x_max, z_max)."""
    x_min, z_min, x_max, z_max = bounds
    touched: list[TileKey] = []
    for i, j in near_tiles():
        tile_x = i * NEAR_TILE_SIZE + LATTICE_SHIFT
        tile_z = j * NEAR_TILE_SIZE + LATTICE_SHIFT
        if (
            x_max + margin >= tile_x
            and x_min - margin <= tile_x + NEAR_TILE_SIZE
            and z_max + margin >= tile_z
            and z_min - margin <= tile_z + NEAR_TILE_SIZE
        ):
            touched.append((i, j))
    return touched


def _intersection(
    first: tuple[float, float, float], second: tuple[float, float, float], axis: int, bound: float
) -> tuple[float, float, float]:
    """Point of segment ``first-second`` at coordinate ``bound`` on ``axis`` (0 = x, 2 = z).

    Endpoints are ordered before interpolating so that the two triangles sharing the edge
    compute bit-identical points.
    """
    low, high = sorted((first, second), key=lambda p: (p[0], p[2]))
    t = (bound - low[axis]) / (high[axis] - low[axis])
    point = [low[k] + t * (high[k] - low[k]) for k in range(3)]
    point[axis] = bound
    return point[0], point[1], point[2]


def _clip_polygon(
    polygon: list[tuple[float, float, float]], axis: int, bound: float, keep_above: bool
) -> list[tuple[float, float, float]]:
    def inside(p: tuple[float, float, float]) -> bool:
        return p[axis] >= bound if keep_above else p[axis] <= bound

    clipped: list[tuple[float, float, float]] = []
    for k, current in enumerate(polygon):
        following = polygon[(k + 1) % len(polygon)]
        if inside(current):
            clipped.append(current)
        if inside(current) != inside(following):
            clipped.append(_intersection(current, following, axis, bound))
    return clipped


def clip_to_rect(
    xyz: Floats64, triangles: npt.NDArray[np.int64], area: LocalRect
) -> tuple[Floats64, npt.NDArray[np.int64]]:
    """Clip a mesh to ``area`` (Sutherland-Hodgman per straddling triangle), welding new points."""
    x, z = xyz[:, 0], xyz[:, 2]
    inside = (x >= area.x_min) & (x <= area.x_max) & (z >= area.z_min) & (z <= area.z_max)
    corner_x, corner_z = x[triangles], z[triangles]
    outside = (
        (corner_x < area.x_min).all(axis=1)
        | (corner_x > area.x_max).all(axis=1)
        | (corner_z < area.z_min).all(axis=1)
        | (corner_z > area.z_max).all(axis=1)
    )
    whole = inside[triangles].all(axis=1)
    straddling = np.flatnonzero(~whole & ~outside)
    kept = triangles[whole]
    used = np.unique(kept.ravel())
    remap = np.full(xyz.shape[0], -1, dtype=np.int64)
    remap[used] = np.arange(used.size)
    vertices: list[tuple[float, float, float]] = [
        (float(p[0]), float(p[1]), float(p[2])) for p in xyz[used]
    ]
    index = {(p[0], p[2]): k for k, p in enumerate(vertices)}
    new_triangles: list[tuple[int, int, int]] = []
    for t in straddling:
        polygon = [(float(xyz[v, 0]), float(xyz[v, 1]), float(xyz[v, 2])) for v in triangles[t]]
        for axis, bound, above in (
            (0, area.x_min, True),
            (0, area.x_max, False),
            (2, area.z_min, True),
            (2, area.z_max, False),
        ):
            polygon = _clip_polygon(polygon, axis, bound, above)
            if len(polygon) < 3:
                break
        if len(polygon) < 3:
            continue
        ids: list[int] = []
        for point in polygon:
            key = (point[0], point[2])
            if key not in index:
                index[key] = len(vertices)
                vertices.append(point)
            ids.append(index[key])
        for k in range(1, len(ids) - 1):
            a, b, c = ids[0], ids[k], ids[k + 1]
            pa, pb, pc = vertices[a], vertices[b], vertices[c]
            twice_area = (pb[2] - pa[2]) * (pc[0] - pa[0]) - (pb[0] - pa[0]) * (pc[2] - pa[2])
            if abs(twice_area) > 1e-9:
                new_triangles.append((a, b, c))
    merged = np.concatenate([remap[kept], np.array(new_triangles, dtype=np.int64).reshape(-1, 3)])
    return np.array(vertices, dtype=np.float64), merged


def far_extent(grid: dem.Grid) -> LocalRect:
    """The DEM sample extent: the area the far mesh and its texture cover."""
    return LocalRect(
        grid.x0,
        grid.z0,
        grid.x0 + (grid.width - 1) * grid.cell,
        grid.z0 + (grid.height - 1) * grid.cell,
    )


def _on_hole_edge(xyz: Floats64, edges: npt.NDArray[np.int64]) -> npt.NDArray[np.bool_]:
    """Boundary edges that lie along one side of the near box."""
    first, second = xyz[edges[:, 0]], xyz[edges[:, 1]]
    keep = np.zeros(edges.shape[0], dtype=bool)
    for axis, other, bounds in (
        (0, 2, (NEAR_X_MIN, NEAR_X_MAX)),
        (2, 0, (NEAR_Z_MIN, NEAR_Z_MAX)),
    ):
        lo, hi = (NEAR_Z_MIN, NEAR_Z_MAX) if axis == 0 else (NEAR_X_MIN, NEAR_X_MAX)
        for bound in bounds:
            along = (first[:, axis] == bound) & (second[:, axis] == bound)
            within = (
                (first[:, other] >= lo)
                & (first[:, other] <= hi)
                & (second[:, other] >= lo)
                & (second[:, other] <= hi)
            )
            keep |= along & within
    return keep


def build_far(grid: dem.Grid) -> TerrainMesh:
    """The far mesh: work area minus the near box, RTIN at ``FAR_MAX_ERROR`` on a 4 m sampling."""
    axis = np.arange(FAR_SAMPLES, dtype=np.float64) * FAR_CELL
    xs, zs = np.meshgrid(FAR_X0 + axis, FAR_Z0 + axis)
    heights = grid.sample(xs, zs)
    col0 = round((NEAR_X_MIN - FAR_X0) / FAR_CELL)
    row0 = round((NEAR_Z_MIN - FAR_Z0) / FAR_CELL)
    span = round((NEAR_X_MAX - NEAR_X_MIN) / FAR_CELL)
    box = rtin.Box(col0=col0, row0=row0, col1=col0 + span, row1=row0 + span)
    mesh = rtin.build(heights, FAR_MAX_ERROR, box)
    xyz = np.stack(
        [
            FAR_X0 + mesh.columns.astype(np.float64) * FAR_CELL,
            heights[mesh.rows, mesh.columns],
            FAR_Z0 + mesh.rows.astype(np.float64) * FAR_CELL,
        ],
        axis=1,
    )
    extent = far_extent(grid)
    xyz, triangles = clip_to_rect(xyz, mesh.triangles.astype(np.int64), extent)
    return _assemble(grid, xyz, triangles, extent, FAR_SKIRT, _on_hole_edge)


def corridor_margin(polygon: Sequence[Sequence[float]]) -> float:
    """Smallest distance from a corridor vertex to the near-box border (negative if outside)."""
    margins = [
        min(x - NEAR_X_MIN, NEAR_X_MAX - x, z - NEAR_Z_MIN, NEAR_Z_MAX - z) for x, z in polygon
    ]
    return float(min(margins))


def check_corridor(trail_path: Path = TRAIL_GENERATED) -> float | None:
    """Margin of the trail corridor inside the near box; raises when below ``CORRIDOR_MARGIN``."""
    if not trail_path.is_file():
        log.warning(
            "%s is missing: corridor containment not checked (run `penyal trail`)", trail_path
        )
        return None
    polygon = json.loads(trail_path.read_text(encoding="utf-8"))["corridor"]["polygon"]
    margin = corridor_margin(polygon)
    if margin < CORRIDOR_MARGIN:
        raise TerrainError(
            f"the trail corridor is only {margin:.1f} m inside the near box "
            f"(need >= {CORRIDOR_MARGIN:.0f} m): extend the box by whole tiles"
        )
    return margin


def optimize_glb(raw: Path, out: Path, quality: int | None = TEXTURE_QUALITY) -> int:
    """Texture (KTX2 ETC1S) + meshopt through ``scripts/optimize.mjs``; returns the byte size.

    ``quality=None`` keeps textures untouched (meshopt only): for meshes without textures.
    """
    node = shutil.which("node")
    if node is None:
        raise TerrainError("`node` is not on PATH (see .node-version)")
    command = [node, str(OPTIMIZE_SCRIPT), str(raw), str(out)]
    if quality is None:
        command += ["--textures", "keep"]
    else:
        command += ["--textures", "etc1s", "--quality", str(quality)]
    run = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    if run.returncode != 0:
        raise TerrainError(f"optimize failed for {raw.name}:\n{run.stderr or run.stdout}")
    return out.stat().st_size


def _rounded(value: float) -> float:
    return round(float(value), 3)


@dataclass
class _LodResult:
    lod: Lod
    triangles: int
    min_y: float
    max_y: float
    future: Future[int]
    url: str


@dataclass
class BuildReport:
    manifest: dict[str, Any]
    outside_pixels: int
    seconds: float
    corridor_margin: float | None


def _bounds(extent: LocalRect, min_y: float, max_y: float) -> dict[str, float]:
    return {
        "minX": extent.x_min,
        "maxX": extent.x_max,
        "minZ": extent.z_min,
        "maxZ": extent.z_max,
        "minY": _rounded(min_y),
        "maxY": _rounded(max_y),
    }


def start_area_bytes(
    manifest: dict[str, Any],
    anchor: tuple[float, float] = START_ANCHOR,
    radius: float = START_RADIUS,
) -> dict[str, int]:
    """Download at the start position: far + every LOD2 + LOD0/LOD1 of tiles within ``radius``."""
    far = int(manifest["far"]["bytes"]) if manifest.get("far") else 0
    coarse = 0
    fine = 0
    for tile in manifest["near"]["tiles"]:
        b = tile["bounds"]
        dx = max(b["minX"] - anchor[0], 0.0, anchor[0] - b["maxX"])
        dz = max(b["minZ"] - anchor[1], 0.0, anchor[1] - b["maxZ"])
        lods = {lod["level"]: int(lod["bytes"]) for lod in tile["lods"]}
        coarse += lods[max(lods)]
        if (dx * dx + dz * dz) ** 0.5 <= radius:
            fine += sum(size for level, size in lods.items() if level != max(lods))
    return {"far": far, "lod2": coarse, "nearLod0Lod1": fine, "total": far + coarse + fine}


def merge_manifest(existing: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """``existing`` with the tiles of ``update`` replaced (same ids, same order).

    ``far`` is kept unless ``update`` has one.

    Only meaningful when both come from the same DEM and orthophoto: otherwise the untouched
    tiles would describe different data, so this refuses and asks for a full terrain build.
    """
    if existing["source"] != update["source"]:
        raise TerrainError(
            "the DEM or the orthophoto changed since the manifest was written: "
            "run a full `penyal terrain` instead of updating tiles"
        )
    for field in ("inputs", "tools"):
        if existing.get(field) != update.get(field):
            raise TerrainError(
                f"the recorded {field} changed since the manifest was written (or it predates "
                "provenance): run a full `penyal terrain` instead of updating tiles"
            )
    replacements = {tile["id"]: tile for tile in update["near"]["tiles"]}
    unknown = set(replacements) - {tile["id"] for tile in existing["near"]["tiles"]}
    if unknown:
        raise TerrainError(f"tiles {sorted(unknown)} are not in the existing manifest")
    merged = dict(existing)
    merged["near"] = {
        **existing["near"],
        "tiles": [replacements.get(tile["id"], tile) for tile in existing["near"]["tiles"]],
    }
    if "far" in update:
        merged["far"] = update["far"]
    return merged


def run_terrain(
    out_dir: Path = TERRAIN_GENERATED_DIR,
    build_dir: Path = TERRAIN_BUILD_DIR / "glb",
    tiles: Sequence[TileKey] | None = None,
    include_far: bool = True,
    quality: int = TEXTURE_QUALITY,
    workers: int = 3,
    features: TerrainFeatures | None = None,
    update_manifest: bool = False,
) -> BuildReport:
    """Build, export and optimise the terrain, then write ``manifest.json`` into ``out_dir``.

    ``features`` (the tunnel) carve the heights of every tile and cut the openings out of the
    LODs in ``OPENING_LODS``. With ``update_manifest`` the tiles built here replace their entries
    in the manifest already in ``out_dir`` instead of writing a partial one.
    """
    started = time.perf_counter()
    margin = check_corridor()
    grid, dem_meta = dem.load_dem()
    if features is not None:
        grid = features.carve.apply(grid)
    ortho_file = ortho.locate_ortho()
    selected = list(tiles) if tiles is not None else near_tiles()
    build_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / TILES_DIR).mkdir(parents=True, exist_ok=True)
    outside_pixels = 0
    tile_results: dict[TileKey, list[_LodResult]] = {}
    far_result: tuple[TerrainMesh, Future[int]] | None = None
    with (
        ortho.open_ortho(ortho_file.path) as src,
        ThreadPoolExecutor(max_workers=workers) as pool,
    ):

        def export(name: str, mesh: TerrainMesh, size: int, final: Path) -> Future[int]:
            nonlocal outside_pixels
            texture = ortho.read_texture(src, mesh.extent, size)
            outside_pixels += texture.outside
            raw = build_dir / final.name
            blender_terrain.export_terrain(
                blender_terrain.TerrainExport(
                    name=name,
                    positions=mesh.positions,
                    normals=mesh.normals,
                    uvs=mesh.uvs,
                    triangles=mesh.triangles,
                    rgb=texture.rgb,
                ),
                raw,
            )
            return pool.submit(optimize_glb, raw, final, quality)

        for i, j in selected:
            results: list[_LodResult] = []
            for lod in LODS:
                mesh = build_tile(grid, i, j, lod, tile_openings(features, lod))
                name = f"{tile_id(i, j)}_lod{lod.level}"
                final = out_dir / TILES_DIR / f"{name}.glb"
                log.info("%s: %d triangles", name, mesh.triangle_count)
                results.append(
                    _LodResult(
                        lod=lod,
                        triangles=mesh.triangle_count,
                        min_y=mesh.min_y,
                        max_y=mesh.max_y,
                        future=export(name, mesh, lod.texture, final),
                        url=f"{TILES_DIR}/{name}.glb",
                    )
                )
            tile_results[(i, j)] = results
        if include_far:
            far_mesh = build_far(grid)
            log.info("far: %d triangles", far_mesh.triangle_count)
            far_result = (far_mesh, export("far", far_mesh, FAR_TEXTURE, out_dir / FAR_NAME))
        sizes = {key: [r.future.result() for r in results] for key, results in tile_results.items()}
        far_bytes = far_result[1].result() if far_result is not None else 0
    manifest = _manifest(dem_meta, ortho_file.sha256, tile_results, sizes, far_result, far_bytes)
    if update_manifest:
        manifest_path = out_dir / MANIFEST_NAME
        if not manifest_path.is_file():
            raise TerrainError(f"{manifest_path} does not exist: run a full `penyal terrain` first")
        manifest = merge_manifest(json.loads(manifest_path.read_text(encoding="utf-8")), manifest)
    (out_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    report = BuildReport(
        manifest=manifest,
        outside_pixels=outside_pixels,
        seconds=time.perf_counter() - started,
        corridor_margin=margin,
    )
    return report


def _manifest(
    dem_meta: dict[str, Any],
    ortho_sha: str,
    tile_results: dict[TileKey, list[_LodResult]],
    sizes: dict[TileKey, list[int]],
    far_result: tuple[TerrainMesh, Future[int]] | None,
    far_bytes: int,
) -> dict[str, Any]:
    tiles: list[dict[str, Any]] = []
    for (i, j), results in tile_results.items():
        x_min, z_min = i * NEAR_TILE_SIZE, j * NEAR_TILE_SIZE
        nominal = LocalRect(x_min, z_min, x_min + NEAR_TILE_SIZE, z_min + NEAR_TILE_SIZE)
        tiles.append(
            {
                "id": tile_id(i, j),
                "bounds": _bounds(
                    nominal, min(r.min_y for r in results), max(r.max_y for r in results)
                ),
                "lods": [
                    {
                        "level": r.lod.level,
                        "url": r.url,
                        "maxError": r.lod.max_error,
                        "texture": r.lod.texture,
                        "triangles": r.triangles,
                        "bytes": size,
                    }
                    for r, size in zip(results, sizes[(i, j)], strict=True)
                ],
            }
        )
    manifest: dict[str, Any] = {
        "version": 1,
        "frame": {"crs": "EPSG:25830", "origin": {"e": int(ORIGIN_E), "n": int(ORIGIN_N)}},
        "source": {
            "dem": {"id": dem_meta["source"]["id"], "sha256": dem_meta["source"]["sha256"]},
            "ortho": {"id": ortho.ORTHO_SOURCE_ID, "sha256": ortho_sha},
        },
        "near": {"tileSize": NEAR_TILE_SIZE, "tiles": tiles},
        **artefacts.provenance("terrain"),
    }
    if far_result is not None:
        far_mesh, _ = far_result
        manifest["far"] = {
            "url": FAR_NAME,
            "maxError": FAR_MAX_ERROR,
            "texture": FAR_TEXTURE,
            "bounds": _bounds(far_mesh.extent, far_mesh.min_y, far_mesh.max_y),
            "triangles": far_mesh.triangle_count,
            "bytes": far_bytes,
        }
    return manifest
