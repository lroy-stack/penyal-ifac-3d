import itertools
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import shapely
from conftest import raw_marks
from shapely.geometry import Point

from penyal_pipeline import artefacts, dem, trail
from penyal_pipeline.dem import DemBuild, Grid
from penyal_pipeline.geo import to_local
from penyal_pipeline.rawdata import locate
from penyal_pipeline.trail import OsmData, SegmentSpec, TrailError, TunnelSpec, Way

type Doc = dict[str, Any]

# --- pure functions on synthetic data ----------------------------------------------------------


def test_slice_way_forwards_and_backwards() -> None:
    nodes = (10, 11, 12, 13, 14)
    assert trail.slice_way(nodes, 11, 13) == [11, 12, 13]
    assert trail.slice_way(nodes, 13, 11) == [13, 12, 11]
    assert trail.slice_way(nodes, 12, 12) == [12]
    with pytest.raises(TrailError, match="not both on the way"):
        trail.slice_way(nodes, 11, 99)


def test_densify_keeps_vertices_and_caps_spacing() -> None:
    line = np.array([[0.0, 0.0], [2.5, 0.0], [2.5, 0.4]])
    out = trail.densify(line)
    assert out[0].tolist() == [0.0, 0.0]
    assert out[-1].tolist() == [2.5, 0.4]
    assert [2.5, 0.0] in out.tolist()
    assert float(np.linalg.norm(np.diff(out, axis=0), axis=1).max()) <= trail.MAX_STEP + 1e-9
    assert trail.path_length(out) == pytest.approx(2.9)


def test_ascent_counts_only_climbing() -> None:
    assert trail.ascent(np.array([0.0, 2.0, 1.0, 4.0])) == 5.0


def _ramp_grid() -> Grid:
    c = np.arange(100, dtype=np.float32)
    heights = np.tile(c * 0.5, (20, 1))  # 0.5 m per metre eastwards
    return Grid(heights, 0.5, 0.5)


TUNNEL = TunnelSpec(
    west_floor=171.0, east_floor=193.0, width=2.0, steps_ramp_start=8.0, east_blend=5.0
)


def test_drape_follows_the_dem() -> None:
    grid = _ramp_grid()
    xz = trail.densify(np.array([[10.0, 5.0], [30.0, 5.0]]))
    assert trail.drape(grid, xz)[[0, -1]] == pytest.approx([5.0 - 0.25, 15.0 - 0.25], abs=1e-6)


def test_tunnel_floor_is_linear_between_the_curated_portal_floors() -> None:
    xz = trail.densify(np.array([[10.0, 5.0], [30.0, 5.0]]))
    floor = trail.tunnel_heights(xz, 171.0, 193.0)
    assert floor[0] == 171.0
    assert floor[-1] == pytest.approx(193.0)
    assert np.all(np.diff(floor) > 0)
    assert floor[len(floor) // 2] == pytest.approx(182.0, abs=0.2)


def test_tunnel_floor_ignores_a_hump_in_the_dem() -> None:
    grid = _ramp_grid()
    grid.heights[:, 15:25] += 100.0
    xz = trail.densify(np.array([[10.0, 5.0], [30.0, 5.0]]))
    assert trail.tunnel_heights(xz, 171.0, 193.0).max() <= 193.0
    assert trail.drape(grid, xz).max() > 100.0


def test_steps_follow_the_dem_then_climb_straight_to_the_west_floor() -> None:
    grid = _ramp_grid()
    xz = trail.densify(np.array([[10.0, 5.0], [30.0, 5.0]]))
    y = trail.steps_heights(xz, grid, west_floor=20.0, ramp_start=8.0)
    draped = trail.drape(grid, xz)
    along = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(xz, axis=0), axis=1))])
    assert np.allclose(y[along <= 8.0], draped[along <= 8.0])
    assert y[-1] == 20.0
    ramp = y[along >= 8.0]
    assert np.allclose(np.diff(ramp, 2), 0.0, atol=1e-9), "the climb is a straight line"
    assert y[along <= 8.0][-1] == pytest.approx(ramp[0])


def test_steps_reject_a_ramp_start_outside_the_path() -> None:
    xz = trail.densify(np.array([[10.0, 5.0], [30.0, 5.0]]))
    with pytest.raises(TrailError, match="ramp start"):
        trail.steps_heights(xz, _ramp_grid(), west_floor=20.0, ramp_start=25.0)


def test_exit_starts_at_the_east_floor_and_fades_into_the_dem() -> None:
    grid = _ramp_grid()
    xz = trail.densify(np.array([[10.0, 5.0], [30.0, 5.0]]))
    y = trail.exit_heights(xz, grid, east_floor=6.0, blend=5.0)
    draped = trail.drape(grid, xz)
    along = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(xz, axis=0), axis=1))])
    assert y[0] == pytest.approx(6.0)
    assert np.allclose(y[along >= 5.0], draped[along >= 5.0])
    assert y[2] == pytest.approx(draped[2] + (6.0 - draped[0]) * 0.6)


