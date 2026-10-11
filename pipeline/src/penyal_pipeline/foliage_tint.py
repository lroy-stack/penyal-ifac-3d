"""Foliage colour of the generated trees and plants, derived from the reference photographs.

The Poly Haven leaf textures are pale grey-green and the first tint was a green picked by eye,
too saturated for the garrigue and pinewood of the Penyal. Here the colour of each foliage is
measured in two reference photographs (``data/manual/fotos-referencia/commons``, Wikimedia
Commons, 26 and 17) over boxes chosen by hand, and applied as a MULTIPLIER of the texture colour
(a per-vertex colour, which glTF multiplies into the base colour; the textures themselves are not
touched, and one shared material per GLB keeps the draw calls down, which a material factor
could not do for several plants with different colours).

Method, per foliage:

1. The pixels of its boxes are pooled and the brighter half (by the largest channel) is kept: the
   median of a bush includes its own shade, which the renderer's lighting supplies again.
2. The target is the median RGB of those pixels, taken to linear light.
3. The multiplier is ``target / mean linear colour of the opaque texture pixels`` per channel. A
   multiplier cannot brighten, so when the largest channel exceeds 1 all three are divided by it:
   hue and saturation are kept and brightness falls short of the photograph (``kept`` below).

Results (sunlit median sRGB of the photographs, its hue / saturation, the texture's own, and the
share of the photographs' brightness kept; they live in ``FOLIAGE_FACTORS``):

========  ===============  ============  ==============  =====
foliage   photographs      hue / sat     texture hue/sat kept
========  ===============  ============  ==============  =====
pine      120 122  63      62 / 0.48     57 / 0.34       0.44
lentisc   76  70  49       47 / 0.36     67 / 0.32       1.00
rosemary  122 106 77       39 / 0.37     72 / 0.28       0.68
grass     128 109 89       31 / 0.30     64 / 0.34       1.00
========  ===============  ============  ==============  =====

The pine target is a yellow-green olive (hue 62), not the saturated green the first tint gave; the
lentisc, rosemary and grass boxes are dry-season garrigue, brown-olive rather than green. The
rosemary box mixes a low shrub with soil and a dark shrub of photograph 17: it is the weakest
estimate.
"""

import warnings
from collections.abc import Mapping
from pathlib import Path

import numpy as np
import numpy.typing as npt
import rasterio
from rasterio.errors import NotGeoreferencedWarning

type Floats = npt.NDArray[np.float64]

PHOTO_FILES = {
    "26": "26-Le-sentier-du-penon-de-ifach-panoramio.jpg",
    "17": "17-Calpe-panoramio-68.jpg",
}
# foliage: boxes (photo, x0, y0, x1, y1) in pixels of the full-size photograph, chosen by hand
REGIONS: dict[str, list[tuple[str, int, int, int, int]]] = {
    # pine needle masses: bright left pine, upper left pine, pines behind the right shrub (26)
    "pine": [("26", 40, 480, 420, 760), ("26", 180, 140, 520, 300), ("26", 1560, 80, 1840, 240)],
    # dark evergreen shrubs: the bush under the cliff and the one on the right slope (17)
    "lentisc": [("17", 330, 230, 600, 400), ("17", 1330, 760, 1700, 900)],
    # low grey-olive shrub between the fence rails (26) and the right slope scrub (17)
    "rosemary": [("26", 0, 1010, 380, 1150), ("17", 1330, 760, 1700, 900)],
    # dry grass on the left slope of photograph 17
    "grass": [("17", 20, 840, 140, 1120)],
}
# Linear-light RGB multipliers (see the module docstring); ``derive`` reproduces them.
FOLIAGE_FACTORS: dict[str, tuple[float, float, float]] = {
    "pine": (0.907, 1.0, 0.568),
    "lentisc": (0.456, 0.356, 0.399),
    "rosemary": (1.0, 0.655, 0.666),
    "grass": (0.883, 0.595, 0.941),
}


def srgb_to_linear(values: npt.ArrayLike) -> Floats:
    c = np.asarray(values, dtype=np.float64)
    return np.asarray(np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4))


def linear_to_srgb(values: npt.ArrayLike) -> Floats:
    c = np.asarray(values, dtype=np.float64)
    return np.asarray(
        np.where(c <= 0.0031308, c * 12.92, 1.055 * np.maximum(c, 0.0) ** (1 / 2.4) - 0.055)
    )


def sunlit_median(pixels: Floats) -> Floats:
    """Median RGB of the brighter half of ``(n, 3)`` sRGB pixels in 0..1 (the shade is dropped)."""
    value = pixels.max(axis=1)
    return np.asarray(np.median(pixels[value >= np.median(value)], axis=0))


def factor_for(target_linear: Floats, source_linear: Floats) -> Floats:
    """Per-channel multiplier from the texture's linear colour to the target; scaled by its
    largest channel when that would exceed 1 (a multiplier cannot brighten)."""
    raw = np.asarray(target_linear, dtype=np.float64) / np.asarray(source_linear, dtype=np.float64)
    return np.asarray(raw if raw.max() <= 1.0 else raw / raw.max())


def read_photo(path: Path) -> npt.NDArray[np.uint8]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with rasterio.open(path) as src:
            return np.asarray(src.read().transpose(1, 2, 0), dtype=np.uint8)


def derive(photo_dir: Path, sources: Mapping[str, Floats]) -> dict[str, Floats]:
    """The multipliers from the photographs and the textures' mean linear colour per foliage."""
    photos = {key: read_photo(photo_dir / name) for key, name in PHOTO_FILES.items()}
    derived = {}
    for name, boxes in REGIONS.items():
        pooled = np.concatenate(
            [photos[p][y0:y1, x0:x1].reshape(-1, 3) for p, x0, y0, x1, y1 in boxes]
        ).astype(np.float64)
        target = sunlit_median(pooled / 255.0)
        derived[name] = factor_for(srgb_to_linear(target), sources[name])
    return derived
