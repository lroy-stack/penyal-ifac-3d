"""Tunnel geometry in the local frame (ADR 0004): cross-section, interior shell, cut volumes.

The cross-section is a flattened arch: flat floor, vertical walls, and a circular vault whose rise
is ``ARCH_RISE_FRACTION`` of the half-width. It is swept along the axis with vertical sections
(the ceiling stays ``height`` above the floor measured vertically, so a sloping floor shears the
extrusion instead of tilting the section). Joints between straight runs are mitred.

The same rings feed the visual shell (``build_shell``) and the convex ``Prism`` pieces used to cut
the terrain (``cut_openings``), so the opening in the terrain is exactly the tunnel volume.

At a mitred joint the left and right floor corners of a ring share one height while the two
adjoining runs slope, so the four floor corners of a prism piece are not exactly coplanar: the cut
volume differs from the shell by under 6 cm there (14 degrees of bend, 0.45 m/m slope). Pieces
split by a plane leave collinear T-junctions on edges whose neighbour was not split; they have no
gap and sit on the rim of the opening.

Profile coordinates are ``(u, v)``: ``u`` towards the left of the walking direction, ``v`` up from
the floor. Strips are listed in an order such that ``sweep x profile_direction`` points into the
tunnel, which fixes both the triangle winding and the normals of the shell.
"""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import shapely

from penyal_pipeline.dem import Grid

ARCH_RISE_FRACTION = 0.8
ARC_SEGMENTS = 12
OVERRUN = 1.0  # metres of shell and cut volume beyond each portal
PLANE_TOLERANCE = 1e-9
FLOOR_NORMAL_Y = 0.85  # inward normals at least this vertical belong to the floor
MIN_PIECE_AREA = 1e-9

type Floats = npt.NDArray[np.float64]
type Ints = npt.NDArray[np.int64]


class GeometryError(ValueError):
    """The section or the axis cannot produce a valid tunnel."""


@dataclass(frozen=True)
class Strip:
    """Consecutive profile vertices that share one smooth surface."""

    uv: Floats  # (k, 2)
    tangent: Floats  # (k, 2) unit profile direction at each vertex


def _arch(width: float, height: float) -> tuple[float, float, float]:
    """``(wall_top, radius, centre_v)`` of the vault."""
    half = width / 2.0
    rise = ARCH_RISE_FRACTION * half
    wall_top = height - rise
    if width <= 0 or height <= 0 or wall_top < 0:
        raise GeometryError(
            f"section {width} x {height} m has no room for a vault of rise {rise:.2f} m"
        )
    radius = (half * half + rise * rise) / (2.0 * rise)
    return wall_top, radius, height - radius


def polygon_uv(width: float, height: float) -> Floats:
    """Closed convex outline: left floor corner, left wall top, the vault, right floor corner.

    The floor edge joins the last vertex back to the first. Shape ``(ARC_SEGMENTS + 3, 2)``.
    """
    half = width / 2.0
    wall_top, radius, centre_v = _arch(width, height)
    start = np.arctan2(wall_top - centre_v, half)
    angles = np.linspace(start, np.pi - start, ARC_SEGMENTS + 1)
    arc = np.column_stack([radius * np.cos(angles), centre_v + radius * np.sin(angles)])
    return np.vstack([[half, 0.0], arc, [-half, 0.0]])


def strips(width: float, height: float) -> tuple[Strip, ...]:
    """Left wall (up), vault (left to right), right wall (down) and floor (right to left)."""
    half = width / 2.0
    wall_top, radius, centre_v = _arch(width, height)
    start = np.arctan2(wall_top - centre_v, half)
    angles = np.linspace(start, np.pi - start, ARC_SEGMENTS + 1)
    arc = np.column_stack([radius * np.cos(angles), centre_v + radius * np.sin(angles)])
    arc_tangent = np.column_stack([-np.sin(angles), np.cos(angles)])

    def straight(a: tuple[float, float], b: tuple[float, float], d: tuple[float, float]) -> Strip:
        return Strip(np.array([a, b]), np.array([d, d]))

    return (
        straight((half, 0.0), (half, wall_top), (0.0, 1.0)),
        Strip(arc, arc_tangent),
        straight((-half, wall_top), (-half, 0.0), (0.0, -1.0)),
        straight((-half, 0.0), (half, 0.0), (1.0, 0.0)),
    )


