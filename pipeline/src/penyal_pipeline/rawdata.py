"""Locate files under ``data/raw`` through ``data/manifest.lock.json``."""

from dataclasses import dataclass
from pathlib import Path

from penyal_pipeline.fetch import read_manifest
from penyal_pipeline.paths import DATA_DIR


class RawDataError(RuntimeError):
    """A required raw file is not in the manifest or not on disk."""


@dataclass(frozen=True)
class RawFile:
    source_id: str
    path: Path
    sha256: str


def locate(source_id: str, suffix: str, data_dir: Path = DATA_DIR) -> RawFile:
    """Return the single manifest file of ``source_id`` whose name ends with ``suffix``."""
    manifest = read_manifest(data_dir / "manifest.lock.json")
    entry = manifest["sources"].get(source_id)
    if entry is None:
        raise RawDataError(
            f"{source_id} is not in manifest.lock.json; run `penyal fetch --phase 1 "
            f"--only {source_id}` first"
        )
    matches = [f for f in entry["files"] if str(f["name"]).endswith(suffix)]
    if len(matches) != 1:
        raise RawDataError(
            f"{source_id}: expected exactly one manifest file ending in {suffix!r}, "
            f"found {len(matches)}"
        )
    path = data_dir / "raw" / source_id / matches[0]["name"]
    if not path.is_file():
        raise RawDataError(f"{path} is listed in the manifest but missing on disk")
    return RawFile(source_id=source_id, path=path, sha256=str(matches[0]["sha256"]))
