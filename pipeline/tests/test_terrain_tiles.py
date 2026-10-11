"""Terrain tiles on the real DEM: geometric accuracy, the summit, and byte-identical re-runs.

Needs ``build/terrain/dem.f32`` (``penyal dem``) and the orthophoto (``penyal fetch``).
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest
from conftest import raw_marks

from penyal_pipeline import dem, rtin, tiles, tunnel
from penyal_pipeline.paths import REPO_ROOT, TERRAIN_BUILD_DIR

POINTS_PER_LOD = 2000
LOD_LIMITS = {0: 0.5, 1: 2.0, 2: 6.0}  # plan: max error vs the DEM per LOD
DEM_READY = (TERRAIN_BUILD_DIR / "dem.f32").is_file() and (TERRAIN_BUILD_DIR / "dem.json").is_file()
needs_dem = pytest.mark.skipif(
    not DEM_READY, reason="build/terrain/dem.f32 missing; run `penyal dem`"
)
needs_optimizer = pytest.mark.skipif(
    shutil.which("node") is None
    or not (REPO_ROOT / "tools" / "bin" / "ktx").exists()
    or not (REPO_ROOT / "node_modules" / ".bin" / "gltf-transform").exists(),
    reason="node, tools/bin/ktx and `pnpm install` are needed to optimise GLBs",
)


pytestmark = [*raw_marks("icv-orto-2024-0848-7-2/*.tif"), needs_dem]


@pytest.fixture(scope="module")
def grid() -> dem.Grid:
    return dem.load_dem()[0]


def random_points(count: int, seed: int) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    rng = np.random.default_rng(seed)
    x = rng.uniform(tiles.NEAR_X_MIN, tiles.NEAR_X_MAX, count)
    z = rng.uniform(tiles.NEAR_Z_MIN, tiles.NEAR_Z_MAX, count)
    return x, z


def tile_of(x: npt.NDArray[np.float64], z: npt.NDArray[np.float64]) -> list[tiles.TileKey]:
    i = np.clip(np.floor((x + 0.5) / tiles.NEAR_TILE_SIZE).astype(int), 1, 4)
    j = np.clip(np.floor((z + 0.5) / tiles.NEAR_TILE_SIZE).astype(int), -5, -2)
    return list(zip(i.tolist(), j.tolist(), strict=True))


def surface_rtin(
    mesh: tiles.TerrainMesh, x_min: float, z_min: float
) -> tuple[rtin.Mesh, npt.NDArray[np.float64]]:
    """The exported surface triangles as a lattice mesh plus the exported vertex heights."""
    vertices = mesh.positions[: mesh.surface_vertices].astype(np.float64)
    lattice = rtin.Mesh(
        columns=np.rint(vertices[:, 0] - x_min).astype(np.int64),
        rows=np.rint(vertices[:, 2] - z_min).astype(np.int64),
        triangles=mesh.triangles[: mesh.surface_triangles],
    )
    return lattice, vertices[:, 1]


@pytest.fixture(scope="module")
def sampled(
    grid: dem.Grid,
) -> tuple[
    npt.NDArray[np.float64],
    dict[int, npt.NDArray[np.float64]],
    npt.NDArray[np.float64],
]:
    """Heights at random points: DEM bilinear, the full-resolution mesh, and each LOD."""
    x, z = random_points(POINTS_PER_LOD, seed=2026)
    owners = tile_of(x, z)
    reference = np.full(x.shape, np.nan)
    by_lod = {level: np.full(x.shape, np.nan) for level in LOD_LIMITS}
    for key in sorted(set(owners)):
        i, j = key
        chosen = np.flatnonzero([owner == key for owner in owners])
        heights, x_min, z_min = tiles.tile_lattice(grid, i, j)
        full = rtin.build(heights, 0.0)
        reference[chosen] = rtin.interpolate(
            full, heights[full.rows, full.columns], x[chosen] - x_min, z[chosen] - z_min
        )
        for lod in tiles.LODS:
            lattice, vertex_heights = surface_rtin(tiles.build_tile(grid, i, j, lod), x_min, z_min)
            by_lod[lod.level][chosen] = rtin.interpolate(
                lattice, vertex_heights, x[chosen] - x_min, z[chosen] - z_min
            )
    return grid.sample(x, z), by_lod, reference


@pytest.mark.parametrize("lod", tiles.LODS, ids=lambda lod: f"lod{lod.level}")
def test_mesh_stays_within_the_lod_error_of_the_dem_surface(
    sampled: tuple[
        npt.NDArray[np.float64], dict[int, npt.NDArray[np.float64]], npt.NDArray[np.float64]
    ],
    lod: tiles.Lod,
) -> None:
    _, by_lod, reference = sampled
    assert not np.isnan(by_lod[lod.level]).any(), "every point lies inside a tile mesh"
    error = np.abs(by_lod[lod.level] - reference)
    assert error.max() <= lod.max_error + 1e-6
    assert lod.max_error <= LOD_LIMITS[lod.level]


@pytest.mark.parametrize("lod", tiles.LODS, ids=lambda lod: f"lod{lod.level}")
def test_mesh_matches_the_bilinear_dem_at_the_99th_percentile(
    sampled: tuple[
        npt.NDArray[np.float64], dict[int, npt.NDArray[np.float64]], npt.NDArray[np.float64]
    ],
    lod: tiles.Lod,
) -> None:
    """Against the bilinear DEM the maximum is dominated by cliff cells: no triangulation of
    the 1 m samples reproduces the bilinear twist there (the full-resolution mesh itself is
    up to ~2.3 m off at some points), so the contract is the 99th percentile."""
    bilinear, by_lod, _ = sampled
    error = np.abs(by_lod[lod.level] - bilinear)
    assert np.percentile(error, 99) <= LOD_LIMITS[lod.level]


def test_every_dem_sample_is_within_the_lod_error(grid: dem.Grid) -> None:
    heights, x_min, z_min = tiles.tile_lattice(grid, 2, -4)
    for lod in tiles.LODS:
        lattice, vertex_heights = surface_rtin(tiles.build_tile(grid, 2, -4, lod), x_min, z_min)
        columns, rows = np.meshgrid(np.arange(257.0), np.arange(257.0))
        got = rtin.interpolate(lattice, vertex_heights, columns.ravel(), rows.ravel())
        assert np.abs(got - heights.ravel()).max() <= lod.max_error + 1e-6


def test_summit_cell_is_present_in_lod0(grid: dem.Grid) -> None:
    summit = dem.summit_cells(grid)
    i = int(np.floor((summit["x"] + 0.5) / tiles.NEAR_TILE_SIZE))
    j = int(np.floor((summit["z"] + 0.5) / tiles.NEAR_TILE_SIZE))
    mesh = tiles.build_tile(grid, i, j, tiles.LODS[0])
    assert mesh.max_y == pytest.approx(summit["height"], abs=0.5)
    assert float(grid.heights.max()) == pytest.approx(summit["height"], abs=1e-3)


def test_the_trail_corridor_sits_well_inside_the_near_box() -> None:
    margin = tiles.check_corridor()
    assert margin is not None
    assert margin >= tiles.CORRIDOR_MARGIN


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): sha256(p) for p in sorted(root.rglob("*")) if p.is_file()}


@needs_optimizer
@pytest.mark.slow
def test_rerun_with_another_hash_seed_is_byte_identical(tmp_path: Path) -> None:
    pair = [(2, -4), (1, -3)]
    first = tmp_path / "first"
    # `penyal terrain` always applies the tunnel features, so the in-process run does too.
    tiles.run_terrain(
        out_dir=first / "out",
        build_dir=first / "glb",
        tiles=pair,
        include_far=False,
        features=tunnel.load_terrain_features(),
    )
    second = tmp_path / "second"
    env = {**os.environ, "PYTHONHASHSEED": "4242"}
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "penyal_pipeline.cli",
            "terrain",
            "--tile",
            "t_2_-4",
            "t_1_-3",
            "--no-far",
            "--out-dir",
            str(second / "out"),
            "--build-dir",
            str(second / "glb"),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0, run.stderr
    assert hashes(first / "glb") == hashes(second / "glb"), "unoptimised GLBs differ"
    assert hashes(first / "out") == hashes(second / "out"), "optimised GLBs or manifest differ"
    names = sorted(hashes(first / "out"))
    assert "manifest.json" in names
    assert len([n for n in names if n.endswith(".glb")]) == 6
    manifest = json.loads((first / "out" / "manifest.json").read_text(encoding="utf-8"))
    for tile in manifest["near"]["tiles"]:
        for lod in tile["lods"]:
            assert (first / "out" / lod["url"]).stat().st_size == lod["bytes"]
            assert lod["triangles"] > 0
