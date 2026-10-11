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
from shapely.geometry.base import BaseGeometry

from penyal_pipeline import dem, ortho, provenance, trail, understory, vegetation
from penyal_pipeline.cellhash import hash_cells, unit_float
from penyal_pipeline.dem import Grid
from penyal_pipeline.geo import ORIGIN_E, ORIGIN_N
from penyal_pipeline.paths import REPO_ROOT, TERRAIN_BUILD_DIR, TRAIL_GENERATED
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
)


@pytest.fixture(scope="module")
def found() -> vegetation.Detection:
    return vegetation.detect()


class TestWithData:
    pytestmark: ClassVar = [
        *raw_marks(*DATA_PATTERNS),
        *build_marks(TERRAIN_BUILD_DIR / "dem.f32", TRAIL_GENERATED),
    ]

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
        assert 0 < int(found.absent.sum()) < len(found.crowns) / 5
        assert found.ndvi[found.absent].max() < vegetation.NDVI_ABSENT_THRESHOLD
        assert found.ndvi[~found.absent].min() >= vegetation.NDVI_ABSENT_THRESHOLD

    def test_no_kept_crown_is_a_cliff_artefact(self, found: vegetation.Detection) -> None:
        kept = found.kept
        on_cliff = found.slope >= vegetation.CLIFF_SLOPE
        assert int((on_cliff & found.cliff).sum()) > 50
        assert not (kept & on_cliff & (found.crowns.radius <= vegetation.MIN_CROWN_RADIUS)).any()
        assert not (kept & on_cliff & (found.ndvi < vegetation.CLIFF_MIN_NDVI)).any()
        assert int(found.cliff.sum()) == int((found.cliff & on_cliff).sum())

    def test_no_trunk_foot_is_on_the_walkable_corridor_or_near_the_path_axis(
        self, found: vegetation.Detection
    ) -> None:
        document = json.loads(TRAIL_GENERATED.read_text(encoding="utf-8"))
        corridor = vegetation.surface_corridor(document)
        x, z = found.feet.x[found.kept], found.feet.z[found.kept]
        assert not shapely.contains_xy(corridor, x, z).any()
        axis = shapely.MultiLineString(
            [
                [(p[0], p[2]) for p in s["points"]]
                for s in document["route"]["segments"]
                if s["id"] != "tunnel"
            ]
        )  # trees may stand over the tunnel, not over the path on the surface
        assert shapely.distance(shapely.points(x, z), axis).min() >= 3.0
        apex_x, apex_z = found.crowns.x[found.kept], found.crowns.z[found.kept]
        lean = np.hypot(apex_x - x, apex_z - z)
        assert 5 < int((lean > 0).sum()) < len(x) / 5  # some trunks moved, most did not
        assert (
            lean <= vegetation.MAX_LEAN_PER_HEIGHT * found.crowns.height[found.kept] + 1e-6
        ).all()

    def test_a_moved_trunk_keeps_the_crown_at_its_measured_elevation(
        self, found: vegetation.Detection
    ) -> None:
        kept = found.kept
        crowns = found.crowns.select(kept)
        vertical = found.vertical
        moved = (found.feet.x[kept] != crowns.x) | (found.feet.z[kept] != crowns.z)
        assert int(moved.sum()) > 5
        foot_y, apex_y = vertical.foot_y[kept], vertical.apex_y[kept]
        assert np.allclose(apex_y, crowns.y + crowns.height)  # the measured top, moved or not
        assert (np.abs(foot_y - crowns.y)[moved] <= vegetation.MAX_FOOT_DROP + 1e-6).all()
        assert (apex_y - foot_y).min() >= vegetation.MIN_CROWN_HEIGHT
        slope = dem.slope_at(
            dem.slope_degrees(found.grid), found.grid, found.feet.x[kept], found.feet.z[kept]
        )
        assert not (moved & (slope >= vegetation.CLIFF_SLOPE)).any()

    def test_the_pine_is_never_stretched_more_than_the_ratio(
        self, found: vegetation.Detection
    ) -> None:
        crowns = found.crowns.select(found.kept)
        vertical, horizontal = vegetation.instance_scale(crowns.height, crowns.radius)
        ratio = horizontal / vertical
        assert ratio.min() >= vegetation.SCALE_RATIO[0] - 1e-9
        assert ratio.max() <= vegetation.SCALE_RATIO[1] + 1e-9

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
            crowns["count"] + doc["droppedCrowns"]["count"] + doc["counts"]["crownsTooTall"]
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
        assert [m["id"] for m in shrubs["models"]] == ["lentisc", "rosemary", "grass"]

    def test_no_understory_stands_on_a_cliff_in_the_silene_band(
        self, found: vegetation.Detection
    ) -> None:
        exclusion = understory.exclusion_zone(found.osm, TRAIL_GENERATED)
        shrubs = understory.place(found.points, found.grid, found.area, exclusion)
        x, z, y = (np.array(shrubs[k]) for k in ("x", "z", "y"))
        slope = dem.slope_at(dem.slope_degrees(found.grid), found.grid, x, z)
        low, high = understory.SILENE_BAND
        in_band = (y >= low) & (y <= high)
        assert not (in_band & (slope >= understory.SILENE_CLIFF_SLOPE)).any()
        assert int(in_band.sum()) > 1000  # the rule removes the cliffs, not the band

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
        np.array([12.0]),
    )
    assert sample["ndvi"] == [None]
    assert sample["count"] == 1
    assert json.dumps(sample)


