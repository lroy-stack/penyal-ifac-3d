"""The three OSM staircases as meshes with a handrail and a collision proxy (spec 003, E1.4).

Each ``highway=steps`` way becomes a flight of ``step_count`` stone steps along its OSM line
(``way/26330269`` 30 steps, ``way/862108205`` 10 steps, ``way/862108208`` 6 steps), draped on the
DEM: the first step starts on the ground at the bottom of the flight and the last step's tread
ends on the ground at the top, with identical risers in between. Tread depth is the flight
length divided by ``step_count`` and the riser is the height difference divided by
``step_count``, so both are *derived from data*; only the width and the handrail are assumptions.

* **Orientation** follows the DEM, not the OSM ``incline`` tag: ``way/862108205`` is tagged
  ``incline=down`` but its DEM rises 2.0 m along the way, so the tag and the heights disagree and
  the heights win (reported as ``inclineTag`` / ``reversedWay`` in ``structures.json``).
* **The portal flight** (``way/862108208``) does not use the raw DEM, which is the rock wall there
  (ADR 0009): its heights are the ones ``trail.json`` uses, and the six steps occupy the climb
  that starts ``steps_ramp_start`` metres along the way (``data/curated/tunnel.toml``), ending on
  the curated west floor.
* **Handrail**: OSM says ``handrail=yes`` without a side. One rail on the **right-hand side when
  going up** is assumed (the conventional single rail, and the side OSM would call ``right``
  for ways drawn uphill): it is the least that ``handrail=yes`` guarantees; two rails would
  claim more than the data says. Provisional until the user's photos show the real side.
* **Collision proxy**: one horizontal quad per tread at its own top height. The player's walker
  (``app/src/player/controller.ts``) steps up at most ``STEP_HEIGHT`` = 0.4 m, so every riser has
  to stay under :data:`PLAYER_STEP_HEIGHT`; a flight that would not is rejected, not simplified.

Every constant marked provisional is an approximation listed in ``CREDITS.md``.
"""

import itertools
import json
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from penyal_pipeline import tiles, trail
from penyal_pipeline.dem import Grid
from penyal_pipeline.geo import ORIGIN_E, ORIGIN_N
from penyal_pipeline.paths import BUILD_DIR, GENERATED_DIR
from penyal_pipeline.rawdata import locate
from penyal_pipeline.trail import OsmData, TunnelSpec

log = logging.getLogger(__name__)

STRUCTURES_JSON = "structures.json"
STRUCTURES_GLB = "structures.glb"
STRUCTURES_BUILD_DIR = BUILD_DIR / "structures"

# Mirrors STEP_HEIGHT in app/src/player/controller.ts: the highest rise the player climbs at once.
PLAYER_STEP_HEIGHT = 0.4

# PROVISIONAL (approximations, CREDITS.md): not in OSM, replaced by the user's tape measurements.
CONSTANTS_STATUS = "provisional"
STAIR_WIDTH = 1.5  # metres, between the side faces
RAIL_HEIGHT = 0.9  # metres, rail axis above the nosing line (the line through the tread edges)
RAIL_SECTION = 0.05  # metres, square rail bar
POST_SECTION = 0.05  # metres, square post
RAIL_INSET = 0.1  # metres, rail axis inside the side edge of the steps
POST_SPACING = 1.5  # metres along the flight, between posts (both ends always get one)
HANDRAIL_SIDE = "right"  # when going up; see the module docstring
# Not measurements either: how deep the steps are buried and the posts sunk, so nothing floats.
STEP_EMBED = 0.25
POST_EMBED = 0.1

STONE = 0  # material slots
METAL = 1
FOOTPRINT_SAMPLES = (0.0, 0.5, 1.0)  # across and along each step, to find the lowest ground

type Float1 = npt.NDArray[np.float64]
type Float2 = npt.NDArray[np.float64]


class StructuresError(RuntimeError):
    """A staircase cannot be built from the data or violates a contract."""


@dataclass(frozen=True)
class StairSpec:
    id: str
    name: str
    way: int
    flight_start: float  # metres along the OSM way where the steps start
    ground: str  # "dem" (drape on the DEM) or "portal-steps" (the heights of trail.json)


@dataclass(frozen=True)
class StairMesh:
    """Flat-shaded triangle soup: four own vertices per quad, so normals are the face normals."""

    positions: npt.NDArray[np.float32]
    normals: npt.NDArray[np.float32]
    triangles: npt.NDArray[np.int32]
    materials: npt.NDArray[np.int32]  # per triangle: STONE or METAL
    name: str = ""


