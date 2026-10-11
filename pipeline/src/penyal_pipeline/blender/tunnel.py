"""Tunnel interior GLB export through Blender (``bpy``).

The shell (positions, inward normals, winding) is computed with numpy in ``tunnel_geometry``;
this module only turns it into a Blender mesh with one plain rock-grey material (no textures,
no photographs) and exports it with the options ``spike`` proved byte-reproducible. Frames and
winding are handled exactly like ``terrain``. The material is double-sided so the vault stays
rock-coloured where the DEM surface dips below it near a portal.
"""

import importlib
from pathlib import Path
from typing import Any

import numpy as np

from penyal_pipeline.blender.spike import export_glb
from penyal_pipeline.blender.terrain import to_blender
from penyal_pipeline.tunnel_geometry import ShellMesh

ROCK_COLOUR = (0.36, 0.34, 0.31, 1.0)  # linear RGB, limestone grey
ROUGHNESS = 0.95
METALLIC = 0.0
OBJECT_NAME = "tunnel_interior"
MATERIAL_NAME = "tunnel_rock"


def build_scene(bpy: Any, shell: ShellMesh) -> None:
    """Replace the current Blender scene with the tunnel interior."""
    bpy.ops.wm.read_factory_settings(use_empty=True)

    triangles = shell.triangles.astype(np.int32)
    mesh = bpy.data.meshes.new(OBJECT_NAME)
    mesh.vertices.add(len(shell.positions))
    mesh.vertices.foreach_set("co", to_blender(shell.positions).reshape(-1))
    mesh.loops.add(triangles.size)
    mesh.loops.foreach_set("vertex_index", triangles.reshape(-1))
    mesh.polygons.add(len(triangles))
    mesh.polygons.foreach_set("loop_start", np.arange(len(triangles), dtype=np.int32) * 3)
    mesh.polygons.foreach_set("loop_total", np.full(len(triangles), 3, dtype=np.int32))
    mesh.polygons.foreach_set("use_smooth", np.ones(len(triangles), dtype=np.bool_))
    mesh.update(calc_edges=True)
    mesh.validate()
    mesh.normals_split_custom_set_from_vertices(to_blender(shell.normals).tolist())

    material = bpy.data.materials.new(MATERIAL_NAME)
    material.use_backface_culling = False
    bsdf = material.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = ROCK_COLOUR
    bsdf.inputs["Roughness"].default_value = ROUGHNESS
    bsdf.inputs["Metallic"].default_value = METALLIC
    mesh.materials.append(material)

    bpy.context.scene.collection.objects.link(bpy.data.objects.new(OBJECT_NAME, mesh))


def export_tunnel(shell: ShellMesh, out: Path) -> Path:
    """Build ``shell`` in a fresh Blender state and write the GLB to ``out``."""
    bpy = importlib.import_module("bpy")
    build_scene(bpy, shell)
    export_glb(bpy, out)
    return out