# --- cliff rule ---------------------------------------------------------------------------------


def crowns_with(radius: list[float]) -> Crowns:
    n = len(radius)
    return Crowns(
        x=np.arange(n, dtype=np.float64) * 10.0,
        y=np.zeros(n),
        z=np.zeros(n),
        height=np.full(n, 6.0),
        radius=np.array(radius),
    )


def test_on_a_cliff_a_crown_needs_more_than_the_minimum_radius_and_a_vegetation_ndvi() -> None:
    crowns = crowns_with([0.75, 2.0, 2.0, 0.75, 2.0])
    slope = np.array([70.0, 70.0, 70.0, 30.0, 59.9])
    ndvi = np.array([0.5, 0.1, 0.3, 0.1, 0.1])
    keep = vegetation.cliff_keep(crowns, slope, ndvi)
    # min radius on a cliff, bare on a cliff, fine on a cliff, any crown off a cliff, just under 60
    assert keep.tolist() == [False, False, True, True, True]


def test_a_cliff_crown_without_a_measured_ndvi_is_dropped() -> None:
    crowns = crowns_with([2.0])
    keep = vegetation.cliff_keep(crowns, np.array([80.0]), np.array([np.nan]))
    assert keep.tolist() == [False]


# --- NDVI sampling ------------------------------------------------------------------------------


def write_half_nir(path: Path) -> Path:
    """4 x 4 m image over local x 10..14, z -10..-6 (north up): near infrared high only in the
    north half (z -10..-8), equal to red in the south half."""
    size = 16
    data = np.zeros((4, size, size), dtype=np.uint8)
    data[0] = 100
    data[3] = 100
    data[3, : size // 2, :] = 200
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=size,
        height=size,
        count=4,
        dtype="uint8",
        crs="EPSG:25830",
        transform=from_origin(ORIGIN_E + 10.0, ORIGIN_N + 10.0, 0.25, 0.25),
    ) as dst:
        dst.write(data)
    return path


def test_ndvi_is_high_in_the_north_half_and_low_in_the_south_half(
    tmp_path: Path,
) -> None:
    path = write_half_nir(tmp_path / "half.tif")
    with rasterio.open(path) as src:
        raster = vegetation.read_ndvi(src, (10.0, -10.0, 14.0, -6.0))
    crowns = Crowns(
        x=np.array([12.0, 12.0]),
        y=np.zeros(2),
        z=np.array([-9.0, -6.5]),  # z grows southwards: -9 is the north half
        height=np.full(2, 6.0),
        radius=np.array([1.5, 1.5]),
    )
    ndvi = vegetation.crown_ndvi(raster, crowns)
    assert ndvi[0] == pytest.approx(1.0 / 3.0)
    assert ndvi[1] == pytest.approx(0.0, abs=0.05)


