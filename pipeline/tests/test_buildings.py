"""E3: the two visitor-centre buildings extruded from OSM and sized from the LiDAR roof points."""

import hashlib
import json
import shutil
from pathlib import Path
from typing import ClassVar

import numpy as np
import numpy.typing as npt
import pytest
import shapely
from conftest import build_marks, raw_marks
from shapely.geometry import Polygon
from test_terrain_export import accessor, read_glb

from penyal_pipeline import buildings, dem, trail
from penyal_pipeline.buildings import (
    Building,
    BuildingsError,
    BuildingSpec,
    RoofPoints,
)
from penyal_pipeline.dem import Grid
from penyal_pipeline.paths import REPO_ROOT, TERRAIN_BUILD_DIR
from penyal_pipeline.rawdata import locate

type Floats = npt.NDArray[np.float64]

GROUND = 100.0
SLOPE = 0.1  # metres of height per metre eastwards
EAVE, RIDGE = 106.0, 108.0
needs_dem = build_marks(TERRAIN_BUILD_DIR / "dem.f32", TERRAIN_BUILD_DIR / "dem.json")
needs_optimizer = pytest.mark.skipif(
    shutil.which("node") is None
    or not (REPO_ROOT / "node_modules" / ".bin" / "gltf-transform").exists(),
    reason="node and `pnpm install` are needed to optimise GLBs",
)


def ramp_grid(slope: float = SLOPE) -> Grid:
    columns = np.arange(120, dtype=np.float64)
    heights = np.tile((GROUND + slope * columns).astype(np.float32), (120, 1))
    return Grid(heights, x0=0.0, z0=0.0, cell=1.0)


# an L-shaped hexagon like the centre building, in the grid's frame
L_SHAPE = np.array(
    [[10, 10], [40, 10], [40, 30], [30, 30], [30, 42], [10, 42], [10, 10]], dtype=np.float64
)
RECTANGLE = np.array([[10, 10], [40, 10], [40, 30], [10, 30], [10, 10]], dtype=np.float64)


def roof_points(
    footprint: Floats, eave: float = EAVE, ridge: float = RIDGE, bump: bool = False
) -> RoofPoints:
    """A deterministic lattice of class-6 points whose heights ramp from eave to ridge."""
    polygon = Polygon(footprint)
    x0, z0, x1, z1 = polygon.bounds
    gx, gz = np.meshgrid(np.arange(x0, x1, 1.3), np.arange(z0, z1, 1.3))
    inside = shapely.contains_xy(polygon, gx.ravel(), gz.ravel())
    x, z = gx.ravel()[inside], gz.ravel()[inside]
    across = np.clip((x - x0) / (x1 - x0), 0.0, 1.0)
    y = eave + (ridge - eave) * across
    if bump:
        near = (np.abs(x - 20.0) < 2.5) & (np.abs(z - 20.0) < 2.5)
        y = np.where(near, y + 3.0, y)
    return RoofPoints(x, z, y)


def build(footprint: Floats = L_SHAPE, bump: bool = False, eave: float = EAVE) -> Building:
    spec = BuildingSpec("test", "test building", 1)
    return buildings.build_building(
        spec, footprint, roof_points(footprint, eave=eave, bump=bump), ramp_grid()
    )


def face_normals(mesh: buildings.BuildingMesh) -> Floats:
    p = mesh.positions.astype(np.float64)
    t = mesh.triangles
    normal = np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]])
    return np.asarray(normal / np.linalg.norm(normal, axis=1)[:, None], dtype=np.float64)


class TestFootprint:
    @pytest.mark.parametrize("flip", [False, True])
    def test_edge_normals_point_out_whatever_the_winding(self, flip: bool) -> None:
        ring = buildings.orient_ring(L_SHAPE[::-1] if flip else L_SHAPE)
        polygon = Polygon(ring)
        mid = (ring + np.roll(ring, -1, axis=0)) / 2.0
        probes = mid + 0.05 * buildings.outward_normals(ring)
        assert not any(polygon.contains(shapely.Point(p)) for p in probes)

    def test_the_closing_node_is_dropped(self) -> None:
        assert len(buildings.orient_ring(L_SHAPE)) == 6

    def test_a_degenerate_footprint_is_rejected(self) -> None:
        with pytest.raises(BuildingsError):
            buildings.orient_ring(np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0], [0.0, 0.0]]))

    def test_the_eave_overhang_grows_the_outline_by_the_overhang(self) -> None:
        ring = buildings.orient_ring(RECTANGLE)
        grown = Polygon(buildings.offset_ring(ring, 0.5))
        assert grown.area == pytest.approx(31.0 * 21.0)


