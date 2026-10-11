"""T1.8a: curated tunnel data, evidence, tunnel.json, terrain carve and portal openings."""

import hashlib
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import numpy.typing as npt
import pytest
from conftest import build_marks, raw_marks
from test_terrain_export import accessor, read_glb

from penyal_pipeline import dem, tiles, trail, tunnel, tunnel_geometry
from penyal_pipeline.dem import Grid
from penyal_pipeline.paths import REPO_ROOT, TERRAIN_BUILD_DIR, TUNNEL_CURATED
from penyal_pipeline.rawdata import locate
from penyal_pipeline.tunnel import Analysis, Curated, LidarPoints, TunnelError

type Doc = dict[str, Any]
type Floats = npt.NDArray[np.float64]

OSM_FILE = "osm-penyal/osm-penyal.json"
LIDAR_FILES = (
    "icv-lidar-2016-766-4280/*.laz",
    "icv-lidar-2016-766-4282/*.laz",
    "icv-lidar-2016-768-4280/*.laz",
    "icv-lidar-2016-768-4282/*.laz",
)
needs_dem = build_marks(TERRAIN_BUILD_DIR / "dem.f32", TERRAIN_BUILD_DIR / "dem.json")
needs_optimizer = pytest.mark.skipif(
    shutil.which("node") is None
    or not (REPO_ROOT / "tools" / "bin" / "ktx").exists()
    or not (REPO_ROOT / "node_modules" / ".bin" / "gltf-transform").exists(),
    reason="node, tools/bin/ktx and `pnpm install` are needed to optimise GLBs",
)


# --- the curated file ---


@pytest.fixture(scope="module")
def curated() -> Curated:
    return tunnel.load_curated()


def edited_toml(tmp_path: Path, old: str, new: str) -> Path:
    text = TUNNEL_CURATED.read_text(encoding="utf-8")
    assert old in text, old
    out = tmp_path / "tunnel.toml"
    out.write_text(text.replace(old, new, 1), encoding="utf-8")
    return out


def test_curated_values_are_the_agreed_approximations(curated: Curated) -> None:
    assert curated.status == "approximate"
    assert curated.west.value == 171.0
    assert (curated.west.low, curated.west.high) == (170.0, 172.5)
    assert curated.east.value == 193.0
    assert curated.east.low == pytest.approx(193.0 - 0.7)
    assert curated.east.high == pytest.approx(193.0 + 0.7)
    assert 1.0 < curated.section.width < 3.0
    assert curated.section.height > curated.section.width
    assert "not measured" in curated.section.basis.lower()
    assert set(curated.sources) >= {"axis", "steps", "terrain", "official_text"}


def test_the_west_approach_correction_is_recorded_with_its_evidence(curated: Curated) -> None:
    correction = curated.west_approach
    assert correction.half_width == 3.0
    assert correction.cells == 39
    assert correction.max_lowering == 13.3
    assert any("0009" in reference for reference in correction.evidence)
    assert any("approach_lidar_ground_median" in ref for ref in correction.evidence)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("half_width_m = 3.0", "half_width_m = 0.0", "half_width_m"),
        ("cells = 39", "cells = 39.5", "cells"),
        ("max_lowering_m = 13.3", "max_lowering_m = -1.0", "max_lowering_m"),
        ("[corrections.west_approach]", "[corrections.other]", "west_approach"),
    ],
)
def test_curated_rejects_an_incomplete_correction(
    tmp_path: Path, old: str, new: str, message: str
) -> None:
    with pytest.raises(TunnelError, match=message):
        tunnel.load_curated(edited_toml(tmp_path, old, new))


def test_curated_feeds_the_trail(curated: Curated) -> None:
    spec = curated.trail_spec()
    assert (spec.west_floor, spec.east_floor, spec.width) == (171.0, 193.0, curated.section.width)
    assert spec.corridor_half_width == pytest.approx(curated.section.width / 2.0 - 0.3)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ('status = "approximate"\nopen_question', 'status = "measured"\nopen_question', "status"),
        ("floor_m = 171.0", "floor_m = 180.0", "outside its range"),
        ("range_m = [170.0, 172.5]", "range_m = [172.5, 170.0]", "not ordered"),
        ("width_m = 2.0", "width_m = 4.0", "section.width"),
        ("riser_m = 0.18", 'riser_m = "tall"', "must be a number"),
    ],
)
def test_curated_rejects_inconsistent_files(
    tmp_path: Path, old: str, new: str, message: str
) -> None:
    with pytest.raises(TunnelError, match=message):
        tunnel.load_curated(edited_toml(tmp_path, old, new))


def test_curated_requires_evidence_and_sources(tmp_path: Path) -> None:
    text = TUNNEL_CURATED.read_text(encoding="utf-8")
    without_evidence = re.sub(r"\[portals\.east\.evidence\].*?\n\n", "", text, flags=re.S)
    path = tmp_path / "no-evidence.toml"
    path.write_text(without_evidence, encoding="utf-8")
    with pytest.raises(TunnelError, match="evidence"):
        tunnel.load_curated(path)
    with pytest.raises(TunnelError, match="is missing"):
        tunnel.load_curated(tmp_path / "absent.toml")


