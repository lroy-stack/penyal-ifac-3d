import json
from pathlib import Path

import pytest

from penyal_pipeline import doctor
from penyal_pipeline.doctor import FAIL, OK, WARN, CheckResult


def test_transform_check_accepts_reference_and_rejects_outliers() -> None:
    assert doctor.evaluate_transform(767614.0, 4280754.0, "x", "y").status == OK
    assert doctor.evaluate_transform(767615.9, 4280752.1, "x", "y").status == OK
    assert doctor.evaluate_transform(767617.0, 4280754.0, "x", "y").status == FAIL


def test_pyproj_check_runs_for_real() -> None:
    result = doctor.check_pyproj_transform()
    assert result.status == OK, result.detail


def test_exit_code_only_fails_on_required_failures() -> None:
    ok = CheckResult("a", OK, "")
    warn = CheckResult("b", WARN, "", required=False)
    optional_fail = CheckResult("c", FAIL, "", required=False)
    required_fail = CheckResult("d", FAIL, "")
    assert doctor.exit_code([ok, warn]) == 0
    assert doctor.exit_code([ok, optional_fail]) == 0
    assert doctor.exit_code([ok, required_fail]) == 1


def test_render_table_and_json() -> None:
    results = [CheckResult("python", OK, "3.13"), CheckResult("ktx", WARN, "missing", False)]
    table = doctor.render_table(results)
    assert table.splitlines()[0].startswith("STATUS")
    assert "WARN    ktx" in table
    payload = json.loads(doctor.render_json(results))
    assert payload["ok"] is True
    assert payload["checks"][1] == {
        "name": "ktx",
        "status": "warn",
        "detail": "missing",
        "required": False,
    }


def test_missing_tools_warn(tmp_path: Path) -> None:
    assert doctor.check_gltf_transform(tmp_path).status == WARN
    result = doctor.check_ktx(tmp_path)
    assert result.status in {OK, WARN}
    assert not result.required


def test_local_ktx_is_reported_with_version(tmp_path: Path) -> None:
    binary = tmp_path / "tools" / "bin" / "ktx"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/bin/sh\necho 'ktx version: v4.4.0'\n")
    binary.chmod(0o755)
    result = doctor.check_ktx(tmp_path)
    assert result.status == OK
    assert "v4.4.0" in result.detail


@pytest.mark.slow
def test_bpy_exports_glb() -> None:
    result = doctor.check_gltf_export()
    assert result.status == OK, result.detail
    assert "bytes" in result.detail


def test_bpy_version_is_pinned() -> None:
    result = doctor.check_bpy()
    assert result.status == OK
    assert result.detail.startswith("5.2.2")


def test_laspy_has_lazrs() -> None:
    assert doctor.check_laspy().status == OK


def _script(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(0o755)
    return path


@pytest.mark.parametrize("body", ["exit 0", "echo oops >&2; exit 3"])
def test_tool_with_unreadable_version_is_a_warning_not_ok(tmp_path: Path, body: str) -> None:
    tool = _script(tmp_path / "tool", body)
    result = doctor.check_tool("tool", [str(tool), "--version"], "hint")
    assert result.status == WARN
    assert "version" in result.detail
    assert not result.required


@pytest.mark.parametrize("body", ["exit 0", "exit 3"])
def test_local_ktx_with_unreadable_version_warns(tmp_path: Path, body: str) -> None:
    _script(tmp_path / "tools" / "bin" / "ktx", body)
    result = doctor.check_ktx(tmp_path)
    assert result.status == WARN
    assert "version" in result.detail


def test_gltf_transform_with_unreadable_version_warns(tmp_path: Path) -> None:
    _script(tmp_path / "node_modules" / ".bin" / "gltf-transform", "exit 1")
    assert doctor.check_gltf_transform(tmp_path).status == WARN
