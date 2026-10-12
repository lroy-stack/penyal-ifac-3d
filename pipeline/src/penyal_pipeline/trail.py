"""Ruta Roja trail, walkable corridor and anchors from the OSM extract (ADR 0004, 0006, 0007).

``build_trail`` produces the JSON document written to ``app/public/assets/generated/trail.json``.
It is derived from OpenStreetMap data (ODbL 1.0) and must stay a separate file; the heights come
from the ICV DEM, draped on the path except around and inside the tunnel, where they come from
the curated portal floors (``data/curated/tunnel.toml``, approximate). Corridor polygon rings are
exterior-only, counter-clockwise in the (x, z) plane, and do not repeat the first vertex.
"""

import itertools
import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient
from shapely.ops import nearest_points, polygonize, substring, unary_union

from penyal_pipeline.dem import Grid
from penyal_pipeline.geo import to_local_array, wgs84_to_25830_array
from penyal_pipeline.rawdata import locate

log = logging.getLogger(__name__)

OSM_SOURCE_ID = "osm-penyal"
OSM_FILE = "osm-penyal.json"
LICENCE = "ODbL-1.0"
ATTRIBUTION = "© OpenStreetMap contributors"

MAX_STEP = 1.0  # densification spacing, metres
TRAIL_HALF_WIDTH = 3.0
FORECOURT_RADIUS = 15.0
SUMMIT_RADIUS = 10.0
CARABINERS_RADIUS = 8.0
VIEWPOINT_RADIUS = 6.0
VIEWPOINT_MAX_TRAIL_DISTANCE = 25.0
SIMPLIFY_TOLERANCE = 0.25
WALKABLE_MARGIN = 30.0
CAPSULE_RADIUS = 0.3  # player capsule: the tunnel corridor keeps this clear of each wall
TUNNEL_STRIP_OVERLAP = (
    0.5  # the tunnel strip reaches this far past the portals to fuse with the rest
)

CENTRE_BUILDING_WAY = 26330271
ANNEX_BUILDING_WAY = 26330272
# Modelled as solid volumes by `penyal buildings` (no collision mesh): the corridor keeps the
# capsule clear of their walls, so it is their collision.
SOLID_BUILDING_WAYS = (CENTRE_BUILDING_WAY, ANNEX_BUILDING_WAY)
# Approximation: the `centre` anchor stands this far in front of the wall, towards the trail, so
# the player does not start touching it. The door position is unknown until the user's photos.
CENTRE_ANCHOR_CLEARANCE = 1.0
POBLA_WAY = 1159140951
TURNSTILE_NODE = 8032598828
TUNNEL_WEST_NODE = 288471873
TUNNEL_EAST_NODE = 288471874
BIFURCATION_NODE = 288472006
SUMMIT_NODE = 409151051
CARABINERS_NODE = 288472096
TUNNEL_SEGMENT = "tunnel"
PORTAL_STEPS_SEGMENT = "portal-steps"
EXIT_SEGMENT = "tunnel-bifurcation"

type Array2 = npt.NDArray[np.float64]


class TrailError(RuntimeError):
    """The OSM extract does not describe the expected route."""


@dataclass(frozen=True)
class TunnelSpec:
    """Curated tunnel inputs of the trail (``data/curated/tunnel.toml``, all approximate)."""

    west_floor: float  # metres, floor height at the west portal
    east_floor: float  # metres, floor height at the east portal
    width: float  # metres, cross-section width
    steps_ramp_start: float  # metres along portal-steps where the climb to the west floor starts
    east_blend: float  # metres along tunnel-bifurcation over which the DEM is blended to the floor

    @property
    def corridor_half_width(self) -> float:
        return self.width / 2.0 - CAPSULE_RADIUS


@dataclass(frozen=True)
class SegmentSpec:
    id: str
    name: str
    way: int
    start: int
    end: int


