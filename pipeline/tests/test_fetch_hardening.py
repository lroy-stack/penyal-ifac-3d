"""Lock semantics, resume safety, WFS paging, non-transient errors, concurrency (F0 review)."""

import errno
import fcntl
import hashlib
import json
import ssl
import urllib.error
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from conftest import FakeServer

from penyal_pipeline import fetch
from penyal_pipeline.catalog import Layer, Source, load_catalog
from penyal_pipeline.fetch import (
    Downloader,
    FetchError,
    SizeMismatchError,
    read_manifest,
    run_fetch,
    verify_sources,
)
from penyal_pipeline.paths import DATA_DIR

PAYLOAD = bytes(range(256)) * 400
OTHER = PAYLOAD[::-1]
TODAY = date(2026, 10, 11)
LATER = date(2026, 12, 1)
WFS_FORMAT = "application/json; subtype=geojson"


def _source(url: str, **overrides: object) -> Source:
    fields: dict[str, object] = {
        "id": "demo",
        "phase": 1,
        "kind": "file",
        "description": "demo",
        "used_for": "tests",
        "licence": "CC BY 4.0",
        "attribution": "Demo attribution",
        "url": url,
        "expected_bytes": len(PAYLOAD),
    }
    fields.update(overrides)
    return Source(**fields)  # type: ignore[arg-type]


def _wfs(server: FakeServer, layers: tuple[Layer, ...], page_size: int = 2, **kw: Any) -> Source:
    return _source(
        server.url("/wfs"),
        id="wfs-demo",
        kind="wfs",
        expected_bytes=None,
        version="2.0.0",
        bbox=(1.0, 2.0, 3.0, 4.0),
        crs="EPSG:25830",
        output_format=WFS_FORMAT,
        page_size=page_size,
        layers=layers,
        **kw,
    )


def _osm(server: FakeServer) -> Source:
    return _source(server.url("/map.json"), id="osm-demo", kind="osm", expected_bytes=None)


def _manifest_bytes(data_dir: Path) -> bytes:
    return (data_dir / "manifest.lock.json").read_bytes()


# --- 1. the manifest is a lock ------------------------------------------------------------------


def test_different_bytes_for_a_pinned_source_fail_and_leave_the_manifest_untouched(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    source = _source(server.url("/a.bin"))
    assert run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY) == []
    before = _manifest_bytes(tmp_path)

    target = tmp_path / "raw" / "demo" / "a.bin"
    target.unlink()
    server.files["/a.bin"] = OTHER
    errors = run_fetch([source], data_dir=tmp_path, downloader=downloader, today=LATER)

    assert len(errors) == 1
    assert "--update-lock" in errors[0]
    assert "sha256" in errors[0]
    assert _manifest_bytes(tmp_path) == before
    assert not target.exists(), "an unlocked file must not be left where pipeline code reads it"
    assert (target.with_name("a.bin.rejected")).read_bytes() == OTHER


def test_local_file_that_differs_from_the_pin_fails_without_touching_it(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    source = _source(server.url("/a.bin"))
    run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY)
    before = _manifest_bytes(tmp_path)
    target = tmp_path / "raw" / "demo" / "a.bin"
    target.write_bytes(OTHER)

    errors = run_fetch([source], data_dir=tmp_path, downloader=downloader, today=LATER)

    assert len(errors) == 1
    assert "--update-lock" in errors[0]
    assert _manifest_bytes(tmp_path) == before
    assert target.read_bytes() == OTHER


def test_update_lock_accepts_the_change(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    source = _source(server.url("/a.bin"))
    run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY)
    (tmp_path / "raw" / "demo" / "a.bin").unlink()
    server.files["/a.bin"] = OTHER

    errors = run_fetch(
        [source], data_dir=tmp_path, downloader=downloader, today=LATER, update_lock=True
    )

    assert errors == []
    entry = read_manifest(tmp_path / "manifest.lock.json")["sources"]["demo"]
    assert entry["files"][0]["sha256"] == hashlib.sha256(OTHER).hexdigest()
    assert entry["retrieved"] == "2026-12-01"


def test_retrieved_is_kept_when_nothing_changed(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    source = _source(server.url("/a.bin"))
    run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY)
    before = _manifest_bytes(tmp_path)
    assert run_fetch([source], data_dir=tmp_path, downloader=downloader, today=LATER) == []
    assert _manifest_bytes(tmp_path) == before


