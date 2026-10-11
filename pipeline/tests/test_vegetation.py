"""Crown detection (E2.1), the NDVI check (E2.2) and the understory (E2.4)."""

import json
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import pytest
import rasterio
import shapely
from conftest import build_marks, raw_marks
from rasterio.transform import from_origin

from penyal_pipeline import dem, ortho, understory, vegetation
from penyal_pipeline.cellhash import hash_cells, unit_float
from penyal_pipeline.dem import Grid
from penyal_pipeline.geo import ORIGIN_E, ORIGIN_N
from penyal_pipeline.paths import TERRAIN_BUILD_DIR, TRAIL_GENERATED
from penyal_pipeline.vegetation import (
    Crowns,
    NdviRaster,
    VegetationError,
    VegetationPoints,
)

# --- synthetic helpers --------------------------------------------------------------------------


def flat_grid(height: float = 50.0) -> Grid:
    return Grid(np.full((200, 200), height, dtype=np.float32), x0=-100.0, z0=-100.0)


def points_of(cells: list[tuple[float, float, float]], lidar_class: int = 5) -> VegetationPoints:
    """One point per ``(x, z, height)``."""
    arr = np.array(cells, dtype=np.float64).reshape(-1, 3)
    return VegetationPoints(
        arr[:, 0], arr[:, 1], arr[:, 2], np.full(len(arr), lidar_class, dtype=np.uint8)
    )


def cone(cx: float, cz: float, top: float, slope: float = 1.5) -> list[tuple[float, float, float]]:
    """A cone of one point per metre cell: ``top`` at the centre, falling ``slope`` m per metre."""
    out = []
    for dx in range(-8, 9):
        for dz in range(-8, 9):
            h = top - slope * float(np.hypot(dx, dz))
            if h > 0.2:
                out.append((cx + dx, cz + dz, h))
    return out


# --- canopy height model and peaks --------------------------------------------------------------


def test_chm_keeps_the_highest_point_per_cell_centred_on_whole_metres() -> None:
    chm = vegetation.canopy_height_model(
        points_of([(10.4, 20.0, 3.0), (9.6, 20.4, 5.0), (11.0, 20.0, 4.0)])
    )
    assert (chm.ix0, chm.iz0) == (10, 20)
    assert chm.heights.shape == (1, 2)
    assert chm.heights[0].tolist() == [5.0, 4.0]
    values = chm.value_at(np.array([10.0, 11.4, 50.0]), np.array([20.0, 19.6, 20.0]))
    assert values[0] == 5.0
    assert values[1] == 4.0
    assert np.isnan(values[2])


def test_a_single_cone_is_one_crown_with_its_height_and_cell_centre() -> None:
    crowns = vegetation.detect_crowns(points_of(cone(5, -7, 8.0)), flat_grid())
    assert len(crowns) == 1
    assert (crowns.x[0], crowns.z[0]) == (5.0, -7.0)
    assert crowns.height[0] == 8.0
    assert crowns.y[0] == 50.0


def test_crowns_under_three_metres_are_ignored() -> None:
    assert len(vegetation.detect_crowns(points_of(cone(0, 0, 2.9)), flat_grid())) == 0
    assert len(vegetation.detect_crowns(points_of(cone(0, 0, 3.0)), flat_grid())) == 1


def test_a_lower_neighbour_inside_the_window_is_not_a_crown() -> None:
    near = [*cone(0, 0, 9.0), (2.0, 0.0, 8.9)]
    far = [*cone(0, 0, 9.0), (3.0, 0.0, 8.9)]
    assert len(vegetation.detect_crowns(points_of(near), flat_grid())) == 1
    assert len(vegetation.detect_crowns(points_of(far), flat_grid())) == 2


def test_equal_heights_inside_a_window_give_one_crown_the_first_in_raster_order() -> None:
    plateau = [(0.0, 0.0, 6.0), (1.0, 0.0, 6.0), (0.0, 1.0, 6.0)]
    crowns = vegetation.detect_crowns(points_of(plateau), flat_grid())
    assert len(crowns) == 1
    assert (crowns.x[0], crowns.z[0]) == (0.0, 0.0)


