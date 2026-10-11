"""Surface-class masks for the terrain material, from OpenStreetMap ways (spec 003, E1.1).

One RGBA8 KTX2 (UASTC) per near terrain tile (``t_{i}_{j}.ktx2``), at 0.25 m per pixel, so
1024 x 1024 pixels for a 256 m tile. Only tiles with at least one covered pixel are written.

**Why this layout** (what ``terrain/material.ts`` can sample most cheaply): the image is aligned
with the terrain tile's mesh extent and rows run north to south exactly like the orthophoto, so
the shader reuses the tile's own UV (``u = (x - x_min) / 256``, ``v = (z - z_min) / 256``): one
texture read, no per-tile transform, no extra draw call. The four channels are independent
coverages in 0..1 of the four classes in :data:`CLASSES` (R, G, B, A); hardware bilinear
filtering then blends both the soft edge and the transition between two classes correctly, which
a class-id channel could not do. After compositing, the four channels of a pixel sum to at most 1
(255), and ``1 - sum`` is the share of bare terrain. Load it as data, not as colour: the KTX2
carries a linear transfer function (no sRGB), the A channel is the asphalt coverage and must not
be premultiplied, ``flipY = false`` (glTF convention).

**Why KTX2 UASTC and not PNG:** a browser may premultiply the alpha of a PNG decoded through an
``HTMLImageElement`` and wipe RGB where A = 0 (asphalt is A), and a decoded RGBA8 tile is 4 MiB
of GPU memory (8 tiles = 32 MiB) against about 1 MiB per tile once UASTC is transcoded to ASTC 4x4
or BC7. UASTC, not ETC1S: ETC1S mixes channels. Only the tiles the player has resident load their
mask; the manifest lists which tiles exist. The PNG is only the intermediate fed to ``ktx create``.

**Classes.** ``dirt``, ``ground``, ``gravel`` and ``compacted`` are merged into one class,
``compacted``: they are unbound earth or fines surfaces that look alike at the resolution of a
1k texture, and nothing in the data (no photographs of them) tells them apart; the single channel
keeps one texture tap for four classes. The OSM value of every way stays in the manifest. ``sett``
and ``paving_stones`` are merged for the same reason. Ways without a ``surface`` tag, ``rock``
(the terrain already is rock) and ``concrete`` (two nodes, no evidence of its look) paint
nothing: no surface is invented.

**Widths are provisional.** OSM has no widths for these ways, so :data:`HIGHWAY_WIDTHS` holds one
approximate width per ``highway`` value, listed in ``CREDITS.md`` until the tape measurements of
``docs/specs/002/protocolo-fotos.md`` replace them (a ``width`` tag in OSM wins over the table).
Everything is derived from OpenStreetMap (ODbL 1.0).
"""

import hashlib
import json
import logging
import math
import re
import shutil
import struct
import subprocess
import tempfile
import zlib
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from penyal_pipeline import tiles
from penyal_pipeline.geo import ORIGIN_E, ORIGIN_N
from penyal_pipeline.ortho import LocalRect
from penyal_pipeline.paths import GENERATED_DIR, REPO_ROOT
from penyal_pipeline.rawdata import locate
from penyal_pipeline.trail import ATTRIBUTION, LICENCE, OSM_FILE, OSM_SOURCE_ID, OsmData, load_osm

log = logging.getLogger(__name__)

SURFACES_GENERATED_DIR = GENERATED_DIR / "surfaces"
MANIFEST_NAME = "manifest.json"

CELL_SIZE = 0.25  # metres per pixel
TILE_PIXELS = round(tiles.NEAR_TILE_SIZE / CELL_SIZE)
EDGE_FALLOFF = 0.75  # metres: coverage goes from 1 to 0 across this distance, centred on the edge

# Channel order of the mask: R, G, B, A.
CLASSES = ("unhewn_cobblestone", "compacted", "paving_stones", "asphalt")
# Later classes are painted over earlier ones where ways cross.
PAINT_ORDER = ("compacted", "unhewn_cobblestone", "paving_stones", "asphalt")

SURFACE_CLASS: dict[str, str] = {
    "unhewn_cobblestone": "unhewn_cobblestone",
    "compacted": "compacted",
    "dirt": "compacted",
    "ground": "compacted",
    "gravel": "compacted",
    "paving_stones": "paving_stones",
    "sett": "paving_stones",
    "asphalt": "asphalt",
}

