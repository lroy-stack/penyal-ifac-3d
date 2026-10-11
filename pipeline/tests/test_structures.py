"""E1.4: the OSM staircases as meshes with a handrail and a step-height-aware collision proxy."""

import hashlib
import json
import shutil
from pathlib import Path
from typing import ClassVar

import numpy as np
import numpy.typing as npt
import pytest
from conftest import build_marks, raw_marks
from test_terrain_export import read_glb

from penyal_pipeline import dem, structures, trail, tunnel
from penyal_pipeline.dem import Grid
from penyal_pipeline.paths import REPO_ROOT, TERRAIN_BUILD_DIR
from penyal_pipeline.rawdata import locate
from penyal_pipeline.structures import Staircase, StairSpec, StructuresError

type Floats = npt.NDArray[np.float64]

SLOPE = 0.2  # metres of height per metre eastwards on the synthetic ramp
X0, Z0 = -50.0, -50.0
needs_dem = build_marks(TERRAIN_BUILD_DIR / "dem.f32", TERRAIN_BUILD_DIR / "dem.json")
needs_optimizer = pytest.mark.skipif(
    shutil.which("node") is None
    or not (REPO_ROOT / "tools" / "bin" / "ktx").exists()
    or not (REPO_ROOT / "node_modules" / ".bin" / "gltf-transform").exists(),
    reason="node, tools/bin/ktx and `pnpm install` are needed to optimise GLBs",
)


def ramp_grid(slope: float = SLOPE) -> Grid:
    columns = np.arange(200, dtype=np.float64)
    heights = np.tile((100.0 + slope * columns).astype(np.float32), (200, 1))
    return Grid(heights, x0=X0, z0=Z0, cell=1.0)


def ramp_height(x: float, slope: float = SLOPE) -> float:
    return 100.0 + slope * (x - X0)


def spec(flight_start: float = 0.0) -> StairSpec:
    return StairSpec(id="test", name="test stairs", way=1, flight_start=flight_start, ground="dem")


def straight(length: float = 12.0, steps: int = 12, slope: float = SLOPE) -> Staircase:
    xz = np.array([[0.0, 0.0], [length, 0.0]])
    return structures.build_staircase(spec(), xz, steps, ramp_grid(slope).sample)


def face_normals(stairs: Staircase) -> Floats:
    p = stairs.mesh.positions.astype(np.float64)
    t = stairs.mesh.triangles
    return np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]])


class TestFlight:
    def test_it_has_the_osm_step_count_with_one_tread_each(self) -> None:
        stairs = straight(steps=12)
        assert stairs.step_count == 12
        assert len(stairs.treads) == 12
        assert len({round(t.top, 6) for t in stairs.treads}) == 12

    def test_risers_are_uniform(self) -> None:
        stairs = straight(steps=12)
        tops = np.array([t.top for t in stairs.treads])
        rises = np.diff(np.concatenate([[stairs.base[1]], tops]))
        assert rises == pytest.approx(np.full(12, stairs.riser), abs=1e-9)
        assert stairs.riser == pytest.approx(SLOPE * 12.0 / 12, abs=1e-4)

    def test_first_step_starts_on_the_dem_and_the_last_ends_on_it(self) -> None:
        stairs = straight(length=12.0, steps=12)
        assert stairs.base[1] == pytest.approx(ramp_height(0.0), abs=1e-4)
        assert stairs.treads[-1].top == pytest.approx(ramp_height(12.0), abs=1e-4)
        assert stairs.top[1] == pytest.approx(ramp_height(12.0), abs=1e-4)

    def test_treads_split_the_flight_evenly(self) -> None:
        stairs = straight(length=12.0, steps=6, slope=0.1)
        depth = [
            float(np.hypot(*(t.quad[3] - t.quad[0]))) for t in stairs.treads
        ]  # left edge of each tread
        assert depth == pytest.approx([2.0] * 6, abs=1e-9)
        assert stairs.tread_depth == pytest.approx(2.0)

    def test_a_flight_that_descends_along_the_way_is_turned_round(self) -> None:
        xz = np.array([[12.0, 0.0], [0.0, 0.0]])
        stairs = structures.build_staircase(spec(), xz, 12, ramp_grid().sample)
        assert stairs.base[0] == pytest.approx(0.0)
        assert stairs.top[0] == pytest.approx(12.0)
        assert stairs.reversed_way is True

    def test_a_riser_the_player_could_not_climb_is_rejected(self) -> None:
        with pytest.raises(StructuresError, match="step height"):
            straight(length=12.0, steps=3, slope=0.5)

    def test_a_flat_flight_is_rejected(self) -> None:
        with pytest.raises(StructuresError, match="rise"):
            straight(slope=0.0)

    def test_a_bend_keeps_the_count_and_a_monotone_rise(self) -> None:
        xz = np.array([[0.0, 0.0], [6.0, 0.0], [6.0, 4.0], [10.0, 4.0]])
        stairs = structures.build_staircase(spec(), xz, 9, ramp_grid().sample)
        tops = [t.top for t in stairs.treads]
        assert len(tops) == 9
        assert tops == sorted(tops)
        for tread in stairs.treads:
            assert float(np.hypot(*(tread.quad[1] - tread.quad[0]))) == pytest.approx(
                structures.STAIR_WIDTH
            )

    def test_the_flight_can_start_part_way_along_the_way(self) -> None:
        xz = np.array([[0.0, 0.0], [12.0, 0.0]])
        stairs = structures.build_staircase(spec(flight_start=6.0), xz, 6, ramp_grid().sample)
        assert stairs.base[0] == pytest.approx(6.0)
        assert stairs.base[1] == pytest.approx(ramp_height(6.0), abs=1e-4)
        assert stairs.tread_depth == pytest.approx(1.0)


