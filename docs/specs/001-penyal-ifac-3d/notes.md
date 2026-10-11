# Research notes — 001 (2026-10-10)

Full proposal with map, architecture and phase plan: https://claude.ai/artifact/3Hf99ecPeJhcp4WSftym7K (private; share from its menu). The verified facts live in `content/facts.json`; this file keeps the technical findings that are not facts for the cards.

## Data sources tested
- **ICV downloads (no login, EPSG:25830, CC BY 4.0)** — headers read with HTTP range requests on 2026-10-10:
  - MDT 1 m 2016, sheet 0848: 29760×19550 px, float32, LZW, 1-row strips (not COG), nodata −9999, origin x 744640 / y 4284540, ~825 MB.
  - Orthophoto 2024 RGBI 25 cm, sheet 0848_7-2: 16040×11320 px, JPEG tiles of 512, covers x 766380–770390 / y 4279420–4282250 (no sea south of y ≈ 4279.42 km), ~173 MB.
  - LiDAR 2016 LAZ 2×2 km tiles `<xmin km>-<ymax km>`: 766-4282 (LAS 1.2, 1,904,351 points ≈ 0.48 pt/m², z max 328.07 m, z min −97 m = noise), 768-4282, 766-4280, 768-4280.
  - MDSnV (vegetation height) 1 m 2016, sheet 0848, ~491 MB (F3).
- **ICV WFS CV05**: `https://terramapas.icv.gva.es/0101_BCV05`, typeNames `CurvasNivelBCV05` (5 m), `PuntosCotaBCV05`, `EdificacionesBCV05`, `RedComunicacionesBCV05`, `ZonasArboladasBCV05`, `OrografiaLineasBCV05`; `outputFormat=application/json; subtype=geojson`; bbox in EPSG:25830 works.
- **ICV WMS orthophoto 2024**: `https://terramapas.icv.gva.es/0202_2024CVAL0025` layers `2024CVAL0025_RGB`, `2024CVAL0025_IRG`, max 4096×4096 per request.
- **CNIG/IGN**: unreachable on 2026-10-10/11. Candidates to check: LiDAR PNOA 3rd coverage (Comunitat Valenciana flown 2023-08 → 2024-06, 5 pt/m², 1 km tiles, zone token in the filename) and MDT50cm v1 (reportedly published 2026-06-29). Read the zone token (H30/H31) and reproject 25831 → 25830 if needed.
- **OSM**: API `map.json` by bbox works; Overpass main host unreliable, `lz4.overpass-api.de` works with a User-Agent.

## Trail geometry from OSM (lengths in plan, 2026-10-10)
| Segment | OSM way | Length |
|---|---|---|
| Centre steps (30 steps, handrail) | 26330269 | 17 m |
| Centre → tunnel | 26330273 | 724 m |
| Steps to the west portal | 862108208 | 17 m |
| Tunnel (`tunnel=yes`) | 26330275 | 49.2 m |
| Tunnel → bifurcation (node 288472006) | 26330276 (part) | 355 m |
| Bifurcation → summit | 34887788 | 535 m |
| Bifurcation → Mirador de Carabiners | 26330276 (rest) | 259 m |

Key nodes: summit 409151051 (38.634959 N, 0.074459 E → EPSG:25830 ≈ 767614, 4280754); Mirador de Carabiners 288472096; turnstile 8032598828; Centre d'Informació way 26330271 (≈ 767511, 4281051); la Pobla d'Ifac way 1159140951. Way 1557553367 (tunnel exit → summit, untagged `highway=path`) is not part of the official route.

## Measurements to reconcile in F1
- Summit: ICV spot height 325.8 m at (767615.67, 4280757.87), 4 m from the OSM peak; LiDAR max 328.07 m; official 332 m.
- Route 3D length and elevation gain from the DEM vs GVA (~2 km), MACMA (0.83 km, 173 m).

## Tooling facts (versions checked 2026-10-10)
three 0.186.1 (no `MSFT_lod` in GLTFLoader; basis transcoder in `examples/jsm/libs/basis/`), vite 8.3.4, typescript 7.0.2, vitest 5.0.3, zod 4.6.5, biome 2.5.15, three-mesh-bvh 0.9.16, @gltf-transform/cli 4.5.1, bpy 5.2.2 (Python 3.13), rasterio 1.5.2, suncalc 2.1.1. `postprocessing` 6.39.5 pins `three <0.187` (avoid).

## Assets shortlisted (licence checked by research, verify per file before use)
Poly Haven CC0 (`seaside_rock`, `rocky_trail`, `pine_tree_01`, shrubs, `grass_medium_02`; avoid `rock_face`/`cliff_side`, wrong colour), ambientCG CC0 `Rock030`, Quaternius Universal Animation Library CC0 (hiker animations), Sketchfab CC BY low-poly seagulls (credit required). Avoid: Mixamo, Ready Player Me (closed), Google Photorealistic 3D Tiles, NC/SA Sketchfab models, CC BY-SA photos as textures.
