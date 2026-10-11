"""Tunnel cross-section, interior shell and terrain cutting on synthetic geometry."""

import itertools

import numpy as np
import numpy.typing as npt
import pytest

from penyal_pipeline import tunnel_geometry as geo

WIDTH, HEIGHT = 2.0, 2.6


def straight_axis(length: float = 10.0, rise: float = 0.0, step: float = 0.5) -> npt.NDArray:
    s = np.arange(0.0, length + 1e-9, step)
    return np.column_stack([s, rise * s / length, np.zeros_like(s)])


def bent_axis() -> npt.NDArray:
    """West to east with a 30 degree bend and a sloping floor."""
    corners = np.array([[0.0, 0.0, 0.0], [10.0, 2.0, 0.0], [10.0 + 8.66, 6.0, 5.0]])
    return corners


def triangle_areas(xyz: npt.NDArray, triangles: npt.NDArray) -> npt.NDArray:
    a, b, c = (xyz[triangles[:, k]] for k in range(3))
    return np.linalg.norm(np.cross(b - a, c - a), axis=1) / 2.0


def test_outline_is_a_closed_convex_flattened_arch() -> None:
    outline = geo.polygon_uv(WIDTH, HEIGHT)
    assert outline[0].tolist() == [1.0, 0.0]
    assert outline[-1].tolist() == [-1.0, 0.0]
    assert outline[:, 1].max() == pytest.approx(HEIGHT)
    assert np.abs(outline[:, 0]).max() == pytest.approx(WIDTH / 2.0)
    edges = np.roll(outline, -1, axis=0) - outline
    turns = edges[:-1, 0] * edges[1:, 1] - edges[:-1, 1] * edges[1:, 0]
    assert (turns > -1e-12).all() or (turns < 1e-12).all(), "outline must be convex"
    rise = geo.ARCH_RISE_FRACTION * WIDTH / 2.0
    assert outline[1, 1] == pytest.approx(HEIGHT - rise)


def test_a_section_without_room_for_the_vault_is_rejected() -> None:
    with pytest.raises(geo.GeometryError, match="no room"):
        geo.polygon_uv(2.0, 0.5)


def test_extend_axis_pushes_both_ends_outwards_at_the_end_height() -> None:
    axis = np.array([[0.0, 5.0, 0.0], [3.0, 6.0, 4.0], [3.0, 9.0, 8.0]])
    out = geo.extend_axis(axis, 1.0)
    assert out.shape == (5, 3)
    assert out[0].tolist() == pytest.approx([-0.6, 5.0, -0.8])
    assert out[-1].tolist() == pytest.approx([3.0, 9.0, 9.0])
    assert out[1:-1].tolist() == axis.tolist()


def inward_reference(mesh: geo.ShellMesh, axis: npt.NDArray) -> npt.NDArray:
    """Vector from each shell vertex towards the section centre of its nearest ring."""
    reference = np.empty_like(mesh.positions, dtype=np.float64)
    for n, p in enumerate(mesh.positions.astype(np.float64)):
        ring = int(np.argmin(np.linalg.norm(axis - p, axis=1)))
        reference[n] = axis[ring] + np.array([0.0, HEIGHT / 2.0, 0.0]) - p
    return reference


@pytest.mark.parametrize("axis_factory", [straight_axis, lambda: geo.extend_axis(bent_axis())])
def test_shell_normals_and_winding_face_the_inside(axis_factory) -> None:
    axis = axis_factory()
    mesh = geo.build_shell(axis, WIDTH, HEIGHT)
    positions = mesh.positions.astype(np.float64)
    reference = inward_reference(mesh, axis)
    assert (np.einsum("ij,ij->i", mesh.normals, reference) > 0).all()
    tri = mesh.triangles
    face = np.cross(
        positions[tri[:, 1]] - positions[tri[:, 0]], positions[tri[:, 2]] - positions[tri[:, 0]]
    )
    centroid_ref = reference[tri].mean(axis=1)
    assert (np.einsum("ij,ij->i", face, centroid_ref) > 0).all(), "winding must face inwards"
    vertex_normal = mesh.normals[tri].mean(axis=1)
    assert (np.einsum("ij,ij->i", face, vertex_normal) > 0).all()
    assert np.allclose(np.linalg.norm(mesh.normals, axis=1), 1.0, atol=1e-5)


