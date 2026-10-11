import textwrap

import pytest

from penyal_pipeline.catalog import (
    CATALOG_PATH,
    CatalogError,
    load_catalog,
    parse_catalog,
    select_sources,
)

FILE_ENTRY = """
[[source]]
id = "a"
phase = 1
kind = "file"
description = "d"
used_for = "u"
url = "https://example.org/dir/a.tif"
expected_bytes = 100
licence = "CC BY 4.0"
attribution = "x"
"""


def _bad(old: str, new: str) -> str:
    return textwrap.dedent(FILE_ENTRY).replace(old, new)


def test_real_catalog_is_valid() -> None:
    sources = load_catalog(CATALOG_PATH)
    ids = {s.id for s in sources}
    assert {"icv-mdt-2016-0848", "icv-cv05-penyal", "osm-penyal"} <= ids
    assert len([s for s in sources if s.phase == 1]) == 8
    osm = next(s for s in sources if s.id == "osm-penyal")
    assert osm.share_alike
    cv05 = next(s for s in sources if s.id == "icv-cv05-penyal")
    # Every CV05 layer, Hidrografia included, returned features from the live WFS (2026-10-11).
    assert [layer.name for layer in cv05.layers if not layer.confirmed] == []
    assert cv05.bbox == (766400, 4279450, 769000, 4282000)


def test_file_entry_derives_name_and_host() -> None:
    (source,) = parse_catalog(FILE_ENTRY)
    assert source.filenames == ("a.tif",)
    assert source.host == "example.org"
    assert source.size_tolerance == 0.01


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('kind = "file"', 'kind = "ftp"'),
        ("phase = 1", 'phase = "one"'),
        ('url = "https://example.org/dir/a.tif"', 'url = "ftp://example.org/a.tif"'),
        ("expected_bytes = 100", "expected_bytes = -5"),
        ('licence = "CC BY 4.0"\n', ""),
        ("used_for", "used_four"),
    ],
)
def test_invalid_entries_are_rejected_with_context(old: str, new: str) -> None:
    with pytest.raises(CatalogError, match=r"source #1 \(a\)"):
        parse_catalog(_bad(old, new))


def test_unknown_field_is_named() -> None:
    with pytest.raises(CatalogError, match=r"unknown field.*colour"):
        parse_catalog(FILE_ENTRY + 'colour = "red"\n')


def test_wfs_requires_layers_and_bbox() -> None:
    text = """
[[source]]
id = "w"
phase = 1
kind = "wfs"
description = "d"
used_for = "u"
licence = "l"
attribution = "a"
endpoint = "https://example.org/wfs"
version = "2.0.0"
crs = "EPSG:25830"
output_format = "application/json"
bbox = [1, 2, 3, 4]
"""
    with pytest.raises(CatalogError, match=r"layers"):
        parse_catalog(text)


def test_duplicate_ids_are_rejected() -> None:
    with pytest.raises(CatalogError, match=r"duplicate source id.*a"):
        parse_catalog(FILE_ENTRY + FILE_ENTRY)


def test_invalid_toml_and_missing_file(tmp_path) -> None:
    with pytest.raises(CatalogError, match=r"invalid TOML"):
        parse_catalog("[[source")
    with pytest.raises(CatalogError, match=r"cannot read catalogue"):
        load_catalog(tmp_path / "nope.toml")


def test_select_sources_by_phase_and_only() -> None:
    sources = load_catalog(CATALOG_PATH)
    assert {s.phase for s in select_sources(sources, 3)} == {3}
    assert [s.id for s in select_sources(sources, 1, ["osm-penyal"])] == ["osm-penyal"]
    with pytest.raises(CatalogError, match=r"unknown id.*nope"):
        select_sources(sources, 1, ["nope"])
    with pytest.raises(CatalogError, match=r"no catalogue entries"):
        select_sources(sources, 9)


@pytest.mark.parametrize("bad_id", ["../x", "A", "a_b", "a/b", "-a", "a-", "a--b", "a b", ".."])
def test_ids_must_be_kebab_case_so_they_cannot_escape_data_raw(bad_id: str) -> None:
    with pytest.raises(CatalogError, match="kebab-case"):
        parse_catalog(_bad('id = "a"', f'id = "{bad_id}"'))


@pytest.mark.parametrize("good_id", ["a", "icv-mdt-2016-0848", "osm-penyal"])
def test_kebab_case_ids_are_accepted(good_id: str) -> None:
    (source,) = parse_catalog(_bad('id = "a"', f'id = "{good_id}"'))
    assert source.id == good_id


WFS_ENTRY = """
[[source]]
id = "w"
phase = 1
kind = "wfs"
description = "d"
used_for = "u"
endpoint = "https://example.org/wfs"
version = "2.0.0"
bbox = [1, 2, 3, 4]
crs = "EPSG:25830"
output_format = "application/json"
licence = "CC BY 4.0"
attribution = "x"

[[source.layers]]
name = "LAYER"
"""


@pytest.mark.parametrize("name", ["../x", "a/b", "a b", "a\\\\b", "", "a;b", "é"])
def test_wfs_layer_names_are_restricted_to_safe_characters(name: str) -> None:
    with pytest.raises(CatalogError, match="layer name"):
        parse_catalog(WFS_ENTRY.replace("LAYER", name))


@pytest.mark.parametrize("name", ["Roads", "ns:Roads_2", "a.b-c"])
def test_wfs_layer_names_with_namespace_characters_are_accepted(name: str) -> None:
    (source,) = parse_catalog(WFS_ENTRY.replace("LAYER", name))
    assert source.filenames == (f"{name}.geojson",)


def test_file_names_derived_from_the_url_must_be_safe() -> None:
    url = "https://example.org/a/.."
    with pytest.raises(CatalogError, match="safe file name"):
        parse_catalog(_bad("https://example.org/dir/a.tif", url))


def test_sort_by_is_optional_and_validated() -> None:
    (plain,) = parse_catalog(WFS_ENTRY.replace("LAYER", "Roads"))
    assert plain.sort_by == ""
    with_sort = WFS_ENTRY.replace("LAYER", "Roads").replace(
        'crs = "EPSG:25830"', 'crs = "EPSG:25830"\nsort_by = "id"'
    )
    assert parse_catalog(with_sort)[0].sort_by == "id"
    bad = with_sort.replace('sort_by = "id"', 'sort_by = "id&x=1"')
    with pytest.raises(CatalogError, match="sort_by"):
        parse_catalog(bad)


def test_real_catalog_keeps_the_locked_snapshot_order() -> None:
    """sortBy=id is supported by the ICV server but reorders the features (probed 2026-10-11),
    which would silently change the locked snapshot, so it stays off."""
    cv05 = next(s for s in load_catalog() if s.id == "icv-cv05-penyal")
    assert cv05.sort_by == ""