# Walking order. The Carabiners branch starts at the bifurcation, where "summit-ascent" starts too.
SEGMENT_SPECS: tuple[SegmentSpec, ...] = (
    SegmentSpec(
        "access", "Access path from the Centre d'Informació", 26330270, 1795591680, 288471763
    ),
    SegmentSpec(
        "centre-steps", "Centre steps (30 steps, handrail)", 26330269, 288471763, 288471765
    ),
    SegmentSpec(
        "centre-path", "Path from the Centre to the tunnel", 26330273, 288471765, 8032598845
    ),
    SegmentSpec(
        "portal-steps", "Steps to the west portal", 862108208, 8032598845, TUNNEL_WEST_NODE
    ),
    SegmentSpec(TUNNEL_SEGMENT, "Tunnel", 26330275, TUNNEL_WEST_NODE, TUNNEL_EAST_NODE),
    SegmentSpec(
        "tunnel-bifurcation",
        "Tunnel to the bifurcation",
        26330276,
        TUNNEL_EAST_NODE,
        BIFURCATION_NODE,
    ),
    SegmentSpec(
        "summit-ascent", "Bifurcation to the summit", 34887788, BIFURCATION_NODE, SUMMIT_NODE
    ),
    SegmentSpec(
        "carabiners-branch",
        "Bifurcation to the Mirador de Carabiners",
        26330276,
        BIFURCATION_NODE,
        288472082,
    ),
)


# Outer members of relation/2172136 (Parc Natural del Penyal d'Ifac).
PARK_BOUNDARY_WAYS = (26330277, 162335453)
PARK_RELATION = 2172136
STEPS_FOOT_NODE = 288471763
# Walking access from the foot of the centre steps down to the park boundary on the Avinguda de
# l'Illa de Formentera: two footways, the service track closed to motor vehicles (gate
# node/288471681) and the avenue. Not part of the Ruta Roja: it only widens the corridor so the
# walk reaches the park entrance.
ACCESS_SPECS = (
    SegmentSpec(
        "access-footway", "Footway below the centre steps", 26330270, STEPS_FOOT_NODE, 1795591680
    ),
    SegmentSpec(
        "access-footway-2", "Footway to the service track", 862108209, 1795591680, 288471757
    ),
    SegmentSpec("access-track", "Service track (cobbled)", 862108206, 288471757, 1795591774),
    SegmentSpec("access-track-2", "Service track to the gate", 37656546, 1795591774, 288471681),
    SegmentSpec(
        "access-track-3", "Service track below the gate", 1159140950, 288471681, 8032598839
    ),
    SegmentSpec(
        "access-avenue", "Avinguda de l'Illa de Formentera", 37656545, 8032598839, 441403801
    ),
)


@dataclass(frozen=True)
class Way:
    nodes: tuple[int, ...]
    tags: dict[str, str]


@dataclass(frozen=True)
class OsmData:
    """OSM nodes projected to the local frame (``xz`` = x, z) plus ways."""

    xz: dict[int, tuple[float, float]]
    node_tags: dict[int, dict[str, str]]
    ways: dict[int, Way]


def load_osm(path: Path) -> OsmData:
    raw = json.loads(path.read_text(encoding="utf-8"))
    nodes = [e for e in raw["elements"] if e["type"] == "node"]
    e, n = wgs84_to_25830_array([v["lat"] for v in nodes], [v["lon"] for v in nodes])
    x, _, z = to_local_array(e, n)
    xz = {int(v["id"]): (float(x[i]), float(z[i])) for i, v in enumerate(nodes)}
    node_tags = {int(v["id"]): dict(v["tags"]) for v in nodes if "tags" in v}
    ways = {
        int(w["id"]): Way(tuple(int(i) for i in w["nodes"]), dict(w.get("tags", {})))
        for w in raw["elements"]
        if w["type"] == "way"
    }
    return OsmData(xz=xz, node_tags=node_tags, ways=ways)


def slice_way(way_nodes: tuple[int, ...], start: int, end: int) -> list[int]:
    """Node ids of ``way_nodes`` from ``start`` to ``end``, reversing the way if needed."""
    try:
        i, j = way_nodes.index(start), way_nodes.index(end)
    except ValueError as exc:
        raise TrailError(f"nodes {start} and {end} are not both on the way: {exc}") from exc
    return list(way_nodes[i : j + 1]) if i <= j else list(way_nodes[j : i + 1][::-1])


def segment_nodes(osm: OsmData, spec: SegmentSpec) -> list[int]:
    way = osm.ways.get(spec.way)
    if way is None:
        raise TrailError(f"way {spec.way} ({spec.id}) is missing from the OSM extract")
    return slice_way(way.nodes, spec.start, spec.end)


def segment_polyline_2d(osm: OsmData, spec: SegmentSpec) -> Array2:
    return np.array([osm.xz[n] for n in segment_nodes(osm, spec)], dtype=np.float64)


def polygon_centroid(osm: OsmData, way_id: int) -> tuple[float, float]:
    way = osm.ways.get(way_id)
    if way is None:
        raise TrailError(f"way {way_id} is missing from the OSM extract")
    centroid = Polygon([osm.xz[n] for n in way.nodes]).centroid
    return float(centroid.x), float(centroid.y)