# --- evidence on synthetic data ---


def flat_grid(height: float) -> Grid:
    return Grid(np.full((200, 200), height, dtype=np.float32), 0.0, 0.0)


def lidar(points: list[tuple[float, float, float, int]]) -> LidarPoints:
    array = np.array(points, dtype=np.float64)
    return LidarPoints(array[:, 0], array[:, 1], array[:, 2], array[:, 3].astype(int))


def test_west_evidence_combines_dem_lidar_and_the_step_rise(curated: Curated) -> None:
    grid = flat_grid(100.0)
    steps = np.array([[10.0, 50.0], [30.0, 50.0]])
    portal, outward = np.array([30.0, 50.0]), np.array([-1.0, 0.0])
    points = lidar(
        [
            (12.0, 50.0, 99.0, 2),  # ground on the approach
            (14.0, 51.0, 101.0, 2),
            (16.0, 50.0, 105.0, 3),  # not ground
            (28.0, 50.0, 104.0, 1),  # within 3 m outside the portal
            (29.0, 50.0, 106.0, 2),
            (31.0, 50.0, 90.0, 2),  # inside the rock: ignored
        ]
    )
    result = tunnel.west_evidence(grid, points, steps, portal, outward, 6, curated)
    assert result["dem_at_portal"] == 100.0
    assert result["approach_dem_median"] == 100.0
    assert result["approach_lidar_ground_count"] == 2.0
    assert result["approach_lidar_ground_median"] == 100.0
    assert result["steps_rise"] == pytest.approx(6 * curated.riser)
    assert result["approach_plus_steps"] == pytest.approx(100.0 + 6 * curated.riser)
    assert result["lowest_return_within_3m"] == 104.0
    assert result["lowest_return_within_5m"] == 104.0


def test_east_evidence_uses_the_path_leaving_the_portal(curated: Curated) -> None:
    grid = flat_grid(50.0)
    leaving = np.array([[40.0, 20.0], [60.0, 20.0]])
    portal, outward = np.array([40.0, 20.0]), np.array([1.0, 0.0])
    points = lidar(
        [(41.0, 20.0, 49.0, 2), (42.0, 21.0, 51.0, 2), (43.0, 20.0, 60.0, 5), (39.0, 20.0, 10.0, 2)]
    )
    result = tunnel.east_evidence(grid, points, leaving, portal, outward, curated)
    assert result["exit_dem_median"] == 50.0
    assert result["exit_lidar_ground_median"] == 50.0
    assert result["exit_lidar_all_median"] == 51.0
    assert result["outside_ground_median_within_3m"] == 50.0


def test_evidence_without_samples_is_an_error(curated: Curated) -> None:
    grid = flat_grid(100.0)
    steps = np.array([[10.0, 50.0], [30.0, 50.0]])
    nowhere = lidar([(150.0, 150.0, 100.0, 2)])
    with pytest.raises(TunnelError, match="no samples"):
        tunnel.west_evidence(
            grid, nowhere, steps, np.array([30.0, 50.0]), np.array([-1.0, 0.0]), 6, curated
        )


def test_evidence_drift_is_reported(curated: Curated) -> None:
    same = Analysis(west=dict(curated.west.evidence), east=dict(curated.east.evidence))
    assert tunnel.evidence_drift(curated, same) == []
    moved = Analysis(
        west={**curated.west.evidence, "dem_at_portal": 100.0},
        east={k: v for k, v in curated.east.evidence.items() if k != "exit_dem_min"},
    )
    problems = tunnel.evidence_drift(curated, moved)
    assert any("west.dem_at_portal" in p for p in problems)
    assert any("east.exit_dem_min" in p and "only one" in p for p in problems)


# --- tunnel.json and the real OSM axis ---


@pytest.fixture(scope="module")
def osm() -> trail.OsmData:
    return trail.load_osm(locate("osm-penyal", "osm-penyal.json").path)


@pytest.fixture(scope="module")
def document(osm: trail.OsmData, curated: Curated) -> Doc:
    return tunnel.build_document(osm, curated, "sha")