def _toy_osm() -> OsmData:
    xz = {1: (0.0, 0.0), 2: (10.0, 0.0), 3: (10.0, -10.0), 4: (30.0, 0.0), 5: (10.0, -12.0)}
    ways = {100: Way((1, 2, 3), {}), 101: Way((4, 2), {})}
    return OsmData(xz=xz, node_tags={5: {"tourism": "viewpoint"}}, ways=ways)


def test_segment_polyline_follows_the_requested_direction() -> None:
    osm = _toy_osm()
    forward = trail.segment_polyline_2d(osm, SegmentSpec("a", "a", 100, 1, 3))
    backward = trail.segment_polyline_2d(osm, SegmentSpec("b", "b", 100, 3, 1))
    assert forward.tolist() == [[0.0, 0.0], [10.0, 0.0], [10.0, -10.0]]
    assert backward.tolist() == forward[::-1].tolist()
    with pytest.raises(TrailError, match="missing"):
        trail.segment_nodes(osm, SegmentSpec("c", "c", 999, 1, 2))


def _lateral_extent(corridor: shapely.Polygon, line: np.ndarray, k: int) -> float:
    """Half the corridor width across the line at vertex ``k`` (cross-section perpendicular)."""
    direction = line[k + 1] - line[k - 1]
    direction /= np.linalg.norm(direction)
    across = np.array([-direction[1], direction[0]])
    cut = shapely.LineString([line[k] - across * 5.0, line[k] + across * 5.0])
    piece = corridor.intersection(cut)
    return float(piece.length) / 2.0


def test_select_viewpoints_uses_the_distance_limit() -> None:
    osm = _toy_osm()
    near = shapely.LineString([(0.0, 0.0), (10.0, -10.0)])
    far = shapely.LineString([(-100.0, 0.0), (-90.0, 0.0)])
    assert trail.select_viewpoints(osm, near) == [5]
    assert trail.select_viewpoints(osm, far) == []


# --- the real route ----------------------------------------------------------------------------

OSM_FILE = "osm-penyal/osm-penyal.json"
ICV_SUMMIT = (767615.67, 4280757.87)


@pytest.fixture(scope="module")
def osm() -> OsmData:
    return trail.load_osm(locate("osm-penyal", "osm-penyal.json").path)


@pytest.fixture(scope="module")
def flat_dem() -> Grid:
    """A constant DEM covering the work area: geometry tests do not depend on terrain heights."""
    x0, z0 = dem.local_origin(dem.WORK_BBOX)
    return Grid(np.full((2550, 2600), 100.0, dtype=np.float32), x0, z0)


@pytest.fixture(scope="module")
def document(osm: OsmData, flat_dem: Grid) -> Doc:
    return trail.build_trail(osm, flat_dem, "sha", {"id": "dem"}, TUNNEL)


