"""Environment checks behind ``penyal doctor``.

Each check is a pure function returning a ``CheckResult``; ``main`` in ``cli`` renders them.
"""

import contextlib
import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from penyal_pipeline.paths import REPO_ROOT
from penyal_pipeline.render import format_table

OK, WARN, FAIL = "ok", "warn", "fail"

# Penyal d'Ifac summit (OSM), WGS84 -> ETRS89 / UTM 30N.
SUMMIT_LAT, SUMMIT_LON = 38.634959, 0.074459
SUMMIT_E, SUMMIT_N = 767614.0, 4280754.0
TRANSFORM_TOLERANCE_M = 2.0


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str
    required: bool = True

    def as_dict(self) -> dict[str, str | bool]:
        return asdict(self)


def _run_version(command: list[str]) -> str | None:
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    output = (done.stdout or done.stderr).strip()
    return output.splitlines()[0] if done.returncode == 0 and output else None


def check_python() -> CheckResult:
    version = platform.python_version()
    if sys.version_info[:2] != (3, 13):
        return CheckResult("python", FAIL, f"{version} (bpy 5.2.2 needs Python 3.13)")
    return CheckResult("python", OK, version)


def check_bpy() -> CheckResult:
    try:
        bpy = importlib.import_module("bpy")
    except Exception as exc:
        return CheckResult("bpy", FAIL, f"import failed: {exc}")
    return CheckResult("bpy", OK, str(bpy.app.version_string))


def check_gltf_export() -> CheckResult:
    """Export a cube to a temporary .glb with the bundled exporter and report its size."""
    name = "bpy glTF exporter"
    try:
        bpy = importlib.import_module("bpy")
        addon_utils = importlib.import_module("addon_utils")
        _, loaded = addon_utils.check("io_scene_gltf2")
        if not hasattr(bpy.ops.export_scene, "gltf"):
            return CheckResult(name, FAIL, "bpy.ops.export_scene.gltf is not registered")
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.mesh.primitive_cube_add()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "cube.glb"
            # The exporter prints progress on stdout, which would corrupt `--json` output.
            with contextlib.redirect_stdout(sys.stderr):
                result = bpy.ops.export_scene.gltf(filepath=str(target), export_format="GLB")
            if "FINISHED" not in result or not target.exists():
                return CheckResult(name, FAIL, f"export returned {sorted(result)}")
            size = target.stat().st_size
            magic = target.read_bytes()[:4]
    except Exception as exc:
        return CheckResult(name, FAIL, f"export failed: {exc}")
    if magic != b"glTF":
        return CheckResult(name, FAIL, f"output is not a GLB (magic {magic!r})")
    state = "enabled" if loaded else "loaded on demand"
    return CheckResult(name, OK, f"io_scene_gltf2 {state}; cube.glb = {size} bytes")


def check_rasterio() -> CheckResult:
    try:
        rasterio = importlib.import_module("rasterio")
    except Exception as exc:
        return CheckResult("rasterio", FAIL, f"import failed: {exc}")
    return CheckResult("rasterio", OK, f"{rasterio.__version__} (GDAL {rasterio.__gdal_version__})")


def check_pyproj_transform() -> CheckResult:
    name = "pyproj"
    try:
        pyproj = importlib.import_module("pyproj")
        transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:25830", always_xy=True)
        east, north = transformer.transform(SUMMIT_LON, SUMMIT_LAT)
    except Exception as exc:
        return CheckResult(name, FAIL, f"failed: {exc}")
    return evaluate_transform(east, north, str(pyproj.__version__), str(pyproj.proj_version_str))


def evaluate_transform(
    east: float, north: float, pyproj_version: str, proj_version: str
) -> CheckResult:
    """Judge a WGS84 -> EPSG:25830 result for the summit against the reference."""
    error = max(abs(east - SUMMIT_E), abs(north - SUMMIT_N))
    detail = (
        f"{pyproj_version} (PROJ {proj_version}); summit -> E {east:.1f} N {north:.1f}, "
        f"off by {error:.2f} m"
    )
    status = OK if error <= TRANSFORM_TOLERANCE_M else FAIL
    return CheckResult("pyproj", status, detail)


def check_laspy() -> CheckResult:
    try:
        laspy = importlib.import_module("laspy")
    except Exception as exc:
        return CheckResult("laspy", FAIL, f"import failed: {exc}")
    available = {backend.name for backend in laspy.LazBackend.detect_available()}
    if "Lazrs" not in available:
        return CheckResult("laspy", FAIL, f"{laspy.__version__}; lazrs backend unavailable")
    return CheckResult(
        "laspy", OK, f"{laspy.__version__}; lazrs backend available (backends: {sorted(available)})"
    )


def check_tool(name: str, command: list[str], hint: str) -> CheckResult:
    """Optional external tool resolved from PATH; warns when missing."""
    path = shutil.which(command[0])
    if path is None:
        return CheckResult(name, WARN, f"not found. {hint}", required=False)
    return _versioned(name, command, path)


def _versioned(name: str, command: list[str], path: str) -> CheckResult:
    """OK with the version, or WARN when the tool exists but its version cannot be read."""
    version = _run_version(command)
    if version is None:
        return CheckResult(
            name,
            WARN,
            f"found at {path} but `{' '.join(command[1:])}` gave no readable version; "
            "it may be broken or the wrong binary",
            required=False,
        )
    return CheckResult(name, OK, f"{version} ({path})", required=False)


def check_node() -> CheckResult:
    return check_tool("node", ["node", "--version"], "Install via fnm (see .node-version).")


def check_pnpm() -> CheckResult:
    return check_tool("pnpm", ["pnpm", "--version"], "Run `corepack enable` or install pnpm.")


def check_gltf_transform(repo_root: Path = REPO_ROOT) -> CheckResult:
    binary = repo_root / "node_modules" / ".bin" / "gltf-transform"
    if not binary.exists():
        return CheckResult(
            "gltf-transform", WARN, f"missing at {binary}. Run `pnpm install`.", required=False
        )
    return _versioned("gltf-transform", [str(binary), "--version"], str(binary))


def check_ktx(repo_root: Path = REPO_ROOT) -> CheckResult:
    local = repo_root / "tools" / "bin" / "ktx"
    hint = "Install KTX-Software into tools/bin (see tools/README.md); KTX2 textures need it."
    if local.exists() and os.access(local, os.X_OK):
        return _versioned("ktx", [str(local), "--version"], str(local))
    on_path = check_tool("ktx", ["ktx", "--version"], hint)
    return on_path


CHECKS: tuple[Callable[[], CheckResult], ...] = (
    check_python,
    check_bpy,
    check_gltf_export,
    check_rasterio,
    check_pyproj_transform,
    check_laspy,
    check_node,
    check_pnpm,
    check_gltf_transform,
    check_ktx,
)


def run_checks(checks: tuple[Callable[[], CheckResult], ...] = CHECKS) -> list[CheckResult]:
    return [check() for check in checks]


def exit_code(results: list[CheckResult]) -> int:
    """0 unless a required component failed; warnings never fail."""
    return 1 if any(r.status == FAIL and r.required for r in results) else 0


def render_table(results: list[CheckResult]) -> str:
    rows = [[r.status.upper(), r.name, r.detail] for r in results]
    return format_table(["STATUS", "CHECK", "DETAIL"], rows)


def render_json(results: list[CheckResult]) -> str:
    payload = {"ok": exit_code(results) == 0, "checks": [r.as_dict() for r in results]}
    return json.dumps(payload, indent=2, ensure_ascii=False)