def test_a_small_crown_whose_apex_is_shifted_off_its_canopy_is_still_measured() -> None:
    """The orthophoto is rectified on the terrain, so a tall crown's apex lands about a metre
    away from its canopy: the apex disk of a 0.75 m crown can be bare while the tree is there."""
    values = np.zeros((80, 80), dtype=np.float32)  # 20 x 20 m at 0.25 m
    values[:, 42:] = 0.4  # green from x = 10.5 m east
    raster = NdviRaster(values, x_min=0.0, z_min=0.0, res=0.25)
    crowns = Crowns(
        x=np.array([10.0]),
        y=np.zeros(1),
        z=np.array([10.0]),
        height=np.full(1, 5.0),
        radius=np.array([0.75]),
    )
    assert vegetation.crown_ndvi(raster, crowns)[0] == pytest.approx(0.4)
    far = Crowns(
        x=np.array([8.0]),
        y=np.zeros(1),
        z=np.array([10.0]),
        height=np.full(1, 5.0),
        radius=np.array([0.75]),
    )
    assert vegetation.crown_ndvi(raster, far)[0] == pytest.approx(0.0)


# --- trunk feet ---------------------------------------------------------------------------------

PATH_CORRIDOR = shapely.box(-20.0, -3.0, 20.0, 3.0)  # ADR 0006: 3 m each side of a path along x


def test_a_trunk_foot_leaves_the_corridor_and_leans_towards_the_apex() -> None:
    feet = vegetation.place_feet(
        np.array([0.0, 5.0, 8.0]),
        np.array([0.5, -1.0, 9.0]),
        np.array([8.0, 8.0, 8.0]),
        PATH_CORRIDOR,
    )
    assert feet.ok.tolist() == [True, True, True]
    assert (feet.x[2], feet.z[2]) == (
        8.0,
        9.0,
    )  # outside the corridor: the apex is the foot
    assert not shapely.contains_xy(PATH_CORRIDOR, feet.x, feet.z).any()
    margin = vegetation.FOOT_MARGIN
    assert feet.z[0] >= 3.0 + margin  # nearest side of the apex at z = 0.5 is the south
    assert feet.z[1] <= -3.0 - margin  # and for z = -1 the north side
    lean = np.hypot(feet.x - np.array([0.0, 5.0, 8.0]), feet.z - np.array([0.5, -1.0, 9.0]))
    assert lean[0] < 4.0
    assert lean[2] == 0.0


def test_a_crown_too_short_to_lean_out_of_the_corridor_is_blocked() -> None:
    feet = vegetation.place_feet(
        np.array([0.0, 0.0]), np.array([0.0, 0.0]), np.array([4.0, 8.0]), PATH_CORRIDOR
    )
    # 3.5 m from the centre to the clear ground: a 4 m tree cannot lean that far, an 8 m one can
    assert feet.ok.tolist() == [False, True]


# --- instance scale -----------------------------------------------------------------------------


def test_the_horizontal_scale_follows_the_radius_within_a_band_of_the_vertical_one() -> None:
    height = np.array([10.0, 5.0, 4.0, 8.0])
    radius = np.array([3.2, 0.75, 6.0, 3.2])
    vertical, horizontal = vegetation.instance_scale(height, radius)
    assert vertical == pytest.approx([1.0, 0.5, 0.4, 0.8])
    assert horizontal[0] == pytest.approx(1.0)  # radius and height as modelled
    assert horizontal[1] == pytest.approx(0.6 * 0.5)  # a thin crown is not squeezed past 0.6
    assert horizontal[2] == pytest.approx(1.6 * 0.4)  # nor a wide one stretched past 1.6
    assert horizontal[3] == pytest.approx(1.0)  # 3.2 / 3.2 lies inside [0.48, 1.28]


