"""Orthophoto windows for terrain textures.

The ICV orthophoto is RGB+NIR, 8 bit, 25 cm, EPSG:25830. Web textures use the RGB bands only;
the NIR band stays out of every output (it feeds vegetation masks later). Windows are expressed
in the local frame (ADR 0004) as ``(x_min, z_min, x_max, z_max)`` and returned top-down: row 0 is
the north edge (``z_min``) and column 0 the west edge (``x_min``), the layout of an image file.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
import rasterio
from rasterio.enums import Resampling
from rasterio.io import DatasetReader
from rasterio.windows import Window

from penyal_pipeline.geo import ORIGIN_E, ORIGIN_N
from penyal_pipeline.rawdata import RawFile, locate

log = logging.getLogger(__name__)

ORTHO_SOURCE_ID = "icv-orto-2024-0848-7-2"
ORTHO_SUFFIX = ".tif"
EPSG = 25830
RGB_BANDS = (1, 2, 3)
# Neutral Mediterranean blue for pixels outside the image (none expected inside the work area).
SEA_RGB = (24, 56, 80)

type Rgb = npt.NDArray[np.uint8]


class OrthoError(RuntimeError):
    """The orthophoto does not match what the pipeline expects."""


@dataclass(frozen=True)
class LocalRect:
    """A rectangle in the local frame, ``x`` east and ``z`` south."""

    x_min: float
    z_min: float
    x_max: float
    z_max: float


@dataclass(frozen=True)
class TextureRead:
    """``rgb`` is ``(size, size, 3)`` uint8, top-down; ``outside`` counts sea-filled pixels."""

    rgb: Rgb
    outside: int


def locate_ortho() -> RawFile:
    return locate(ORTHO_SOURCE_ID, ORTHO_SUFFIX)


def open_ortho(path: Path) -> DatasetReader:
    """Open the orthophoto, checking CRS, band count and north-up orientation."""
    src = rasterio.open(path)
    if src.crs is None or src.crs.to_epsg() != EPSG:
        src.close()
        raise OrthoError(f"{path.name}: CRS is {src.crs}, expected EPSG:{EPSG}")
    if src.count < 3 or src.dtypes[0] != "uint8":
        src.close()
        raise OrthoError(f"{path.name}: expected >= 3 uint8 bands, got {src.count} {src.dtypes}")
    transform = src.transform
    if transform.b != 0 or transform.d != 0 or transform.e >= 0:
        src.close()
        raise OrthoError(f"{path.name}: raster is not north-up and axis-aligned: {transform}")
    return src


def pixel_window(src: DatasetReader, area: LocalRect) -> Window:
    """The (fractional) pixel window of ``area`` in the orthophoto."""
    transform = src.transform
    east_min = ORIGIN_E + area.x_min
    east_max = ORIGIN_E + area.x_max
    north_top = ORIGIN_N - area.z_min
    north_bottom = ORIGIN_N - area.z_max
    col = (east_min - transform.c) / transform.a
    row = (north_top - transform.f) / transform.e
    width = (east_max - east_min) / transform.a
    height = (north_top - north_bottom) / -transform.e
    return Window.from_slices((row, row + height), (col, col + width), boundless=True)


def covers(src: DatasetReader, area: LocalRect) -> bool:
    """Whether ``area`` lies completely inside the image."""
    window = pixel_window(src, area)
    return bool(
        window.col_off >= 0
        and window.row_off >= 0
        and window.col_off + window.width <= src.width
        and window.row_off + window.height <= src.height
    )


def read_texture(src: DatasetReader, area: LocalRect, size: int) -> TextureRead:
    """RGB of ``area`` resampled (area average) to ``size`` x ``size``; outside pixels are sea."""
    window = pixel_window(src, area)
    data = src.read(
        list(RGB_BANDS),
        window=window,
        out_shape=(len(RGB_BANDS), size, size),
        resampling=Resampling.average,
        boundless=True,
        masked=True,
    )
    outside_mask = np.ma.getmaskarray(data).any(axis=0)
    rgb = np.ma.getdata(data).transpose(1, 2, 0).astype(np.uint8)
    rgb[outside_mask] = SEA_RGB
    return TextureRead(rgb=np.ascontiguousarray(rgb), outside=int(outside_mask.sum()))
