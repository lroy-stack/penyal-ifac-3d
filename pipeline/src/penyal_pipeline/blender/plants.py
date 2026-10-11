"""Procedural understory plants (E2.4): lentisc, rosemary and a grass tuft. GENERATED, not measured.

The shape of each plant is invented here after its species (several curved stems carrying twig
cards); only the leaf and blade pixels come from the CC0 Poly Haven textures already in the
catalogue (``shrub_04``, ``shrub_02``, ``grass_medium_02``). Those textures are JPEGs without an
alpha channel, with the leaves floating on smeared background, so each leaf is cut out with an
analytic leaf outline (pointed ellipse) around the leaf's axis and pasted along a stem to make a
twig sprite; the grass is cut by its black background.

One GLB holds nine meshes sharing one material and one 1024 x 512 atlas: for each model
``<id>_lod0`` (near, <= 1500 triangles), ``<id>_lod1`` (mid, <= 400) and ``<id>_card`` (two
crossed quads), so each mesh draws in one call. Plants are modelled at the nominal size of
``understory.MODELS``; an instance scales uniformly by ``height / nominal height``.

Geometry and the atlas are numpy (pure, testable without Blender), reusing the tube and card
builders of ``pine``; only the export touches ``bpy``.
"""

import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from penyal_pipeline import artefacts, tiles, understory
from penyal_pipeline.blender import pine
from penyal_pipeline.blender.pine import PineMesh, Tube, Tuft, unit
from penyal_pipeline.paths import PINE_GENERATED, PLANTS_BUILD

PlantMesh = PineMesh
LEVELS = ("lod0", "lod1", "card")
LOD0_MAX_TRIANGLES = 1500
LOD1_MAX_TRIANGLES = 400
PLANTS_GLB = "plants.glb"
PLANTS_JSON = "plants.json"
MATERIAL_NAME = "plants"
SEEDS = {"lentisc": 5101, "rosemary": 5202, "grass": 5303}

SHRUB_04, SHRUB_02, GRASS_02 = artefacts.PLANT_TEXTURES
SPRITE = (256, 512)  # width, height of a twig sprite in the atlas
# Leaves in the 1k sources as (base x, base y, tip x, tip y, width) in pixels; each lies clearly
# apart from its neighbours (checked on the images). The leaf outline is analytic.
LENTISC_LEAVES = ((303, 933, 292, 662, 95), (455, 945, 425, 718, 100), (627, 897, 590, 702, 85))
ROSEMARY_LEAVES = ((270, 848, 240, 330, 110), (583, 845, 570, 330, 105), (835, 835, 900, 420, 100))
LENTISC_STEM_PIXELS = (860, 450, 880, 800)  # a stretch of the red-brown twig in shrub_04
GRASS_CROP = (30, 20, 430, 995)  # three clean blades of grass_medium_02
GRASS_BLACK = 0.12  # brightness under which a grass pixel is background
LENTISC_TINT = (0.72, 1.0, 0.62)  # glossy dark green instead of pale grey-green
ROSEMARY_TINT = (0.85, 0.97, 0.82)

CELLS = {
    "lentisc": (0, 0, 256, 512),
    "rosemary": (256, 0, 512, 512),
    "grass": (512, 0, 768, 512),
    "lentisc_far": (768, 0, 1024, 224),
    "rosemary_far": (768, 224, 1024, 448),
    "stem": (768, 448, 1024, 512),  # a solid stem colour for the stem tubes
}
ATLAS_SIZE = (1024, 512)

type Floats = npt.NDArray[np.float32]
type Vec = npt.NDArray[np.float64]


@dataclass(frozen=True)
class Atlas:
    rgba: npt.NDArray[np.uint8]  # (512, 1024, 4) straight alpha, top-down
    cells: dict[str, tuple[int, int, int, int]]


# --- atlas --------------------------------------------------------------------------------------


