"""Deterministic pseudo-random values keyed by cell id (no generator state, no visit order)."""

import numpy as np
import numpy.typing as npt

SEED = 20261011  # the one seed behind every pseudo-random placement choice (variants, jitter)

type Floats = npt.NDArray[np.float64]


def hash_cells(
    ix: npt.NDArray[np.int64], iz: npt.NDArray[np.int64], salt: int
) -> npt.NDArray[np.uint64]:
    """A splitmix64 hash of whole-metre cell ids: the same cell always gives the same value, in any
    order and on any run."""
    with np.errstate(over="ignore"):
        state = (
            ix.astype(np.uint64) * np.uint64(0x9E3779B97F4A7C15)
            + iz.astype(np.uint64) * np.uint64(0xC2B2AE3D27D4EB4F)
            + np.uint64(SEED)
            + np.uint64(salt) * np.uint64(0x165667B19E3779F9)
        )
        state = (state ^ (state >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        state = (state ^ (state >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        return state ^ (state >> np.uint64(31))


def unit_float(hashed: npt.NDArray[np.uint64]) -> Floats:
    """Uniform values in [0, 1) from the top 53 bits of a hash."""
    return (hashed >> np.uint64(11)).astype(np.float64) / float(1 << 53)
