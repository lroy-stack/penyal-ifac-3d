"""Surface-class masks from OSM: synthetic geometry first, then the real extract."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from conftest import raw_marks

from penyal_pipeline import surfaces, trail
from penyal_pipeline.rawdata import locate
from penyal_pipeline.surfaces import SurfaceWay
from penyal_pipeline.trail import OsmData, Way

pytestmark = pytest.mark.filterwarnings("ignore::rasterio.errors.NotGeoreferencedWarning")

CHANNELS = len(surfaces.CLASSES)


def straight_way(
    way_id: int, surface: str, highway: str, a: tuple[float, float], b: tuple[float, float]
) -> SurfaceWay:
    cls = surfaces.surface_class(surface)
    assert cls is not None
    return SurfaceWay(
        way_id=way_id,
        highway=highway,
        surface=surface,
        surface_class=cls,
        width=surfaces.HIGHWAY_WIDTHS[highway],
        xz=np.array([a, b], dtype=np.float64),
    )


def centre_of(i: int, j: int) -> tuple[float, float]:
    rect = surfaces.tile_rect(i, j)
    return (rect.x_min + rect.x_max) / 2, (rect.z_min + rect.z_max) / 2


class TestClassification:
    @pytest.mark.parametrize(
        ("surface", "expected"),
        [
            ("unhewn_cobblestone", "unhewn_cobblestone"),
            ("compacted", "compacted"),
            ("dirt", "compacted"),
            ("ground", "compacted"),
            ("gravel", "compacted"),
            ("paving_stones", "paving_stones"),
            ("sett", "paving_stones"),
            ("asphalt", "asphalt"),
            ("rock", None),
            ("concrete", None),
            ("something-new", None),
            (None, None),
        ],
    )
    def test_osm_surface_to_class(self, surface: str | None, expected: str | None) -> None:
        assert surfaces.surface_class(surface) == expected

    def test_every_class_has_a_channel_and_the_mask_is_rgba(self) -> None:
        assert len(surfaces.CLASSES) == 4
        assert set(surfaces.SURFACE_CLASS.values()) == set(surfaces.CLASSES)

    def test_widths_are_exposed_as_provisional_data(self) -> None:
        assert surfaces.WIDTHS_STATUS == "provisional"
        assert all(width > 0 for width in surfaces.HIGHWAY_WIDTHS.values())
        assert surfaces.HIGHWAY_WIDTHS["residential"] > surfaces.HIGHWAY_WIDTHS["footway"]


class TestRasterise:
    def test_tile_geometry_matches_the_terrain_tile_extent(self) -> None:
        rect = surfaces.tile_rect(2, -4)
        assert (rect.x_min, rect.z_min) == (511.5, -1024.5)
        assert rect.x_max - rect.x_min == 256
        assert surfaces.TILE_PIXELS == 1024

    def test_a_way_is_full_on_its_axis_and_empty_beyond_its_width(self) -> None:
        cx, cz = centre_of(2, -4)
        way = straight_way(1, "asphalt", "residential", (cx - 40, cz), (cx + 40, cz))
        mask = surfaces.rasterise_tile([way], 2, -4)
        half = way.width / 2
        on_axis = surfaces.value_at(mask, 2, -4, cx, cz)
        assert on_axis.tolist() == [0, 0, 0, 255]
        inside = surfaces.value_at(mask, 2, -4, cx, cz + half - 0.5)
        assert inside[3] == 255
        outside = surfaces.value_at(mask, 2, -4, cx, cz + half + 0.5)
        assert outside.tolist() == [0, 0, 0, 0]

    def test_the_edge_falls_off_softly_and_monotonically(self) -> None:
        cx, cz = centre_of(2, -4)
        way = straight_way(1, "asphalt", "residential", (cx - 40, cz), (cx + 40, cz))
        mask = surfaces.rasterise_tile([way], 2, -4)
        half = way.width / 2
        offsets = np.arange(-0.6, 0.6, surfaces.CELL_SIZE)
        alpha = [int(surfaces.value_at(mask, 2, -4, cx, cz + half + o)[3]) for o in offsets]
        assert alpha == sorted(alpha, reverse=True)
        assert 0 < alpha[len(alpha) // 2] < 255
        assert surfaces.EDGE_FALLOFF >= 2 * surfaces.CELL_SIZE

    def test_the_end_of_a_way_is_rounded_not_extended(self) -> None:
        cx, cz = centre_of(2, -4)
        way = straight_way(1, "compacted", "path", (cx - 40, cz), (cx, cz))
        mask = surfaces.rasterise_tile([way], 2, -4)
        assert surfaces.value_at(mask, 2, -4, cx + 0.25, cz)[1] > 0
        assert surfaces.value_at(mask, 2, -4, cx + 3.0, cz)[1] == 0

    def test_a_later_class_covers_an_earlier_one_and_channels_never_exceed_one(self) -> None:
        cx, cz = centre_of(2, -4)
        road = straight_way(1, "asphalt", "residential", (cx - 40, cz), (cx + 40, cz))
        trail_way = straight_way(2, "unhewn_cobblestone", "footway", (cx, cz - 40), (cx, cz + 40))
        mask = surfaces.rasterise_tile([trail_way, road], 2, -4)
        assert int(mask.sum(axis=2, dtype=np.int64).max()) <= 255 + CHANNELS
        crossing = surfaces.value_at(mask, 2, -4, cx, cz)
        assert crossing.tolist() == [0, 0, 0, 255]
        arm = surfaces.value_at(mask, 2, -4, cx, cz + 10)
        assert arm.tolist() == [255, 0, 0, 0]

    def test_a_way_crossing_a_tile_border_is_continuous(self) -> None:
        left, right = surfaces.tile_rect(2, -4), surfaces.tile_rect(3, -4)
        assert left.x_max == right.x_min
        z = left.z_min + 100.125
        way = straight_way(1, "compacted", "service", (left.x_max - 30, z), (left.x_max + 30, z))
        a = surfaces.rasterise_tile([way], 2, -4)
        b = surfaces.rasterise_tile([way], 3, -4)
        last_column, first_column = a[:, -1, :], b[:, 0, :]
        assert int(np.abs(last_column.astype(int) - first_column.astype(int)).max()) <= 40
        assert last_column[:, 1].max() == 255
        assert first_column[:, 1].max() == 255

    def test_rasterising_twice_gives_the_same_bytes(self) -> None:
        cx, cz = centre_of(2, -4)
        way = straight_way(1, "paving_stones", "footway", (cx - 33, cz - 7), (cx + 21, cz + 12))
        first = surfaces.rasterise_tile([way], 2, -4)
        second = surfaces.rasterise_tile([way], 2, -4)
        assert first.tobytes() == second.tobytes()


class TestPng:
    def test_the_png_round_trips_losslessly(self, tmp_path: Path) -> None:
        rng = np.random.default_rng(7)
        mask = rng.integers(0, 256, size=(16, 16, 4), dtype=np.uint8)
        path = tmp_path / "mask.png"
        path.write_bytes(surfaces.encode_png(mask))
        with rasterio.open(path) as src:
            decoded = src.read()
        assert decoded.shape == (4, 16, 16)
        assert np.array_equal(np.moveaxis(decoded, 0, -1), mask)

    def test_encoding_is_deterministic(self) -> None:
        mask = np.zeros((8, 8, 4), dtype=np.uint8)
        mask[2:5, 3:6, 1] = 255
        assert surfaces.encode_png(mask) == surfaces.encode_png(mask)

    def test_a_wrong_shape_is_rejected(self) -> None:
        with pytest.raises(surfaces.SurfacesError, match="RGBA"):
            surfaces.encode_png(np.zeros((8, 8, 3), dtype=np.uint8))


class TestSelection:
    def test_only_ways_with_a_known_surface_inside_the_near_box_are_kept(self) -> None:
        cx, cz = centre_of(2, -4)
        xz = {
            1: (cx - 10, cz),
            2: (cx + 10, cz),
            3: (cx, cz - 10),
            4: (cx, cz + 10),
            5: (9000.0, 9000.0),
            6: (9010.0, 9000.0),
        }
        ways = {
            10: Way((1, 2), {"highway": "footway", "surface": "unhewn_cobblestone"}),
            11: Way((3, 4), {"highway": "path"}),
            12: Way((1, 4), {"highway": "path", "surface": "rock"}),
            13: Way((5, 6), {"highway": "service", "surface": "asphalt"}),
            14: Way((1, 3), {"waterway": "stream", "surface": "dirt"}),
            15: Way((2, 4), {"highway": "bridleway", "surface": "dirt"}),
        }
        selected, skipped = surfaces.select_ways(OsmData(xz=xz, node_tags={}, ways=ways))
        assert [w.way_id for w in selected] == [10]
        assert selected[0].width == surfaces.HIGHWAY_WIDTHS["footway"]
        assert skipped == {
            "noSurfaceTag": 1,
            "surfaceWithoutOverlay": 1,
            "outsideNearBox": 1,
            "highwayWithoutWidth": 1,
        }

    def test_a_width_tag_overrides_the_provisional_width(self) -> None:
        cx, cz = centre_of(2, -4)
        osm = OsmData(
            xz={1: (cx - 10, cz), 2: (cx + 10, cz)},
            node_tags={},
            ways={10: Way((1, 2), {"highway": "path", "surface": "dirt", "width": "2.5"})},
        )
        selected, _ = surfaces.select_ways(osm)
        assert selected[0].width == 2.5


# --- the real extract --------------------------------------------------------------------------

pytestmark_data = raw_marks("osm-penyal/osm-penyal.json")


def midpoint(osm: OsmData, way_id: int) -> tuple[float, float]:
    nodes = osm.ways[way_id].nodes
    a, b = osm.xz[nodes[len(nodes) // 2 - 1]], osm.xz[nodes[len(nodes) // 2]]
    return (a[0] + b[0]) / 2, (a[1] + b[1]) / 2


def tile_of(x: float, z: float) -> tuple[int, int]:
    return int(np.floor((x + 0.5) / 256)), int(np.floor((z + 0.5) / 256))


@pytest.fixture(scope="module")
def osm() -> OsmData:
    return trail.load_osm(locate(trail.OSM_SOURCE_ID, trail.OSM_FILE).path)


@pytest.fixture(scope="module")
def run_a(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict[str, object]]:
    out = tmp_path_factory.mktemp("surfaces-a")
    return out, surfaces.run_surfaces(out, {"inputs": [], "tools": {}})


def class_at(out: Path, x: float, z: float) -> list[int]:
    i, j = tile_of(x, z)
    path = out / f"t_{i}_{j}.png"
    if not path.is_file():
        return [0, 0, 0, 0]
    with rasterio.open(path) as src:
        pixels = np.moveaxis(src.read(), 0, -1)
    return surfaces.value_at(pixels, i, j, x, z).tolist()


@pytest.mark.data
class TestRealExtract:
    pytestmark = pytestmark_data

    def test_the_pilot_trail_is_cobblestone(
        self, osm: OsmData, run_a: tuple[Path, dict[str, object]]
    ) -> None:
        x, z = midpoint(osm, 26330273)
        assert class_at(run_a[0], x, z) == [255, 0, 0, 0]

    def test_avinguda_del_port_is_asphalt(
        self, osm: OsmData, run_a: tuple[Path, dict[str, object]]
    ) -> None:
        x, z = midpoint(osm, 85587115)
        assert class_at(run_a[0], x, z) == [0, 0, 0, 255]

    def test_the_centre_steps_are_paving_stones(
        self, osm: OsmData, run_a: tuple[Path, dict[str, object]]
    ) -> None:
        x, z = midpoint(osm, 26330269)
        assert class_at(run_a[0], x, z) == [0, 0, 255, 0]

    def test_the_service_track_is_compacted(
        self, osm: OsmData, run_a: tuple[Path, dict[str, object]]
    ) -> None:
        x, z = midpoint(osm, 37656546)
        assert class_at(run_a[0], x, z) == [0, 255, 0, 0]

    def test_a_point_twenty_metres_off_the_trail_has_no_surface(
        self, osm: OsmData, run_a: tuple[Path, dict[str, object]]
    ) -> None:
        way = osm.ways[26330273]
        nodes = np.array([osm.xz[n] for n in way.nodes])
        a, b = nodes[40], nodes[41]
        direction = (b - a) / np.linalg.norm(b - a)
        normal = np.array([-direction[1], direction[0]])
        x, z = (a + b) / 2 + normal * 20.0
        everything = np.array([osm.xz[n] for w in osm.ways.values() for n in w.nodes])
        assert float(np.hypot(*(everything - [x, z]).T).min()) > 10.0
        assert class_at(run_a[0], x, z) == [0, 0, 0, 0]

    def test_the_manifest_exposes_widths_coverage_and_tiles(
        self, run_a: tuple[Path, dict[str, object]]
    ) -> None:
        out, returned = run_a
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        assert manifest == returned
        assert manifest["channels"] == list(surfaces.CLASSES)
        assert manifest["widths"]["status"] == "provisional"
        assert manifest["widths"]["highway"] == surfaces.HIGHWAY_WIDTHS
        assert manifest["cellSize"] == 0.25
        assert manifest["tilePixels"] == 1024
        assert all(manifest["coverageM2"][c] > 0 for c in surfaces.CLASSES)
        for tile in manifest["tiles"]:
            data = (out / tile["url"]).read_bytes()
            assert hashlib.sha256(data).hexdigest() == tile["sha256"]
            assert len(data) == tile["bytes"]
        assert {w["id"] for w in manifest["ways"]} >= {26330273, 85587115, 26330269}

    def test_two_runs_write_identical_files(
        self, run_a: tuple[Path, dict[str, object]], tmp_path: Path
    ) -> None:
        surfaces.run_surfaces(tmp_path, {"inputs": [], "tools": {}})
        names = sorted(p.name for p in run_a[0].iterdir())
        assert names == sorted(p.name for p in tmp_path.iterdir())
        for name in names:
            first = hashlib.sha256((run_a[0] / name).read_bytes()).hexdigest()
            second = hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
            assert first == second, name
