"""Procedural Aleppo-pine stand-in (E2.3): GENERATED shape, not measured.

Only the position, height and crown radius of each tree come from the LiDAR (``vegetation``); the
tree itself is invented by this module, after the open, irregular crown of *Pinus halepensis*: a
leaning, curved trunk, bare for its lower third, and layered main branches that carry tufts of
needles at their ends. Needle tufts are crossed cards textured with the twigs of Poly Haven's
``pine_tree_01`` (CC0, textures only: its mesh is not used) and the bark of the same asset.

One GLB holds every mesh, sharing one 1024 x 512 atlas (bark, two twigs, a far silhouette) so
each mesh draws in one call: ``pine_v<N>_lod0`` (near, <= 8000 triangles), ``pine_v<N>_lod1``
(mid, <= 1500) for each of ``VARIANT_COUNT`` seeded variants, and ``pine_far_card`` (two crossed
planes of single-sided twin quads, drawn with the back-face-culled twin of the material). Trees
are modelled 10 m tall with a 3.2 m crown radius (``NOMINAL_*``); an instance scales y by
``height / 10`` and x, z by ``radius / 3.2``.

Geometry and the atlas are computed with numpy (pure, testable without Blender); only
``build_scene`` and ``export_pine`` touch ``bpy``, with the exporter options ``spike`` proved
byte-reproducible. Frames are glTF (y up) until ``terrain.to_blender``.
"""

import importlib
import json
import warnings
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import numpy.typing as npt
import rasterio
from rasterio.errors import NotGeoreferencedWarning

from penyal_pipeline import artefacts, budget, foliage_tint, tiles
from penyal_pipeline.blender.spike import export_glb
from penyal_pipeline.blender.terrain import blender_uvs, to_blender
from penyal_pipeline.paths import PINE_BUILD, PINE_GENERATED
from penyal_pipeline.rawdata import locate

VARIANT_COUNT = 4
VARIANT_SEEDS = (1101, 2202, 3303, 4404)
NOMINAL_HEIGHT = 10.0
NOMINAL_RADIUS = 3.2
LOD0_MAX_TRIANGLES = 8000
LOD1_MAX_TRIANGLES = 1500
CARD_NAME = "pine_far_card"
PINE_GLB = "pine.glb"
PINE_JSON = "pine.json"
MATERIAL_NAME = "pine"
ROUGHNESS = 0.95
# Card normals are "outwards from the crown, then up by this much" (needle cards and far cards
# alike), so foliage takes skylight on every face it shows and its LODs shade alike.
SHADE_UP = 0.8

TWIG_DIFFUSE, TWIG_ALPHA, BARK_DIFFUSE = artefacts.PINE_TEXTURES

# The bark of the Poly Haven photograph is near black; the trunks of the Penyal are pale grey
# (reference photos 26 and 17), so the bark cell is greyed and brightened in the atlas. The
# needle colour is NOT baked: it is a per-vertex multiplier derived from the photographs
# (``foliage_tint``), so the atlas keeps the texture's own colours.
BARK_GREY_MIX = 0.9  # share of the luminance (the rest is the photograph's colour)
BARK_BRIGHTNESS = 1.9
TRUNK_TOP = 0.8  # fraction of the nominal height where the trunk ends; the tufts reach the rest
CROWN_BASE = 0.72  # fraction of the trunk where the lowest branch starts (crown from ~50 % up)
ATLAS_WIDTH, ATLAS_HEIGHT = 1024, 512
# Rectangles (x0, y0, x1, y1) in atlas pixels, rows top-down.
BARK_CELL = (0, 0, 512, 512)
TWIG_A_CELL = (512, 0, 768, 512)  # upright sprig, stem at the bottom
TWIG_B_CELL = (768, 0, 1024, 256)  # sideways sprig, stem on the left
FAR_CELL = (768, 256, 1024, 512)  # silhouette of a whole tree
# Where each twig sits in the 1k source (x0, y0, x1, y1) and the corners of that crop that hold
# unrelated atlas islands (the source alpha is white outside its islands): zeroed rectangles
# (row0, row1, col0, col1) in crop coordinates.
TWIG_A_SOURCE = (35, 45, 225, 455)
TWIG_A_CLEAR = ((335, 410, 0, 88), (335, 410, 116, 190))
TWIG_B_SOURCE = (665, 350, 960, 530)
TWIG_B_CLEAR = ((0, 50, 0, 60), (0, 20, 0, 90), (150, 180, 0, 70))

type Floats = npt.NDArray[np.float32]
type Ints = npt.NDArray[np.int32]
type Vec = npt.NDArray[np.float64]


@dataclass(frozen=True)
class PineMesh:
    """One mesh of the GLB: glTF-frame positions and normals, glTF-convention UVs."""

    name: str
    positions: Floats
    normals: Floats
    uvs: Floats
    triangles: Ints
    colours: Floats | None = None  # (n, 3) linear multiplier of the base colour (COLOR_0)
    single_sided: bool = False  # drawn with the back-face-culled card material

    @property
    def triangle_count(self) -> int:
        return len(self.triangles)


@dataclass(frozen=True)
class Lod:
    trunk_sides: int
    branch_sides: int
    twig_sides: int  # 0: no secondary branches
    cards_per_tuft: int
    tuft_stride: int  # every n-th tuft
    card_scale: float


