"""Terrain GLB export through Blender (``bpy``).

Geometry, normals, UVs and the texture are computed with numpy elsewhere (``tiles``, ``ortho``);
this module only turns them into a Blender mesh with a Principled BSDF material and exports one
GLB, using the exporter options that ``spike`` proved byte-reproducible.

Frames: arrays arrive in the local frame (``x`` east, ``y`` up, ``z`` south). Blender is Z-up,
so a vertex is stored as ``(x, -z, y)``; the exporter's ``export_yup`` maps it back to
``(x, y, z)``, which keeps the glTF in local-frame metres with no node offsets. The rotation has
determinant +1, so triangle winding is preserved.

UVs arrive in the glTF convention (``v`` measured downwards from the top row of the image) and
are flipped to Blender's bottom-left origin here; the exporter flips them back. The image is
supplied top-down (row 0 = north) and stored bottom-up, as Blender expects.
"""

import importlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from penyal_pipeline.blender.spike import export_glb


class _WarningsOnly(logging.Filter):
    """The glTF exporter logs several INFO lines per export; keep warnings and errors."""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= logging.WARNING


logging.getLogger("glTFImporter").addFilter(_WarningsOnly())

ROUGHNESS = 0.9
METALLIC = 0.0

type Floats = npt.NDArray[np.float32]
type Ints = npt.NDArray[np.int32]
type Rgb = npt.NDArray[np.uint8]


@dataclass(frozen=True)
class TerrainExport:
    """Everything needed to export one textured terrain mesh."""

    name: str
    positions: Floats  # (n, 3) local frame
    normals: Floats  # (n, 3) local frame, unit length
    uvs: Floats  # (n, 2) glTF convention
    triangles: Ints  # (m, 3) counter-clockwise seen from +Y
    rgb: Rgb  # (h, w, 3) top-down


def to_blender(vectors: Floats) -> Floats:
    """Local ``(x, y, z)`` points or directions to Blender ``(x, -z, y)``."""
    return np.stack([vectors[:, 0], -vectors[:, 2], vectors[:, 1]], axis=1).astype(np.float32)


def blender_uvs(uvs: Floats) -> Floats:
    """glTF ``(u, v)`` to Blender ``(u, 1 - v)``."""
    return np.stack([uvs[:, 0], 1.0 - uvs[:, 1]], axis=1).astype(np.float32)


def image_pixels(rgb: Rgb) -> Floats:
    """Flat RGBA float pixels, rows bottom-to-top, from a top-down RGB uint8 image."""
    height, width, _ = rgb.shape
    pixels = np.ones((height, width, 4), dtype=np.float32)
    pixels[..., :3] = rgb[::-1].astype(np.float32) / 255.0
    return pixels.reshape(-1)


def build_scene(bpy: Any, item: TerrainExport) -> None:
    """Replace the current Blender scene with the textured terrain mesh of ``item``."""
    bpy.ops.wm.read_factory_settings(use_empty=True)

    triangles = item.triangles.astype(np.int32)
    mesh = bpy.data.meshes.new(item.name)
    mesh.vertices.add(len(item.positions))
    mesh.vertices.foreach_set("co", to_blender(item.positions).reshape(-1))
    mesh.loops.add(triangles.size)
    mesh.loops.foreach_set("vertex_index", triangles.reshape(-1))
    mesh.polygons.add(len(triangles))
    mesh.polygons.foreach_set("loop_start", np.arange(len(triangles), dtype=np.int32) * 3)
    mesh.polygons.foreach_set("loop_total", np.full(len(triangles), 3, dtype=np.int32))
    mesh.polygons.foreach_set("use_smooth", np.ones(len(triangles), dtype=np.bool_))
    uv_layer = mesh.uv_layers.new(name="UVMap")
    uv_layer.data.foreach_set("uv", blender_uvs(item.uvs)[triangles.reshape(-1)].reshape(-1))
    mesh.update(calc_edges=True)
    mesh.validate()
    mesh.normals_split_custom_set_from_vertices(to_blender(item.normals).tolist())

    height, width, _ = item.rgb.shape
    image = bpy.data.images.new(f"{item.name}_ortho", width, height, alpha=False)
    image.pixels.foreach_set(image_pixels(item.rgb))
    image.update()
    image.pack()

    material = bpy.data.materials.new("terrain")
    material.use_backface_culling = True
    nodes = material.node_tree.nodes
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = ROUGHNESS
    bsdf.inputs["Metallic"].default_value = METALLIC
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.extension = "EXTEND"
    material.node_tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    mesh.materials.append(material)

    terrain = bpy.data.objects.new(item.name, mesh)
    bpy.context.scene.collection.objects.link(terrain)


def export_terrain(item: TerrainExport, out: Path) -> Path:
    """Build ``item`` in a fresh Blender state and write the GLB to ``out``."""
    bpy = importlib.import_module("bpy")
    build_scene(bpy, item)
    export_glb(bpy, out)
    return out