class TestRoofLevels:
    def test_eave_and_ridge_are_the_25th_and_95th_percentile(self) -> None:
        y = np.linspace(70.0, 80.0, 201)
        levels = buildings.roof_levels(RoofPoints(np.zeros(201), np.zeros(201), y))
        assert levels.eave == pytest.approx(72.5)
        assert levels.ridge == pytest.approx(79.5)
        assert levels.count == 201

    def test_too_few_points_are_rejected(self) -> None:
        with pytest.raises(BuildingsError):
            buildings.roof_levels(RoofPoints(np.zeros(5), np.zeros(5), np.ones(5)))


class TestTurrets:
    def test_a_bump_two_metres_over_the_roof_is_one_turret(self) -> None:
        points = roof_points(L_SHAPE, eave=EAVE, ridge=EAVE, bump=True)
        found, mask = buildings.detect_turrets(points, 0.0)
        assert len(found) == 1
        assert found[0].centre == pytest.approx((20.0, 20.0), abs=1.5)
        assert mask.sum() == found[0].points
        assert found[0].top_y == pytest.approx(EAVE + 3.0, abs=0.01)

    def test_a_plain_roof_has_none(self) -> None:
        found, mask = buildings.detect_turrets(roof_points(L_SHAPE), 0.0)
        assert found == []
        assert not mask.any()

    def test_the_turret_is_left_out_of_the_roof_levels(self) -> None:
        with_bump = build(bump=True)
        plain = build()
        assert len(with_bump.turrets) == 1
        assert with_bump.levels.ridge == pytest.approx(plain.levels.ridge, abs=0.2)


class TestMesh:
    def test_walls_start_at_the_lowest_ground_and_the_roof_tops_at_the_ridge(self) -> None:
        building = build()
        y = building.mesh.positions[:, 1]
        assert building.ground_min == pytest.approx(GROUND + SLOPE * 10.0, abs=1e-3)
        assert float(y.min()) == pytest.approx(building.base_y, abs=1e-3)
        assert building.base_y < building.ground_min
        assert float(y.max()) == pytest.approx(building.levels.ridge, abs=1e-3)

    def test_the_whitewash_stands_between_the_plinth_and_the_eave(self) -> None:
        mesh = build().mesh
        white = buildings.srgb_to_linear(buildings.COLOURS["whitewash"])
        is_white = np.all(np.isclose(mesh.colours, white, atol=1e-5), axis=1)
        assert is_white.any()
        assert float(mesh.positions[is_white, 1].max()) == pytest.approx(
            build().levels.eave, abs=1e-3
        )

    def test_every_vertex_has_a_linear_colour_and_a_unit_normal(self) -> None:
        mesh = build(bump=True).mesh
        assert mesh.colours.shape == mesh.positions.shape == mesh.normals.shape
        assert np.linalg.norm(mesh.normals, axis=1) == pytest.approx(1.0, abs=1e-5)
        assert mesh.triangles.max() == len(mesh.positions) - 1

    def test_wall_triangles_face_away_from_the_building(self) -> None:
        building = build()
        mesh = building.mesh
        polygon = Polygon(building.ring)
        normals = face_normals(mesh)
        triangles = mesh.positions.reshape(-1, 3, 3).astype(np.float64)
        eave = building.levels.eave
        vertical = np.abs(normals[:, 1]) < 1e-6
        walls = vertical & (triangles[:, :, 1].max(axis=1) <= eave + 1e-4)
        assert walls.any()
        for tri, normal in zip(triangles[walls], normals[walls], strict=True):
            middle = tri.mean(axis=0)[[0, 2]]
            probe = middle + 0.05 * normal[[0, 2]]
            assert not polygon.contains(shapely.Point(probe))

    def test_roof_and_cap_face_up(self) -> None:
        building = build()
        normals = face_normals(building.mesh)
        triangles = building.mesh.positions.reshape(-1, 3, 3)
        roof = triangles[:, :, 1].min(axis=1) >= building.levels.eave - 1e-4
        up = normals[roof & (triangles[:, :, 1].max(axis=1) > building.levels.eave + 1e-4), 1]
        assert up.size > 0
        assert (up > 0.0).all()

    def test_the_stone_follows_the_slope_up_the_wall(self) -> None:
        building = build()
        stone = buildings.srgb_to_linear(buildings.COLOURS["plinth"])
        is_stone = np.all(np.isclose(building.mesh.colours, stone, atol=1e-5), axis=1)
        tops = building.mesh.positions[is_stone, 1]
        assert float(tops.max()) == pytest.approx(
            float(ramp_grid().sample(40.0, 10.0)) + buildings.PLINTH_RISE, abs=0.35
        )

    def test_the_roof_model_follows_the_points_it_was_cut_from(self) -> None:
        building = build()
        assert building.fit["points"] == building.levels.count
        assert abs(building.fit["meanError"]) < 1.0
        assert building.fit["rmse"] < 1.5

    def test_it_stays_small(self) -> None:
        assert build(bump=True).mesh.triangles.shape[0] < 1000

    def test_building_twice_gives_the_same_arrays(self) -> None:
        first, second = build(bump=True).mesh, build(bump=True).mesh
        for name in ("positions", "normals", "colours", "triangles"):
            assert np.array_equal(getattr(first, name), getattr(second, name))

    def test_an_eave_under_the_ground_is_rejected(self) -> None:
        with pytest.raises(BuildingsError, match="eave"):
            build(eave=GROUND - 5.0)