def test_the_crown_columns_carry_the_clamped_scale() -> None:
    crowns = Crowns(
        np.array([1.0, 2.0]),
        np.zeros(2),
        np.array([1.0, 2.0]),
        np.array([5.0, 10.0]),
        np.array([0.75, 3.2]),
    )
    columns = vegetation.crown_columns(crowns, np.array([0.3, 0.3]), np.array([10.0, 10.0]))
    assert columns["scaleXZ"] == [0.3, 1.0]


# --- no understory on the cliffs of the Silene band ---------------------------------------------


def ramp_grid(base: float, rise_per_metre: float) -> Grid:
    """A 200 x 200 m grid: flat at ``base`` for x < 0, rising ``rise_per_metre`` for x >= 0."""
    x = np.arange(200, dtype=np.float64) - 100.0
    row = base + np.maximum(x, 0.0) * rise_per_metre
    return Grid(np.tile(row.astype(np.float32), (200, 1)), x0=-100.0, z0=-100.0)


def understory_on_both_sides() -> VegetationPoints:
    pts = [
        (float(x) + 0.5, float(z) + 0.5, 0.8)
        for x in range(-40, 40, 4)
        for z in range(-40, 40, 4)
        for _ in range(7)
    ]
    return points_of(pts, lidar_class=4)


def instances_of(grid: Grid) -> dict[str, Any]:
    area = shapely.box(-100, -100, 100, 100)
    return understory.instances(understory_on_both_sides(), grid, area, shapely.Point(500, 500))


def test_no_understory_on_a_cliff_inside_the_silene_elevation_band() -> None:
    doc = instances_of(ramp_grid(base=100.0, rise_per_metre=2.0))  # 63 degrees at 100-180 m
    x = np.array(doc["x"])
    assert len(x) > 100
    assert (x < 1.0).all()  # the ramp starts at x = 0 and the cell centre smears it by a metre


def test_cliff_understory_stays_outside_the_band_and_below_the_slope_threshold() -> None:
    below = instances_of(ramp_grid(base=5.0, rise_per_metre=1.0))  # steep, but under 60 m
    assert (np.array(below["x"]) >= 0).any()
    gentle = instances_of(ramp_grid(base=100.0, rise_per_metre=1.0))  # 45 degrees: under 50
    assert (np.array(gentle["x"]) >= 0).any()


# --- exclusion zone and the OSM boundary --------------------------------------------------------


def osm_with(ways: dict[int, trail.Way], nodes: dict[int, tuple[float, float]]) -> trail.OsmData:
    return trail.OsmData(xz=nodes, node_tags={}, ways=ways)


def corridor_file(tmp_path: Path) -> Path:
    path = tmp_path / "trail.json"
    ring = [[-30.0, 20.0], [-10.0, 20.0], [-10.0, 30.0], [-30.0, 30.0], [-30.0, 20.0]]
    path.write_text(json.dumps({"corridor": {"polygon": ring}}), encoding="utf-8")
    return path


def zone_of(tmp_path: Path) -> shapely.geometry.base.BaseGeometry:
    nodes = {
        1: (0.0, 0.0),
        2: (100.0, 0.0),  # a footpath along x
        3: (0.0, 50.0),
        4: (100.0, 50.0),  # a residential street
        5: (20.0, 70.0),
        6: (30.0, 70.0),
        7: (30.0, 80.0),
        8: (20.0, 80.0),  # a building
        9: (500.0, 500.0),
    }
    ways = {
        10: trail.Way((1, 2), {"highway": "path"}),
        11: trail.Way((3, 4), {"highway": "residential"}),
        12: trail.Way((5, 6, 7, 8, 5), {"building": "yes"}),
        13: trail.Way((1, 99), {"highway": "path"}),  # node 99 is not in the extract
    }
    return understory.exclusion_zone(osm_with(ways, nodes), corridor_file(tmp_path))