def _horizontal_unit(vectors: Floats) -> Floats:
    flat = vectors * np.array([1.0, 0.0, 1.0])
    length = np.linalg.norm(flat, axis=-1, keepdims=True)
    if np.any(length < 1e-12):
        raise GeometryError("axis has a zero-length horizontal step")
    return flat / length


@dataclass(frozen=True)
class Frames:
    """Per-vertex frames of an axis: mitred left vector, its scale, unit left, 3D sweep."""

    left: Floats  # (n, 3) unit horizontal vector to the left of the walking direction
    miter: Floats  # (n,) 1 / cos(half the turn): lateral offsets scale by this at joints
    sweep: Floats  # (n, 3) unit 3D tangent


def frames(axis: Floats) -> Frames:
    steps = np.diff(axis, axis=0)
    directions = _horizontal_unit(steps)
    padded = np.vstack([directions[:1], directions, directions[-1:]])
    bisector = _horizontal_unit(padded[:-1] + padded[1:])
    up = np.array([0.0, 1.0, 0.0])
    left = np.cross(up, bisector)
    flat_steps = np.vstack([directions[:1], directions, directions[-1:]])
    cos_half = np.einsum("ij,ij->i", bisector, flat_steps[:-1])
    sweep_raw = np.vstack([steps[:1], steps[:-1] + steps[1:], steps[-1:]])
    sweep = sweep_raw / np.linalg.norm(sweep_raw, axis=1, keepdims=True)
    return Frames(left=left, miter=1.0 / cos_half, sweep=sweep)


def extend_axis(axis: Floats, overrun: float = OVERRUN) -> Floats:
    """Push both ends ``overrun`` metres outwards along the end segments at the end heights."""
    first = axis[0]
    second = next(p for p in axis if np.hypot(*(p - first)[[0, 2]]) > 1e-9)
    last = axis[-1]
    before = next(p for p in axis[::-1] if np.hypot(*(p - last)[[0, 2]]) > 1e-9)

    def push(end: Floats, towards: Floats) -> Floats:
        direction = _horizontal_unit((end - towards)[None, :])[0]
        return np.array([end[0], end[1], end[2]]) + direction * overrun

    return np.vstack([push(first, second), axis, push(last, before)])


@dataclass(frozen=True)
class ShellMesh:
    positions: npt.NDArray[np.float32]
    normals: npt.NDArray[np.float32]
    triangles: npt.NDArray[np.int32]


def build_shell(axis: Floats, width: float, height: float) -> ShellMesh:
    """The interior surface: one quad strip per profile strip, between consecutive axis rings."""
    if axis.shape[0] < 2:
        raise GeometryError("the axis needs at least two points")
    frame = frames(axis)
    positions: list[Floats] = []
    normals: list[Floats] = []
    triangles: list[Ints] = []
    up = np.array([0.0, 1.0, 0.0])
    ring_count = axis.shape[0]
    offset = 0
    for strip in strips(width, height):
        count = strip.uv.shape[0]
        for i in range(ring_count):
            u, v = strip.uv[:, 0:1], strip.uv[:, 1:2]
            positions.append(axis[i] + frame.left[i] * u * frame.miter[i] + up * v)
            profile3 = frame.left[i] * strip.tangent[:, 0:1] + up * strip.tangent[:, 1:2]
            normal = np.cross(frame.sweep[i], profile3)
            normals.append(normal / np.linalg.norm(normal, axis=1, keepdims=True))
        base = offset + np.arange(ring_count - 1)[:, None] * count
        for k in range(count - 1):
            a, b = base + k, base + count + k
            triangles.append(np.stack([a, b, a + 1], axis=-1).reshape(-1, 3))
            triangles.append(np.stack([a + 1, b, b + 1], axis=-1).reshape(-1, 3))
        offset += ring_count * count
    return ShellMesh(
        positions=np.concatenate(positions).astype(np.float32),
        normals=np.concatenate(normals).astype(np.float32),
        triangles=np.concatenate(triangles).astype(np.int32),
    )


