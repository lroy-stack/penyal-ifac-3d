"""The minimap image: the ICV 2024 orthophoto cropped around the walkable corridor (spec 004, X1.1).

One north-up JPEG at 0.5 m per pixel covering the bounding box of ``trail.json``
``corridor.polygon`` plus a margin, and ``minimap.json`` with its local-frame bounds so the app
can place the player and the points of interest on it (``u = (x - x0) / (x1 - x0)``,
``v = (z - z0) / (z1 - z0)``, row 0 is the north edge ``z0``, column 0 the west edge ``x0``).

**Why JPEG:** every browser decodes it natively (``Image`` / ``createImageBitmap`` /
``TextureLoader``), so the app needs no new decoder, and for an aerial photograph it is smaller
than lossy WebP at similar quality (measured on this crop: 664 KB against 733 KB). PNG would be
several MB. The encoder is GDAL's libjpeg through rasterio (already a dependency): the same input
and library give the same bytes, and the output carries no georeferencing or timestamps. The JPEG
is progressive. Its quality is the highest one whose file fits :data:`MAX_IMAGE_BYTES`, searched
deterministically, and is recorded in the manifest.

Only bands 1-3 (RGB) are read; the NIR band stays out. Each pixel is the area average of 2 x 2
pixels of the 25 cm orthophoto.
"""

import hashlib
import json
import logging
import math
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import rasterio
from rasterio.shutil import copy as raster_copy
from rasterio.transform import from_origin

from penyal_pipeline import ortho
from penyal_pipeline.geo import ORIGIN_E, ORIGIN_N
from penyal_pipeline.paths import GENERATED_DIR, TRAIL_GENERATED

log = logging.getLogger(__name__)

MINIMAP_GENERATED_DIR = GENERATED_DIR / "minimap"
IMAGE_NAME = "minimap.jpg"
MANIFEST_NAME = "minimap.json"
METRES_PER_PIXEL = 0.5
MARGIN_M = 60.0
MAX_IMAGE_BYTES = 600_000
MIN_QUALITY = 40
MAX_QUALITY = 95
LICENCE = "CC-BY-4.0"
ATTRIBUTION = "© Institut Cartogràfic Valencià, CC BY 4.0"

type Rgb = npt.NDArray[np.uint8]
type Encoder = Callable[[int], bytes]


class MinimapError(RuntimeError):
    """The corridor, the orthophoto or the size cap do not allow the minimap."""


@dataclass(frozen=True)
class Bounds:
    """The image extent in the local frame (``x`` east, ``z`` south), aligned to whole pixels."""

    x0: float
    z0: float
    x1: float
    z1: float
    metres_per_pixel: float

    @property
    def width(self) -> int:
        return round((self.x1 - self.x0) / self.metres_per_pixel)

    @property
    def height(self) -> int:
        return round((self.z1 - self.z0) / self.metres_per_pixel)

    def rect(self) -> ortho.LocalRect:
        return ortho.LocalRect(self.x0, self.z0, self.x1, self.z1)

    def contains(self, x: float, z: float) -> bool:
        return self.x0 <= x <= self.x1 and self.z0 <= z <= self.z1

    def to_pixel(self, x: float, z: float) -> tuple[float, float]:
        """``(column, row)`` of a local point; fractional, a pixel's top-left corner is integral."""
        return (x - self.x0) / self.metres_per_pixel, (z - self.z0) / self.metres_per_pixel

    def from_pixel(self, column: float, row: float) -> tuple[float, float]:
        """The local ``(x, z)`` of an image position (inverse of :meth:`to_pixel`)."""
        return self.x0 + column * self.metres_per_pixel, self.z0 + row * self.metres_per_pixel


def crop_bounds(
    polygon: Sequence[Sequence[float]],
    margin: float = MARGIN_M,
    metres_per_pixel: float = METRES_PER_PIXEL,
) -> Bounds:
    """Bounding box of ``polygon`` grown by ``margin``, snapped outwards to the pixel grid."""
    if len(polygon) < 3:
        raise MinimapError(f"the corridor polygon has {len(polygon)} points, expected >= 3")
    xs = [float(point[0]) for point in polygon]
    zs = [float(point[1]) for point in polygon]
    step = metres_per_pixel
    return Bounds(
        x0=math.floor((min(xs) - margin) / step) * step,
        z0=math.floor((min(zs) - margin) / step) * step,
        x1=math.ceil((max(xs) + margin) / step) * step,
        z1=math.ceil((max(zs) + margin) / step) * step,
        metres_per_pixel=step,
    )