def test_height_is_measured_above_the_dem() -> None:
    sample = points_of([(0.0, 0.0, 4.0)])
    crowns = vegetation.detect_crowns(sample, flat_grid(20.0))
    assert crowns.height[0] == 4.0
    assert crowns.y[0] == 20.0


def test_radius_is_the_half_height_contour() -> None:
    chm = vegetation.canopy_height_model(points_of(cone(0, 0, 8.0, slope=1.0)))
    radius = vegetation.crown_radii(chm, np.array([0.0]), np.array([0.0]), np.array([8.0]))
    # the cone falls below half its height (4 m) at 4 m from the top
    assert radius[0] == pytest.approx(4.0, abs=0.5)


def test_radius_is_clamped_to_its_limits() -> None:
    lone = vegetation.canopy_height_model(points_of([(0.0, 0.0, 6.0)]))
    small = vegetation.crown_radii(lone, np.array([0.0]), np.array([0.0]), np.array([6.0]))
    assert small[0] == vegetation.MIN_CROWN_RADIUS
    plateau = vegetation.canopy_height_model(
        points_of([(float(x), float(z), 6.0) for x in range(-20, 21) for z in range(-20, 21)])
    )
    wide = vegetation.crown_radii(plateau, np.array([0.0]), np.array([0.0]), np.array([6.0]))
    assert wide[0] == vegetation.MAX_CROWN_RADIUS


def disc(
    radius: float, hole: tuple[float, float] | None = None
) -> list[tuple[float, float, float]]:
    """A flat 6 m crown of ``radius``; cells whose distance is within ``hole`` are missing."""
    out = []
    for x in range(-12, 13):
        for z in range(-12, 13):
            distance = float(np.hypot(x, z))
            if distance > radius or (hole and hole[0] <= distance <= hole[1]):
                continue
            out.append((float(x), float(z), 6.0))
    return out


def reach(points: list[tuple[float, float, float]]) -> float:
    chm = vegetation.canopy_height_model(points_of(points))
    radii = vegetation.crown_radii(chm, np.array([0.0]), np.array([0.0]), np.array([6.0]))
    return float(radii[0])


def test_the_radius_crosses_a_gap_of_empty_cells_but_not_a_wide_one() -> None:
    solid = reach(disc(5.0))
    assert solid == pytest.approx(5.0, abs=0.6)
    assert reach(disc(5.0, hole=(2.0, 2.4))) == pytest.approx(solid, abs=0.3)
    assert reach(disc(6.0, hole=(1.6, 4.6))) < solid - 1.0


def test_detection_is_independent_of_point_order() -> None:
    pts = cone(0, 0, 9.0) + cone(14, 3, 6.0)
    rng = np.random.default_rng(3)
    shuffled = [pts[i] for i in rng.permutation(len(pts))]
    a = vegetation.detect_crowns(points_of(pts), flat_grid())
    b = vegetation.detect_crowns(points_of(shuffled), flat_grid())
    assert np.array_equal(a.x, b.x)
    assert np.array_equal(a.z, b.z)
    assert np.array_equal(a.height, b.height)
    assert np.array_equal(a.radius, b.radius)


def test_the_cell_grid_does_not_depend_on_the_extent_of_the_points() -> None:
    pts = cone(0, 0, 9.0)
    alone = vegetation.detect_crowns(points_of(pts), flat_grid())
    with_far_point = vegetation.detect_crowns(points_of([*pts, (60.0, 60.0, 1.0)]), flat_grid())
    assert alone.x.tolist() == with_far_point.x.tolist()


# --- NDVI ---------------------------------------------------------------------------------------


def write_rgbi(path: Path, red: int, nir: int, size: int = 40, pixel: float = 0.25) -> Path:
    data = np.zeros((4, size, size), dtype=np.uint8)
    data[0], data[1], data[2], data[3] = red, 90, 60, nir
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=size,
        height=size,
        count=4,
        dtype="uint8",
        crs="EPSG:25830",
        transform=from_origin(ORIGIN_E + 10.0, ORIGIN_N + 10.0, pixel, pixel),
    ) as dst:
        dst.write(data)
    return path


