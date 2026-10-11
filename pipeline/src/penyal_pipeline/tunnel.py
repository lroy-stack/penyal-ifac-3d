"""Tunnel data (T1.8a): curated portal floors and section, evidence analysis, ``tunnel.json``.

Nothing here is measured on site. ``data/curated/tunnel.toml`` records every approximation with its
method and evidence; ``analyse`` re-derives the evidence numbers from the DEM and the LiDAR so the
file cannot drift from the data (a test compares them). The axis comes from OSM way 26330275
(ODbL), so ``tunnel.json`` carries the ODbL fields like ``trail.json`` (ADR 0007).
"""

import json
import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import laspy
import numpy as np
import numpy.typing as npt
import shapely

from penyal_pipeline import artefacts, dem, tiles, trail
from penyal_pipeline.dem import Grid
from penyal_pipeline.geo import ORIGIN_E, ORIGIN_N
from penyal_pipeline.paths import (
    GENERATED_DIR,
    TUNNEL_BUILD_DIR,
    TUNNEL_CURATED,
    TUNNEL_GLB,
    TUNNEL_JSON,
)
from penyal_pipeline.rawdata import locate
from penyal_pipeline.tunnel_geometry import (
    Carve,
    TerrainFeatures,
    build_shell,
    extend_axis,
    prisms,
)

log = logging.getLogger(__name__)

AXIS_WAY = 26330275
AXIS_SPACING = 0.5  # metres, densification of the axis in tunnel.json
STATUS_APPROXIMATE = "approximate"
LIDAR_GROUND_RADIUS = 2.0  # metres from the approach path
NEAR_RADII = (3.0, 5.0)  # metres from a portal, on its outer side
LIDAR_WINDOW = 70.0  # metres around the tunnel read from the point clouds
DRIFT_TOLERANCE = 0.011  # curated evidence is rounded to centimetres

type Floats = npt.NDArray[np.float64]


class TunnelError(RuntimeError):
    """The curated tunnel file or the data it is checked against is inconsistent."""


@dataclass(frozen=True)
class PortalFloor:
    value: float
    low: float
    high: float
    method: str
    evidence: dict[str, float]


@dataclass(frozen=True)
class CrossSection:
    width: float
    height: float
    width_range: tuple[float, float]
    height_range: tuple[float, float]
    basis: str


@dataclass(frozen=True)
class ApproachCorrection:
    """The ADR 0009 terrain correction at the west approach: its extent and its evidence."""

    half_width: float
    cells: int
    max_lowering: float
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class Curated:
    status: str
    west: PortalFloor
    east: PortalFloor
    section: CrossSection
    ramp_start: float
    east_blend: float
    riser: float
    riser_range: tuple[float, float]
    sources: dict[str, str]
    west_approach: ApproachCorrection

    def trail_spec(self) -> trail.TunnelSpec:
        return trail.TunnelSpec(
            west_floor=self.west.value,
            east_floor=self.east.value,
            width=self.section.width,
            steps_ramp_start=self.ramp_start,
            east_blend=self.east_blend,
        )


def _number(table: dict[str, Any], key: str, where: str) -> float:
    value = table.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TunnelError(f"{where}.{key} must be a number")
    return float(value)


def _range(table: dict[str, Any], key: str, where: str) -> tuple[float, float]:
    value = table.get(key)
    if not (isinstance(value, list) and len(value) == 2):
        raise TunnelError(f"{where}.{key} must be [low, high]")
    low, high = float(value[0]), float(value[1])
    if low > high:
        raise TunnelError(f"{where}.{key} is not ordered")
    return low, high


