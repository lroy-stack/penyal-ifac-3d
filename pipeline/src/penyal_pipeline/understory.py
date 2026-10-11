"""Shrubs and grass from the LiDAR low and medium vegetation (E2.4).

The ground is cut into 4 m cells aligned to whole metres. Each cell holds up to two instances; the
chance of each grows with the number of class 3 and 4 points in the cell, and every random choice
(slot, jitter, yaw, priority) is a hash of the cell id (``cellhash.hash_cells``), so the result
does not depend on the order the cells are visited in. The model comes from the median height of
the points. Nothing is placed on the walkable corridor (ADR 0006) or on paths, roads and buildings
of OSM, and the three plants are generic stand-ins: no protected species is represented
(``docs/specs/002/vegetacion-especies.md`` §4).
"""

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt
import shapely
from shapely.geometry.base import BaseGeometry

from penyal_pipeline import dem, surfaces, tiles, trail
from penyal_pipeline.cellhash import hash_cells, unit_float

if TYPE_CHECKING:
    from penyal_pipeline.vegetation import VegetationPoints

CELL = 4.0  # metres
UNDERSTORY_CLASSES = (3, 4)
POINTS_FOR_CERTAIN = 6  # points in a cell that make its first instance certain
POINTS_FOR_SECOND = 12  # points that make the second one certain
MIN_HEIGHT, MAX_HEIGHT = 0.3, 3.0  # metres, instance height
TALL_SHRUB_FROM = 1.0  # median height from which a cell holds the tall shrub
LOW_SHRUB_FROM = 0.4  # ... the low shrub; below it, grass
# Silene hifacensis lives in cliff fissures between 60 and 385 m (docs/specs/002/
# vegetacion-especies.md, section 4), and the project must never show where. A cliff mask would
# be a map of its habitat, so no understory is placed on a slope of 50 degrees or more inside that
# elevation band: cliff vegetation is deliberately absent from the 3D world (CREDITS.md).
SILENE_BAND = (60.0, 385.0)  # metres a.s.l.
SILENE_CLIFF_SLOPE = 50.0  # degrees
CORRIDOR_CLEARANCE = 0.75  # metres kept free around the ADR 0006 corridor
FOOTPATH_CLEARANCE = 1.5  # metres around OSM paths (provisional: E1's surface widths replace it)
ROAD_CLEARANCE = 4.0  # metres around other OSM highways (provisional)
BUILDING_CLEARANCE = 1.0
FOOTPATH_HIGHWAYS = frozenset({"path", "footway", "steps", "pedestrian", "bridleway", "cycleway"})
SALT_FIRST = 10  # one salt block per slot: x, z, yaw, priority, chance
SALT_SLOTS = 8

PROTECTED_SPECIES = (
    "Silene hifacensis",
    "Teucrium hifacense",
    "Centaurea rouyi",
    "Hippocrepis valentina",
)


@dataclass(frozen=True)
class Model:
    """A procedural plant (``blender/plants.py``) with the size it is modelled at."""

    id: str
    stand_in: str
    height: float  # metres, modelled
    radius: float  # metres, modelled


# Index in this tuple is the ``model`` column of the output. The three plants replace the Poly
# Haven shrub_04 / shrub_02 / grass_medium_02 meshes: shrub_04 is a 0.22 m young plant with an
# end pivot and 27k triangles (scaled 5-14x to a 1-3 m lentisc it was a caricature, and ten
# instances already exceeded the 250k-triangle budget), and none of the three had LODs or cards.
# Only their (CC0) leaf and blade textures are used.
MODELS = (
    Model("lentisc", "Pistacia lentiscus (lentisc), approximate", 2.0, 1.0),
    Model("rosemary", "Rosmarinus officinalis / Lavandula dentata, approximate", 0.8, 0.5),
    Model("grass", "scrub grasses, generic", 0.5, 0.25),
)
TALL, LOW, GRASS = 0, 1, 2

type Floats = npt.NDArray[np.float64]
type Reject = Callable[[Floats, Floats], npt.NDArray[np.bool_]]  # positions -> True to drop


def model_description(model: Model) -> dict[str, Any]:
    """What the app needs to instance ``model``: its meshes by level and its nominal size."""
    return {
        "id": model.id,
        "standsFor": model.stand_in,
        "nominalHeight": model.height,
        "nominalRadius": model.radius,
        "file": "vegetation/plants.glb",
        "meshes": {level: f"{model.id}_{level}" for level in ("lod0", "lod1", "card")},
        "licence": "CC0 1.0",
    }


HARDSTANDING_LANDUSE = frozenset(
    {"brownfield", "construction", "commercial", "retail", "industrial", "garages", "railway"}
)
AREA_HIGHWAYS = frozenset({"pedestrian", "footway", "service", "living_street", "residential"})


