"""Which inputs and tools each generated artefact is made from (the provenance blocks)."""

from pathlib import Path
from typing import Any

from penyal_pipeline import buildings, dem, ortho, trail
from penyal_pipeline.paths import REPO_ROOT, SURFACES_MANIFEST, TRAIL_GENERATED, TUNNEL_CURATED
from penyal_pipeline.provenance import ProvenanceError, relative, sha256_file, tool_versions
from penyal_pipeline.rawdata import locate

type Input = dict[str, str]

BLENDER_TOOLS = ("bpy", "gltf-transform", "ktx", "node")
PLANT_TEXTURES = (
    ("polyhaven-shrub-04-diff-1k", ".jpg"),
    ("polyhaven-shrub-02-diff-1k", ".jpg"),
    ("polyhaven-grass-medium-02-diff-1k", ".jpg"),
)
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
    trail_json = root / TRAIL_GENERATED.relative_to(REPO_ROOT)
    surfaces_manifest = root / SURFACES_MANIFEST.relative_to(REPO_ROOT)
    return [
        *_dem_inputs(root),
        _osm_input(root),
        raw_input(ortho.ORTHO_SOURCE_ID, ortho.ORTHO_SUFFIX, root),
        *(raw_input(source_id, ".laz", root) for source_id in dem.LIDAR_SOURCE_IDS),
        {"file": relative(trail_json, root), "sha256": sha256_file(trail_json)},
        # the surface masks the understory avoids (E1): their manifest fingerprints them
        {"file": relative(surfaces_manifest, root), "sha256": sha256_file(surfaces_manifest)},
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
        case "surfaces":
            return [_osm_input(root)]
        case "collision" | "trail":
            return [*_dem_inputs(root), _osm_input(root), curated_input(root)]
        case "vegetation":
            return _vegetation_inputs(root)
        case "pine":
            return [raw_input(*source, root) for source in PINE_TEXTURES]
        case "plants":
            return [raw_input(*source, root) for source in PLANT_TEXTURES]
        case "buildings":
            # the footprints (OSM), the DEM they stand on and the roof points (the one LiDAR tile)
            return [
                *_dem_inputs(root),
                _osm_input(root),
                raw_input(buildings.LIDAR_SOURCE_ID, ".laz", root),
            ]
        case "tunnel" | "structures":
            # the shell is clipped against the carved DEM (run_tunnel), so the DEM is an input
            return [*_dem_inputs(root), _osm_input(root), curated_input(root)]
    raise ProvenanceError(f"unknown artefact kind {kind!r}")


def _tools(kind: str) -> tuple[str, ...]:
    match kind:
        case "terrain":
            return BLENDER_TOOLS
        case "pine" | "plants":
            return BLENDER_TOOLS
        case "tunnel" | "structures":
            return ("bpy", "gltf-transform", "node")
        case "buildings":
            return ("bpy", "gltf-transform", "node", "numpy", "shapely", "laspy")
        case "collision":
            return ("numpy", "rasterio", "shapely")
        case "surfaces":
            return ("numpy", "ktx")
        case "vegetation":
            return ("numpy", "rasterio", "shapely", "laspy")
        case _:
            return ("numpy", "shapely")


def provenance(kind: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    """The ``inputs`` and ``tools`` fields of a ``terrain`` / ``collision`` / ``trail`` /
    ``tunnel`` document, read from the files and tools present now."""
    return {"inputs": _inputs(kind, root), "tools": tool_versions(_tools(kind), root)}
