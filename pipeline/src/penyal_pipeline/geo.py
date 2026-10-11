"""Coordinate frames (ADR 0004).

The canonical frame is ETRS89 / UTM 30N (EPSG:25830). Rendering uses a local frame with the
origin at (E 767000, N 4280000): ``x = E - 767000``, ``y = H`` (orthometric metres) and
``z = -(N - 4280000)``, so that north is -Z. ``app/src/geo/frame.ts`` implements the same
transform and both are tested against ``fixtures/geo/frame.json``.
"""

from functools import lru_cache

import numpy as np
import numpy.typing as npt
from pyproj import Transformer

ORIGIN_E = 767000.0
ORIGIN_N = 4280000.0
EPSG_UTM30 = 25830

type FloatArray = npt.NDArray[np.float64]


def to_local(e: float, n: float, h: float = 0.0) -> tuple[float, float, float]:
    """EPSG:25830 easting/northing (+ height) to local ``(x, y, z)``."""
    return e - ORIGIN_E, h, -(n - ORIGIN_N)


def from_local(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Local ``(x, y, z)`` to EPSG:25830 ``(e, n, h)``."""
    return x + ORIGIN_E, -z + ORIGIN_N, y


def to_local_array(
    e: npt.ArrayLike, n: npt.ArrayLike, h: npt.ArrayLike = 0.0
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Vectorised :func:`to_local`; broadcasts its inputs."""
    e_a, n_a, h_a = np.broadcast_arrays(
        np.asarray(e, dtype=np.float64),
        np.asarray(n, dtype=np.float64),
        np.asarray(h, dtype=np.float64),
    )
    return e_a - ORIGIN_E, h_a.copy(), -(n_a - ORIGIN_N)


def from_local_array(
    x: npt.ArrayLike, y: npt.ArrayLike, z: npt.ArrayLike
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Vectorised :func:`from_local`; broadcasts its inputs."""
    x_a, y_a, z_a = np.broadcast_arrays(
        np.asarray(x, dtype=np.float64),
        np.asarray(y, dtype=np.float64),
        np.asarray(z, dtype=np.float64),
    )
    return x_a + ORIGIN_E, -z_a + ORIGIN_N, y_a.copy()


@lru_cache(maxsize=1)
def _wgs84_to_utm30() -> Transformer:
    return Transformer.from_crs("EPSG:4326", f"EPSG:{EPSG_UTM30}", always_xy=True)


def wgs84_to_25830(lat: float, lon: float) -> tuple[float, float]:
    """WGS84 latitude/longitude in degrees to EPSG:25830 ``(e, n)``."""
    e, n = _wgs84_to_utm30().transform(lon, lat)
    return float(e), float(n)


def wgs84_to_25830_array(lat: npt.ArrayLike, lon: npt.ArrayLike) -> tuple[FloatArray, FloatArray]:
    """Vectorised :func:`wgs84_to_25830`."""
    e, n = _wgs84_to_utm30().transform(
        np.asarray(lon, dtype=np.float64), np.asarray(lat, dtype=np.float64)
    )
    return np.asarray(e, dtype=np.float64), np.asarray(n, dtype=np.float64)
