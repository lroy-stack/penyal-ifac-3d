"""A threaded local HTTP server with Range support and scriptable failures."""

import json
import os
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

from penyal_pipeline.fetch import Downloader
from penyal_pipeline.paths import DATA_DIR


def pytest_configure(config: pytest.Config) -> None:
    # Registered here (not in pyproject) so it also applies when pytest runs from the repo root.
    config.addinivalue_line(
        "markers", 'slow: exercises bpy; runs by default, deselect with -m "not slow"'
    )
    config.addinivalue_line(
        "markers", "require_data(message): fail with message (PENYAL_REQUIRE_DATA=1, data missing)"
    )
    config.addinivalue_line(
        "markers", "data: needs files under data/raw (penyal fetch); skipped only when absent"
    )


def require_data() -> bool:
    """``PENYAL_REQUIRE_DATA=1``: missing data must fail the data-dependent tests, not skip them."""
    return os.environ.get("PENYAL_REQUIRE_DATA") == "1"


def data_gate(missing: list[str], hint: str) -> list[pytest.MarkDecorator]:
    """No marks when nothing is missing; else a skip, or a failure under ``PENYAL_REQUIRE_DATA``."""
    if not missing:
        return []
    reason = f"{hint} is missing {missing}"
    if require_data():
        return [pytest.mark.require_data(f"PENYAL_REQUIRE_DATA=1 but {reason}")]
    return [pytest.mark.skip(reason=f"{reason}; run `penyal fetch --phase 1` / `penyal dem`")]


def raw_marks(*patterns: str, raw_dir: Path | None = None) -> list[pytest.MarkDecorator]:
    """Marks for ``pytestmark``: ``data``, plus the gate for globs with no match in data/raw."""
    raw = raw_dir if raw_dir is not None else DATA_DIR / "raw"
    missing = [p for p in patterns if not any(raw.glob(p))]
    return [pytest.mark.data, *data_gate(missing, "data/raw")]


def build_marks(*files: Path) -> list[pytest.MarkDecorator]:
    """Marks for outputs of earlier pipeline steps (``build/``), derived from data/raw."""
    missing = [str(f) for f in files if not f.is_file()]
    return data_gate(missing, "the build output")


def pytest_runtest_setup(item: pytest.Item) -> None:
    marker = item.get_closest_marker("require_data")
    if marker is not None:
        pytest.fail(marker.args[0], pytrace=False)


@dataclass
class FakeServer:
    base_url: str
    files: dict[str, bytes] = field(default_factory=dict)
    ignore_range: set[str] = field(default_factory=set)
    fail_500: dict[str, int] = field(default_factory=dict)
    truncate_once: dict[str, int] = field(default_factory=dict)
    wfs_features: dict[str, int] = field(default_factory=dict)
    wfs_missing: set[str] = field(default_factory=set)
    wfs_matched: dict[str, Any] = field(default_factory=dict)  # layer -> numberMatched override
    wfs_max_page: int | None = None  # server-side cap on the page size
    wfs_forever: set[str] = field(default_factory=set)  # layers that never run out of features
    etags: dict[str, str] = field(default_factory=dict)
    last_modified: dict[str, str] = field(default_factory=dict)
    shift_range: dict[str, int] = field(default_factory=dict)  # 206 starts this many bytes late
    requests: list[tuple[str, dict[str, str]]] = field(default_factory=list)

    def url(self, path: str) -> str:
        return self.base_url + path


def _make_handler(state: FakeServer) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            state.requests.append((self.path, dict(self.headers.items())))
            if state.fail_500.get(parsed.path, 0) > 0:
                state.fail_500[parsed.path] -= 1
                self.send_error(500)
                return
            if parsed.path == "/wfs":
                self._wfs(parse_qs(parsed.query))
                return
            body = state.files.get(parsed.path)
            if body is None:
                self.send_error(404)
                return
            self._file(parsed.path, body)

        def _wfs(self, query: dict[str, list[str]]) -> None:
            layer = query["typeNames"][0]
            if layer in state.wfs_missing:
                self.send_error(400, "unknown type")
                return
            total = state.wfs_features[layer]
            start = int(query["startIndex"][0])
            count = int(query["count"][0])
            if state.wfs_max_page is not None:
                count = min(count, state.wfs_max_page)
            end = start + count if layer in state.wfs_forever else min(start + count, total)
            feats = [
                {"type": "Feature", "id": f"{layer}.{i}", "properties": {"i": i}, "geometry": None}
                for i in range(start, end)
            ]
            body: dict[str, Any] = {"type": "FeatureCollection", "features": feats}
            matched = state.wfs_matched.get(layer, total)
            if matched is not None:
                body["numberMatched"] = matched
            payload = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _file(self, path: str, body: bytes) -> None:
            range_header = self.headers.get("Range")
            validators = {state.etags.get(path), state.last_modified.get(path)} - {None}
            if_range = self.headers.get("If-Range")
            if if_range is not None and if_range not in validators:
                range_header = None  # RFC 9110: a stale validator means "send the whole thing"
            start = 0
            status = 200
            if range_header and path not in state.ignore_range:
                start = int(range_header.removeprefix("bytes=").split("-")[0])
                if start >= len(body):
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{len(body)}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                status = 206
            if status == 206:
                start += state.shift_range.get(path, 0)
            chunk = body[start:]
            self.send_response(status)
            if path in state.etags:
                self.send_header("ETag", state.etags[path])
            if path in state.last_modified:
                self.send_header("Last-Modified", state.last_modified[path])
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{len(body) - 1}/{len(body)}")
            self.send_header("Content-Length", str(len(chunk)))
            self.end_headers()
            cut = state.truncate_once.pop(path, None)
            if cut is not None:
                self.wfile.write(chunk[:cut])
                self.wfile.flush()
                self.close_connection = True
                return
            self.wfile.write(chunk)

    return Handler


@pytest.fixture
def server() -> Iterator[FakeServer]:
    state = FakeServer(base_url="")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(state))
    state.base_url = f"http://127.0.0.1:{httpd.server_address[1]}"
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


@pytest.fixture
def sleeps() -> list[float]:
    return []


@pytest.fixture
def downloader(sleeps: list[float]) -> Downloader:
    """Fast downloader: recorded (not performed) backoff, short timeout."""
    return Downloader(timeout=5, retries=3, backoff=0.001, sleep=sleeps.append)