def fit_quality(
    encode: Encoder,
    max_bytes: int = MAX_IMAGE_BYTES,
    low: int = MIN_QUALITY,
    high: int = MAX_QUALITY,
) -> tuple[int, bytes]:
    """The highest quality in ``low..high`` whose encoding fits ``max_bytes`` (size is monotone)."""
    best: tuple[int, bytes] | None = None
    floor = low
    while low <= high:
        quality = (low + high) // 2
        data = encode(quality)
        if len(data) <= max_bytes:
            best = (quality, data)
            low = quality + 1
        else:
            high = quality - 1
    if best is None:
        raise MinimapError(
            f"the image does not fit {max_bytes} bytes even at quality {floor}: "
            "shrink the margin or coarsen the pixel size"
        )
    return best


def encode_jpeg(rgb: Rgb, quality: int) -> bytes:
    """Progressive JPEG of a ``(height, width, 3)`` uint8 image, no metadata."""
    height, width, _ = rgb.shape
    bands = np.ascontiguousarray(rgb.transpose(2, 0, 1))
    # JPEG stores no georeferencing; a transform only avoids GDAL's "no geotransform" warning
    transform = from_origin(0.0, 0.0, 0.5, 0.5)
    with (
        rasterio.MemoryFile() as memory,
        tempfile.TemporaryDirectory(prefix="minimap-") as scratch,
    ):
        with memory.open(
            driver="GTiff", width=width, height=height, count=3, dtype="uint8", transform=transform
        ) as tmp:
            tmp.write(bands)
        target = Path(scratch) / IMAGE_NAME
        with memory.open() as tmp:
            raster_copy(tmp, str(target), driver="JPEG", QUALITY=quality, PROGRESSIVE="YES")
        return target.read_bytes()


def load_corridor(trail_json: Path = TRAIL_GENERATED) -> tuple[list[list[float]], dict[str, Any]]:
    """The corridor polygon and the anchors of ``trail.json``."""
    if not trail_json.is_file():
        raise MinimapError(f"{trail_json} is missing: run `penyal trail` first")
    document = json.loads(trail_json.read_text(encoding="utf-8"))
    polygon = document.get("corridor", {}).get("polygon")
    if not isinstance(polygon, list):
        raise MinimapError(f"{trail_json.name} has no corridor.polygon: regenerate it")
    return polygon, document.get("anchors", {})


def build_manifest(
    bounds: Bounds, image: dict[str, Any], provenance: dict[str, Any]
) -> dict[str, Any]:
    return {
        "version": 1,
        "licence": LICENCE,
        "attribution": ATTRIBUTION,
        "frame": {"crs": "EPSG:25830", "origin": {"e": int(ORIGIN_E), "n": int(ORIGIN_N)}},
        "bounds": {"x0": bounds.x0, "z0": bounds.z0, "x1": bounds.x1, "z1": bounds.z1},
        "metresPerPixel": bounds.metres_per_pixel,
        "size": {"width": bounds.width, "height": bounds.height},
        "marginM": MARGIN_M,
        "rows": "row 0 is the north edge (z0), column 0 the west edge (x0); north is up",
        "image": image,
        **provenance,
    }


def run_minimap(
    out_dir: Path = MINIMAP_GENERATED_DIR,
    provenance: dict[str, Any] | None = None,
    trail_json: Path = TRAIL_GENERATED,
) -> dict[str, Any]:
    """Write ``minimap.jpg`` and ``minimap.json`` into ``out_dir``."""
    polygon, anchors = load_corridor(trail_json)
    bounds = crop_bounds(polygon)
    for name, anchor in anchors.items():
        if not bounds.contains(anchor["x"], anchor["z"]):
            raise MinimapError(f"anchor {name} lies outside the minimap bounds")
    with ortho.open_ortho(ortho.locate_ortho().path) as src:
        if not ortho.covers(src, bounds.rect()):
            raise MinimapError("the orthophoto does not cover the minimap bounds")
        texture = ortho.read_rgb(src, bounds.rect(), bounds.width, bounds.height)
    quality, data = fit_quality(lambda q: encode_jpeg(texture.rgb, q))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / IMAGE_NAME).write_bytes(data)
    image = {
        "url": IMAGE_NAME,
        "format": "jpeg",
        "progressive": True,
        "quality": quality,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    manifest = build_manifest(bounds, image, provenance or {"inputs": [], "tools": {}})
    (out_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    log.info(
        "%s: %dx%d px, %d bytes, q%d", IMAGE_NAME, bounds.width, bounds.height, len(data), quality
    )
    return manifest
