# 0009. Allow evidence-backed local terrain corrections where a 2.5D DEM cannot represent the ground

- Status: accepted (refines 0004)
- Date: 2026-10-11
- Deciders: tech lead (to be confirmed by the product owner in the F1 report)

## Context
ADR 0004 says the terrain is never offset or scaled to match a published figure. At the west tunnel portal the 1 m MDT puts the last 8 m of the approach 4–11 m above the trail: a 2.5D grid at the foot of a vertical wall mixes the wall into the ground cells. LiDAR 2016 ground returns along the approach (median 168.74 m), the DEM a few metres further out (median 168.89 m) and the 6 OSM steps point to a floor at ≈ 169.9–171 m (see `data/curated/tunnel.toml`). With the raw DEM the tunnel mouth stays buried and the player would float metres above the visible ground.

## Options considered
1. **Keep the raw DEM everywhere** — purest, but the official route becomes impossible to walk and the portal invisible.
2. **Evidence-backed local corrections** — lower the terrain only where independent evidence (LiDAR ground points, OSM structure tags, survey) shows the DEM misrepresents the ground because of the 2.5D limit, in the smallest area needed, recorded as curated data with the evidence and flagged as approximate.
3. **Hide the problem** (e.g. teleport through the tunnel) — dishonest and breaks the walk.

## Decision
Option 2. A correction is allowed only when (a) the cause is a representational limit of the DEM (overhang, tunnel, wall foot), not a disagreement with a published number; (b) independent measured evidence supports the corrected height; (c) it is defined in `data/curated/` with the evidence, the affected cells and the maximum change; (d) it is listed under "Approximations" in `CREDITS.md`; (e) tests prove it stays local. First use: the west tunnel approach carve (6 m strip, 39 cells, max −13.3 m), applied to the visual tiles and the collision grid.

## Consequences
- The summit and every other area keep the raw DEM; the 332 m vs 326.9 m discrepancy stays visible and explained.
- Each correction is reversible by removing its curated entry and rebuilding.
- Corrections must be revisited when better data arrives (CNIG 3rd-coverage LiDAR, the user's site measurements, the park).