@dataclass(frozen=True)
class Tread:
    quad: Float2  # (4, 2) local (x, z): left edge below, right edge below, right above, left above
    top: float


@dataclass(frozen=True)
class Handrail:
    side: str
    rail: npt.NDArray[np.float64]  # (n, 3): the rail axis at each post
    posts: npt.NDArray[np.float64]  # (n, 3): foot of each post, on the nosing line


@dataclass(frozen=True)
class Staircase:
    spec: StairSpec
    step_count: int
    riser: float
    tread_depth: float
    flight_length: float
    base: tuple[float, float, float]
    top: tuple[float, float, float]
    treads: list[Tread]
    handrail: Handrail
    mesh: StairMesh
    reversed_way: bool
    incline_tag: str | None

    def mesh_named(self, name: str) -> StairMesh:
        return replace(self.mesh, name=name)


def staircase_specs(curated: TunnelSpec) -> tuple[StairSpec, ...]:
    return (
        StairSpec("centre-steps", "Centre steps (30 steps, handrail)", 26330269, 0.0, "dem"),
        StairSpec("steps-10", "Steps of 10 (sett, handrail)", 862108205, 0.0, "dem"),
        StairSpec(
            "portal-steps",
            "Steps to the west portal (6 rock steps, handrail)",
            862108208,
            curated.steps_ramp_start,
            "portal-steps",
        ),
    )


def step_count_of(tags: dict[str, str], way: int) -> int:
    raw = tags.get("step_count", "")
    if not raw.isdigit() or int(raw) < 1:
        raise StructuresError(f"way {way} has no usable step_count tag ({raw!r})")
    return int(raw)


def _along(xz: Float2) -> Float1:
    return np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(xz, axis=0), axis=1))])


def _points_at(xz: Float2, along: Float1, s: Float1) -> Float2:
    return np.column_stack([np.interp(s, along, xz[:, 0]), np.interp(s, along, xz[:, 1])])


def _tangents_at(xz: Float2, along: Float1, s: Float1) -> Float2:
    index = np.clip(np.searchsorted(along, s, side="right") - 1, 0, len(xz) - 2)
    direction = xz[index + 1] - xz[index]
    return direction / np.linalg.norm(direction, axis=1, keepdims=True)