def paste_leaf(
    canvas: Floats,
    source: Floats,
    leaf: tuple[int, int, int, int, int],
    base: tuple[float, float],
    angle: float,
    length: float,
    squeeze: float = 1.0,
) -> None:
    """Paste the leaf of ``source`` into ``canvas`` with its base at ``base`` (x, y in pixels),
    its axis turned ``angle`` radians clockwise from straight up and ``length`` pixels long.

    The outline is a pointed ellipse, ``squeeze`` narrows it. Later leaves cover earlier ones.
    """
    bx, by, tx, ty, width = leaf
    axis = np.array([tx - bx, ty - by], dtype=np.float64)
    source_length = float(np.linalg.norm(axis))
    axis /= source_length
    across_source = np.array([-axis[1], axis[0]])
    direction = np.array([np.sin(angle), -np.cos(angle)])
    across = np.array([-direction[1], direction[0]])
    half_width = width * (length / source_length) * squeeze / 2.0
    reach = length + half_width
    height, wide = canvas.shape[:2]
    x0, x1 = (
        int(max(0, min(base[0] - reach, base[0] + reach))),
        int(min(wide, max(base[0] - reach, base[0] + reach) + 1)),
    )
    y0, y1 = int(max(0, base[1] - reach)), int(min(height, base[1] + reach + 1))
    if x1 <= x0 or y1 <= y0:
        return
    xs, ys = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
    dx, dy = xs - base[0], ys - base[1]
    u = (dx * direction[0] + dy * direction[1]) / length
    v = (dx * across[0] + dy * across[1]) / max(half_width, 1e-6)
    profile = np.sin(np.pi * np.clip(u, 0.0, 1.0) ** 0.7) ** 0.8
    inside = (u >= 0.0) & (u <= 1.0) & (np.abs(v) <= profile)
    if not inside.any():
        return
    sx = bx + u * source_length * axis[0] + v * (width / 2.0) * across_source[0]
    sy = by + u * source_length * axis[1] + v * (width / 2.0) * across_source[1]
    sample = source[
        np.clip(sy[inside].astype(np.intp), 0, source.shape[0] - 1),
        np.clip(sx[inside].astype(np.intp), 0, source.shape[1] - 1),
    ]
    region = canvas[y0:y1, x0:x1]
    region[inside, :3] = sample
    region[inside, 3] = 1.0


def draw_stem(
    canvas: Floats, points: list[tuple[float, float]], radius: float, colour: Vec
) -> None:
    """A thick polyline (distance to the segments <= radius) in ``colour``."""
    height, wide = canvas.shape[:2]
    ys, xs = np.mgrid[0:height, 0:wide]
    px, py = xs + 0.5, ys + 0.5
    for (ax, ay), (bx, by) in itertools.pairwise(points):
        seg = np.array([bx - ax, by - ay])
        t = np.clip(((px - ax) * seg[0] + (py - ay) * seg[1]) / float(seg @ seg), 0.0, 1.0)
        distance = np.hypot(px - (ax + t * seg[0]), py - (ay + t * seg[1]))
        hit = distance <= radius
        canvas[hit, :3] = colour
        canvas[hit, 3] = 1.0


def lentisc_sprite(source: Floats) -> Floats:
    """A twig: a stem with alternate leaves, shorter and more upright towards the tip."""
    width, height = SPRITE
    canvas = np.zeros((height, width, 4), dtype=np.float32)
    x0, y0, x1, y1 = LENTISC_STEM_PIXELS
    stem_colour = source[y0:y1, x0:x1].reshape(-1, 3).mean(axis=0).astype(np.float64)
    top = (width / 2.0 + 14.0, 30.0)
    bottom = (width / 2.0, height - 8.0)
    draw_stem(canvas, [bottom, top], 3.0, stem_colour)
    for k in range(10):
        s = 0.1 + 0.85 * k / 9.0
        base = (bottom[0] + (top[0] - bottom[0]) * s, bottom[1] + (top[1] - bottom[1]) * s)
        side = 1.0 if k % 2 == 0 else -1.0
        angle = side * np.radians(62.0 - 38.0 * s)
        paste_leaf(canvas, source, LENTISC_LEAVES[k % 3], base, angle, 190.0 - 70.0 * s)
    paste_leaf(canvas, source, LENTISC_LEAVES[0], top, 0.0, 100.0)
    return canvas


