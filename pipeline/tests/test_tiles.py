"""Tile and far-mesh geometry on a synthetic DEM with the real grid geometry (no data needed)."""

import numpy as np
import numpy.typing as npt
import pytest

from penyal_pipeline import tiles
from penyal_pipeline.dem import Grid
from penyal_pipeline.ortho import LocalRect

WIDTH, HEIGHT = 2600, 2550
X0, Z0 = -599.5, -1999.5


def analytic_height(
    x: npt.NDArray[np.float64], z: npt.NDArray[np.float64]
) -> npt.NDArray[np.float64]:
    hill = 120.0 * np.exp(-((x - 700.0) ** 2 + (z + 700.0) ** 2) / (2 * 150.0**2))
    return hill + 4.0 * np.sin(x / 31.0) * np.cos(z / 23.0)


@pytest.fixture(scope="module")
def grid() -> Grid:
    xs = X0 + np.arange(WIDTH, dtype=np.float64)
    zs = Z0 + np.arange(HEIGHT, dtype=np.float64)
    heights = analytic_height(xs[None, :], zs[:, None]).astype(np.float32)
    return Grid(heights, x0=X0, z0=Z0)


@pytest.fixture(scope="module")
def far(grid: Grid) -> tiles.TerrainMesh:
    return tiles.build_far(grid)


def surface_xz(mesh: tiles.TerrainMesh) -> npt.NDArray[np.float32]:
    return mesh.positions[: mesh.surface_vertices][:, [0, 2]]


def facing_up(mesh: tiles.TerrainMesh, triangles: npt.NDArray[np.int32]) -> npt.NDArray[np.bool_]:
    p = mesh.positions.astype(np.float64)
    u = p[triangles[:, 1]] - p[triangles[:, 0]]
    v = p[triangles[:, 2]] - p[triangles[:, 0]]
    return (u[:, 2] * v[:, 0] - u[:, 0] * v[:, 2]) > 0


def test_near_box_matches_the_plan() -> None:
    assert tiles.near_tiles()[0] == (1, -5)
    assert tiles.near_tiles()[-1] == (4, -2)
    assert len(tiles.near_tiles()) == 16
    assert (tiles.NEAR_X_MIN, tiles.NEAR_X_MAX) == (255.5, 1279.5)
    assert (tiles.NEAR_Z_MIN, tiles.NEAR_Z_MAX) == (-1280.5, -256.5)


@pytest.mark.parametrize("text", ["t_1_-3", "t_4_-2", "t_1_-5"])
def test_tile_ids_round_trip(text: str) -> None:
    i, j = tiles.parse_tile_id(text)
    assert tiles.tile_id(i, j) == text


@pytest.mark.parametrize("text", ["t_0_-3", "t_5_-3", "t_1_-6", "t_1_-1", "tile", "t_1", "1_2"])
def test_tile_ids_outside_the_near_box_are_rejected(text: str) -> None:
    with pytest.raises(tiles.TerrainError):
        tiles.parse_tile_id(text)


@pytest.mark.parametrize("lod", tiles.LODS, ids=lambda lod: f"lod{lod.level}")
def test_tile_surface_is_a_ccw_tiling_of_the_tile(grid: Grid, lod: tiles.Lod) -> None:
    mesh = tiles.build_tile(grid, 2, -3, lod)
    x_min, z_min = 2 * 256 - 0.5, -3 * 256 - 0.5
    xz = surface_xz(mesh)
    assert xz[:, 0].min() == x_min
    assert xz[:, 0].max() == x_min + 256
    assert xz[:, 1].min() == z_min
    assert xz[:, 1].max() == z_min + 256
    surface = mesh.triangles[: mesh.surface_triangles]
    assert facing_up(mesh, surface).all()
    p = mesh.positions.astype(np.float64)
    twice_area = (p[surface[:, 1], 2] - p[surface[:, 0], 2]) * (
        p[surface[:, 2], 0] - p[surface[:, 0], 0]
    ) - (p[surface[:, 1], 0] - p[surface[:, 0], 0]) * (p[surface[:, 2], 2] - p[surface[:, 0], 2])
    assert twice_area.sum() / 2 == pytest.approx(256.0**2)