def is_hardstanding(tags: dict[str, str]) -> bool:
    """A closed way that is paved or built-over ground: parking, a pitch, a pedestrian area
    (``highway`` with ``area=yes``) or hardstanding landuse. Gardens, scrub and sand are not."""
    if tags.get("amenity") == "parking" or tags.get("leisure") == "pitch":
        return True
    if tags.get("landuse") in HARDSTANDING_LANDUSE:
        return True
    return tags.get("area") == "yes" and tags.get("highway") in AREA_HIGHWAYS


class SurfaceCover:
    """The E1 surface masks (``surfaces``: asphalt, paving, cobblestone, compacted earth) held in
    memory per near tile, to ask whether a position is on any painted surface."""

    def __init__(self, ways: list[surfaces.SurfaceWay]) -> None:
        self.masks: dict[tuple[int, int], npt.NDArray[np.uint8]] = {}
        for i, j in tiles.near_tiles():
            near = [w for w in ways if surfaces._touches(w, surfaces.tile_rect(i, j))]
            if not near:
                continue
            mask = surfaces.rasterise_tile(near, i, j)
            if mask.any():
                self.masks[(i, j)] = mask

    def covered(self, x: npt.ArrayLike, z: npt.ArrayLike) -> npt.NDArray[np.bool_]:
        x_a, z_a = np.asarray(x, dtype=np.float64), np.asarray(z, dtype=np.float64)
        out = np.zeros(x_a.shape, dtype=np.bool_)
        for (i, j), mask in self.masks.items():
            rect = surfaces.tile_rect(i, j)
            col = np.floor((x_a - rect.x_min) / surfaces.CELL_SIZE).astype(np.int64)
            row = np.floor((z_a - rect.z_min) / surfaces.CELL_SIZE).astype(np.int64)
            inside = (col >= 0) & (col < mask.shape[1]) & (row >= 0) & (row < mask.shape[0])
            out[inside] |= mask[row[inside], col[inside]].any(axis=1)
        return out


def surface_cover(osm: trail.OsmData) -> SurfaceCover:
    ways, _ = surfaces.select_ways(osm)
    return SurfaceCover(ways)


def exclusion_zone(osm: trail.OsmData, trail_path: Path) -> BaseGeometry:
    """Where no understory goes: the corridor, OSM paths, roads, buildings, hardstanding."""
    corridor = shapely.Polygon(
        json.loads(trail_path.read_text(encoding="utf-8"))["corridor"]["polygon"]
    )
    zones: list[BaseGeometry] = [corridor.buffer(CORRIDOR_CLEARANCE, quad_segs=8)]
    for way in osm.ways.values():
        nodes = [osm.xz[n] for n in way.nodes if n in osm.xz]
        if len(nodes) < 2:
            continue
        highway = way.tags.get("highway")
        closed = len(nodes) >= 4 and way.nodes[0] == way.nodes[-1]
        if closed and is_hardstanding(way.tags):
            zones.append(shapely.Polygon(nodes))
        elif highway is not None:
            clearance = FOOTPATH_CLEARANCE if highway in FOOTPATH_HIGHWAYS else ROAD_CLEARANCE
            zones.append(shapely.LineString(nodes).buffer(clearance, quad_segs=4))
        elif "building" in way.tags and len(nodes) >= 4 and way.nodes[0] == way.nodes[-1]:
            zones.append(shapely.Polygon(nodes).buffer(BUILDING_CLEARANCE, quad_segs=2))
    return shapely.unary_union(zones)


@dataclass(frozen=True)
class Cell:
    """A cell that holds understory: id, point count, median and 90th percentile height."""

    ix: int
    iz: int
    count: int
    median: float
    p90: float


def summarise_cells(points: "VegetationPoints") -> list[Cell]:
    """Class 3 and 4 points grouped by 4 m cell, in cell-id order."""
    keep = np.isin(points.lidar_class, UNDERSTORY_CLASSES)
    ix = np.floor(points.x[keep] / CELL).astype(np.int64)
    iz = np.floor(points.z[keep] / CELL).astype(np.int64)
    height = points.height[keep]
    if ix.size == 0:
        return []
    order = np.lexsort((height, iz, ix))
    ix, iz, height = ix[order], iz[order], height[order]
    change = np.nonzero((np.diff(ix) != 0) | (np.diff(iz) != 0))[0] + 1
    starts = np.concatenate([[0], change])
    ends = np.concatenate([change, [ix.size]])
    return [
        Cell(
            int(ix[s]),
            int(iz[s]),
            int(e - s),
            float(np.median(height[s:e])),
            float(np.percentile(height[s:e], 90)),
        )
        for s, e in zip(starts, ends, strict=True)
    ]


