"""End-to-end asset spike: a deterministic textured terrain-like grid exported as GLB.

The geometry and the texture are computed with numpy (pure, testable without Blender); only
``build_scene`` and ``export_glb`` touch ``bpy``. The output must be byte-identical across runs.
"""

import contextlib
import importlib
import sys
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from penyal_pipeline.paths import SPIKE_GLB

GRID_VERTICES = 129
GRID_SIZE_M = 256.0
TEXTURE_SIZE = 512
CHECKER_CELLS = 16

# Exporter options, checked against bpy 5.2.2 (`bpy.ops.export_scene.gltf.get_rna_type()`).
# `export_extras` and `export_keep_originals` stay off so no Blender-side metadata or file paths
# leak into the output.
EXPORT_OPTIONS: dict[str, Any] = {
    "export_format": "GLB",
    "export_image_format": "AUTO",
    "export_yup": True,
    "export_apply": True,
    "export_texcoords": True,
    "export_normals": True,
    "export_tangents": False,
    "export_materials": "EXPORT",
    "export_animations": False,
    "export_cameras": False,
    "export_lights": False,
    "export_extras": False,
    "export_keep_originals": False,
    "use_selection": False,
}


def height_at(x: NDArray[np.float64], y: NDArray[np.float64]) -> NDArray[np.float64]:
    """Analytic relief in metres: a central hill with two gentle ripples. No randomness."""
    radius_sq = x * x + y * y
    hill = 40.0 * np.exp(-radius_sq / (2.0 * 60.0**2))
    ripples = 3.0 * np.sin(x / 20.0) * np.cos(y / 25.0)
    return hill + ripples


def grid_vertices(count: int = GRID_VERTICES, size: float = GRID_SIZE_M) -> NDArray[np.float32]:
    """``count * count`` vertices (row-major, x fastest), centred on the origin, z up."""
    axis = np.linspace(-size / 2.0, size / 2.0, count, dtype=np.float64)
    x, y = np.meshgrid(axis, axis)
    z = height_at(x, y)
    return np.stack([x, y, z], axis=-1).reshape(-1, 3).astype(np.float32)


def grid_uvs(count: int = GRID_VERTICES) -> NDArray[np.float32]:
    """Per-vertex UVs spanning 0..1 in both axes."""
    axis = np.linspace(0.0, 1.0, count, dtype=np.float64)
    u, v = np.meshgrid(axis, axis)
    return np.stack([u, v], axis=-1).reshape(-1, 2).astype(np.float32)


def grid_quads(count: int = GRID_VERTICES) -> NDArray[np.int32]:
    """Counter-clockwise quad indices, shape ``((count-1)**2, 4)``."""
    row, col = np.meshgrid(np.arange(count - 1), np.arange(count - 1), indexing="ij")
    base = (row * count + col).reshape(-1)
    return np.stack([base, base + 1, base + count + 1, base + count], axis=-1).astype(np.int32)


def checker_pixels(size: int = TEXTURE_SIZE) -> NDArray[np.float32]:
    """RGBA float pixels (rows bottom-to-top, as Blender stores them): checker over a gradient."""
    coords = np.arange(size)
    cell = size // CHECKER_CELLS
    parity = ((coords[:, None] // cell) + (coords[None, :] // cell)) % 2
    shade = np.where(parity == 0, 1.0, 0.55)
    ramp_x = (coords / (size - 1))[None, :]
    ramp_y = (coords / (size - 1))[:, None]
    red = shade * (0.25 + 0.75 * ramp_x)
    green = shade * (0.25 + 0.75 * ramp_y)
    blue = shade * (1.0 - 0.6 * ramp_x)
    alpha = np.ones((size, size))
    return np.stack([red, green, blue, alpha], axis=-1).astype(np.float32).reshape(-1)


def _import_bpy() -> Any:
    return importlib.import_module("bpy")


def build_scene(bpy: Any) -> None:
    """Replace the current scene with the textured grid mesh."""
    bpy.ops.wm.read_factory_settings(use_empty=True)

    mesh = bpy.data.meshes.new("spike_terrain")
    vertices = grid_vertices()
    quads = grid_quads()
    mesh.vertices.add(len(vertices))
    mesh.vertices.foreach_set("co", vertices.reshape(-1))
    mesh.loops.add(quads.size)
    mesh.loops.foreach_set("vertex_index", quads.reshape(-1))
    mesh.polygons.add(len(quads))
    mesh.polygons.foreach_set("loop_start", np.arange(len(quads), dtype=np.int32) * 4)
    mesh.polygons.foreach_set("loop_total", np.full(len(quads), 4, dtype=np.int32))
    mesh.polygons.foreach_set("use_smooth", np.ones(len(quads), dtype=np.bool_))
    uv_layer = mesh.uv_layers.new(name="UVMap")
    uv_layer.data.foreach_set("uv", grid_uvs()[quads.reshape(-1)].reshape(-1))
    mesh.update(calc_edges=True)
    mesh.validate()

    image = bpy.data.images.new("spike_checker", TEXTURE_SIZE, TEXTURE_SIZE, alpha=False)
    image.pixels.foreach_set(checker_pixels())
    image.update()
    image.pack()

    material = bpy.data.materials.new("spike_material")
    nodes = material.node_tree.nodes
    bsdf = nodes["Principled BSDF"]
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    material.node_tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    mesh.materials.append(material)

    terrain = bpy.data.objects.new("spike_terrain", mesh)
    bpy.context.scene.collection.objects.link(terrain)


def export_glb(bpy: Any, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    # The exporter prints progress on stdout; keep stdout clean for callers.
    with contextlib.redirect_stdout(sys.stderr):
        result = bpy.ops.export_scene.gltf(filepath=str(out), **EXPORT_OPTIONS)
    if "FINISHED" not in result or not out.exists():
        raise RuntimeError(f"glTF export did not finish (returned {sorted(result)}).")


def run_spike(out: Path = SPIKE_GLB) -> Path:
    """Build the spike scene in a fresh Blender state and write it to ``out``."""
    bpy = _import_bpy()
    build_scene(bpy)
    export_glb(bpy, out)
    return out
