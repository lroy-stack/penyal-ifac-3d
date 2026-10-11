"""The procedural Aleppo pine: geometry budgets, atlas, and a byte-reproducible GLB (E2.3)."""

import hashlib
import itertools
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
from conftest import raw_marks

from penyal_pipeline.blender import pine
from penyal_pipeline.paths import REPO_ROOT

TEXTURES = (
    "polyhaven-pine-tree-01-twig-diff-1k/*.jpg",
    "polyhaven-pine-tree-01-twig-alpha-1k/*.jpg",
    "polyhaven-pine-tree-01-bark-diff-1k/*.jpg",
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
    "from penyal_pipeline.blender import pine\n"
    "atlas = pine.build_atlas()\n"
    "pine.export_pine(pine.build_meshes(atlas), atlas, Path(sys.argv[1]))\n"
)
GLB_MAGIC = 0x46546C67
JSON_CHUNK = 0x4E4F534A


def read_glb_json(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<III", data, 0)
    assert (magic, version, length) == (GLB_MAGIC, 2, len(data))
    chunk_length, chunk_type = struct.unpack_from("<II", data, 12)
    assert chunk_type == JSON_CHUNK
    return json.loads(data[20 : 20 + chunk_length])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): sha256(p) for p in sorted(root.rglob("*")) if p.is_file()}


