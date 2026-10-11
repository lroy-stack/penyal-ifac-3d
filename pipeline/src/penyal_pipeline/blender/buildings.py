"""Visitor-centre GLB export through Blender (``bpy``).

The geometry (flat-shaded triangle soup with a linear RGB colour per vertex) is computed with
numpy in ``buildings``; this module only builds one Blender object per building with a single
untextured PBR material whose base colour is read from the vertex colours (no downloaded
texture), and exports it with the options ``spike`` proved byte-reproducible. Frames and winding
are handled exactly like ``structures``.
"""

import importlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from penyal_pipeline.blender.spike import export_glb
from penyal_pipeline.blender.terrain import to_blender
from penyal_pipeline.buildings import BuildingMesh

MATERIAL_NAME = "buildings_painted"
COLOUR_LAYER = "Col"
ROUGHNESS = 0.9


def _material(bpy: Any) -> Any:
    material = bpy.data.materials.new(MATERIAL_NAME)
    material.use_backface_culling = True
    nodes = material.node_tree.nodes
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = ROUGHNESS
    bsdf.inputs["Metallic"].default_value = 0.0
    colour = nodes.new("ShaderNodeVertexColor")
    colour.layer_name = COLOUR_LAYER
    material.node_tree.links.new(colour.outputs["Color"], bsdf.inputs["Base Color"])
    return material


def build_scene(bpy: Any, meshes: Sequence[BuildingMesh]) -> None:
    """Replace the current Blender scene with one object per building mesh."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    material = _material(bpy)
    for item in meshes:
        triangles = item.triangles.astype(np.int32)
        mesh = bpy.data.meshes.new(item.name)
        mesh.vertices.add(len(item.positions))
        mesh.vertices.foreach_set("co", to_blender(item.positions).reshape(-1))
        mesh.loops.add(triangles.size)
        mesh.loops.foreach_set("vertex_index", triangles.reshape(-1))
        mesh.polygons.add(len(triangles))
        mesh.polygons.foreach_set("loop_start", np.arange(len(triangles), dtype=np.int32) * 3)
        mesh.polygons.foreach_set("loop_total", np.full(len(triangles), 3, dtype=np.int32))
        mesh.polygons.foreach_set("use_smooth", np.zeros(len(triangles), dtype=np.bool_))
        mesh.update(calc_edges=True)
        mesh.validate()
        mesh.normals_split_custom_set_from_vertices(to_blender(item.normals).tolist())
        layer = mesh.color_attributes.new(COLOUR_LAYER, "FLOAT_COLOR", "POINT")
        rgba = np.concatenate(
            [item.colours, np.ones((len(item.colours), 1), dtype=np.float32)], axis=1
        )
        layer.data.foreach_set("color", rgba.astype(np.float32).reshape(-1))
        mesh.materials.append(material)
        bpy.context.scene.collection.objects.link(bpy.data.objects.new(item.name, mesh))


def export_buildings(meshes: Sequence[BuildingMesh], out: Path) -> Path:
    """Build ``meshes`` in a fresh Blender state and write the GLB to ``out``."""
    bpy = importlib.import_module("bpy")
    build_scene(bpy, meshes)
    export_glb(bpy, out)
    return out