def _text(table: dict[str, Any], key: str, where: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TunnelError(f"{where}.{key} must be a non-empty string")
    return value


def _portal(table: dict[str, Any], name: str) -> PortalFloor:
    where = f"portals.{name}"
    value = _number(table, "floor_m", where)
    low, high = _range(table, "range_m", where)
    if not low <= value <= high:
        raise TunnelError(f"{where}.floor_m {value} is outside its range [{low}, {high}]")
    evidence = table.get("evidence")
    if not isinstance(evidence, dict) or not evidence:
        raise TunnelError(f"{where}.evidence must list the numbers behind the value")
    return PortalFloor(
        value=value,
        low=low,
        high=high,
        method=_text(table, "method", where),
        evidence={str(k): _number(evidence, k, f"{where}.evidence") for k in evidence},
    )


def _positive(table: dict[str, Any], key: str, where: str) -> float:
    value = _number(table, key, where)
    if value <= 0.0:
        raise TunnelError(f"{where}.{key} must be positive")
    return value


def _correction(raw: dict[str, Any]) -> ApproachCorrection:
    where = "corrections.west_approach"
    table = raw.get("corrections", {}).get("west_approach")
    if not isinstance(table, dict):
        raise TunnelError(f"{where} is missing: ADR 0009 requires the correction to be recorded")
    cells = table.get("cells")
    if isinstance(cells, bool) or not isinstance(cells, int) or cells <= 0:
        raise TunnelError(f"{where}.cells must be a positive integer")
    evidence = table.get("evidence")
    if not (
        isinstance(evidence, list)
        and evidence
        and all(isinstance(item, str) and item.strip() for item in evidence)
    ):
        raise TunnelError(f"{where}.evidence must list the evidence references")
    return ApproachCorrection(
        half_width=_positive(table, "half_width_m", where),
        cells=cells,
        max_lowering=_positive(table, "max_lowering_m", where),
        evidence=tuple(evidence),
    )


def load_curated(path: Path = TUNNEL_CURATED) -> Curated:
    """Read and validate ``data/curated/tunnel.toml``."""
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TunnelError(f"{path} is missing") from exc
    status = _text(raw, "status", "tunnel")
    if status != STATUS_APPROXIMATE:
        raise TunnelError(f"status must be {STATUS_APPROXIMATE!r} until measured (got {status!r})")
    approach = raw.get("approach", {})
    section = raw.get("section", {})
    portals = raw.get("portals", {})
    section_data = CrossSection(
        width=_number(section, "width_m", "section"),
        height=_number(section, "height_m", "section"),
        width_range=_range(section, "width_range_m", "section"),
        height_range=_range(section, "height_range_m", "section"),
        basis=_text(section, "basis", "section"),
    )
    for label, value, (low, high) in (
        ("width", section_data.width, section_data.width_range),
        ("height", section_data.height, section_data.height_range),
    ):
        if not low <= value <= high:
            raise TunnelError(f"section.{label} {value} is outside its range [{low}, {high}]")
    sources = raw.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise TunnelError("sources must list where the numbers come from")
    return Curated(
        status=status,
        west=_portal(portals.get("west", {}), "west"),
        east=_portal(portals.get("east", {}), "east"),
        section=section_data,
        ramp_start=_number(approach, "steps_ramp_start_m", "approach"),
        east_blend=_number(approach, "east_blend_m", "approach"),
        riser=_number(approach, "riser_m", "approach"),
        riser_range=_range(approach, "riser_range_m", "approach"),
        sources={str(k): str(v) for k, v in sources.items()},
        west_approach=_correction(raw),
    )


# --- evidence ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class LidarPoints:
    """LiDAR returns in the local frame with their ASPRS class."""

    x: Floats
    z: Floats
    y: Floats
    classification: npt.NDArray[np.int_]


def load_lidar(centre: tuple[float, float], window: float = LIDAR_WINDOW) -> LidarPoints:
    """Returns within ``window`` metres of ``centre``, noise removed (see ``dem``)."""
    parts: list[LidarPoints] = []
    for path in dem.lidar_paths():
        las = laspy.read(path)
        x = np.asarray(las.x, dtype=np.float64) - ORIGIN_E
        z = -(np.asarray(las.y, dtype=np.float64) - ORIGIN_N)
        y = np.asarray(las.z, dtype=np.float64)
        keep = (
            (np.abs(x - centre[0]) <= window)
            & (np.abs(z - centre[1]) <= window)
            & (y >= dem.LIDAR_NOISE_RANGE[0])
            & (y <= dem.LIDAR_NOISE_RANGE[1])
        )
        parts.append(LidarPoints(x[keep], z[keep], y[keep], np.asarray(las.classification)[keep]))
    return LidarPoints(
        np.concatenate([p.x for p in parts]),
        np.concatenate([p.z for p in parts]),
        np.concatenate([p.y for p in parts]),
        np.concatenate([p.classification for p in parts]),
    )


def _near_path(
    lidar: LidarPoints,
    path_xz: Floats,
    ground_only: bool,
    behind: tuple[Floats, Floats] | None = None,
) -> Floats:
    """Heights of returns within ``LIDAR_GROUND_RADIUS`` of the path.

    ``behind`` is a portal and its outward vector: returns on the tunnel side of the portal are
    dropped (they are rock above the tunnel, not the approach).
    """
    distance = shapely.distance(shapely.LineString(path_xz), shapely.points(lidar.x, lidar.z))
    chosen = distance <= LIDAR_GROUND_RADIUS
    if behind is not None:
        portal, outward = behind
        chosen &= (lidar.x - portal[0]) * outward[0] + (lidar.z - portal[1]) * outward[1] >= 0.0
    if ground_only:
        chosen &= lidar.classification == dem.LIDAR_GROUND_CLASS
    return lidar.y[chosen]


def _outside_returns(
    lidar: LidarPoints, portal: Floats, outward: Floats, radius: float, ground_only: bool
) -> Floats:
    dx, dz = lidar.x - portal[0], lidar.z - portal[1]
    chosen = (np.hypot(dx, dz) <= radius) & (dx * outward[0] + dz * outward[1] >= 0.0)
    if ground_only:
        chosen &= lidar.classification == dem.LIDAR_GROUND_CLASS
    return lidar.y[chosen]


def _stretch(path_xz: Floats, length: float, from_end: bool) -> Floats:
    """The part of a 0.5 m densified ``path_xz`` within ``length`` metres of its start (or end)."""
    path = trail.densify(path_xz, AXIS_SPACING)
    ordered = path[::-1] if from_end else path
    along = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(ordered, axis=0), axis=1))])
    return ordered[along <= length + 1e-9]