def densify(points: Array2, max_step: float = MAX_STEP) -> Array2:
    """Insert evenly spaced points so that no step exceeds ``max_step``; vertices are kept."""
    out: list[Array2] = [points[:1]]
    for a, b in itertools.pairwise(points):
        pieces = max(1, math.ceil(float(np.hypot(*(b - a))) / max_step))
        t = np.arange(1, pieces + 1, dtype=np.float64)[:, None] / pieces
        out.append(a + (b - a) * t)
    return np.vstack(out)


def path_length(points: npt.NDArray[np.float64]) -> float:
    return float(np.sum(np.linalg.norm(np.diff(points, axis=0), axis=1)))


def ascent(heights: npt.NDArray[np.float64]) -> float:
    return float(np.sum(np.clip(np.diff(heights), 0.0, None)))


def drape(dem: Grid, xz: Array2) -> npt.NDArray[np.float64]:
    return dem.sample(xz[:, 0], xz[:, 1])


def _along(xz: Array2) -> npt.NDArray[np.float64]:
    return np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(xz, axis=0), axis=1))])


def tunnel_heights(xz: Array2, west: float, east: float) -> npt.NDArray[np.float64]:
    """Floor heights linear in path distance between the curated portal floors."""
    along = _along(xz)
    return west + (east - west) * (along / along[-1])


def steps_heights(
    xz: Array2, dem: Grid, west_floor: float, ramp_start: float
) -> npt.NDArray[np.float64]:
    """Draped DEM up to ``ramp_start`` metres, then a straight climb to the west portal floor.

    The DEM beside the west portal is the rock wall, 4-11 m above the footpath, so only the
    approach is draped; the last stretch (the 6 steps and the ramp before them) reaches the
    curated floor linearly. The path ends exactly at ``west_floor``.
    """
    along = _along(xz)
    if not 0.0 < ramp_start < along[-1]:
        raise TrailError(f"steps ramp start {ramp_start} m is outside the {along[-1]:.1f} m path")
    draped = drape(dem, xz)
    start_height = float(np.interp(ramp_start, along, draped))
    ramp = start_height + (west_floor - start_height) * (along - ramp_start) / (
        along[-1] - ramp_start
    )
    return np.where(along <= ramp_start, draped, ramp)


def exit_heights(xz: Array2, dem: Grid, east_floor: float, blend: float) -> npt.NDArray[np.float64]:
    """Draped DEM whose offset from the east portal floor fades out over ``blend`` metres."""
    draped = drape(dem, xz)
    fade = np.clip(1.0 - _along(xz) / blend, 0.0, 1.0)
    return draped + (east_floor - draped[0]) * fade


def segment_heights(
    spec: SegmentSpec, xz: Array2, dem: Grid, tunnel: TunnelSpec
) -> npt.NDArray[np.float64]:
    if spec.id == TUNNEL_SEGMENT:
        return tunnel_heights(xz, tunnel.west_floor, tunnel.east_floor)
    if spec.id == PORTAL_STEPS_SEGMENT:
        return steps_heights(xz, dem, tunnel.west_floor, tunnel.steps_ramp_start)
    if spec.id == EXIT_SEGMENT:
        return exit_heights(xz, dem, tunnel.east_floor, tunnel.east_blend)
    return drape(dem, xz)


def build_segments(osm: OsmData, dem: Grid, tunnel: TunnelSpec) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for spec in SEGMENT_SPECS:
        xz = densify(segment_polyline_2d(osm, spec))
        y = segment_heights(spec, xz, dem, tunnel)
        xyz = np.column_stack([xz[:, 0], y, xz[:, 1]])
        segments.append(
            {
                "id": spec.id,
                "name": spec.name,
                "osmWays": [spec.way],
                "points": [[round(float(v), 3) for v in p] for p in xyz],
                "length2d": round(path_length(xz), 2),
                "length3d": round(path_length(xyz), 2),
                "ascent": round(ascent(y), 2),
            }
        )
    return segments


def route_lines_2d(osm: OsmData) -> list[Array2]:
    return [segment_polyline_2d(osm, spec) for spec in SEGMENT_SPECS]


