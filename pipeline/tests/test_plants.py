"""The procedural understory plants: lentisc, rosemary and grass with LODs and far cards (E2.4)."""

import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any, ClassVar

import numpy as np
import pytest
from conftest import glb_attribute, raw_marks

from penyal_pipeline import foliage_tint, understory
from penyal_pipeline.blender import pine, plants
from penyal_pipeline.paths import REPO_ROOT

TEXTURES = (
    "polyhaven-shrub-04-diff-1k/*.jpg",
    "polyhaven-shrub-02-diff-1k/*.jpg",
    "polyhaven-grass-medium-02-diff-1k/*.jpg",
)
needs_optimizer = pytest.mark.skipif(
    shutil.which("node") is None
    or not (REPO_ROOT / "tools" / "bin" / "ktx").exists()
    or not (REPO_ROOT / "node_modules" / ".bin" / "gltf-transform").exists(),
    reason="node, tools/bin/ktx and `pnpm install` are needed to optimise GLBs",
)
EXPORT_SCRIPT = (
    "import sys\n"
    "from pathlib import Path\n"
    "from penyal_pipeline.blender import plants\n"
    "atlas = plants.build_atlas()\n"
    "plants.export_plants(plants.build_meshes(atlas), atlas, Path(sys.argv[1]))\n"
)


