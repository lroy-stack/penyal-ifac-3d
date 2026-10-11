"""Right-triangulated irregular networks (RTIN) over a square height lattice.

Same triangle hierarchy as Mapbox "Martini" (Will Evans, after Lindstrom & Pascucci): the
``(n x n)`` lattice, ``n = 2**k + 1``, is split into two right triangles and every triangle
``(a, b, c)`` (right angle at ``c``, hypotenuse ``a-b``) into ``(c, a, m)`` and ``(b, c, m)``
with ``m`` the midpoint of the hypotenuse. A triangle is a leaf when its midpoint error is
within the tolerance, and triangles that share a hypotenuse share the midpoint error, so the
mesh never has T-junctions inside the lattice.

Difference from Martini: Martini only measures the error at hypotenuse midpoints, which does
not bound the error at the other lattice points of a leaf. Here the error of a triangle is the
exact maximum vertical distance between the lattice heights inside it and its plane, so the
guarantee holds: **every lattice point is within ``max_error`` of the returned mesh**. The
extra cost is one pass over the lattice per hierarchy level, vectorised with numpy.

Lattice coordinates are ``(x, y) = (column, row)``. Output is deterministic: no randomness, no
hash-ordered containers, all reductions are order-independent maxima.
"""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import numpy.typing as npt

type IntArray = npt.NDArray[np.int64]
type FloatArray = npt.NDArray[np.float64]

_CHUNK_POINTS = 4_000_000


class RtinError(ValueError):
    """The lattice or the request is not valid for an RTIN."""


@dataclass(frozen=True)
class Box:
    """Closed lattice rectangle ``[col0, col1] x [row0, row1]`` that is cut out of the mesh.

    Its edges must lie on lattice lines that are multiples of a power of two dividing the
    box size (an aligned quadtree block) so that triangles never need to be split below a
    few levels to respect it.
    """

    col0: int
    row0: int
    col1: int
    row1: int


@dataclass(frozen=True)
class Mesh:
    """Lattice vertices (``columns``/``rows``, sorted by flat index) and CCW-from-above triangles.

    Winding: a triangle ``(a, b, c)`` has a positive ``+Y`` normal when ``x`` is the column and
    ``z`` the row (``u_z * v_x - u_x * v_z > 0``), the convention of the local frame.
    """

    columns: IntArray
    rows: IntArray
    triangles: npt.NDArray[np.int32]


@dataclass(frozen=True)
class _Level:
    a: IntArray  # (n, 2) lattice (x, y)
    b: IntArray
    c: IntArray
    axis_legs: bool


def lattice_size_ok(count: int) -> bool:
    """``count == 2**k + 1`` with ``k >= 1``."""
    return count >= 3 and (count - 1) & (count - 2) == 0


def _check_lattice(heights: FloatArray) -> int:
    if heights.ndim != 2 or heights.shape[0] != heights.shape[1]:
        raise RtinError(f"heights must be a square lattice, got shape {heights.shape}")
    count = int(heights.shape[0])
    if not lattice_size_ok(count):
        raise RtinError(f"lattice size must be 2**k + 1, got {count}")
    return count


@lru_cache(maxsize=4)
def _hierarchy(size: int) -> tuple[_Level, ...]:
    """All triangles whose hypotenuse midpoint is a lattice point, level by level."""
    a = np.array([[0, 0], [size, size]], dtype=np.int64)
    b = np.array([[size, size], [0, 0]], dtype=np.int64)
    c = np.array([[size, 0], [0, size]], dtype=np.int64)
    levels: list[_Level] = []
    axis_legs = True
    while True:
        levels.append(_Level(a, b, c, axis_legs))
        if not axis_legs and int(np.abs(a[0] - c[0]).max()) == 1:
            break
        m = (a + b) // 2
        a, b, c = (
            np.concatenate([c, b]),
            np.concatenate([a, c]),
            np.concatenate([m, m]),
        )
        axis_legs = not axis_legs
    return tuple(levels)


def _offsets(level: _Level) -> tuple[IntArray, IntArray, IntArray]:
    """Barycentric lattice points of one level's triangles: ``(num_a, num_b, denominator)``.

    A point ``c + (num_a * (a - c) + num_b * (b - c)) / denominator`` with
    ``num_a, num_b >= 0`` and ``num_a + num_b <= denominator``. Diagonal-leg triangles
    contain lattice points only where ``num_a`` and ``num_b`` have the same parity.
    """
    leg = int(np.abs(level.a[0] - level.c[0]).max())
    denominator = leg if level.axis_legs else 2 * leg
    first, second = np.meshgrid(np.arange(denominator + 1), np.arange(denominator + 1))
    keep = first + second <= denominator
    if not level.axis_legs:
        keep &= (first - second) % 2 == 0
    return first[keep], second[keep], np.full(int(keep.sum()), denominator, dtype=np.int64)