def test_url_change_needs_update_lock(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    server.files["/b/a.bin"] = PAYLOAD
    run_fetch(
        [_source(server.url("/a.bin"))], data_dir=tmp_path, downloader=downloader, today=TODAY
    )
    before = _manifest_bytes(tmp_path)
    moved = _source(server.url("/b/a.bin"))
    errors = run_fetch([moved], data_dir=tmp_path, downloader=downloader, today=LATER)
    assert len(errors) == 1
    assert "url" in errors[0]
    assert _manifest_bytes(tmp_path) == before
    assert (
        run_fetch([moved], data_dir=tmp_path, downloader=downloader, today=LATER, update_lock=True)
        == []
    )
    assert read_manifest(tmp_path / "manifest.lock.json")["sources"]["demo"]["url"] == moved.url


def test_wfs_request_parameters_are_recorded_and_pinned(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.wfs_features["Roads"] = 3
    source = _wfs(server, (Layer("Roads"),))
    run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY)
    entry = read_manifest(tmp_path / "manifest.lock.json")["sources"]["wfs-demo"]
    assert entry["request"] == {
        "bbox": [1.0, 2.0, 3.0, 4.0],
        "crs": "EPSG:25830",
        "outputFormat": WFS_FORMAT,
        "typeNames": ["Roads"],
        "version": "2.0.0",
    }
    before = _manifest_bytes(tmp_path)
    changed = replace(source, bbox=(1.0, 2.0, 3.0, 5.0))
    errors = run_fetch([changed], data_dir=tmp_path, downloader=downloader, today=LATER)
    assert len(errors) == 1
    assert "bbox" in errors[0]
    assert _manifest_bytes(tmp_path) == before
    assert verify_sources([changed], data_dir=tmp_path) != []


def test_sort_by_is_part_of_the_pinned_request(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.wfs_features["Roads"] = 3
    source = _wfs(server, (Layer("Roads"),))
    run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY)
    errors = run_fetch(
        [replace(source, sort_by="id")], data_dir=tmp_path, downloader=downloader, today=LATER
    )
    assert len(errors) == 1
    assert "sortBy" in errors[0]


def test_refresh_implies_update_lock_only_for_osm_and_wfs(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/map.json"] = b'{"elements":[1]}'
    server.files["/a.bin"] = PAYLOAD
    osm, plain = _osm(server), _source(server.url("/a.bin"))
    run_fetch([osm, plain], data_dir=tmp_path, downloader=downloader, today=TODAY)

    server.files["/map.json"] = b'{"elements":[2]}'
    assert (
        run_fetch([osm], data_dir=tmp_path, downloader=downloader, today=LATER, refresh=True) == []
    )
    sources = read_manifest(tmp_path / "manifest.lock.json")["sources"]
    assert sources["osm-demo"]["retrieved"] == "2026-12-01"

    (tmp_path / "raw" / "demo" / "a.bin").unlink()
    server.files["/a.bin"] = OTHER
    errors = run_fetch([plain], data_dir=tmp_path, downloader=downloader, today=LATER, refresh=True)
    assert len(errors) == 1


def test_adding_a_layer_is_not_drift(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.wfs_features.update({"Roads": 1, "Paths": 1})
    run_fetch(
        [_wfs(server, (Layer("Roads"),))], data_dir=tmp_path, downloader=downloader, today=TODAY
    )
    both = _wfs(server, (Layer("Roads"), Layer("Paths")))
    assert run_fetch([both], data_dir=tmp_path, downloader=downloader, today=LATER) == []
    entry = read_manifest(tmp_path / "manifest.lock.json")["sources"]["wfs-demo"]
    assert [f["name"] for f in entry["files"]] == ["Roads.geojson", "Paths.geojson"]
    assert entry["request"]["typeNames"] == ["Roads", "Paths"]
    assert verify_sources([both], data_dir=tmp_path) == []


def test_repo_manifest_matches_the_catalogue_definitions() -> None:
    catalog = {s.id: s for s in load_catalog()}
    manifest = read_manifest(DATA_DIR / "manifest.lock.json")
    for source_id, entry in manifest["sources"].items():
        assert fetch.definition_drift(entry, catalog[source_id]) == [], source_id


# --- 2. resume safety ---------------------------------------------------------------------------


def test_206_with_a_shifted_start_is_discarded_and_restarted(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    server.shift_range["/a.bin"] = 10
    (tmp_path / "a.bin.part").write_bytes(PAYLOAD[:1000])
    record = downloader.download(server.url("/a.bin"), tmp_path / "a.bin")
    assert (tmp_path / "a.bin").read_bytes() == PAYLOAD
    assert record.sha256 == hashlib.sha256(PAYLOAD).hexdigest()
    ranges = [h.get("Range") for _, h in server.requests]
    assert ranges == ["bytes=1000-", None]


def test_validator_is_stored_and_sent_as_if_range_on_resume(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    server.etags["/a.bin"] = '"v1"'
    server.truncate_once["/a.bin"] = 30_000
    downloader.download(server.url("/a.bin"), tmp_path / "a.bin")
    assert (tmp_path / "a.bin").read_bytes() == PAYLOAD
    first, second = (h for _, h in server.requests)
    assert "If-Range" not in first
    assert second["Range"] == "bytes=30000-"
    assert second["If-Range"] == '"v1"'
    assert not (tmp_path / "a.bin.part.meta").exists()


def test_part_meta_records_etag_and_last_modified(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    server.etags["/a.bin"] = '"v1"'
    server.last_modified["/a.bin"] = "Sat, 10 Oct 2026 10:00:00 GMT"
    server.truncate_once["/a.bin"] = 30_000
    seen: list[dict[str, str]] = []
    original = fetch.Downloader._attempt_download  # pyright: ignore[reportPrivateUsage]

    def spy(self: Downloader, url: str, dest: Path, part: Path, *args: Any) -> Any:
        meta = part.with_name(part.name + ".meta")
        if meta.exists():
            seen.append(json.loads(meta.read_text()))
        return original(self, url, dest, part, *args)

    fetch.Downloader._attempt_download = spy  # type: ignore[method-assign]
    try:
        downloader.download(server.url("/a.bin"), tmp_path / "a.bin")
    finally:
        fetch.Downloader._attempt_download = original  # type: ignore[method-assign]
    assert seen == [{"etag": '"v1"', "lastModified": "Sat, 10 Oct 2026 10:00:00 GMT"}]


def test_changed_validator_restarts_cleanly(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = OTHER
    server.etags["/a.bin"] = '"v2"'
    (tmp_path / "a.bin.part").write_bytes(PAYLOAD[:1000])
    (tmp_path / "a.bin.part.meta").write_text(json.dumps({"etag": '"v1"', "lastModified": None}))
    record = downloader.download(server.url("/a.bin"), tmp_path / "a.bin")
    assert (tmp_path / "a.bin").read_bytes() == OTHER
    assert record.sha256 == hashlib.sha256(OTHER).hexdigest()
    assert server.requests[0][1]["If-Range"] == '"v1"'
    assert not (tmp_path / "a.bin.part.meta").exists()


def test_last_modified_is_the_fallback_validator(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    server.last_modified["/a.bin"] = "Sat, 10 Oct 2026 10:00:00 GMT"
    server.truncate_once["/a.bin"] = 30_000
    downloader.download(server.url("/a.bin"), tmp_path / "a.bin")
    assert server.requests[1][1]["If-Range"] == "Sat, 10 Oct 2026 10:00:00 GMT"


def test_final_size_must_equal_the_announced_total(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    """A 206 whose Content-Range total disagrees with what we end up with is not accepted."""
    server.files["/a.bin"] = PAYLOAD
    # Part is larger than the file on the server: the 206 request starts beyond a shorter file.
    (tmp_path / "a.bin.part").write_bytes(PAYLOAD + b"extra")
    record = downloader.download(server.url("/a.bin"), tmp_path / "a.bin")
    assert (tmp_path / "a.bin").read_bytes() == PAYLOAD
    assert record.bytes == len(PAYLOAD)


# --- 3. WFS paging ------------------------------------------------------------------------------


def _layer_ids(tmp_path: Path, layer: str) -> list[str]:
    collection = json.loads((tmp_path / "raw" / "wfs-demo" / f"{layer}.geojson").read_text())
    return [f["id"] for f in collection["features"]]


def test_short_page_is_not_the_end_while_number_matched_says_otherwise(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.wfs_features["Roads"] = 5
    server.wfs_max_page = 2  # server caps pages below the requested page size of 4
    source = _wfs(server, (Layer("Roads"),), page_size=4)
    assert run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY) == []
    assert _layer_ids(tmp_path, "Roads") == [f"Roads.{i}" for i in range(5)]
    assert len(server.requests) == 3


def test_empty_page_before_number_matched_fails(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.wfs_features["Roads"] = 4
    server.wfs_matched["Roads"] = 10
    errors = run_fetch(
        [_wfs(server, (Layer("Roads"),))], data_dir=tmp_path, downloader=downloader, today=TODAY
    )
    assert len(errors) == 1
    assert "4 of 10" in errors[0]
    assert not (tmp_path / "raw" / "wfs-demo" / "Roads.geojson").exists()
    assert not (tmp_path / "manifest.lock.json").exists()


def test_more_features_than_number_matched_fails(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.wfs_features["Roads"] = 4
    server.wfs_matched["Roads"] = 3
    errors = run_fetch(
        [_wfs(server, (Layer("Roads"),))], data_dir=tmp_path, downloader=downloader, today=TODAY
    )
    assert len(errors) == 1
    assert "numberMatched" in errors[0]


def test_page_cap_stops_a_server_that_never_ends(
    server: FakeServer, downloader: Downloader, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(fetch, "MAX_WFS_PAGES", 5)
    server.wfs_features["Roads"] = 1
    server.wfs_matched["Roads"] = 10**9
    server.wfs_forever.add("Roads")
    errors = run_fetch(
        [_wfs(server, (Layer("Roads"),))], data_dir=tmp_path, downloader=downloader, today=TODAY
    )
    assert len(errors) == 1
    assert "5 pages" in errors[0]
    assert len(server.requests) == 5


@pytest.mark.parametrize("matched", [None, "unknown"])
def test_without_an_integer_number_matched_a_short_page_ends_paging(
    server: FakeServer, downloader: Downloader, tmp_path: Path, matched: str | None
) -> None:
    server.wfs_features["Roads"] = 3
    server.wfs_matched["Roads"] = matched
    source = _wfs(server, (Layer("Roads"),))
    assert run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY) == []
    assert _layer_ids(tmp_path, "Roads") == ["Roads.0", "Roads.1", "Roads.2"]


def test_sort_by_is_sent_only_when_configured(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.wfs_features["Roads"] = 1
    plain = _wfs(server, (Layer("Roads"),))
    run_fetch([plain], data_dir=tmp_path / "a", downloader=downloader, today=TODAY)
    assert "sortBy" not in parse_qs(urlparse(server.requests[0][0]).query)
    sorted_source = replace(plain, sort_by="id")
    run_fetch([sorted_source], data_dir=tmp_path / "b", downloader=downloader, today=TODAY)
    assert parse_qs(urlparse(server.requests[1][0]).query)["sortBy"] == ["id"]


# --- 4. non-transient errors --------------------------------------------------------------------


def test_certificate_failure_is_not_retried(
    downloader: Downloader, sleeps: list[float], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*_: Any, **__: Any) -> Any:
        raise urllib.error.URLError(
            ssl.SSLCertVerificationError(1, "certificate verify failed: self-signed certificate")
        )

    monkeypatch.setattr(downloader._opener, "open", refuse)  # pyright: ignore[reportPrivateUsage]
    with pytest.raises(FetchError, match="certificate"):
        downloader.download("https://example.invalid/a.bin", tmp_path / "a.bin")
    with pytest.raises(FetchError, match="certificate"):
        downloader.get_bytes("https://example.invalid/map.json")
    assert sleeps == []


def test_unwritable_directory_fails_immediately(
    server: FakeServer, downloader: Downloader, sleeps: list[float], tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    target = tmp_path / "ro"
    target.mkdir()
    target.chmod(0o500)
    try:
        with pytest.raises(FetchError, match="cannot write"):
            downloader.download(server.url("/a.bin"), target / "a.bin")
    finally:
        target.chmod(0o700)
    assert sleeps == []


def test_disk_full_fails_immediately(
    server: FakeServer,
    downloader: Downloader,
    sleeps: list[float],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server.files["/a.bin"] = PAYLOAD
    real_open = Path.open

    def full(self: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if self.name.endswith(".part") and "w" in mode:
            raise OSError(errno.ENOSPC, "No space left on device")
        return real_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", full)
    with pytest.raises(FetchError, match="No space left"):
        downloader.download(server.url("/a.bin"), tmp_path / "a.bin")
    assert sleeps == []


# --- 5. size mismatch message -------------------------------------------------------------------


def test_size_mismatch_names_the_part_file_left_on_disk(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    with pytest.raises(SizeMismatchError) as caught:
        downloader.download(
            server.url("/a.bin"), tmp_path / "a.bin", expected_bytes=10, tolerance=0.01
        )
    message = str(caught.value)
    part = tmp_path / "a.bin.part"
    assert part.exists()
    assert str(part) in message
    assert "delete" in message.lower()


def test_size_mismatch_of_an_existing_file_names_that_file(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    target = tmp_path / "raw" / "demo" / "a.bin"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"short")
    errors = run_fetch(
        [_source(server.url("/a.bin"))], data_dir=tmp_path, downloader=downloader, today=TODAY
    )
    assert str(target) in errors[0]


# --- 6. concurrency -----------------------------------------------------------------------------


def test_second_concurrent_run_fails_fast(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    source = _source(server.url("/a.bin"))
    lock = tmp_path / "raw" / ".fetch.lock"
    lock.parent.mkdir(parents=True)
    with lock.open("w") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(FetchError, match="another"):
            run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY)
        with pytest.raises(FetchError, match="another"):
            verify_sources([source], data_dir=tmp_path)
    assert server.requests == []
    assert run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY) == []
