"""What the vegetation was budgeted against (ADR 0010 section 3 and 4), shared by the generators.

The quality tiers set a vegetation density and a maximum distance; the budget table sets the draw
calls and triangles the whole vegetation system may use per colour pass. The level-of-detail
distances are fixed here as fractions of the tier distance so the app and the pipeline cannot
drift apart: ``vegetation.json``, ``pine.json`` and ``plants.json`` record what was checked.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Tier:
    density: float  # share of instances drawn (``keep < 100 * density``)
    distance: float  # metres, the farthest a tree is drawn
    calls: int  # ADR 0010 vegetation row: draw calls
    triangles: int  # ... and triangles, per colour pass


TIERS = {
    "low": Tier(0.35, 60.0, 20, 100_000),
    "medium": Tier(0.7, 120.0, 40, 250_000),
    "high": Tier(1.0, 200.0, 50, 400_000),
}
# Where each level ends, as a fraction of the tier distance: near mesh, mid mesh, far card.
TREE_LOD = (0.25, 7.0 / 12.0, 1.0)  # medium: 30 / 70 / 120 m
UNDERSTORY_LOD = (8.0 / 120.0, 24.0 / 120.0, 0.5)  # medium: 8 / 24 / 60 m
# Near and mid levels never reach further than at ``medium``: at ``high`` (200 m) the fractions
# alone gave 50 / 117 m, 649,874 triangles against the 400,000 row, so ``high`` spends its extra
# distance on far cards (4 triangles) only. The understory near / mid distances were 12 / 30 m
# until its instances followed the LiDAR points (clumped, 264,786 triangles at medium against
# 250,000): 8 / 24 m gives 239,940 (6 / 20 m would give 227,712).
TREE_LOD_CAP = (30.0, 70.0)
UNDERSTORY_LOD_CAP = (8.0, 24.0)
VIEWPOINT_SPACING = 5.0  # metres between the viewpoints the cost is sampled from


def tree_distances(tier: Tier) -> tuple[float, float, float]:
    return (
        min(tier.distance * TREE_LOD[0], TREE_LOD_CAP[0]),
        min(tier.distance * TREE_LOD[1], TREE_LOD_CAP[1]),
        tier.distance * TREE_LOD[2],
    )


def understory_distances(tier: Tier) -> tuple[float, float, float]:
    return (
        min(tier.distance * UNDERSTORY_LOD[0], UNDERSTORY_LOD_CAP[0]),
        min(tier.distance * UNDERSTORY_LOD[1], UNDERSTORY_LOD_CAP[1]),
        tier.distance * UNDERSTORY_LOD[2],
    )


def describe() -> dict[str, object]:
    """The budget assumptions as written into the generated JSON files."""
    return {
        "adr": "docs/adr/0010-world-systems-and-shared-contracts.md section 4",
        "viewpointSpacingM": VIEWPOINT_SPACING,
        "tiers": {
            name: {
                "density": tier.density,
                "distanceM": tier.distance,
                "drawCalls": tier.calls,
                "triangles": tier.triangles,
                "treeLodM": [round(d, 1) for d in tree_distances(tier)],
                "understoryLodM": [round(d, 1) for d in understory_distances(tier)],
            }
            for name, tier in TIERS.items()
        },
        "rule": "an instance is drawn when keep < 100 * density; trees use the mesh of the "
        "nearest level up to treeLodM (near, mid, far card), understory up to understoryLodM",
    }
