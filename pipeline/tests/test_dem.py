import json
from pathlib import Path
from typing import Any

import laspy
import numpy as np
import pytest
import rasterio
import shapely
from conftest import raw_marks
from rasterio.transform import from_origin
from shapely.geometry import box

from penyal_pipeline import dem, trail
from penyal_pipeline.dem import DemBuild, DemError, Grid
from penyal_pipeline.geo import to_local
from penyal_pipeline.rawdata import locate

# --- synthetic rasters -------------------------------------------------------------------------


def _write_raster(
    path: Path,
    data: np.ndarray,
    left: float = 1000.0,
    top: float = 5000.0,
    cell: float = 1.0,
    epsg: int = 25830,
    nodata: float | None = -9999.0,
) -> Path:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype="float32",
        crs=f"EPSG:{epsg}",
        transform=from_origin(left, top, cell, cell),
        nodata=nodata,
        compress="lzw",
        blockysize=1,
        tiled=False,
    ) as dst:
        dst.write(data.astype(np.float32), 1)
    return path


def _coded(rows: int = 40, cols: int = 50) -> np.ndarray:
    """Every pixel holds ``row * 1000 + col``, so a window read proves where it came from."""
    return (np.arange(rows)[:, None] * 1000 + np.arange(cols)[None, :]).astype(np.float32)


def test_window_math_and_orientation(tmp_path: Path) -> None:
    path = _write_raster(tmp_path / "a.tif", _coded())
    # Raster covers E 1000..1050, N 4960..5000 (north-up: row 0 at N 5000).
    data, nodata_cells = dem.read_window(path, (1010.0, 4970.0, 1030.0, 4990.0))
    assert data.shape == (20, 20)
    assert nodata_cells == 0
    # Top-left of the bbox is (E 1010, N 4990): raster row 10, col 10.
    assert data[0, 0] == 10 * 1000 + 10
    assert data[0, -1] == 10 * 1000 + 29  # eastwards increases the column
    assert data[-1, 0] == 29 * 1000 + 10  # southwards increases the row


def test_nodata_becomes_nan_and_is_counted(tmp_path: Path) -> None:
    raster = _coded()
    raster[12, 12] = -9999.0
    raster[13, 14] = -9999.0
    path = _write_raster(tmp_path / "a.tif", raster)
    data, nodata_cells = dem.read_window(path, (1010.0, 4970.0, 1030.0, 4990.0))
    assert nodata_cells == 2
    assert np.isnan(data[2, 2])
    assert np.isnan(data[3, 4])
    assert int(np.isnan(data).sum()) == 2


@pytest.mark.parametrize(
    ("kwargs", "bbox", "message"),
    [
        ({"epsg": 25831}, (1010.0, 4970.0, 1030.0, 4990.0), "CRS"),
        ({"cell": 2.0}, (1010.0, 4930.0, 1030.0, 4990.0), "pixel size"),
        ({}, (990.0, 4970.0, 1030.0, 4990.0), "not fully inside"),
        ({}, (1010.5, 4970.0, 1030.5, 4990.0), "not aligned"),
    ],
)
def test_read_window_fails_loudly(
    tmp_path: Path, kwargs: dict[str, Any], bbox: tuple[float, float, float, float], message: str
) -> None:
    path = _write_raster(tmp_path / "a.tif", _coded(), **kwargs)
    with pytest.raises(DemError, match=message):
        dem.read_window(path, bbox)


def test_local_origin_of_the_work_area() -> None:
    x0, z0 = dem.local_origin(dem.WORK_BBOX)
    assert (x0, z0) == (-599.5, -1999.5)
    # Same point through the frame helpers: centre of the NW cell is (E 766400.5, N 4281999.5).
    assert to_local(766400.5, 4281999.5)[::2] == (x0, z0)


# --- sea fill ----------------------------------------------------------------------------------


def test_rasterize_sea_orientation() -> None:
    bbox = (0.0, 0.0, 10.0, 10.0)
    north_west = box(0.0, 5.0, 5.0, 10.0)
    mask = dem.rasterize_sea(north_west, (10, 10), bbox)
    assert mask[0, 0]
    assert mask[4, 4]
    assert not mask[5, 5]
    assert not mask[9, 9]
    assert not mask[0, 9]
    assert int(mask.sum()) == 25


