"""Provenance of generated artefacts: input hashes, tool versions and the staleness check.

Every generated manifest carries ``inputs: [{id?, file, sha256}]`` (what its content was computed
from) and ``tools: {name: version}`` (what computed it). ``verify_generated`` recomputes the
inputs and the installed tool versions and reports the artefacts where either no longer matches.
It checks data and tools, not the pipeline code: after changing generation code, regenerate the
affected artefacts by hand.

Inputs with an ``id`` are catalogue sources: their hash is the one in ``data/manifest.lock.json``
(``penyal fetch --verify`` checks the lock against the disk). Inputs without an ``id`` (curated
files) are hashed from disk.
"""

import hashlib
import importlib.metadata
import json
import shutil
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from penyal_pipeline.fetch import read_manifest
from penyal_pipeline.paths import REPO_ROOT

ARTEFACTS = (
    "terrain/manifest.json",
    "terrain/collision.json",
    "tunnel.json",
    "trail.json",
    "vegetation.json",
    "vegetation/pine.json",
    "vegetation/plants.json",
    "materials/manifest.json",
    "surfaces/manifest.json",
    "structures.json",
)
PYTHON_PACKAGES = ("bpy", "numpy", "rasterio", "shapely", "laspy", "pyproj")
BINARIES = ("gltf-transform", "ktx", "node")
VERSION_TIMEOUT = 20


class ProvenanceError(RuntimeError):
    """An input or a tool needed for the provenance block cannot be read."""


@dataclass(frozen=True)
class Problem:
    artefact: str
    message: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _binary(name: str, root: Path) -> str | None:
    local = {
        "gltf-transform": root / "node_modules" / ".bin" / "gltf-transform",
        "ktx": root / "tools" / "bin" / "ktx",
    }.get(name)
    if local is not None and local.is_file():
        return str(local)
    return shutil.which(name)


def _binary_version(name: str, root: Path) -> str:
    binary = _binary(name, root)
    if binary is None:
        raise ProvenanceError(f"{name} not found: cannot record its version (see tools/README.md)")
    try:
        done = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=VERSION_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ProvenanceError(f"{binary} --version failed: {exc}") from exc
    lines = (done.stdout or done.stderr).strip().splitlines()
    if done.returncode != 0 or not lines or not lines[0].split():
        raise ProvenanceError(f"{binary} --version gave no readable version")
    return lines[0].split()[-1].removeprefix("v")


def tool_versions(names: Iterable[str], root: Path = REPO_ROOT) -> dict[str, str]:
    """Exact versions of ``names`` read now: installed packages and ``--version`` of binaries."""
    versions: dict[str, str] = {}
    for name in names:
        if name in PYTHON_PACKAGES:
            try:
                versions[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError as exc:
                raise ProvenanceError(f"python package {name} is not installed") from exc
        elif name in BINARIES:
            versions[name] = _binary_version(name, root)
        else:
            raise ProvenanceError(f"unknown tool {name!r}")
    return versions


def _locked_sha(root: Path, source_id: str, file: str) -> str | None:
    entry = read_manifest(root / "data" / "manifest.lock.json")["sources"].get(source_id)
    if entry is None:
        return None
    name = Path(file).name
    for item in entry["files"]:
        if item["name"] == name:
            return str(item["sha256"])
    return None


def _check_input(entry: dict[str, Any], root: Path) -> str | None:
    file, recorded = str(entry.get("file", "")), entry.get("sha256")
    source_id = entry.get("id")
    if source_id is not None:
        current = _locked_sha(root, str(source_id), file)
        if current is None:
            return f"{file}: source {source_id} is no longer in data/manifest.lock.json"
    else:
        path = root / file
        if not path.is_file():
            return f"{file}: input file is missing"
        current = sha256_file(path)
    if current != recorded:
        return f"{file}: recorded sha256 {str(recorded)[:12]} but now {current[:12]}"
    return None


def _check_tools(document: dict[str, Any], root: Path) -> list[str]:
    recorded = document.get("tools")
    if not isinstance(recorded, dict):
        return []
    messages = []
    for name, version in recorded.items():
        try:
            current = tool_versions((str(name),), root)[str(name)]
        except ProvenanceError as exc:
            messages.append(f"tool {name}: {exc}")
            continue
        if current != version:
            messages.append(f"tool {name}: recorded version {version} but now {current}")
    return messages


def verify_artefact(path: Path, name: str, root: Path) -> list[Problem]:
    if not path.is_file():
        return [Problem(name, "missing: generate it with the penyal pipeline")]
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [Problem(name, f"not valid JSON ({exc})")]
    inputs = document.get("inputs") if isinstance(document, dict) else None
    if not isinstance(inputs, list) or not inputs:
        return [Problem(name, "no provenance block (inputs): it predates provenance, regenerate")]
    problems = []
    for entry in inputs:
        message = _check_input(entry, root)
        if message is not None:
            problems.append(Problem(name, f"stale, {message}"))
    for message in _check_tools(document, root):
        problems.append(Problem(name, f"stale, {message}"))
    return problems


def verify_generated(assets_dir: Path, root: Path = REPO_ROOT) -> list[Problem]:
    """Problems of every artefact whose recorded inputs no longer match (empty when all do)."""
    problems: list[Problem] = []
    for name in ARTEFACTS:
        problems.extend(verify_artefact(assets_dir / name, name, root))
    return problems
