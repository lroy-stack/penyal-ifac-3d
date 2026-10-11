"""DEM preparation: clip the ICV MDT, fill the sea with a seabed proxy, write heightfields.

Heights are metres (orthometric, ADR 0004). Grids are 1 m, row 0 is the northmost row and
column 0 the westmost; ``x0``/``z0`` are the local coordinates of the CENTRE of cell [0, 0],
so cell ``(r, c)`` is centred at ``x = x0 + c * cell``, ``z = z0 + r * cell``.
Land heights are never altered. The MDT holds exactly 0.0 m over water, so cells inside the
official CV05 sea polygon whose height is within ``SEA_LEVEL_TOLERANCE`` of sea level, and
nodata cells, get the constant ``SEA_FILL_HEIGHT`` (an approximation of the seabed).
"""

import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import laspy
import numpy as np
import numpy.typing as npt
import rasterio
from rasterio.features import rasterize
from rasterio.transform import Affine, from_origin
from rasterio.windows import Window
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from penyal_pipeline.geo import ORIGIN_E, ORIGIN_N
from penyal_pipeline.paths import TERRAIN_BUILD_DIR, TERRAIN_GENERATED_DIR
from penyal_pipeline.rawdata import RawFile, locate

log = logging.getLogger(__name__)

WORK_BBOX = (766400.0, 4279450.0, 769000.0, 4282000.0)  # EPSG:25830 (e_min, n_min, e_max, n_max)
CELL_SIZE = 1.0
EPSG = 25830
SEA_FILL_HEIGHT = -3.0
SEA_LEVEL_TOLERANCE = 0.1
SEA_POLYGON_NAME = "Mar Mediterrani"
QUANT_SCALE = 0.01  # collision heights: 1 cm steps
MDT_SOURCE_ID = "icv-mdt-2016-0848"
MDT_SUFFIX = ".tif"
CV05_SOURCE_ID = "icv-cv05-penyal"
CV05_HYDROGRAPHY = "HidrografiaBCV05.geojson"
LIDAR_SOURCE_IDS = (
    "icv-lidar-2016-766-4280",
    "icv-lidar-2016-766-4282",
    "icv-lidar-2016-768-4280",
    "icv-lidar-2016-768-4282",
)
LIDAR_GROUND_CLASS = 2
GENTLE_SLOPE_DEGREES = 30.0
LIDAR_NOISE_RANGE = (-5.0, 340.0)  # metres; the 2016 tiles hold points down to -97 m

type HeightGrid = npt.NDArray[np.float32]


class DemError(RuntimeError):
    """The source raster does not match what the pipeline expects."""


@dataclass(frozen=True)
class Grid:
    """A regular height grid in the local frame (see module docstring for conventions)."""

    heights: HeightGrid
    x0: float
    z0: float
    cell: float = CELL_SIZE

    @property
    def height(self) -> int:
        return int(self.heights.shape[0])

    @property
    def width(self) -> int:
        return int(self.heights.shape[1])

    def sample(self, x: npt.ArrayLike, z: npt.ArrayLike) -> npt.NDArray[np.float64]:
        """Bilinear height at local ``(x, z)``; positions outside the grid are clamped."""
        fc = np.clip((np.asarray(x, dtype=np.float64) - self.x0) / self.cell, 0, self.width - 1)
        fr = np.clip((np.asarray(z, dtype=np.float64) - self.z0) / self.cell, 0, self.height - 1)
        c0 = np.minimum(np.floor(fc).astype(np.intp), self.width - 2)
        r0 = np.minimum(np.floor(fr).astype(np.intp), self.height - 2)
        tc, tr = fc - c0, fr - r0
        h = self.heights.astype(np.float64)
        top = h[r0, c0] * (1 - tc) + h[r0, c0 + 1] * tc
        bottom = h[r0 + 1, c0] * (1 - tc) + h[r0 + 1, c0 + 1] * tc
        return top * (1 - tr) + bottom * tr


# Trail code only needs the sampling interface.
Dem = Grid


def bbox_to_window(
    transform: Affine, bbox: tuple[float, float, float, float]
) -> tuple[int, int, int, int]:
    """``(col_off, row_off, width, height)`` of the pixels covering ``bbox``.

    The raster must be north-up and axis-aligned, and ``bbox`` must align to whole pixels.
    """
    if transform.b != 0 or transform.d != 0 or transform.e >= 0:
        raise DemError(f"raster is not north-up and axis-aligned: {transform}")
    e_min, n_min, e_max, n_max = bbox
    col = (e_min - transform.c) / transform.a
    row = (n_max - transform.f) / transform.e
    width = (e_max - e_min) / transform.a
    height = (n_max - n_min) / -transform.e
    for name, value in (("col", col), ("row", row), ("width", width), ("height", height)):
        if abs(value - round(value)) > 1e-6:
            raise DemError(f"bbox {bbox} is not aligned to the pixel grid ({name}={value})")
    return round(col), round(row), round(width), round(height)


