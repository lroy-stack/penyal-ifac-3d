"""The three OSM staircases as meshes with a handrail and a collision proxy (spec 003, E1.4).

Each ``highway=steps`` way becomes a flight of ``step_count`` stone steps along its OSM line
(``way/26330269`` 30 steps, ``way/862108205`` 10 steps, ``way/862108208`` 6 steps), built on the
DEM exactly as the terrain tiles render it (after the ADR 0009 carve). The riser is uniform: the
rise of the flight divided by ``step_count``. Each nosing is placed where the monotone envelope of
the highest ground across the flight's width reaches ``base + k * riser``, so tread depth varies
with the terrain and the ground never rises above a tread (the player walks on the highest ground
and LOD0 terrain would otherwise hide the steps). Riser and depths are *derived from data*; only
the width and the handrail are assumptions.

* **Orientation** follows the DEM, not the OSM ``incline`` tag: ``way/862108205`` is tagged
  ``incline=down`` but its DEM rises 2.2 m along the way, so the tag and the heights disagree and
  the heights win (reported as ``inclineTag`` / ``reversedWay`` in ``structures.json``).
* **The portal flight** (``way/862108208``) is measured along the polyline the carve uses
  (``trail.segment_polyline_2d``). It starts after ``steps_ramp_start`` metres
  (``data/curated/tunnel.toml``) and where the rock wall stops overhanging it, and stops short of
  the portal plane, where the carve strip ends (``StairSpec.end_margin``).
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
PORTAL_END_MARGIN = 0.75  # metres, see StairSpec.end_margin

STONE = 0  # material slots
METAL = 1
FOOTPRINT_SAMPLES = (0.0, 0.5, 1.0)  # across and along each step, to find the lowest ground
# Where across the flight the ground is sampled, as fractions of the half width.
LATERAL_SIDES = (-1.0, -0.5, 0.0, 0.5, 1.0)
# The flight starts where the ground beside it is no higher than the axis by more than this: a
# step cannot start inside a bank (the portal flight begins at the foot of the rock wall).
START_OVERHANG = 0.1
PROFILE_SPACING = 0.05  # metres along the flight between samples of the ground profile
CLEARANCE_SPACING = 0.1  # metres between the samples that check the ground under each tread
# The ground under a tread may exceed its top by this much: the check samples a bilinear DEM
# every 10 cm and the surface between two samples can only differ by a few millimetres.
CLEARANCE_TOLERANCE = 0.02
MIN_TREAD_DEPTH = 0.15  # metres: shallower than this and the ground profile cannot be followed

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
    segment: str | None = None  # id of the trail.json segment that walks this way, if any
    # Metres before the end of the way where the steps stop: the ADR 0009 carve strip ends flat at
    # the portal plane and its last half metre blends back into the rock wall (the carved DEM
    # reads 171.5 m then 178 m there, against the 171.0 m floor), so the steps stop short of it.
    end_margin: float = 0.0


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
    tread_depths: npt.NDArray[np.float64]
    clearance: npt.NDArray[np.float64]  # per tread: top minus the highest ground under it
    flight_length: float
    base: tuple[float, float, float]
    top: tuple[float, float, float]
    treads: list[Tread]
    handrail: Handrail
    mesh: StairMesh
    reversed_way: bool
    incline_tag: str | None

    @property
    def tread_depth(self) -> float:
        return float(self.tread_depths.mean())

    def mesh_named(self, name: str) -> StairMesh:
        return replace(self.mesh, name=name)


def staircase_specs(curated: TunnelSpec) -> tuple[StairSpec, ...]:
    return (
        StairSpec(
            "centre-steps", "Centre steps (30 steps, handrail)", 26330269, 0.0, "centre-steps"
        ),
        StairSpec("steps-10", "Steps of 10 (sett, handrail)", 862108205, 0.0),
        StairSpec(
            "portal-steps",
            "Steps to the west portal (6 rock steps, handrail)",
            862108208,
            curated.steps_ramp_start,
            "portal-steps",
            end_margin=PORTAL_END_MARGIN,
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


def _ground_profile(
    dem_sample: Callable[[Float1, Float1], Float1], line: Float2, along: Float1, arcs: Float1
) -> Float1:
    """Highest ground across the stair width at each arc length of ``line``."""
    points = _points_at(line, along, arcs)
    heading = _tangents_at(line, along, arcs)
    left = np.column_stack([heading[:, 1], -heading[:, 0]]) * (STAIR_WIDTH / 2.0)
    heights = [dem_sample(*(points + side * left).T) for side in LATERAL_SIDES]
    return np.max(heights, axis=0)


def _nosing_arcs(
    profile: Float1, arcs: Float1, base_y: float, riser: float, step_count: int, spec_id: str
) -> Float1:
    """Arc length of each step's nosing: where the MONOTONE envelope of the ground profile
    reaches ``base + k * riser``. The ground before a nosing is then never above the tread."""
    envelope = np.maximum.accumulate(profile)
    wanted = base_y + np.arange(1, step_count) * riser
    index = np.searchsorted(envelope, wanted, side="left")
    if np.any(index == 0) or np.any(index >= len(arcs)):
        raise StructuresError(
            f"{spec_id}: the ground profile does not rise through every step height"
        )
    lower, upper = envelope[index - 1], envelope[index]
    fraction = (wanted - lower) / np.where(upper > lower, upper - lower, 1.0)
    noses = arcs[index - 1] + fraction * (arcs[index] - arcs[index - 1])
    bounds = np.concatenate([[arcs[0]], noses, [arcs[-1]]])
    if float(np.diff(bounds).min()) < MIN_TREAD_DEPTH:
        raise StructuresError(
            f"{spec_id}: a tread would be {float(np.diff(bounds).min()):.2f} m deep "
            f"(< {MIN_TREAD_DEPTH} m): the ground is too steep for this step count"
        )
    return bounds


def tread_clearance(
    treads: Sequence["Tread"], dem_sample: Callable[[Float1, Float1], Float1]
) -> Float1:
    """``top - highest ground under the footprint`` for each tread (>= -CLEARANCE_TOLERANCE)."""
    result = []
    for tread in treads:
        near_left, near_right, far_right, far_left = tread.quad
        across = max(
            2, round(float(np.linalg.norm(near_right - near_left)) / CLEARANCE_SPACING) + 1
        )
        along = max(2, round(float(np.linalg.norm(far_left - near_left)) / CLEARANCE_SPACING) + 1)
        u, v = np.meshgrid(np.linspace(0.0, 1.0, across), np.linspace(0.0, 1.0, along))
        near = near_left + u[..., None] * (near_right - near_left)
        far = far_left + u[..., None] * (far_right - far_left)
        points = ((1.0 - v[..., None]) * near + v[..., None] * far).reshape(-1, 2)
        result.append(tread.top - float(dem_sample(points[:, 0], points[:, 1]).max()))
    return np.array(result)


def build_staircase(
    spec: StairSpec,
    xz: Float2,
    step_count: int,
    dem_sample: Callable[[Float1, Float1], Float1],
    *,
    incline_tag: str | None = None,
) -> Staircase:
    """The flight of ``step_count`` steps along ``xz``, an OSM way in its own direction.

    ``dem_sample`` is the ground as rendered (the carved DEM). The profile is the highest ground
    across the flight's width at each arc length. The flight starts where the ground beside it
    stops overhanging the axis, begins at the profile height there and climbs to the highest
    ground it has to clear; the riser is uniform (rise over ``step_count``) and each nosing sits
    where the monotone envelope of the profile reaches ``base + k * riser`` (see
    :func:`_nosing_arcs`). Treads are as deep as the terrain lets them be and the ground never
    rises above one (to :data:`CLEARANCE_TOLERANCE`).
    """
    if step_count < 1:
        raise StructuresError(f"{spec.id}: a flight needs at least one step")
    length = float(_along(xz)[-1]) - spec.end_margin
    if not 0.0 <= spec.flight_start < length:
        raise StructuresError(f"{spec.id}: the flight starts outside the {length:.1f} m way")

    def axis_height(line: Float2, s: float) -> float:
        point = _points_at(line, _along(line), np.array([s]))
        return float(dem_sample(point[:, 0], point[:, 1])[0])

    reversed_way = axis_height(xz, length) < axis_height(xz, spec.flight_start)
    line, first = xz, spec.flight_start
    if reversed_way:
        if spec.flight_start != 0.0 or spec.end_margin != 0.0:
            raise StructuresError(
                f"{spec.id}: a flight that starts or stops part way cannot be turned round"
            )
        line = xz[::-1]
    along = _along(line)
    samples = np.append(np.arange(first, length, PROFILE_SPACING), length)
    profile = _ground_profile(dem_sample, line, along, samples)
    axis = _points_at(line, along, samples)
    overhang = profile - dem_sample(axis[:, 0], axis[:, 1])
    clear = np.flatnonzero(overhang <= START_OVERHANG)
    if clear.size == 0:
        raise StructuresError(f"{spec.id}: the ground beside the flight never clears its width")
    samples, profile = samples[clear[0] :], profile[clear[0] :]
    first = float(samples[0])
    base_y, top_y = float(profile[0]), float(np.maximum.accumulate(profile)[-1])
    rise = top_y - base_y
    if rise <= 0.0:
        raise StructuresError(f"{spec.id}: the flight has no rise ({rise:.3f} m)")
    riser = rise / step_count
    if riser > PLAYER_STEP_HEIGHT:
        raise StructuresError(
            f"{spec.id}: riser {riser:.3f} m is above the player's step height "
            f"{PLAYER_STEP_HEIGHT} m: the step count or the heights are wrong"
        )
    arcs = _nosing_arcs(profile, samples, base_y, riser, step_count, spec.id)
    centres = _points_at(line, along, arcs)
    heading = _tangents_at(line, along, arcs)
    left = np.column_stack([heading[:, 1], -heading[:, 0]])
    half = STAIR_WIDTH / 2.0
    left_edge, right_edge = centres + left * half, centres - left * half
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

    tread_depths = np.diff(arcs)
    every = max(1, round(POST_SPACING / float(tread_depths.mean())))
    indices = sorted({*range(0, step_count + 1, every), step_count})
    rail_side = centres - left * (half - RAIL_INSET)
    nosing = base_y + np.arange(step_count + 1) * riser
    feet = np.array([[rail_side[k, 0], nosing[k], rail_side[k, 1]] for k in indices])
    rail = feet + np.array([0.0, RAIL_HEIGHT, 0.0])
    for foot, axis in zip(feet, rail, strict=True):
        soup.bar(foot - np.array([0.0, POST_EMBED, 0.0]), axis, POST_SECTION, METAL)
    for a, b in itertools.pairwise(rail):
        soup.bar(a, b, RAIL_SECTION, METAL)

    clearance = tread_clearance(treads, dem_sample)
    if float(clearance.min()) < -CLEARANCE_TOLERANCE:
        raise StructuresError(
            f"{spec.id}: the ground rises {-float(clearance.min()):.3f} m above a tread "
            f"(tolerance {CLEARANCE_TOLERANCE} m)"
        )
    return Staircase(
        spec=spec,
        step_count=step_count,
        riser=riser,
        tread_depths=tread_depths,
        clearance=clearance,
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


def _flight_polyline(osm: OsmData, spec: StairSpec) -> Float2:
    """The way's polyline; for a way the trail walks, the one the trail and the carve use."""
    way = osm.ways.get(spec.way)
    if way is None:
        raise StructuresError(f"way {spec.way} ({spec.id}) is missing from the OSM extract")
    own = np.array([osm.xz[n] for n in way.nodes], dtype=np.float64)
    if spec.segment is None:
        return own
    segment = next(sp for sp in trail.SEGMENT_SPECS if sp.id == spec.segment)
    walked = trail.segment_polyline_2d(osm, segment)
    if walked.shape != own.shape or not np.allclose(walked, own):
        raise StructuresError(
            f"{spec.id}: the trail walks way {spec.way} from the other end, so a flight "
            "start measured along the way would not match the carve"
        )
    return walked


def build_all(osm: OsmData, carved: Grid, curated: TunnelSpec) -> list[Staircase]:
    """The staircases on ``carved``: the DEM after the ADR 0009 carve, as the tiles render it."""
    result: list[Staircase] = []
    for spec in staircase_specs(curated):
        xz = _flight_polyline(osm, spec)
        tags = osm.ways[spec.way].tags
        result.append(
            build_staircase(
                spec,
                xz,
                step_count_of(tags, spec.way),
                carved.sample,
                incline_tag=tags.get("incline"),
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
        "treadDepthRange": [_mm(stairs.tread_depths.min()), _mm(stairs.tread_depths.max())],
        "treadClearance": {
            "min": _mm(stairs.clearance.min()),
            "tolerance": CLEARANCE_TOLERANCE,
            "note": "top of each tread minus the highest carved-DEM height under it",
        },
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
    from penyal_pipeline.tunnel import load_curated, terrain_features

    raw = locate(trail.OSM_SOURCE_ID, trail.OSM_FILE)
    osm = trail.load_osm(raw.path)
    grid, _ = dem.load_dem()
    curated = load_curated()
    carved = terrain_features(osm, grid, curated).carve.apply(grid)
    staircases = build_all(osm, carved, curated.trail_spec())
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