def centre_entrance(osm: OsmData, trail: BaseGeometry) -> tuple[float, float]:
    """Point of the Centre d'Informació footprint closest to the trail.

    The forecourt disc and the ``centre`` anchor sit here: the footprint centroid is more than
    18 m from the trail, so a disc around it would not connect to the corridor.
    """
    way = osm.ways.get(CENTRE_BUILDING_WAY)
    if way is None:
        raise TrailError(f"way {CENTRE_BUILDING_WAY} is missing from the OSM extract")
    footprint = LineString([osm.xz[n] for n in way.nodes])
    nearest = nearest_points(footprint, trail)[0]
    return float(nearest.x), float(nearest.y)


def centre_anchor_point(osm: OsmData, trail: BaseGeometry) -> tuple[float, float]:
    """``CENTRE_ANCHOR_CLEARANCE`` in front of the entrance point, on the way to the trail.

    The straight line from the nearest wall point to the trail never re-enters the footprint, so
    the point keeps that distance from the wall.
    """
    entrance = Point(centre_entrance(osm, trail))
    toward = nearest_points(entrance, trail)[1]
    dx, dz = toward.x - entrance.x, toward.y - entrance.y
    length = math.hypot(dx, dz)
    if length <= CENTRE_ANCHOR_CLEARANCE:
        return float(toward.x), float(toward.y)
    step = CENTRE_ANCHOR_CLEARANCE / length
    return float(entrance.x + dx * step), float(entrance.y + dz * step)


def solid_building_clearance(osm: OsmData) -> BaseGeometry:
    """Footprints of ``SOLID_BUILDING_WAYS`` grown by the capsule radius (mitred corners)."""
    footprints: list[BaseGeometry] = []
    for way_id in SOLID_BUILDING_WAYS:
        way = osm.ways.get(way_id)
        if way is None:
            raise TrailError(f"way {way_id} is missing from the OSM extract")
        footprint = Polygon([osm.xz[n] for n in way.nodes])
        footprints.append(footprint.buffer(CAPSULE_RADIUS, join_style="mitre"))
    return unary_union(footprints)


def park_polygon(osm: OsmData) -> Polygon:
    """The park area closed by ``PARK_BOUNDARY_WAYS`` (relation/2172136)."""
    lines: list[LineString] = []
    for way_id in PARK_BOUNDARY_WAYS:
        way = osm.ways.get(way_id)
        if way is None:
            raise TrailError(f"park boundary way {way_id} is missing from the OSM extract")
        lines.append(LineString([osm.xz[n] for n in way.nodes]))
    polygons = list(polygonize(unary_union(lines)))
    if not polygons:
        raise TrailError(f"the boundary ways of relation/{PARK_RELATION} do not close a polygon")
    return max(polygons, key=lambda p: p.area)


def access_line(osm: OsmData) -> LineString:
    """The ``ACCESS_SPECS`` chain from the foot of the centre steps, cut at the park boundary."""
    coords: list[tuple[float, float]] = []
    for spec in ACCESS_SPECS:
        part = [osm.xz[n] for n in segment_nodes(osm, spec)]
        coords.extend(part if not coords else part[1:])
    line = LineString(coords)
    crossings = line.intersection(park_polygon(osm).exterior)
    if crossings.is_empty:
        raise TrailError("the access chain never reaches the park boundary")
    points = getattr(crossings, "geoms", [crossings])
    exit_at = min(line.project(p) for p in points if p.geom_type == "Point")
    cut = substring(line, 0.0, exit_at)
    if not isinstance(cut, LineString):
        raise TrailError("the access chain leaves the park at its first vertex")
    return cut


def park_entrance(osm: OsmData) -> tuple[float, float]:
    """Where the access chain crosses the park boundary."""
    x, z = access_line(osm).coords[-1]
    return float(x), float(z)


def route_geometry(osm: OsmData) -> BaseGeometry:
    return unary_union([LineString(line) for line in route_lines_2d(osm)])


def _disc(centre: tuple[float, float], radius: float) -> Polygon:
    return Point(centre).buffer(radius, quad_segs=16)


def select_viewpoints(osm: OsmData, trail: BaseGeometry) -> list[int]:
    """``tourism=viewpoint`` nodes within 25 m of the trail, excluding the Carabiners one."""
    return sorted(
        node
        for node, tags in osm.node_tags.items()
        if tags.get("tourism") == "viewpoint"
        and node != CARABINERS_NODE
        and Point(osm.xz[node]).distance(trail) <= VIEWPOINT_MAX_TRAIL_DISTANCE
    )