def _require(values: Floats, what: str) -> Floats:
    if values.size == 0:
        raise TunnelError(f"no samples for {what}: the data does not cover the portal")
    return values


def _stat(values: Floats, fn: str) -> float:
    return round(float(getattr(np, fn)(_require(values, fn))), 2)


def west_evidence(
    grid: Grid,
    lidar: LidarPoints,
    steps_xz: Floats,
    portal: Floats,
    outward: Floats,
    step_count: int,
    curated: Curated,
) -> dict[str, float]:
    """Numbers behind the west floor: approach + steps, and the lowest returns by the portal."""
    approach = _stretch(steps_xz, curated.ramp_start, from_end=False)
    dem_values = grid.sample(approach[:, 0], approach[:, 1])
    ground = _require(_near_path(lidar, approach, ground_only=True), "the approach ground")
    rise = step_count * curated.riser
    mid = (float(np.median(dem_values)) + float(np.median(ground))) / 2.0
    evidence = {
        "dem_at_portal": _stat(grid.sample([portal[0]], [portal[1]]), "median"),
        "approach_dem_min": _stat(dem_values, "min"),
        "approach_dem_median": _stat(dem_values, "median"),
        "approach_dem_max": _stat(dem_values, "max"),
        "approach_lidar_ground_count": float(ground.size),
        "approach_lidar_ground_median": _stat(ground, "median"),
        "approach_lidar_ground_p90": round(float(np.percentile(ground, 90)), 2),
        "step_count": float(step_count),
        "steps_rise": round(rise, 2),
        "approach_plus_steps": round(mid + rise, 2),
    }
    for radius in NEAR_RADII:
        returns = _outside_returns(lidar, portal, outward, radius, ground_only=False)
        evidence[f"lowest_return_within_{radius:.0f}m"] = _stat(returns, "min")
    return evidence