def rosemary_sprite(source: Floats) -> Floats:
    """A fan of long narrow leaves from one point."""
    width, height = SPRITE
    canvas = np.zeros((height, width, 4), dtype=np.float32)
    base = (width / 2.0, height - 6.0)
    for k in range(9):
        angle = np.radians(-58.0 + 116.0 * k / 8.0)
        paste_leaf(
            canvas, source, ROSEMARY_LEAVES[k % 3], base, angle, 470.0 - 90.0 * abs(angle), 0.42
        )
    return canvas


def grass_sprite(diffuse: Floats) -> Floats:
    """Three blades cut from their black background and fitted to the sprite cell."""
    x0, y0, x1, y1 = GRASS_CROP
    crop = diffuse[y0:y1, x0:x1]
    alpha = (crop.max(axis=2) > GRASS_BLACK).astype(np.float32)
    rgba = np.concatenate([crop, alpha[..., None]], axis=2)
    width, height = SPRITE
    scale = min(width / rgba.shape[1], height / rgba.shape[0])
    fitted = pine.resize(rgba, round(rgba.shape[0] * scale), round(rgba.shape[1] * scale))
    canvas = np.zeros((height, width, 4), dtype=np.float32)
    top = height - fitted.shape[0]
    left = (width - fitted.shape[1]) // 2
    canvas[top:, left : left + fitted.shape[1]] = fitted
    canvas[..., 3] = (canvas[..., 3] > 0.5).astype(np.float32)
    return canvas


def blob_silhouette(
    colour: Vec, size: tuple[int, int], seed: int, spread: float, flat: float
) -> Floats:
    """A bush silhouette (seeded blobs standing on the bottom edge) as straight RGBA."""
    rng = np.random.default_rng(seed)
    width, height = size
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float64)
    xx, yy = xx / width, yy / height
    alpha = np.zeros((height, width))
    for _ in range(40):
        cx = float(np.clip(0.5 + rng.normal(0.0, spread), 0.2, 0.8))
        cy = float(np.clip(0.62 + rng.normal(0.0, 0.12), 0.35, 0.8))
        rx, ry = rng.uniform(0.1, 0.2), rng.uniform(0.07, 0.14) * flat
        alpha = np.maximum(alpha, (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) < 1.0)
    coarse = 0.75 + 0.5 * rng.random((32, 32, 1))
    shade = pine.resize(coarse.astype(np.float32), height, width)[..., 0]
    rgb = np.clip(colour[None, None, :] * shade[..., None], 0.0, 1.0)
    return np.concatenate([rgb, alpha[..., None]], axis=2).astype(np.float32)


def build_atlas() -> Atlas:
    shrub_04 = pine._read_rgb(SHRUB_04)
    sx0, sy0, sx1, sy1 = LENTISC_STEM_PIXELS
    stem_colour = shrub_04[sy0:sy1, sx0:sx1].reshape(-1, 3).mean(axis=0)
    shrub_02 = pine._read_rgb(SHRUB_02)
    grass = pine._read_rgb(GRASS_02)
    atlas = np.zeros((ATLAS_SIZE[1], ATLAS_SIZE[0], 4), dtype=np.float32)
    sprites = {
        "lentisc": lentisc_sprite(shrub_04),
        "rosemary": rosemary_sprite(shrub_02),
        "grass": grass_sprite(grass),
    }
    tints = {"lentisc": LENTISC_TINT, "rosemary": ROSEMARY_TINT, "grass": (1.0, 1.0, 1.0)}
    means = {}
    for name, sprite in sprites.items():
        sprite[..., :3] = np.clip(sprite[..., :3] * np.array(tints[name], dtype=np.float32), 0, 1)
        means[name] = sprite[sprite[..., 3] > 0.5][:, :3].mean(axis=0).astype(np.float64)
        x0, y0, x1, y1 = CELLS[name]
        atlas[y0:y1, x0:x1] = sprite
    for name, spread, flat in (("lentisc", 0.16, 1.0), ("rosemary", 0.2, 0.7)):
        x0, y0, x1, y1 = CELLS[f"{name}_far"]
        atlas[y0:y1, x0:x1] = blob_silhouette(
            means[name], (x1 - x0, y1 - y0), SEEDS[name] + 9, spread, flat
        )
    sx0, sy0, sx1, sy1 = CELLS["stem"]
    atlas[sy0:sy1, sx0:sx1, :3] = stem_colour
    atlas[sy0:sy1, sx0:sx1, 3] = 1.0
    # colour under fully transparent pixels: the sprite mean, never black (texture filtering)
    for name in ("lentisc", "rosemary", "grass"):
        x0, y0, x1, y1 = CELLS[name]
        cell = atlas[y0:y1, x0:x1]
        cell[cell[..., 3] == 0.0, :3] = means[name]
        if name != "grass":
            fx0, fy0, fx1, fy1 = CELLS[f"{name}_far"]
            far = atlas[fy0:fy1, fx0:fx1]
            far[far[..., 3] == 0.0, :3] = means[name]
    return Atlas(np.rint(atlas * 255.0).astype(np.uint8), dict(CELLS))