def _tunnel_line(osm: OsmData) -> Array2:
    spec = next(s for s in SEGMENT_SPECS if s.id == TUNNEL_SEGMENT)
    return segment_polyline_2d(osm, spec)


def _tunnel_strip(line: Array2, half_width: float) -> BaseGeometry:
    """The tunnel corridor: flat-capped, reaching ``TUNNEL_STRIP_OVERLAP`` past each portal."""
    head = line[0] - line[1]
    tail = line[-1] - line[-2]
    extended = np.vstack(
        [
            line[0] + head / np.linalg.norm(head) * TUNNEL_STRIP_OVERLAP,
            line,
            line[-1] + tail / np.linalg.norm(tail) * TUNNEL_STRIP_OVERLAP,
        ]
    )
    return LineString(extended).buffer(half_width, cap_style="flat", quad_segs=8)


def build_corridor(osm: OsmData, tunnel: TunnelSpec | None = None) -> tuple[Polygon, list[int]]:
    """Corridor polygon (ADR 0006) and the viewpoint node ids that were added to it.

    With ``tunnel`` the corridor inside the tunnel is the tunnel width minus the capsule radius
    on each side; everything else keeps ``TRAIL_HALF_WIDTH``. The wide buffers are cut at the
    portal planes so they do not spill into the tunnel.
    """
    trail = route_geometry(osm)
    viewpoints = select_viewpoints(osm, trail)
    if tunnel is None:
        wide_lines: BaseGeometry = trail
    else:
        wide_lines = unary_union(
            [
                LineString(segment_polyline_2d(osm, spec))
                for spec in SEGMENT_SPECS
                if spec.id != TUNNEL_SEGMENT
            ]
        )
    parts: list[BaseGeometry] = [
        wide_lines.buffer(TRAIL_HALF_WIDTH, quad_segs=8),
        access_line(osm).buffer(TRAIL_HALF_WIDTH, quad_segs=8),
        _disc(centre_entrance(osm, trail), FORECOURT_RADIUS),
        _disc(osm.xz[SUMMIT_NODE], SUMMIT_RADIUS),
        _disc(osm.xz[CARABINERS_NODE], CARABINERS_RADIUS),
        *(_disc(osm.xz[n], VIEWPOINT_RADIUS) for n in viewpoints),
    ]
    merged = unary_union(parts)
    if tunnel is None:
        merged = merged.simplify(SIMPLIFY_TOLERANCE, preserve_topology=True)
    else:
        line = _tunnel_line(osm)
        zone = LineString(line).buffer(TRAIL_HALF_WIDTH + 1.0, cap_style="flat", quad_segs=8)
        wide = merged.difference(zone).simplify(SIMPLIFY_TOLERANCE, preserve_topology=True)
        merged = unary_union([wide, _tunnel_strip(line, tunnel.corridor_half_width)])
    # After simplifying, so the simplification cannot eat into the capsule clearance.
    merged = merged.difference(solid_building_clearance(osm))
    if not isinstance(merged, Polygon):
        raise TrailError(f"corridor is not a single polygon ({merged.geom_type})")
    if merged.interiors:
        raise TrailError(f"corridor has {len(merged.interiors)} hole(s); inspect the OSM geometry")
    return orient(merged), viewpoints


def walkable_bounds(
    osm: OsmData, margin: float = WALKABLE_MARGIN, tunnel: TunnelSpec | None = None
) -> tuple[float, float, float, float]:
    """Local ``(x_min, z_min, x_max, z_max)`` of the corridor plus ``margin`` metres."""
    corridor, _ = build_corridor(osm, tunnel)
    x0, z0, x1, z1 = corridor.bounds
    return x0 - margin, z0 - margin, x1 + margin, z1 + margin


def _anchor(
    dem: Grid, xz: tuple[float, float], osm_ref: str, y: float | None = None
) -> dict[str, Any]:
    height = float(dem.sample(np.array([xz[0]]), np.array([xz[1]]))[0]) if y is None else y
    return {
        "x": round(xz[0], 3),
        "y": round(height, 3),
        "z": round(xz[1], 3),
        "osm": osm_ref,
    }


