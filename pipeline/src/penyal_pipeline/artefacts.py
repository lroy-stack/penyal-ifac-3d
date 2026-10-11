"""Which inputs and tools each generated artefact is made from (the provenance blocks)."""

from pathlib import Path
from typing import Any

from penyal_pipeline import dem, ortho, trail, understory
from penyal_pipeline.paths import REPO_ROOT, TUNNEL_CURATED
from penyal_pipeline.provenance import ProvenanceError, relative, sha256_file, tool_versions
from penyal_pipeline.rawdata import locate

type Input = dict[str, str]

BLENDER_TOOLS = ("bpy", "gltf-transform", "ktx", "node")
PINE_TEXTURES = (
    ("polyhaven-pine-tree-01-twig-diff-1k", ".jpg"),
    ("polyhaven-pine-tree-01-twig-alpha-1k", ".jpg"),
    ("polyhaven-pine-tree-01-bark-diff-1k", ".jpg"),
)


def raw_input(source_id: str, suffix: str, root: Path = REPO_ROOT) -> Input:
    raw = locate(source_id, suffix, root / "data")
    return {"id": source_id, "file": relative(raw.path, root), "sha256": raw.sha256}


def curated_input(root: Path = REPO_ROOT) -> Input:
    path = root / TUNNEL_CURATED.relative_to(REPO_ROOT)
    return {"file": relative(path, root), "sha256": sha256_file(path)}


def _dem_inputs(root: Path) -> list[Input]:
    return [
        raw_input(dem.MDT_SOURCE_ID, dem.MDT_SUFFIX, root),
        raw_input(dem.CV05_SOURCE_ID, dem.CV05_HYDROGRAPHY, root),
    ]


def _osm_input(root: Path) -> Input:
    return raw_input(trail.OSM_SOURCE_ID, trail.OSM_FILE, root)


def _vegetation_inputs(root: Path) -> list[Input]:
    trail_json = root / "app" / "public" / "assets" / "generated" / "trail.json"
    return [
        *_dem_inputs(root),
        _osm_input(root),
        raw_input(ortho.ORTHO_SOURCE_ID, ortho.ORTHO_SUFFIX, root),
        *(raw_input(source_id, ".laz", root) for source_id in dem.LIDAR_SOURCE_IDS),
        {"file": relative(trail_json, root), "sha256": sha256_file(trail_json)},
        *(raw_input(m.source_id, m.gltf, root) for m in understory.MODELS),
    ]


def _inputs(kind: str, root: Path) -> list[Input]:
    match kind:
        case "terrain":
            return [
                *_dem_inputs(root),
                _osm_input(root),
                raw_input(ortho.ORTHO_SOURCE_ID, ortho.ORTHO_SUFFIX, root),
                curated_input(root),
            ]
        case "collision" | "trail":
            return [*_dem_inputs(root), _osm_input(root), curated_input(root)]
        case "vegetation":
            return _vegetation_inputs(root)
        case "pine":
            return [raw_input(*source, root) for source in PINE_TEXTURES]
        case "tunnel":
            # the shell is clipped against the carved DEM (run_tunnel), so the DEM is an input
            return [*_dem_inputs(root), _osm_input(root), curated_input(root)]
    raise ProvenanceError(f"unknown artefact kind {kind!r}")


def _tools(kind: str) -> tuple[str, ...]:
    match kind:
        case "terrain":
            return BLENDER_TOOLS
        case "pine":
            return BLENDER_TOOLS
        case "tunnel":
            return ("bpy", "gltf-transform", "node")
        case "collision":
            return ("numpy", "rasterio", "shapely")
        case "vegetation":
            return ("numpy", "rasterio", "shapely", "laspy")
        case _:
            return ("numpy", "shapely")


def provenance(kind: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    """The ``inputs`` and ``tools`` fields of a ``terrain`` / ``collision`` / ``trail`` /
    ``tunnel`` document, read from the files and tools present now."""
    return {"inputs": _inputs(kind, root), "tools": tool_versions(_tools(kind), root)}