def test_shell_spans_the_section_and_follows_the_floor() -> None:
    axis = straight_axis(10.0, rise=4.0)
    mesh = geo.build_shell(axis, WIDTH, HEIGHT)
    p = mesh.positions.astype(np.float64)
    assert p[:, 2].min() == pytest.approx(-WIDTH / 2.0)
    assert p[:, 2].max() == pytest.approx(WIDTH / 2.0)
    assert p[:, 0].min() == pytest.approx(0.0)
    assert p[:, 0].max() == pytest.approx(10.0)
    floor = p[mesh.normals[:, 1] > 0.85]
    assert np.allclose(floor[:, 1], 0.4 * floor[:, 0], atol=1e-5)
    crown = p[:, 1] - 0.4 * p[:, 0]
    assert crown.max() == pytest.approx(HEIGHT, abs=1e-5)


def test_shell_is_mitred_at_a_bend_so_walls_keep_their_distance() -> None:
    axis = geo.extend_axis(bent_axis())
    mesh = geo.build_shell(axis, WIDTH, HEIGHT)
    p = mesh.positions.astype(np.float64)
    wall = p[np.abs(mesh.normals[:, 1]) < 1e-3]
    flat = wall[:, [0, 2]]
    line = axis[:, [0, 2]]
    distance = np.array([np.min(_segment_distance(point, line)) for point in flat])
    assert distance.max() <= 1.0 / np.cos(np.radians(15.0)) + 1e-5
    assert distance.min() >= 1.0 - 1e-5


def _segment_distance(point: npt.NDArray, polyline: npt.NDArray) -> npt.NDArray:
    a, b = polyline[:-1], polyline[1:]
    ab = b - a
    t = np.clip(np.einsum("ij,ij->i", point - a, ab) / np.einsum("ij,ij->i", ab, ab), 0.0, 1.0)
    return np.linalg.norm(a + ab * t[:, None] - point, axis=1)


def test_prisms_contain_the_section_and_nothing_else() -> None:
    corners = geo.extend_axis(bent_axis())
    pieces = geo.prisms(corners, WIDTH, HEIGHT)
    assert len(pieces) == 4
    samples = []
    for a, b in itertools.pairwise(corners):
        for t in np.linspace(0.05, 0.95, 7):
            centre = a + (b - a) * t
            samples.append(centre + np.array([0.0, 1.2, 0.0]))
            samples.append(centre + np.array([0.0, 0.15, 0.0]))
    inside = np.array(samples)
    assert any(piece.contains(inside).any() for piece in pieces)
    covered = np.zeros(len(inside), dtype=bool)
    for piece in pieces:
        covered |= piece.contains(inside)
    assert covered.all()
    outside = np.array(
        [c + np.array([0.0, HEIGHT + 0.3, 0.0]) for c in corners[1:-1]]
        + [corners[0] - np.array([3.0, 0.0, 0.0])]
    )
    assert not any(piece.contains(outside).any() for piece in pieces)
    sideways = np.array([corners[1] + [0.0, 1.0, 1.4], corners[2] + [0.0, 1.0, -1.4]])
    assert not any(piece.contains(sideways).any() for piece in pieces)


def flat_terrain(
    height: float, extent: float = 12.0, cells: int = 24
) -> tuple[npt.NDArray, npt.NDArray]:
    axis = np.linspace(-extent, extent, cells + 1)
    gx, gz = np.meshgrid(axis, axis)
    xyz = np.column_stack([gx.ravel(), np.full(gx.size, height), gz.ravel()])
    n = cells + 1
    tris = []
    for r in range(cells):
        for c in range(cells):
            a = r * n + c
            tris += [(a, a + n, a + 1), (a + 1, a + n, a + n + 1)]  # counter-clockwise from +y
    return xyz, np.array(tris, dtype=np.int64)


def test_cut_openings_removes_exactly_the_volume_footprint() -> None:
    xyz, triangles = flat_terrain(1.0)
    run = geo.prisms(np.array([[-5.0, 0.0, 0.3], [6.0, 0.0, 0.3]]), WIDTH, HEIGHT)
    new_xyz, new_triangles = geo.cut_openings(xyz, triangles, run)
    before = triangle_areas(xyz, triangles).sum()
    after = triangle_areas(new_xyz, new_triangles).sum()
    assert before - after == pytest.approx(11.0 * WIDTH, abs=1e-6)
    assert (
        np.cross(
            new_xyz[new_triangles[:, 1]] - new_xyz[new_triangles[:, 0]],
            new_xyz[new_triangles[:, 2]] - new_xyz[new_triangles[:, 0]],
        )[:, 1]
        > 0
    ).all(), "winding is preserved"
    centroids = new_xyz[new_triangles].mean(axis=1)
    assert not run[0].contains(centroids).any()
    assert np.unique(new_triangles).size == new_xyz.shape[0], "no unreferenced vertices"