LOD0 = Lod(
    trunk_sides=8, branch_sides=5, twig_sides=4, cards_per_tuft=6, tuft_stride=1, card_scale=1.0
)
LOD1 = Lod(
    trunk_sides=5, branch_sides=3, twig_sides=0, cards_per_tuft=3, tuft_stride=2, card_scale=1.4
)


@dataclass(frozen=True)
class Tube:
    points: Vec  # (k, 3)
    radii: Vec  # (k,)
    main: bool  # trunk or main branch (kept in LOD1)
    trunk: bool


@dataclass(frozen=True)
class Tuft:
    position: Vec
    direction: Vec
    size: float
    sideways: bool  # the sideways twig instead of the upright one


@dataclass(frozen=True)
class Skeleton:
    tubes: list[Tube]
    tufts: list[Tuft]
    crown_centre: Vec


# --- atlas --------------------------------------------------------------------------------------


def _read_rgb(source: tuple[str, str]) -> npt.NDArray[np.float32]:
    raw = locate(*source)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with rasterio.open(raw.path) as src:
            data = src.read()
    return np.asarray(data.transpose(1, 2, 0), dtype=np.float32) / 255.0


def resize(image: npt.NDArray[np.float32], height: int, width: int) -> npt.NDArray[np.float32]:
    """Bilinear resize (pixel centres) of an ``(h, w, c)`` image."""
    src_h, src_w = image.shape[:2]
    ys = np.clip((np.arange(height) + 0.5) * src_h / height - 0.5, 0, src_h - 1)
    xs = np.clip((np.arange(width) + 0.5) * src_w / width - 0.5, 0, src_w - 1)
    y0, x0 = np.floor(ys).astype(np.intp), np.floor(xs).astype(np.intp)
    y1, x1 = np.minimum(y0 + 1, src_h - 1), np.minimum(x0 + 1, src_w - 1)
    fy, fx = (ys - y0)[:, None, None], (xs - x0)[None, :, None]
    top = image[y0][:, x0] * (1 - fx) + image[y0][:, x1] * fx
    bottom = image[y1][:, x0] * (1 - fx) + image[y1][:, x1] * fx
    return np.asarray(top * (1 - fy) + bottom * fy, dtype=np.float32)


def twig_rgba(
    diffuse: npt.NDArray[np.float32],
    alpha: npt.NDArray[np.float32],
    source: tuple[int, int, int, int],
    clear: tuple[tuple[int, int, int, int], ...],
    cell: tuple[int, int, int, int],
) -> tuple[npt.NDArray[np.float32], tuple[int, int, int, int]]:
    """The twig crop as straight RGBA scaled to fit ``cell`` (kept aspect, centred) and its rect.

    Colour under transparent pixels is replaced by the mean needle colour so the bilinear
    filtering and the texture compression do not bleed the black island background into edges.
    """
    x0, y0, x1, y1 = source
    colour = diffuse[y0:y1, x0:x1]
    cut = alpha[y0:y1, x0:x1, 0].copy()
    for r0, r1, c0, c1 in clear:
        cut[r0:r1, c0:c1] = 0.0
    opaque = cut > 0.5
    mean = colour[opaque].mean(axis=0)
    colour = np.where(opaque[..., None], colour, mean)
    rgba = np.concatenate([colour, cut[..., None]], axis=2)
    cx0, cy0, cx1, cy1 = cell
    scale = min((cx1 - cx0) / rgba.shape[1], (cy1 - cy0) / rgba.shape[0])
    height, width = round(rgba.shape[0] * scale), round(rgba.shape[1] * scale)
    out = resize(rgba, height, width)
    left, top = cx0 + ((cx1 - cx0) - width) // 2, cy0 + ((cy1 - cy0) - height) // 2
    return out, (left, top, left + width, top + height)


def far_silhouette(mean_colour: npt.NDArray[np.float32], size: int) -> npt.NDArray[np.float32]:
    """A tree silhouette (open crown of seeded blobs over a trunk) as straight RGBA."""
    rng = np.random.default_rng(VARIANT_SEEDS[0] + 7)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64) / size
    alpha = np.zeros((size, size))
    for _ in range(46):
        cx = float(np.clip(0.5 + rng.normal(0.0, 0.14), 0.24, 0.76))
        cy = float(np.clip(0.36 + rng.normal(0.0, 0.1), 0.2, 0.55))
        rx, ry = rng.uniform(0.06, 0.12), rng.uniform(0.04, 0.08)
        alpha = np.maximum(alpha, (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) < 1.0)
    alpha = np.maximum(alpha, (np.abs(xx - 0.5) < 0.018) & (yy > 0.3))
    coarse = 0.75 + 0.5 * rng.random((32, 32, 1))
    shade = resize(coarse.astype(np.float32), size, size)[..., 0]
    colour = np.clip(mean_colour[None, None, :] * shade[..., None], 0.0, 1.0)
    return np.concatenate([colour, alpha[..., None]], axis=2).astype(np.float32)


@dataclass(frozen=True)
class Atlas:
    rgba: npt.NDArray[np.uint8]  # (512, 1024, 4) straight alpha, top-down
    twig_a: tuple[int, int, int, int]  # rect of the content in atlas pixels
    twig_b: tuple[int, int, int, int]