def test_ndvi_uses_the_red_and_the_near_infrared_bands(tmp_path: Path) -> None:
    assert (vegetation.RED_BAND, vegetation.NIR_BAND) == (1, 4)
    path = write_rgbi(tmp_path / "o.tif", red=100, nir=200)
    with rasterio.open(path) as src:
        raster = vegetation.read_ndvi(src, (10.0, -10.0, 20.0, 0.0))
    assert raster.values.shape == (40, 40)
    assert np.allclose(raster.values, (200 - 100) / (200 + 100))
    assert (raster.x_min, raster.z_min, raster.res) == (10.0, -10.0, 0.25)


def test_ndvi_is_nan_where_both_bands_are_black(tmp_path: Path) -> None:
    path = write_rgbi(tmp_path / "o.tif", red=0, nir=0)
    with rasterio.open(path) as src:
        raster = vegetation.read_ndvi(src, (10.0, -10.0, 20.0, 0.0))
    assert np.isnan(raster.values).all()


def test_ndvi_needs_the_window_inside_the_image(tmp_path: Path) -> None:
    path = write_rgbi(tmp_path / "o.tif", red=100, nir=200)
    with rasterio.open(path) as src, pytest.raises(VegetationError, match="does not cover"):
        vegetation.read_ndvi(src, (500.0, 500.0, 510.0, 510.0))


def test_crown_ndvi_is_the_median_over_the_disk() -> None:
    values = np.full((40, 40), 0.1, dtype=np.float32)
    values[:, 20:] = 0.5  # right half, x >= 5 m
    raster = NdviRaster(values, x_min=0.0, z_min=0.0, res=0.25)
    crowns = Crowns(
        x=np.array([2.5, 7.5]),
        y=np.zeros(2),
        z=np.array([5.0, 5.0]),
        height=np.full(2, 6.0),
        radius=np.array([1.0, 1.0]),
    )
    ndvi = vegetation.crown_ndvi(raster, crowns)
    assert ndvi[0] == pytest.approx(0.1)
    assert ndvi[1] == pytest.approx(0.5)


def test_crown_ndvi_is_nan_outside_the_raster_and_such_crowns_are_kept() -> None:
    raster = NdviRaster(np.full((8, 8), 0.4, dtype=np.float32), 0.0, 0.0, 0.25)
    crowns = Crowns(
        np.array([100.0]), np.zeros(1), np.array([100.0]), np.array([5.0]), np.array([1.0])
    )
    ndvi = vegetation.crown_ndvi(raster, crowns)
    assert np.isnan(ndvi[0])
    assert vegetation.present_mask(ndvi, 0.07).tolist() == [True]


def test_present_mask_cuts_at_the_threshold() -> None:
    ndvi = np.array([0.0, 0.069, 0.07, 0.3])
    assert vegetation.present_mask(ndvi, 0.07).tolist() == [False, False, True, True]


# --- hashing ------------------------------------------------------------------------------------


def test_cell_hash_is_stable_and_order_independent() -> None:
    ix = np.arange(-50, 50, dtype=np.int64)
    iz = ix * 3
    forward = hash_cells(ix, iz, 7)
    backward = hash_cells(ix[::-1], iz[::-1], 7)[::-1]
    assert np.array_equal(forward, backward)
    assert (
        hash_cells(np.array([5]), np.array([9]), 7)[0]
        == hash_cells(np.array([5]), np.array([9]), 7)[0]
    )
    assert not np.array_equal(forward, hash_cells(ix, iz, 8))


def test_unit_float_is_in_range_and_roughly_uniform() -> None:
    ix, iz = np.meshgrid(np.arange(200, dtype=np.int64), np.arange(200, dtype=np.int64))
    values = unit_float(hash_cells(ix.ravel(), iz.ravel(), 1))
    assert values.min() >= 0.0
    assert values.max() < 1.0
    assert abs(values.mean() - 0.5) < 0.01


# --- understory ---------------------------------------------------------------------------------


