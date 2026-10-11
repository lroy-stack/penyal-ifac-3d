"""The asset spike must export a well-formed, byte-reproducible GLB (AC1)."""

import hashlib
import json
import os
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from penyal_pipeline.blender import spike

GLB_MAGIC = 0x46546C67  # "glTF"
JSON_CHUNK = 0x4E4F534A  # "JSON"


def read_glb_json(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<III", data, 0)
    assert magic == GLB_MAGIC
    assert version == 2
    assert length == len(data)
    chunk_length, chunk_type = struct.unpack_from("<II", data, 12)
    assert chunk_type == JSON_CHUNK
    return json.loads(data[20 : 20 + chunk_length])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp("spike")
    first = spike.run_spike(root / "first" / "spike.glb")
    second = root / "second" / "spike.glb"
    # A fresh interpreter with a pinned, different hash seed: set/dict ordering must not leak
    # into the export.
    env = {**os.environ, "PYTHONHASHSEED": "4242" if _current_seed() != "4242" else "17"}
    done = subprocess.run(
        [sys.executable, "-m", "penyal_pipeline.cli", "spike", "--out", str(second)],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return first, second


def _current_seed() -> str | None:
    return os.environ.get("PYTHONHASHSEED")


def test_height_function_is_deterministic_and_bounded() -> None:
    vertices = spike.grid_vertices()
    assert np.array_equal(vertices, spike.grid_vertices())
    assert vertices.shape == (129 * 129, 3)
    assert vertices[:, 0].min() == -128.0
    assert vertices[:, 0].max() == 128.0
    assert vertices[:, 1].min() == -128.0
    assert vertices[:, 1].max() == 128.0
    assert 0.0 < vertices[:, 2].max() < 41.0


def test_uvs_span_unit_square() -> None:
    uvs = spike.grid_uvs()
    assert uvs.min() == 0.0
    assert uvs.max() == 1.0


def test_quads_cover_grid() -> None:
    quads = spike.grid_quads()
    assert quads.shape == (128 * 128, 4)
    assert quads.max() == 129 * 129 - 1


def test_two_runs_are_byte_identical(runs: tuple[Path, Path]) -> None:
    first, second = runs
    assert sha256(first) == sha256(second)


def test_glb_structure(runs: tuple[Path, Path]) -> None:
    gltf = read_glb_json(runs[0])
    assert gltf["asset"]["generator"].startswith("Khronos glTF Blender I/O")
    assert len(gltf["meshes"]) == 1
    assert len(gltf["images"]) == 1
    assert gltf["images"][0]["mimeType"] == "image/png"
    assert len(gltf["materials"]) == 1
    assert "animations" not in gltf
    assert "cameras" not in gltf
    assert "KHR_lights_punctual" not in gltf.get("extensionsUsed", [])

    primitive = gltf["meshes"][0]["primitives"][0]
    position = gltf["accessors"][primitive["attributes"]["POSITION"]]
    # Smooth shading and continuous UVs mean the exporter does not split any vertex.
    assert position["count"] == 129 * 129
    assert primitive["attributes"].keys() >= {"POSITION", "NORMAL", "TEXCOORD_0"}
    assert gltf["accessors"][primitive["indices"]]["count"] == 128 * 128 * 2 * 3
    # Y-up: the 256 m footprint lies on X and Z, the relief on Y.
    assert position["max"][0] == 128.0
    assert position["max"][2] == 128.0
    assert 0.0 < position["max"][1] < 41.0