def _uv(cell: tuple[int, int, int, int]) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = cell
    return x0 / ATLAS_SIZE[0], y0 / ATLAS_SIZE[1], x1 / ATLAS_SIZE[0], y1 / ATLAS_SIZE[1]


# --- skeletons ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Shape:
    """How a plant is grown and meshed at one level of detail."""

    stems: int
    stem_length: tuple[float, float]  # fraction of the nominal height
    elevation: tuple[float, float]  # radians above the horizontal at the stem foot
    tuft_at: tuple[float, ...]  # fractions along a stem
    fillers: int  # extra tufts on random stems
    tuft_size: float  # card length is 1.9 x this (metres)
    cards: int  # crossed cards per tuft at LOD0
    spread: float  # horizontal radius of the stem feet


SHAPES = {
    "lentisc": Shape(6, (0.8, 1.0), (1.0, 1.3), (0.45, 0.6, 0.75, 0.9, 1.0), 60, 0.30, 4, 0.12),
    "rosemary": Shape(9, (0.75, 1.0), (0.95, 1.4), (0.5, 0.7, 0.85, 1.0), 30, 0.24, 3, 0.1),
}
GRASS_BLADES = (12, 5)  # cards at LOD0 and LOD1


def _stem(rng: np.random.Generator, shape: Shape, height: float, index: int) -> Tube:
    azimuth = 2.0 * np.pi * (index + rng.uniform(-0.2, 0.2)) / shape.stems
    elevation = rng.uniform(*shape.elevation)
    length = height * rng.uniform(*shape.stem_length)
    heading = np.array([np.cos(azimuth), 0.0, np.sin(azimuth)])
    start = heading * rng.uniform(0.0, shape.spread)
    points = [start]
    for _ in range(3):
        direction = np.cos(elevation) * heading + np.sin(elevation) * np.array([0.0, 1.0, 0.0])
        points.append(points[-1] + (direction + rng.normal(0.0, 0.06, size=3)) * length / 3.0)
        elevation = max(elevation - rng.uniform(0.0, 0.12), 0.5)
    radius = rng.uniform(0.02, 0.03)
    return Tube(np.array(points), radius * np.linspace(1.0, 0.3, 4), main=True, trunk=False)


