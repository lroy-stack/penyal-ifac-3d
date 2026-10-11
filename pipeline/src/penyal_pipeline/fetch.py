"""Download catalogue sources into ``data/raw`` and maintain ``data/manifest.lock.json``."""

import contextlib
import fcntl
import hashlib
import http.client
import json
import logging
import re
import ssl
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from penyal_pipeline.catalog import Source
from penyal_pipeline.nat64 import Nat64Resolver
from penyal_pipeline.paths import DATA_DIR
from penyal_pipeline.render import human_bytes

log = logging.getLogger(__name__)

USER_AGENT = "penyal-ifac-3d pipeline/0.1"
MANIFEST_VERSION = 1
CHUNK = 1024 * 1024
MAX_WFS_PAGES = 1000
LOCK_FILE = ".fetch.lock"
OSM_AND_WFS = ("osm", "wfs")


class FetchError(RuntimeError):
    """A download failed and will not be retried further."""


class SizeMismatchError(FetchError):
    """The downloaded size is outside the catalogue tolerance."""


class _Retryable(Exception):
    """Transient failure; the operation may be repeated."""


@dataclass(frozen=True)
class FileRecord:
    name: str
    bytes: int
    sha256: str


def _hasher_for(path: Path) -> "hashlib._Hash":
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest


def sha256_file(path: Path) -> str:
    return _hasher_for(path).hexdigest()


def check_size(
    name: str,
    size: int,
    expected: int | None,
    tolerance: float,
    source_id: str,
    *,
    path: Path | None = None,
) -> None:
    """Fail loudly when ``size`` deviates from ``expected`` by more than ``tolerance``.

    ``path`` is the file on disk that holds the data (the ``.part`` file while downloading).
    """
    if expected is None:
        return
    if abs(size - expected) > expected * tolerance:
        where = str(path) if path is not None else name
        raise SizeMismatchError(
            f"{source_id}: {name} is {size} bytes but the catalogue expects about {expected} "
            f"(tolerance {tolerance:.1%}). The data is left at {where}. If the source "
            f"legitimately changed, update expected_bytes in data/catalog.toml and run again "
            f"(that file is then reused); otherwise delete {where} and retry."
        )


def _local_error(path: Path, exc: OSError) -> FetchError:
    return FetchError(
        f"cannot write {path}: {exc.strerror or exc}. This is a local problem (disk space or "
        "permissions), so it is not retried; fix it and run the command again, partial "
        "downloads resume."
    )


def _meta_path(part: Path) -> Path:
    return part.with_name(part.name + ".meta")


