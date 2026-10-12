"""X1.1: the minimap crop of the orthophoto around the trail corridor."""

import json
from pathlib import Path
from typing import ClassVar

import numpy as np
import pytest
import rasterio
from conftest import build_marks, raw_marks

from penyal_pipeline import artefacts, minimap, ortho
from penyal_pipeline.minimap import Bounds, MinimapError
from penyal_pipeline.paths import TRAIL_GENERATED

pytestmark = pytest.mark.filterwarnings("ignore::rasterio.errors.NotGeoreferencedWarning")

SQUARE = [[10.0, 20.0], [110.0, 20.0], [110.0, 70.0], [10.0, 70.0]]


class TestCropBounds:
    def test_it_grows_the_bounding_box_by_the_margin(self) -> None:
        bounds = crop_square(margin=60.0)
        assert (bounds.x0, bounds.z0, bounds.x1, bounds.z1) == (-50.0, -40.0, 170.0, 130.0)

    def test_it_snaps_outwards_to_whole_pixels(self) -> None:
        bounds = minimap.crop_bounds([[0.1, 0.1], [10.2, 0.1], [10.2, 5.3]], margin=0.0)
        assert (bounds.x0, bounds.z0) == (0.0, 0.0)
        assert (bounds.x1, bounds.z1) == (10.5, 5.5)
        assert (bounds.width, bounds.height) == (21, 11)

    def test_every_point_of_the_polygon_is_inside(self) -> None:
        bounds = crop_square(margin=60.0)
        assert all(bounds.contains(x, z) for x, z in SQUARE)

    def test_it_rejects_a_degenerate_polygon(self) -> None:
        with pytest.raises(MinimapError, match="expected >= 3"):
            minimap.crop_bounds([[0.0, 0.0], [1.0, 1.0]])


def crop_square(margin: float) -> Bounds:
    return minimap.crop_bounds(SQUARE, margin=margin, metres_per_pixel=0.5)


class TestPixelMapping:
    def test_pixel_size_follows_the_bounds_and_resolution(self) -> None:
        bounds = crop_square(margin=60.0)
        assert (bounds.width, bounds.height) == (440, 340)

    def test_the_north_west_corner_is_pixel_zero(self) -> None:
        bounds = crop_square(margin=60.0)
        assert bounds.to_pixel(bounds.x0, bounds.z0) == (0.0, 0.0)

    def test_north_is_up_so_a_larger_z_is_a_lower_row(self) -> None:
        bounds = crop_square(margin=60.0)
        column, row = bounds.to_pixel(bounds.x0 + 10.0, bounds.z0 + 20.0)
        assert (column, row) == (20.0, 40.0)

    def test_the_south_east_corner_is_the_image_size(self) -> None:
        bounds = crop_square(margin=60.0)
        assert bounds.to_pixel(bounds.x1, bounds.z1) == (bounds.width, bounds.height)

    def test_from_pixel_inverts_to_pixel(self) -> None:
        bounds = crop_square(margin=60.0)
        column, row = bounds.to_pixel(33.25, 41.5)
        assert bounds.from_pixel(column, row) == (33.25, 41.5)


class TestSizeCap:
    def test_it_picks_the_highest_quality_that_fits(self) -> None:
        quality, data = minimap.fit_quality(lambda q: bytes(q * 100), max_bytes=7000)
        assert quality == 70
        assert len(data) == 7000

    def test_it_takes_the_ceiling_when_everything_fits(self) -> None:
        quality, _ = minimap.fit_quality(lambda q: bytes(q), max_bytes=10_000)
        assert quality == minimap.MAX_QUALITY

    def test_it_fails_loudly_when_even_the_lowest_quality_is_too_big(self) -> None:
        with pytest.raises(MinimapError, match="does not fit 10 bytes"):
            minimap.fit_quality(lambda q: bytes(q * 100), max_bytes=10)


class TestEncoding:
    @staticmethod
    def gradient() -> np.ndarray:
        rows, cols = np.indices((64, 96))
        planes = (rows * 4, cols * 2, (rows + cols) * 2)
        return np.stack(planes, axis=2).astype(np.uint8)

    def test_it_writes_a_progressive_jpeg_that_decodes_to_the_same_size(self) -> None:
        data = minimap.encode_jpeg(self.gradient(), 80)
        assert data[:3] == b"\xff\xd8\xff"
        with rasterio.MemoryFile(data) as memory, memory.open() as image:
            assert (image.width, image.height, image.count) == (96, 64, 3)

    def test_the_same_pixels_encode_to_the_same_bytes(self) -> None:
        rgb = self.gradient()
        assert minimap.encode_jpeg(rgb, 80) == minimap.encode_jpeg(rgb, 80)

    def test_a_lower_quality_is_smaller(self) -> None:
        rgb = self.gradient()
        assert len(minimap.encode_jpeg(rgb, 40)) < len(minimap.encode_jpeg(rgb, 90))