def test_lods_get_coarser(grid: Grid) -> None:
    counts = [tiles.build_tile(grid, 2, -3, lod).triangle_count for lod in tiles.LODS]
    assert counts[0] > counts[1] > counts[2] > 0


def test_normals_follow_the_dem_gradient_and_match_across_lods(grid: Grid) -> None:
    fine = tiles.build_tile(grid, 2, -3, tiles.LODS[0])
    coarse = tiles.build_tile(grid, 2, -3, tiles.LODS[2])
    fine_normals = {
        (float(p[0]), float(p[2])): n
        for p, n in zip(
            fine.positions[: fine.surface_vertices],
            fine.normals[: fine.surface_vertices],
            strict=True,
        )
    }
    shared = 0
    for p, n in zip(
        coarse.positions[: coarse.surface_vertices],
        coarse.normals[: coarse.surface_vertices],
        strict=True,
    ):
        match = fine_normals.get((float(p[0]), float(p[2])))
        if match is not None:
            shared += 1
            assert np.array_equal(match, n)
    assert shared == coarse.surface_vertices, "every coarse vertex is also a fine vertex"

    h = grid.heights.astype(np.float64)
    interior = [
        k
        for k in range(fine.surface_vertices)
        if 2 * 256 < fine.positions[k, 0] < 3 * 256 - 1
        and -3 * 256 < fine.positions[k, 2] < -2 * 256 - 1
    ]
    assert interior, "the test tile has interior vertices"
    for k in interior[:20]:
        c, r = round(float(fine.positions[k, 0]) - X0), round(float(fine.positions[k, 2]) - Z0)
        expected = np.array(
            [-(h[r, c + 1] - h[r, c - 1]) / 2, 1.0, -(h[r + 1, c] - h[r - 1, c]) / 2]
        )
        expected /= np.linalg.norm(expected)
        assert np.allclose(fine.normals[k], expected, atol=1e-6)
    assert np.linalg.norm(fine.normals, axis=1) == pytest.approx(1.0, abs=1e-5)


@pytest.mark.parametrize("lod", tiles.LODS, ids=lambda lod: f"lod{lod.level}")
def test_skirts_hang_below_the_border_and_face_outwards(grid: Grid, lod: tiles.Lod) -> None:
    mesh = tiles.build_tile(grid, 2, -3, lod)
    skirt_vertices = mesh.positions[mesh.surface_vertices :]
    assert skirt_vertices.shape[0] > 0
    centre = np.array([2 * 256 - 0.5 + 128, -3 * 256 - 0.5 + 128])
    border = np.max(np.abs(skirt_vertices[:, [0, 2]] - centre), axis=1)
    assert np.all(border == 128), "skirt vertices lie on the tile border"
    copied = mesh.positions[: mesh.surface_vertices]
    top = {(float(p[0]), float(p[2])): float(p[1]) for p in copied}
    for p in skirt_vertices:
        assert p[1] == pytest.approx(np.float32(top[(float(p[0]), float(p[2]))] - lod.skirt))
    p = mesh.positions.astype(np.float64)
    strips = mesh.triangles[mesh.surface_triangles :]
    normal = np.cross(p[strips[:, 1]] - p[strips[:, 0]], p[strips[:, 2]] - p[strips[:, 0]])
    assert np.allclose(normal[:, 1], 0.0), "skirt strips are vertical"
    outward = p[strips[:, 0]][:, [0, 2]] - centre
    assert (np.einsum("ij,ij->i", normal[:, [0, 2]], outward) > 0).all()
    # normals and UVs of skirt vertices copy their top vertices
    lowered = mesh.normals[mesh.surface_vertices :]
    assert np.linalg.norm(lowered, axis=1) == pytest.approx(1.0, abs=1e-5)