def build_atlas() -> Atlas:
    diffuse, alpha = _read_rgb(TWIG_DIFFUSE), _read_rgb(TWIG_ALPHA)
    bark = _read_rgb(BARK_DIFFUSE)
    atlas = np.zeros((ATLAS_HEIGHT, ATLAS_WIDTH, 4), dtype=np.float32)
    bx0, by0, bx1, by1 = BARK_CELL
    bark = resize(bark, by1 - by0, bx1 - bx0)
    luminance = bark @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    bark = (BARK_GREY_MIX * luminance[..., None] + (1.0 - BARK_GREY_MIX) * bark) * BARK_BRIGHTNESS
    atlas[by0:by1, bx0:bx1, :3] = np.clip(bark, 0.0, 1.0)
    atlas[by0:by1, bx0:bx1, 3] = 1.0
    twig_a, rect_a = twig_rgba(diffuse, alpha, TWIG_A_SOURCE, TWIG_A_CLEAR, TWIG_A_CELL)
    twig_b, rect_b = twig_rgba(diffuse, alpha, TWIG_B_SOURCE, TWIG_B_CLEAR, TWIG_B_CELL)
    for twig, (x0, y0, x1, y1) in ((twig_a, rect_a), (twig_b, rect_b)):
        atlas[y0:y1, x0:x1] = twig
    needle = atlas[rect_a[1] : rect_a[3], rect_a[0] : rect_a[2]]
    mean = needle[needle[..., 3] > 0.5][:, :3].mean(axis=0)
    fx0, fy0, fx1, fy1 = FAR_CELL
    atlas[fy0:fy1, fx0:fx1] = far_silhouette(mean.astype(np.float32), fx1 - fx0)
    # colour under fully transparent pixels: the needle mean, never black
    empty = atlas[..., 3] == 0.0
    atlas[empty, :3] = mean
    return Atlas(np.rint(atlas * 255.0).astype(np.uint8), rect_a, rect_b)