def _plane_deviation(
    heights: FloatArray, level: _Level, start: int, stop: int, num: tuple[IntArray, IntArray]
) -> FloatArray:
    """Max ``|height - plane|`` over the lattice points inside triangles ``start:stop``."""
    count = heights.shape[0]
    a, b, c = level.a[start:stop], level.b[start:stop], level.c[start:stop]
    step_a = np.sign(a - c)
    step_b = np.sign(b - c)
    leg = int(np.abs(a[0] - c[0]).max())
    denominator = leg if level.axis_legs else 2 * leg
    divisor = 1 if level.axis_legs else 2
    num_a, num_b = num
    xy = (
        c[:, None, :]
        + (num_a[None, :, None] * step_a[:, None, :] + num_b[None, :, None] * step_b[:, None, :])
        // divisor
    )
    flat = xy[..., 1] * count + xy[..., 0]
    h_flat = heights.reshape(-1)
    h_c = h_flat[c[:, 1] * count + c[:, 0]]
    h_a = h_flat[a[:, 1] * count + a[:, 0]]
    h_b = h_flat[b[:, 1] * count + b[:, 0]]
    plane = (
        h_c[:, None]
        + (num_a[None, :] / denominator) * (h_a - h_c)[:, None]
        + (num_b[None, :] / denominator) * (h_b - h_c)[:, None]
    )
    return np.abs(h_flat[flat] - plane).max(axis=1)


def _straddles(level: _Level, box: Box) -> npt.NDArray[np.bool_]:
    """Triangles whose interior overlaps the open box without lying inside the closed box."""
    verts = np.stack([level.a, level.b, level.c], axis=1)  # (n, 3, 2)
    lo = verts.min(axis=1)
    hi = verts.max(axis=1)
    inside = (
        (lo[:, 0] >= box.col0)
        & (hi[:, 0] <= box.col1)
        & (lo[:, 1] >= box.row0)
        & (hi[:, 1] <= box.row1)
    )
    overlap = (
        (lo[:, 0] < box.col1)
        & (hi[:, 0] > box.col0)
        & (lo[:, 1] < box.row1)
        & (hi[:, 1] > box.row0)
    )
    corners = np.array(
        [[box.col0, box.row0], [box.col1, box.row0], [box.col0, box.row1], [box.col1, box.row1]]
    )
    for first, second in ((0, 1), (1, 2), (2, 0)):
        edge = verts[:, second] - verts[:, first]
        normal = np.stack([-edge[:, 1], edge[:, 0]], axis=1)
        tri_proj = np.einsum("nvk,nk->nv", verts, normal)
        box_proj = corners @ normal.T  # (4, n)
        separated = (box_proj.min(axis=0) >= tri_proj.max(axis=1)) | (
            box_proj.max(axis=0) <= tri_proj.min(axis=1)
        )
        overlap &= ~separated
    return overlap & ~inside