class TestMesh:
    def test_every_face_points_away_from_the_solid(self) -> None:
        stairs = straight()
        normals = face_normals(stairs)
        assert float(np.linalg.norm(normals, axis=1).min()) > 0.0
        assert stairs.mesh.normals.shape == stairs.mesh.positions.shape
        unit = stairs.mesh.normals.astype(np.float64)
        assert np.allclose(np.linalg.norm(unit, axis=1), 1.0, atol=1e-5)
        by_face = normals / np.linalg.norm(normals, axis=1, keepdims=True)
        stored = unit[stairs.mesh.triangles[:, 0]]
        assert np.einsum("ij,ij->i", by_face, stored).min() > 0.999

    def test_treads_face_up(self) -> None:
        stairs = straight()
        normals = face_normals(stairs)
        tops = stairs.mesh.positions[stairs.mesh.triangles].mean(axis=1)[:, 1]
        horizontal = (normals[:, 1] > 0) & (np.abs(normals[:, 0]) + np.abs(normals[:, 2]) < 1e-9)
        top_levels = {round(t.top, 4) for t in stairs.treads}
        assert top_levels <= {round(float(y), 4) for y in tops[horizontal]}

    def test_stone_and_metal_use_two_material_slots(self) -> None:
        stairs = straight()
        assert set(stairs.mesh.materials.tolist()) == {structures.STONE, structures.METAL}
        assert stairs.mesh.materials.shape == (stairs.mesh.triangles.shape[0],)

    def test_the_stone_stays_inside_the_stair_footprint_and_under_the_top(self) -> None:
        stairs = straight(length=12.0, steps=12)
        stone = stairs.mesh.positions[stairs.mesh.triangles[stairs.mesh.materials == 0]]
        flat = stone.reshape(-1, 3)
        assert flat[:, 0].min() >= -1e-4
        assert flat[:, 0].max() <= 12.0 + 1e-4
        assert np.abs(flat[:, 2]).max() <= structures.STAIR_WIDTH / 2 + 1e-4
        assert flat[:, 1].max() == pytest.approx(ramp_height(12.0), abs=1e-3)

    def test_the_steps_are_buried_below_the_ground(self) -> None:
        stairs = straight()
        lowest = stairs.mesh.positions[:, 1].min()
        assert lowest < ramp_height(0.0) - structures.STEP_EMBED + 1e-4

    def test_building_twice_gives_identical_arrays(self) -> None:
        a, b = straight(), straight()
        assert a.mesh.positions.tobytes() == b.mesh.positions.tobytes()
        assert a.mesh.triangles.tobytes() == b.mesh.triangles.tobytes()
        assert a.mesh.materials.tobytes() == b.mesh.materials.tobytes()