class TestDocument:
    pytestmark = raw_marks(OSM_FILE)

    def test_follows_the_plan_contract(self, document: Doc, curated: Curated) -> None:
        assert set(document) == {
            "version",
            "licence",
            "attribution",
            "status",
            "axis",
            "width",
            "height",
            "sectionBasis",
            "portals",
            "sources",
            "mesh",
            "source",
            "inputs",
            "tools",
        }
        assert document["version"] == 1
        assert document["licence"] == "ODbL-1.0"
        assert document["attribution"] == "© OpenStreetMap contributors"
        assert document["status"] == "approximate"
        assert (document["width"], document["height"]) == (
            curated.section.width,
            curated.section.height,
        )
        assert document["sectionBasis"] == curated.section.basis
        assert document["sources"] == {
            "axis": "osm:way/26330275",
            "portalHeights": "data/curated/tunnel.toml",
        }
        assert document["mesh"] == "tunnel.glb"
        assert document["source"] == {"id": "osm-penyal", "sha256": "sha"}

    def test_axis_runs_west_to_east_at_most_half_a_metre_apart(self, document: Doc) -> None:
        axis = np.array(document["axis"])
        assert axis[0, 0] < axis[-1, 0]
        steps = np.linalg.norm(np.diff(axis[:, [0, 2]], axis=0), axis=1)
        assert steps.max() <= tunnel.AXIS_SPACING + 1e-3
        assert float(steps.sum()) == pytest.approx(49.0, abs=1.0)

    def test_floor_is_linear_between_the_curated_portal_heights(self, document: Doc) -> None:
        axis = np.array(document["axis"])
        assert axis[0, 1] == 171.0
        assert axis[-1, 1] == 193.0
        along = np.concatenate(
            [[0.0], np.cumsum(np.linalg.norm(np.diff(axis[:, [0, 2]], axis=0), axis=1))]
        )
        assert np.abs(axis[:, 1] - (171.0 + 22.0 * along / along[-1])).max() < 2e-3

    def test_portals_are_the_axis_ends(self, document: Doc) -> None:
        axis = document["axis"]
        assert [document["portals"]["west"][k] for k in "xyz"] == axis[0]
        assert [document["portals"]["east"][k] for k in "xyz"] == axis[-1]

    def test_portals_agree_with_the_trail_anchors(
        self, osm: trail.OsmData, curated: Curated, document: Doc
    ) -> None:
        x0, z0 = dem.local_origin(dem.WORK_BBOX)
        flat = Grid(np.full((2550, 2600), 100.0, dtype=np.float32), x0, z0)
        built = trail.build_trail(osm, flat, "sha", {"id": "dem"}, curated.trail_spec())
        for name, anchor in (("west", "tunnel-west"), ("east", "tunnel-east")):
            portal = document["portals"][name]
            assert [built["anchors"][anchor][k] for k in "xyz"] == [portal[k] for k in "xyz"]

    def test_floor_slope_is_about_twenty_four_degrees(
        self, osm: trail.OsmData, curated: Curated
    ) -> None:
        slope = tunnel.floor_slope_degrees(tunnel.axis_points(osm, curated))
        assert slope == pytest.approx(24.2, abs=0.3)


# --- evidence against the real data ---


@pytest.fixture(scope="module")
def found(curated: Curated) -> Analysis:
    return tunnel.analyse_data(curated)


class TestEvidenceOnRealData:
    pytestmark: ClassVar = [*raw_marks(OSM_FILE, *LIDAR_FILES), *needs_dem]

    def test_the_toml_evidence_is_what_the_data_gives(
        self, curated: Curated, found: Analysis
    ) -> None:
        assert tunnel.evidence_drift(curated, found) == []

    def test_the_west_dem_at_the_portal_is_the_rock_wall(
        self, curated: Curated, found: Analysis
    ) -> None:
        assert found.west["dem_at_portal"] > curated.west.high + 5.0

    def test_the_west_floor_lies_between_the_two_estimates(
        self, curated: Curated, found: Analysis
    ) -> None:
        assert found.west["approach_plus_steps"] <= curated.west.value
        assert curated.west.value <= found.west["lowest_return_within_3m"]
        assert curated.west.low <= found.west["approach_plus_steps"] + 0.2
        assert curated.west.high >= found.west["lowest_return_within_3m"]

    def test_the_east_floor_is_within_the_dem_and_lidar_scatter(
        self, curated: Curated, found: Analysis
    ) -> None:
        east = found.east
        assert east["exit_dem_min"] <= curated.east.value <= east["exit_dem_max"]
        assert abs(curated.east.value - east["dem_at_portal"]) <= 0.2
        assert curated.east.low <= east["exit_lidar_all_median"] + 0.2


# --- terrain: tiles, merging, openings ---


def test_tiles_touching_selects_the_tiles_whose_rectangle_meets_the_bounds() -> None:
    assert tiles.tiles_touching((700.0, -840.0, 760.0, -815.0)) == [(2, -4)]
    both = tiles.tiles_touching((760.0, -840.0, 770.0, -815.0))
    assert both == [(2, -4), (3, -4)]
    assert tiles.tiles_touching((-5000.0, -5000.0, -4990.0, -4990.0)) == []


def manifest(tile_bytes: dict[str, int], far: int = 7, sha: str = "d") -> dict[str, Any]:
    return {
        "version": 1,
        "source": {"dem": {"sha256": sha}, "ortho": {"sha256": "o"}},
        "near": {
            "tileSize": 256,
            "tiles": [
                {"id": tile, "lods": [{"level": 0, "bytes": size}]}
                for tile, size in tile_bytes.items()
            ],
        },
        "far": {"bytes": far},
    }