class TestRealRoute:
    pytestmark = raw_marks(OSM_FILE)

    def test_chain_is_connected(self, document: Doc) -> None:
        segments = {s["id"]: s["points"] for s in document["route"]["segments"]}
        main = [
            "access",
            "centre-steps",
            "centre-path",
            "portal-steps",
            "tunnel",
            "tunnel-bifurcation",
            "summit-ascent",
        ]
        for previous, following in itertools.pairwise(main[:-1]):
            assert segments[previous][-1] == segments[following][0], (previous, following)
        # The summit ascent and the Carabiners branch both leave from the bifurcation.
        assert segments["tunnel-bifurcation"][-1] == segments["summit-ascent"][0]
        assert segments["tunnel-bifurcation"][-1] == segments["carabiners-branch"][0]

    def test_segments_share_osm_nodes(self, osm: OsmData) -> None:
        ends = {
            spec.id: (trail.segment_nodes(osm, spec)[0], trail.segment_nodes(osm, spec)[-1])
            for spec in trail.SEGMENT_SPECS
        }
        assert ends["centre-path"][0] == ends["centre-steps"][1] == 288471765
        assert ends["portal-steps"][1] == trail.TUNNEL_WEST_NODE == ends["tunnel"][0]
        assert ends["tunnel"][1] == trail.TUNNEL_EAST_NODE == ends["tunnel-bifurcation"][0]
        assert ends["summit-ascent"][1] == trail.SUMMIT_NODE

    def test_excluded_way_is_not_used(self, document: Doc) -> None:
        used = {w for s in document["route"]["segments"] for w in s["osmWays"]}
        assert 1557553367 not in used
        assert {26330273, 862108208, 26330275, 26330276, 34887788} <= used

    def test_tunnel_length_is_49_metres(self, document: Doc) -> None:
        tunnel = next(s for s in document["route"]["segments"] if s["id"] == "tunnel")
        assert tunnel["length2d"] == pytest.approx(49.0, abs=1.0)

    def test_lengths_match_the_osm_table(self, document: Doc) -> None:
        for _, ids, osm_length in trail.REPORT_GROUPS:
            if osm_length is None:
                continue
            by_id = {s["id"]: s for s in document["route"]["segments"]}
            total = sum(by_id[i]["length2d"] for i in ids)
            assert total == pytest.approx(osm_length, abs=3.0), ids

    def test_points_are_at_most_one_metre_apart(self, document: Doc) -> None:
        for segment in document["route"]["segments"]:
            xz = np.array(segment["points"])[:, [0, 2]]
            assert float(np.linalg.norm(np.diff(xz, axis=0), axis=1).max()) <= 1.0 + 1e-6

    def test_every_trail_vertex_is_inside_the_corridor(self, document: Doc) -> None:
        corridor = shapely.Polygon(document["corridor"]["polygon"])
        for segment in document["route"]["segments"]:
            pts = np.array(segment["points"])
            assert shapely.covers(corridor, shapely.points(pts[:, 0], pts[:, 2])).all(), segment[
                "id"
            ]

    def test_corridor_contains_the_anchors_except_pobla(self, document: Doc) -> None:
        corridor = shapely.Polygon(document["corridor"]["polygon"])
        anchors = document["anchors"]
        assert {
            "centre",
            "turnstile",
            "tunnel-west",
            "tunnel-east",
            "bifurcation",
            "summit",
            "carabiners",
            "pobla",
        } <= set(anchors)
        for name, a in anchors.items():
            inside = corridor.covers(Point(a["x"], a["z"]))
            assert inside is (name != "pobla"), name

    def test_corridor_is_one_hole_free_simplified_polygon(self, osm: OsmData) -> None:
        corridor, viewpoints = trail.build_corridor(osm)
        assert corridor.geom_type == "Polygon"
        assert not corridor.interiors
        assert corridor.exterior.is_ccw
        assert set(viewpoints) == {288472097, 1795591637, 3635481353, 3635481356}
        assert 10_000 < corridor.area < 20_000

    def test_summit_anchor_is_at_the_osm_summit_near_the_icv_spot(self, document: Doc) -> None:
        summit = document["anchors"]["summit"]
        spot = to_local(*ICV_SUMMIT)
        # The OSM peak node is ~4 m from the ICV 1:5000 spot height (notes.md), not 2 m.
        distance = float(np.hypot(summit["x"] - spot[0], summit["z"] - spot[2]))
        assert distance == pytest.approx(4.1, abs=0.2)
        assert distance <= 5.0

    def test_tunnel_anchors_are_at_path_height(self, document: Doc) -> None:
        tunnel = next(s for s in document["route"]["segments"] if s["id"] == "tunnel")
        anchors = document["anchors"]
        assert [anchors["tunnel-west"][k] for k in "xyz"] == tunnel["points"][0]
        assert [anchors["tunnel-east"][k] for k in "xyz"] == tunnel["points"][-1]

    def test_tunnel_floor_endpoints_are_the_curated_heights(self, document: Doc) -> None:
        by_id = {s["id"]: s["points"] for s in document["route"]["segments"]}
        assert by_id["tunnel"][0][1] == TUNNEL.west_floor
        assert by_id["tunnel"][-1][1] == TUNNEL.east_floor
        assert by_id["portal-steps"][-1] == by_id["tunnel"][0]
        assert by_id["tunnel-bifurcation"][0] == by_id["tunnel"][-1]

    def test_the_corridor_inside_the_tunnel_is_the_width_minus_the_capsule(
        self, osm: OsmData, document: Doc
    ) -> None:
        corridor = shapely.Polygon(document["corridor"]["polygon"])
        tunnel = np.array(
            next(s for s in document["route"]["segments"] if s["id"] == "tunnel")["points"]
        )[:, [0, 2]]
        half = TUNNEL.width / 2.0 - trail.CAPSULE_RADIUS
        lateral = [
            _lateral_extent(corridor, tunnel, k)
            for k in range(
                int(trail.TRAIL_HALF_WIDTH) + 1, len(tunnel) - int(trail.TRAIL_HALF_WIDTH) - 1
            )
        ]
        # Cuts at the mid-bend vertex are a hair oblique to the offset edge: 1 mm slack.
        assert max(lateral) <= half + 1e-3
        assert min(lateral) >= half - 1e-3, "the strip is not narrower than needed either"

    def test_outside_the_tunnel_the_corridor_keeps_three_metres(self, osm: OsmData) -> None:
        corridor, _ = trail.build_corridor(osm, TUNNEL)
        steps = shapely.LineString(
            trail.segment_polyline_2d(
                osm, next(s for s in trail.SEGMENT_SPECS if s.id == "portal-steps")
            )
        )
        probe = steps.interpolate(steps.length / 2.0)
        assert corridor.contains(probe)
        assert corridor.exterior.distance(probe) == pytest.approx(trail.TRAIL_HALF_WIDTH, abs=0.3)

    def test_the_wide_buffers_do_not_spill_into_the_tunnel(self, osm: OsmData) -> None:
        corridor, _ = trail.build_corridor(osm, TUNNEL)
        tunnel = trail.segment_polyline_2d(
            osm, next(s for s in trail.SEGMENT_SPECS if s.id == "tunnel")
        )
        direction = (tunnel[1] - tunnel[0]) / np.linalg.norm(tunnel[1] - tunnel[0])
        across = np.array([-direction[1], direction[0]])
        spill = shapely.Point(tunnel[0] + direction * 2.0 + across * 2.0)
        assert not corridor.contains(spill)

    def test_licence_and_provenance(self, document: Doc) -> None:
        assert document["licence"] == "ODbL-1.0"
        assert document["attribution"] == "© OpenStreetMap contributors"
        assert document["source"] == {"id": "osm-penyal", "sha256": "sha"}
        assert document["frame"]["origin"] == {"e": 767000, "n": 4280000}


