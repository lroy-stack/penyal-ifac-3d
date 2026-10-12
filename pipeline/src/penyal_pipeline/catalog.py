"""Load and validate ``data/catalog.toml``."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from penyal_pipeline.paths import DATA_DIR

CATALOG_PATH = DATA_DIR / "catalog.toml"
KINDS = ("file", "wfs", "osm", "wms")
WMS_FORMATS = {"image/jpeg": "jpg", "image/png": "png"}
DEFAULT_SIZE_TOLERANCE = 0.01
# Ids and layer names become path components under data/raw, so they must not be able to escape it.
ID_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
LAYER_PATTERN = re.compile(r"[A-Za-z0-9_.:-]+")
SORT_BY_PATTERN = re.compile(r"[A-Za-z0-9_.:+, -]+")
FILENAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


class CatalogError(ValueError):
    """The catalogue is missing, malformed or inconsistent."""


@dataclass(frozen=True)
class Layer:
    name: str
    confirmed: bool = True


@dataclass(frozen=True)
class Source:
    id: str
    phase: int
    kind: str
    description: str
    used_for: str
    licence: str
    attribution: str
    url: str
    optional: bool = False
    share_alike: bool = False
    expected_bytes: int | None = None
    size_tolerance: float = DEFAULT_SIZE_TOLERANCE
    version: str = ""
    bbox: tuple[float, float, float, float] | None = None
    crs: str = ""
    output_format: str = ""
    page_size: int = 1000
    sort_by: str = ""
    layers: tuple[Layer, ...] = ()
    layer: str = ""
    width: int = 0
    height: int = 0
    filename: str = ""

    @property
    def host(self) -> str:
        return urlparse(self.url).netloc

    @property
    def filenames(self) -> tuple[str, ...]:
        """Names of the files this source produces inside ``data/raw/<id>/``."""
        if self.kind == "wfs":
            return tuple(f"{layer.name}.geojson" for layer in self.layers)
        if self.kind == "osm":
            return (f"{self.id}.json",)
        if self.filename:
            return (self.filename,)
        if self.kind == "wms":
            return (f"{self.id}.{WMS_FORMATS[self.output_format]}",)
        return (Path(urlparse(self.url).path).name,)


_COMMON = ("id", "phase", "kind", "description", "used_for", "licence", "attribution")
_ALLOWED: dict[str, set[str]] = {
    "file": {"url", "expected_bytes", "size_tolerance", "filename"},
    "wfs": {
        "endpoint",
        "version",
        "bbox",
        "crs",
        "output_format",
        "page_size",
        "sort_by",
        "layers",
    },
    "osm": {"url"},
    "wms": {
        "endpoint",
        "version",
        "layer",
        "crs",
        "bbox",
        "width",
        "height",
        "output_format",
        "expected_bytes",
        "size_tolerance",
        "filename",
    },
}
_REQUIRED: dict[str, tuple[str, ...]] = {
    "file": ("url",),
    "wfs": ("endpoint", "version", "bbox", "crs", "output_format", "layers"),
    "osm": ("url",),
    "wms": ("endpoint", "version", "layer", "crs", "bbox", "width", "height", "output_format"),
}


def _fail(where: str, message: str) -> CatalogError:
    return CatalogError(f"{where}: {message}")


def _str(raw: dict[str, Any], key: str, where: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _fail(where, f"'{key}' must be a non-empty string")
    return value


def _http_url(value: str, key: str, where: str) -> str:
    if urlparse(value).scheme not in ("http", "https"):
        raise _fail(where, f"'{key}' must be an http(s) URL, got {value!r}")
    return value


def _parse_layers(raw: object, where: str) -> tuple[Layer, ...]:
    if not isinstance(raw, list) or not raw:
        raise _fail(where, "'layers' needs at least one [[source.layers]] table")
    layers: list[Layer] = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise _fail(where, "every layer needs a string 'name'")
        confirmed = item.get("confirmed", True)
        if not isinstance(confirmed, bool):
            raise _fail(where, f"layer {item['name']!r}: 'confirmed' must be a boolean")
        if not LAYER_PATTERN.fullmatch(item["name"]):
            raise _fail(
                where,
                f"layer name {item['name']!r} must match {LAYER_PATTERN.pattern} (it names a file)",
            )
        layers.append(Layer(item["name"], confirmed))
    names = [layer.name for layer in layers]
    if len(set(names)) != len(names):
        raise _fail(where, "duplicate layer names")
    return tuple(layers)


def _parse_bbox(raw: object, where: str) -> tuple[float, float, float, float]:
    ok = (
        isinstance(raw, list)
        and len(raw) == 4
        and all(isinstance(v, int | float) and not isinstance(v, bool) for v in raw)
    )
    if not ok:
        raise _fail(where, "'bbox' must be four numbers: minx, miny, maxx, maxy")
    minx, miny, maxx, maxy = (float(v) for v in raw)  # type: ignore[union-attr]
    if minx >= maxx or miny >= maxy:
        raise _fail(where, "'bbox' must satisfy minx < maxx and miny < maxy")
    return (minx, miny, maxx, maxy)


def _parse_source(raw: object, index: int) -> Source:
    if not isinstance(raw, dict):
        raise CatalogError(f"source #{index}: must be a table")
    where = f"source #{index} ({raw.get('id', 'no id')})"
    for key in _COMMON:
        if key not in raw:
            raise _fail(where, f"missing required field '{key}'")
    kind = _str(raw, "kind", where)
    if kind not in KINDS:
        raise _fail(where, f"'kind' must be one of {', '.join(KINDS)}, got {kind!r}")
    phase = raw["phase"]
    if not isinstance(phase, int) or isinstance(phase, bool) or phase < 0:
        raise _fail(where, "'phase' must be a non-negative integer")
    for key in _REQUIRED[kind]:
        if key not in raw:
            raise _fail(where, f"kind '{kind}' requires '{key}'")
    allowed = set(_COMMON) | {"optional", "share_alike"} | _ALLOWED[kind]
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise _fail(where, f"unknown field(s) for kind '{kind}': {', '.join(unknown)}")
    for flag in ("optional", "share_alike"):
        if not isinstance(raw.get(flag, False), bool):
            raise _fail(where, f"'{flag}' must be a boolean")

    source_id = _str(raw, "id", where)
    if not ID_PATTERN.fullmatch(source_id):
        raise _fail(where, f"'id' must be kebab-case ({ID_PATTERN.pattern}), got {source_id!r}")
    common: dict[str, Any] = {
        "id": source_id,
        "phase": phase,
        "kind": kind,
        "description": _str(raw, "description", where),
        "used_for": _str(raw, "used_for", where),
        "licence": _str(raw, "licence", where),
        "attribution": _str(raw, "attribution", where),
        "optional": raw.get("optional", False),
        "share_alike": raw.get("share_alike", False),
    }
    if kind == "wfs":
        page_size = raw.get("page_size", 1000)
        if not isinstance(page_size, int) or isinstance(page_size, bool) or page_size < 1:
            raise _fail(where, "'page_size' must be a positive integer")
        sort_by = raw.get("sort_by", "")
        if sort_by != "" and (
            not isinstance(sort_by, str) or not SORT_BY_PATTERN.fullmatch(sort_by)
        ):
            raise _fail(where, f"'sort_by' must match {SORT_BY_PATTERN.pattern}")
        return Source(
            **common,
            sort_by=sort_by,
            url=_http_url(_str(raw, "endpoint", where), "endpoint", where),
            version=_str(raw, "version", where),
            bbox=_parse_bbox(raw["bbox"], where),
            crs=_str(raw, "crs", where),
            output_format=_str(raw, "output_format", where),
            page_size=page_size,
            layers=_parse_layers(raw["layers"], where),
        )

    if kind == "osm":
        return Source(**common, url=_http_url(_str(raw, "url", where), "url", where))

    extra: dict[str, Any] = {}
    if kind == "wms":
        output_format = _str(raw, "output_format", where)
        if output_format not in WMS_FORMATS:
            raise _fail(where, f"'output_format' must be one of {', '.join(WMS_FORMATS)}")
        for key in ("width", "height"):
            value = raw[key]
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise _fail(where, f"'{key}' must be a positive integer")
        extra = {
            "layer": _str(raw, "layer", where),
            "version": _str(raw, "version", where),
            "crs": _str(raw, "crs", where),
            "bbox": _parse_bbox(raw["bbox"], where),
            "width": raw["width"],
            "height": raw["height"],
            "output_format": output_format,
        }
        url = _http_url(_str(raw, "endpoint", where), "endpoint", where)
    else:
        url = _http_url(_str(raw, "url", where), "url", where)

    expected = raw.get("expected_bytes")
    if expected is not None and (
        not isinstance(expected, int) or isinstance(expected, bool) or expected <= 0
    ):
        raise _fail(where, "'expected_bytes' must be a positive integer")
    tolerance = raw.get("size_tolerance", DEFAULT_SIZE_TOLERANCE)
    if (
        not isinstance(tolerance, int | float)
        or isinstance(tolerance, bool)
        or not 0 <= tolerance < 1
    ):
        raise _fail(where, "'size_tolerance' must be a fraction in [0, 1)")
    filename = raw.get("filename", "")
    if filename != "" and not (isinstance(filename, str) and FILENAME_PATTERN.fullmatch(filename)):
        raise _fail(where, f"'filename' must match {FILENAME_PATTERN.pattern}, got {filename!r}")
    source = Source(
        **common,
        **extra,
        url=url,
        expected_bytes=expected,
        size_tolerance=float(tolerance),
        filename=filename,
    )
    name = source.filenames[0]
    if not name or name in (".", "..") or "/" in name or "\\" in name or "\0" in name:
        raise _fail(where, f"cannot derive a safe file name from url {url!r}")
    return source


def parse_catalog(text: str) -> list[Source]:
    """Parse catalogue TOML text into validated sources."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise CatalogError(f"invalid TOML: {exc}") from exc
    raw_sources = data.get("source")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise CatalogError("no [[source]] entries found")
    sources = [_parse_source(raw, i) for i, raw in enumerate(raw_sources, start=1)]
    ids = [s.id for s in sources]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise CatalogError(f"duplicate source id(s): {', '.join(duplicates)}")
    return sources


def load_catalog(path: Path = CATALOG_PATH) -> list[Source]:
    """Read and validate the catalogue file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CatalogError(f"cannot read catalogue {path}: {exc.strerror}") from exc
    try:
        return parse_catalog(text)
    except CatalogError as exc:
        raise CatalogError(f"{path}: {exc}") from exc


def select_sources(
    sources: list[Source], phase: int, only: list[str] | None = None
) -> list[Source]:
    """Sources of ``phase``, optionally restricted to the ids in ``only``."""
    if only:
        known = {s.id for s in sources}
        unknown = [i for i in only if i not in known]
        if unknown:
            raise CatalogError(
                f"unknown id(s): {', '.join(unknown)}. Known ids: {', '.join(sorted(known))}"
            )
    chosen = [s for s in sources if s.phase == phase and (not only or s.id in only)]
    if not chosen:
        raise CatalogError(
            f"no catalogue entries match phase {phase}" + (f" and ids {only}" if only else "")
        )
    return chosen