def test_merge_manifest_replaces_only_the_rebuilt_tiles_in_place() -> None:
    existing = manifest({"t_1_-3": 1, "t_2_-4": 2, "t_3_-4": 3})
    update = manifest({"t_2_-4": 20})
    del update["far"]
    merged = tiles.merge_manifest(existing, update)
    assert [t["id"] for t in merged["near"]["tiles"]] == ["t_1_-3", "t_2_-4", "t_3_-4"]
    assert [t["lods"][0]["bytes"] for t in merged["near"]["tiles"]] == [1, 20, 3]
    assert merged["far"] == {"bytes": 7}
    assert existing["near"]["tiles"][1]["lods"][0]["bytes"] == 2, "the input is not modified"


@pytest.mark.parametrize("field", ["inputs", "tools"])
def test_merge_manifest_refuses_changed_or_missing_provenance(field: str) -> None:
    existing = manifest({"t_1_-3": 1})
    update = manifest({"t_1_-3": 2})
    update[field] = {"bpy": "1"}
    with pytest.raises(tiles.TerrainError, match=field):
        tiles.merge_manifest(existing, update)
    existing[field] = {"bpy": "2"}
    with pytest.raises(tiles.TerrainError, match=field):
        tiles.merge_manifest(existing, update)
    existing[field] = {"bpy": "1"}
    assert tiles.merge_manifest(existing, update)[field] == {"bpy": "1"}


def test_merge_manifest_refuses_other_data_or_unknown_tiles() -> None:
    existing = manifest({"t_1_-3": 1})
    with pytest.raises(tiles.TerrainError, match="changed"):
        tiles.merge_manifest(existing, manifest({"t_1_-3": 2}, sha="other"))
    with pytest.raises(tiles.TerrainError, match="not in the existing manifest"):
        tiles.merge_manifest(existing, manifest({"t_2_-4": 2}))


def sloped_grid() -> Grid:
    xs = np.arange(2600, dtype=np.float64)
    heights = np.tile((100.0 + 0.02 * xs).astype(np.float32), (2550, 1))
    return Grid(heights, x0=-599.5, z0=-1999.5)


def synthetic_opening() -> list[tunnel_geometry.Prism]:
    corners = np.array([[700.0, 120.0, -836.0], [740.0, 120.0, -836.0]])
    return tunnel_geometry.prisms(tunnel_geometry.extend_axis(corners), 2.0, 12.0)


@pytest.mark.parametrize("level", tiles.OPENING_LODS)
def test_openings_are_cut_in_the_fine_lods(level: int) -> None:
    grid, lod = sloped_grid(), tiles.LODS[level]
    volumes = synthetic_opening()
    plain = tiles.build_tile(grid, 2, -4, lod)
    cut = tiles.build_tile(grid, 2, -4, lod, tiles.tile_openings(_features(volumes), lod))
    centroids = cut.positions[cut.triangles[: cut.surface_triangles]].mean(axis=1)
    assert not any(v.contains(centroids.astype(np.float64)).any() for v in volumes)
    assert cut.surface_triangles > plain.surface_triangles


def test_the_coarsest_lod_keeps_the_rock() -> None:
    grid, lod = sloped_grid(), tiles.LODS[-1]
    assert lod.level not in tiles.OPENING_LODS
    plain = tiles.build_tile(grid, 2, -4, lod)
    cut = tiles.build_tile(
        grid, 2, -4, lod, tiles.tile_openings(_features(synthetic_opening()), lod)
    )
    assert np.array_equal(cut.positions, plain.positions)
    assert np.array_equal(cut.triangles, plain.triangles)


def test_skirts_hang_below_the_tile_border_only_not_along_the_opening() -> None:
    mesh = tiles.build_tile(sloped_grid(), 2, -4, tiles.LODS[0], synthetic_opening())
    skirt = mesh.positions[mesh.surface_vertices :].astype(np.float64)
    assert skirt.shape[0] > 0
    x_edge = np.isclose(skirt[:, 0], mesh.extent.x_min) | np.isclose(skirt[:, 0], mesh.extent.x_max)
    z_edge = np.isclose(skirt[:, 2], mesh.extent.z_min) | np.isclose(skirt[:, 2], mesh.extent.z_max)
    assert (x_edge | z_edge).all()


def _features(volumes: list[tunnel_geometry.Prism]) -> tunnel_geometry.TerrainFeatures:
    carve = tunnel_geometry.Carve(
        path=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        half_width=1.0,
        portal=np.array([1.0, 0.0]),
        outward=np.array([1.0, 0.0]),
    )
    return tunnel_geometry.TerrainFeatures(carve=carve, openings=volumes)