def read_window(
    path: Path, bbox: tuple[float, float, float, float] = WORK_BBOX
) -> tuple[HeightGrid, int]:
    """Read the ``bbox`` window; returns heights (NaN where nodata) and the nodata cell count."""
    with rasterio.open(path) as src:
        if src.crs is None or src.crs.to_epsg() != EPSG:
            raise DemError(f"{path.name}: CRS is {src.crs}, expected EPSG:{EPSG}")
        if (abs(src.res[0] - CELL_SIZE) > 1e-9) or (abs(src.res[1] - CELL_SIZE) > 1e-9):
            raise DemError(f"{path.name}: pixel size is {src.res}, expected {CELL_SIZE} m")
        col, row, width, height = bbox_to_window(src.transform, bbox)
        if col < 0 or row < 0 or col + width > src.width or row + height > src.height:
            raise DemError(f"{path.name}: bbox {bbox} is not fully inside the raster")
        window = Window.from_slices((row, row + height), (col, col + width))
        data = src.read(1, window=window).astype(np.float32)
        nodata = src.nodata
    mask = np.isnan(data) if nodata is None else (data == np.float32(nodata)) | np.isnan(data)
    data[mask] = np.nan
    return data, int(mask.sum())


def load_sea_polygon(cv05_hydrography: Path) -> BaseGeometry:
    """The CV05 ``Mar Mediterrani`` polygon (EPSG:25830)."""
    collection = json.loads(cv05_hydrography.read_text(encoding="utf-8"))
    seas = [
        shape(f["geometry"])
        for f in collection["features"]
        if f["properties"].get("texto") == SEA_POLYGON_NAME and f["geometry"]
    ]
    if len(seas) != 1:
        raise DemError(f"expected one {SEA_POLYGON_NAME!r} polygon in {cv05_hydrography.name}")
    return seas[0]


def rasterize_sea(
    sea: BaseGeometry, shape_hw: tuple[int, int], bbox: tuple[float, float, float, float]
) -> npt.NDArray[np.bool_]:
    """Cells whose centre lies inside ``sea``."""
    transform = from_origin(bbox[0], bbox[3], CELL_SIZE, CELL_SIZE)
    burned = rasterize([(sea, 1)], out_shape=shape_hw, transform=transform, fill=0, dtype="uint8")
    return np.asarray(burned, dtype=np.bool_)


def fill_sea(
    heights: HeightGrid, sea_mask: npt.NDArray[np.bool_]
) -> tuple[HeightGrid, dict[str, int]]:
    """Replace nodata and sea-level cells inside the sea polygon with the seabed proxy."""
    nodata = np.isnan(heights)
    sea = sea_mask & ~nodata & (heights <= SEA_LEVEL_TOLERANCE)
    out = heights.copy()
    out[nodata | sea] = np.float32(SEA_FILL_HEIGHT)
    return out, {"seaCells": int(sea.sum()), "nodataCells": int(nodata.sum())}


