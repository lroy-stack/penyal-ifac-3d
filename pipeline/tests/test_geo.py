import json

import numpy as np
import pytest

from penyal_pipeline import geo
from penyal_pipeline.paths import REPO_ROOT

FIXTURE = REPO_ROOT / "fixtures" / "geo" / "frame.json"


def _points() -> list[dict[str, float | str]]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["points"]


def test_fixture_has_the_required_points() -> None:
    names = {str(p["name"]) for p in _points()}
    assert {
        "osm-summit-409151051",
        "centre-informacio-way-26330271",
        "tunnel-west-portal",
        "tunnel-east-portal",
        "mirador-carabiners-288472096",
    } <= names


@pytest.mark.parametrize("point", _points(), ids=lambda p: str(p["name"]))
def test_fixture_matches_recomputation(point: dict[str, float]) -> None:
    e, n = geo.wgs84_to_25830(point["lat"], point["lon"])
    assert e == pytest.approx(point["e"], abs=0.0005)
    assert n == pytest.approx(point["n"], abs=0.0005)
    x, y, z = geo.to_local(point["e"], point["n"], point["h"])
    assert x == pytest.approx(point["x"], abs=0.0005)
    assert y == point["y"]
    assert z == pytest.approx(point["z"], abs=0.0005)


def test_osm_summit_lands_near_documented_utm_position() -> None:
    e, n = geo.wgs84_to_25830(38.634959, 0.074459)
    assert abs(e - 767614) < 1.0
    assert abs(n - 4280754) < 1.0


def test_local_frame_axes() -> None:
    assert geo.to_local(767000.0, 4280000.0, 5.0) == (0.0, 5.0, 0.0)
    x, y, z = geo.to_local(767100.0, 4280250.0, 7.0)
    assert (x, y, z) == (100.0, 7.0, -250.0)  # north is -Z


def test_round_trip_scalar_and_array() -> None:
    e, n, h = geo.from_local(*geo.to_local(767613.885, 4280754.151, 325.8))
    assert (e, n, h) == pytest.approx((767613.885, 4280754.151, 325.8), abs=1e-9)
    es = np.array([766400.0, 767613.885, 769000.0])
    ns = np.array([4279450.0, 4280754.151, 4282000.0])
    hs = np.array([-3.0, 325.8, 12.0])
    back = geo.from_local_array(*geo.to_local_array(es, ns, hs))
    for got, want in zip(back, (es, ns, hs), strict=True):
        np.testing.assert_allclose(got, want, atol=1e-9)


def test_array_variants_match_scalar_ones() -> None:
    lat = np.array([38.634959, 38.632359])
    lon = np.array([0.074459, 0.080352])
    es, ns = geo.wgs84_to_25830_array(lat, lon)
    for i in range(2):
        e, n = geo.wgs84_to_25830(float(lat[i]), float(lon[i]))
        assert (float(es[i]), float(ns[i])) == pytest.approx((e, n), abs=1e-6)
    xs, ys, zs = geo.to_local_array(es, ns)
    assert xs[0] == pytest.approx(es[0] - 767000.0)
    assert ys[0] == 0.0
    assert zs[0] == pytest.approx(-(ns[0] - 4280000.0))