def error_map(heights: FloatArray, cut: Box | None = None) -> FloatArray:
    """Per-lattice-point error: the hypotenuse-midpoint error of the RTIN hierarchy.

    Points that are never a midpoint (the four corners) hold 0. With ``cut`` set, triangles
    straddling the box get an infinite error so that the box edge is always respected.
    """
    count = _check_lattice(heights)
    levels = _hierarchy(count - 1)
    errors = np.zeros(count * count, dtype=np.float64)
    child_midpoints: IntArray | None = None
    for depth in range(len(levels) - 1, -1, -1):
        level = levels[depth]
        size = level.a.shape[0]
        num_a, num_b, _ = _offsets(level)
        deviation = np.empty(size, dtype=np.float64)
        per_chunk = max(1, _CHUNK_POINTS // num_a.size)
        for start in range(0, size, per_chunk):
            stop = min(size, start + per_chunk)
            deviation[start:stop] = _plane_deviation(heights, level, start, stop, (num_a, num_b))
        if child_midpoints is not None:
            half = size
            deviation = np.maximum(deviation, errors[child_midpoints[:half]])
            deviation = np.maximum(deviation, errors[child_midpoints[half : 2 * half]])
        if cut is not None:
            deviation[_straddles(level, cut)] = np.inf
        mid = (level.a + level.b) // 2
        mid_flat = mid[:, 1] * count + mid[:, 0]
        np.maximum.at(errors, mid_flat, deviation)
        child_midpoints = mid_flat
    return errors.reshape(count, count)


def extract(errors: FloatArray, max_error: float, cut: Box | None = None) -> Mesh:
    """Triangulate: split every triangle whose midpoint error exceeds ``max_error``."""
    count = errors.shape[0]
    levels = _hierarchy(count - 1)
    flat_errors = errors.reshape(-1)
    leaves: list[IntArray] = []
    first = levels[0]
    a, b, c = first.a, first.b, first.c
    for depth in range(len(levels)):
        if cut is not None and a.shape[0]:
            verts = np.stack([a, b, c], axis=1)
            inside = (
                (verts[..., 0] >= cut.col0).all(axis=1)
                & (verts[..., 0] <= cut.col1).all(axis=1)
                & (verts[..., 1] >= cut.row0).all(axis=1)
                & (verts[..., 1] <= cut.row1).all(axis=1)
            )
            a, b, c = a[~inside], b[~inside], c[~inside]
        mid = (a + b) // 2
        split = flat_errors[mid[:, 1] * count + mid[:, 0]] > max_error
        keep = ~split
        if keep.any():
            leaves.append(np.stack([a[keep], b[keep], c[keep]], axis=1))
        a, b, c, mid = a[split], b[split], c[split], mid[split]
        a, b, c = np.concatenate([c, b]), np.concatenate([a, c]), np.concatenate([mid, mid])
        if depth == len(levels) - 1 and a.shape[0]:
            # The children of the finest level are unit triangles: always leaves.
            leaves.append(np.stack([a, b, c], axis=1))
    tris = np.concatenate(leaves) if leaves else np.zeros((0, 3, 2), dtype=np.int64)
    flat = tris[..., 1] * count + tris[..., 0]
    unique, inverse = np.unique(flat, return_inverse=True)
    triangles = inverse.reshape(-1, 3).astype(np.int32)
    return _orient(Mesh(unique % count, unique // count, triangles))


def _orient(mesh: Mesh) -> Mesh:
    """Flip triangles so that the +Y normal is positive (see :class:`Mesh`)."""
    x = mesh.columns[mesh.triangles].astype(np.int64)
    z = mesh.rows[mesh.triangles].astype(np.int64)
    ux, uz = x[:, 1] - x[:, 0], z[:, 1] - z[:, 0]
    vx, vz = x[:, 2] - x[:, 0], z[:, 2] - z[:, 0]
    flip = (uz * vx - ux * vz) < 0
    triangles = mesh.triangles.copy()
    triangles[flip] = triangles[flip][:, [0, 2, 1]]
    return Mesh(mesh.columns, mesh.rows, triangles)


def build(heights: FloatArray, max_error: float, cut: Box | None = None) -> Mesh:
    """RTIN of a ``2**k + 1`` square lattice with vertical error ``<= max_error`` everywhere."""
    if max_error < 0:
        raise RtinError(f"max_error must be >= 0, got {max_error}")
    return extract(error_map(heights, cut), max_error, cut)


def interpolate(
    mesh: Mesh,
    vertex_heights: FloatArray,
    columns: npt.ArrayLike,
    rows: npt.ArrayLike,
) -> FloatArray:
    """Barycentric height of the mesh at fractional lattice positions (NaN when outside).

    ``vertex_heights`` holds one height per mesh vertex.

    Brute force over all triangles for every query; meant for verification, not for runtime.
    """
    px = np.atleast_1d(np.asarray(columns, dtype=np.float64))
    py = np.atleast_1d(np.asarray(rows, dtype=np.float64))
    corners = mesh.triangles
    vx = mesh.columns.astype(np.float64)
    vy = mesh.rows.astype(np.float64)
    vh = vertex_heights
    ax, bx, cx = (vx[corners[:, k]] for k in range(3))
    ay, by, cy = (vy[corners[:, k]] for k in range(3))
    ha, hb, hc = (vh[corners[:, k]] for k in range(3))
    det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    low_x, high_x = np.minimum(np.minimum(ax, bx), cx), np.maximum(np.maximum(ax, bx), cx)
    low_y, high_y = np.minimum(np.minimum(ay, by), cy), np.maximum(np.maximum(ay, by), cy)
    result = np.full(px.shape, np.nan)
    tolerance = 1e-9
    for q in range(px.size):
        near = np.flatnonzero(
            (low_x <= px[q]) & (high_x >= px[q]) & (low_y <= py[q]) & (high_y >= py[q])
        )
        dx, dy = px[q] - cx[near], py[q] - cy[near]
        w_a = ((by[near] - cy[near]) * dx + (cx[near] - bx[near]) * dy) / det[near]
        w_b = ((cy[near] - ay[near]) * dx + (ax[near] - cx[near]) * dy) / det[near]
        w_c = 1.0 - w_a - w_b
        hit = np.flatnonzero((w_a >= -tolerance) & (w_b >= -tolerance) & (w_c >= -tolerance))
        if hit.size:
            k = near[hit[0]]
            result[q] = w_a[hit[0]] * ha[k] + w_b[hit[0]] * hb[k] + w_c[hit[0]] * hc[k]
    return result