def _read_meta(part: Path) -> dict[str, str | None]:
    try:
        raw = json.loads(_meta_path(part).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _discard_partial(part: Path) -> None:
    part.unlink(missing_ok=True)
    _meta_path(part).unlink(missing_ok=True)


class Downloader:
    """HTTP GET client with resume, retries with exponential backoff and timeouts."""

    def __init__(
        self,
        *,
        timeout: float = 60.0,
        retries: int = 4,
        backoff: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
        user_agent: str = USER_AGENT,
        nat64: Nat64Resolver | None = None,
    ) -> None:
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.sleep = sleep
        self.user_agent = user_agent
        self._opener = nat64.opener() if nat64 else urllib.request.build_opener()

    def _with_retries[T](self, description: str, operation: Callable[[], T]) -> T:
        for attempt in range(self.retries + 1):
            try:
                return operation()
            except _Retryable as exc:
                if attempt == self.retries:
                    raise FetchError(
                        f"{description} failed after {self.retries + 1} attempts: {exc}. "
                        "Check the network connection and run the command again; partial "
                        "downloads resume."
                    ) from exc
                delay = self.backoff * 2**attempt
                log.warning("%s: %s; retrying in %.2fs", description, exc, delay)
                self.sleep(delay)
        raise AssertionError("unreachable")

    def _open(self, url: str, headers: dict[str, str] | None = None) -> Any:
        request = urllib.request.Request(
            url, headers={"User-Agent": self.user_agent, **(headers or {})}
        )
        try:
            return self._opener.open(request, timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            if exc.code >= 500 or exc.code == 429:
                raise _Retryable(f"HTTP {exc.code}") from exc
            raise
        except (urllib.error.URLError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, ssl.SSLCertVerificationError):
                raise FetchError(
                    f"TLS certificate verification failed for {url}: {reason}. Not retried: "
                    "check the system clock and certificates, or whether a proxy is "
                    "intercepting the connection."
                ) from exc
            raise _Retryable(str(exc)) from exc

    def get_bytes(self, url: str) -> bytes:
        """GET ``url`` fully into memory (small payloads: WFS pages, OSM)."""

        def attempt() -> bytes:
            try:
                with self._open(url) as response:
                    return response.read()
            except urllib.error.HTTPError as exc:
                raise FetchError(f"GET {url} answered HTTP {exc.code} {exc.reason}") from exc
            except (http.client.HTTPException, OSError) as exc:
                raise _Retryable(str(exc)) from exc

        return self._with_retries(f"GET {url}", attempt)

    def download(
        self,
        url: str,
        dest: Path,
        *,
        source_id: str = "",
        expected_bytes: int | None = None,
        tolerance: float = 0.01,
    ) -> FileRecord:
        """Stream ``url`` into ``dest`` through ``dest.part``, resuming when possible."""
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise _local_error(dest.parent, exc) from exc
        part = dest.with_name(dest.name + ".part")

        def attempt() -> FileRecord:
            return self._attempt_download(url, dest, part, source_id, expected_bytes, tolerance)

        return self._with_retries(f"download {url}", attempt)

    def _attempt_download(
        self,
        url: str,
        dest: Path,
        part: Path,
        source_id: str,
        expected_bytes: int | None,
        tolerance: float,
    ) -> FileRecord:
        offset = part.stat().st_size if part.exists() else 0
        headers: dict[str, str] = {}
        if offset:
            headers["Range"] = f"bytes={offset}-"
            meta = _read_meta(part)
            validator = meta.get("etag") or meta.get("lastModified")
            if validator:
                headers["If-Range"] = validator
        try:
            response = self._open(url, headers or None)
        except urllib.error.HTTPError as exc:
            if exc.code == 416 and offset:
                match = re.fullmatch(r"bytes \*/(\d+)", exc.headers.get("Content-Range", ""))
                if match and int(match.group(1)) == offset:
                    return self._finalize(dest, part, source_id, expected_bytes, tolerance)
                _discard_partial(part)
                raise _Retryable("stale partial file discarded (HTTP 416)") from exc
            raise FetchError(f"GET {url} answered HTTP {exc.code} {exc.reason}") from exc

        digest = hashlib.sha256()
        with response:
            total: int | None
            if offset and response.status == 206:
                total = self._check_content_range(response, offset, part)
                log.info("resuming %s at byte %d", dest.name, offset)
                digest = _hasher_for(part)
                mode = "ab"
            else:
                if offset:
                    log.info(
                        "server ignored Range or the file changed for %s; restarting", dest.name
                    )
                mode = "wb"
                length = response.headers.get("Content-Length")
                total = int(length) if length is not None and length.isdigit() else None
                self._write_meta(part, response)
            announced = response.headers.get("Content-Length")
            received = 0
            try:
                out = part.open(mode)
            except OSError as exc:
                raise _local_error(part, exc) from exc
            with out:
                while True:
                    try:
                        chunk = response.read(CHUNK)
                    except (http.client.HTTPException, OSError) as exc:
                        raise _Retryable(f"transfer interrupted: {exc}") from exc
                    if not chunk:
                        break
                    try:
                        out.write(chunk)
                    except OSError as exc:
                        raise _local_error(part, exc) from exc
                    digest.update(chunk)
                    received += len(chunk)
            if announced is not None and received != int(announced):
                raise _Retryable(f"transfer interrupted after {received} of {announced} bytes")
        size = part.stat().st_size
        if total is not None and size != total:
            if size > total:
                _discard_partial(part)
            raise _Retryable(f"{dest.name} has {size} bytes but the server announced {total}")
        return self._finalize(dest, part, source_id, expected_bytes, tolerance, digest.hexdigest())

    @staticmethod
    def _check_content_range(response: Any, offset: int, part: Path) -> int | None:
        """Require a ``Content-Range`` that starts at ``offset``; return the announced total."""
        header = response.headers.get("Content-Range", "")
        match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+|\*)", header)
        if match is None or int(match.group(1)) != offset:
            _discard_partial(part)
            raise _Retryable(
                f"server answered 206 with Content-Range {header!r} for a request at byte "
                f"{offset}; partial file discarded"
            )
        return None if match.group(3) == "*" else int(match.group(3))

    @staticmethod
    def _write_meta(part: Path, response: Any) -> None:
        meta = {
            "etag": response.headers.get("ETag"),
            "lastModified": response.headers.get("Last-Modified"),
        }
        try:
            if meta["etag"] or meta["lastModified"]:
                _meta_path(part).write_text(json.dumps(meta), encoding="utf-8")
            else:
                _meta_path(part).unlink(missing_ok=True)
        except OSError as exc:
            raise _local_error(_meta_path(part), exc) from exc

    def _finalize(
        self,
        dest: Path,
        part: Path,
        source_id: str,
        expected_bytes: int | None,
        tolerance: float,
        sha: str | None = None,
    ) -> FileRecord:
        size = part.stat().st_size
        check_size(dest.name, size, expected_bytes, tolerance, source_id, path=part)
        sha = sha or sha256_file(part)
        part.replace(dest)
        _meta_path(part).unlink(missing_ok=True)
        return FileRecord(dest.name, size, sha)


def _write_atomic(path: Path, data: bytes) -> FileRecord:
    tmp = path.with_name(path.name + ".part")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(data)
        tmp.replace(path)
    except OSError as exc:
        raise _local_error(path, exc) from exc
    return FileRecord(path.name, len(data), hashlib.sha256(data).hexdigest())


def _coordinate(value: float) -> str:
    """Plain decimal text without exponent or precision loss (``:g`` would print 4.27945e+06)."""
    return str(int(value)) if float(value).is_integer() else repr(float(value))


def _wfs_url(source: Source, layer: str, count: int, start: int) -> str:
    assert source.bbox is not None
    minx, miny, maxx, maxy = source.bbox
    params = {
        "service": "WFS",
        "version": source.version,
        "request": "GetFeature",
        "typeNames": layer,
        "srsName": source.crs,
        "bbox": ",".join([*(_coordinate(v) for v in (minx, miny, maxx, maxy)), source.crs]),
        "outputFormat": source.output_format,
        "count": str(count),
        "startIndex": str(start),
    }
    if source.sort_by:
        params["sortBy"] = source.sort_by
    sep = "&" if "?" in source.url else "?"
    return f"{source.url}{sep}{urlencode(params)}"


def fetch_wfs_layer(downloader: Downloader, source: Source, layer: str) -> bytes:
    """Page through one WFS feature type and return a single GeoJSON FeatureCollection.

    When the server reports an integer ``numberMatched`` it is authoritative: paging continues
    until it is reached (a short page is not the end) and fails on an empty page, on a count
    mismatch, or after ``MAX_WFS_PAGES`` pages. Without it, a short page ends the paging.
    """
    where = f"{source.id}/{layer}"
    features: list[Any] = []
    expected: int | None = None
    for _ in range(MAX_WFS_PAGES):
        url = _wfs_url(source, layer, source.page_size, len(features))
        try:
            page = json.loads(downloader.get_bytes(url))
        except json.JSONDecodeError as exc:
            raise FetchError(
                f"{where}: the server did not return JSON ({exc}). Check "
                "output_format and typeNames in data/catalog.toml."
            ) from exc
        page_features = page.get("features") if isinstance(page, dict) else None
        if not isinstance(page_features, list):
            raise FetchError(f"{where}: response has no 'features' array")
        matched = page.get("numberMatched")
        if isinstance(matched, int) and not isinstance(matched, bool):
            if expected is not None and matched != expected:
                raise FetchError(
                    f"{where}: numberMatched changed from {expected} to {matched} while "
                    "paging; the layer is being edited. Run the command again later."
                )
            expected = matched
        features.extend(page_features)
        if expected is not None:
            if len(features) >= expected:
                break
            if not page_features:
                raise FetchError(
                    f"{where}: the server returned an empty page after {len(features)} of "
                    f"{expected} features (numberMatched). Retry later, or lower page_size or "
                    "set sort_by in data/catalog.toml."
                )
        elif len(page_features) < source.page_size:
            break
    else:
        raise FetchError(
            f"{where}: paging did not finish within {MAX_WFS_PAGES} pages "
            f"({len(features)} features so far); the server may ignore startIndex"
        )
    if expected is not None and len(features) != expected:
        raise FetchError(
            f"{where}: got {len(features)} features but numberMatched is {expected}; the "
            "paging is inconsistent (set sort_by in data/catalog.toml or retry later)"
        )
    log.info("%s: %d features", where, len(features))
    collection = {"type": "FeatureCollection", "features": features}
    return json.dumps(collection, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _existing(path: Path) -> FileRecord:
    return FileRecord(path.name, path.stat().st_size, sha256_file(path))


def fetch_source(
    downloader: Downloader, source: Source, raw_dir: Path, *, refresh: bool = False
) -> list[FileRecord]:
    """Fetch every file of ``source`` into ``raw_dir/<id>/`` and return their records.

    Files already present are kept (and re-hashed) so that pipeline inputs stay a fixed
    snapshot; ``refresh`` re-downloads OSM and WFS snapshots, which change upstream.
    """
    target = raw_dir / source.id
    if source.kind == "file":
        dest = target / source.filenames[0]
        if dest.exists():
            log.info("%s: %s already present, checking it", source.id, dest.name)
            size = dest.stat().st_size
            check_size(
                dest.name, size, source.expected_bytes, source.size_tolerance, source.id, path=dest
            )
            return [FileRecord(dest.name, size, sha256_file(dest))]
        return [
            downloader.download(
                source.url,
                dest,
                source_id=source.id,
                expected_bytes=source.expected_bytes,
                tolerance=source.size_tolerance,
            )
        ]
    if source.kind == "osm":
        dest = target / source.filenames[0]
        if dest.exists() and not refresh:
            log.info("%s: keeping snapshot %s (use --refresh to replace it)", source.id, dest.name)
            return [_existing(dest)]
        return [_write_atomic(dest, downloader.get_bytes(source.url))]

    records: list[FileRecord] = []
    for layer in source.layers:
        dest = target / f"{layer.name}.geojson"
        if dest.exists() and not refresh:
            log.info("%s: keeping snapshot %s (use --refresh to replace it)", source.id, dest.name)
            records.append(_existing(dest))
            continue
        try:
            payload = fetch_wfs_layer(downloader, source, layer.name)
        except FetchError as exc:
            if layer.confirmed:
                raise
            log.warning("skipping unconfirmed layer %s: %s", layer.name, exc)
            continue
        records.append(_write_atomic(dest, payload))
    return records


def read_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": MANIFEST_VERSION, "sources": {}}
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FetchError(f"{path} is not valid JSON ({exc}); restore it from git") from exc
    if not isinstance(manifest, dict) or not isinstance(manifest.get("sources"), dict):
        raise FetchError(f"{path} has an unexpected layout; restore it from git")
    return manifest


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def source_request(source: Source) -> dict[str, Any]:
    """Parameters that define what is requested, beyond the URL (empty for plain files)."""
    if source.kind == "osm":
        return {"url": source.url}
    if source.kind == "wfs":
        request: dict[str, Any] = {
            "version": source.version,
            "bbox": list(source.bbox or ()),
            "crs": source.crs,
            "outputFormat": source.output_format,
        }
        if source.sort_by:
            request["sortBy"] = source.sort_by
        return request
    return {}


def definition_drift(entry: dict[str, Any], source: Source) -> list[str]:
    """Differences between a manifest entry and the catalogue definition of ``source``."""
    problems: list[str] = []
    if entry.get("url") != source.url:
        problems.append(f"url {entry.get('url')!r} -> {source.url!r}")
    recorded = {k: v for k, v in entry.get("request", {}).items() if k != "typeNames"}
    wanted = source_request(source)
    for key in sorted(set(recorded) | set(wanted)):
        if recorded.get(key) != wanted.get(key):
            problems.append(f"{key} {recorded.get(key)!r} -> {wanted.get(key)!r}")
    return problems


def lock_drift(entry: dict[str, Any], source: Source, records: list[FileRecord]) -> list[str]:
    """Everything that differs between the lock and what was fetched or reused."""
    problems = definition_drift(entry, source)
    pinned = {f["name"]: f for f in entry["files"]}
    for record in records:
        old = pinned.get(record.name)
        if old is not None and (old["sha256"] != record.sha256 or old["bytes"] != record.bytes):
            problems.append(
                f"{record.name} sha256 {old['sha256'][:12]}... ({old['bytes']} bytes) -> "
                f"{record.sha256[:12]}... ({record.bytes} bytes)"
            )
    return problems


def manifest_entry(
    source: Source,
    records: list[FileRecord],
    today: date,
    previous: dict[str, Any] | None = None,
    *,
    merge: bool = False,
) -> dict[str, Any]:
    """Manifest entry for ``source``.

    ``merge`` keeps files recorded earlier that were not fetched this time. ``retrieved`` only
    moves when the files or the URL changed.
    """
    files = [{"name": r.name, "bytes": r.bytes, "sha256": r.sha256} for r in records]
    if merge and previous is not None:
        fresh = {f["name"]: f for f in files}
        files = [fresh.pop(f["name"], f) for f in previous["files"]] + list(fresh.values())
    entry: dict[str, Any] = {
        "url": source.url,
        "files": files,
        "retrieved": today.isoformat(),
        "licence": source.licence,
        "attribution": source.attribution,
    }
    request = source_request(source)
    if source.kind == "wfs":
        request["typeNames"] = [f["name"].removesuffix(".geojson") for f in files]
    if request:
        entry["request"] = request
    if (
        previous is not None
        and previous.get("files") == files
        and previous.get("url") == source.url
    ):
        entry["retrieved"] = previous["retrieved"]
    return entry


@contextlib.contextmanager
def exclusive_lock(data_dir: Path) -> Iterator[None]:
    """Hold ``data/raw/.fetch.lock`` (flock) so that two runs cannot write the same files."""
    lock = data_dir / "raw" / LOCK_FILE
    try:
        lock.parent.mkdir(parents=True, exist_ok=True)
        handle = lock.open("a")
    except OSError as exc:
        raise _local_error(lock, exc) from exc
    with handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise FetchError(
                f"another penyal fetch/verify is already running ({lock} is locked). Wait for "
                "it to finish, then run the command again."
            ) from exc
        yield


def _quarantine(names: list[str], directory: Path) -> list[Path]:
    """Move freshly downloaded files that the lock rejected out of the way (``.rejected``)."""
    moved: list[Path] = []
    for name in names:
        path = directory / name
        if path.exists():
            target = path.with_name(path.name + ".rejected")
            path.replace(target)
            moved.append(target)
    return moved


def run_fetch(
    sources: list[Source],
    *,
    data_dir: Path = DATA_DIR,
    downloader: Downloader | None = None,
    today: date | None = None,
    refresh: bool = False,
    update_lock: bool = False,
) -> list[str]:
    """Fetch ``sources`` and record them in the manifest. Returns error messages.

    The manifest is a lock: an existing entry is only replaced when the fetched or reused
    files and the source definition still match it, unless ``update_lock`` is set (``refresh``
    implies it for OSM and WFS sources, which change upstream by nature).
    """
    downloader = downloader or Downloader()
    today = today or date.today()
    manifest_path = data_dir / "manifest.lock.json"
    errors: list[str] = []
    with exclusive_lock(data_dir):
        manifest = read_manifest(manifest_path)
        for source in sources:
            log.info("fetching %s", source.id)
            target = data_dir / "raw" / source.id
            present = {name for name in source.filenames if (target / name).exists()}
            try:
                records = fetch_source(downloader, source, data_dir / "raw", refresh=refresh)
            except FetchError as exc:
                log.error("%s: %s", source.id, exc)
                errors.append(f"{source.id}: {exc}")
                continue
            previous = manifest["sources"].get(source.id)
            accept = update_lock or (refresh and source.kind in OSM_AND_WFS)
            if previous is not None and not accept:
                problems = lock_drift(previous, source, records)
                if problems:
                    rejected = _quarantine(
                        [r.name for r in records if r.name not in present], target
                    )
                    message = (
                        f"{source.id}: the lock (manifest.lock.json) pins different data: "
                        + "; ".join(problems)
                        + ". The manifest was not changed. If the upstream data or the source "
                        "definition legitimately changed, run again with --update-lock; "
                        "otherwise restore the pinned files (see `penyal fetch --verify`)."
                    )
                    if rejected:
                        message += " Newly downloaded data was kept as " + ", ".join(
                            str(r) for r in rejected
                        )
                    log.error(message)
                    errors.append(message)
                    continue
            entry = manifest_entry(source, records, today, previous, merge=not accept)
            if entry != previous:
                manifest["sources"][source.id] = entry
                write_manifest(manifest_path, manifest)
    return errors


def verify_sources(sources: list[Source], *, data_dir: Path = DATA_DIR) -> list[str]:
    """Compare ``data/raw`` and the catalogue with the manifest; one message per problem."""
    with exclusive_lock(data_dir):
        return _verify(sources, data_dir)


def _verify(sources: list[Source], data_dir: Path) -> list[str]:
    manifest = read_manifest(data_dir / "manifest.lock.json")
    problems: list[str] = []
    for source in sources:
        entry = manifest["sources"].get(source.id)
        if entry is None:
            problems.append(f"{source.id}: not in manifest.lock.json; run `penyal fetch` first")
            continue
        drift = definition_drift(entry, source)
        if drift:
            problems.append(
                f"{source.id}: the catalogue definition differs from the lock "
                f"({'; '.join(drift)}); revert data/catalog.toml or run "
                "`penyal fetch --update-lock`"
            )
        for file in entry["files"]:
            path = data_dir / "raw" / source.id / file["name"]
            if not path.exists():
                problems.append(f"{source.id}: {file['name']} is missing from data/raw")
            elif path.stat().st_size != file["bytes"]:
                problems.append(
                    f"{source.id}: {file['name']} has {path.stat().st_size} bytes, manifest "
                    f"says {file['bytes']}"
                )
            elif sha256_file(path) != file["sha256"]:
                problems.append(f"{source.id}: {file['name']} sha256 differs from the manifest")
            else:
                log.info("%s: %s ok", source.id, file["name"])
    return problems


def plan_rows(sources: list[Source]) -> list[list[str]]:
    """Rows for ``--dry-run``: id, file, host, expected size, licence."""
    rows: list[list[str]] = []
    for s in sources:
        if s.kind == "wfs":
            files = f"{len(s.layers)} GeoJSON layers"
            size = "small (paged WFS)"
        elif s.kind == "osm":
            files = s.filenames[0]
            size = "small (single request)"
        else:
            files = s.filenames[0]
            size = f"~{human_bytes(s.expected_bytes)}" if s.expected_bytes else "unknown"
        suffix = " [optional]" if s.optional else ""
        rows.append([s.id + suffix, files, s.host, size, s.licence])
    return rows