def run_cli(args: list[str], seed: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONHASHSEED": seed}
    return subprocess.run(
        [sys.executable, "-m", "penyal_pipeline.cli", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


# --- pure geometry (no data, no Blender) --------------------------------------------------------


def test_resize_keeps_a_constant_image_constant() -> None:
    image = np.full((10, 7, 4), 0.25, dtype=np.float32)
    out = pine.resize(image, 23, 31)
    assert out.shape == (23, 31, 4)
    assert np.allclose(out, 0.25)


def test_a_skeleton_is_reproducible_and_variants_differ() -> None:
    first, again = pine.skeleton(0), pine.skeleton(0)
    assert len(first.tubes) == len(again.tubes)
    assert all(
        np.array_equal(a.points, b.points) for a, b in zip(first.tubes, again.tubes, strict=True)
    )
    other = pine.skeleton(1)
    assert not np.array_equal(first.tubes[0].points, other.tubes[0].points)


def test_the_trunk_ends_above_its_foot_and_tapers() -> None:
    for variant in range(pine.VARIANT_COUNT):
        trunk = pine.skeleton(variant).tubes[0]
        assert np.hypot(*trunk.points[-1][[0, 2]]) < 1e-9
        assert np.hypot(*trunk.points[0][[0, 2]]) < 1e-9
        assert trunk.radii[0] > trunk.radii[-1]


def test_tube_normals_point_away_from_the_axis_and_triangles_are_valid() -> None:
    tube = pine.skeleton(0).tubes[0]
    positions, normals, uvs, triangles = pine.tube_mesh(
        tube, 6, (0.0, 0.0, 0.5, 1.0), np.ones(len(tube.radii))
    )
    assert triangles.max() == len(positions) - 1
    assert np.allclose(np.linalg.norm(normals, axis=1), 1.0)
    segments = np.stack([tube.points[:-1], tube.points[1:]], axis=1).reshape(-1, 3)
    centres = np.repeat(segments, 7, axis=0)  # every segment owns its two rings (bark UVs)
    assert len(positions) == len(centres)
    assert (np.einsum("ij,ij->i", positions - centres, normals) > 0).all()
    assert uvs[:, 0].min() >= 0.0
    assert uvs[:, 0].max() <= 0.5


def test_bark_texels_are_square_on_every_segment() -> None:
    """A trunk segment maps the cell once around and ``length / circumference`` along."""
    tube = pine.skeleton(0).tubes[0]
    sides = 8
    positions, _, uvs, _ = pine.tube_mesh(
        tube, sides, (0.0, 0.0, 0.5, 1.0), np.ones(len(tube.radii))
    )
    per_segment = 2 * (sides + 1)
    for segment in range(len(tube.points) - 1):
        start = segment * per_segment
        bottom = positions[start : start + sides + 1]
        circumference = float(np.linalg.norm(np.diff(bottom, axis=0), axis=1).sum())
        length = float(np.linalg.norm(tube.points[segment + 1] - tube.points[segment]))
        v = uvs[start : start + per_segment, 1]
        du = 0.5  # the whole cell width is one circumference
        expected = min(length / circumference * du, 1.0)
        assert float(v.max() - v.min()) == pytest.approx(expected, rel=0.15, abs=0.02)
        assert v.min() >= 0.0
        assert v.max() <= 1.0


def test_the_triangle_winding_faces_outwards() -> None:
    tube = pine.skeleton(0).tubes[0]
    positions, normals, _, triangles = pine.tube_mesh(
        tube, 6, (0.0, 0.0, 0.5, 1.0), np.ones(len(tube.radii))
    )
    a, b, c = (positions[triangles[:, i]] for i in range(3))
    face = np.cross(b - a, c - a)
    vertex_normals = normals[triangles].sum(axis=1)
    assert (np.einsum("ij,ij->i", face, vertex_normals) > 0).all()


def test_a_card_is_two_triangles_and_cards_cross_around_the_growth_direction() -> None:
    tuft = pine.Tuft(np.zeros(3), np.array([0.0, 1.0, 0.0]), 1.0, sideways=False)
    rects = ((0.5, 0.0, 0.75, 1.0), (0.75, 0.0, 1.0, 0.5))
    positions, normals, uvs, triangles = pine.card_mesh(tuft, 3, 1.0, rects, np.zeros(3), 0.0)
    assert positions.shape == (12, 3)
    assert len(triangles) == 6
    assert np.allclose(np.linalg.norm(normals, axis=1), 1.0)
    assert uvs[:, 0].min() == 0.5
    assert uvs[:, 0].max() == 0.75
    stems = positions[::4], positions[1::4]
    assert np.allclose(stems[0][:, 1], 0.0)
    assert np.allclose(stems[1][:, 1], 0.0)
    assert positions[2::4][:, 1].min() > 1.0


def test_the_far_card_is_shaded_like_the_crown_not_flat_up() -> None:
    card = pine.far_card()
    assert np.allclose(np.linalg.norm(card.normals, axis=1), 1.0, atol=1e-5)
    assert card.normals[:, 1].min() > 0.3  # lit from above...
    assert abs(card.normals[:, 0]).max() > 0.3  # ...and turned outwards at the sides


def test_the_far_card_is_two_crossed_quads_of_four_triangles() -> None:
    card = pine.far_card()
    assert card.name == pine.CARD_NAME
    assert card.triangle_count == 4
    assert card.positions[:, 1].max() == pine.NOMINAL_HEIGHT
    assert card.positions[:, 1].min() == 0.0


@pytest.fixture(scope="module")
def atlas() -> pine.Atlas:
    return pine.build_atlas()


@pytest.fixture(scope="module")
def meshes(atlas: pine.Atlas) -> list[pine.PineMesh]:
    return pine.build_meshes(atlas)


class TestWithTextures:
    pytestmark: ClassVar = raw_marks(*TEXTURES)

    def test_the_atlas_has_opaque_bark_twigs_with_holes_and_no_black_under_alpha(
        self, atlas: pine.Atlas
    ) -> None:
        rgba = atlas.rgba
        assert rgba.shape == (pine.ATLAS_HEIGHT, pine.ATLAS_WIDTH, 4)
        bx0, by0, bx1, by1 = pine.BARK_CELL
        assert (rgba[by0:by1, bx0:bx1, 3] == 255).all()
        for rect in (atlas.twig_a, atlas.twig_b):
            x0, y0, x1, y1 = rect
            alpha = rgba[y0:y1, x0:x1, 3]
            assert 0.15 < (alpha > 127).mean() < 0.6
        transparent = rgba[rgba[..., 3] == 0]
        assert transparent[:, :3].mean(axis=0).min() > 40

    def test_the_needles_are_a_bright_green_and_the_bark_a_grey(self, atlas: pine.Atlas) -> None:
        x0, y0, x1, y1 = atlas.twig_a
        needle = atlas.rgba[y0:y1, x0:x1].reshape(-1, 4)
        needle = needle[needle[:, 3] > 200][:, :3].astype(np.float64)
        red, green, blue = needle.mean(axis=0)
        assert green > red * 1.15  # green, not olive
        assert green > blue * 1.6
        bx0, by0, bx1, by1 = pine.BARK_CELL
        bark = atlas.rgba[by0:by1, bx0:bx1, :3].reshape(-1, 3).astype(np.float64)
        assert (bark.max(axis=1) - bark.min(axis=1)).mean() < 22  # nearly neutral
        assert bark.mean() > 70  # and not the near-black of the raw photograph

    def test_the_crown_starts_at_half_the_height_and_the_foliage_sits_high(
        self, atlas: pine.Atlas, meshes: list[pine.PineMesh]
    ) -> None:
        for variant in range(pine.VARIANT_COUNT):
            skeleton = pine.skeleton(variant)
            starts = [tube.points[0][1] for tube in skeleton.tubes if tube.main and not tube.trunk]
            lowest = min(starts) * pine.variant_scale(variant, atlas)[1]
            assert 0.45 * pine.NOMINAL_HEIGHT <= lowest <= 0.62 * pine.NOMINAL_HEIGHT
            mesh = next(m for m in meshes if m.name == f"pine_v{variant}_lod0")
            foliage = mesh.positions[mesh.uvs[:, 0] > 0.5]  # twig cards, not bark
            assert (foliage[:, 1] > 0.5 * pine.NOMINAL_HEIGHT).mean() > 0.9

    def test_the_foliage_is_denser_than_a_sparse_tree_but_inside_the_budget(
        self, meshes: list[pine.PineMesh]
    ) -> None:
        for mesh in meshes:
            if mesh.name.endswith("lod0"):
                assert 4000 <= mesh.triangle_count <= pine.LOD0_MAX_TRIANGLES

    def test_the_alpha_coverage_per_mip_level_is_recorded_and_not_zero(
        self, atlas: pine.Atlas
    ) -> None:
        coverage = pine.alpha_coverage_by_level(atlas, levels=5)
        assert len(coverage) == 5
        assert coverage[0] > 0.15
        assert all(b <= a * 1.05 for a, b in itertools.pairwise(coverage))
        assert coverage[-1] > 0.02  # the needles do not vanish at the smallest mip

    def test_the_far_silhouette_has_a_crown_and_a_trunk(self, atlas: pine.Atlas) -> None:
        x0, y0, x1, y1 = pine.FAR_CELL
        alpha = atlas.rgba[y0:y1, x0:x1, 3] > 127
        height = y1 - y0
        assert alpha[: height // 2].mean() > 0.3
        assert 0.0 < alpha[height * 3 // 4 :].mean() < 0.1

    def test_every_variant_fits_the_budget_and_the_nominal_size(
        self, meshes: list[pine.PineMesh]
    ) -> None:
        by_name = {m.name: m for m in meshes}
        assert len(meshes) == 2 * pine.VARIANT_COUNT + 1
        for variant in range(pine.VARIANT_COUNT):
            lod0, lod1 = by_name[f"pine_v{variant}_lod0"], by_name[f"pine_v{variant}_lod1"]
            assert 0 < lod1.triangle_count <= pine.LOD1_MAX_TRIANGLES
            assert lod1.triangle_count < lod0.triangle_count <= pine.LOD0_MAX_TRIANGLES
            radial = np.hypot(lod0.positions[:, 0], lod0.positions[:, 2])
            assert lod0.positions[:, 1].max() == pytest.approx(pine.NOMINAL_HEIGHT, abs=1e-3)
            assert np.percentile(radial, 90) == pytest.approx(pine.NOMINAL_RADIUS, abs=1e-3)

    def test_meshes_are_valid_and_uvs_stay_in_the_atlas(self, meshes: list[pine.PineMesh]) -> None:
        for mesh in meshes:
            assert mesh.triangles.min() >= 0
            assert mesh.triangles.max() == len(mesh.positions) - 1
            assert mesh.uvs.min() >= 0.0
            assert mesh.uvs.max() <= 1.0
            assert np.allclose(np.linalg.norm(mesh.normals, axis=1), 1.0, atol=1e-5)

    def test_building_twice_gives_identical_meshes(
        self, atlas: pine.Atlas, meshes: list[pine.PineMesh]
    ) -> None:
        for first, second in zip(meshes, pine.build_meshes(atlas), strict=True):
            assert first.name == second.name
            assert np.array_equal(first.positions, second.positions)
            assert np.array_equal(first.uvs, second.uvs)
            assert np.array_equal(first.triangles, second.triangles)


# --- the GLB ------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def exports(
    tmp_path_factory: pytest.TempPathFactory,
    atlas: pine.Atlas,
    meshes: list[pine.PineMesh],
) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp("pine")
    first = pine.export_pine(meshes, atlas, root / "first" / "pine.glb")
    second = root / "second" / "pine.glb"
    # a fresh interpreter with a different hash seed: set/dict ordering must not leak in
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
    pytestmark: ClassVar = raw_marks(*TEXTURES)

    def test_two_raw_exports_are_byte_identical(self, exports: tuple[Path, Path]) -> None:
        first, second = exports
        assert sha256(first) == sha256(second)

    def test_the_glb_holds_every_mesh_one_masked_material_and_one_atlas(
        self, exports: tuple[Path, Path]
    ) -> None:
        gltf = read_glb_json(exports[0])
        names = sorted(n["name"] for n in gltf["nodes"])
        expected = sorted(
            [pine.CARD_NAME]
            + [f"pine_v{v}_lod{lod}" for v in range(pine.VARIANT_COUNT) for lod in (0, 1)]
        )
        assert names == expected
        assert len(gltf["materials"]) == 1
        material = gltf["materials"][0]
        assert material["alphaMode"] == "MASK"
        assert material["doubleSided"] is True
        assert len(gltf["images"]) == 1
        assert all(len(m["primitives"]) == 1 for m in gltf["meshes"])
        assert gltf["samplers"][0]["wrapS"] == 33071  # CLAMP_TO_EDGE: no bleeding between cells
        assert gltf["samplers"][0]["wrapT"] == 33071
        assert "animations" not in gltf


@needs_optimizer
@pytest.mark.slow
class TestOptimisedDeterminism:
    pytestmark: ClassVar = raw_marks(*TEXTURES)

    def test_the_optimised_glb_and_manifest_are_byte_identical_across_runs_and_hash_seeds(
        self, tmp_path: Path
    ) -> None:
        for name, seed in (("first", "1"), ("second", "4242")):
            done = run_cli(
                [
                    "pine",
                    "--out-dir",
                    str(tmp_path / name),
                    "--build-dir",
                    str(tmp_path / f"{name}-build"),
                ],
                seed,
            )
            assert done.returncode == 0, done.stderr
        assert hashes(tmp_path / "first") == hashes(tmp_path / "second")
        assert sorted(hashes(tmp_path / "first")) == ["pine.glb", "pine.json"]
        assert hashes(tmp_path / "first-build") == hashes(tmp_path / "second-build")

    def test_the_manifest_records_the_budget_the_sources_and_the_tools(
        self, tmp_path: Path
    ) -> None:
        done = run_cli(
            ["pine", "--out-dir", str(tmp_path), "--build-dir", str(tmp_path / "build")], "1"
        )
        assert done.returncode == 0, done.stderr
        document = json.loads((tmp_path / "pine.json").read_text(encoding="utf-8"))
        assert document["file"]["bytes"] == (tmp_path / "pine.glb").stat().st_size
        by_name = {m["name"]: m["triangles"] for m in document["meshes"]}
        assert max(t for n, t in by_name.items() if n.endswith("lod0")) <= pine.LOD0_MAX_TRIANGLES
        assert max(t for n, t in by_name.items() if n.endswith("lod1")) <= pine.LOD1_MAX_TRIANGLES
        assert {i["id"] for i in document["inputs"]} == {
            "polyhaven-pine-tree-01-twig-diff-1k",
            "polyhaven-pine-tree-01-twig-alpha-1k",
            "polyhaven-pine-tree-01-bark-diff-1k",
        }
        assert {"bpy", "ktx", "gltf-transform"} <= set(document["tools"])
        assert "not measured" in document["shape"]
        assert document["budget"]["tiers"]["medium"]["treeLodM"] == [30.0, 70.0, 120.0]
        assert document["budget"]["tiers"]["low"]["density"] == 0.35