@pytest.fixture(scope="module")
def real_build() -> DemBuild:
    return dem.build_dem(*dem.locate_inputs())


@pytest.fixture(scope="module")
def built(real_build: DemBuild, tmp_path_factory: pytest.TempPathFactory) -> Doc:
    out = tmp_path_factory.mktemp("trail") / "trail.json"
    document = trail.run_trail(
        real_build.grid, real_build.source, (out,), TUNNEL, artefacts.provenance("trail")
    )
    assert json.loads(out.read_text(encoding="utf-8")) == json.loads(json.dumps(document))
    return document


class TestRealRouteOnTheRealDem:
    pytestmark = raw_marks(OSM_FILE, "icv-mdt-2016-0848/*.tif", "icv-cv05-penyal/*.geojson")

    def test_draped_heights_follow_the_dem_outside_the_tunnel(
        self, built: Doc, real_build: DemBuild
    ) -> None:
        for segment in built["route"]["segments"]:
            pts = np.array(segment["points"])
            expected = real_build.grid.sample(pts[:, 0], pts[:, 2])
            along = np.concatenate(
                [[0.0], np.cumsum(np.linalg.norm(np.diff(pts[:, [0, 2]], axis=0), axis=1))]
            )
            if segment["id"] == "tunnel":
                continue
            if segment["id"] == "portal-steps":
                free = along <= TUNNEL.steps_ramp_start
            elif segment["id"] == "tunnel-bifurcation":
                free = along >= TUNNEL.east_blend
            else:
                free = np.ones(len(pts), dtype=bool)
            assert np.abs(pts[free, 1] - expected[free]).max() < 0.02, segment["id"]

    def test_the_west_climb_never_drops_and_ends_at_the_curated_floor(self, built: Doc) -> None:
        steps = np.array(
            next(s for s in built["route"]["segments"] if s["id"] == "portal-steps")["points"]
        )
        assert steps[-1, 1] == TUNNEL.west_floor
        ramp = steps[len(steps) - 9 :, 1]
        assert np.all(np.diff(ramp) >= -1e-9)

    def test_tunnel_is_linear_between_the_portal_heights(self, built: Doc) -> None:
        tunnel = np.array(
            next(s for s in built["route"]["segments"] if s["id"] == "tunnel")["points"]
        )
        along = np.concatenate(
            [[0.0], np.cumsum(np.linalg.norm(np.diff(tunnel[:, [0, 2]], axis=0), axis=1))]
        )
        line = tunnel[0, 1] + (tunnel[-1, 1] - tunnel[0, 1]) * along / along[-1]
        assert np.abs(tunnel[:, 1] - line).max() < 2e-3

    def test_records_the_inputs_and_tools_it_was_built_from(self, built: Doc) -> None:
        files = {entry["file"] for entry in built["inputs"]}
        assert "data/curated/tunnel.toml" in files
        assert any(f.startswith("data/raw/osm-penyal/") for f in files)
        assert set(built["tools"]) == {"numpy", "shapely"}

    def test_summit_anchor_height_is_the_dem_height(self, built: Doc) -> None:
        assert built["anchors"]["summit"]["y"] == pytest.approx(325.4, abs=1.0)
        assert built["demSource"]["id"] == "icv-mdt-2016-0848"

    def test_output_is_deterministic(
        self, built: Doc, real_build: DemBuild, tmp_path: Path
    ) -> None:
        again = trail.run_trail(
            real_build.grid,
            real_build.source,
            (tmp_path / "t.json",),
            TUNNEL,
            artefacts.provenance("trail"),
        )
        assert again == built