def clip_shell_to_surface(
    shell: ShellMesh,
    surface: Callable[[Floats, Floats], Floats],
    skin: float,
) -> ShellMesh:
    """Remove the walls and vault above ``surface - skin`` so nothing pokes out of the rock.

    ``surface(x, z)`` is the terrain height. Near a portal the terrain falls below the vault; the
    shell there would be a half-pipe lying on the ground, visible from outside. Triangles are cut
    where the (affine over a triangle) height excess crosses zero; new vertices are shared between
    neighbours, with interpolated normals. Floor vertices (inward normal ``y >= FLOOR_NORMAL_Y``)
    are never cut: the floor is the walkable surface and fills the opening in the terrain.
    """
    positions = shell.positions.astype(np.float64)
    excess = positions[:, 1] - (surface(positions[:, 0], positions[:, 2]) - skin)
    excess[shell.normals[:, 1] >= FLOOR_NORMAL_Y] = -1.0
    outside = excess > 0.0
    corner_out = outside[shell.triangles]
    count = corner_out.sum(axis=1)
    keep = shell.triangles[count == 0]
    new_positions: list[Floats] = []
    new_normals: list[Floats] = []
    cache: dict[tuple[int, int], int] = {}
    base = positions.shape[0]

    def crossing(a: int, b: int) -> int:
        low, high = (a, b) if a < b else (b, a)
        if (low, high) not in cache:
            t = excess[low] / (excess[low] - excess[high])
            cache[(low, high)] = base + len(new_positions)
            new_positions.append(positions[low] + (positions[high] - positions[low]) * t)
            blended = (
                shell.normals[low].astype(np.float64) * (1 - t)
                + shell.normals[high].astype(np.float64) * t
            )
            new_normals.append(blended / np.linalg.norm(blended))
        return cache[(low, high)]

    fresh: list[tuple[int, int, int]] = []
    for t in np.flatnonzero((count > 0) & (count < 3)):
        ids = [int(v) for v in shell.triangles[t]]
        polygon: list[int] = []
        for k, current in enumerate(ids):
            following = ids[(k + 1) % 3]
            if not outside[current]:
                polygon.append(current)
            if outside[current] != outside[following]:
                polygon.append(crossing(current, following))
        for k in range(1, len(polygon) - 1):
            fresh.append((polygon[0], polygon[k], polygon[k + 1]))
    all_positions = np.vstack([positions, np.array(new_positions).reshape(-1, 3)])
    all_normals = np.vstack(
        [shell.normals.astype(np.float64), np.array(new_normals).reshape(-1, 3)]
    )
    triangles = np.concatenate(
        [keep.astype(np.int64), np.array(fresh, dtype=np.int64).reshape(-1, 3)]
    )
    used = np.unique(triangles.ravel())
    remap = np.full(all_positions.shape[0], -1, dtype=np.int64)
    remap[used] = np.arange(used.size)
    return ShellMesh(
        positions=all_positions[used].astype(np.float32),
        normals=all_normals[used].astype(np.float32),
        triangles=remap[triangles].astype(np.int32),
    )


@dataclass(frozen=True)
class Prism:
    """A convex volume: a point is inside when ``planes[:, :3] @ p <= planes[:, 3]`` for all."""

    planes: Floats  # (k, 4) outward unit normal and offset
    low: Floats  # axis-aligned bounds
    high: Floats

    def contains(self, points: Floats, margin: float = 0.0) -> npt.NDArray[np.bool_]:
        distance = points @ self.planes[:, :3].T - self.planes[:, 3]
        return np.asarray((distance <= -margin).all(axis=1))


def _plane(a: Floats, b: Floats, c: Floats, inside: Floats) -> Floats:
    normal = np.cross(b - a, c - a)
    normal = normal / np.linalg.norm(normal)
    if float(normal @ (inside - a)) > 0:
        normal = -normal
    return np.append(normal, float(normal @ a))