class TestHandrail:
    def test_it_is_on_the_right_hand_when_going_up(self) -> None:
        stairs = straight()
        assert structures.HANDRAIL_SIDE == "right"
        metal = stairs.mesh.positions[stairs.mesh.triangles[stairs.mesh.materials == 1]]
        flat = metal.reshape(-1, 3)
        # Walking east (+x) the right hand is south (+z) in the local frame.
        assert flat[:, 2].min() > 0.0
        assert flat[:, 2].max() < structures.STAIR_WIDTH / 2
        assert stairs.handrail.side == "right"

    def test_the_rail_runs_at_the_rail_height_above_the_nosing_line(self) -> None:
        stairs = straight()
        rail = stairs.handrail.rail
        heights = rail[:, 1] - np.array([ramp_height(x) for x in rail[:, 0]])
        assert heights == pytest.approx(np.full(rail.shape[0], structures.RAIL_HEIGHT), abs=1e-4)

    def test_posts_are_at_both_ends_and_about_every_post_spacing(self) -> None:
        stairs = straight(length=12.0, steps=12)
        posts = stairs.handrail.posts
        assert posts[0][0] == pytest.approx(0.0)
        assert posts[-1][0] == pytest.approx(12.0)
        gaps = np.diff([p[0] for p in posts])
        assert gaps.max() <= structures.POST_SPACING + 1.0


class TestCollision:
    def test_each_tread_is_a_quad_at_its_own_top(self) -> None:
        stairs = straight(length=12.0, steps=12)
        assert [t.quad.shape for t in stairs.treads] == [(4, 2)] * 12
        first = stairs.treads[0]
        assert first.quad[:, 0].min() == pytest.approx(0.0)
        assert first.quad[:, 0].max() == pytest.approx(1.0)

    def test_the_rise_between_neighbouring_treads_is_walkable(self) -> None:
        stairs = straight()
        tops = [stairs.base[1], *[t.top for t in stairs.treads]]
        assert max(np.diff(tops)) <= structures.PLAYER_STEP_HEIGHT

    def test_surface_below_picks_the_tread_under_a_point(self) -> None:
        stairs = straight(length=12.0, steps=12)
        assert structures.tread_height(stairs.treads, 0.5, 0.0) == pytest.approx(
            stairs.treads[0].top
        )
        assert structures.tread_height(stairs.treads, 11.5, 0.2) == pytest.approx(
            stairs.treads[11].top
        )
        assert structures.tread_height(stairs.treads, 5.5, 3.0) is None
        assert structures.tread_height(stairs.treads, 13.0, 0.0) is None


class TestSpecs:
    def test_the_three_osm_staircases_are_specified_by_way(self) -> None:
        curated = tunnel.load_curated().trail_spec()
        specs = structures.staircase_specs(curated)
        assert {s.way for s in specs} == {26330269, 862108205, 862108208}
        flights = {s.way: s.flight_start for s in specs}
        assert flights[862108208] == curated.steps_ramp_start
        assert flights[26330269] == 0.0

    def test_a_way_without_a_step_count_is_rejected(self) -> None:
        with pytest.raises(StructuresError, match="step_count"):
            structures.step_count_of({"highway": "steps"}, 5)

    def test_the_step_count_is_read_as_an_integer(self) -> None:
        assert structures.step_count_of({"step_count": "30"}, 5) == 30


# --- the real data -----------------------------------------------------------------------------

real_marks = [*raw_marks("osm-penyal/osm-penyal.json"), *needs_dem]


@pytest.fixture(scope="module")
def real() -> dict[int, Staircase]:
    osm = trail.load_osm(locate(trail.OSM_SOURCE_ID, trail.OSM_FILE).path)
    grid, _ = dem.load_dem()
    curated = tunnel.load_curated().trail_spec()
    return {s.spec.way: s for s in structures.build_all(osm, grid, curated)}