def block_means(rgb: np.ndarray, block: int = 8) -> np.ndarray:
    """Mean colour of block x block tiles, so JPEG noise averages out and only content remains."""
    height, width, _ = rgb.shape
    tiles = rgb[: height // block * block, : width // block * block].astype(np.float64)
    return tiles.reshape(height // block, block, width // block, block, 3).mean(axis=(1, 3))


class TestCorridor:
    def test_a_missing_trail_names_the_command_to_run(self, tmp_path: Path) -> None:
        with pytest.raises(MinimapError, match="penyal trail"):
            minimap.load_corridor(tmp_path / "trail.json")

    def test_a_trail_without_a_corridor_is_rejected(self, tmp_path: Path) -> None:
        trail_json = tmp_path / "trail.json"
        trail_json.write_text("{}", encoding="utf-8")
        with pytest.raises(MinimapError, match=r"no corridor\.polygon"):
            minimap.load_corridor(trail_json)


needs_trail = build_marks(TRAIL_GENERATED)


@pytest.fixture(scope="module")
def first(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("minimap-a")
    minimap.run_minimap(out, artefacts.provenance("minimap"))
    return out


@pytest.fixture(scope="module")
def second(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("minimap-b")
    minimap.run_minimap(out, artefacts.provenance("minimap"))
    return out


class TestGenerated:
    """Against the real orthophoto and the generated ``trail.json``."""

    pytestmark: ClassVar = [*raw_marks(f"{ortho.ORTHO_SOURCE_ID}/*.tif"), *needs_trail]

    def test_two_runs_produce_byte_identical_files(self, first: Path, second: Path) -> None:
        for name in (minimap.IMAGE_NAME, minimap.MANIFEST_NAME):
            assert (first / name).read_bytes() == (second / name).read_bytes()

    def test_the_image_fits_the_cap_and_matches_the_manifest(self, first: Path) -> None:
        manifest = json.loads((first / minimap.MANIFEST_NAME).read_text(encoding="utf-8"))
        image = (first / minimap.IMAGE_NAME).read_bytes()
        assert len(image) <= minimap.MAX_IMAGE_BYTES
        assert manifest["image"]["bytes"] == len(image)
        with rasterio.MemoryFile(image) as memory, memory.open() as decoded:
            assert (decoded.width, decoded.height) == (
                manifest["size"]["width"],
                manifest["size"]["height"],
            )

    def test_the_manifest_carries_the_attribution_and_the_provenance(self, first: Path) -> None:
        manifest = json.loads((first / minimap.MANIFEST_NAME).read_text(encoding="utf-8"))
        assert manifest["attribution"] == "© Institut Cartogràfic Valencià, CC BY 4.0"
        assert manifest["metresPerPixel"] == 0.5
        assert {entry["file"].rsplit("/", 1)[-1] for entry in manifest["inputs"]} >= {"trail.json"}
        assert set(manifest["tools"]) == {"numpy", "rasterio"}

    def test_the_bounds_cover_the_corridor_and_every_anchor_with_the_margin(self) -> None:
        polygon, anchors = minimap.load_corridor()
        bounds = minimap.crop_bounds(polygon)
        xs = [point[0] for point in polygon]
        zs = [point[1] for point in polygon]
        assert bounds.x0 <= min(xs) - minimap.MARGIN_M
        assert bounds.z0 <= min(zs) - minimap.MARGIN_M
        assert bounds.x1 >= max(xs) + minimap.MARGIN_M
        assert bounds.z1 >= max(zs) + minimap.MARGIN_M
        for key in ("park-entrance", "summit", "carabiners"):
            assert bounds.contains(anchors[key]["x"], anchors[key]["z"])

    def test_the_pixels_are_the_orthophoto_rgb_north_up(self, first: Path) -> None:
        manifest = json.loads((first / minimap.MANIFEST_NAME).read_text(encoding="utf-8"))
        b = manifest["bounds"]
        bounds = Bounds(b["x0"], b["z0"], b["x1"], b["z1"], manifest["metresPerPixel"])
        with ortho.open_ortho(ortho.locate_ortho().path) as src:
            expected = ortho.read_rgb(src, bounds.rect(), bounds.width, bounds.height).rgb
        jpeg = (first / minimap.IMAGE_NAME).read_bytes()
        with rasterio.MemoryFile(jpeg) as memory, memory.open() as decoded:
            actual = decoded.read().transpose(1, 2, 0).astype(np.int16)
        assert np.abs(block_means(actual) - block_means(expected)).mean() < 2.0
