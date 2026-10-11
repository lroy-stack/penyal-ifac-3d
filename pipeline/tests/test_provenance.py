"""Provenance blocks (inputs + tool versions) and the staleness check."""

import hashlib
import importlib.metadata
import json
import stat
from pathlib import Path

import pytest

from penyal_pipeline import artefacts, provenance
from penyal_pipeline.cli import main
from penyal_pipeline.provenance import ProvenanceError

TOML_TEXT = 'status = "approximate"\n'
RAW_FILES = {
    "icv-mdt-2016-0848": "mdt.tif",
    "icv-cv05-penyal": "HidrografiaBCV05.geojson",
    "osm-penyal": "osm-penyal.json",
    "icv-orto-2024-0848-7-2": "ortho.tif",
    "polyhaven-marble-cliff-05-diff-1k": "marble_cliff_05_diff_1k.jpg",
}
ALL_JSON = {
    "terrain/manifest.json",
    "terrain/collision.json",
    "tunnel.json",
    "trail.json",
    "materials/manifest.json",
    "surfaces/manifest.json",
    "structures.json",
}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def write_script(path: Path, output: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\necho '{output}'\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def write_lock(root: Path, shas: dict[str, str]) -> None:
    sources = {
        source_id: {"files": [{"name": name, "bytes": 1, "sha256": shas[source_id]}]}
        for source_id, name in RAW_FILES.items()
    }
    (root / "data").mkdir(parents=True, exist_ok=True)
    (root / "data" / "manifest.lock.json").write_text(
        json.dumps({"version": 1, "sources": sources}), encoding="utf-8"
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A miniature repository: raw files, lock, curated toml and fake external tools."""
    root = tmp_path / "repo"
    for source_id, name in RAW_FILES.items():
        raw = root / "data" / "raw" / source_id / name
        raw.parent.mkdir(parents=True)
        raw.write_text(source_id, encoding="utf-8")
    write_lock(root, {source_id: sha(source_id) for source_id in RAW_FILES})
    curated = root / "data" / "curated" / "tunnel.toml"
    curated.parent.mkdir(parents=True)
    curated.write_text(TOML_TEXT, encoding="utf-8")
    write_script(root / "tools" / "bin" / "ktx", "ktx version: v9.8.7")
    write_script(root / "node_modules" / ".bin" / "gltf-transform", "1.2.3")
    return root


def materials_manifest(root: Path) -> dict[str, object]:
    """What scripts/make-material-textures.mjs records for one texture."""
    entry = {
        "id": "polyhaven-marble-cliff-05-diff-1k",
        "file": "data/raw/polyhaven-marble-cliff-05-diff-1k/marble_cliff_05_diff_1k.jpg",
        "sha256": sha("polyhaven-marble-cliff-05-diff-1k"),
    }
    return {"version": 1, "inputs": [entry], "tools": {"ktx": "9.8.7"}, "files": []}


@pytest.fixture
def assets(repo: Path, tmp_path: Path) -> Path:
    """Generated artefacts written with the provenance the producers record."""
    out = tmp_path / "generated"
    for name, kind in (
        ("terrain/manifest.json", "terrain"),
        ("terrain/collision.json", "collision"),
        ("tunnel.json", "tunnel"),
        ("trail.json", "trail"),
        ("surfaces/manifest.json", "surfaces"),
        ("structures.json", "structures"),
    ):
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"version": 1, **artefacts.provenance(kind, repo)}), "utf-8")
    materials = out / "materials" / "manifest.json"
    materials.parent.mkdir()
    materials.write_text(json.dumps(materials_manifest(repo)), encoding="utf-8")
    return out


def flagged(problems: list[provenance.Problem]) -> set[str]:
    return {problem.artefact for problem in problems}


class TestHashing:
    def test_sha256_file(self, tmp_path: Path) -> None:
        path = tmp_path / "a.bin"
        path.write_bytes(b"abc")
        assert provenance.sha256_file(path) == hashlib.sha256(b"abc").hexdigest()


class TestInputs:
    def test_a_raw_input_carries_id_repo_relative_file_and_the_locked_sha(self, repo: Path) -> None:
        entry = artefacts.raw_input("osm-penyal", "osm-penyal.json", repo)
        assert entry == {
            "id": "osm-penyal",
            "file": "data/raw/osm-penyal/osm-penyal.json",
            "sha256": sha("osm-penyal"),
        }

    def test_the_curated_file_is_hashed_from_disk(self, repo: Path) -> None:
        assert artefacts.curated_input(repo) == {
            "file": "data/curated/tunnel.toml",
            "sha256": sha(TOML_TEXT),
        }

    @pytest.mark.parametrize(
        ("kind", "ids", "curated"),
        [
            (
                "terrain",
                {"icv-mdt-2016-0848", "icv-cv05-penyal", "osm-penyal", "icv-orto-2024-0848-7-2"},
                True,
            ),
            ("collision", {"icv-mdt-2016-0848", "icv-cv05-penyal", "osm-penyal"}, True),
            ("trail", {"icv-mdt-2016-0848", "icv-cv05-penyal", "osm-penyal"}, True),
            ("tunnel", {"icv-mdt-2016-0848", "icv-cv05-penyal", "osm-penyal"}, True),
            ("surfaces", {"osm-penyal"}, False),
            ("structures", {"icv-mdt-2016-0848", "icv-cv05-penyal", "osm-penyal"}, True),
        ],
    )
    def test_each_artefact_lists_every_input_that_changes_it(
        self, repo: Path, kind: str, ids: set[str], curated: bool
    ) -> None:
        block = artefacts.provenance(kind, repo)
        listed = block["inputs"]
        assert {i["id"] for i in listed if "id" in i} == ids
        assert any(i["file"] == "data/curated/tunnel.toml" for i in listed) is curated

    def test_the_tunnel_shell_is_clipped_against_the_carved_dem_so_a_dem_change_makes_it_stale(
        self, repo: Path, assets: Path
    ) -> None:
        shas = {source_id: sha(source_id) for source_id in RAW_FILES}
        shas["icv-mdt-2016-0848"] = sha("new mdt")
        write_lock(repo, shas)
        assert "tunnel.json" in flagged(provenance.verify_generated(assets, repo))

    def test_unknown_kind_is_rejected(self, repo: Path) -> None:
        with pytest.raises(ProvenanceError, match="unknown"):
            artefacts.provenance("nope", repo)


class TestTools:
    def test_python_packages_are_read_from_the_environment(self, repo: Path) -> None:
        tools = provenance.tool_versions(("numpy", "bpy"), repo)
        assert tools == {
            "numpy": importlib.metadata.version("numpy"),
            "bpy": importlib.metadata.version("bpy"),
        }

    def test_external_binaries_are_asked_for_their_version(self, repo: Path) -> None:
        tools = provenance.tool_versions(("ktx", "gltf-transform"), repo)
        assert tools == {"ktx": "9.8.7", "gltf-transform": "1.2.3"}

    def test_a_missing_binary_is_an_error(self, tmp_path: Path) -> None:
        with pytest.raises(ProvenanceError, match="ktx"):
            provenance.tool_versions(("ktx",), tmp_path)

    def test_unknown_tool_is_an_error(self, repo: Path) -> None:
        with pytest.raises(ProvenanceError, match="unknown tool"):
            provenance.tool_versions(("hammer",), repo)

    def test_blocks_record_the_tools_that_make_the_artefact(self, repo: Path) -> None:
        assert set(artefacts.provenance("terrain", repo)["tools"]) >= {
            "bpy",
            "gltf-transform",
            "ktx",
        }
        assert "bpy" not in artefacts.provenance("trail", repo)["tools"]


class TestVerify:
    def test_a_matching_tree_passes(self, repo: Path, assets: Path) -> None:
        assert provenance.verify_generated(assets, repo) == []

    def test_editing_the_curated_toml_flags_exactly_the_artefacts_that_use_it(
        self, repo: Path, assets: Path
    ) -> None:
        (repo / "data" / "curated" / "tunnel.toml").write_text(TOML_TEXT + "# edit\n", "utf-8")
        problems = provenance.verify_generated(assets, repo)
        assert flagged(problems) == {
            "terrain/manifest.json",
            "terrain/collision.json",
            "tunnel.json",
            "trail.json",
        }
        assert all("data/curated/tunnel.toml" in p.message for p in problems)

    def test_a_changed_raw_source_flags_only_its_consumers(self, repo: Path, assets: Path) -> None:
        shas = {source_id: sha(source_id) for source_id in RAW_FILES}
        shas["icv-orto-2024-0848-7-2"] = sha("new orthophoto")
        write_lock(repo, shas)
        assert flagged(provenance.verify_generated(assets, repo)) == {"terrain/manifest.json"}

    def test_an_osm_change_flags_the_surface_masks(self, repo: Path, assets: Path) -> None:
        shas = {source_id: sha(source_id) for source_id in RAW_FILES}
        shas["osm-penyal"] = sha("new osm extract")
        write_lock(repo, shas)
        assert "surfaces/manifest.json" in flagged(provenance.verify_generated(assets, repo))

    def test_a_texture_source_change_flags_the_materials(self, repo: Path, assets: Path) -> None:
        shas = {source_id: sha(source_id) for source_id in RAW_FILES}
        shas["polyhaven-marble-cliff-05-diff-1k"] = sha("replaced")
        write_lock(repo, shas)
        assert flagged(provenance.verify_generated(assets, repo)) == {"materials/manifest.json"}

    def test_a_tool_whose_installed_version_differs_from_the_recorded_one_flags_the_artefact(
        self, repo: Path, assets: Path
    ) -> None:
        write_script(repo / "tools" / "bin" / "ktx", "ktx version: v9.9.0")
        problems = provenance.verify_generated(assets, repo)
        assert flagged(problems) == {"terrain/manifest.json", "materials/manifest.json"}
        assert all("ktx" in p.message and "9.8.7" in p.message for p in problems)

    def test_a_recorded_tool_that_can_no_longer_be_read_flags_the_artefact(
        self, repo: Path, assets: Path
    ) -> None:
        (repo / "tools" / "bin" / "ktx").unlink()
        problems = provenance.verify_generated(assets, repo)
        assert flagged(problems) == {"terrain/manifest.json", "materials/manifest.json"}
        assert all("ktx" in p.message for p in problems)

    def test_an_artefact_without_a_provenance_block_is_reported(
        self, repo: Path, assets: Path
    ) -> None:
        (assets / "trail.json").write_text('{"version":1}', encoding="utf-8")
        (problem,) = provenance.verify_generated(assets, repo)
        assert problem.artefact == "trail.json"
        assert "no provenance" in problem.message

    def test_a_missing_artefact_is_reported(self, repo: Path, assets: Path) -> None:
        (assets / "materials" / "manifest.json").unlink()
        (problem,) = provenance.verify_generated(assets, repo)
        assert problem.artefact == "materials/manifest.json"
        assert "missing" in problem.message

    def test_an_input_that_is_gone_is_reported(self, repo: Path, assets: Path) -> None:
        (repo / "data" / "curated" / "tunnel.toml").unlink()
        assert "tunnel.json" in flagged(provenance.verify_generated(assets, repo))


class TestCommand:
    def test_an_empty_assets_dir_fails_naming_every_artefact(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["verify-generated", "--assets-dir", str(tmp_path)]) == 1
        output = capsys.readouterr().out
        for name in ALL_JSON:
            assert name in output