# Linear data, never sRGB; UASTC (not ETC1S, which mixes channels) with Zstandard; one thread and
# no RDO so that the output is deterministic. The mip chain is box filtered (a coverage average).
KTX_CREATE_ARGS = [
    "--format",
    "R8G8B8A8_UNORM",
    "--assign-tf",
    "linear",
    "--assign-primaries",
    "none",
    "--encode",
    "uastc",
    "--uastc-quality",
    "2",
    "--zstd",
    "19",
    "--generate-mipmap",
    "--mipmap-filter",
    "box",
    "--threads",
    "1",
]

WIDTHS_STATUS = "provisional"
# PROVISIONAL widths in metres per OSM ``highway`` value: approximations, not measurements. They
# are listed in CREDITS.md and are replaced by the user's tape measurements (spec 003, E1).
HIGHWAY_WIDTHS: dict[str, float] = {
    "footway": 2.0,
    "path": 1.2,
    "steps": 1.5,
    "pedestrian": 4.0,
    "service": 3.0,
    "track": 3.0,
    "residential": 6.0,
}

type Mask = npt.NDArray[np.uint8]
type Float2 = npt.NDArray[np.float64]


class SurfacesError(RuntimeError):
    """The surface masks cannot be built or violate a contract."""


@dataclass(frozen=True)
class SurfaceWay:
    """An OSM way that paints a surface class, polyline in the local ``(x, z)`` frame."""

    way_id: int
    highway: str
    surface: str
    surface_class: str
    width: float
    width_source: str  # "osm" (a width tag) or "table" (HIGHWAY_WIDTHS, provisional)
    xz: Float2


def surface_class(surface: str | None) -> str | None:
    """The mask class that paints an OSM ``surface`` value, or None when it paints nothing."""
    return None if surface is None else SURFACE_CLASS.get(surface)


def tile_rect(i: int, j: int) -> LocalRect:
    """Mesh extent of near tile ``(i, j)``, half a DEM cell off the nominal grid (see ``tiles``)."""
    x_min = i * tiles.NEAR_TILE_SIZE + tiles.LATTICE_SHIFT
    z_min = j * tiles.NEAR_TILE_SIZE + tiles.LATTICE_SHIFT
    return LocalRect(x_min, z_min, x_min + tiles.NEAR_TILE_SIZE, z_min + tiles.NEAR_TILE_SIZE)


def _width_tag(tags: dict[str, str]) -> float | None:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(?:m)?\s*", tags.get("width", ""))
    return None if match is None else float(match.group(1))


def _near_box_overlaps(xz: Float2) -> bool:
    low, high = xz.min(axis=0), xz.max(axis=0)
    return bool(
        high[0] >= tiles.NEAR_X_MIN
        and low[0] <= tiles.NEAR_X_MAX
        and high[1] >= tiles.NEAR_Z_MIN
        and low[1] <= tiles.NEAR_Z_MAX
    )


def select_ways(osm: OsmData) -> tuple[list[SurfaceWay], dict[str, int]]:
    """The ``highway`` ways of the near box that paint a surface, and why the others do not."""
    skipped = {
        "outsideNearBox": 0,
        "noSurfaceTag": 0,
        "surfaceWithoutOverlay": 0,
        "highwayWithoutWidth": 0,
    }
    selected: list[SurfaceWay] = []
    for way_id in sorted(osm.ways):
        way = osm.ways[way_id]
        highway = way.tags.get("highway")
        if highway is None:
            continue
        xz = np.array([osm.xz[n] for n in way.nodes], dtype=np.float64)
        if not _near_box_overlaps(xz):
            skipped["outsideNearBox"] += 1
            continue
        surface = way.tags.get("surface")
        if surface is None:
            skipped["noSurfaceTag"] += 1
            continue
        klass = surface_class(surface)
        if klass is None:
            skipped["surfaceWithoutOverlay"] += 1
            continue
        tagged = _width_tag(way.tags)
        if tagged is not None and tagged > 0.0:
            width, source = tagged, "osm"
        elif highway in HIGHWAY_WIDTHS:
            width, source = HIGHWAY_WIDTHS[highway], "table"
        else:
            skipped["highwayWithoutWidth"] += 1
            continue
        selected.append(SurfaceWay(way_id, highway, surface, klass, width, source, xz))
    return selected, skipped


def _segment_distance(gx: Float2, gz: Float2, a: Float2, b: Float2) -> Float2:
    ab = b - a
    length_sq = float(ab @ ab)
    if length_sq == 0.0:
        return np.hypot(gx - a[0], gz - a[1])
    t = np.clip(((gx - a[0]) * ab[0] + (gz - a[1]) * ab[1]) / length_sq, 0.0, 1.0)
    return np.hypot(gx - (a[0] + t * ab[0]), gz - (a[1] + t * ab[1]))