class _Soup:
    """Collects quads and square bars as a flat-shaded mesh with one material slot per face."""

    def __init__(self) -> None:
        self.positions: list[Float1] = []
        self.normals: list[Float1] = []
        self.triangles: list[tuple[int, int, int]] = []
        self.materials: list[int] = []

    def quad(self, corners: Sequence[Float1], inside: Float1, material: int) -> None:
        p = [np.asarray(c, dtype=np.float64) for c in corners]
        normal = np.cross(p[1] - p[0], p[2] - p[0])
        centroid = np.mean(p, axis=0)
        if float(normal @ (centroid - inside)) < 0.0:
            p = [p[0], p[3], p[2], p[1]]
            normal = -normal
        length = float(np.linalg.norm(normal))
        if length == 0.0:
            raise StructuresError("a degenerate face was generated")
        base = len(self.positions)
        self.positions.extend(p)
        self.normals.extend([normal / length] * 4)
        self.triangles.extend([(base, base + 1, base + 2), (base, base + 2, base + 3)])
        self.materials.extend([material, material])

    def bar(self, a: Float1, b: Float1, section: float, material: int) -> None:
        axis = b - a
        axis = axis / np.linalg.norm(axis)
        reference = np.array([0.0, 1.0, 0.0]) if abs(axis[1]) < 0.99 else np.array([1.0, 0.0, 0.0])
        u = np.cross(axis, reference)
        u /= np.linalg.norm(u)
        v = np.cross(axis, u)
        half = section / 2.0
        ring = [half * (su * u + sv * v) for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        near, far = [a + r for r in ring], [b + r for r in ring]
        inside = (a + b) / 2.0
        for k in range(4):
            n = (k + 1) % 4
            self.quad([near[k], near[n], far[n], far[k]], inside, material)
        self.quad(near, inside, material)
        self.quad(far, inside, material)

    def build(self) -> StairMesh:
        return StairMesh(
            positions=np.array(self.positions, dtype=np.float32),
            normals=np.array(self.normals, dtype=np.float32),
            triangles=np.array(self.triangles, dtype=np.int32),
            materials=np.array(self.materials, dtype=np.int32),
        )


def _lowest_ground(
    dem_sample: Callable[[Float1, Float1], Float1], quad: Float2, ceiling: float
) -> float:
    """Lowest DEM height under a tread footprint, never above ``ceiling``."""
    left0, right0, right1, left1 = quad
    steps = np.array(FOOTPRINT_SAMPLES)
    u, v = np.meshgrid(steps, steps)
    near = left0 + u[..., None] * (right0 - left0)
    far = left1 + u[..., None] * (right1 - left1)
    points = ((1.0 - v[..., None]) * near + v[..., None] * far).reshape(-1, 2)
    return min(float(dem_sample(points[:, 0], points[:, 1]).min()), ceiling)


def _at(point: Float1, y: float) -> Float1:
    return np.array([point[0], y, point[1]])


def _add_step(
    soup: _Soup, quad: Float2, floor: float, riser_foot: float, top: float, closed_back: bool
) -> None:
    """One stone block: tread, visible riser, both sides and, on the last step, the back.

    ``riser_foot`` is where the visible riser starts: the top of the step below (the rest of the
    block is inside it) or, for the first step, the buried floor. The bottom is left open.
    """
    inside = np.mean([_at(p, y) for p in quad for y in (floor, top)], axis=0)
    near_left, near_right, far_right, far_left = quad
    soup.quad([_at(p, top) for p in quad], inside, STONE)
    soup.quad(
        [
            _at(near_left, riser_foot),
            _at(near_right, riser_foot),
            _at(near_right, top),
            _at(near_left, top),
        ],
        inside,
        STONE,
    )
    soup.quad(
        [_at(near_left, floor), _at(far_left, floor), _at(far_left, top), _at(near_left, top)],
        inside,
        STONE,
    )
    soup.quad(
        [_at(near_right, floor), _at(far_right, floor), _at(far_right, top), _at(near_right, top)],
        inside,
        STONE,
    )
    if closed_back:
        soup.quad(
            [_at(far_left, floor), _at(far_right, floor), _at(far_right, top), _at(far_left, top)],
            inside,
            STONE,
        )


def build_staircase(
    spec: StairSpec,
    xz: Float2,
    step_count: int,
    dem_sample: Callable[[Float1, Float1], Float1],
    *,
    along_height: Callable[[Float1], Float1] | None = None,
    incline_tag: str | None = None,
) -> Staircase:
    """The flight of ``step_count`` steps along ``xz``, an OSM way in its own direction.

    Heights come from ``along_height`` (metres along the way to height) when given, else from
    ``dem_sample`` at the point; ``dem_sample`` also finds the ground under each step's footprint.
    """
    if step_count < 1:
        raise StructuresError(f"{spec.id}: a flight needs at least one step")
    length = float(_along(xz)[-1])
    if not 0.0 <= spec.flight_start < length:
        raise StructuresError(f"{spec.id}: the flight starts outside the {length:.1f} m way")

    def ground(line: Float2, s: Float1, mirrored: bool) -> Float1:
        """Height at arc length ``s`` of ``line``; ``mirrored`` lines run against the OSM way."""
        if along_height is not None:
            return along_height(length - s if mirrored else s)
        points = _points_at(line, _along(line), s)
        return dem_sample(points[:, 0], points[:, 1])

    start_height = float(ground(xz, np.array([spec.flight_start]), False)[0])
    end_height = float(ground(xz, np.array([length]), False)[0])
    reversed_way = end_height < start_height
    line, first = xz, spec.flight_start
    if reversed_way:
        if spec.flight_start != 0.0:
            raise StructuresError(
                f"{spec.id}: a flight that starts part way cannot be turned round"
            )
        line = xz[::-1]
    along = _along(line)
    arcs = first + np.arange(step_count + 1) * (length - first) / step_count
    centres = _points_at(line, along, arcs)
    heading = _tangents_at(line, along, arcs)
    left = np.column_stack([heading[:, 1], -heading[:, 0]])
    half = STAIR_WIDTH / 2.0
    left_edge, right_edge = centres + left * half, centres - left * half
    base_y = float(ground(line, np.array([first]), reversed_way)[0])
    top_y = float(ground(line, np.array([length]), reversed_way)[0])
    rise = top_y - base_y
    if rise <= 0.0:
        raise StructuresError(f"{spec.id}: the flight has no rise ({rise:.3f} m)")
    riser = rise / step_count
    if riser > PLAYER_STEP_HEIGHT:
        raise StructuresError(
            f"{spec.id}: riser {riser:.3f} m is above the player's step height "
            f"{PLAYER_STEP_HEIGHT} m: the step count or the heights are wrong"
        )
    tops = base_y + (np.arange(step_count) + 1) * riser

    soup = _Soup()
    treads: list[Tread] = []
    for i in range(step_count):
        quad = np.array([left_edge[i], right_edge[i], right_edge[i + 1], left_edge[i + 1]])
        top = float(tops[i])
        treads.append(Tread(quad=quad, top=top))
        floor = _lowest_ground(dem_sample, quad, top - riser) - STEP_EMBED
        riser_foot = floor if i == 0 else float(tops[i - 1])
        _add_step(soup, quad, floor, riser_foot, top, closed_back=i == step_count - 1)

    tread_depth = (length - first) / step_count
    every = max(1, round(POST_SPACING / tread_depth))
    indices = sorted({*range(0, step_count + 1, every), step_count})
    rail_side = centres - left * (half - RAIL_INSET)
    nosing = base_y + np.arange(step_count + 1) * riser
    feet = np.array([[rail_side[k, 0], nosing[k], rail_side[k, 1]] for k in indices])
    rail = feet + np.array([0.0, RAIL_HEIGHT, 0.0])
    for foot, axis in zip(feet, rail, strict=True):
        soup.bar(foot - np.array([0.0, POST_EMBED, 0.0]), axis, POST_SECTION, METAL)
    for a, b in itertools.pairwise(rail):
        soup.bar(a, b, RAIL_SECTION, METAL)

    return Staircase(
        spec=spec,
        step_count=step_count,
        riser=riser,
        tread_depth=tread_depth,
        flight_length=length - first,
        base=(float(centres[0, 0]), base_y, float(centres[0, 1])),
        top=(float(centres[-1, 0]), top_y, float(centres[-1, 1])),
        treads=treads,
        handrail=Handrail(side=HANDRAIL_SIDE, rail=rail, posts=feet),
        mesh=soup.build(),
        reversed_way=reversed_way,
        incline_tag=incline_tag,
    )


def tread_height(treads: Sequence[Tread], x: float, z: float) -> float | None:
    """Top of the tread under local ``(x, z)``, or None: the proxy a walker would query."""
    for tread in treads:
        q = tread.quad
        signs = []
        for k in range(4):
            a, b = q[k], q[(k + 1) % 4]
            signs.append((b[0] - a[0]) * (z - a[1]) - (b[1] - a[1]) * (x - a[0]))
        if all(s >= -1e-9 for s in signs) or all(s <= 1e-9 for s in signs):
            return tread.top
    return None


def build_all(osm: OsmData, grid: Grid, curated: TunnelSpec) -> list[Staircase]:
    result: list[Staircase] = []
    for spec in staircase_specs(curated):
        way = osm.ways.get(spec.way)
        if way is None:
            raise StructuresError(f"way {spec.way} ({spec.id}) is missing from the OSM extract")
        xz = np.array([osm.xz[n] for n in way.nodes], dtype=np.float64)
        along_height: Callable[[Float1], Float1] | None = None
        if spec.ground == "portal-steps":
            dense = trail.densify(xz)
            heights = trail.steps_heights(dense, grid, curated.west_floor, curated.steps_ramp_start)
            dense_along = _along(dense)

            def portal(s: Float1, a: Float1 = dense_along, h: Float1 = heights) -> Float1:
                return np.interp(s, a, h)

            along_height = portal
        result.append(
            build_staircase(
                spec,
                xz,
                step_count_of(way.tags, spec.way),
                grid.sample,
                along_height=along_height,
                incline_tag=way.tags.get("incline"),
            )
        )
    return result


@dataclass(frozen=True)
class StructuresReport:
    document: dict[str, Any]
    triangles: int
    glb_bytes: int
    json_bytes: int


def _mm(value: float) -> float:
    return round(float(value), 3)


def _staircase_entry(stairs: Staircase, osm: OsmData) -> dict[str, Any]:
    tags = osm.ways[stairs.spec.way].tags
    return {
        "id": stairs.spec.id,
        "name": stairs.spec.name,
        "osmWay": stairs.spec.way,
        "osmTags": {
            k: tags[k] for k in ("surface", "handrail", "incline", "step_count") if k in tags
        },
        "stepCount": stairs.step_count,
        "riser": _mm(stairs.riser),
        "treadDepth": _mm(stairs.tread_depth),
        "width": STAIR_WIDTH,
        "flightLength": _mm(stairs.flight_length),
        "flightStartAlongWay": stairs.spec.flight_start,
        "base": [_mm(v) for v in stairs.base],
        "top": [_mm(v) for v in stairs.top],
        "orientation": {
            "by": "dem",
            "inclineTag": stairs.incline_tag,
            "reversedWay": stairs.reversed_way,
        },
        "handrail": {
            "side": stairs.handrail.side,
            "posts": int(stairs.handrail.posts.shape[0]),
            "status": CONSTANTS_STATUS,
        },
        "mesh": {
            "node": f"stairs_{stairs.spec.id.replace('-', '_')}",
            "triangles": int(stairs.mesh.triangles.shape[0]),
        },
        "collision": {
            "kind": "treads",
            "note": "one horizontal quad per tread, bottom to top; (x, z) corners then top height",
            "treads": [
                {"top": _mm(t.top), "quad": [[_mm(x), _mm(z)] for x, z in t.quad]}
                for t in stairs.treads
            ],
        },
    }


def build_document(
    staircases: Sequence[Staircase], osm: OsmData, osm_sha256: str, provenance: dict[str, Any]
) -> dict[str, Any]:
    return {
        "version": 1,
        "licence": trail.LICENCE,
        "attribution": trail.ATTRIBUTION,
        "source": {"id": trail.OSM_SOURCE_ID, "sha256": osm_sha256},
        "frame": {"crs": "EPSG:25830", "origin": {"e": int(ORIGIN_E), "n": int(ORIGIN_N)}},
        "glb": STRUCTURES_GLB,
        "materials": {"stone": "stairs_stone", "handrail": "stairs_handrail_metal"},
        "constants": {
            "status": CONSTANTS_STATUS,
            "stairWidth": STAIR_WIDTH,
            "railHeight": RAIL_HEIGHT,
            "railSection": RAIL_SECTION,
            "postSection": POST_SECTION,
            "railInset": RAIL_INSET,
            "postSpacing": POST_SPACING,
            "handrailSide": HANDRAIL_SIDE,
            "handrailSideBasis": "OSM handrail=yes names no side: one rail on the right going up",
            "stepEmbed": STEP_EMBED,
            "playerStepHeight": PLAYER_STEP_HEIGHT,
        },
        "staircases": [_staircase_entry(s, osm) for s in staircases],
        **provenance,
    }


def run_structures(
    out_dir: Path = GENERATED_DIR,
    build_dir: Path = STRUCTURES_BUILD_DIR,
    provenance: dict[str, Any] | None = None,
) -> StructuresReport:
    """Write ``structures.glb`` (optimised) and ``structures.json`` into ``out_dir``."""
    from penyal_pipeline import dem
    from penyal_pipeline.blender import structures as blender_structures
    from penyal_pipeline.tunnel import load_curated

    raw = locate(trail.OSM_SOURCE_ID, trail.OSM_FILE)
    osm = trail.load_osm(raw.path)
    grid, _ = dem.load_dem()
    staircases = build_all(osm, grid, load_curated().trail_spec())
    meshes = [s.mesh_named(f"stairs_{s.spec.id.replace('-', '_')}") for s in staircases]
    build_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_glb = blender_structures.export_structures(meshes, build_dir / STRUCTURES_GLB)
    glb_bytes = tiles.optimize_glb(raw_glb, out_dir / STRUCTURES_GLB, None)
    document = build_document(
        staircases, osm, raw.sha256, provenance or {"inputs": [], "tools": {}}
    )
    path = out_dir / STRUCTURES_JSON
    path.write_text(json.dumps(document, separators=(",", ":"), ensure_ascii=False) + "\n", "utf-8")
    log.info("wrote %s (%d bytes)", path, path.stat().st_size)
    return StructuresReport(
        document=document,
        triangles=sum(int(s.mesh.triangles.shape[0]) for s in staircases),
        glb_bytes=glb_bytes,
        json_bytes=path.stat().st_size,
    )