def understory_points(count_per_cell: int, height: float, cells: int = 12) -> VegetationPoints:
    pts = []
    for i in range(cells):
        for j in range(cells):
            for k in range(count_per_cell):
                pts.append((i * 4 + 0.3 + 0.2 * k, j * 4 + 1.0, height))
    return points_of(pts, lidar_class=4)


def test_models_follow_the_median_height() -> None:
    assert understory.model_for(1.5) == understory.TALL
    assert understory.model_for(0.7) == understory.LOW
    assert understory.model_for(0.1) == understory.GRASS


def test_cells_with_more_points_get_more_instances() -> None:
    sparse = understory.candidates(understory.summarise_cells(understory_points(1, 0.8)))
    dense = understory.candidates(understory.summarise_cells(understory_points(14, 0.8)))
    assert len(dense["x"]) == 2 * 12 * 12
    assert 0 < len(sparse["x"]) < len(dense["x"]) / 2


def test_candidates_stay_inside_their_cell_and_are_reproducible() -> None:
    cells = understory.summarise_cells(understory_points(8, 0.8))
    a, b = understory.candidates(cells), understory.candidates(cells)
    for key in a:
        assert np.array_equal(a[key], b[key])
    assert (a["x"] >= 0).all()
    assert (a["x"] <= 12 * understory.CELL).all()
    assert set(np.unique(a["keep"])) <= set(range(100))
    assert a["height"].min() >= understory.MIN_HEIGHT
    assert a["height"].max() <= understory.MAX_HEIGHT


def test_a_cell_gets_the_same_instances_whichever_cells_surround_it() -> None:
    alone = understory.candidates(understory.summarise_cells(understory_points(8, 0.8, cells=1)))
    among = understory.candidates(understory.summarise_cells(understory_points(8, 0.8, cells=6)))
    in_cell = (among["x"] < understory.CELL) & (among["z"] < understory.CELL)
    first = np.sort(among["x"][in_cell])
    assert np.array_equal(np.sort(alone["x"]), first)


def test_place_keeps_out_of_the_exclusion_zone_and_outside_the_area() -> None:
    points = understory_points(14, 0.8)
    area = shapely.box(0, 0, 48, 48).difference(shapely.box(40, 0, 48, 48))
    exclusion = shapely.box(0, 0, 20, 48)
    doc = understory.instances(points, flat_grid(), area, exclusion)
    x = np.array(doc["x"])
    assert doc["count"] == len(x) > 0
    assert (x >= 20).all()
    assert (x <= 40).all()
    assert understory.protected_species_in(doc) == []


# --- data ---------------------------------------------------------------------------------------

DATA_PATTERNS = (
    "osm-penyal/osm-penyal.json",
    "icv-mdt-2016-0848/*.tif",
    "icv-orto-2024-0848-7-2/*.tif",
    "icv-lidar-2016-766-4282/*.laz",
    "icv-lidar-2016-768-4282/*.laz",
    "polyhaven-shrub-04-gltf-1k/*.gltf",
    "polyhaven-shrub-02-gltf-1k/*.gltf",
    "polyhaven-grass-medium-02-gltf-1k/*.gltf",
)


@pytest.fixture(scope="module")
def found() -> vegetation.Detection:
    return vegetation.detect()