def _stamp(coverage: Float2, rect: LocalRect, xz: Float2, half_width: float) -> None:
    """Raise ``coverage`` to the soft coverage of the buffer of ``half_width`` around ``xz``."""
    reach = half_width + EDGE_FALLOFF / 2.0
    for a, b in pairwise(xz):
        low, high = np.minimum(a, b) - reach, np.maximum(a, b) + reach
        c0 = max(0, math.floor((low[0] - rect.x_min) / CELL_SIZE))
        c1 = min(TILE_PIXELS, math.ceil((high[0] - rect.x_min) / CELL_SIZE))
        r0 = max(0, math.floor((low[1] - rect.z_min) / CELL_SIZE))
        r1 = min(TILE_PIXELS, math.ceil((high[1] - rect.z_min) / CELL_SIZE))
        if c0 >= c1 or r0 >= r1:
            continue
        xs = rect.x_min + (np.arange(c0, c1, dtype=np.float64) + 0.5) * CELL_SIZE
        zs = rect.z_min + (np.arange(r0, r1, dtype=np.float64) + 0.5) * CELL_SIZE
        gx = np.broadcast_to(xs[None, :], (r1 - r0, c1 - c0))
        gz = np.broadcast_to(zs[:, None], (r1 - r0, c1 - c0))
        soft = np.clip((reach - _segment_distance(gx, gz, a, b)) / EDGE_FALLOFF, 0.0, 1.0)
        window = coverage[r0:r1, c0:c1]
        np.maximum(window, soft, out=window)


def rasterise_tile(ways: Sequence[SurfaceWay], i: int, j: int) -> Mask:
    """The ``(1024, 1024, 4)`` uint8 mask of near tile ``(i, j)``; row 0 is its north edge."""
    rect = tile_rect(i, j)
    per_class = {name: np.zeros((TILE_PIXELS, TILE_PIXELS)) for name in CLASSES}
    for way in ways:
        _stamp(per_class[way.surface_class], rect, way.xz, way.width / 2.0)
    composite = np.zeros((TILE_PIXELS, TILE_PIXELS, len(CLASSES)))
    for name in PAINT_ORDER:
        coverage = per_class[name]
        if not coverage.any():
            continue
        composite *= (1.0 - coverage)[:, :, None]
        composite[:, :, CLASSES.index(name)] += coverage
    return np.rint(composite * 255.0).astype(np.uint8)


def value_at(mask: Mask, i: int, j: int, x: float, z: float) -> Mask:
    """The four channel values of the pixel of tile ``(i, j)`` that contains local ``(x, z)``."""
    rect = tile_rect(i, j)
    column = math.floor((x - rect.x_min) / CELL_SIZE)
    row = math.floor((z - rect.z_min) / CELL_SIZE)
    if not (0 <= column < mask.shape[1] and 0 <= row < mask.shape[0]):
        raise SurfacesError(f"({x}, {z}) is outside tile t_{i}_{j}")
    return mask[row, column]


def _chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))


def encode_png(mask: Mask) -> bytes:
    """A lossless 8-bit RGBA PNG with no ancillary chunks: byte-identical for the same pixels."""
    if mask.ndim != 3 or mask.shape[2] != 4 or mask.dtype != np.uint8:
        raise SurfacesError(
            f"expected an (h, w, 4) uint8 RGBA array, got {mask.shape} {mask.dtype}"
        )
    height, width, _ = mask.shape
    raw = b"".join(b"\x00" + mask[row].tobytes() for row in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )


def _ktx_binary() -> str:
    local = REPO_ROOT / "tools" / "bin" / "ktx"
    found = str(local) if local.is_file() else shutil.which("ktx")
    if found is None:
        raise SurfacesError("`ktx` not found in tools/bin or on PATH (see tools/README.md)")
    return found