def build_anchors(
    osm: OsmData, dem: Grid, segments: list[dict[str, Any]], viewpoints: list[int]
) -> dict[str, dict[str, Any]]:
    trail = route_geometry(osm)
    by_id = {s["id"]: s for s in segments}
    tunnel = by_id[TUNNEL_SEGMENT]["points"]
    portal_west, portal_east = tunnel[0], tunnel[-1]
    bifurcation = by_id["summit-ascent"]["points"][0]

    def at_route(point: list[float], node: int) -> dict[str, Any]:
        return {"x": point[0], "y": point[1], "z": point[2], "osm": f"node/{node}"}

    anchors: dict[str, dict[str, Any]] = {
        "centre": _anchor(dem, centre_anchor_point(osm, trail), f"way/{CENTRE_BUILDING_WAY}"),
        "turnstile": _anchor(dem, osm.xz[TURNSTILE_NODE], f"node/{TURNSTILE_NODE}"),
        "park-entrance": _anchor(dem, park_entrance(osm), f"relation/{PARK_RELATION}"),
        "tunnel-west": at_route(portal_west, TUNNEL_WEST_NODE),
        "tunnel-east": at_route(portal_east, TUNNEL_EAST_NODE),
        "bifurcation": at_route(bifurcation, BIFURCATION_NODE),
        "summit": _anchor(dem, osm.xz[SUMMIT_NODE], f"node/{SUMMIT_NODE}"),
        "carabiners": _anchor(dem, osm.xz[CARABINERS_NODE], f"node/{CARABINERS_NODE}"),
        "pobla": _anchor(dem, polygon_centroid(osm, POBLA_WAY), f"way/{POBLA_WAY}"),
    }
    for node in viewpoints:
        anchors[f"viewpoint-{node}"] = _anchor(dem, osm.xz[node], f"node/{node}")
    return anchors


def build_trail(
    osm: OsmData,
    dem: Grid,
    osm_sha256: str,
    dem_source: dict[str, Any],
    tunnel: TunnelSpec,
) -> dict[str, Any]:
    segments = build_segments(osm, dem, tunnel)
    corridor, viewpoints = build_corridor(osm, tunnel)
    ring = list(corridor.exterior.coords)[:-1]
    log.info("corridor: %.0f m2, viewpoints %s", corridor.area, viewpoints)
    return {
        "licence": LICENCE,
        "attribution": ATTRIBUTION,
        "source": {"id": OSM_SOURCE_ID, "sha256": osm_sha256},
        "demSource": dem_source,
        "frame": {
            "crs": "EPSG:25830",
            "origin": {"e": 767000, "n": 4280000},
            "axes": "x = E - origin.e, y = H, z = -(N - origin.n)",
        },
        "route": {"segments": segments},
        "corridor": {"polygon": [[round(x, 3), round(z, 3)] for x, z in ring]},
        "anchors": build_anchors(osm, dem, segments, viewpoints),
    }


# Groups reported against the OSM 2D figures in notes.md (segment ids, summed); the access path
# is not in that table.
REPORT_GROUPS: tuple[tuple[str, tuple[str, ...], float | None], ...] = (
    ("access path (way 26330270)", ("access",), None),
    ("centre steps + path to the steps", ("centre-steps", "centre-path"), 741.0),
    ("steps to the west portal", ("portal-steps",), 17.0),
    ("tunnel", ("tunnel",), 49.0),
    ("tunnel -> bifurcation", ("tunnel-bifurcation",), 355.0),
    ("bifurcation -> summit", ("summit-ascent",), 535.0),
    ("bifurcation -> Carabiners", ("carabiners-branch",), 259.0),
)


def report_rows(document: dict[str, Any]) -> list[list[str]]:
    """Rows ``[group, OSM 2D, 2D, 3D, ascent]`` (metres) for the groups above."""
    by_id = {s["id"]: s for s in document["route"]["segments"]}
    rows: list[list[str]] = []
    for label, ids, osm_length in REPORT_GROUPS:
        parts = [by_id[i] for i in ids]
        rows.append(
            [
                label,
                "-" if osm_length is None else f"{osm_length:.0f}",
                f"{sum(p['length2d'] for p in parts):.1f}",
                f"{sum(p['length3d'] for p in parts):.1f}",
                f"{sum(p['ascent'] for p in parts):.1f}",
            ]
        )
    return rows


def run_trail(
    dem: Grid,
    dem_source: dict[str, Any],
    outputs: tuple[Path, ...],
    tunnel: TunnelSpec,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    raw = locate(OSM_SOURCE_ID, OSM_FILE)
    document = {
        **build_trail(load_osm(raw.path), dem, raw.sha256, dem_source, tunnel),
        **provenance,
    }
    text = json.dumps(document, separators=(",", ":"), ensure_ascii=False) + "\n"
    for out in outputs:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        log.info("wrote %s (%d bytes)", out, out.stat().st_size)
    return document
