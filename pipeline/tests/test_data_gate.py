"""``PENYAL_REQUIRE_DATA=1`` turns skips of data-dependent tests into failures."""

from pathlib import Path

import pytest
from conftest import raw_marks

pytest_plugins = ["pytester"]

CONFTEST = Path(__file__).with_name("conftest.py")
MISSING = "no-such-source/*.tif"
TEST_FILE = f"""
from conftest import raw_marks
import pytest

pytestmark = raw_marks({MISSING!r})

def test_needs_the_data():
    raise AssertionError("must not run without the data")
"""


@pytest.fixture
def project(pytester: pytest.Pytester) -> pytest.Pytester:
    pytester.makeconftest(CONFTEST.read_text(encoding="utf-8"))
    pytester.makepyfile(test_data=TEST_FILE)
    return pytester


def test_missing_data_skips_by_default(
    project: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PENYAL_REQUIRE_DATA", raising=False)
    project.runpytest().assert_outcomes(skipped=1)


def test_missing_data_fails_when_required(
    project: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PENYAL_REQUIRE_DATA", "1")
    result = project.runpytest()
    result.assert_outcomes(errors=1)
    assert result.ret != 0
    result.stdout.fnmatch_lines([f"*PENYAL_REQUIRE_DATA=1*{MISSING}*"])


def test_other_values_do_not_require_data(
    project: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PENYAL_REQUIRE_DATA", "0")
    project.runpytest().assert_outcomes(skipped=1)


def test_present_data_adds_no_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PENYAL_REQUIRE_DATA", "1")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.tif").write_bytes(b"")
    marks = raw_marks("src/*.tif", raw_dir=tmp_path)
    assert [mark.name for mark in marks] == ["data"]