def plant_parts(name: str, level: str, atlas: Atlas) -> list[Any]:
    """Tube and card parts of ``name`` at ``level`` (raw, before normalisation)."""
    model = next(m for m in understory.MODELS if m.id == name)
    rng = np.random.default_rng(SEEDS[name])
    uv = _uv(atlas.cells[name])
    cx0, cy0, cx1, cy1 = atlas.cells["stem"]
    stem_uv = _uv((cx0 + 8, cy0 + 8, cx1 - 8, cy1 - 8))
    near = level == "lod0"
    parts: list[Any] = []
    if name == "grass":
        count = GRASS_BLADES[0 if near else 1]
        for _ in range(count):
            tilt = rng.uniform(0.15, 0.7)
            azimuth = rng.uniform(0.0, 2.0 * np.pi)
            direction = unit(
                np.array(
                    [np.sin(tilt) * np.cos(azimuth), np.cos(tilt), np.sin(tilt) * np.sin(azimuth)]
                )
            )
            foot = np.array([rng.normal(0.0, 0.03), 0.0, rng.normal(0.0, 0.03)])
            tuft = Tuft(
                foot, direction, 0.27 * rng.uniform(0.8, 1.2) * (1.0 if near else 1.3), False
            )
            centre = np.array([0.0, 0.5 * model.height, 0.0])
            parts.append(
                pine.card_mesh(tuft, 1, 1.0, (uv, uv), centre, float(rng.uniform(0, np.pi)))
            )
        return parts
    shape = SHAPES[name]
    stems = [_stem(rng, shape, model.height, i) for i in range(shape.stems)]
    for stem in stems:
        parts.append(pine.tube_mesh(stem, 3, stem_uv, np.ones(len(stem.radii))))
    tufts: list[Tuft] = []
    for stem in stems:
        for s in shape.tuft_at:
            position, direction = pine._along(stem, s)
            tufts.append(
                Tuft(position, direction, shape.tuft_size * rng.uniform(0.85, 1.15), False)
            )
    for _ in range(shape.fillers):
        stem = stems[int(rng.integers(0, len(stems)))]
        position, direction = pine._along(stem, float(rng.uniform(0.35, 1.0)))
        out = unit(direction + rng.normal(0.0, 0.7, size=3) + np.array([0.0, 0.2, 0.0]))
        tufts.append(Tuft(position, out, shape.tuft_size * rng.uniform(0.7, 1.1), False))
    stride, cards, scale = (1, shape.cards, 1.0) if near else (3, 2, 1.4)
    centre = np.array([0.0, 0.5 * model.height, 0.0])
    for tuft in tufts[::stride]:
        parts.append(
            pine.card_mesh(tuft, cards, scale, (uv, uv), centre, float(rng.uniform(0, np.pi)))
        )
    return parts


def _assemble(
    parts: list[Any],
) -> tuple[Vec, Vec, Vec, npt.NDArray[np.int64]]:
    offsets = np.cumsum([0, *(len(p[0]) for p in parts[:-1])])
    return (
        np.concatenate([p[0] for p in parts]),
        np.concatenate([p[1] for p in parts]),
        np.concatenate([p[2] for p in parts]),
        np.concatenate([p[3] + o for p, o in zip(parts, offsets, strict=True)]),
    )


def model_scale(name: str, atlas: Atlas) -> tuple[float, float]:
    """Horizontal and vertical factors giving the LOD0 of ``name`` its nominal size: its top at
    the nominal height and 90 % of its vertices within the nominal radius of the axis."""
    model = next(m for m in understory.MODELS if m.id == name)
    positions = _assemble(plant_parts(name, "lod0", atlas))[0]
    radial = np.hypot(positions[:, 0], positions[:, 2])
    return (
        float(model.radius / np.percentile(radial, 90)),
        float(model.height / positions[:, 1].max()),
    )


def build_plant(name: str, level: str, atlas: Atlas) -> PlantMesh:
    positions, normals, uvs, triangles = _assemble(plant_parts(name, level, atlas))
    horizontal, vertical = model_scale(name, atlas)
    factors = np.array([horizontal, vertical, horizontal])
    positions = positions * factors
    positions[:, 1] = np.maximum(positions[:, 1], 0.0)
    return PlantMesh(
        f"{name}_{level}",
        positions.astype(np.float32),
        unit(normals / factors).astype(np.float32),
        uvs.astype(np.float32),
        triangles.astype(np.int32),
    )


