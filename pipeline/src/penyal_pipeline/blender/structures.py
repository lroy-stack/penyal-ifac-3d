"""Staircase GLB export through Blender (``bpy``).

The geometry (flat-shaded triangle soup with one material slot per face) is computed with numpy
in ``structures``; this module only builds the Blender objects, one per staircase, with two
untextured PBR materials (stone steps, metal handrail: flat factors, no downloaded texture) and
exports them with the options ``spike`` proved byte-reproducible. Frames and winding are handled
exactly like ``tunnel``.
"""

import importlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from penyal_pipeline.blender.spike import export_glb
from penyal_pipeline.blender.terrain import to_blender
from penyal_pipeline.structures import STONE, StairMesh

STONE_COLOUR = (0.45, 0.43, 0.40, 1.0)  # linear RGB, weathered limestone paving
STONE_ROUGHNESS = 0.9
METAL_COLOUR = (0.12, 0.12, 0.13, 1.0)  # linear RGB, dark painted steel
METAL_ROUGHNESS = 0.5
METAL_METALLIC = 0.9
STONE_MATERIAL = "stairs_stone"
METAL_MATERIAL = "stairs_handrail_metal"


def _material(
    bpy: Any,
    name: str,
    colour: tuple[float, float, float, float],
    roughness: float,
    metallic: float,
) -> Any:
    material = bpy.data.materials.new(name)
    material.use_backface_culling = True
    bsdf = material.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = colour
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return material


def build_scene(bpy: Any, meshes: Sequence[StairMesh]) -> None:
    """Replace the current Blender scene with one object per staircase mesh."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    stone = _material(bpy, STONE_MATERIAL, STONE_COLOUR, STONE_ROUGHNESS, 0.0)
    metal = _material(bpy, METAL_MATERIAL, METAL_COLOUR, METAL_ROUGHNESS, METAL_METALLIC)
    assert STONE == 0  # slot order: stone first, metal second
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
        mesh.polygons.foreach_set("material_index", item.materials.astype(np.int32))
        mesh.update(calc_edges=True)
        mesh.validate()
        mesh.normals_split_custom_set_from_vertices(to_blender(item.normals).tolist())
        mesh.materials.append(stone)
        mesh.materials.append(metal)
        bpy.context.scene.collection.objects.link(bpy.data.objects.new(item.name, mesh))


def export_structures(meshes: Sequence[StairMesh], out: Path) -> Path:
    """Build ``meshes`` in a fresh Blender state and write the GLB to ``out``."""
    bpy = importlib.import_module("bpy")
    build_scene(bpy, meshes)
    export_glb(bpy, out)
    return out