def prisms(corners: Floats, width: float, height: float) -> list[Prism]:
    """One convex prism per straight run of ``corners`` (mitred, vertical sections)."""
    frame = frames(corners)
    outline = polygon_uv(width, height)
    up = np.array([0.0, 1.0, 0.0])
    rings = np.stack(
        [
            corners[i] + frame.left[i] * outline[:, 0:1] * frame.miter[i] + up * outline[:, 1:2]
            for i in range(corners.shape[0])
        ]
    )
    pieces: list[Prism] = []
    for k in range(corners.shape[0] - 1):
        start, end = rings[k], rings[k + 1]
        inside = (start.mean(axis=0) + end.mean(axis=0)) / 2.0
        planes = []
        count = outline.shape[0]
        for e in range(count):
            nxt = (e + 1) % count
            planes.append(_plane(start[e], start[nxt], end[e], inside))
        for index, sign in ((k, -1.0), (k + 1, 1.0)):
            bisector = _horizontal_unit(np.cross(frame.left[index], up)[None, :])[0]
            normal = sign * bisector
            planes.append(np.append(normal, float(normal @ corners[index])))
        both = np.vstack([start, end])
        pieces.append(Prism(np.array(planes), both.min(axis=0), both.max(axis=0)))
    return pieces


def _polygon_area(polygon: list[Floats]) -> float:
    origin = polygon[0]
    total = np.zeros(3)
    for k in range(1, len(polygon) - 1):
        total += np.cross(polygon[k] - origin, polygon[k + 1] - origin)
    return float(np.linalg.norm(total)) / 2.0


def _split_point(a: Floats, b: Floats, plane: Floats) -> Floats:
    """Intersection of segment ``a-b`` with ``plane``, identical whichever way it is traversed."""
    low, high = (a, b) if tuple(a) <= tuple(b) else (b, a)
    d_low = float(plane[:3] @ low) - plane[3]
    d_high = float(plane[:3] @ high) - plane[3]
    return low + (high - low) * (d_low / (d_low - d_high))


def _clip(polygon: list[Floats], plane: Floats, keep_inside: bool) -> list[Floats]:
    sign = 1.0 if keep_inside else -1.0

    def signed(p: Floats) -> float:
        return sign * (float(plane[:3] @ p) - plane[3])

    out: list[Floats] = []
    for k, current in enumerate(polygon):
        following = polygon[(k + 1) % len(polygon)]
        s_current, s_following = signed(current), signed(following)
        if s_current <= PLANE_TOLERANCE:
            out.append(current)
        if (s_current < -PLANE_TOLERANCE and s_following > PLANE_TOLERANCE) or (
            s_current > PLANE_TOLERANCE and s_following < -PLANE_TOLERANCE
        ):
            out.append(_split_point(current, following, plane))
    return out


def _subtract(triangle: list[Floats], prism: Prism) -> list[list[Floats]] | None:
    """The convex pieces of ``triangle`` outside ``prism``; ``None`` if it does not overlap."""
    overlap = triangle
    for plane in prism.planes:
        overlap = _clip(overlap, plane, keep_inside=True)
        if len(overlap) < 3:
            return None
    if _polygon_area(overlap) < MIN_PIECE_AREA:
        return None
    pieces: list[list[Floats]] = []
    remaining = triangle
    for plane in prism.planes:
        outer = _clip(remaining, plane, keep_inside=False)
        if len(outer) >= 3 and _polygon_area(outer) >= MIN_PIECE_AREA:
            pieces.append(outer)
        remaining = _clip(remaining, plane, keep_inside=True)
        if len(remaining) < 3:
            break
    return pieces


def cut_openings(xyz: Floats, triangles: Ints, volumes: list[Prism]) -> tuple[Floats, Ints]:
    """Remove the parts of the triangles that lie inside ``volumes``.

    Triangles that do not overlap a volume are returned untouched. Straddling ones are split on
    the volume's planes with bit-identical points on shared edges; the inside part is dropped.
    Unreferenced vertices are removed (order of the remaining vertices is preserved).
    """
    corners = xyz[triangles]
    new_vertices: list[Floats] = []
    index: dict[tuple[float, float, float], int] = {}
    kept: list[Ints] = []
    cut = np.zeros(triangles.shape[0], dtype=bool)
    pending: dict[int, list[list[Floats]]] = {}
    for volume in volumes:
        low, high = volume.low - 1e-6, volume.high + 1e-6
        near = (corners.max(axis=1) >= low).all(axis=1) & (corners.min(axis=1) <= high).all(axis=1)
        for t in np.flatnonzero(near):
            parts = pending.get(int(t), [list(corners[t])])
            replaced: list[list[Floats]] = []
            touched = False
            for part in parts:
                pieces = _subtract(part, volume)
                if pieces is None:
                    replaced.append(part)
                else:
                    touched = True
                    replaced.extend(pieces)
            if touched:
                pending[int(t)] = replaced
                cut[t] = True
    base = xyz.shape[0]
    for t in pending:
        for vertex in triangles[t]:
            index[(float(xyz[vertex, 0]), float(xyz[vertex, 1]), float(xyz[vertex, 2]))] = int(
                vertex
            )
    kept.append(triangles[~cut])
    fresh: list[tuple[int, int, int]] = []
    for t in sorted(pending):
        for piece in pending[t]:
            ids: list[int] = []
            for point in piece:
                key = (float(point[0]), float(point[1]), float(point[2]))
                if key not in index:
                    index[key] = base + len(new_vertices)
                    new_vertices.append(np.array(key))
                ids.append(index[key])
            for k in range(1, len(ids) - 1):
                fresh.append((ids[0], ids[k], ids[k + 1]))
    all_xyz = np.vstack([xyz, np.array(new_vertices).reshape(-1, 3)])
    all_triangles = np.concatenate([kept[0], np.array(fresh, dtype=np.int64).reshape(-1, 3)])
    used = np.unique(all_triangles.ravel())
    remap = np.full(all_xyz.shape[0], -1, dtype=np.int64)
    remap[used] = np.arange(used.size)
    return all_xyz[used], remap[all_triangles]