def inside(zone: shapely.geometry.base.BaseGeometry, x: float, z: float) -> bool:
    return bool(shapely.contains_xy(zone, x, z))


def test_footpaths_keep_the_understory_off_by_the_footpath_clearance(
    tmp_path: Path,
) -> None:
    zone = zone_of(tmp_path)
    assert inside(zone, 50.0, understory.FOOTPATH_CLEARANCE - 0.1)
    assert not inside(zone, 50.0, understory.FOOTPATH_CLEARANCE + 0.1)


def test_roads_keep_the_understory_off_by_the_road_clearance(tmp_path: Path) -> None:
    zone = zone_of(tmp_path)
    assert inside(zone, 50.0, 50.0 + understory.ROAD_CLEARANCE - 0.1)
    assert not inside(zone, 50.0, 50.0 + understory.ROAD_CLEARANCE + 0.1)


def test_buildings_and_their_clearance_are_excluded(tmp_path: Path) -> None:
    zone = zone_of(tmp_path)
    assert inside(zone, 25.0, 75.0)
    assert inside(zone, 30.0 + understory.BUILDING_CLEARANCE - 0.1, 75.0)
    assert not inside(zone, 30.0 + understory.BUILDING_CLEARANCE + 0.1, 75.0)


def test_the_corridor_is_excluded_with_its_clearance(tmp_path: Path) -> None:
    zone = zone_of(tmp_path)
    assert inside(zone, -20.0, 25.0)
    assert inside(zone, -10.0 + understory.CORRIDOR_CLEARANCE - 0.05, 25.0)
    assert not inside(zone, -10.0 + understory.CORRIDOR_CLEARANCE + 0.05, 25.0)


def test_a_way_with_a_node_missing_from_the_extract_is_skipped_not_fatal(
    tmp_path: Path,
) -> None:
    zone = zone_of(tmp_path)  # way 13 lists node 99, which is absent: it must not raise
    assert inside(zone, 50.0, 0.0)  # the other footpath still counts


def reserve_osm(tmp_path: Path) -> tuple[Path, trail.OsmData]:
    path = tmp_path / "osm.json"
    relation = {
        "type": "relation",
        "id": vegetation.RESERVE_RELATION,
        "members": [
            {"type": "way", "ref": 1, "role": "outer"},
            {"type": "way", "ref": 2, "role": "outer"},
        ],
    }
    path.write_text(json.dumps({"elements": [relation]}), encoding="utf-8")
    nodes = {1: (0.0, 0.0), 2: (10.0, 0.0), 3: (10.0, 10.0), 4: (0.0, 10.0)}
    ways = {1: trail.Way((1, 2, 3), {}), 2: trail.Way((3, 4, 1), {})}
    return path, osm_with(ways, nodes)


def test_the_reserve_polygon_closes_from_its_outer_ways(tmp_path: Path) -> None:
    path, osm = reserve_osm(tmp_path)
    assert vegetation.reserve_polygon(path, osm).area == pytest.approx(100.0)


def test_a_reserve_way_with_a_node_missing_is_a_clear_error_not_a_key_error(
    tmp_path: Path,
) -> None:
    path, osm = reserve_osm(tmp_path)
    broken = osm_with(osm.ways, {k: v for k, v in osm.xz.items() if k != 2})
    with pytest.raises(VegetationError, match="node 2"):
        vegetation.reserve_polygon(path, broken)


# --- point and crown filters --------------------------------------------------------------------


def test_crowns_taller_than_the_limit_are_not_plausible() -> None:
    height = np.array([3.0, vegetation.MAX_CROWN_HEIGHT, vegetation.MAX_CROWN_HEIGHT + 0.01, 94.0])
    crowns = Crowns(np.zeros(4), np.zeros(4), np.zeros(4), height, np.ones(4))
    assert vegetation.plausible(crowns).tolist() == [True, True, False, False]