@pytest.mark.data
class TestRealStaircases:
    pytestmark: ClassVar = real_marks

    def test_step_counts_come_from_osm(self, real: dict[int, Staircase]) -> None:
        assert {way: s.step_count for way, s in real.items()} == {
            26330269: 30,
            862108205: 10,
            862108208: 6,
        }
        assert all(len(s.treads) == s.step_count for s in real.values())

    def test_risers_are_uniform_and_walkable(self, real: dict[int, Staircase]) -> None:
        for stairs in real.values():
            tops = np.array([stairs.base[1], *[t.top for t in stairs.treads]])
            rises = np.diff(tops)
            assert rises == pytest.approx(np.full(stairs.step_count, stairs.riser), abs=1e-9)
            assert 0.10 < stairs.riser <= structures.PLAYER_STEP_HEIGHT

    def test_the_draped_flights_start_and_end_on_the_dem(self, real: dict[int, Staircase]) -> None:
        grid, _ = dem.load_dem()
        for way in (26330269, 862108205):
            stairs = real[way]
            for point in (stairs.base, stairs.top):
                on_dem = float(grid.sample(point[0], point[2]))
                assert point[1] == pytest.approx(on_dem, abs=0.01)

    def test_the_portal_flight_ends_on_the_curated_west_floor(
        self, real: dict[int, Staircase]
    ) -> None:
        floor = tunnel.load_curated().west.value
        stairs = real[862108208]
        assert stairs.top[1] == pytest.approx(floor, abs=1e-6)
        assert stairs.base[1] == pytest.approx(169.87, abs=0.05)

    def test_the_ten_step_flight_is_oriented_by_the_dem_not_by_the_incline_tag(
        self, real: dict[int, Staircase]
    ) -> None:
        stairs = real[862108205]
        assert stairs.incline_tag == "down"
        assert stairs.top[1] > stairs.base[1]
        assert stairs.reversed_way is False

    def test_the_mesh_stays_small(self, real: dict[int, Staircase]) -> None:
        assert sum(s.mesh.triangles.shape[0] for s in real.values()) < 3000


# --- GLB export and determinism ----------------------------------------------------------------


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.slow
class TestExport:
    def test_the_glb_has_one_node_per_staircase_with_two_plain_materials(
        self, tmp_path: Path
    ) -> None:
        from penyal_pipeline.blender import structures as blender_structures

        out = blender_structures.export_structures(
            [straight().mesh_named("stairs_a"), straight().mesh_named("stairs_b")],
            tmp_path / "structures.glb",
        )
        gltf, _ = read_glb(out)
        assert sorted(n["name"] for n in gltf["nodes"]) == ["stairs_a", "stairs_b"]
        assert "images" not in gltf
        by_name = {m["name"]: m for m in gltf["materials"]}
        assert set(by_name) == {"stairs_stone", "stairs_handrail_metal"}
        assert by_name["stairs_handrail_metal"]["pbrMetallicRoughness"]["metallicFactor"] > 0.5
        assert by_name["stairs_stone"]["pbrMetallicRoughness"]["metallicFactor"] == 0.0
        for mesh in gltf["meshes"]:
            assert len(mesh["primitives"]) == 2

    def test_two_exports_are_byte_identical(self, tmp_path: Path) -> None:
        from penyal_pipeline.blender import structures as blender_structures

        meshes = [straight().mesh_named("stairs_a")]
        first = blender_structures.export_structures(meshes, tmp_path / "a" / "s.glb")
        second = blender_structures.export_structures(meshes, tmp_path / "b" / "s.glb")
        assert sha256(first) == sha256(second)


@needs_optimizer
@pytest.mark.slow
@pytest.mark.data
class TestRun:
    pytestmark: ClassVar = real_marks

    def test_run_twice_writes_identical_files_and_a_provenance_block(self, tmp_path: Path) -> None:
        reports = []
        for name in ("first", "second"):
            out = tmp_path / name
            reports.append(
                structures.run_structures(
                    out, tmp_path / f"{name}-build", {"inputs": [], "tools": {}}
                )
            )
            assert sorted(p.name for p in out.iterdir()) == ["structures.glb", "structures.json"]
        for name in ("structures.glb", "structures.json"):
            assert sha256(tmp_path / "first" / name) == sha256(tmp_path / "second" / name)
        document = json.loads((tmp_path / "first" / "structures.json").read_text(encoding="utf-8"))
        assert [s["stepCount"] for s in document["staircases"]] == [30, 10, 6]
        assert document["constants"]["status"] == "provisional"
        assert reports[0].triangles == sum(s["mesh"]["triangles"] for s in document["staircases"])
        assert (tmp_path / "first" / "structures.glb").stat().st_size == reports[0].glb_bytes