def read_glb_json(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<III", data, 0)
    assert (magic, version, length) == (0x46546C67, 2, len(data))
    chunk_length, _ = struct.unpack_from("<II", data, 12)
    return json.loads(data[20 : 20 + chunk_length])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_cli(args: list[str], seed: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "penyal_pipeline.cli", *args],
        env={**os.environ, "PYTHONHASHSEED": seed},
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


pytestmark = raw_marks(*TEXTURES)


@pytest.fixture(scope="module")
def atlas() -> plants.Atlas:
    return plants.build_atlas()


@pytest.fixture(scope="module")
def meshes(atlas: plants.Atlas) -> list[plants.PlantMesh]:
    return plants.build_meshes(atlas)


def test_every_model_has_a_near_a_mid_and_a_far_mesh(meshes: list[plants.PlantMesh]) -> None:
    names = [m.name for m in meshes]
    expected = [f"{model.id}_{level}" for model in understory.MODELS for level in plants.LEVELS]
    assert sorted(names) == sorted(expected)
    assert len(names) == 9


def test_the_triangle_budgets_hold(meshes: list[plants.PlantMesh]) -> None:
    by_name = {m.name: m for m in meshes}
    for model in understory.MODELS:
        lod0, lod1 = by_name[f"{model.id}_lod0"], by_name[f"{model.id}_lod1"]
        card = by_name[f"{model.id}_card"]
        assert 0 < lod1.triangle_count <= plants.LOD1_MAX_TRIANGLES
        assert lod1.triangle_count < lod0.triangle_count <= plants.LOD0_MAX_TRIANGLES
        assert card.triangle_count == 8  # two crossed planes of single-sided twin quads


def test_the_tall_shrub_is_a_real_lentisc_sized_model_not_a_stretched_small_one(
    meshes: list[plants.PlantMesh],
) -> None:
    lentisc = next(m for m in meshes if m.name == "lentisc_lod0")
    assert lentisc.positions[:, 1].max() == pytest.approx(2.0, abs=1e-3)
    assert lentisc.triangle_count >= 600  # a bush, not a handful of cards


def test_each_model_is_normalised_to_its_nominal_size(meshes: list[plants.PlantMesh]) -> None:
    for model in understory.MODELS:
        mesh = next(m for m in meshes if m.name == f"{model.id}_lod0")
        radial = np.hypot(mesh.positions[:, 0], mesh.positions[:, 2])
        assert mesh.positions[:, 1].max() == pytest.approx(model.height, abs=1e-3)
        assert np.percentile(radial, 90) == pytest.approx(model.radius, abs=1e-3)
        assert mesh.positions[:, 1].min() >= -1e-6  # stands on the ground


def test_meshes_are_valid_and_uvs_stay_in_the_atlas(meshes: list[plants.PlantMesh]) -> None:
    for mesh in meshes:
        assert mesh.triangles.min() >= 0
        assert mesh.triangles.max() == len(mesh.positions) - 1
        assert mesh.uvs.min() >= 0.0
        assert mesh.uvs.max() <= 1.0
        assert np.allclose(np.linalg.norm(mesh.normals, axis=1), 1.0, atol=1e-5)


def test_the_far_cards_are_single_sided_twins_shaded_on_their_own_side(
    meshes: list[plants.PlantMesh],
) -> None:
    # In-plane normals made the cards grazing-lit from the front and black from behind.
    for mesh in (m for m in meshes if m.name.endswith("_card")):
        p = mesh.positions.astype(np.float64)[mesh.triangles]
        face = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
        face /= np.linalg.norm(face, axis=1, keepdims=True)
        towards = np.einsum("tvk,tk->tv", mesh.normals[mesh.triangles], face)
        assert mesh.single_sided, mesh.name
        assert (towards > 0.3).all(), mesh.name
        assert mesh.normals[:, 1].min() > 0.3, mesh.name


def test_the_sprites_have_leaves_holes_and_no_black_background(atlas: plants.Atlas) -> None:
    for name, cell in atlas.cells.items():
        if name == "stem":
            continue  # a solid colour patch, checked below
        x0, y0, x1, y1 = cell
        sprite = atlas.rgba[y0:y1, x0:x1]
        opaque = sprite[..., 3] > 127
        assert 0.08 < opaque.mean() < 0.8, name
        colour = sprite[opaque][:, :3].astype(np.float64)
        assert colour.mean() > 50, name  # no black photograph background leaks in
        green = colour[:, 1].mean()
        assert green >= colour[:, 2].mean(), name


def test_the_stem_patch_is_one_opaque_colour(atlas: plants.Atlas) -> None:
    x0, y0, x1, y1 = atlas.cells["stem"]
    patch = atlas.rgba[y0:y1, x0:x1].reshape(-1, 4)
    assert (patch == patch[0]).all()
    assert patch[0, 3] == 255


def test_building_twice_gives_identical_meshes(
    atlas: plants.Atlas, meshes: list[plants.PlantMesh]
) -> None:
    for first, second in zip(meshes, plants.build_meshes(atlas), strict=True):
        assert first.name == second.name
        assert np.array_equal(first.positions, second.positions)
        assert np.array_equal(first.triangles, second.triangles)


def test_the_models_block_of_vegetation_json_describes_the_procedural_plants() -> None:
    described = [understory.model_description(m) for m in understory.MODELS]
    assert [m["id"] for m in described] == ["lentisc", "rosemary", "grass"]
    assert described[0]["nominalHeight"] == 2.0
    assert described[0]["meshes"] == {
        "lod0": "lentisc_lod0",
        "lod1": "lentisc_lod1",
        "card": "lentisc_card",
    }
    assert all(m["licence"] == "CC0 1.0" for m in described)
    assert understory.protected_species_in({"models": described}) == []


@pytest.fixture(scope="module")
def exports(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp("plants")
    atlas = plants.build_atlas()
    first = plants.export_plants(plants.build_meshes(atlas), atlas, root / "a" / "plants.glb")
    second = root / "b" / "plants.glb"
    seed = "4242" if os.environ.get("PYTHONHASHSEED") != "4242" else "17"
    done = subprocess.run(
        [sys.executable, "-c", EXPORT_SCRIPT, str(second)],
        env={**os.environ, "PYTHONHASHSEED": seed},
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return first, second


@pytest.mark.slow
class TestExport:
    def test_two_raw_exports_are_byte_identical(self, exports: tuple[Path, Path]) -> None:
        assert sha256(exports[0]) == sha256(exports[1])

    def test_the_glb_holds_every_mesh_and_masked_materials_sharing_one_atlas(
        self, exports: tuple[Path, Path]
    ) -> None:
        gltf = read_glb_json(exports[0])
        assert len(gltf["nodes"]) == 9
        names = sorted(m["name"] for m in gltf["materials"])
        card = pine.card_material_name(plants.MATERIAL_NAME)
        assert names == sorted([plants.MATERIAL_NAME, card])
        assert all(m["alphaMode"] == "MASK" for m in gltf["materials"])
        cards = [m for m in gltf["meshes"] if m["name"].endswith("_card")]
        assert {gltf["materials"][m["primitives"][0]["material"]]["name"] for m in cards} == {card}
        assert len(gltf["images"]) == 1
        assert gltf["samplers"][0]["wrapS"] == 33071
        assert all(len(m["primitives"]) == 1 for m in gltf["meshes"])

    def test_the_materials_have_no_specular_reflection(self, exports: tuple[Path, Path]) -> None:
        gltf = read_glb_json(exports[0])
        for material in gltf["materials"]:
            specular = material["extensions"]["KHR_materials_specular"]
            assert specular["specularFactor"] == 0.0, material["name"]

    def test_each_foliage_multiplier_reaches_color_0_unchanged(
        self, exports: tuple[Path, Path]
    ) -> None:
        # COLOR_0 is linear (glTF): decoding the factors as sRGB made the cards near black.
        for model in understory.MODELS:
            factor = np.array(foliage_tint.FOLIAGE_FACTORS[model.id])
            card = glb_attribute(exports[0], f"{model.id}_card", "COLOR_0")[:, :3]
            assert np.allclose(card, factor, atol=1 / 255), model.id


@needs_optimizer
@pytest.mark.slow
class TestOptimised:
    pytestmark: ClassVar = raw_marks(*TEXTURES)

    def test_the_optimised_files_are_byte_identical_across_runs_and_hash_seeds(
        self, tmp_path: Path
    ) -> None:
        for name, seed in (("first", "1"), ("second", "4242")):
            done = run_cli(
                [
                    "plants",
                    "--out-dir",
                    str(tmp_path / name),
                    "--build-dir",
                    str(tmp_path / f"{name}-b"),
                ],
                seed,
            )
            assert done.returncode == 0, done.stderr
        first = {p.name: sha256(p) for p in sorted((tmp_path / "first").iterdir())}
        second = {p.name: sha256(p) for p in sorted((tmp_path / "second").iterdir())}
        assert first == second
        assert sorted(first) == ["plants.glb", "plants.json"]

    def test_the_manifest_records_budgets_sources_and_notes(self, tmp_path: Path) -> None:
        done = run_cli(
            ["plants", "--out-dir", str(tmp_path), "--build-dir", str(tmp_path / "b")], "1"
        )
        assert done.returncode == 0, done.stderr
        document = json.loads((tmp_path / "plants.json").read_text(encoding="utf-8"))
        assert document["file"]["bytes"] == (tmp_path / "plants.glb").stat().st_size
        assert {i["id"] for i in document["inputs"]} == {
            "polyhaven-shrub-04-diff-1k",
            "polyhaven-shrub-02-diff-1k",
            "polyhaven-grass-medium-02-diff-1k",
        }
        assert "not measured" in document["shape"]
        assert document["notes"]
        assert document["budget"]["tiers"]["medium"]["understoryLodM"] == [8.0, 24.0, 60.0]
        assert document["budget"]["tiers"]["high"]["distanceM"] == 200.0