def encode_ktx2(mask: Mask) -> bytes:
    """The mask as a linear UASTC KTX2 with a box-filtered mip chain, through ``ktx create``."""
    with tempfile.TemporaryDirectory(prefix="penyal-surfaces-") as work:
        source, target = Path(work) / "mask.png", Path(work) / "mask.ktx2"
        source.write_bytes(encode_png(mask))
        done = subprocess.run(
            [_ktx_binary(), "create", *KTX_CREATE_ARGS, str(source), str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        if done.returncode != 0:
            raise SurfacesError(f"ktx create failed: {done.stderr or done.stdout}")
        return target.read_bytes()


def _touches(way: SurfaceWay, rect: LocalRect) -> bool:
    reach = way.width / 2.0 + EDGE_FALLOFF
    low, high = way.xz.min(axis=0) - reach, way.xz.max(axis=0) + reach
    return bool(
        high[0] >= rect.x_min
        and low[0] <= rect.x_max
        and high[1] >= rect.z_min
        and low[1] <= rect.z_max
    )


def _coverage_m2(mask: Mask) -> dict[str, float]:
    total = mask.reshape(-1, len(CLASSES)).sum(axis=0, dtype=np.int64)
    return {name: float(total[k]) / 255.0 * CELL_SIZE**2 for k, name in enumerate(CLASSES)}


def build_manifest(
    osm_sha256: str,
    ways: Sequence[SurfaceWay],
    skipped: dict[str, int],
    tile_entries: list[dict[str, Any]],
    coverage: dict[str, float],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    return {
        "version": 1,
        "licence": LICENCE,
        "attribution": ATTRIBUTION,
        "source": {"id": OSM_SOURCE_ID, "sha256": osm_sha256},
        "frame": {"crs": "EPSG:25830", "origin": {"e": int(ORIGIN_E), "n": int(ORIGIN_N)}},
        "cellSize": CELL_SIZE,
        "tileSize": tiles.NEAR_TILE_SIZE,
        "tilePixels": TILE_PIXELS,
        "edgeFalloff": EDGE_FALLOFF,
        "channels": list(CLASSES),
        "encoding": {
            "format": "ktx2",
            "codec": "uastc",
            "supercompression": "zstd",
            "ktxCreateArgs": KTX_CREATE_ARGS,
            "mipmaps": "full chain, box filter",
            "channelsPerPixel": 4,
            "transfer": "linear",
            "usage": "data, not colour: no sRGB decode, no alpha premultiplication",
            "channelOrder": list(CLASSES),
            "loading": "only tiles the player has resident load their mask (the terrain tile "
            "LODs that load a mask); the manifest lists which tiles have one",
            "rows": "row 0 is the tile's north edge (z_min), column 0 its west edge (x_min)",
            "uv": "the tile mesh UV: u = (x - x_min) / tileSize, v = (z - z_min) / tileSize, "
            "x_min = tileSize * i - 0.5, z_min = tileSize * j - 0.5; load with flipY = false",
            "channelSum": "at most 255 per pixel before encoding; 255 - sum is bare terrain",
            "consumerRequirement": "clamp the sum of the four channels to 1 after sampling: "
            "UASTC leaks coverage into the channels of neighbouring classes at transitions",
            "measuredLeak": {"maxChannelLeak": 48, "maxChannelSumExcess": 57},
            "measuredLeakUnit": "of 255, over the 8 tiles, after transcoding to RGBA8",
        },
        "surfaceClasses": dict(sorted(SURFACE_CLASS.items())),
        "widths": {"status": WIDTHS_STATUS, "highway": HIGHWAY_WIDTHS},
        "coverageM2": {name: round(coverage[name], 1) for name in CLASSES},
        "skippedWays": skipped,
        "ways": [
            {
                "id": w.way_id,
                "highway": w.highway,
                "surface": w.surface,
                "class": w.surface_class,
                "width": w.width,
                "widthSource": w.width_source,
            }
            for w in ways
        ],
        "tiles": tile_entries,
        **provenance,
    }


def run_surfaces(
    out_dir: Path = SURFACES_GENERATED_DIR, provenance: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Write a KTX2 per near tile with a covered pixel, plus ``manifest.json``, into ``out_dir``."""
    raw = locate(OSM_SOURCE_ID, OSM_FILE)
    ways, skipped = select_ways(load_osm(raw.path))
    if not ways:
        raise SurfacesError("no OSM way paints a surface inside the near box")
    out_dir.mkdir(parents=True, exist_ok=True)
    kept: set[str] = set()
    tile_entries: list[dict[str, Any]] = []
    coverage: dict[str, float] = dict.fromkeys(CLASSES, 0.0)
    for i, j in tiles.near_tiles():
        rect = tile_rect(i, j)
        near = [w for w in ways if _touches(w, rect)]
        if not near:
            continue
        mask = rasterise_tile(near, i, j)
        if not mask.any():
            continue
        name = f"{tiles.tile_id(i, j)}.ktx2"
        data = encode_ktx2(mask)
        (out_dir / name).write_bytes(data)
        kept.add(name)
        tile_covered = _coverage_m2(mask)
        for klass, area in tile_covered.items():
            coverage[klass] += area
        tile_entries.append(
            {
                "id": tiles.tile_id(i, j),
                "url": name,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "coverageM2": {k: round(v, 1) for k, v in tile_covered.items()},
            }
        )
        log.info("%s: %d bytes", name, len(data))
    for stale in out_dir.glob("t_*"):
        if stale.name not in kept:
            stale.unlink()
    manifest = build_manifest(
        raw.sha256, ways, skipped, tile_entries, coverage, provenance or {"inputs": [], "tools": {}}
    )
    (out_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
