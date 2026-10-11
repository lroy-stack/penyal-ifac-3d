"""Visitor-centre GLB export through Blender (``bpy``).

The geometry (flat-shaded triangle soup with a linear RGB tint, UVs in metres and a surface per
triangle) is computed with numpy in ``buildings``; this module only builds one Blender object
with one material per surface (a tiled albedo texture multiplied by the vertex colour) and
exports it with the options ``spike`` proved byte-reproducible, textures as JPEG. Frames and
winding are handled exactly like ``structures``.
"""

import importlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from penyal_pipeline.blender.spike import export_glb
from penyal_pipeline.blender.terrain import blender_uvs, to_blender
from penyal_pipeline.buildings import SURFACES, TEXTURE_SIZE, BuildingMesh

MATERIAL_PREFIX = "buildings_"
COLOUR_LAYER = "Col"
UV_LAYER = "UVMap"
ROUGHNESS = 0.9
JPEG_QUALITY = 95  # intermediate: the optimise step re-encodes to KTX2
EXPORT_OVERRIDES: dict[str, Any] = {
    "export_image_format": "JPEG",
    "export_jpeg_quality": JPEG_QUALITY,
}


def _material(bpy: Any, surface: str, texture: Path) -> Any:
    image = bpy.data.images.load(str(texture))
    image.name = f"{MATERIAL_PREFIX}{surface}"
    if tuple(image.size) != (TEXTURE_SIZE, TEXTURE_SIZE):
        image.scale(TEXTURE_SIZE, TEXTURE_SIZE)
    image.pack()
    material = bpy.data.materials.new(f"{MATERIAL_PREFIX}{surface}")
    material.use_backface_culling = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = ROUGHNESS
    bsdf.inputs["Metallic"].default_value = 0.0
    texture_node = nodes.new("ShaderNodeTexImage")
    texture_node.image = image
    colour = nodes.new("ShaderNodeVertexColor")
    colour.layer_name = COLOUR_LAYER
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    links.new(texture_node.outputs["Color"], mix.inputs["A"])
    links.new(colour.outputs["Color"], mix.inputs["B"])
    links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    return material


def build_scene(bpy: Any, mesh_data: BuildingMesh, textures: Sequence[Path]) -> None:
    """Replace the current Blender scene with one object holding ``mesh_data``."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    triangles = mesh_data.triangles.astype(np.int32)
    mesh = bpy.data.meshes.new(mesh_data.name)
    mesh.vertices.add(len(mesh_data.positions))
    mesh.vertices.foreach_set("co", to_blender(mesh_data.positions).reshape(-1))
    mesh.loops.add(triangles.size)
    mesh.loops.foreach_set("vertex_index", triangles.reshape(-1))
    mesh.polygons.add(len(triangles))
    mesh.polygons.foreach_set("loop_start", np.arange(len(triangles), dtype=np.int32) * 3)
    mesh.polygons.foreach_set("loop_total", np.full(len(triangles), 3, dtype=np.int32))
    mesh.polygons.foreach_set("use_smooth", np.zeros(len(triangles), dtype=np.bool_))
    mesh.polygons.foreach_set("material_index", mesh_data.materials.astype(np.int32))
    mesh.update(calc_edges=True)
    mesh.validate()
    mesh.normals_split_custom_set_from_vertices(to_blender(mesh_data.normals).tolist())
    layer = mesh.uv_layers.new(name=UV_LAYER)
    layer.data.foreach_set(
        "uv", blender_uvs(mesh_data.uvs)[triangles.reshape(-1)].reshape(-1).astype(np.float32)
    )
    colours = mesh.color_attributes.new(COLOUR_LAYER, "FLOAT_COLOR", "POINT")
    rgba = np.concatenate(
        [mesh_data.colours, np.ones((len(mesh_data.colours), 1), dtype=np.float32)], axis=1
    )
    colours.data.foreach_set("color", rgba.astype(np.float32).reshape(-1))
    for surface, texture in zip(SURFACES, textures, strict=True):
        mesh.materials.append(_material(bpy, surface, texture))
    bpy.context.scene.collection.objects.link(bpy.data.objects.new(mesh_data.name, mesh))


def export_buildings(mesh_data: BuildingMesh, textures: Sequence[Path], out: Path) -> Path:
    """Build ``mesh_data`` in a fresh Blender state and write the GLB to ``out``."""
    bpy = importlib.import_module("bpy")
    build_scene(bpy, mesh_data, textures)
    export_glb(bpy, out, EXPORT_OVERRIDES)
    return out
