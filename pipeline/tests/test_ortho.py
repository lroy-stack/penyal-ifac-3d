"""Orthophoto windows: orientation, resampling, RGB-only output and the UV <-> image contract."""

from pathlib import Path

import numpy as np
import numpy.typing as npt
import pytest
import rasterio
from rasterio.transform import from_origin

from penyal_pipeline import ortho, tiles
from penyal_pipeline.dem import Grid
from penyal_pipeline.geo import ORIGIN_E, ORIGIN_N
from penyal_pipeline.ortho import LocalRect, OrthoError

MARKER_NE = (255, 0, 255)
MARKER_SW = (0, 255, 0)
NIR = 7
BACKGROUND = (90, 100, 110)


def write_ortho(
    path: Path,
    area: LocalRect,
    pixel: float = 0.25,
    epsg: int = 25830,
    count: int = 4,
) -> Path:
    """RGBI GeoTIFF over ``area`` with a magenta block in the NE corner and green in the SW."""
    width = round((area.x_max - area.x_min) / pixel)
    height = round((area.z_max - area.z_min) / pixel)
    data = np.empty((count, height, width), dtype=np.uint8)
    for band in range(min(count, 3)):
        data[band] = BACKGROUND[band]
    if count == 4:
        data[3] = NIR
    block = 16
    for band in range(min(count, 3)):
        data[band, :block, width - block :] = MARKER_NE[band]  # row 0 = north, last cols = east
        data[band, height - block :, :block] = MARKER_SW[band]
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=width,
        height=height,
        count=count,
        dtype="uint8",
        crs=f"EPSG:{epsg}",
        transform=from_origin(ORIGIN_E + area.x_min, ORIGIN_N - area.z_min, pixel, pixel),
    ) as dst:
        dst.write(data)
    return path


@pytest.fixture
def photo(tmp_path: Path) -> Path:
    return write_ortho(tmp_path / "ortho.tif", LocalRect(0.0, -300.0, 300.0, 0.0))


def test_window_is_returned_top_down_with_north_up(photo: Path) -> None:
    area = LocalRect(0.0, -100.0, 100.0, 0.0)
    with ortho.open_ortho(photo) as src:
        read = ortho.read_texture(src, area, 400)
    assert read.rgb.shape == (400, 400, 3)
    assert read.rgb.dtype == np.uint8
    assert read.outside == 0
    # the window's NW corner is the image's top-left pixel, its NE corner the top-right pixel
    assert read.rgb[0, 399].tolist() == list(BACKGROUND)  # block is in the photo's NE, not here
    with ortho.open_ortho(photo) as src:
        whole = ortho.read_texture(src, LocalRect(0.0, -300.0, 300.0, 0.0), 1200)
    assert whole.rgb[0, 1199].tolist() == list(MARKER_NE)
    assert whole.rgb[1199, 0].tolist() == list(MARKER_SW)
    assert whole.rgb[0, 0].tolist() == list(BACKGROUND)


def test_nir_band_never_reaches_the_texture(photo: Path) -> None:
    with ortho.open_ortho(photo) as src:
        read = ortho.read_texture(src, LocalRect(0.0, -300.0, 300.0, 0.0), 256)
    assert read.rgb.shape[-1] == 3
    assert NIR not in read.rgb.reshape(-1, 3)[:, 0]


def test_downsampling_is_an_area_average(tmp_path: Path) -> None:
    area = LocalRect(0.0, -4.0, 4.0, 0.0)
    path = write_ortho(tmp_path / "small.tif", area, pixel=0.25)
    with rasterio.open(path, "r+") as dst:
        chessboard = (np.indices((16, 16)).sum(axis=0) % 2 * 200).astype(np.uint8)
        dst.write(chessboard, 1)
    with ortho.open_ortho(path) as src:
        read = ortho.read_texture(src, area, 8)
    assert np.all(read.rgb[..., 0] == 100)


def test_pixels_outside_the_image_are_sea_and_counted(photo: Path) -> None:
    with ortho.open_ortho(photo) as src:
        area = LocalRect(-50.0, -300.0, 50.0, -200.0)  # west half is outside the photo
        assert not ortho.covers(src, area)
        read = ortho.read_texture(src, area, 100)
    assert read.outside == 100 * 50
    assert read.rgb[0, 0].tolist() == list(ortho.SEA_RGB)
    assert read.rgb[0, 99].tolist() == list(BACKGROUND)


def test_covers_reports_fully_inside_windows(photo: Path) -> None:
    with ortho.open_ortho(photo) as src:
        assert ortho.covers(src, LocalRect(0.0, -300.0, 300.0, 0.0))
        assert not ortho.covers(src, LocalRect(0.0, -300.0, 300.5, 0.0))


def test_wrong_crs_and_band_count_are_rejected(tmp_path: Path) -> None:
    area = LocalRect(0.0, -10.0, 10.0, 0.0)
    with pytest.raises(OrthoError, match="CRS"):
        ortho.open_ortho(write_ortho(tmp_path / "utm31.tif", area, epsg=25831))
    with pytest.raises(OrthoError, match="bands"):
        ortho.open_ortho(write_ortho(tmp_path / "gray.tif", area, count=1))


def sample_like_gltf(rgb: npt.NDArray[np.uint8], uv: npt.NDArray[np.float32]) -> list[int]:
    """Texel under a UV with glTF's convention: ``(0, 0)`` is the top-left corner of the image."""
    height, width, _ = rgb.shape
    col = min(int(uv[0] * width), width - 1)
    row = min(int(uv[1] * height), height - 1)
    return rgb[row, col].tolist()


def test_tile_uvs_land_on_the_matching_corner_of_the_texture(tmp_path: Path) -> None:
    i, j = 1, -3
    x_min, z_min = i * 256 - 0.5, j * 256 - 0.5
    area = LocalRect(x_min, z_min, x_min + 256, z_min + 256)
    photo = write_ortho(tmp_path / "tile.tif", area)
    xs = -599.5 + np.arange(2600, dtype=np.float64)
    zs = -1999.5 + np.arange(2550, dtype=np.float64)
    heights = (10.0 * np.sin(xs[None, :] / 40.0) + 0.0 * zs[:, None]).astype(np.float32)
    mesh = tiles.build_tile(Grid(heights, x0=-599.5, z0=-1999.5), i, j, tiles.LODS[2])
    with ortho.open_ortho(photo) as src:
        texture = ortho.read_texture(src, mesh.extent, 1024)
    assert texture.outside == 0
    surface = mesh.positions[: mesh.surface_vertices]
    north_east = int(np.argmax(surface[:, 0] - surface[:, 2]))
    south_west = int(np.argmin(surface[:, 0] - surface[:, 2]))
    assert (surface[north_east, 0], surface[north_east, 2]) == (x_min + 256, z_min)
    assert (surface[south_west, 0], surface[south_west, 2]) == (x_min, z_min + 256)
    assert sample_like_gltf(texture.rgb, mesh.uvs[north_east]) == list(MARKER_NE)
    assert sample_like_gltf(texture.rgb, mesh.uvs[south_west]) == list(MARKER_SW)
    centre = int(
        np.argmin(np.abs(surface[:, 0] - (x_min + 128)) + np.abs(surface[:, 2] - (z_min + 128)))
    )
    assert sample_like_gltf(texture.rgb, mesh.uvs[centre]) == list(BACKGROUND)