def test_fill_sea_keeps_land_and_fills_water_and_nodata() -> None:
    heights = np.array(
        [
            [0.0, 0.0, 5.0],  # sea, sea, land-looking cell inside the polygon (a rock)
            [0.0, np.nan, 12.0],  # land at 0 m outside the polygon, nodata, land
        ],
        dtype=np.float32,
    )
    sea = np.array([[True, True, True], [False, False, False]])
    out, counts = dem.fill_sea(heights, sea)
    assert out[0, 0] == dem.SEA_FILL_HEIGHT
    assert out[0, 1] == dem.SEA_FILL_HEIGHT
    assert out[0, 2] == 5.0  # inside the polygon but clearly above sea level: untouched
    assert out[1, 0] == 0.0  # land at sea level outside the polygon: untouched
    assert out[1, 1] == dem.SEA_FILL_HEIGHT  # nodata
    assert out[1, 2] == 12.0
    assert counts == {"seaCells": 2, "nodataCells": 1}
    assert np.isnan(heights[1, 1]), "input must not be modified"


# --- grids -------------------------------------------------------------------------------------


def _plane(x: Any, z: Any) -> Any:
    """Height 10 m at (100, -200), rising 0.5 m per metre east and 0.25 m per metre south."""
    return 10.0 + 0.5 * (x - 100.0) + 0.25 * (z + 200.0)


def _plane_grid() -> Grid:
    rows, cols = 6, 8
    r, c = np.mgrid[0:rows, 0:cols]
    x0, z0 = 100.5, -200.5
    heights = _plane(x0 + c, z0 + r).astype(np.float32)
    return Grid(heights, x0, z0)


def test_sample_is_exact_on_a_plane_and_at_cell_centres() -> None:
    grid = _plane_grid()
    for x, z in [(100.5, -200.5), (103.25, -198.75), (107.5, -195.5)]:
        assert grid.sample(x, z) == pytest.approx(_plane(x, z), abs=1e-4)
    assert grid.sample(101.5, -199.5) == grid.heights[1, 1]


def test_sample_clamps_outside_the_grid() -> None:
    grid = _plane_grid()
    assert grid.sample(-1e6, -1e6) == grid.heights[0, 0]
    assert grid.sample(1e6, 1e6) == grid.heights[-1, -1]


def test_crop_snaps_outwards_and_keeps_registration() -> None:
    grid = _plane_grid()
    sub = dem.crop(grid, (102.2, -198.7, 104.1, -197.2))
    # Cells are centred on .5, so cell edges are at integers: x 102..105 -> cols 2..4,
    # z -199..-197 -> rows 2..3.
    assert (sub.x0, sub.z0) == (102.5, -198.5)
    assert sub.heights.shape == (2, 3)
    np.testing.assert_array_equal(sub.heights, grid.heights[2:4, 2:5])
    assert sub.sample(103.5, -198.5) == pytest.approx(grid.sample(103.5, -198.5))


def test_crop_clamps_to_the_grid_and_rejects_disjoint_bounds() -> None:
    grid = _plane_grid()
    whole = dem.crop(grid, (0.0, -1000.0, 1000.0, 1000.0))
    assert whole.heights.shape == grid.heights.shape
    with pytest.raises(DemError, match="do not overlap"):
        dem.crop(grid, (500.0, 500.0, 600.0, 600.0))


def test_quantisation_round_trip_error_within_half_a_centimetre() -> None:
    rng = np.random.default_rng(7)
    heights = rng.uniform(-3.0, 330.0, size=(200, 300)).astype(np.float32)
    heights[0, 0] = -3.0
    steps, offset = dem.quantise(heights)
    assert steps.dtype == np.uint16
    error = np.abs(dem.dequantise(steps, offset) - heights.astype(np.float64))
    assert float(error.max()) <= 0.005 + 1e-6


def test_quantise_rejects_ranges_that_do_not_fit() -> None:
    with pytest.raises(DemError, match="uint16"):
        dem.quantise(np.array([[0.0, 700.0]], dtype=np.float32))


def test_dem_files_round_trip(tmp_path: Path) -> None:
    grid = _plane_grid()
    source = {"id": "x", "file": "x.tif", "sha256": "ab"}
    sea_fill = {"height": -3.0, "approximate": True}
    dem.write_dem(tmp_path, grid, source, sea_fill)
    assert (tmp_path / "dem.f32").stat().st_size == grid.heights.size * 4
    loaded, meta = dem.load_dem(tmp_path)
    np.testing.assert_array_equal(loaded.heights, grid.heights)
    assert (loaded.x0, loaded.z0) == (grid.x0, grid.z0)
    assert meta["width"] == 8
    assert meta["height"] == 6
    assert meta["source"] == source
    assert meta["seaFill"] == sea_fill
    assert meta["origin"] == {"e": 767000, "n": 4280000}
    assert meta["minHeight"] == pytest.approx(float(grid.heights.min()), abs=1e-3)