def write_las(path: Path, rows: list[tuple[float, float, float, int]]) -> Path:
    """A LAS file with one point per ``(easting offset, northing offset, z, class)``."""
    import laspy

    header = laspy.LasHeader(point_format=3, version="1.2")
    header.scales = np.array([0.01, 0.01, 0.01])
    header.offsets = np.array([ORIGIN_E, ORIGIN_N, 0.0])
    las = laspy.LasData(header)
    las.x = np.array([ORIGIN_E + r[0] for r in rows])
    las.y = np.array([ORIGIN_N - r[1] for r in rows])  # local z grows southwards
    las.z = np.array([r[2] for r in rows])
    las.classification = np.array([r[3] for r in rows], dtype=np.uint8)
    las.write(str(path))
    return path


def test_only_usable_vegetation_points_survive_the_reader(tmp_path: Path) -> None:
    heights = np.full((200, 200), 50.0, dtype=np.float32)
    heights[:, :100] = 0.2  # the west half is at sea level: boats, masts, sea clutter
    grid = Grid(heights, x0=-100.0, z0=-100.0)
    rows = [
        (20.0, 0.0, 58.0, 5),  # good: 8 m above 50 m ground
        (21.0, 0.0, 58.0, 2),  # ground class: not vegetation
        (22.0, 0.0, 49.0, 5),  # below the DEM
        (-20.0, 0.0, 12.0, 5),  # over the sea (ground 0.2 m)
        (23.0, 0.0, 400.0, 5),  # above the noise range
        (500.0, 0.0, 58.0, 5),  # outside the bounds
    ]
    las = write_las(tmp_path / "t.las", rows)
    points = vegetation.read_vegetation_points([las], (-90.0, -90.0, 90.0, 90.0), grid)
    assert points.x.size == 1
    assert points.height[0] == pytest.approx(8.0, abs=0.01)
    assert points.lidar_class.tolist() == [5]


# --- reproducibility ----------------------------------------------------------------------------


def test_the_cell_hash_and_the_variant_and_yaw_of_a_known_cell_are_pinned() -> None:
    """Pinned so a numpy or platform change cannot silently move every tree."""
    assert int(hash_cells(np.array([5]), np.array([9]), 1)[0]) == 9336431854891424590
    assert int(hash_cells(np.array([-3]), np.array([7]), 2)[0]) == 13009522658322218369
    crowns = Crowns(
        np.array([5.0, -3.0]),
        np.zeros(2),
        np.array([9.0, 7.0]),
        np.array([6.0, 6.0]),
        np.array([2.0, 2.0]),
    )
    columns = vegetation.crown_columns(crowns, np.array([0.3, 0.3]), np.array([5.0, 5.0]))
    assert columns["variant"] == [2, 0]
    assert columns["yaw"] == [54, 253]


def test_keep_values_thin_the_understory_in_nested_subsets() -> None:
    points = points_of(
        [
            (float(x) + 0.5, float(z) + 0.5, 0.8)
            for x in range(-96, 96, 4)
            for z in range(-96, 96, 4)
            for _ in range(14)
        ],
        lidar_class=4,
    )
    area = shapely.box(-100, -100, 100, 100)
    keep = np.array(
        understory.instances(points, flat_grid(), area, shapely.Point(500, 500))["keep"]
    )
    low, high = keep < 35, keep < 70
    assert (low <= high).all()  # what a low tier draws, a high tier draws too
    assert low.mean() == pytest.approx(0.35, abs=0.03)
    assert high.mean() == pytest.approx(0.70, abs=0.03)


# --- the research prototype's pilot figure, as properties of the algorithm ----------------------

PILOT_FIXTURE = REPO_ROOT / "fixtures" / "vegetation" / "pilot-crowns.json"
PILOT_REFERENCE_CROWNS = 186  # docs/research/003-inventario-datos-propios.md section 4
PILOT_PARK_CROWNS = 185