def test_uv_maps_tile_bounds_with_north_at_v_zero(grid: Grid) -> None:
    mesh = tiles.build_tile(grid, 1, -3, tiles.LODS[2])
    x_min, z_min = 256 - 0.5, -3 * 256 - 0.5
    corners = {
        (x_min, z_min): (0.0, 0.0),  # north-west
        (x_min + 256, z_min): (1.0, 0.0),  # north-east
        (x_min, z_min + 256): (0.0, 1.0),  # south-west
        (x_min + 256, z_min + 256): (1.0, 1.0),  # south-east
    }
    for k in range(mesh.surface_vertices):
        key = (float(mesh.positions[k, 0]), float(mesh.positions[k, 2]))
        if key in corners:
            assert tuple(mesh.uvs[k]) == corners.pop(key)
    assert not corners, "all four tile corners are vertices"
    assert mesh.uvs.min() >= 0.0
    assert mesh.uvs.max() <= 1.0


def test_neighbouring_tiles_agree_along_their_shared_border(grid: Grid) -> None:
    west = tiles.build_tile(grid, 2, -3, tiles.LODS[0])
    east = tiles.build_tile(grid, 3, -3, tiles.LODS[0])
    border_x = np.float32(3 * 256 - 0.5)

    def border_heights(mesh: tiles.TerrainMesh) -> dict[float, float]:
        surface = mesh.positions[: mesh.surface_vertices]
        sel = surface[:, 0] == border_x
        return {float(p[2]): float(p[1]) for p in surface[sel]}

    shared = border_heights(west).keys() & border_heights(east).keys()
    assert len(shared) > 2
    for z in shared:
        assert border_heights(west)[z] == border_heights(east)[z]


def test_far_mesh_covers_the_dem_extent_minus_the_near_box(far: tiles.TerrainMesh) -> None:
    surface = far.triangles[: far.surface_triangles]
    p = far.positions.astype(np.float64)
    xs, zs = p[surface][:, :, 0], p[surface][:, :, 2]
    twice_area = (zs[:, 1] - zs[:, 0]) * (xs[:, 2] - xs[:, 0]) - (xs[:, 1] - xs[:, 0]) * (
        zs[:, 2] - zs[:, 0]
    )
    assert (twice_area > 0).all(), "counter-clockwise from above"
    extent = (WIDTH - 1) * (HEIGHT - 1)
    near_box = (tiles.NEAR_X_MAX - tiles.NEAR_X_MIN) * (tiles.NEAR_Z_MAX - tiles.NEAR_Z_MIN)
    assert twice_area.sum() / 2 == pytest.approx(extent - near_box, rel=1e-9)
    centre_x, centre_z = xs.mean(axis=1), zs.mean(axis=1)
    in_box = (
        (centre_x > tiles.NEAR_X_MIN)
        & (centre_x < tiles.NEAR_X_MAX)
        & (centre_z > tiles.NEAR_Z_MIN)
        & (centre_z < tiles.NEAR_Z_MAX)
    )
    assert not in_box.any()
    assert xs.min() == X0
    assert xs.max() == X0 + WIDTH - 1
    assert zs.min() == Z0
    assert zs.max() == Z0 + HEIGHT - 1