@dataclass(frozen=True)
class Carve:
    """Lowers the terrain along the west approach so the footpath is open down to the floor.

    The DEM beside the west portal is the rock wall, 4-11 m above the footpath. Inside ``strip``
    and on the outer side of the portal plane, heights are capped at the footpath's own floor
    height (linear in ``path`` distance), which leaves a trench ending in the rock face at the
    portal. Cells already below the floor are untouched.
    """

    path: Floats  # (n, 3) local x, floor height, z from where the climb starts to the portal
    half_width: float
    portal: Floats  # (2,) local x, z
    outward: Floats  # (2,) unit vector from the portal away from the tunnel

    def _line(self) -> shapely.LineString:
        return shapely.LineString(self.path[:, [0, 2]])

    @property
    def strip(self) -> shapely.Polygon:
        return self._line().buffer(self.half_width, cap_style="flat", quad_segs=8)

    def apply(self, grid: Grid) -> Grid:
        """A copy of ``grid`` with the approach carved; the input is not modified."""
        x_min, z_min, x_max, z_max = self.strip.bounds
        c0 = max(0, int(np.floor((x_min - grid.x0) / grid.cell)))
        c1 = min(grid.width, int(np.ceil((x_max - grid.x0) / grid.cell)) + 1)
        r0 = max(0, int(np.floor((z_min - grid.z0) / grid.cell)))
        r1 = min(grid.height, int(np.ceil((z_max - grid.z0) / grid.cell)) + 1)
        cols, rows = np.meshgrid(np.arange(c0, c1), np.arange(r0, r1))
        x = grid.x0 + cols * grid.cell
        z = grid.z0 + rows * grid.cell
        outside = (x - self.portal[0]) * self.outward[0] + (z - self.portal[1]) * self.outward[
            1
        ] >= 0.0
        inside = shapely.intersects_xy(self.strip, x, z) & outside
        line = self._line()
        along = np.concatenate(
            [[0.0], np.cumsum(np.linalg.norm(np.diff(self.path[:, [0, 2]], axis=0), axis=1))]
        )
        points = shapely.points(x[inside], z[inside])
        floor = np.interp(shapely.line_locate_point(line, points), along, self.path[:, 1])
        heights = grid.heights.copy()
        window = heights[r0:r1, c0:c1]
        window[inside] = np.minimum(window[inside], floor.astype(np.float32))
        return Grid(heights, grid.x0, grid.z0, grid.cell)


@dataclass(frozen=True)
class TerrainFeatures:
    """What the tunnel does to the terrain: the carved approach and the cut openings."""

    carve: Carve
    openings: list[Prism]

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Local ``(x_min, z_min, x_max, z_max)`` touched by the carve or the openings."""
        x0, z0, x1, z1 = self.carve.strip.bounds
        for prism in self.openings:
            x0, z0 = min(x0, float(prism.low[0])), min(z0, float(prism.low[2]))
            x1, z1 = max(x1, float(prism.high[0])), max(z1, float(prism.high[2]))
        return x0, z0, x1, z1
