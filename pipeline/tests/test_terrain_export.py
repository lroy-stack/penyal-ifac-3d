"""The Blender export keeps local-frame metres, winding, normals, UVs and the texture intact."""

import json
import struct
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import pytest
from rasterio.io import MemoryFile

from penyal_pipeline import tiles
from penyal_pipeline.blender import terrain
from penyal_pipeline.dem import Grid

pytestmark = [
    pytest.mark.slow,
    pytest.mark.filterwarnings("ignore:Dataset has no geotransform"),
]

COMPONENT_DTYPES = {5126: np.float32, 5123: np.uint16, 5125: np.uint32}
COMPONENTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}
RED = (255, 0, 0)
BLUE = (0, 0, 255)


def read_glb(path: Path) -> tuple[dict[str, Any], bytes]:
    data = path.read_bytes()
    json_length, _ = struct.unpack_from("<II", data, 12)
    gltf = json.loads(data[20 : 20 + json_length])
    return gltf, data[20 + json_length + 8 :]


def accessor(gltf: dict[str, Any], blob: bytes, index: int) -> npt.NDArray[Any]:
    description = gltf["accessors"][index]
    view = gltf["bufferViews"][description["bufferView"]]
    dtype = COMPONENT_DTYPES[description["componentType"]]
    count = description["count"] * COMPONENTS[description["type"]]
    start = view.get("byteOffset", 0) + description.get("byteOffset", 0)
    values = np.frombuffer(blob, dtype=dtype, count=count, offset=start)
    return values.reshape(description["count"], COMPONENTS[description["type"]]).squeeze()


def decode_png(gltf: dict[str, Any], blob: bytes) -> npt.NDArray[np.uint8]:
    image = gltf["images"][0]
    assert image["mimeType"] == "image/png"
    view = gltf["bufferViews"][image["bufferView"]]
    start = view.get("byteOffset", 0)
    with MemoryFile(blob[start : start + view["byteLength"]]) as memory, memory.open() as src:
        return src.read().transpose(1, 2, 0)[:, :, :3]


def texel(rgb: npt.NDArray[np.uint8], uv: npt.NDArray[np.float32]) -> list[int]:
    height, width, _ = rgb.shape
    return rgb[min(int(uv[1] * height), height - 1), min(int(uv[0] * width), width - 1)].tolist()


@pytest.fixture(scope="module")
def exported(tmp_path_factory: pytest.TempPathFactory) -> tuple[tiles.TerrainMesh, Path, Any]:
    xs = -599.5 + np.arange(2600, dtype=np.float64)
    zs = -1999.5 + np.arange(2550, dtype=np.float64)
    heights = (
        60.0 * np.exp(-((xs[None, :] - 400.0) ** 2 + (zs[:, None] + 700.0) ** 2) / 20000.0)
    ).astype(np.float32)
    mesh = tiles.build_tile(Grid(heights, x0=-599.5, z0=-1999.5), 1, -3, tiles.LODS[2])
    rng = np.random.default_rng(3)
    rgb = rng.integers(0, 256, (128, 128, 3), dtype=np.uint8)
    rgb[:8, -8:] = RED  # top row = north, right columns = east
    rgb[-8:, :8] = BLUE
    out = tmp_path_factory.mktemp("export") / "tile.glb"
    terrain.export_terrain(
        terrain.TerrainExport(
            name="t_1_-3_lod2",
            positions=mesh.positions,
            normals=mesh.normals,
            uvs=mesh.uvs,
            triangles=mesh.triangles,
            rgb=rgb,
        ),
        out,
    )
    return mesh, out, rgb


def test_vertices_stay_in_local_frame_metres_without_node_offsets(
    exported: tuple[tiles.TerrainMesh, Path, Any],
) -> None:
    mesh, out, _ = exported
    gltf, blob = read_glb(out)
    assert [node.get("translation") for node in gltf["nodes"]] == [None]
    assert "rotation" not in gltf["nodes"][0]
    assert "scale" not in gltf["nodes"][0]
    primitive = gltf["meshes"][0]["primitives"][0]
    positions = accessor(gltf, blob, primitive["attributes"]["POSITION"])
    assert positions.shape == mesh.positions.shape
    assert np.allclose(positions, mesh.positions, atol=1e-4)
    assert positions[:, 0].min() == pytest.approx(255.5)
    assert positions[:, 2].max() == pytest.approx(-3 * 256 - 0.5 + 256)


def test_triangles_keep_their_ccw_winding_seen_from_above(
    exported: tuple[tiles.TerrainMesh, Path, Any],
) -> None:
    mesh, out, _ = exported
    gltf, blob = read_glb(out)
    primitive = gltf["meshes"][0]["primitives"][0]
    positions = accessor(gltf, blob, primitive["attributes"]["POSITION"]).astype(np.float64)
    triangles = accessor(gltf, blob, primitive["indices"]).reshape(-1, 3)
    assert triangles.shape == mesh.triangles.shape
    assert np.array_equal(triangles, mesh.triangles)
    u = positions[triangles[:, 1]] - positions[triangles[:, 0]]
    v = positions[triangles[:, 2]] - positions[triangles[:, 0]]
    surface = slice(0, mesh.surface_triangles)
    assert ((u[:, 2] * v[:, 0] - u[:, 0] * v[:, 2])[surface] > 0).all()


def test_dem_normals_survive_the_export(exported: tuple[tiles.TerrainMesh, Path, Any]) -> None:
    mesh, out, _ = exported
    gltf, blob = read_glb(out)
    normals = accessor(gltf, blob, gltf["meshes"][0]["primitives"][0]["attributes"]["NORMAL"])
    # Blender encodes custom normals relative to each loop's normal space (16 bit): typically
    # 1e-4 off, up to ~4e-3 (0.2 degrees) on a handful of steep vertices.
    error = np.abs(normals - mesh.normals).max(axis=1)
    assert np.median(error) < 5e-4
    assert error.max() < 1e-2
    assert normals[: mesh.surface_vertices, 1].min() > 0.0


def test_uvs_and_texture_round_trip_with_north_at_the_top(
    exported: tuple[tiles.TerrainMesh, Path, Any],
) -> None:
    mesh, out, rgb = exported
    gltf, blob = read_glb(out)
    uvs = accessor(gltf, blob, gltf["meshes"][0]["primitives"][0]["attributes"]["TEXCOORD_0"])
    assert np.allclose(uvs, mesh.uvs, atol=1e-6)
    decoded = decode_png(gltf, blob)
    assert np.array_equal(decoded, rgb), "the texture is stored losslessly, top row = north"
    surface = mesh.positions[: mesh.surface_vertices]
    north_east = int(np.argmax(surface[:, 0] - surface[:, 2]))
    south_west = int(np.argmin(surface[:, 0] - surface[:, 2]))
    assert texel(decoded, uvs[north_east]) == list(RED)
    assert texel(decoded, uvs[south_west]) == list(BLUE)


def test_material_is_rough_non_metallic_clamped_and_single_sided(
    exported: tuple[tiles.TerrainMesh, Path, Any],
) -> None:
    _, out, _ = exported
    gltf, _ = read_glb(out)
    (material,) = gltf["materials"]
    assert material["pbrMetallicRoughness"]["roughnessFactor"] == pytest.approx(0.9)
    assert material["pbrMetallicRoughness"]["metallicFactor"] == 0
    assert not material.get("doubleSided", False)
    (sampler,) = gltf["samplers"]
    assert sampler["wrapS"] == sampler["wrapT"] == 33071
    assert "extensionsUsed" not in gltf
    assert "animations" not in gltf