def alpha_coverage_by_level(atlas: Atlas, levels: int = 5) -> list[float]:
    """Share of the twig and silhouette texels that pass the alpha test (>= 0.5) at each mip level
    (2 x 2 box filter of the alpha, as a GPU mip chain does). It falls as thin needles blur out:
    the app should alpha-to-coverage or scale the alpha with distance (E2.5)."""
    alpha = atlas.rgba[..., 3].astype(np.float64) / 255.0
    mask = np.zeros(alpha.shape, dtype=bool)
    for x0, y0, x1, y1 in (atlas.twig_a, atlas.twig_b, FAR_CELL):
        mask[y0:y1, x0:x1] = True
    coverage = []
    for _ in range(levels):
        coverage.append(float((alpha[mask] >= 0.5).mean()))
        h, w = alpha.shape[0] // 2 * 2, alpha.shape[1] // 2 * 2
        alpha = alpha[:h, :w].reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))
        mask = mask[:h, :w].reshape(h // 2, 2, w // 2, 2).all(axis=(1, 3))
    return coverage


# --- vector helpers -----------------------------------------------------------------------------


def unit(vectors: Vec) -> Vec:
    norm = np.linalg.norm(vectors, axis=-1, keepdims=True)
    return np.asarray(vectors / np.maximum(norm, 1e-12), dtype=np.float64)


def frames(points: Vec) -> tuple[Vec, Vec, Vec]:
    """Tangent, normal and binormal at each point of a polyline (parallel transport)."""
    count = len(points)
    tangent = np.empty_like(points)
    tangent[0] = points[1] - points[0]
    tangent[-1] = points[-1] - points[-2]
    tangent[1:-1] = points[2:] - points[:-2]
    tangent = unit(tangent)
    reference = np.array([0.0, 0.0, 1.0]) if abs(tangent[0, 2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    normal = np.empty_like(points)
    normal[0] = unit(np.cross(tangent[0], reference))
    for i in range(1, count):
        previous = normal[i - 1]
        normal[i] = unit(previous - np.dot(previous, tangent[i]) * tangent[i])
    return tangent, normal, np.cross(tangent, normal)


# --- skeleton -----------------------------------------------------------------------------------


def _trunk(rng: np.random.Generator, variant: int) -> Tube:
    """A sinuous trunk: it bulges to one side, swings back and returns to the axis, so its top is
    above its foot (the app leans it to the measured apex)."""
    rings = 14
    t = np.linspace(0.0, 1.0, rings)
    bulge = rng.uniform(0.6, 1.2, size=2) * rng.choice([-1.0, 1.0], size=2)
    second = rng.uniform(0.3, 0.6, size=2) * rng.choice([-1.0, 1.0], size=2)
    x = bulge[0] * np.sin(np.pi * t) + second[0] * np.sin(2.0 * np.pi * t)
    z = bulge[1] * np.sin(np.pi * t) + second[1] * np.sin(2.0 * np.pi * t)
    y = t * NOMINAL_HEIGHT * TRUNK_TOP
    base = rng.uniform(0.2, 0.28) * (1.0 + 0.1 * variant)
    radii = base * (1.0 - t) ** 0.85 + 0.03
    radii[0] *= 1.25  # root flare
    radii[1] *= 1.08
    return Tube(np.stack([x, y, z], axis=1), radii, main=True, trunk=True)


def _branch(
    rng: np.random.Generator,
    origin: Vec,
    azimuth: float,
    elevation: float,
    length: float,
    radius: float,
) -> Tube:
    """A branch leaving ``origin``: it starts at ``elevation`` and bends up (reaching for light)."""
    points = [origin]
    heading = np.array([np.cos(azimuth), 0.0, np.sin(azimuth)])
    steps = 4
    angle = elevation
    for _ in range(steps):
        direction = np.cos(angle) * heading + np.sin(angle) * np.array([0.0, 1.0, 0.0])
        wobble = rng.normal(0.0, 0.08, size=3)
        points.append(points[-1] + (direction + wobble) * length / steps)
        angle = min(angle + rng.uniform(0.0, 0.14), 1.2)
    radii = radius * np.linspace(1.0, 0.25, steps + 1)
    return Tube(np.array(points), radii, main=True, trunk=False)


def _twig(rng: np.random.Generator, base: Tube, at: float, side: float, length: float) -> Tube:
    index = at * (len(base.points) - 1)
    low = int(np.floor(index))
    high = min(low + 1, len(base.points) - 1)
    origin = base.points[low] + (base.points[high] - base.points[low]) * (index - low)
    along = unit(base.points[high] - base.points[low])
    across = unit(np.cross(along, np.array([0.0, 1.0, 0.0])))
    heading = unit(along * 0.7 + across * side * 0.8 + np.array([0.0, 0.35, 0.0]))
    points = [origin]
    for _ in range(2):
        points.append(points[-1] + (heading + rng.normal(0.0, 0.1, size=3)) * length / 2.0)
    radius = float(np.interp(index, np.arange(len(base.radii)), base.radii)) * 0.55
    return Tube(
        np.array(points), np.array([radius, radius * 0.6, radius * 0.3]), main=False, trunk=False
    )


def _along(tube: Tube, s: float) -> tuple[Vec, Vec]:
    """Point and growth direction at fraction ``s`` of a tube."""
    index = s * (len(tube.points) - 1)
    low = min(int(np.floor(index)), len(tube.points) - 2)
    segment = tube.points[low + 1] - tube.points[low]
    return tube.points[low] + segment * (index - low), unit(segment)


def skeleton(variant: int) -> Skeleton:
    """The tree of ``variant``: tubes and tufts, from its fixed seed.

    Bare trunk up to the crown base, then branches grouped in a few irregular clumps (each with
    its own preferred direction and reach), longer and flatter towards the top (the umbrella
    tendency of old Aleppo pines), with needle tufts along their outer half.
    """
    rng = np.random.default_rng(VARIANT_SEEDS[variant])
    trunk = _trunk(rng, variant)
    tubes = [trunk]
    tufts: list[Tuft] = []
    if variant % 2 == 1:  # a second leader, as in the multi-stemmed pines of the slope
        origin, _ = _along(trunk, 0.4)
        leader = _branch(rng, origin, rng.uniform(0.0, 2.0 * np.pi), 1.0, NOMINAL_HEIGHT * 0.4, 0.1)
        tubes.append(replace(leader, trunk=True))
    clumps = rng.uniform(0.0, 2.0 * np.pi, size=3)
    clump_reach = rng.uniform(0.7, 1.3, size=3)
    branch_count = 20
    for i in range(branch_count):
        t = CROWN_BASE + (0.96 - CROWN_BASE) * (i + rng.uniform(-0.3, 0.3)) / branch_count
        t = float(np.clip(t, CROWN_BASE, 0.97))
        height = (t - CROWN_BASE) / (0.97 - CROWN_BASE)  # 0 at the crown base, 1 at the top
        origin, _ = _along(trunk, t)
        clump = int(rng.integers(0, 3))
        azimuth = clumps[clump] + rng.normal(0.0, 0.45)
        reach = NOMINAL_RADIUS * (0.7 + 0.6 * height) * clump_reach[clump] * rng.uniform(0.85, 1.15)
        elevation = 0.55 - 0.3 * height + rng.normal(0.0, 0.1)
        radius = float(
            np.interp(t * (len(trunk.radii) - 1), np.arange(len(trunk.radii)), trunk.radii)
        )
        branch = _branch(rng, origin, azimuth, elevation, reach, max(radius * 0.4, 0.03))
        tubes.append(branch)
        for at, side in ((0.45, 1.0), (0.7, -1.0)):
            twig = _twig(rng, branch, at, side * rng.choice([-1.0, 1.0]), reach * 0.4)
            tubes.append(twig)
            for s in (0.65, 1.0):
                position, direction = _along(twig, s)
                tufts.append(
                    Tuft(position, direction, rng.uniform(0.8, 1.2), bool(rng.random() < 0.3))
                )
        for s in (0.35, 0.5, 0.65, 0.8, 0.92, 1.0):
            position, direction = _along(branch, s)
            size = rng.uniform(1.1, 1.6) if s == 1.0 else rng.uniform(0.8, 1.3)
            tufts.append(Tuft(position, direction, size, bool(rng.random() < 0.3)))
    top, direction = _along(trunk, 1.0)
    for k in range(3):
        spread = unit(direction + rng.normal(0.0, 0.4, size=3))
        tufts.append(Tuft(top, spread, rng.uniform(1.1, 1.5), k == 2))
    crown = trunk.points[int(0.75 * (len(trunk.points) - 1))].copy()
    return Skeleton(tubes, tufts, crown)


# --- meshes -------------------------------------------------------------------------------------


def tube_mesh(
    tube: Tube, sides: int, uv_cell: tuple[float, float, float, float], jitter: Vec
) -> tuple[Vec, Vec, Vec, npt.NDArray[np.int64]]:
    """Positions, normals, UVs and triangles of a tapered tube (open at both ends).

    Every segment owns its two rings so its bark UVs can restart: it maps the whole cell width
    once around and ``length / circumference`` of the cell height along (square texels instead of
    a trunk-long stretch), starting at a pseudo-random height of the cell so neighbours differ.
    ``jitter`` offsets each ring's radius a little (bark irregularity).
    """
    _, normal, binormal = frames(tube.points)
    angles = np.linspace(0.0, 2.0 * np.pi, sides + 1)
    radial = (
        np.cos(angles)[None, :, None] * normal[:, None, :]
        + np.sin(angles)[None, :, None] * binormal[:, None, :]
    )
    radii = (tube.radii * jitter[: len(tube.radii)])[:, None, None]
    rings = tube.points[:, None, :] + radial * radii  # (k, sides + 1, 3)
    u0, v0, u1, v1 = uv_cell
    around = u0 + (u1 - u0) * np.arange(sides + 1) / sides
    segments = len(tube.points) - 1
    positions, normals, uvs, triangles = [], [], [], []
    for s in range(segments):
        ring_pair = rings[s : s + 2]
        length = float(np.linalg.norm(tube.points[s + 1] - tube.points[s]))
        circumference = float(np.linalg.norm(np.diff(ring_pair[0], axis=0), axis=1).sum())
        span = min(length / max(circumference, 1e-9) * (u1 - u0), (v1 - v0) * 0.98)
        start = v0 + (v1 - v0 - span) * ((s * 0.6180339887) % 1.0)
        v = np.array([start, start + span])
        base = s * 2 * (sides + 1)
        positions.append(ring_pair.reshape(-1, 3))
        normals.append(radial[s : s + 2].reshape(-1, 3))
        uvs.append(np.stack([np.tile(around, 2), np.repeat(v, sides + 1)], axis=1))
        index = base + np.arange(sides)
        bottom0, bottom1 = index, index + 1
        top0, top1 = index + sides + 1, index + sides + 2
        triangles.append(np.stack([bottom0, bottom1, top1], axis=1))
        triangles.append(np.stack([bottom0, top1, top0], axis=1))
    return (
        np.concatenate(positions),
        np.concatenate(normals),
        np.concatenate(uvs),
        np.concatenate(triangles),
    )


def card_mesh(
    tuft: Tuft,
    cards: int,
    scale: float,
    rects: tuple[tuple[float, float, float, float], tuple[float, float, float, float]],
    crown: Vec,
    roll: float,
) -> tuple[Vec, Vec, Vec, npt.NDArray[np.int64]]:
    """``cards`` crossed quads around the growth direction of ``tuft``; stems at the tuft point."""
    direction = tuft.direction
    reference = np.array([0.0, 1.0, 0.0]) if abs(direction[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    side0 = unit(np.cross(direction, reference))
    side1 = np.cross(direction, side0)
    u0, v0, u1, v1 = rects[1] if tuft.sideways else rects[0]
    length = (1.5 if tuft.sideways else 1.9) * tuft.size * scale
    width = length * (0.62 if tuft.sideways else 0.5)
    positions, normals, uvs, triangles = [], [], [], []
    for k in range(cards):
        angle = roll + np.pi * k / cards
        side = np.cos(angle) * side0 + np.sin(angle) * side1
        base = tuft.position
        tip = tuft.position + direction * length
        corners = np.array(
            [
                base - side * width / 2.0,
                base + side * width / 2.0,
                tip + side * width * 0.45,
                tip - side * width * 0.45,
            ]
        )
        if tuft.sideways:  # stem on the left of the image, tip on the right
            corner_uv = [(u0, v1), (u0, v0), (u1, v0), (u1, v1)]
        else:  # stem at the bottom of the image
            corner_uv = [(u0, v1), (u1, v1), (u1, v0), (u0, v0)]
        outward = unit(corners - crown[None, :])
        shade = unit(outward + np.array([0.0, SHADE_UP, 0.0]))
        offset = len(positions) * 4
        positions.append(corners)
        normals.append(shade)
        uvs.append(np.array(corner_uv))
        triangles.append(np.array([[0, 1, 2], [0, 2, 3]]) + offset)
    return (
        np.concatenate(positions),
        np.concatenate(normals),
        np.concatenate(uvs),
        np.concatenate(triangles),
    )


def _cell_uv(cell: tuple[int, int, int, int]) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = cell
    return x0 / ATLAS_WIDTH, y0 / ATLAS_HEIGHT, x1 / ATLAS_WIDTH, y1 / ATLAS_HEIGHT


def _bark_cell() -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = BARK_CELL
    inset = 4
    return _cell_uv((x0 + inset, y0 + inset, x1 - inset, y1 - inset))


def _raw_variant(
    variant: int, lod: Lod, atlas: Atlas
) -> tuple[Vec, Vec, Vec, npt.NDArray[np.int64]]:
    skel = skeleton(variant)
    rng = np.random.default_rng(VARIANT_SEEDS[variant] + 1)
    rects = (_cell_uv(atlas.twig_a), _cell_uv(atlas.twig_b))
    parts: list[tuple[Vec, Vec, Vec, npt.NDArray[np.int64]]] = []
    for tube in skel.tubes:
        if not tube.main and lod.twig_sides == 0:
            continue
        sides = (
            lod.trunk_sides if tube.trunk else (lod.branch_sides if tube.main else lod.twig_sides)
        )
        jitter = rng.uniform(0.9, 1.1, size=len(tube.radii))
        parts.append(tube_mesh(tube, sides, _bark_cell(), jitter))
    for tuft in skel.tufts[:: lod.tuft_stride]:
        roll = float(rng.uniform(0.0, np.pi))
        parts.append(
            card_mesh(tuft, lod.cards_per_tuft, lod.card_scale, rects, skel.crown_centre, roll)
        )
    offsets = np.cumsum([0, *(len(p[0]) for p in parts[:-1])])
    return (
        np.concatenate([p[0] for p in parts]),
        np.concatenate([p[1] for p in parts]),
        np.concatenate([p[2] for p in parts]),
        np.concatenate([p[3] + o for p, o in zip(parts, offsets, strict=True)]),
    )


def variant_scale(variant: int, atlas: Atlas) -> tuple[float, float]:
    """Horizontal and vertical factors that give the LOD0 of ``variant`` the nominal size: its top
    at ``NOMINAL_HEIGHT`` and 90 % of its vertices within ``NOMINAL_RADIUS`` of the axis."""
    positions = _raw_variant(variant, LOD0, atlas)[0]
    radial = np.hypot(positions[:, 0], positions[:, 2])
    return (
        float(NOMINAL_RADIUS / np.percentile(radial, 90)),
        float(NOMINAL_HEIGHT / positions[:, 1].max()),
    )


def needle_linear_mean(atlas: Atlas) -> npt.NDArray[np.float64]:
    """Mean linear RGB of the opaque upright-twig pixels: the colour the multiplier acts on."""
    x0, y0, x1, y1 = atlas.twig_a
    pixels = atlas.rgba[y0:y1, x0:x1].reshape(-1, 4)
    opaque = pixels[pixels[:, 3] > 127][:, :3].astype(np.float64) / 255.0
    return np.asarray(foliage_tint.srgb_to_linear(opaque).mean(axis=0))


def foliage_colours(
    uvs: Floats, foliage: npt.NDArray[np.bool_], factor: tuple[float, ...]
) -> Floats:
    """White for bark, ``factor`` for foliage vertices."""
    colours = np.ones((len(uvs), 3), dtype=np.float32)
    colours[foliage] = np.array(factor, dtype=np.float32)
    return colours


def build_variant(variant: int, lod: Lod, name: str, atlas: Atlas) -> PineMesh:
    """The mesh of one variant at one level of detail, at the nominal size."""
    positions, normals, uvs, triangles = _raw_variant(variant, lod, atlas)
    horizontal, vertical = variant_scale(variant, atlas)
    factors = np.array([horizontal, vertical, horizontal])
    return PineMesh(
        name,
        (positions * factors).astype(np.float32),
        unit(normals / factors).astype(np.float32),
        uvs.astype(np.float32),
        triangles.astype(np.int32),
        foliage_colours(
            uvs.astype(np.float32), uvs[:, 0] > 0.5, foliage_tint.FOLIAGE_FACTORS["pine"]
        ),
    )


def crossed_quads(
    half: float, height: float, uv_rect: tuple[float, float, float, float]
) -> tuple[Floats, Floats, Floats, Ints]:
    """Two vertical planes crossed at the axis, each a pair of single-sided twin quads facing
    opposite ways (8 triangles), ``2 * half`` wide, mapping ``uv_rect``. Draw with back faces
    culled (``single_sided``).

    Each twin is shaded like the needle cards of the crown: its normal points out of the crown
    surface it stands for (the vertex's direction from the axis plus the twin's own facing
    direction), then up by ``SHADE_UP``. One double-sided quad cannot do that: the renderer flips
    its normal for the back face, so an upward normal points down and goes black from behind,
    and the in-plane normals used before gave N.V = 0 to anyone facing the card, whose grazing
    specular washed it out to a pale beige.
    """
    u0, v0, u1, v1 = uv_rect
    up = np.array([0.0, SHADE_UP, 0.0])
    positions, normals, uvs, triangles = [], [], [], []
    for dx, dz in ((1.0, 0.0), (0.0, 1.0)):
        corners = np.array(
            [
                (-dx * half, 0.0, -dz * half),
                (dx * half, 0.0, dz * half),
                (dx * half, height, dz * half),
                (-dx * half, height, -dz * half),
            ]
        )
        corner_uv = [(u0, v1), (u1, v1), (u1, v0), (u0, v0)]
        front = unit(np.cross(corners[1] - corners[0], corners[2] - corners[0]))
        radial = unit(corners * np.array([1.0, 0.0, 1.0]))
        for side, order in ((1.0, [0, 1, 2, 3]), (-1.0, [1, 0, 3, 2])):
            offset = len(positions) * 4
            positions.append(corners[order])
            normals.append(unit(unit(radial[order] + side * front) + up))
            uvs.append([corner_uv[i] for i in order])
            triangles.append(np.array([[0, 1, 2], [0, 2, 3]]) + offset)
    return (
        np.concatenate(positions).astype(np.float32),
        np.concatenate(normals).astype(np.float32),
        np.array(uvs, dtype=np.float32).reshape(-1, 2),
        np.concatenate(triangles).astype(np.int32),
    )


def far_card() -> PineMesh:
    """Two crossed twin-quad planes (8 triangles) with the silhouette cell, as wide as the
    nominal crown."""
    positions, normals, uvs, triangles = crossed_quads(
        NOMINAL_RADIUS * 1.1, NOMINAL_HEIGHT, _cell_uv(FAR_CELL)
    )
    return PineMesh(
        CARD_NAME,
        positions,
        normals,
        uvs,
        triangles,
        np.tile(
            np.array(foliage_tint.FOLIAGE_FACTORS["pine"], dtype=np.float32), (len(positions), 1)
        ),
        single_sided=True,
    )


def build_meshes(atlas: Atlas) -> list[PineMesh]:
    """Every mesh of the GLB, in export order."""
    meshes = []
    for variant in range(VARIANT_COUNT):
        meshes.append(build_variant(variant, LOD0, f"pine_v{variant}_lod0", atlas))
        meshes.append(build_variant(variant, LOD1, f"pine_v{variant}_lod1", atlas))
    meshes.append(far_card())
    return meshes


# --- Blender ------------------------------------------------------------------------------------


class HasRgba(Protocol):
    @property
    def rgba(self) -> npt.NDArray[np.uint8]: ...


def rgba_pixels(rgba: npt.NDArray[np.uint8]) -> Floats:
    """Flat float pixels, rows bottom-to-top, from a top-down RGBA uint8 image."""
    return np.asarray(rgba[::-1].astype(np.float32) / 255.0, dtype=np.float32).reshape(-1)


def _make_object(bpy: Any, bmesh: Any, item: PineMesh, material: Any) -> None:
    mesh = bpy.data.meshes.new(item.name)
    positions = to_blender(item.positions)
    uvs = blender_uvs(item.uvs)
    builder = bmesh.new()
    layer = builder.loops.layers.uv.new("UVMap")
    # FLOAT_COLOR holds linear values as written. The byte layer (``layers.color``) stores sRGB,
    # so the exporter decoded each factor once more (0.568 -> 0.28): dark, olive-brown foliage.
    colour_layer = builder.loops.layers.float_color.new("Color")
    colours = np.ones((len(positions), 3)) if item.colours is None else item.colours
    verts = [builder.verts.new(tuple(float(c) for c in p)) for p in positions]
    for a, b, c in item.triangles:
        face = builder.faces.new((verts[a], verts[b], verts[c]))
        face.smooth = True
        for loop, index in zip(face.loops, (a, b, c), strict=True):
            loop[layer].uv = tuple(float(v) for v in uvs[index])
            loop[colour_layer] = (*(float(c) for c in colours[index]), 1.0)
    builder.to_mesh(mesh)
    builder.free()
    mesh.normals_split_custom_set_from_vertices(to_blender(item.normals).tolist())
    mesh.materials.append(material)
    bpy.context.scene.collection.objects.link(bpy.data.objects.new(item.name, mesh))


def card_material_name(name: str) -> str:
    """The back-face-culled twin of material ``name``, for the ``single_sided`` far cards."""
    return f"{name}_card"


def _make_material(bpy: Any, image: Any, name: str, double_sided: bool) -> Any:
    material = bpy.data.materials.new(name)
    material.use_backface_culling = not double_sided  # needle cards are seen from both sides
    nodes, links = material.node_tree.nodes, material.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = ROUGHNESS
    bsdf.inputs["Metallic"].default_value = 0.0
    # No specular (glTF KHR_materials_specular, specularFactor 0): the card normals are shading
    # proxies for a crown, not surfaces. Seen from below the slope and against the sun they sit
    # at grazing angles, where the Fresnel term turned every crown a pale, sun-coloured beige.
    bsdf.inputs["Specular IOR Level"].default_value = 0.0
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.extension = "EXTEND"  # glTF CLAMP_TO_EDGE: cells must not bleed into each other
    rounding = nodes.new("ShaderNodeMath")
    rounding.operation = "ROUND"  # the glTF exporter reads Alpha -> Round as alphaMode MASK
    vertex_colour = nodes.new("ShaderNodeVertexColor")
    vertex_colour.layer_name = "Color"
    multiply = nodes.new("ShaderNodeMix")
    multiply.data_type = "RGBA"
    multiply.blend_type = "MULTIPLY"  # the exporter reads texture x colour attribute as COLOR_0
    multiply.inputs["Factor"].default_value = 1.0
    links.new(texture.outputs["Color"], multiply.inputs["A"])
    links.new(vertex_colour.outputs["Color"], multiply.inputs["B"])
    links.new(multiply.outputs["Result"], bsdf.inputs["Base Color"])
    links.new(texture.outputs["Alpha"], rounding.inputs[0])
    links.new(rounding.outputs["Value"], bsdf.inputs["Alpha"])
    return material


def build_scene(
    bpy: Any, meshes: list[PineMesh], atlas: HasRgba, material_name: str = MATERIAL_NAME
) -> None:
    """Replace the current Blender scene with every mesh sharing one atlas image: the
    double-sided material, and its back-face-culled twin for the ``single_sided`` far cards."""
    bmesh = importlib.import_module("bmesh")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    image = bpy.data.images.new(f"{material_name}_atlas", ATLAS_WIDTH, ATLAS_HEIGHT, alpha=True)
    image.pixels.foreach_set(rgba_pixels(atlas.rgba))
    image.update()
    image.pack()
    material = _make_material(bpy, image, material_name, double_sided=True)
    card = _make_material(bpy, image, card_material_name(material_name), double_sided=False)
    for item in meshes:
        _make_object(bpy, bmesh, item, card if item.single_sided else material)


def export_scene(
    meshes: list[PineMesh], atlas: HasRgba, out: Path, material_name: str = MATERIAL_NAME
) -> Path:
    """Build ``meshes`` sharing one atlas (``build_scene``) in a fresh Blender state and write
    ``out``."""
    bpy = importlib.import_module("bpy")
    build_scene(bpy, meshes, atlas, material_name)
    export_glb(bpy, out)
    return out


def export_pine(meshes: list[PineMesh], atlas: Atlas, out: Path) -> Path:
    """Build the meshes in a fresh Blender state and write the (unoptimised) GLB to ``out``."""
    bpy = importlib.import_module("bpy")
    build_scene(bpy, meshes, atlas)
    export_glb(bpy, out)
    return out


# --- artefact -----------------------------------------------------------------------------------


def manifest(meshes: list[PineMesh], atlas: Atlas, glb_bytes: int) -> dict[str, Any]:
    """The ``pine.json`` document: what the GLB holds, at which size, and where it came from."""
    return {
        "version": 1,
        "shape": "generated by blender/pine.py, not measured; the LiDAR gives each tree's "
        "position, height and crown radius only",
        "licence": "CC0 1.0",
        "attribution": "Textures: Rob Tuytel and Rico Cilliers, Poly Haven (polyhaven.com), CC0 "
        "(credited as courtesy); tree shape generated by the project",
        "nominal": {"height": NOMINAL_HEIGHT, "crownRadius": NOMINAL_RADIUS},
        "instancing": "scale y by height / nominal.height and x, z by the crown's scaleXZ "
        "(radius / crownRadius held within 0.6-1.6 x the vertical scale, see vegetation.json); "
        "the model stands upright on its foot: lean it towards the crown's leanX, leanZ",
        "notes": [
            "y in vegetation.json is the uncarved 1 m DEM; resample the ground on the rendered "
            "terrain tiles, which differ where ADR 0009 corrected it",
            "the atlas alpha loses coverage in the mips (atlas.alphaCoverage): use "
            "alpha-to-coverage or scale the alpha cut-off with distance",
            "foliage colour is a per-vertex multiplier (COLOR_0, linear) from the reference photos "
            "(foliage_tint.py); the bark grey is baked into the atlas (BARK_*)",
        ],
        "variants": VARIANT_COUNT,
        "seeds": list(VARIANT_SEEDS),
        "file": {"name": PINE_GLB, "bytes": glb_bytes},
        "material": {
            "name": MATERIAL_NAME,
            "alphaMode": "MASK",
            "atlas": [ATLAS_WIDTH, ATLAS_HEIGHT],
            "cards": card_material_name(MATERIAL_NAME),
        },
        "atlas": {
            "bark": list(BARK_CELL),
            "twigUpright": list(atlas.twig_a),
            "twigSideways": list(atlas.twig_b),
            "farSilhouette": list(FAR_CELL),
            "alphaCoverage": [round(c, 4) for c in alpha_coverage_by_level(atlas)],
        },
        "meshes": [
            {
                "name": mesh.name,
                "triangles": mesh.triangle_count,
                "vertices": len(mesh.positions),
            }
            for mesh in meshes
        ],
        "budget": {
            "lod0MaxTriangles": LOD0_MAX_TRIANGLES,
            "lod1MaxTriangles": LOD1_MAX_TRIANGLES,
            **budget.describe(),
        },
    }


def run_pine(out_dir: Path = PINE_GENERATED, build_dir: Path = PINE_BUILD) -> dict[str, Any]:
    """Build every mesh, export the GLB through Blender, optimise it (KTX2 + meshopt) and write
    ``pine.glb`` and ``pine.json`` into ``out_dir``. Returns the document."""
    atlas = build_atlas()
    meshes = build_meshes(atlas)
    raw = export_pine(meshes, atlas, build_dir / PINE_GLB)
    out_dir.mkdir(parents=True, exist_ok=True)
    glb_bytes = tiles.optimize_glb(raw, out_dir / PINE_GLB)
    document = {**manifest(meshes, atlas, glb_bytes), **artefacts.provenance("pine")}
    (out_dir / PINE_JSON).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return document
