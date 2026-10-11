"""Foliage colour: derived from the reference photographs, applied as a base-colour multiplier."""

import colorsys
import json
import struct
from pathlib import Path

import numpy as np
import pytest
from conftest import raw_marks

from penyal_pipeline import foliage_tint, understory
from penyal_pipeline.blender import pine, plants
from penyal_pipeline.paths import DATA_DIR

TEXTURES = (
    "polyhaven-pine-tree-01-twig-diff-1k/*.jpg",
    "polyhaven-pine-tree-01-twig-alpha-1k/*.jpg",
    "polyhaven-pine-tree-01-bark-diff-1k/*.jpg",
    "polyhaven-shrub-04-diff-1k/*.jpg",
    "polyhaven-shrub-02-diff-1k/*.jpg",
    "polyhaven-grass-medium-02-diff-1k/*.jpg",
)
PHOTOS_PRESENT = all(
    (DATA_DIR / "manual" / "fotos-referencia" / "commons" / name).is_file()
    for name in foliage_tint.PHOTO_FILES.values()
)


def test_srgb_and_linear_round_trip() -> None:
    values = np.array([0.0, 0.02, 0.2, 0.5, 1.0])
    assert foliage_tint.linear_to_srgb(foliage_tint.srgb_to_linear(values)) == pytest.approx(values)
    assert foliage_tint.srgb_to_linear(np.array([0.5]))[0] == pytest.approx(0.2140, abs=1e-3)


def test_the_target_is_the_median_of_the_brighter_half_of_the_pixels() -> None:
    shade = np.tile([0.05, 0.05, 0.05], (50, 1))
    sun = np.tile([0.5, 0.6, 0.2], (50, 1))
    target = foliage_tint.sunlit_median(np.concatenate([shade, sun]))
    assert target == pytest.approx([0.5, 0.6, 0.2])


def test_a_multiplier_that_would_brighten_is_scaled_to_keep_hue_and_saturation() -> None:
    source = np.array([0.1, 0.1, 0.1])
    brighter = foliage_tint.factor_for(np.array([0.4, 0.2, 0.1]), source)  # raw 4 / 2 / 1
    assert brighter.max() == pytest.approx(1.0)
    assert brighter == pytest.approx([1.0, 0.5, 0.25])
    darker = foliage_tint.factor_for(np.array([0.05, 0.04, 0.02]), source)  # raw 0.5 / 0.4 / 0.2
    assert darker == pytest.approx([0.5, 0.4, 0.2])


def test_the_constants_are_valid_multipliers_for_every_foliage() -> None:
    assert set(foliage_tint.FOLIAGE_FACTORS) == {"pine", "lentisc", "rosemary", "grass"}
    for factor in foliage_tint.FOLIAGE_FACTORS.values():
        assert len(factor) == 3
        assert all(0.0 < c <= 1.0 for c in factor)


def test_every_region_lies_inside_its_photograph() -> None:
    sizes = {"26": (1920, 1440), "17": (1920, 1440)}
    for name, boxes in foliage_tint.REGIONS.items():
        for photo, x0, y0, x1, y1 in boxes:
            width, height = sizes[photo]
            assert 0 <= x0 < x1 <= width, name
            assert 0 <= y0 < y1 <= height, name


@pytest.mark.skipif(not PHOTOS_PRESENT, reason="data/manual/fotos-referencia is not present")
class TestFromThePhotos:
    pytestmark = raw_marks(*TEXTURES)

    def test_the_constants_are_what_the_photos_and_the_textures_give(self) -> None:
        pine_atlas, plant_atlas = pine.build_atlas(), plants.build_atlas()
        sources = {
            "pine": pine.needle_linear_mean(pine_atlas),
            "lentisc": plants.sprite_linear_mean(plant_atlas, "lentisc"),
            "rosemary": plants.sprite_linear_mean(plant_atlas, "rosemary"),
            "grass": plants.sprite_linear_mean(plant_atlas, "grass"),
        }
        derived = foliage_tint.derive(DATA_DIR / "manual" / "fotos-referencia" / "commons", sources)
        for name, factor in foliage_tint.FOLIAGE_FACTORS.items():
            assert derived[name] == pytest.approx(factor, abs=0.01), name

    def test_the_needle_texture_is_left_as_photographed_olive_not_baked_green(self) -> None:
        atlas = pine.build_atlas()
        x0, y0, x1, y1 = atlas.twig_a
        needle = atlas.rgba[y0:y1, x0:x1].reshape(-1, 4)
        needle = needle[needle[:, 3] > 200][:, :3].astype(np.float64) / 255.0
        hue = colorsys.rgb_to_hsv(*needle.mean(axis=0))[0] * 360.0
        assert 45.0 <= hue <= 75.0  # the textured twig's own olive; the green is the multiplier's


@pytest.mark.slow
class TestMeshesCarryTheMultiplier:
    pytestmark = raw_marks(*TEXTURES)

    def test_needle_cards_carry_the_pine_factor_and_bark_stays_white(self) -> None:
        atlas = pine.build_atlas()
        mesh = next(m for m in pine.build_meshes(atlas) if m.name == "pine_v0_lod0")
        assert mesh.colours is not None
        needles = mesh.uvs[:, 0] > 0.5
        factor = np.array(foliage_tint.FOLIAGE_FACTORS["pine"], dtype=np.float32)
        assert np.allclose(mesh.colours[needles], factor)
        assert np.allclose(mesh.colours[~needles], 1.0)

    def test_each_plant_carries_its_own_factor(self) -> None:
        atlas = plants.build_atlas()
        for model in understory.MODELS:
            mesh = next(m for m in plants.build_meshes(atlas) if m.name == f"{model.id}_lod0")
            assert mesh.colours is not None
            factor = np.array(foliage_tint.FOLIAGE_FACTORS[model.id], dtype=np.float32)
            leaves = mesh.uvs[:, 1] < plants.STEM_V_MIN  # the stem patch sits at the atlas foot
            assert np.allclose(mesh.colours[leaves], factor), model.id

    def test_the_exported_glb_has_vertex_colours_and_a_multiplied_material(
        self, tmp_path: Path
    ) -> None:
        atlas = pine.build_atlas()
        out = pine.export_pine(pine.build_meshes(atlas), atlas, tmp_path / "pine.glb")
        data = out.read_bytes()
        length = struct.unpack_from("<I", data, 12)[0]
        gltf = json.loads(data[20 : 20 + length])
        primitive = gltf["meshes"][0]["primitives"][0]
        assert "COLOR_0" in primitive["attributes"]