def test_carve_caps_heights_to_the_footpath_floor_outside_the_portal_plane() -> None:
    heights = np.full((40, 40), 20.0, dtype=np.float32)
    heights[:, :10] = 5.0  # already below the floor
    grid = Grid(heights, x0=0.0, z0=0.0)
    carve = tunnel_geometry.Carve(
        path=np.array([[12.0, 10.0, 20.0], [28.0, 14.0, 20.0]]),
        half_width=3.0,
        portal=np.array([28.0, 20.0]),
        outward=np.array([-1.0, 0.0]),
    )
    out = carve.apply(grid)
    assert grid.heights[20, 20] == 20.0, "the input grid is not modified"
    assert out.heights[20, 12] == pytest.approx(10.0)
    assert out.heights[20, 20] == pytest.approx(12.0)
    assert out.heights[20, 28] == pytest.approx(14.0)
    assert out.heights[20, 29] == 20.0, "rock beyond the portal plane stays"
    assert out.heights[20, 5] == 5.0, "cells below the floor are untouched"
    assert out.heights[16, 20] == 20.0, "outside the strip (4 m to the side) the rock stays"
    assert out.heights[18, 20] == pytest.approx(12.0)


# --- geometry against the real terrain ---


def ray_hits(
    origin: Floats, direction: Floats, length: float, mesh: tiles.TerrainMesh
) -> list[float]:
    """Distances (Moller-Trumbore, both faces) at which the segment crosses mesh triangles."""
    p = mesh.positions.astype(np.float64)
    tri = mesh.triangles
    end = origin + direction * length
    low, high = np.minimum(origin, end) - 1e-6, np.maximum(origin, end) + 1e-6
    corners = p[tri]
    near = (corners.max(axis=1) >= low).all(axis=1) & (corners.min(axis=1) <= high).all(axis=1)
    a, b, c = (p[tri[near, k]] for k in range(3))
    edge1, edge2 = b - a, c - a
    h = np.cross(direction, edge2)
    det = np.einsum("ij,ij->i", edge1, h)
    parallel = np.abs(det) < 1e-12
    inv = np.where(parallel, 0.0, 1.0 / np.where(parallel, 1.0, det))
    s = origin - a
    u = inv * np.einsum("ij,ij->i", s, h)
    q = np.cross(s, edge1)
    v = inv * (q @ direction)
    t = inv * np.einsum("ij,ij->i", edge2, q)
    hit = ~parallel & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-9) & (t <= length)
    return sorted(float(x) for x in t[hit])


@pytest.fixture(scope="module")
def world(osm: trail.OsmData, curated: Curated) -> dict[str, Any]:
    grid, _ = dem.load_dem()
    features = tunnel.terrain_features(osm, grid, curated)
    carved = features.carve.apply(grid)
    affected = tiles.tiles_touching(features.bounds)
    assert affected == [(2, -4)]
    cut = {
        lod.level: tiles.build_tile(carved, 2, -4, lod, tiles.tile_openings(features, lod))
        for lod in tiles.LODS
    }
    raw = {lod.level: tiles.build_tile(grid, 2, -4, lod) for lod in tiles.LODS}
    axis = tunnel.axis_points(osm, curated)
    return {"cut": cut, "raw": raw, "axis": axis, "features": features}


class TestWestApproachCorrection:
    pytestmark: ClassVar = [*raw_marks(OSM_FILE), *needs_dem]

    def test_the_carve_reads_its_half_width_from_the_toml(
        self, osm: trail.OsmData, tmp_path: Path
    ) -> None:
        grid, _ = dem.load_dem()
        narrow = tunnel.load_curated(
            edited_toml(tmp_path, "half_width_m = 3.0", "half_width_m = 2.0")
        )
        features = tunnel.terrain_features(osm, grid, narrow)
        assert features.carve.half_width == 2.0

    def test_the_recorded_cell_count_and_maximum_lowering_match_the_real_dem(
        self, osm: trail.OsmData, curated: Curated
    ) -> None:
        grid, _ = dem.load_dem()
        carved = tunnel.terrain_features(osm, grid, curated).carve.apply(grid)
        lowering = grid.heights.astype(np.float64) - carved.heights
        assert lowering.min() >= 0.0, "the carve only lowers"
        assert int((lowering > 0.0).sum()) == curated.west_approach.cells
        assert float(lowering.max()) == pytest.approx(curated.west_approach.max_lowering, abs=0.05)