def test_collision_files_round_trip(tmp_path: Path) -> None:
    grid = _plane_grid()
    meta = dem.write_collision(tmp_path, grid, {"id": "x"}, {"height": -3.0})
    assert meta["heightScale"] == 0.01
    assert (tmp_path / "collision.bin").stat().st_size == grid.heights.size * 2
    loaded, stored = dem.load_collision(tmp_path)
    assert stored == json.loads((tmp_path / "collision.json").read_text(encoding="utf-8"))
    assert float(np.abs(loaded.heights.astype(np.float64) - grid.heights).max()) <= 0.0051


# --- LiDAR on a synthetic LAS ------------------------------------------------------------------


def test_lidar_samples_filter_class_noise_and_bounds(tmp_path: Path) -> None:
    grid = _plane_grid()  # x 100.5..107.5, z -200.5..-195.5 (local)
    xs = np.array([103.5, 103.5, 103.5, 104.5, 150.0])
    zs = np.array([-198.5, -198.5, -198.5, -197.5, -198.5])
    plane = _plane(xs, zs)
    zs_utm = 4280000.0 - zs
    xs_utm = 767000.0 + xs
    heights = plane + np.array([0.5, 0.0, 0.0, -0.25, 0.0])
    heights[2] = -97.0  # noise
    classes = np.array([2, 1, 2, 2, 2], dtype=np.uint8)  # point 1 is vegetation, 4 is outside
    header = laspy.LasHeader(point_format=3, version="1.2")
    header.scales = np.array([0.001, 0.001, 0.001])
    header.offsets = np.array([767000.0, 4279000.0, 0.0])
    las = laspy.LasData(header)
    las.x, las.y, las.z = xs_utm, zs_utm, heights
    las.classification = classes
    path = tmp_path / "t.las"
    las.write(str(path))

    samples = dem.lidar_ground_samples(grid, [path], (100.0, -201.0, 108.0, -195.0))
    assert samples.noise == 1
    assert samples.errors == pytest.approx([0.5, -0.25], abs=2e-3)
    assert samples.x == pytest.approx([103.5, 104.5], abs=2e-3)
    stats = dem.error_stats(samples.errors)
    assert stats["count"] == 2
    assert stats["mean"] == pytest.approx(0.125, abs=2e-3)
    assert stats["maxAbs"] == pytest.approx(0.5, abs=2e-3)


def test_slope_degrees_of_a_plane() -> None:
    grid = _plane_grid()
    expected = np.degrees(np.arctan(np.hypot(0.5, 0.25)))
    assert dem.slope_degrees(grid) == pytest.approx(np.full(grid.heights.shape, expected), abs=1e-3)


# --- real data ---------------------------------------------------------------------------------

ICV_SUMMIT = (767615.67, 4280757.87)
ICV_SUMMIT_HEIGHT = 325.8


type Samples = tuple[dem.LidarSamples, np.ndarray]


@pytest.fixture(scope="module")
def samples(real: DemBuild) -> Samples:
    osm = trail.load_osm(locate("osm-penyal", "osm-penyal.json").path)
    corridor, _ = trail.build_corridor(osm)
    found = dem.lidar_ground_samples(real.grid, dem.lidar_paths(), corridor.bounds)
    return found, shapely.contains_xy(corridor, found.x, found.z)


@pytest.fixture(scope="module")
def real() -> DemBuild:
    return dem.build_dem(*dem.locate_inputs())