class TestTurretMesh:
    def test_the_turret_adds_a_shaft_and_eight_merlons(self) -> None:
        plain, tower = build(), build(bump=True)
        assert len(tower.turrets) == 1
        # a shaft is 5 quads, a merlon 5 quads: (1 + 8) * 5 quads * 2 triangles
        assert tower.mesh.triangles.shape[0] - plain.mesh.triangles.shape[0] == (1 + 8) * 5 * 2

    def test_the_turret_rises_over_the_roof_and_sits_on_it(self) -> None:
        tower = build(bump=True)
        turret = tower.turrets[0]
        assert turret.base_y < turret.top_y - 1.5
        assert float(tower.mesh.positions[:, 1].max()) == pytest.approx(turret.top_y, abs=1e-3)


# --- GLB export ---------------------------------------------------------------------------------


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.slow
class TestExport:
    def test_the_glb_has_one_node_per_building_and_one_vertex_colour_material(
        self, tmp_path: Path
    ) -> None:
        from penyal_pipeline.blender import buildings as blender_buildings

        meshes = [build().mesh, build(RECTANGLE, bump=False).mesh]
        meshes = [
            buildings.BuildingMesh(m.positions, m.normals, m.colours, m.triangles, name)
            for m, name in zip(meshes, ("building_a", "building_b"), strict=True)
        ]
        out = blender_buildings.export_buildings(meshes, tmp_path / "buildings.glb")
        gltf, blob = read_glb(out)
        assert sorted(n["name"] for n in gltf["nodes"]) == ["building_a", "building_b"]
        assert "images" not in gltf
        assert [m["name"] for m in gltf["materials"]] == ["buildings_painted"]
        for mesh in gltf["meshes"]:
            assert len(mesh["primitives"]) == 1
            attributes = mesh["primitives"][0]["attributes"]
            assert "COLOR_0" in attributes
        colours = accessor(gltf, blob, gltf["meshes"][0]["primitives"][0]["attributes"]["COLOR_0"])
        assert colours.shape[0] == len(meshes[0].positions)

    def test_two_exports_are_byte_identical(self, tmp_path: Path) -> None:
        from penyal_pipeline.blender import buildings as blender_buildings

        meshes = [build(bump=True).mesh]
        first = blender_buildings.export_buildings(meshes, tmp_path / "a" / "b.glb")
        second = blender_buildings.export_buildings(meshes, tmp_path / "b" / "b.glb")
        assert sha256(first) == sha256(second)


# --- the real data -------------------------------------------------------------------------------

real_marks = [
    *raw_marks("osm-penyal/osm-penyal.json", "icv-lidar-2016-766-4282/*.laz"),
    *needs_dem,
]