def east_evidence(
    grid: Grid,
    lidar: LidarPoints,
    exit_xz: Floats,
    portal: Floats,
    outward: Floats,
    curated: Curated,
) -> dict[str, float]:
    """Numbers behind the east floor: the DEM and the LiDAR along the path leaving the portal."""
    leaving = _stretch(exit_xz, curated.east_blend, from_end=False)
    dem_values = grid.sample(leaving[:, 0], leaving[:, 1])
    ground = _near_path(lidar, leaving, ground_only=True, behind=(portal, outward))
    everything = _near_path(lidar, leaving, ground_only=False, behind=(portal, outward))
    outside = _outside_returns(lidar, portal, outward, NEAR_RADII[0], ground_only=True)
    return {
        "dem_at_portal": _stat(grid.sample([portal[0]], [portal[1]]), "median"),
        "exit_dem_min": _stat(dem_values, "min"),
        "exit_dem_median": _stat(dem_values, "median"),
        "exit_dem_max": _stat(dem_values, "max"),
        "exit_lidar_ground_median": _stat(ground, "median"),
        "exit_lidar_all_median": _stat(everything, "median"),
        "outside_ground_median_within_3m": _stat(outside, "median"),
    }


@dataclass(frozen=True)
class Analysis:
    west: dict[str, float]
    east: dict[str, float]


def _spec(specs: tuple[trail.SegmentSpec, ...], segment_id: str) -> trail.SegmentSpec:
    return next(s for s in specs if s.id == segment_id)


def _outward(line: Floats, at_start: bool) -> Floats:
    vector = line[0] - line[1] if at_start else line[-1] - line[-2]
    return vector / np.linalg.norm(vector)


def analyse(osm: trail.OsmData, grid: Grid, lidar: LidarPoints, curated: Curated) -> Analysis:
    """Re-derive the evidence of both portals from the DEM and the LiDAR."""
    specs = trail.SEGMENT_SPECS
    tunnel_xz = trail.segment_polyline_2d(osm, _spec(specs, trail.TUNNEL_SEGMENT))
    steps_xz = trail.segment_polyline_2d(osm, _spec(specs, trail.PORTAL_STEPS_SEGMENT))
    exit_xz = trail.segment_polyline_2d(osm, _spec(specs, trail.EXIT_SEGMENT))
    steps_tag = osm.ways[_spec(specs, trail.PORTAL_STEPS_SEGMENT).way].tags.get("step_count")
    if steps_tag is None or not steps_tag.isdigit():
        raise TunnelError("the OSM steps way has no numeric step_count tag")
    return Analysis(
        west=west_evidence(
            grid,
            lidar,
            steps_xz,
            tunnel_xz[0],
            _outward(tunnel_xz, at_start=True),
            int(steps_tag),
            curated,
        ),
        east=east_evidence(
            grid, lidar, exit_xz, tunnel_xz[-1], _outward(tunnel_xz, at_start=False), curated
        ),
    )


def analyse_data(curated: Curated) -> Analysis:
    """``analyse`` on the real OSM extract, ``build/terrain`` DEM and the 2016 LiDAR."""
    osm = trail.load_osm(locate(trail.OSM_SOURCE_ID, trail.OSM_FILE).path)
    grid, _ = dem.load_dem()
    tunnel_xz = trail.segment_polyline_2d(osm, _spec(trail.SEGMENT_SPECS, trail.TUNNEL_SEGMENT))
    centre = tunnel_xz.mean(axis=0)
    return analyse(osm, grid, load_lidar((float(centre[0]), float(centre[1]))), curated)