def pilot_reference_crowns(points: VegetationPoints, grid: Grid, band: BaseGeometry) -> Crowns:
    """What the research prototype did: the points inside the bounding box of the band are cut
    out first, then the crowns inside the band are kept. The cut leaves the window edge without
    neighbours, which is why a run over the whole park finds one crown fewer."""
    x_min, z_min, x_max, z_max = band.bounds
    window = (points.x >= x_min) & (points.x <= x_max) & (points.z >= z_min) & (points.z <= z_max)
    crowns = vegetation.detect_crowns(vegetation.select_points(points, window), grid)
    return crowns.select(vegetation.crowns_in(crowns, band))


@pytest.fixture(scope="module")
def reference(found: vegetation.Detection) -> Crowns:
    return pilot_reference_crowns(found.points, found.grid, vegetation.pilot_band(found.route))


class TestPilotStretch:
    pytestmark: ClassVar = [
        *raw_marks(*DATA_PATTERNS),
        *build_marks(TERRAIN_BUILD_DIR / "dem.f32", TRAIL_GENERATED),
    ]

    def test_the_clipped_window_reproduces_the_research_figure(self, reference: Crowns) -> None:
        assert len(reference) == PILOT_REFERENCE_CROWNS

    def test_a_run_over_the_whole_park_has_one_crown_fewer_in_the_band(
        self, found: vegetation.Detection
    ) -> None:
        band = vegetation.pilot_band(found.route)
        assert int(vegetation.crowns_in(found.crowns, band).sum()) == PILOT_PARK_CROWNS

    def test_the_height_classes_match_the_research_within_three(self, reference: Crowns) -> None:
        bins = np.histogram(reference.height, bins=[3.0, 5.0, 8.0, 12.0, 100.0])[0]
        assert bins.tolist()[:3] == pytest.approx([58, 108, 20], abs=3)
        assert int(bins[3]) == 0

    def test_a_half_metre_shift_of_every_point_changes_the_count_by_at_most_five_percent(
        self, found: vegetation.Detection
    ) -> None:
        points = found.points
        shifted = VegetationPoints(
            points.x + 0.5, points.z + 0.5, points.height, points.lidar_class
        )
        before = len(vegetation.detect_crowns(points, found.grid))
        after = len(vegetation.detect_crowns(shifted, found.grid))
        assert abs(after - before) <= 0.05 * before

    def test_the_stored_pilot_positions_are_still_found_within_a_metre(
        self, reference: Crowns
    ) -> None:
        stored = np.array(json.loads(PILOT_FIXTURE.read_text(encoding="utf-8"))["crowns"])
        assert len(stored) == PILOT_REFERENCE_CROWNS
        found = np.stack([reference.x, reference.z], axis=1)
        nearest = np.sqrt(((stored[:, None, :] - found[None, :, :]) ** 2).sum(axis=2)).min(axis=1)
        assert (nearest <= 1.0).mean() >= 0.95


class TestRunIsReproducible:
    pytestmark: ClassVar = [
        *raw_marks(*DATA_PATTERNS),
        *build_marks(TERRAIN_BUILD_DIR / "dem.f32", TRAIL_GENERATED),
    ]

    def test_two_runs_write_the_same_bytes_and_a_provenance_block_that_verifies(
        self, tmp_path: Path
    ) -> None:
        first, second = (
            tmp_path / "a" / "vegetation.json",
            tmp_path / "b" / "vegetation.json",
        )
        vegetation.run_vegetation(first)
        vegetation.run_vegetation(second)
        assert first.read_bytes() == second.read_bytes()
        document = json.loads(first.read_text(encoding="utf-8"))
        assert document["inputs"]
        assert set(document["tools"]) == {"numpy", "rasterio", "shapely", "laspy"}
        assert provenance.verify_artefact(first, "vegetation.json", REPO_ROOT) == []


# --- draw budget estimate -----------------------------------------------------------------------