def far_card(name: str, atlas: Atlas) -> PlantMesh:
    """Two crossed quads as wide as the nominal crown with the silhouette (or the sprite)."""
    model = next(m for m in understory.MODELS if m.id == name)
    cell = atlas.cells[f"{name}_far"] if f"{name}_far" in atlas.cells else atlas.cells[name]
    u0, v0, u1, v1 = _uv(cell)
    half = model.radius * 1.1
    quads, uvs, triangles = [], [], []
    for k, (dx, dz) in enumerate(((1.0, 0.0), (0.0, 1.0))):
        quads.append(
            [
                (-dx * half, 0.0, -dz * half),
                (dx * half, 0.0, dz * half),
                (dx * half, model.height, dz * half),
                (-dx * half, model.height, -dz * half),
            ]
        )
        uvs.append([(u0, v1), (u1, v1), (u1, v0), (u0, v0)])
        triangles.append(np.array([[0, 1, 2], [0, 2, 3]]) + 4 * k)
    flat = np.array(quads, dtype=np.float64).reshape(-1, 3)
    horizontal = flat.copy()
    horizontal[:, 1] = 0.0
    normals = unit(unit(horizontal) + np.array([0.0, 0.8, 0.0]))
    return PlantMesh(
        f"{name}_card",
        flat.astype(np.float32),
        normals.astype(np.float32),
        np.array(uvs, dtype=np.float32).reshape(-1, 2),
        np.concatenate(triangles).astype(np.int32),
    )


def build_meshes(atlas: Atlas) -> list[PlantMesh]:
    meshes = []
    for model in understory.MODELS:
        meshes.append(build_plant(model.id, "lod0", atlas))
        meshes.append(build_plant(model.id, "lod1", atlas))
        meshes.append(far_card(model.id, atlas))
    return meshes


# --- Blender and the artefact -------------------------------------------------------------------


def export_plants(meshes: list[PlantMesh], atlas: Atlas, out: Path) -> Path:
    """Build the meshes in a fresh Blender state and write the (unoptimised) GLB to ``out``."""
    return pine.export_scene(meshes, atlas, out, MATERIAL_NAME)


def manifest(meshes: list[PlantMesh], atlas: Atlas, glb_bytes: int) -> dict[str, Any]:
    return {
        "version": 1,
        "shape": "generated by blender/plants.py, not measured; leaf and blade pixels come from "
        "the Poly Haven shrub_04, shrub_02 and grass_medium_02 textures (CC0)",
        "licence": "CC0 1.0",
        "attribution": "Textures: Rico Cilliers, Poly Haven (polyhaven.com), CC0 (credited as "
        "courtesy); plant shapes generated by the project",
        "models": [understory.model_description(m) for m in understory.MODELS],
        "file": {"name": PLANTS_GLB, "bytes": glb_bytes},
        "material": {"name": MATERIAL_NAME, "alphaMode": "MASK", "atlas": list(ATLAS_SIZE)},
        "atlas": {name: list(cell) for name, cell in atlas.cells.items()},
        "meshes": [
            {"name": m.name, "triangles": m.triangle_count, "vertices": len(m.positions)}
            for m in meshes
        ],
        "budget": {"lod0MaxTriangles": LOD0_MAX_TRIANGLES, "lod1MaxTriangles": LOD1_MAX_TRIANGLES},
        "instancing": "scale uniformly by the instance's scale (height / nominal height); y of "
        "an instance is the uncarved 1 m DEM, resample the ground on the rendered terrain",
        "notes": [
            "the leaf outlines are analytic: the source JPEGs have no alpha channel",
            "the atlas alpha loses coverage in the mips: use alpha-to-coverage (E2.5)",
        ],
    }


def run_plants(out_dir: Path = PINE_GENERATED, build_dir: Path = PLANTS_BUILD) -> dict[str, Any]:
    """Build the plants, export and optimise them (KTX2 + meshopt) into ``out_dir``."""
    atlas = build_atlas()
    meshes = build_meshes(atlas)
    raw = export_plants(meshes, atlas, build_dir / PLANTS_GLB)
    out_dir.mkdir(parents=True, exist_ok=True)
    glb_bytes = tiles.optimize_glb(raw, out_dir / PLANTS_GLB)
    document = {**manifest(meshes, atlas, glb_bytes), **artefacts.provenance("plants")}
    (out_dir / PLANTS_JSON).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return document