def evidence_drift(curated: Curated, analysis: Analysis) -> list[str]:
    """Differences between the evidence recorded in the toml and the recomputed numbers."""
    problems: list[str] = []
    for name, recorded, fresh in (
        ("west", curated.west.evidence, analysis.west),
        ("east", curated.east.evidence, analysis.east),
    ):
        for key in sorted(set(recorded) | set(fresh)):
            if key not in recorded or key not in fresh:
                problems.append(f"{name}.{key}: present in only one of toml / analysis")
            elif abs(recorded[key] - fresh[key]) > DRIFT_TOLERANCE:
                problems.append(f"{name}.{key}: toml {recorded[key]} vs data {fresh[key]}")
    return problems


# --- axis, document, terrain features ------------------------------------------------------------


def axis_corners(osm: trail.OsmData, curated: Curated) -> Floats:
    """OSM tunnel vertices west to east with their floor heights: ``(n, 3)`` local x, y, z."""
    xz = trail.segment_polyline_2d(osm, _spec(trail.SEGMENT_SPECS, trail.TUNNEL_SEGMENT))
    floor = trail.tunnel_heights(xz, curated.west.value, curated.east.value)
    return np.column_stack([xz[:, 0], floor, xz[:, 1]])


def axis_points(osm: trail.OsmData, curated: Curated) -> Floats:
    """The densified axis (spacing <= 0.5 m, OSM vertices kept) with its linear floor heights."""
    xz = trail.densify(
        trail.segment_polyline_2d(osm, _spec(trail.SEGMENT_SPECS, trail.TUNNEL_SEGMENT)),
        AXIS_SPACING,
    )
    floor = trail.tunnel_heights(xz, curated.west.value, curated.east.value)
    return np.column_stack([xz[:, 0], floor, xz[:, 1]])


def floor_slope_degrees(axis: Floats) -> float:
    """Mean floor slope between the portals, from the horizontal path length."""
    horizontal = float(np.sum(np.linalg.norm(np.diff(axis[:, [0, 2]], axis=0), axis=1)))
    return float(np.degrees(np.arctan2(axis[-1, 1] - axis[0, 1], horizontal)))


def _round_point(point: Floats) -> list[float]:
    return [round(float(v), 3) for v in point]


def build_document(osm: trail.OsmData, curated: Curated, osm_sha256: str) -> dict[str, Any]:
    """The ``tunnel.json`` contract of the F1 plan (version 1)."""
    axis = axis_points(osm, curated)
    west, east = axis[0], axis[-1]
    return {
        "version": 1,
        "licence": trail.LICENCE,
        "attribution": trail.ATTRIBUTION,
        "status": curated.status,
        "axis": [_round_point(p) for p in axis],
        "width": curated.section.width,
        "height": curated.section.height,
        "sectionBasis": curated.section.basis,
        "portals": {
            "west": dict(zip("xyz", _round_point(west), strict=True)),
            "east": dict(zip("xyz", _round_point(east), strict=True)),
        },
        "sources": {
            "axis": f"osm:way/{AXIS_WAY}",
            "portalHeights": "data/curated/tunnel.toml",
        },
        "mesh": TUNNEL_GLB,
        "source": {"id": trail.OSM_SOURCE_ID, "sha256": osm_sha256},
        **artefacts.provenance("tunnel"),
    }


def write_document(document: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, separators=(",", ":"), ensure_ascii=False) + "\n", "utf-8")
    log.info("wrote %s (%d bytes)", out, out.stat().st_size)