def test_the_budget_estimate_counts_triangles_by_distance_and_draw_calls_by_group() -> None:
    meshes = {"tree": (1000, 100, 4), "bush": (50, 10, 4)}
    trees = np.array([[0.0, 5.0], [0.0, 50.0], [0.0, 100.0], [0.0, 500.0]])  # x, z of 4 trees
    bushes = np.array([[3.0, 0.0], [0.0, 20.0], [0.0, 200.0]])
    estimate = vegetation.estimate_view(
        viewer=(0.0, 0.0),
        groups=[
            vegetation.Group("tree", trees, meshes["tree"], (30.0, 70.0, 120.0)),
            vegetation.Group("bush", bushes, meshes["bush"], (10.0, 30.0, 60.0)),
        ],
    )
    # trees at 5 m (lod0), 50 m (lod1), 100 m (card), 500 m (out); bushes at 3 m, 20 m, out
    assert estimate.triangles == 1000 + 100 + 4 + 50 + 10
    assert estimate.calls == 5  # tree lod0, lod1, card + bush lod0, lod1


# --- the moved foot and the apex elevation ------------------------------------------------------


def tilted_grid(per_metre_z: float, base: float = 100.0) -> Grid:
    """Ground rising ``per_metre_z`` metres per metre towards the south (z grows)."""
    z = np.arange(200, dtype=np.float64) - 100.0
    column = (base + z * per_metre_z).astype(np.float32)
    return Grid(np.tile(column[:, None], (1, 200)), x0=-100.0, z0=-100.0)


def apex_crown(grid: Grid, z: float = 0.5, height: float = 8.0) -> Crowns:
    x = np.array([0.0])
    zz = np.array([z])
    return Crowns(x, np.asarray(grid.sample(x, zz)), zz, np.array([height]), np.array([2.0]))


def vertical_of(grid: Grid, **kwargs: float) -> vegetation.Vertical:
    crowns = apex_crown(grid)
    feet = vegetation.place_feet(crowns.x, crowns.z, crowns.height, PATH_CORRIDOR)
    return vegetation.check_vertical(feet, crowns, grid, dem.slope_degrees(grid), **kwargs)


def test_a_moved_foot_records_the_apex_elevation_and_the_vertical_scale() -> None:
    grid = tilted_grid(0.2)  # a 11 degree bank: the foot (z = 3.5) is 0.6 m above the apex ground
    vertical = vertical_of(grid)
    assert vertical.ok.tolist() == [True]
    assert vertical.apex_y[0] == pytest.approx(grid.sample(0.0, 0.5) + 8.0)
    assert vertical.foot_y[0] == pytest.approx(grid.sample(0.0, 3.5), abs=0.05)
    # the crown is 8 m above the apex ground, so 0.6 m less above the higher foot
    assert vertical.apex_y[0] - vertical.foot_y[0] == pytest.approx(8.0 - 0.6, abs=0.05)


def test_a_foot_across_a_step_taller_than_the_limit_is_dropped() -> None:
    assert vertical_of(tilted_grid(0.2), max_drop=0.5).ok.tolist() == [False]
    assert vertical_of(tilted_grid(1.0)).ok.tolist() == [False]  # 3 m of ground between


def test_a_foot_on_a_cliff_is_dropped_whatever_the_step() -> None:
    grid = tilted_grid(0.0)
    heights = grid.heights.copy()
    heights[105:, :] += 3.5  # a wall one row beyond the foot (z = 3.5): its cell reads 60.3 degrees
    walled = Grid(heights, grid.x0, grid.z0)
    assert dem.slope_at(dem.slope_degrees(walled), walled, 0.0, 3.5) >= vegetation.CLIFF_SLOPE
    assert vertical_of(walled, max_drop=10.0).ok.tolist() == [False]


def test_an_unmoved_crown_keeps_its_own_ground_and_always_passes() -> None:
    grid = tilted_grid(1.0)
    crowns = apex_crown(grid, z=40.0)  # far from the corridor
    feet = vegetation.place_feet(crowns.x, crowns.z, crowns.height, PATH_CORRIDOR)
    vertical = vegetation.check_vertical(feet, crowns, grid, dem.slope_degrees(grid))
    assert vertical.ok.tolist() == [True]
    assert vertical.foot_y[0] == pytest.approx(crowns.y[0])
    assert vertical.apex_y[0] == pytest.approx(crowns.y[0] + 8.0)
