# 0004. Work in EPSG:25830 with a local origin, and never adjust terrain to official figures

- Status: accepted
- Date: 2026-10-11
- Deciders: tech lead

## Context
The ICV delivers all its data for the Comunitat Valenciana in ETRS89 / UTM 30N (EPSG:25830), even east of the 0° meridian where the Penyal sits (x ≈ 767.6 km). CNIG tile products may come in zone 31 (EPSG:25831); the datum is the same, so a zone change needs no datum shift. Absolute UTM coordinates (~10⁶ m) lose centimetres in float32 on the GPU. Heights in the ICV and CNIG models are orthometric. The official summit altitude is 332 m, but the ICV 1:5000 spot height at the summit is 325.8 m and the highest 2016 LiDAR point is 328.07 m.

## Options considered
1. **EPSG:25830 as the canonical frame + local origin (767000, 4280000), Y-up, metres; reproject anything else into it** — float32 keeps millimetre precision over the ~2.5 km area; one frame for Python and TS.
2. **Geographic coordinates (WGS84) with an ENU tangent plane** — more general, but every official dataset would be reprojected and ICV vectors would lose their native grid alignment.

## Decision
Option 1. Local frame: `x = E − 767000`, `y = H` (orthometric metres), `z = −(N − 4280000)` so that north is −Z, matching three.js conventions. The terrain is built from the DEM as is; it is never scaled or offset to match a published figure. Discrepancies are shown in the cards with both values.

## Consequences
- `penyal_pipeline.geo` and `app/src/geo/frame.ts` implement the same transform and are tested against a shared fixture.
- Zone-31 inputs are reprojected to 25830 at ingest; the manifest records the original CRS.
- The far horizon ring (tens of km) is the only geometry far from the origin; it is rendered at low precision on purpose.