def test_cut_openings_leaves_untouched_triangles_and_is_deterministic() -> None:
    xyz, triangles = flat_terrain(1.0)
    run = geo.prisms(np.array([[-5.0, 0.0, 0.3], [6.0, 0.0, 0.3]]), WIDTH, HEIGHT)
    first = geo.cut_openings(xyz, triangles, run)
    second = geo.cut_openings(xyz, triangles, run)
    assert np.array_equal(first[0], second[0])
    assert np.array_equal(first[1], second[1])
    far = xyz[:, 2] > 4.0
    far_triangles = far[triangles].all(axis=1)
    kept = {tuple(map(tuple, xyz[t])) for t in triangles[far_triangles]}
    remaining = {tuple(map(tuple, first[0][t])) for t in first[1]}
    assert kept <= remaining


def test_surface_above_the_vault_is_kept() -> None:
    xyz, triangles = flat_terrain(5.0)
    run = geo.prisms(np.array([[-5.0, 0.0, 0.0], [6.0, 0.0, 0.0]]), WIDTH, HEIGHT)
    new_xyz, new_triangles = geo.cut_openings(xyz, triangles, run)
    assert new_triangles.shape == triangles.shape
    assert triangle_areas(new_xyz, new_triangles).sum() == pytest.approx(
        triangle_areas(xyz, triangles).sum()
    )


def test_split_points_on_shared_edges_are_welded() -> None:
    xyz, triangles = flat_terrain(1.0)
    run = geo.prisms(np.array([[-5.0, 0.0, 0.3], [6.0, 0.0, 0.3]]), WIDTH, HEIGHT)
    new_xyz, _ = geo.cut_openings(xyz, triangles, run)
    rounded = {tuple(np.round(p, 9)) for p in new_xyz}
    assert len(rounded) == new_xyz.shape[0], "no duplicate vertices"


def ramp(x: npt.NDArray, z: npt.NDArray) -> npt.NDArray:
    """Terrain that falls from 4 m at x = 0 to 0 m at x = 10."""
    return 4.0 - 0.4 * x + 0.0 * z


def test_clip_removes_the_walls_and_vault_above_the_terrain_and_keeps_the_floor() -> None:
    shell = geo.build_shell(straight_axis(10.0), WIDTH, HEIGHT)
    clipped = geo.clip_shell_to_surface(shell, ramp, skin=0.25)
    wall = clipped.normals[:, 1] < geo.FLOOR_NORMAL_Y
    p = clipped.positions.astype(np.float64)
    assert (p[wall, 1] <= ramp(p[wall, 0], p[wall, 2]) - 0.25 + 1e-5).all()
    floor = shell.normals[:, 1] >= geo.FLOOR_NORMAL_Y
    assert (clipped.normals[:, 1] >= geo.FLOOR_NORMAL_Y).sum() == floor.sum()
    assert np.allclose(np.linalg.norm(clipped.normals, axis=1), 1.0, atol=1e-5)
    assert clipped.triangles.max() < len(clipped.positions)
    assert len(clipped.triangles) < len(shell.triangles)


def test_clip_leaves_a_shell_that_is_wholly_under_the_terrain_untouched() -> None:
    shell = geo.build_shell(straight_axis(10.0), WIDTH, HEIGHT)
    clipped = geo.clip_shell_to_surface(shell, lambda x, z: np.full_like(x, 50.0), skin=0.25)
    assert clipped.positions.tolist() == shell.positions.tolist()
    assert clipped.triangles.tolist() == shell.triangles.tolist()


def test_clip_is_deterministic_and_welds_shared_edges() -> None:
    shell = geo.build_shell(straight_axis(10.0), WIDTH, HEIGHT)
    first = geo.clip_shell_to_surface(shell, ramp, skin=0.25)
    second = geo.clip_shell_to_surface(shell, ramp, skin=0.25)
    assert first.positions.tolist() == second.positions.tolist()
    assert first.triangles.tolist() == second.triangles.tolist()

    def duplicates(mesh: geo.ShellMesh) -> int:
        return len(mesh.positions) - len({tuple(p) for p in mesh.positions.tolist()})

    assert duplicates(first) <= duplicates(shell), "cut-line vertices are shared by neighbours"