def local_origin(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    """Local ``(x0, z0)`` of the centre of the north-west cell of a grid covering ``bbox``."""
    return bbox[0] + CELL_SIZE / 2 - ORIGIN_E, -(bbox[3] - CELL_SIZE / 2 - ORIGIN_N)


def metadata(grid: Grid, source: dict[str, Any], sea_fill: dict[str, Any]) -> dict[str, Any]:
    return {
        "crs": f"EPSG:{EPSG}",
        "origin": {"e": int(ORIGIN_E), "n": int(ORIGIN_N)},
        "cellSize": grid.cell,
        "width": grid.width,
        "height": grid.height,
        "x0": grid.x0,
        "z0": grid.z0,
        "minHeight": round(float(grid.heights.min()), 3),
        "maxHeight": round(float(grid.heights.max()), 3),
        "rowOrder": "north-to-south",
        "columnOrder": "west-to-east",
        "seaFill": sea_fill,
        "source": source,
    }


def write_dem(
    directory: Path, grid: Grid, source: dict[str, Any], sea_fill: dict[str, Any]
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "dem.f32").write_bytes(grid.heights.astype("<f4").tobytes())
    (directory / "dem.json").write_text(
        json.dumps(metadata(grid, source, sea_fill), indent=2) + "\n", encoding="utf-8"
    )


def load_dem(directory: Path = TERRAIN_BUILD_DIR) -> tuple[Grid, dict[str, Any]]:
    meta = json.loads((directory / "dem.json").read_text(encoding="utf-8"))
    flat = np.fromfile(directory / "dem.f32", dtype="<f4")
    if flat.size != meta["width"] * meta["height"]:
        raise DemError(
            f"{directory / 'dem.f32'} does not match dem.json ({meta['width']}x{meta['height']})"
        )
    heights = flat.reshape(meta["height"], meta["width"]).astype(np.float32)
    return Grid(heights, meta["x0"], meta["z0"], meta["cellSize"]), meta


def crop(grid: Grid, bounds: tuple[float, float, float, float]) -> Grid:
    """Sub-grid covering local ``(x_min, z_min, x_max, z_max)``, snapped outwards to whole cells."""
    x_min, z_min, x_max, z_max = bounds
    left = grid.x0 - grid.cell / 2
    top = grid.z0 - grid.cell / 2
    c0 = max(0, math.floor((x_min - left) / grid.cell))
    c1 = min(grid.width, math.ceil((x_max - left) / grid.cell))
    r0 = max(0, math.floor((z_min - top) / grid.cell))
    r1 = min(grid.height, math.ceil((z_max - top) / grid.cell))
    if c1 <= c0 or r1 <= r0:
        raise DemError(f"bounds {bounds} do not overlap the DEM")
    return Grid(
        grid.heights[r0:r1, c0:c1].copy(),
        grid.x0 + c0 * grid.cell,
        grid.z0 + r0 * grid.cell,
        grid.cell,
    )


def quantise(
    heights: HeightGrid, scale: float = QUANT_SCALE
) -> tuple[npt.NDArray[np.uint16], float]:
    """Heights to uint16 steps of ``scale`` above ``heightOffset`` (returned)."""
    offset = math.floor(float(heights.min()) / scale) * scale
    steps = np.rint((heights.astype(np.float64) - offset) / scale)
    if steps.max() > np.iinfo(np.uint16).max:
        raise DemError(f"height range does not fit uint16 at {scale} m steps")
    return steps.astype(np.uint16), round(offset, 6)


def dequantise(
    steps: npt.NDArray[np.uint16], offset: float, scale: float = QUANT_SCALE
) -> npt.NDArray[np.float64]:
    return offset + steps.astype(np.float64) * scale


def write_collision(
    directory: Path,
    grid: Grid,
    source: dict[str, Any],
    sea_fill: dict[str, Any],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    """Write ``collision.bin`` (uint16 little-endian) and ``collision.json``.

    ``provenance`` is the ``inputs`` / ``tools`` block recorded in the json.
    """
    steps, offset = quantise(grid.heights)
    meta = metadata(grid, source, sea_fill)
    meta.update({"dtype": "uint16le", "heightOffset": offset, "heightScale": QUANT_SCALE})
    meta.update(provenance)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "collision.bin").write_bytes(steps.astype("<u2").tobytes())
    (directory / "collision.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def load_collision(directory: Path = TERRAIN_GENERATED_DIR) -> tuple[Grid, dict[str, Any]]:
    """Read back ``collision.bin`` as float heights (dequantised)."""
    meta = json.loads((directory / "collision.json").read_text(encoding="utf-8"))
    steps = np.fromfile(directory / "collision.bin", dtype="<u2").reshape(
        meta["height"], meta["width"]
    )
    heights = dequantise(steps, meta["heightOffset"], meta["heightScale"]).astype(np.float32)
    return Grid(heights, meta["x0"], meta["z0"], meta["cellSize"]), meta


def summit_cells(grid: Grid) -> dict[str, float]:
    """Location and height of the highest cell, as local coordinates and UTM."""
    r, c = np.unravel_index(int(np.argmax(grid.heights)), grid.heights.shape)
    x, z = grid.x0 + c * grid.cell, grid.z0 + r * grid.cell
    return {
        "height": float(grid.heights[r, c]),
        "x": x,
        "z": z,
        "e": x + ORIGIN_E,
        "n": ORIGIN_N - z,
    }


def source_record(raw: RawFile) -> dict[str, Any]:
    return {"id": raw.source_id, "file": raw.path.name, "sha256": raw.sha256}


@dataclass(frozen=True)
class DemBuild:
    grid: Grid
    meta: dict[str, Any]
    source: dict[str, Any]
    sea_fill: dict[str, Any]


def build_dem(mdt: RawFile, cv05_hydrography: RawFile) -> DemBuild:
    raw_heights, _ = read_window(mdt.path)
    sea = rasterize_sea(load_sea_polygon(cv05_hydrography.path), raw_heights.shape, WORK_BBOX)
    heights, counts = fill_sea(raw_heights, sea)
    x0, z0 = local_origin(WORK_BBOX)
    grid = Grid(heights, x0, z0)
    source = source_record(mdt)
    sea_fill = {
        "height": SEA_FILL_HEIGHT,
        "approximate": True,
        "rule": (
            f"cells inside the CV05 '{SEA_POLYGON_NAME}' polygon with MDT height <= "
            f"{SEA_LEVEL_TOLERANCE} m, plus nodata cells, are set to the constant; "
            "land heights are untouched. The MDT holds 0.0 m over water, so this is a "
            "seabed proxy, not a measurement."
        ),
        "levelTolerance": SEA_LEVEL_TOLERANCE,
        "maskSource": {
            "id": CV05_SOURCE_ID,
            "file": CV05_HYDROGRAPHY,
            "sha256": cv05_hydrography.sha256,
        },
        **counts,
    }
    return DemBuild(grid, metadata(grid, source, sea_fill), source, sea_fill)


def slope_degrees(grid: Grid) -> npt.NDArray[np.float64]:
    """Slope of every cell in degrees from central differences."""
    dz_dr, dz_dc = np.gradient(grid.heights.astype(np.float64), grid.cell)
    return np.degrees(np.arctan(np.hypot(dz_dr, dz_dc)))


@dataclass(frozen=True)
class LidarSamples:
    """LiDAR ground points (class 2) compared with the DEM."""

    errors: npt.NDArray[np.float64]  # LiDAR z minus bilinear DEM height
    slopes: npt.NDArray[np.float64]  # DEM slope (degrees) at the nearest cell
    x: npt.NDArray[np.float64]
    z: npt.NDArray[np.float64]
    noise: int  # points dropped for z outside LIDAR_NOISE_RANGE


def lidar_ground_samples(
    grid: Grid, laz_paths: list[Path], bounds: tuple[float, float, float, float]
) -> LidarSamples:
    """Ground points inside local ``bounds`` (x_min, z_min, x_max, z_max), noise removed."""
    x_min, z_min, x_max, z_max = bounds
    slopes = slope_degrees(grid)
    parts: list[tuple[npt.NDArray[np.float64], ...]] = []
    noise = 0
    for path in laz_paths:
        las = laspy.read(path)
        ground = np.asarray(las.classification) == LIDAR_GROUND_CLASS
        x = np.asarray(las.x, dtype=np.float64) - ORIGIN_E
        z = -(np.asarray(las.y, dtype=np.float64) - ORIGIN_N)
        y = np.asarray(las.z, dtype=np.float64)
        inside = ground & (x >= x_min) & (x <= x_max) & (z >= z_min) & (z <= z_max)
        plausible = (y >= LIDAR_NOISE_RANGE[0]) & (y <= LIDAR_NOISE_RANGE[1])
        noise += int((inside & ~plausible).sum())
        keep = inside & plausible
        kx, kz = x[keep], z[keep]
        rows = np.clip(np.rint((kz - grid.z0) / grid.cell), 0, grid.height - 1).astype(np.intp)
        cols = np.clip(np.rint((kx - grid.x0) / grid.cell), 0, grid.width - 1).astype(np.intp)
        parts.append((y[keep] - grid.sample(kx, kz), slopes[rows, cols], kx, kz))
    cat = [np.concatenate([p[i] for p in parts]) for i in range(4)]
    return LidarSamples(cat[0], cat[1], cat[2], cat[3], noise)


def error_stats(errors: npt.NDArray[np.float64]) -> dict[str, float]:
    return {
        "count": float(errors.size),
        "mean": float(errors.mean()),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "maxAbs": float(np.abs(errors).max()),
        "p95Abs": float(np.percentile(np.abs(errors), 95)),
    }


def lidar_paths() -> list[Path]:
    return [locate(source_id, ".laz").path for source_id in LIDAR_SOURCE_IDS]


def locate_inputs() -> tuple[RawFile, RawFile]:
    return locate(MDT_SOURCE_ID, MDT_SUFFIX), locate(CV05_SOURCE_ID, CV05_HYDROGRAPHY)