def model_for(median: float) -> int:
    if median >= TALL_SHRUB_FROM:
        return TALL
    return LOW if median >= LOW_SHRUB_FROM else GRASS


def candidates(cells: list[Cell]) -> dict[str, Floats]:
    """Up to two jittered instances per cell, before the area and exclusion filters."""
    ix = np.array([c.ix for c in cells], dtype=np.int64)
    iz = np.array([c.iz for c in cells], dtype=np.int64)
    count = np.array([c.count for c in cells], dtype=np.float64)
    p90 = np.array([c.p90 for c in cells], dtype=np.float64)
    model = np.array([model_for(c.median) for c in cells], dtype=np.float64)
    columns: dict[str, list[Floats]] = {k: [] for k in ("x", "z", "height", "yaw", "keep", "model")}
    for slot in range(2):
        salt = SALT_FIRST + slot * SALT_SLOTS
        floor = 0.0 if slot == 0 else POINTS_FOR_CERTAIN
        span = POINTS_FOR_CERTAIN if slot == 0 else POINTS_FOR_SECOND - POINTS_FOR_CERTAIN
        chance = np.clip((count - floor) / span, 0.0, 1.0)
        placed = unit_float(hash_cells(ix, iz, salt + 4)) < chance
        columns["x"].append(((ix + unit_float(hash_cells(ix, iz, salt))) * CELL)[placed])
        columns["z"].append(((iz + unit_float(hash_cells(ix, iz, salt + 1))) * CELL)[placed])
        columns["height"].append(np.clip(p90, MIN_HEIGHT, MAX_HEIGHT)[placed])
        columns["yaw"].append(np.floor(unit_float(hash_cells(ix, iz, salt + 2)) * 360.0)[placed])
        columns["keep"].append(np.floor(unit_float(hash_cells(ix, iz, salt + 3)) * 100.0)[placed])
        columns["model"].append(model[placed])
    return {k: np.concatenate(v) for k, v in columns.items()}


def instances(
    points: "VegetationPoints",
    grid: dem.Grid,
    area: BaseGeometry,
    exclusion: BaseGeometry,
    rejects: Sequence[Reject] = (),
) -> dict[str, Any]:
    """The understory instances (columnar), inside ``area`` and outside ``exclusion``."""
    found = candidates(summarise_cells(points))
    x, z = (
        np.round(found["x"], 2),
        np.round(found["z"], 2),
    )  # as written: filters see what is stored
    ground = grid.sample(x, z)
    ok = np.asarray(shapely.contains_xy(area, x, z), dtype=np.bool_)
    ok &= ~np.asarray(shapely.contains_xy(exclusion, x, z), dtype=np.bool_)
    for reject in rejects:
        ok &= ~reject(x, z)
    ok &= ground >= dem.SEA_LEVEL_TOLERANCE
    slope = dem.slope_at(dem.slope_degrees(grid), grid, x, z)
    habitat = (ground >= SILENE_BAND[0]) & (ground <= SILENE_BAND[1])
    ok &= ~(habitat & (slope >= SILENE_CLIFF_SLOPE))
    order = np.lexsort((x, z))
    order = order[ok[order]]
    return {
        "count": int(order.size),
        "x": [round(float(v), 2) for v in x[order]],
        "y": [round(float(v), 2) for v in ground[order]],
        "z": [round(float(v), 2) for v in z[order]],
        "height": [round(float(v), 2) for v in found["height"][order]],
        "scale": [
            round(float(h) / MODELS[int(m)].height, 3)
            for h, m in zip(found["height"][order], found["model"][order], strict=True)
        ],
        "yaw": [int(v) for v in found["yaw"][order]],
        "model": [int(v) for v in found["model"][order]],
        "keep": [int(v) for v in found["keep"][order]],
    }


def place(
    points: "VegetationPoints",
    grid: dem.Grid,
    area: BaseGeometry,
    exclusion: BaseGeometry,
    rejects: Sequence[Reject] = (),
) -> dict[str, Any]:
    """The understory block of ``vegetation.json``: the models and their instances."""
    return {
        "models": [model_description(m) for m in MODELS],
        **instances(points, grid, area, exclusion, rejects),
        "keepNote": "an instance is drawn when keep < 100 * density of the quality tier",
        "excluded": "corridor (ADR 0006) + clearance, OSM highways, OSM buildings, OSM parking / "
        "pedestrian areas / pitches / hardstanding landuse, every pixel of the E1 surface masks, "
        "cliffs of the Silene band",
    }


def protected_species_in(document: dict[str, Any]) -> list[str]:
    """Protected species named anywhere in ``document`` (must be empty)."""
    text = json.dumps(document)
    return [name for name in PROTECTED_SPECIES if name in text]