class TestRealDem:
    pytestmark = raw_marks("icv-mdt-2016-0848/*.tif", "icv-cv05-penyal/HidrografiaBCV05.geojson")

    def test_grid_matches_the_work_area(self, real: DemBuild) -> None:
        meta = real.meta
        assert (meta["width"], meta["height"]) == (2600, 2550)
        assert (meta["x0"], meta["z0"]) == (-599.5, -1999.5)
        assert meta["crs"] == "EPSG:25830"
        assert meta["source"]["id"] == "icv-mdt-2016-0848"
        assert meta["source"]["sha256"] == locate("icv-mdt-2016-0848", ".tif").sha256

    def test_no_nodata_and_sea_is_filled(self, real: DemBuild) -> None:
        assert not np.isnan(real.grid.heights).any()
        assert real.meta["minHeight"] == dem.SEA_FILL_HEIGHT
        assert real.sea_fill["seaCells"] > 5_000_000
        assert real.sea_fill["approximate"] is True

    def test_only_sea_cells_differ_from_the_source(self, real: DemBuild) -> None:
        mdt, hydrography = dem.locate_inputs()
        source, _ = dem.read_window(mdt.path)
        sea = dem.rasterize_sea(dem.load_sea_polygon(hydrography.path), source.shape, dem.WORK_BBOX)
        changed = real.grid.heights != source
        assert changed.sum() == real.sea_fill["seaCells"]
        assert sea[changed].all()
        assert (source[changed] <= dem.SEA_LEVEL_TOLERANCE).all()
        assert (real.grid.heights[changed] == dem.SEA_FILL_HEIGHT).all()

    def test_dem_at_the_icv_summit_spot_height(self, real: DemBuild) -> None:
        spot = json.loads(
            (locate("icv-cv05-penyal", "PuntosCotaBCV05.geojson").path).read_text(encoding="utf-8")
        )
        heights = [
            f
            for f in spot["features"]
            if f["geometry"] and f["geometry"]["coordinates"] == list(ICV_SUMMIT)
        ]
        assert float(heights[0]["properties"]["texto"]) == ICV_SUMMIT_HEIGHT
        x, _, z = to_local(*ICV_SUMMIT)
        assert float(real.grid.sample(x, z)) == pytest.approx(ICV_SUMMIT_HEIGHT, abs=1.0)

    def test_highest_dem_cell_is_the_summit(self, real: DemBuild) -> None:
        top = dem.summit_cells(real.grid)
        # The model peaks 0.4 m from the ICV spot height, ~1 m above it, below the official 332 m.
        assert top["e"] == pytest.approx(ICV_SUMMIT[0], abs=2.0)
        assert top["n"] == pytest.approx(ICV_SUMMIT[1], abs=2.0)
        assert 325.0 < top["height"] < 328.0

    def test_dem_at_the_osm_summit(self, real: DemBuild) -> None:
        osm = trail.load_osm(locate("osm-penyal", "osm-penyal.json").path)
        x, z = osm.xz[trail.SUMMIT_NODE]
        assert float(real.grid.sample(x, z)) == pytest.approx(ICV_SUMMIT_HEIGHT, abs=1.0)

    def test_collision_covers_the_walkable_area_and_is_small(
        self, real: DemBuild, tmp_path: Path
    ) -> None:
        osm = trail.load_osm(locate("osm-penyal", "osm-penyal.json").path)
        bounds = trail.walkable_bounds(osm)
        sub = dem.crop(real.grid, bounds)
        dem.write_collision(tmp_path, sub, real.source, real.sea_fill)
        assert (tmp_path / "collision.bin").stat().st_size <= 2_000_000
        loaded, _ = dem.load_collision(tmp_path)
        assert float(np.abs(loaded.heights.astype(np.float64) - sub.heights).max()) <= 0.0051
        corridor, _ = trail.build_corridor(osm)
        x0, z0, x1, z1 = corridor.bounds
        assert sub.x0 - 0.5 <= x0 - trail.WALKABLE_MARGIN
        assert sub.z0 - 0.5 <= z0 - trail.WALKABLE_MARGIN
        assert sub.x0 - 0.5 + sub.width >= x1 + trail.WALKABLE_MARGIN
        assert sub.z0 - 0.5 + sub.height >= z1 + trail.WALKABLE_MARGIN


class TestLidarCrossCheck:
    """The DEM is interpolated from the same 2016 LiDAR ground returns, so on gentle slopes the
    two must agree at the decimetre level. Thresholds are ~1.5x the observed values (mean -0.015 m,
    RMSE 0.40 m on slopes <= 30 deg; mean -0.058 m, p95 0.64 m inside the corridor) so that a
    registration or axis error (metres) fails while ordinary data noise does not. Steep faces are
    excluded on purpose: a 2.5D grid cannot represent the Penyal's near-vertical cliffs."""

    pytestmark = raw_marks(
        "icv-mdt-2016-0848/*.tif",
        "icv-cv05-penyal/HidrografiaBCV05.geojson",
        "icv-lidar-2016-*/*.laz",
        "osm-penyal/osm-penyal.json",
    )

    def test_gentle_slopes_agree(self, samples: Samples) -> None:
        found, _ = samples
        stats = dem.error_stats(found.errors[found.slopes <= dem.GENTLE_SLOPE_DEGREES])
        assert stats["count"] > 10_000
        assert abs(stats["mean"]) <= 0.1
        assert stats["rmse"] <= 0.6

    def test_inside_the_corridor_agree(self, samples: Samples) -> None:
        found, inside = samples
        stats = dem.error_stats(found.errors[inside])
        assert stats["count"] > 3_000
        assert abs(stats["mean"]) <= 0.2
        assert stats["p95Abs"] <= 1.0
