"""RTIN: error bound, conformity, winding, determinism and box cut-outs."""

from collections import Counter

import numpy as np
import numpy.typing as npt
import pytest

from penyal_pipeline import rtin

type Heights = npt.NDArray[np.float64]


def lattice(count: int) -> tuple[Heights, Heights]:
    x, y = np.meshgrid(np.arange(count, dtype=np.float64), np.arange(count, dtype=np.float64))
    return x, y


def smooth_surface(count: int) -> Heights:
    x, y = lattice(count)
    return 6.0 * np.sin(x / 5.0) * np.cos(y / 7.0) + 0.05 * x


def cliff_surface(count: int) -> Heights:
    x, y = lattice(count)
    return np.where(x + 0.5 * y > count * 0.7, 30.0, 0.0) + 0.1 * y


def noisy_surface(count: int) -> Heights:
    rng = np.random.default_rng(7)
    return rng.normal(0.0, 1.5, (count, count)) + smooth_surface(count)


SURFACES = {"smooth": smooth_surface, "cliff": cliff_surface, "noisy": noisy_surface}


def max_lattice_error(mesh: rtin.Mesh, heights: Heights) -> float:
    x, y = lattice(heights.shape[0])
    got = rtin.interpolate(mesh, heights[mesh.rows, mesh.columns], x.ravel(), y.ravel()).reshape(
        heights.shape
    )
    assert not np.isnan(got).any(), "every lattice point must lie inside the mesh"
    return float(np.abs(got - heights).max())


def signed_areas(mesh: rtin.Mesh) -> Heights:
    x = mesh.columns[mesh.triangles].astype(np.float64)
    z = mesh.rows[mesh.triangles].astype(np.float64)
    return (
        (z[:, 1] - z[:, 0]) * (x[:, 2] - x[:, 0]) - (x[:, 1] - x[:, 0]) * (z[:, 2] - z[:, 0])
    ) / 2


def test_flat_lattice_is_two_triangles() -> None:
    mesh = rtin.build(np.full((257, 257), 12.5), 0.25)
    assert mesh.triangles.shape == (2, 3)
    assert set(zip(mesh.columns.tolist(), mesh.rows.tolist(), strict=True)) == {
        (0, 0),
        (256, 0),
        (0, 256),
        (256, 256),
    }


def test_tilted_plane_is_still_two_triangles() -> None:
    x, y = lattice(65)
    assert rtin.build(0.3 * x - 0.1 * y, 0.01).triangles.shape[0] == 2


@pytest.mark.parametrize("name", sorted(SURFACES))
@pytest.mark.parametrize("tolerance", [0.0, 0.25, 1.0, 3.0])
@pytest.mark.parametrize("count", [17, 33, 65])
def test_every_lattice_point_is_within_the_tolerance(
    name: str, tolerance: float, count: int
) -> None:
    heights = SURFACES[name](count)
    mesh = rtin.build(heights, tolerance)
    assert max_lattice_error(mesh, heights) <= tolerance + 1e-9


def test_coarser_tolerance_never_adds_triangles() -> None:
    heights = noisy_surface(65)
    counts = [rtin.build(heights, eps).triangles.shape[0] for eps in (0.0, 0.5, 2.0, 8.0)]
    assert counts == sorted(counts, reverse=True)
    assert counts[0] > counts[-1]


@pytest.mark.parametrize("name", sorted(SURFACES))
def test_mesh_is_a_conforming_ccw_tiling_of_the_lattice(name: str) -> None:
    count = 65
    mesh = rtin.build(SURFACES[name](count), 0.5)
    assert (signed_areas(mesh) > 0).all()
    assert signed_areas(mesh).sum() == pytest.approx((count - 1) ** 2)
    edges: Counter[tuple[int, int]] = Counter()
    for tri in mesh.triangles:
        for k in range(3):
            u, v = int(tri[k]), int(tri[(k + 1) % 3])
            edges[(min(u, v), max(u, v))] += 1
    last = count - 1
    for (u, v), uses in edges.items():
        on_border = any(
            (mesh.columns[u] == mesh.columns[v] == edge) or (mesh.rows[u] == mesh.rows[v] == edge)
            for edge in (0, last)
        )
        assert uses == (1 if on_border else 2), "T-junction or open edge inside the lattice"


def test_output_is_deterministic() -> None:
    heights = noisy_surface(65)
    first = rtin.build(heights, 0.7)
    second = rtin.build(heights.copy(), 0.7)
    assert np.array_equal(first.triangles, second.triangles)
    assert np.array_equal(first.columns, second.columns)
    assert np.array_equal(first.rows, second.rows)


@pytest.mark.parametrize("count", [1, 2, 4, 100, 258])
def test_lattice_size_must_be_power_of_two_plus_one(count: int) -> None:
    with pytest.raises(rtin.RtinError):
        rtin.build(np.zeros((count, count)), 1.0)


def test_non_square_and_negative_tolerance_are_rejected() -> None:
    with pytest.raises(rtin.RtinError):
        rtin.build(np.zeros((17, 33)), 1.0)
    with pytest.raises(rtin.RtinError):
        rtin.build(np.zeros((17, 17)), -1.0)


def test_cut_box_is_removed_exactly_and_the_rest_stays_within_tolerance() -> None:
    count = 129
    heights = smooth_surface(count)
    box = rtin.Box(col0=32, row0=32, col1=96, row1=96)
    mesh = rtin.build(heights, 0.5, box)
    area = signed_areas(mesh)
    assert area.sum() == pytest.approx((count - 1) ** 2 - 64 * 64)
    x = mesh.columns[mesh.triangles].astype(np.float64).mean(axis=1)
    z = mesh.rows[mesh.triangles].astype(np.float64).mean(axis=1)
    assert not ((x > 32) & (x < 96) & (z > 32) & (z < 96)).any()
    outside = np.ones(heights.shape, dtype=bool)
    outside[33:96, 33:96] = False
    xs, ys = lattice(count)
    got = rtin.interpolate(mesh, heights[mesh.rows, mesh.columns], xs[outside], ys[outside])
    assert not np.isnan(got).any()
    assert np.abs(got - heights[outside]).max() <= 0.5 + 1e-9


def test_interpolate_reports_nan_outside_the_mesh() -> None:
    mesh = rtin.build(np.zeros((17, 17)), 0.1)
    assert np.isnan(rtin.interpolate(mesh, np.zeros(mesh.columns.size), [20.0], [3.0])).all()