def test_far_mesh_is_welded_and_has_skirts_only_along_the_hole(far: tiles.TerrainMesh) -> None:
    surface = far.positions[: far.surface_vertices][:, [0, 2]]
    assert np.unique(surface, axis=0).shape[0] == far.surface_vertices
    skirt = far.positions[far.surface_vertices :]
    assert skirt.shape[0] > 0
    x, z = skirt[:, 0], skirt[:, 2]
    on_box = (
        ((x == tiles.NEAR_X_MIN) | (x == tiles.NEAR_X_MAX))
        & (z >= tiles.NEAR_Z_MIN)
        & (z <= tiles.NEAR_Z_MAX)
    ) | (
        ((z == tiles.NEAR_Z_MIN) | (z == tiles.NEAR_Z_MAX))
        & (x >= tiles.NEAR_X_MIN)
        & (x <= tiles.NEAR_X_MAX)
    )
    assert on_box.all()
    p = far.positions.astype(np.float64)
    strips = far.triangles[far.surface_triangles :]
    normal = np.cross(p[strips[:, 1]] - p[strips[:, 0]], p[strips[:, 2]] - p[strips[:, 0]])
    inward_of_hole = np.array([(tiles.NEAR_X_MIN + tiles.NEAR_X_MAX) / 2, 0.0, 0.0])
    inward_of_hole[2] = (tiles.NEAR_Z_MIN + tiles.NEAR_Z_MAX) / 2
    towards_hole = inward_of_hole[[0, 2]] - p[strips[:, 0]][:, [0, 2]]
    assert (np.einsum("ij,ij->i", normal[:, [0, 2]], towards_hole) > 0).all(), (
        "far skirts face the hole, away from the far surface"
    )


def test_far_mesh_uvs_span_the_extent(far: tiles.TerrainMesh) -> None:
    assert far.extent == LocalRect(X0, Z0, X0 + WIDTH - 1, Z0 + HEIGHT - 1)
    assert far.uvs.min() == 0.0
    assert far.uvs.max() == 1.0


def test_clip_to_rect_keeps_area_and_welds_cut_points() -> None:
    xyz = np.array(
        [[-2.0, 0.0, -2.0], [6.0, 8.0, -2.0], [-2.0, 4.0, 6.0], [6.0, 2.0, 6.0]], dtype=np.float64
    )
    triangles = np.array([[0, 2, 1], [1, 2, 3]], dtype=np.int64)
    out_xyz, out_tris = tiles.clip_to_rect(xyz, triangles, LocalRect(0.0, 0.0, 4.0, 4.0))
    x, z = out_xyz[out_tris][:, :, 0], out_xyz[out_tris][:, :, 2]
    area = (
        (z[:, 1] - z[:, 0]) * (x[:, 2] - x[:, 0]) - (x[:, 1] - x[:, 0]) * (z[:, 2] - z[:, 0])
    ) / 2
    assert area.sum() == pytest.approx(16.0)
    assert np.unique(out_xyz[:, [0, 2]], axis=0).shape[0] == out_xyz.shape[0]
    assert out_xyz[:, 0].min() == 0.0
    assert out_xyz[:, 0].max() == 4.0
    # heights are interpolated on the cut: plane through (-2,-2,0), (-2,6,4), (6,-2,8) at (0, 0)
    corner = out_xyz[(out_xyz[:, 0] == 0.0) & (out_xyz[:, 2] == 0.0)]
    assert corner.shape[0] == 1
    assert corner[0, 1] == pytest.approx(3.0)


def test_corridor_margin_is_the_smallest_distance_to_the_box_border() -> None:
    inside = [[500.0, -800.0], [700.0, -600.0]]
    assert tiles.corridor_margin(inside) == pytest.approx(500.0 - tiles.NEAR_X_MIN)
    assert tiles.corridor_margin([[100.0, -800.0]]) < 0


def test_start_area_bytes_counts_far_every_lod2_and_close_fine_lods() -> None:
    def tile(i: int, j: int, sizes: tuple[int, int, int]) -> dict[str, object]:
        x, z = 256 * i, 256 * j
        return {
            "id": tiles.tile_id(i, j),
            "bounds": {"minX": x, "maxX": x + 256, "minZ": z, "maxZ": z + 256},
            "lods": [{"level": k, "bytes": size} for k, size in enumerate(sizes)],
        }

    manifest = {
        "far": {"bytes": 1000},
        "near": {"tiles": [tile(2, -4, (100, 10, 1)), tile(4, -2, (200, 20, 2))]},
    }
    got = tiles.start_area_bytes(manifest, anchor=(549.0, -1024.0), radius=300.0)
    assert got == {"far": 1000, "lod2": 3, "nearLod0Lod1": 110, "total": 1113}