class TestTunnelAgainstTheTerrain:
    pytestmark: ClassVar = [*raw_marks(OSM_FILE), *needs_dem]

    def portal_frame(self, axis: Floats, west: bool) -> tuple[Floats, Floats]:
        """Portal point and the horizontal unit vector pointing out of the tunnel."""
        if west:
            vector = axis[0] - axis[1]
            point = axis[0]
        else:
            vector = axis[-1] - axis[-2]
            point = axis[-1]
        flat = np.array([vector[0], 0.0, vector[2]])
        return point, flat / np.linalg.norm(flat)

    @pytest.mark.parametrize("west", [True, False], ids=["west", "east"])
    @pytest.mark.parametrize("level", [0, 1])
    def test_a_ray_from_two_metres_outside_reaches_the_tunnel_unobstructed(
        self, world: dict[str, Any], west: bool, level: int
    ) -> None:
        portal, outward = self.portal_frame(world["axis"], west)
        start = portal + outward * 2.0 + np.array([0.0, 1.5, 0.0])
        mesh = world["cut"][level]
        assert ray_hits(start, -outward, 2.0 + tunnel_geometry.OVERRUN, mesh) == []
        assert ray_hits(start, np.array([0.0, 1.0, 0.0]), 60.0, mesh) == [], "open air above"
        below = ray_hits(start, np.array([0.0, -1.0, 0.0]), 10.0, mesh)
        # The terrain is within the LOD error of the footpath floor, and the floor within half a
        # metre of the flat portal height the app uses outside the tunnel.
        assert below, "there is ground under the start point"
        assert below[0] == pytest.approx(1.5, abs=0.5 + tiles.LODS[level].max_error), "the floor"

    @pytest.mark.parametrize("level", [0, 1])
    def test_the_rock_above_the_west_approach_is_carved_away(
        self, world: dict[str, Any], level: int
    ) -> None:
        portal, outward = self.portal_frame(world["axis"], west=True)
        start = portal + outward * 2.0 + np.array([0.0, 1.5, 0.0])
        rock = ray_hits(start, np.array([0.0, 1.0, 0.0]), 60.0, world["raw"][level])
        assert rock, "without the carve the DEM is the rock wall above the path"
        assert rock[0] > 3.0

    @pytest.mark.parametrize("level", [0, 1])
    def test_a_ray_along_the_axis_never_meets_the_terrain(
        self, world: dict[str, Any], level: int
    ) -> None:
        axis = world["axis"]
        west, outward_west = self.portal_frame(axis, west=True)
        east, outward_east = self.portal_frame(axis, west=False)
        path = np.vstack([west + outward_west * 2.0, axis, east + outward_east * 2.0])
        path[0, 1] = axis[0, 1]
        path[-1, 1] = axis[-1, 1]
        lifted = path + np.array([0.0, 1.5, 0.0])
        for a, b in itertools.pairwise(lifted):
            length = float(np.linalg.norm(b - a))
            assert ray_hits(a, (b - a) / length, length, world["cut"][level]) == []

    def test_the_terrain_above_the_tunnel_is_rock(self, world: dict[str, Any]) -> None:
        axis = world["axis"]
        middle = axis[len(axis) // 2]
        for level in (0, 1):
            above = ray_hits(
                middle + np.array([0.0, 2.6, 0.0]),
                np.array([0.0, 1.0, 0.0]),
                80.0,
                world["cut"][level],
            )
            assert above, "the mountain is still there above the vault"

    def test_the_shell_floor_is_at_the_curated_heights_at_both_portals(
        self, world: dict[str, Any], curated: Curated
    ) -> None:
        shell = tunnel_geometry.build_shell(
            tunnel_geometry.extend_axis(world["axis"]),
            curated.section.width,
            curated.section.height,
        )
        floor = shell.positions[shell.floor].astype(np.float64)
        axis = world["axis"]
        for portal, expected in ((axis[0], curated.west.value), (axis[-1], curated.east.value)):
            ring = floor[np.linalg.norm(floor[:, [0, 2]] - portal[[0, 2]], axis=1) < 1.2]
            assert ring[:, 1].min() == pytest.approx(expected, abs=2e-3) or ring[
                :, 1
            ].max() == pytest.approx(expected, abs=2e-3)
        assert floor[:, 1].min() == pytest.approx(curated.west.value, abs=2e-3)
        assert floor[:, 1].max() == pytest.approx(curated.east.value, abs=2e-3)

    def test_the_walkable_floor_climbs_about_twenty_two_metres_at_twenty_four_degrees(
        self, world: dict[str, Any]
    ) -> None:
        axis = world["axis"]
        slope = tunnel.floor_slope_degrees(axis)
        rise = axis[-1, 1] - axis[0, 1]
        print(
            f"tunnel floor: +{rise:.1f} m over {np.hypot(*(axis[-1] - axis[0])[[0, 2]]):.1f} m "
            f"chord, mean slope {slope:.1f} deg"
        )
        assert rise == pytest.approx(22.0)
        assert 23.0 < slope < 25.5


# --- the shell seen from outside ---

FOOTPRINT_STEP = 0.1  # metres between the top-down samples
PORTAL_REACH = 6.0  # metres from a portal that are checked
# The shell is clipped to the carved DEM at its vertices (0.5 m rings) and then interpolated, so
# across the steep edge of the west carve it can stand above the DEM by a chord error. Measured with
# a 0.1 m step: 1.22 m west, 0 m east, for LOD 0, 1 and 2 alike (it is a property of the shell and
# the carve, not of the mesh). The rock mesh may in addition lie up to ``Lod.max_error`` below the
# DEM, so the allowed protrusion above the DEM is that LOD's maxError plus the chord allowance.
CLIP_CHORD_ALLOWANCE = 1.5  # metres: measured 1.22 m plus 0.28 m of margin
# Exposed area: measured 0.06 m2 (6 samples) west and <= 0.05 m2 east at every LOD; 0.2 m2 is 20
# samples at FOOTPRINT_STEP, a sliver at the carve edge rather than a visible patch of wall.
MAX_EXPOSED_AREA = 0.2  # m2


def top_hits(
    positions: Floats, triangles: npt.NDArray[np.int_], x: Floats, z: Floats
) -> tuple[Floats, npt.NDArray[np.int_]]:
    """Highest surface under each ``(x, z)`` seen from above: height (-inf if none) and triangle."""
    best = np.full(x.shape, -np.inf)
    who = np.full(x.shape, -1)
    corners = positions[triangles]
    near = (
        (corners[:, :, 0].max(axis=1) >= x.min())
        & (corners[:, :, 0].min(axis=1) <= x.max())
        & (corners[:, :, 2].max(axis=1) >= z.min())
        & (corners[:, :, 2].min(axis=1) <= z.max())
    )
    for t in np.flatnonzero(near):
        a, b, c = corners[t]
        det = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(det) < 1e-12:
            continue
        l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / det
        l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / det
        inside = (l1 >= -1e-9) & (l2 >= -1e-9) & (1.0 - l1 - l2 >= -1e-9)
        y = l1 * a[1] + l2 * b[1] + (1.0 - l1 - l2) * c[1]
        better = inside & (y > best)
        best[better] = y[better]
        who[better] = t
    return best, who


@pytest.fixture(scope="module")
def scene(osm: trail.OsmData, curated: Curated) -> dict[str, Any]:
    grid, _ = dem.load_dem()
    features = tunnel.terrain_features(osm, grid, curated)
    carved = features.carve.apply(grid)
    shell = tunnel.tunnel_shell(osm, curated, carved)
    positions = shell.positions.astype(np.float64)
    axis = tunnel.axis_points(osm, curated)
    meshes = {}
    for lod in tiles.LODS:
        mesh = tiles.build_tile(carved, 2, -4, lod, tiles.tile_openings(features, lod))
        meshes[lod.level] = mesh
    return {
        "carved": carved,
        "shell": shell,
        "positions": positions,
        "axis": axis,
        "meshes": meshes,
    }


class TestShellSeenFromOutside:
    """M5 (audit 002): from outside, nothing but rock and the portal mouths may show."""

    pytestmark: ClassVar = [*raw_marks(OSM_FILE), *needs_dem]

    def footprint(self, scene: dict[str, Any], portal: Floats) -> tuple[Floats, Floats]:
        positions = scene["positions"]
        near = np.hypot(positions[:, 0] - portal[0], positions[:, 2] - portal[2]) < PORTAL_REACH
        low, high = positions[near].min(axis=0), positions[near].max(axis=0)
        gx, gz = np.meshgrid(
            np.arange(low[0], high[0], FOOTPRINT_STEP), np.arange(low[2], high[2], FOOTPRINT_STEP)
        )
        keep = np.hypot(gx - portal[0], gz - portal[2]) < PORTAL_REACH
        return gx[keep], gz[keep]

    @pytest.mark.parametrize("end", [0, -1], ids=["west", "east"])
    @pytest.mark.parametrize("level", [0, 1, 2])
    def test_no_wall_or_vault_shows_above_the_rock(
        self, scene: dict[str, Any], end: int, level: int
    ) -> None:
        shell, positions = scene["shell"], scene["positions"]
        x, z = self.footprint(scene, scene["axis"][end])
        shell_y, shell_tri = top_hits(positions, shell.triangles, x, z)
        mesh = scene["meshes"][level]
        rock_y, _ = top_hits(mesh.positions.astype(np.float64), mesh.triangles, x, z)
        wall = ~shell.floor[shell.triangles[np.maximum(shell_tri, 0), 0]]
        exposed = np.isfinite(shell_y) & wall & (shell_y > rock_y + 1e-3)
        dem_y = scene["carved"].sample(x, z)
        protrusion = float(np.max(np.where(exposed, shell_y - dem_y, 0.0)))
        area = float(exposed.sum()) * FOOTPRINT_STEP**2
        print(
            f"LOD{level} {'east' if end else 'west'}: exposed {area:.2f} m2, max {protrusion:.2f} m"
        )
        assert area <= MAX_EXPOSED_AREA, "wall or vault visible from above, outside the rock"
        assert protrusion <= tiles.LODS[level].max_error + CLIP_CHORD_ALLOWANCE

    @pytest.mark.parametrize("end", [0, -1], ids=["west", "east"])
    @pytest.mark.parametrize("level", [0, 1])
    def test_every_cut_in_the_terrain_is_covered_by_the_shell(
        self, scene: dict[str, Any], end: int, level: int
    ) -> None:
        shell = scene["shell"]
        x, z = self.footprint(scene, scene["axis"][end])
        shell_y, _ = top_hits(scene["positions"], shell.triangles, x, z)
        mesh = scene["meshes"][level]
        rock_y, _ = top_hits(mesh.positions.astype(np.float64), mesh.triangles, x, z)
        uncovered = ~np.isfinite(shell_y) & ~np.isfinite(rock_y)
        assert not uncovered.any(), "terrain hole with nothing under it: the sea shows through"


# --- the shell GLB ---


@pytest.fixture(scope="module")
def exported(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, tunnel_geometry.ShellMesh]:
    from penyal_pipeline.blender import tunnel as blender_tunnel

    axis = tunnel_geometry.extend_axis(
        np.array([[0.0, 0.0, 0.0], [10.0, 2.0, 0.0], [18.0, 6.0, 5.0]])
    )
    shell = tunnel_geometry.build_shell(axis, 2.0, 2.6)
    out = tmp_path_factory.mktemp("shell") / "tunnel.glb"
    blender_tunnel.export_tunnel(shell, out)
    return out, shell


@pytest.mark.slow
class TestShellExport:
    def test_glb_keeps_positions_normals_and_triangles(
        self, exported: tuple[Path, tunnel_geometry.ShellMesh]
    ) -> None:
        path, shell = exported
        gltf, blob = read_glb(path)
        assert len(gltf["meshes"]) == 1
        attributes = gltf["meshes"][0]["primitives"][0]["attributes"]
        positions = accessor(gltf, blob, attributes["POSITION"])
        normals = accessor(gltf, blob, attributes["NORMAL"])
        indices = accessor(gltf, blob, gltf["meshes"][0]["primitives"][0]["indices"])
        assert indices.size == shell.triangles.size
        assert positions.min(axis=0) == pytest.approx(shell.positions.min(axis=0), abs=1e-4)
        assert positions.max(axis=0) == pytest.approx(shell.positions.max(axis=0), abs=1e-4)
        assert np.allclose(np.linalg.norm(normals, axis=1), 1.0, atol=1e-4)
        expected = {tuple(np.round(p, 3)) for p in shell.positions}
        assert {tuple(np.round(p, 3)) for p in positions} == expected
        for node in gltf["nodes"]:
            assert not {"translation", "rotation", "scale", "matrix"} & set(node)

    def test_material_is_plain_double_sided_rock_without_textures(
        self, exported: tuple[Path, tunnel_geometry.ShellMesh]
    ) -> None:
        gltf, _ = read_glb(exported[0])
        assert "images" not in gltf
        assert "textures" not in gltf
        (material,) = gltf["materials"]
        assert material["doubleSided"] is True
        pbr = material["pbrMetallicRoughness"]
        assert "baseColorTexture" not in pbr
        assert pbr["metallicFactor"] == 0.0
        red, green, blue, _ = pbr["baseColorFactor"]
        assert abs(red - green) < 0.1, "a grey, not a colour"
        assert abs(green - blue) < 0.1


# --- determinism ---


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): sha256(p) for p in sorted(root.rglob("*")) if p.is_file()}