class TestWithData:
    pytestmark: ClassVar = [
        *raw_marks(*DATA_PATTERNS),
        *build_marks(TERRAIN_BUILD_DIR / "dem.f32", TRAIL_GENERATED),
    ]

    def test_the_pilot_band_reproduces_the_research_figure(
        self, found: vegetation.Detection
    ) -> None:
        assert found.pilot_reference == vegetation.PILOT_REFERENCE_CROWNS == 186

    def test_the_park_run_has_one_crown_fewer_in_the_band(
        self, found: vegetation.Detection
    ) -> None:
        assert found.pilot_park == vegetation.PILOT_PARK_CROWNS == 185

    def test_the_pilot_crowns_have_the_measured_heights(self, found: vegetation.Detection) -> None:
        band = vegetation.pilot_band(found.route)
        heights = found.crowns.height[vegetation.crowns_in(found.crowns, band)]
        assert np.median(heights) == pytest.approx(6.0, abs=0.1)
        assert np.percentile(heights, 90) == pytest.approx(8.0, abs=0.1)
        assert heights.max() == pytest.approx(10.8, abs=0.1)

    def test_crowns_are_inside_the_area_and_plausible(self, found: vegetation.Detection) -> None:
        assert vegetation.crowns_in(found.crowns, found.area).all()
        assert found.crowns.height.min() >= vegetation.MIN_CROWN_HEIGHT
        assert found.crowns.height.max() <= vegetation.MAX_CROWN_HEIGHT
        assert found.crowns.radius.min() >= vegetation.MIN_CROWN_RADIUS
        assert found.crowns.radius.max() <= vegetation.MAX_CROWN_RADIUS

    def test_the_ndvi_check_excludes_some_crowns_and_keeps_most(
        self, found: vegetation.Detection
    ) -> None:
        assert not np.isnan(found.ndvi).any()
        excluded = int((~found.kept).sum())
        assert 0 < excluded < len(found.crowns) / 5
        assert found.ndvi[~found.kept].max() < vegetation.NDVI_ABSENT_THRESHOLD
        assert found.ndvi[found.kept].min() >= vegetation.NDVI_ABSENT_THRESHOLD

    def test_the_document_is_complete_and_has_no_protected_species(
        self, found: vegetation.Detection
    ) -> None:
        exclusion = understory.exclusion_zone(found.osm, TRAIL_GENERATED)
        shrubs = understory.place(found.points, found.grid, found.area, exclusion)
        doc = vegetation.document(found, shrubs, vegetation.NDVI_ABSENT_THRESHOLD)
        crowns = doc["crowns"]
        assert doc["counts"]["crownsKept"] == crowns["count"] == len(crowns["x"])
        assert len(crowns["variant"]) == len(crowns["yaw"]) == crowns["count"]
        assert set(crowns["variant"]) <= set(range(doc["variants"]))
        assert doc["counts"]["crownsDetected"] == (
            crowns["count"] + doc["absentCrowns"]["count"] + doc["counts"]["crownsTooTall"]
        )
        assert understory.protected_species_in(doc) == []
        assert json.loads(json.dumps(doc)) == doc

    def test_no_understory_on_the_corridor_nor_on_buildings(
        self, found: vegetation.Detection
    ) -> None:
        exclusion = understory.exclusion_zone(found.osm, TRAIL_GENERATED)
        shrubs = understory.place(found.points, found.grid, found.area, exclusion)
        assert shrubs["count"] > 1000
        x, z = np.array(shrubs["x"]), np.array(shrubs["z"])
        corridor = shapely.Polygon(
            json.loads(TRAIL_GENERATED.read_text(encoding="utf-8"))["corridor"]["polygon"]
        )
        assert not shapely.contains_xy(corridor, x, z).any()
        assert set(shrubs["model"]) <= set(range(len(understory.MODELS)))
        assert [m["id"] for m in shrubs["models"]] == ["shrub_04", "shrub_02", "grass_medium_02"]

    def test_the_understory_is_reproducible(self, found: vegetation.Detection) -> None:
        exclusion = understory.exclusion_zone(found.osm, TRAIL_GENERATED)
        first = understory.place(found.points, found.grid, found.area, exclusion)
        second = understory.place(found.points, found.grid, found.area, exclusion)
        assert first == second

    def test_the_ortho_has_the_bands_the_ndvi_reads(self) -> None:
        with ortho.open_ortho(ortho.locate_ortho().path) as src:
            assert src.count >= vegetation.NIR_BAND
            assert src.crs.to_epsg() == dem.EPSG


def test_crown_columns_are_json_friendly_and_missing_ndvi_is_null() -> None:
    sample: dict[str, Any] = vegetation.crown_columns(
        Crowns(np.array([1.0]), np.array([2.0]), np.array([3.0]), np.array([5.0]), np.array([1.0])),
        np.array([np.nan]),
    )
    assert sample["ndvi"] == [None]
    assert sample["count"] == 1
    assert json.dumps(sample)
