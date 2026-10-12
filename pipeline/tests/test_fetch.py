import hashlib
import json
from dataclasses import replace
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from conftest import FakeServer

from penyal_pipeline.catalog import Layer, Source
from penyal_pipeline.fetch import (
    Downloader,
    FetchError,
    SizeMismatchError,
    _wfs_url,  # pyright: ignore[reportPrivateUsage]
    _wms_url,  # pyright: ignore[reportPrivateUsage]
    plan_rows,
    read_manifest,
    run_fetch,
    verify_sources,
)

PAYLOAD = bytes(range(256)) * 400  # 102_400 bytes
TODAY = date(2026, 10, 11)


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


def _wfs_source(server: FakeServer, layers: tuple[Layer, ...], page_size: int = 2) -> Source:
    return _source(
        server.url("/wfs"),
        id="wfs-demo",
        kind="wfs",
        expected_bytes=None,
        version="2.0.0",
        bbox=(1.0, 2.0, 3.0, 4.0),
        crs="EPSG:25830",
        output_format="application/json; subtype=geojson",
        page_size=page_size,
        layers=layers,
    )


def test_download_writes_file_and_hash(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    record = downloader.download(server.url("/a.bin"), tmp_path / "x" / "a.bin")
    assert record.bytes == len(PAYLOAD)
    assert record.sha256 == hashlib.sha256(PAYLOAD).hexdigest()
    assert (tmp_path / "x" / "a.bin").read_bytes() == PAYLOAD
    assert not (tmp_path / "x" / "a.bin.part").exists()


def test_interrupted_transfer_resumes_with_range(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    server.truncate_once["/a.bin"] = 30_000
    record = downloader.download(server.url("/a.bin"), tmp_path / "a.bin")
    assert (tmp_path / "a.bin").read_bytes() == PAYLOAD
    assert record.sha256 == hashlib.sha256(PAYLOAD).hexdigest()
    ranges = [h.get("Range") for _, h in server.requests]
    assert ranges == [None, "bytes=30000-"]


def test_existing_part_file_is_resumed(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    (tmp_path / "a.bin.part").write_bytes(PAYLOAD[:1000])
    record = downloader.download(server.url("/a.bin"), tmp_path / "a.bin")
    assert (tmp_path / "a.bin").read_bytes() == PAYLOAD
    assert record.sha256 == hashlib.sha256(PAYLOAD).hexdigest()
    assert server.requests[0][1]["Range"] == "bytes=1000-"


def test_server_ignoring_range_restarts_cleanly(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    server.ignore_range.add("/a.bin")
    (tmp_path / "a.bin.part").write_bytes(b"garbage-from-another-version")
    record = downloader.download(server.url("/a.bin"), tmp_path / "a.bin")
    assert (tmp_path / "a.bin").read_bytes() == PAYLOAD
    assert record.sha256 == hashlib.sha256(PAYLOAD).hexdigest()


def test_complete_part_file_is_finalized_on_416(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    (tmp_path / "a.bin.part").write_bytes(PAYLOAD)
    record = downloader.download(server.url("/a.bin"), tmp_path / "a.bin")
    assert record.bytes == len(PAYLOAD)
    assert (tmp_path / "a.bin").read_bytes() == PAYLOAD


def test_http_500_is_retried_with_exponential_backoff(
    server: FakeServer, downloader: Downloader, sleeps: list[float], tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    server.fail_500["/a.bin"] = 2
    downloader.download(server.url("/a.bin"), tmp_path / "a.bin")
    assert sleeps == [0.001, 0.002]
    assert (tmp_path / "a.bin").read_bytes() == PAYLOAD


def test_persistent_500_fails_after_retries(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    server.fail_500["/a.bin"] = 99
    with pytest.raises(FetchError, match="failed after 4 attempts"):
        downloader.download(server.url("/a.bin"), tmp_path / "a.bin")
    assert not (tmp_path / "a.bin").exists()


def test_http_404_is_not_retried(
    server: FakeServer, downloader: Downloader, sleeps: list[float], tmp_path: Path
) -> None:
    with pytest.raises(FetchError, match="HTTP 404"):
        downloader.download(server.url("/missing"), tmp_path / "m.bin")
    assert sleeps == []


def test_size_mismatch_fails_with_actionable_message(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    source = _source(server.url("/a.bin"), expected_bytes=len(PAYLOAD) * 2)
    errors = run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY)
    assert len(errors) == 1
    assert "expects about" in errors[0]
    assert "expected_bytes" in errors[0]
    assert not (tmp_path / "raw" / "demo" / "a.bin").exists()
    assert not (tmp_path / "manifest.lock.json").exists()


def test_size_within_tolerance_is_accepted(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    source = _source(server.url("/a.bin"), expected_bytes=int(len(PAYLOAD) * 1.005))
    assert run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY) == []


def test_size_mismatch_error_type(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    with pytest.raises(SizeMismatchError):
        downloader.download(
            server.url("/a.bin"), tmp_path / "a.bin", expected_bytes=10, tolerance=0.01
        )


def test_manifest_is_deterministic_and_verify_detects_corruption(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    source = _source(server.url("/a.bin"))
    assert run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY) == []

    text = (tmp_path / "manifest.lock.json").read_text()
    assert text.endswith("}\n")
    manifest = json.loads(text)
    entry = manifest["sources"]["demo"]
    assert entry == {
        "attribution": "Demo attribution",
        "files": [
            {
                "bytes": len(PAYLOAD),
                "name": "a.bin",
                "sha256": hashlib.sha256(PAYLOAD).hexdigest(),
            }
        ],
        "licence": "CC BY 4.0",
        "retrieved": "2026-10-11",
        "url": server.url("/a.bin"),
    }
    assert text == json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    assert verify_sources([source], data_dir=tmp_path) == []

    target = tmp_path / "raw" / "demo" / "a.bin"
    corrupted = bytearray(PAYLOAD)
    corrupted[5] ^= 0xFF
    target.write_bytes(bytes(corrupted))
    problems = verify_sources([source], data_dir=tmp_path)
    assert len(problems) == 1
    assert "sha256 differs" in problems[0]

    target.write_bytes(PAYLOAD[:-1])
    assert "bytes" in verify_sources([source], data_dir=tmp_path)[0]

    target.unlink()
    assert "missing" in verify_sources([source], data_dir=tmp_path)[0]


def test_verify_reports_source_missing_from_manifest(tmp_path: Path) -> None:
    problems = verify_sources([_source("http://x/a.bin")], data_dir=tmp_path)
    assert "not in manifest.lock.json" in problems[0]


def test_rerun_reuses_existing_file_without_network(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/a.bin"] = PAYLOAD
    source = _source(server.url("/a.bin"))
    run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY)
    before = len(server.requests)
    assert run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY) == []
    assert len(server.requests) == before


def test_wfs_pages_until_exhausted(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.wfs_features["Roads"] = 3  # page size 2 -> two pages
    source = _wfs_source(server, (Layer("Roads"),))
    assert run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY) == []

    collection = json.loads((tmp_path / "raw" / "wfs-demo" / "Roads.geojson").read_text())
    assert [f["id"] for f in collection["features"]] == ["Roads.0", "Roads.1", "Roads.2"]
    queries = [path for path, _ in server.requests]
    assert len(queries) == 2
    assert "startIndex=0" in queries[0]
    assert "startIndex=2" in queries[1]
    assert "bbox=1%2C2%2C3%2C4%2CEPSG%3A25830" in queries[0]
    assert "typeNames=Roads" in queries[0]

    files = read_manifest(tmp_path / "manifest.lock.json")["sources"]["wfs-demo"]["files"]
    assert [f["name"] for f in files] == ["Roads.geojson"]


def test_wfs_bbox_keeps_full_coordinate_precision(server: FakeServer) -> None:
    source = _wfs_source(server, (Layer("Roads"),))
    source = replace(source, bbox=(766400.0, 4279453.5, 769000.0, 4282000.0))
    query = parse_qs(urlparse(_wfs_url(source, "Roads", 10, 0)).query)
    assert query["bbox"] == ["766400,4279453.5,769000,4282000,EPSG:25830"]


def test_wfs_exact_multiple_stops_on_number_matched(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.wfs_features["Roads"] = 4
    source = _wfs_source(server, (Layer("Roads"),))
    run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY)
    assert len(server.requests) == 2


def test_unconfirmed_wfs_layer_is_skipped_but_confirmed_failure_is_reported(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.wfs_features["Roads"] = 1
    server.wfs_missing.update({"Water", "Broken"})
    ok = _wfs_source(server, (Layer("Roads"), Layer("Water", confirmed=False)))
    assert run_fetch([ok], data_dir=tmp_path, downloader=downloader, today=TODAY) == []
    files = read_manifest(tmp_path / "manifest.lock.json")["sources"]["wfs-demo"]["files"]
    assert [f["name"] for f in files] == ["Roads.geojson"]

    bad = _wfs_source(server, (Layer("Broken"),))
    errors = run_fetch([bad], data_dir=tmp_path, downloader=downloader, today=TODAY)
    assert len(errors) == 1
    assert "HTTP 400" in errors[0]


def test_osm_single_get_with_user_agent(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    body = b'{"version":"0.6","elements":[]}'
    server.files["/map.json"] = body
    source = _source(server.url("/map.json"), id="osm-demo", kind="osm", expected_bytes=None)
    assert run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY) == []
    assert (tmp_path / "raw" / "osm-demo" / "osm-demo.json").read_bytes() == body
    assert server.requests[0][1]["User-Agent"].startswith("penyal-ifac-3d pipeline")


def test_osm_snapshot_is_kept_on_rerun_so_inputs_stay_reproducible(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/map.json"] = b'{"elements":[1]}'
    source = _source(server.url("/map.json"), id="osm-demo", kind="osm", expected_bytes=None)
    run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY)
    server.files["/map.json"] = b'{"elements":[2]}'
    before = len(server.requests)
    assert run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY) == []
    assert len(server.requests) == before
    assert (tmp_path / "raw" / "osm-demo" / "osm-demo.json").read_bytes() == b'{"elements":[1]}'


def test_refresh_replaces_osm_snapshot(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/map.json"] = b'{"elements":[1]}'
    source = _source(server.url("/map.json"), id="osm-demo", kind="osm", expected_bytes=None)
    run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY)
    server.files["/map.json"] = b'{"elements":[2]}'
    run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY, refresh=True)
    assert (tmp_path / "raw" / "osm-demo" / "osm-demo.json").read_bytes() == b'{"elements":[2]}'


def test_wfs_rerun_only_fetches_missing_layers(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.wfs_features.update({"Roads": 1, "Paths": 1})
    run_fetch(
        [_wfs_source(server, (Layer("Roads"),))],
        data_dir=tmp_path,
        downloader=downloader,
        today=TODAY,
    )
    server.requests.clear()
    both = _wfs_source(server, (Layer("Roads"), Layer("Paths")))
    assert run_fetch([both], data_dir=tmp_path, downloader=downloader, today=TODAY) == []
    assert all("typeNames=Paths" in path for path, _ in server.requests)
    files = read_manifest(tmp_path / "manifest.lock.json")["sources"]["wfs-demo"]["files"]
    assert [f["name"] for f in files] == ["Roads.geojson", "Paths.geojson"]


def test_plan_rows_describe_without_downloading() -> None:
    rows = plan_rows([_source("https://example.org/x/big.tif", expected_bytes=825_000_000)])
    assert rows == [["demo", "big.tif", "example.org", "~825.0 MB", "CC BY 4.0"]]


JPEG = b"\xff\xd8\xff\xe0" + bytes(range(256)) * 40  # 10_244 bytes, JPEG magic number


def _wms_source(server: FakeServer, **overrides: object) -> Source:
    fields: dict[str, object] = {
        "id": "wms-demo",
        "kind": "wms",
        "url": server.url("/wms"),
        "expected_bytes": len(JPEG),
        "size_tolerance": 0.05,
        "version": "1.3.0",
        "layer": "L_PAN",
        "bbox": (767000.0, 4280000.0, 768500.0, 4281500.0),
        "crs": "EPSG:25830",
        "width": 3000,
        "height": 3000,
        "output_format": "image/jpeg",
    }
    fields.update(overrides)
    return _source(**fields)  # type: ignore[arg-type]


def test_wms_url_is_a_deterministic_getmap_with_a_fixed_bbox() -> None:
    source = _wms_source(FakeServer(base_url="http://x"))
    url = _wms_url(source)
    assert url == _wms_url(source)
    query = parse_qs(urlparse(url).query, keep_blank_values=True)
    assert {k: v[0] for k, v in query.items()} == {
        "service": "WMS",
        "version": "1.3.0",
        "request": "GetMap",
        "layers": "L_PAN",
        "styles": "",
        "crs": "EPSG:25830",
        "bbox": "767000,4280000,768500,4281500",
        "width": "3000",
        "height": "3000",
        "format": "image/jpeg",
    }


def test_wms_crop_is_downloaded_hashed_and_locked(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/wms"] = JPEG
    source = _wms_source(server)
    assert run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY) == []
    assert (tmp_path / "raw" / "wms-demo" / "wms-demo.jpg").read_bytes() == JPEG
    entry = read_manifest(tmp_path / "manifest.lock.json")["sources"]["wms-demo"]
    assert entry["files"] == [
        {"name": "wms-demo.jpg", "bytes": len(JPEG), "sha256": hashlib.sha256(JPEG).hexdigest()}
    ]
    assert entry["request"]["bbox"] == [767000.0, 4280000.0, 768500.0, 4281500.0]
    assert entry["request"]["layer"] == "L_PAN"
    assert verify_sources([source], data_dir=tmp_path) == []
    n_requests = len(server.requests)
    assert run_fetch([source], data_dir=tmp_path, downloader=downloader, today=TODAY) == []
    assert len(server.requests) == n_requests  # the snapshot is reused, no network


def test_wms_size_outside_tolerance_is_reported(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/wms"] = JPEG + bytes(2_000)
    errors = run_fetch([_wms_source(server)], data_dir=tmp_path, downloader=downloader, today=TODAY)
    assert len(errors) == 1
    assert "wms-demo" in errors[0]
    assert "tolerance" in errors[0]


def test_wms_service_exception_with_http_200_is_not_saved_as_an_image(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/wms"] = b'<?xml version="1.0"?><ServiceExceptionReport/>'
    errors = run_fetch(
        [_wms_source(server, expected_bytes=None)],
        data_dir=tmp_path,
        downloader=downloader,
        today=TODAY,
    )
    assert len(errors) == 1
    assert "image/jpeg" in errors[0]
    assert not (tmp_path / "raw" / "wms-demo" / "wms-demo.jpg").exists()


def test_changing_the_wms_bbox_is_flagged_as_lock_drift(
    server: FakeServer, downloader: Downloader, tmp_path: Path
) -> None:
    server.files["/wms"] = JPEG
    run_fetch([_wms_source(server)], data_dir=tmp_path, downloader=downloader, today=TODAY)
    moved = _wms_source(server, bbox=(767000.0, 4280000.0, 768000.0, 4281000.0))
    problems = verify_sources([moved], data_dir=tmp_path)
    assert len(problems) == 1
    assert "bbox" in problems[0]


def test_plan_rows_for_a_wms_crop_show_the_expected_size() -> None:
    source = _wms_source(FakeServer(base_url="http://example.org"), expected_bytes=1_280_000)
    row = ["wms-demo", "wms-demo.jpg", "example.org", "~1.3 MB", "CC BY 4.0"]
    assert plan_rows([source]) == [row]