def run_cli(args: list[str], seed: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONHASHSEED": seed}
    return subprocess.run(
        [sys.executable, "-m", "penyal_pipeline.cli", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )


@needs_optimizer
@pytest.mark.slow
class TestDeterminism:
    pytestmark: ClassVar = [*raw_marks(OSM_FILE, "icv-orto-2024-0848-7-2/*.tif"), *needs_dem]

    def test_tunnel_files_are_byte_identical_across_runs_and_hash_seeds(
        self, tmp_path: Path
    ) -> None:
        outputs = []
        for name, seed in (("first", "1"), ("second", "4242")):
            out = tmp_path / name
            done = run_cli(
                [
                    "tunnel",
                    "--out-dir",
                    str(out),
                    "--build-dir",
                    str(tmp_path / f"{name}-build"),
                    "--skip-tiles",
                ],
                seed,
            )
            assert done.returncode == 0, done.stderr
            outputs.append(out)
        assert hashes(outputs[0]) == hashes(outputs[1])
        assert sorted(hashes(outputs[0])) == ["tunnel.glb", "tunnel.json"]
        assert hashes(tmp_path / "first-build") == hashes(tmp_path / "second-build")

    def test_the_cut_tile_is_byte_identical_across_runs_and_hash_seeds(
        self, tmp_path: Path
    ) -> None:
        features = tunnel.load_terrain_features()
        first = tmp_path / "first"
        tiles.run_terrain(
            out_dir=first / "out",
            build_dir=first / "glb",
            tiles=[(2, -4)],
            include_far=False,
            features=features,
        )
        second = tmp_path / "second"
        done = run_cli(
            [
                "terrain",
                "--tile",
                "t_2_-4",
                "--no-far",
                "--out-dir",
                str(second / "out"),
                "--build-dir",
                str(second / "glb"),
            ],
            "4242",
        )
        assert done.returncode == 0, done.stderr
        assert hashes(first / "glb") == hashes(second / "glb")
        assert hashes(first / "out") == hashes(second / "out")
        manifest = json.loads((first / "out" / "manifest.json").read_text(encoding="utf-8"))
        assert [t["id"] for t in manifest["near"]["tiles"]] == ["t_2_-4"]