def terrain_features(osm: trail.OsmData, grid: Grid, curated: Curated) -> TerrainFeatures:
    """The carved west approach and the cut volumes (tunnel plus ``OVERRUN`` at each portal)."""
    specs = trail.SEGMENT_SPECS
    tunnel_xz = trail.segment_polyline_2d(osm, _spec(specs, trail.TUNNEL_SEGMENT))
    steps_xz = trail.densify(
        trail.segment_polyline_2d(osm, _spec(specs, trail.PORTAL_STEPS_SEGMENT))
    )
    steps_y = trail.steps_heights(steps_xz, grid, curated.west.value, curated.ramp_start)
    along = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(steps_xz, axis=0), axis=1))])
    climb = along >= curated.ramp_start
    path = np.column_stack([steps_xz[climb, 0], steps_y[climb], steps_xz[climb, 1]])
    carve = Carve(
        path=path,
        half_width=curated.west_approach.half_width,
        portal=tunnel_xz[0],
        outward=_outward(tunnel_xz, at_start=True),
    )
    corners = extend_axis(axis_corners(osm, curated))
    return TerrainFeatures(
        carve=carve,
        openings=prisms(corners, curated.section.width, curated.section.height),
    )


def load_terrain_features() -> TerrainFeatures:
    """``terrain_features`` from the committed curated file, the OSM extract and ``build/``."""
    osm = trail.load_osm(locate(trail.OSM_SOURCE_ID, trail.OSM_FILE).path)
    grid, _ = dem.load_dem()
    return terrain_features(osm, grid, load_curated())


# --- build -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class TunnelReport:
    document: dict[str, Any]
    json_bytes: int
    glb_bytes: int
    shell_triangles: int
    slope_degrees: float
    tiles: list[tiles.TileKey]
    tile_bytes: int
    tile_triangles: int


def run_tunnel(
    out_dir: Path = GENERATED_DIR,
    build_dir: Path = TUNNEL_BUILD_DIR,
    with_tiles: bool = True,
) -> TunnelReport:
    """Write ``tunnel.json`` and ``tunnel.glb`` into ``out_dir`` and re-export the tiles it cuts.

    The tiles are rebuilt in ``out_dir / "terrain"``, whose ``manifest.json`` must already exist
    (it is updated in place, the other tiles and the far mesh are not touched).
    """
    from penyal_pipeline.blender import tunnel as blender_tunnel

    curated = load_curated()
    raw = locate(trail.OSM_SOURCE_ID, trail.OSM_FILE)
    osm = trail.load_osm(raw.path)
    grid, _ = dem.load_dem()
    document = build_document(osm, curated, raw.sha256)
    write_document(document, out_dir / TUNNEL_JSON)

    axis = extend_axis(axis_points(osm, curated))
    shell = build_shell(axis, curated.section.width, curated.section.height)
    build_dir.mkdir(parents=True, exist_ok=True)
    raw_glb = blender_tunnel.export_tunnel(shell, build_dir / TUNNEL_GLB)
    glb_bytes = tiles.optimize_glb(raw_glb, out_dir / TUNNEL_GLB, None)

    features = terrain_features(osm, grid, curated)
    affected = tiles.tiles_touching(features.bounds) if with_tiles else []
    tile_bytes = tile_triangles = 0
    if affected:
        report = tiles.run_terrain(
            out_dir=out_dir / "terrain",
            build_dir=build_dir / "tiles",
            tiles=affected,
            include_far=False,
            features=features,
            update_manifest=True,
        )
        wanted = {tiles.tile_id(i, j) for i, j in affected}
        for tile in report.manifest["near"]["tiles"]:
            if tile["id"] in wanted:
                tile_bytes += sum(lod["bytes"] for lod in tile["lods"])
                tile_triangles += sum(lod["triangles"] for lod in tile["lods"])
    return TunnelReport(
        document=document,
        json_bytes=(out_dir / TUNNEL_JSON).stat().st_size,
        glb_bytes=glb_bytes,
        shell_triangles=int(shell.triangles.shape[0]),
        slope_degrees=floor_slope_degrees(axis_points(osm, curated)),
        tiles=affected,
        tile_bytes=tile_bytes,
        tile_triangles=tile_triangles,
    )