@pytest.fixture(scope="module")
def real_points() -> dict[str, RoofPoints]:
    osm = trail.load_osm(locate(trail.OSM_SOURCE_ID, trail.OSM_FILE).path)
    lidar = locate(buildings.LIDAR_SOURCE_ID, ".laz").path
    return {
        spec.id: buildings.lidar_roof_points(lidar, Polygon(buildings.footprint_of(osm, spec.way)))
        for spec in buildings.SPECS
    }


@pytest.fixture(scope="module")
def real(real_points: dict[str, RoofPoints]) -> dict[str, Building]:
    osm = trail.load_osm(locate(trail.OSM_SOURCE_ID, trail.OSM_FILE).path)
    grid, _ = dem.load_dem()
    return {
        spec.id: buildings.build_building(
            spec, buildings.footprint_of(osm, spec.way), real_points[spec.id], grid
        )
        for spec in buildings.SPECS
    }


@pytest.mark.data
class TestRealBuildings:
    pytestmark: ClassVar = real_marks

    def test_the_footprints_are_the_osm_areas(self, real: dict[str, Building]) -> None:
        assert real["centre"].area == pytest.approx(651.0, abs=2.0)
        assert real["annex"].area == pytest.approx(483.0, abs=2.0)

    def test_the_lidar_has_roof_points_in_each_footprint(
        self, real_points: dict[str, RoofPoints]
    ) -> None:
        assert len(real_points["centre"].y) > 250
        assert len(real_points["annex"].y) > 150

    def test_eave_and_ridge_lie_inside_the_lidar_percentiles(
        self, real: dict[str, Building], real_points: dict[str, RoofPoints]
    ) -> None:
        for name, building in real.items():
            y = real_points[name].y
            low, median, high = (float(np.percentile(y, p)) for p in (5, 50, 100))
            assert low <= building.levels.eave <= median, name
            assert median <= building.levels.ridge <= high, name
            assert building.levels.ridge - building.levels.eave > 1.0, name

    def test_the_walls_clear_the_highest_ground(self, real: dict[str, Building]) -> None:
        for building in real.values():
            assert building.levels.eave > building.ground_max
            assert building.base_y < building.ground_min

    def test_only_the_centre_building_has_a_turret(self, real: dict[str, Building]) -> None:
        assert len(real["centre"].turrets) == 1
        assert real["annex"].turrets == []
        turret = real["centre"].turrets[0]
        assert Polygon(real["centre"].ring).contains(shapely.Point(turret.centre))
        assert 1.5 < turret.top_y - turret.base_y < 5.0

    def test_the_mesh_budget(self, real: dict[str, Building]) -> None:
        assert sum(b.mesh.triangles.shape[0] for b in real.values()) < 3000


@needs_optimizer
@pytest.mark.slow
@pytest.mark.data
class TestRun:
    pytestmark: ClassVar = real_marks

    def test_run_twice_writes_identical_files_and_a_provenance_block(self, tmp_path: Path) -> None:
        from penyal_pipeline import artefacts

        reports = []
        for name in ("first", "second"):
            out = tmp_path / name
            reports.append(
                buildings.run_buildings(
                    out, tmp_path / f"{name}-build", artefacts.provenance("buildings")
                )
            )
            assert sorted(p.name for p in out.iterdir()) == ["buildings.glb", "buildings.json"]
        for name in ("buildings.glb", "buildings.json"):
            assert sha256(tmp_path / "first" / name) == sha256(tmp_path / "second" / name)
        document = json.loads((tmp_path / "first" / "buildings.json").read_text(encoding="utf-8"))
        assert document["status"] == "approximate"
        assert [b["id"] for b in document["buildings"]] == ["centre", "annex"]
        assert {i.get("id") for i in document["inputs"]} >= {
            trail.OSM_SOURCE_ID,
            buildings.LIDAR_SOURCE_ID,
            dem.MDT_SOURCE_ID,
        }
        assert {"bpy", "laspy", "gltf-transform"} <= set(document["tools"])
        assert reports[0].triangles == sum(b["mesh"]["triangles"] for b in document["buildings"])
        assert (tmp_path / "first" / "buildings.glb").stat().st_size == reports[0].glb_bytes
