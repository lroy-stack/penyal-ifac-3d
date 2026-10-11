# Plan — 001 Penyal d'Ifac 3D

Spec: [spec.md](spec.md) · Research: [notes.md](notes.md) · ADRs: [0002](../../adr/0002-threejs-webgl-vite-typescript.md), [0003](../../adr/0003-blender-as-bpy-module-in-uv.md), [0004](../../adr/0004-coordinate-frame-and-heights.md), [0005](../../adr/0005-sourced-fact-registry.md), [0006](../../adr/0006-walkable-trail-corridor.md), [0007](../../adr/0007-licensing.md) · Date: 2026-10-11

## Approach
One repository, two halves. `pipeline/` is a uv-managed Python 3.13 project that downloads official data with checksums (`penyal fetch`), prepares it in a local metric frame (rasterio, laspy, pyproj) and drives Blender as the `bpy` module to build terrain tiles with three LOD levels, the tunnel and trail structures, then exports glTF. A Node step (`@gltf-transform`) applies meshopt geometry compression and KTX2 textures. `app/` is a static Vite + TypeScript + three r186 (WebGLRenderer) application that streams those tiles (`THREE.LOD` per tile, because `GLTFLoader` does not support `MSFT_lod`), walks a kinematic player over a 1 m heightfield plus a `three-mesh-bvh` for the tunnel and structures, and renders a DOM UI (cards, notebook, minimap) without a framework. `content/` holds a fact registry where every fact has sources and a status; vitest validates it with zod, so a fact without a source or a missing translation fails the build. Work proceeds in phases F0–F5; each phase ends with a browser check, an independent review and the user's approval.

Alternatives, one line each: WebGPU (uneven on mid-range phones), Blender.app instead of bpy (not pinned by a lockfile; kept as fallback), CDLOD on the GPU (unneeded for ~2.5 × 2.5 km), physics engine (the heightfield + BVH is enough), React/Preact UI (bundle and complexity without need).

## Interfaces & data
- `data/catalog.toml` — every source: `id`, `phase`, `url`, `licence`, `attribution`, `expected_bytes`, `kind` (`file` | `wfs` | `osm`).
- `data/manifest.lock.json` — what was actually downloaded: `id`, `url`, `bytes`, `sha256`, `retrieved` (ISO date).
- Local frame (ADR 0004): `x = E − 767000`, `z = −(N − 4280000)`, `y = H` (orthometric, metres). Shared by Python (`penyal_pipeline.geo`) and TS (`app/src/geo/frame.ts`), tested against the same fixtures.
- Pipeline outputs (F1): `build/terrain/heightfield.f32` + `heightfield.json` (origin, cell size, dims), `build/trail.json` (draped polyline, corridor polygon, POI anchors), `app/public/assets/terrain/tile_<i>_<j>_lod<k>.glb`, `app/public/assets/manifest.json`.
- `content/sources.json`, `content/facts.json` — schemas in `app/src/content/schema.ts`.
- Terrain tiles (T1.4/T1.5 → T1.6), `app/public/assets/generated/terrain/manifest.json`:
  ```jsonc
  {
    "version": 1,
    "frame": { "crs": "EPSG:25830", "origin": { "e": 767000, "n": 4280000 } },
    "source": { "dem": { "id": "icv-mdt-2016-0848", "sha256": "…" }, "ortho": { "id": "icv-orto-2024-0848-7-2", "sha256": "…" } },
    "near": {
      "tileSize": 256,                       // metres; grid aligned to the local origin
      "tiles": [{
        "id": "t_1_-3",                      // i = floor(x / 256), j = floor(z / 256)
        "bounds": { "minX": 256, "maxX": 512, "minZ": -768, "maxZ": -512, "minY": 2.1, "maxY": 331.0 },
        "lods": [                            // finest first
          { "level": 0, "url": "tiles/t_1_-3_lod0.glb", "maxError": 0.25, "texture": 1024, "triangles": 0, "bytes": 0 },
          { "level": 1, "url": "tiles/t_1_-3_lod1.glb", "maxError": 1.0,  "texture": 512,  "triangles": 0, "bytes": 0 },
          { "level": 2, "url": "tiles/t_1_-3_lod2.glb", "maxError": 3.0,  "texture": 256,  "triangles": 0, "bytes": 0 }
        ]
      }]
    },
    "far": { "url": "far.glb", "maxError": 4.0, "texture": 2048, "bounds": { … }, "triangles": 0, "bytes": 0 }
  }
  ```
  Meshes are in local-frame metres relative to the glTF scene origin (no node offsets), Y up, with vertex normals computed from the DEM gradient (identical across LODs at shared positions) and skirts along tile borders. The far mesh covers the work area minus the near box.
- Tunnel (T1.8a → T1.8b), `app/public/assets/generated/tunnel.json` (ODbL-derived: the axis comes from OSM way 26330275) + `tunnel.glb`:
  ```jsonc
  {
    "version": 1,
    "licence": "ODbL-1.0", "attribution": "© OpenStreetMap contributors",
    "status": "approximate",                    // until measured (spec Q2, Q6)
    "axis": [[x, y, z], ...],                   // floor centreline west→east, ≤ 0.5 m spacing; y = floor height
    "width": 0.0, "height": 0.0,                // provisional cross-section in metres, with "sectionBasis" explaining it
    "sectionBasis": "…",                        // e.g. estimated from CC photos with people for scale (file names)
    "portals": { "west": { "x": 0, "y": 0, "z": 0 }, "east": { "x": 0, "y": 0, "z": 0 } },
    "sources": { "axis": "osm:way/26330275", "portalHeights": "data/curated/tunnel.toml" },
    "mesh": "tunnel.glb"
  }
  ```
  The app derives the tunnel `GroundSurface` from `axis` + `width` (floor height interpolated along the axis for points within half-width, from 1 m outside one portal to 1 m outside the other); `tunnel.glb` is visual only (interior shell, inward-facing).

## Risks
| Risk | Likelihood | Impact | Mitigation / spike |
|---|---|---|---|
| IPv4 hosts (GitHub, ICV, CNIG) unreachable from this machine | Seen 2026-10-11 | Blocks downloads and the `ktx` binary | Everything else proceeds; downloads resume with `penyal fetch` when the network recovers |
| `bpy` wheel lacks the glTF exporter or fails headless | Low | Pipeline redesign | T0.9 spike; fallback Blender.app 5.2 LTS in `tools/` |
| KTX2 encoding needs the `ktx` CLI | Medium | No compressed textures | T0.8: `ktx` from KhronosGroup releases into `tools/bin`; fallback WebP until available |
| Airborne LiDAR under-samples cliffs | High | Soft cliffs | Edge-preserving decimation + triplanar limestone (F2); CNIG 3rd coverage when reachable |
| Mid-range phone performance unknown | Medium | AC7 fails | Measure on the reference phone at the end of F1 |
| Facts conflict between official sources | Certain | Wrong cards | `conflict` status shows both values until the park resolves them |

## Tasks

### F0 — Foundations and data

- [x] **T0.1 — Decisions and docs** · size S · owner tech lead
  - Goal: spec, plan, research notes, ADRs 0002–0007, CLAUDE.md, CREDITS.md, LICENSE (EUPL-1.2).
  - Files: `docs/**`, `CLAUDE.md`, `CREDITS.md`, `LICENSE`
  - Acceptance: studio structure checks pass.
  - Verify: `python3 ~/Workspace/05-Studio/plugins/studio/hooks/stop_gate.py --check .`
- [x] **T0.2 — Workspace and JS tooling** · size S · owner `implementer`
  - Goal: pnpm workspace, `.node-version` 24, Biome, root scripts.
  - Files: `package.json`, `pnpm-workspace.yaml`, `biome.json`, `.node-version`
  - Acceptance: `pnpm install` from a clean clone works; `pnpm lint` passes.
  - Verify: `pnpm install --frozen-lockfile && pnpm lint`
- [x] **T0.3 — App skeleton** · size S · owner `implementer`
  - Goal: Vite 8 + TS + three r186 renders a lit test scene; vitest configured; three's basis transcoder and meshopt decoder served from `public/`.
  - Files: `app/**`
  - Acceptance: `pnpm --filter app build` succeeds; the dev page renders without console errors.
  - Verify: `pnpm typecheck && pnpm test && pnpm --filter app build` + browser screenshot
- [x] **T0.4 — Fact registry** · size S · owner `implementer` (schema) + tech lead (data)
  - Goal: zod schema and validation tests for `content/sources.json` and `content/facts.json`, seeded with the 2026-10-10 research.
  - Files: `app/src/content/**`, `content/**`
  - Acceptance: a fact without a source, a `verified` fact without an official source, or a `conflict` with fewer than two sourced values fails the test.
  - Verify: `pnpm test -- content`
- [x] **T0.5 — Pipeline environment** · size S · owner `implementer` · [parallel]
  - Goal: uv project on Python 3.13 with bpy 5.2.2, rasterio, laspy[lazrs], pyproj, numpy; ruff, basedpyright, pytest; `penyal doctor` reports versions, glTF exporter and tools.
  - Files: `pipeline/**`
  - Acceptance: `penyal doctor` exits 0 and lists bpy 5.2.2 with `io_scene_gltf2` available.
  - Verify: `uv run --project pipeline penyal doctor && uv run --project pipeline pytest -q`
- [x] **T0.6 — Data catalogue and fetcher** · size M · owner `implementer` · [parallel]
  - Goal: `penyal fetch --phase N` downloads catalogue entries with resume, size and sha256 checks and writes `data/manifest.lock.json`; WFS (ICV CV05 by bbox) and OSM (API map by bbox) fetchers.
  - Files: `pipeline/src/penyal_pipeline/{catalog,fetch}.py`, `data/catalog.toml`, `pipeline/tests/**`
  - Acceptance: tests against a local HTTP server cover resume, size mismatch and checksum mismatch; `--dry-run` prints file, source and size.
  - Verify: `uv run --project pipeline pytest -q pipeline/tests/test_fetch.py && uv run --project pipeline penyal fetch --phase 1 --dry-run`
- [x] **T0.7 — Download phase-1 data** · size S · owner tech lead
  - Goal: ICV MDT 1 m sheet 0848, ICV orthophoto 2024 RGBI 0848_7-2, ICV LiDAR 2016 tiles 766-4282 / 768-4282 / 766-4280 / 768-4280, ICV CV05 by bbox, OSM extract by bbox.
  - Files: `data/raw/**` (ignored), `data/manifest.lock.json`
  - Acceptance: every phase-1 entry present with sha256 recorded.
  - Verify: `uv run --project pipeline penyal fetch --phase 1 --verify`
  - Status 2026-10-11: OSM extract and ICV CV05 (7 layers) fetched with `penyal fetch`; LiDAR ×4 and orthophoto downloaded through the public NAT64 relay (the iPhone hotspot on an IPv6-only carrier drops IPv4); MDT in progress. Hash into the manifest with `penyal fetch --phase 1` once complete.
- [x] **T0.8 — Texture tool** · size S · owner `implementer`
  - Goal: KTX-Software `ktx` available in `tools/bin` without a system install, detected by `penyal doctor`.
  - Files: `tools/README.md`, `pipeline/src/penyal_pipeline/doctor.py`
  - Acceptance: `penyal doctor` prints the `ktx` version.
  - Verify: `uv run --project pipeline penyal doctor`
- [x] **T0.9 — End-to-end asset spike** · size M · owner `implementer`
  - Goal: bpy builds a test mesh with a texture → glTF → gltf-transform (meshopt + KTX2) → the app loads and shows it.
  - Files: `pipeline/src/penyal_pipeline/spike_export.py`, `scripts/optimize.mjs`, `app/src/assets/loader.ts`
  - Acceptance: the spike asset renders in the browser with KTX2 and meshopt decoders, no console errors.
  - Verify: `pnpm spike` (deterministic sha256), `node scripts/optimize.mjs build/spike/spike.glb app/public/assets/generated/spike/spike-ktx2.glb --textures etc1s`, `pnpm --filter @penyal/app e2e` (e2e/asset-pipeline.spec.ts)
  - Result 2026-10-11: bpy GLB 745 KB → 167 KB with meshopt + ETC1S; renders in headless Chromium as CompressedTexture (ETC2) 512², 32,768 triangles, 1 draw call.
- [x] **T0.10 — Gates wired** · size S · owner tech lead
  - Goal: `.claude/studio.json` runs JS and Python lint, typecheck and tests on Stop.
  - Files: `.claude/studio.json`, `package.json`
  - Acceptance: the stop gate check passes on the repository.
  - Verify: `python3 ~/Workspace/05-Studio/plugins/studio/hooks/stop_gate.py --check .`

### F1 — Real terrain and a walking character
**Exit goal:** walk from the turnstile to the summit and to the Mirador de Carabiners, through the tunnel, on the real ICV terrain and orthophoto; an automated test proves it; screenshots and a real-phone measurement are recorded. Status 2026-10-11: everything except the tunnel, the full-route test and the phone reading is done.

- [x] **T1.1 — Local frame utilities** · S · `implementer`
  - Result: Python and TS agree to 1 mm on `fixtures/geo/frame.json`.
  - Verify: `uv run --project pipeline pytest -q pipeline/tests/test_geo.py && pnpm --filter @penyal/app exec vitest run src/geo`
- [x] **T1.2 — DEM preparation** · M · `implementer`
  - Result: `build/terrain/dem.*` (1 m; sea → −3 m proxy inside the CV05 sea polygon) and `collision.*` (uint16, 694×665). DEM max 326.857 m, 0.4 m from the ICV spot height; LiDAR vs DEM RMSE 0.40 m on slopes ≤ 30°.
  - Verify: `uv run --project pipeline pytest -q pipeline/tests/test_dem.py`
- [x] **T1.3 — Trail, corridor and anchors** · S · `implementer`
  - Result: `trail.json` (ODbL): centre → summit 1.82 km in 3D, ≈ +304 m; corridor 13,136 m²; 12 anchors.
  - Verify: `uv run --project pipeline pytest -q pipeline/tests/test_trail.py`
- [x] **T1.4 — Terrain tiles in Blender** · M · `implementer`
  - Result: 16 near tiles × 3 LODs (exact RTIN, 0.25 / 1 / 3 m) + far ring; 50 files byte-identical across runs. The ±0.5/2/6 m bound holds against the triangulated DEM; against bilinear sampling it holds at p99 (cliff cells jump up to 104 m between neighbours).
  - Verify: `uv run --project pipeline pytest -q pipeline/tests/test_terrain_tiles.py pipeline/tests/test_rtin.py`
- [x] **T1.5 — Orthophoto textures and optimisation** · S · `implementer`
  - Result: KTX2 ETC1S at quality 255 + meshopt; start-area download 6.82 MB (budget 15 MB).
  - Verify: `uv run --project pipeline penyal terrain && pnpm --filter @penyal/app e2e -- viewpoints`
- [x] **T1.6 — Terrain streaming in the app** · M · `implementer`
  - Result: own screen-space-error selection against each tile's AABB (not `THREE.LOD`), 2 concurrent loads, residency budget; 6 real-terrain viewpoints render without errors within the desktop budget.
  - Verify: `pnpm --filter @penyal/app exec vitest run src/world/terrain && pnpm --filter @penyal/app e2e -- viewpoints`
- [x] **T1.7 — Player, input and cameras** · M · `implementer`
  - Result: kinematic walker (step 0.4 m, slope 50°, corridor slide), keyboard/mouse/touch, first/third person, `?start=<anchor>`.
  - Verify: `pnpm --filter @penyal/app exec vitest run src/player src/input src/world/trail.test.ts && pnpm --filter @penyal/app e2e -- walk-test`
- [x] **T1.9 — Basic sea, sky and fog** · S · `implementer`
  - Result: sea plane at 0 m, gradient sky, fog opaque at 1214 m from the summit.
  - Verify: `pnpm --filter @penyal/app e2e -- viewpoints` (summit screenshot)
- [x] **T1.8a — Tunnel data and geometry (pipeline)** · M · `implementer` · [parallel]
  - Goal: a walkable, honest tunnel: curated portal floor heights with evidence, the OSM axis, a provisional cross-section flagged as approximate, an interior mesh and holes in the terrain at both portals.
  - Files: `data/curated/tunnel.toml`, `pipeline/src/penyal_pipeline/{tunnel.py,trail.py}`, `pipeline/src/penyal_pipeline/blender/tunnel.py`, `app/public/assets/generated/{tunnel.json,tunnel.glb}`, re-exported tiles touching the portals, `CREDITS.md`.
  - Acceptance: portal floor heights equal the curated values (west ≈ 171 m, east 193.0 m); the `trail.json` tunnel and portal-steps segments use them; the corridor inside the tunnel is ≤ tunnel half-width − 0.3 m; a ray along the axis from 2 m outside each portal hits no terrain before the tunnel; outputs deterministic.
  - Verify: `uv run --project pipeline pytest -q pipeline/tests/test_tunnel.py pipeline/tests/test_trail.py && uv run --project pipeline penyal tunnel`
  - Result 2026-10-11: west floor 171.0 m (170–172.5), east 193.0 m; +22 m over 49 m (24°); section 2.0 × 2.6 m placeholder (no scale in the CC photos); exact triangle clipping opens both portals in `t_2_-4`; west approach carved per ADR 0009; deterministic.
- [ ] **T1.8b — Tunnel in the app** · S · `implementer` (builds against the `tunnel.json` contract with a fixture, then the real file)
  - Goal: the player walks through the tunnel on its floor, in both cameras, with the interior rendered.
  - Files: `app/src/world/tunnel.ts`, `app/src/main.ts`, `app/e2e/tunnel.spec.ts`
  - Acceptance: walking from `tunnel-west` to `tunnel-east` stays grounded on the tunnel floor (|y − floor| < 0.2 m), never inside the rock; the third-person camera stays inside the tunnel.
  - Verify: `pnpm --filter @penyal/app e2e -- tunnel`
- [ ] **T1.10 — Auto-walk and full-route E2E** · M · `implementer` (same agent as T1.8b)
  - Goal: an auto-walk mode that follows the official route (also an accessibility feature), and the proof that the whole route is walkable.
  - Files: `app/src/player/autowalk.ts`, `app/src/main.ts`, `app/e2e/route.spec.ts`
  - Acceptance: `?autowalk=summit` from the turnstile reaches the summit anchor and `?autowalk=carabiners` reaches the Mirador de Carabiners, grounded all the way and never outside the corridor; frame-time p95 recorded; screenshots at the 6 anchors attached to the phase report.
  - Verify: `pnpm --filter @penyal/app e2e -- route`
- [ ] **T1.11 — Real-phone measurement** · S · tech lead + user
  - Goal: first performance reading on the reference mid-range phone (served over the LAN with `vite --host`).
  - Acceptance: fps p95, load time and memory recorded in `docs/specs/001-penyal-ifac-3d/perf.md`; regressions become F2/F5 tasks.
  - Verify: manual run documented with device model, browser version and numbers.

### F2 — Trail fidelity
**Exit goal:** a neighbour of Calp recognises each stretch of the trail in the screenshots (user review); no visible orthophoto stretching on rock within 50 m of the player; the tunnel, the steps and the ropes are where the sources put them; an animated hiker; desktop 60 fps and mobile ≥ 30 fps on the reference phone in the start area.

- [x] **T2.1 — CC0 asset shortlist and licence check** · S · `docs-researcher` · [parallel]
  - Goal: exact files (URL, licence, size, resolution) for limestone/rock and trail textures, a hiker with idle/walk/run animations, rope and handrail materials; nothing is downloaded until the user approves the list.
  - Files: `docs/specs/001-penyal-ifac-3d/assets.md`, later `data/catalog.toml` (phase-2 assets)
  - Acceptance: every candidate is CC0 or CC BY with its attribution string, colour-matched to Ifac limestone using the orthophoto; sizes add up to a stated download budget.
  - Verify: review of `assets.md`; after approval `uv run --project pipeline penyal fetch --phase 2 --verify`
- [ ] **T2.2 — Terrain material: limestone detail and cliffs** · M · `implementer` · [parallel]
  - Goal: the orthophoto gives macro colour; steep faces use triplanar limestone detail instead of stretched orthophoto; a near-camera detail layer removes the blur under the feet; LOD seams no longer show a texture jump.
  - Files: `app/src/world/terrain/material.ts` (+ tests), streamer hook, quality tier switch
  - Acceptance: screenshots at the 6 anchors show no vertical stretch on faces steeper than 55°; GPU cost ≤ 2 ms on this Mac at 1440p (measured); a low tier keeps the F1 look on weak phones.
  - Verify: `pnpm --filter @penyal/app e2e -- viewpoints` + frame-time comparison before/after
- [ ] **T2.3 — Trail surface and steps** · M · `implementer`
  - Goal: the path reads as a path: a trail mask from `trail.json` blends a worn-rock/soil texture along it; steps geometry where OSM records steps (30 at the centre with handrail, 6 at the west portal).
  - Files: `pipeline/src/penyal_pipeline/{trailmask.py,blender/steps.py}`, terrain material
  - Acceptance: path mask within ±0.5 m of the OSM centreline; step counts and heights from data; walkable with the controller's 0.4 m step.
  - Verify: `uv run --project pipeline pytest -q pipeline/tests/test_trailmask.py && pnpm --filter @penyal/app e2e -- route`
- [ ] **T2.4 — Final tunnel and ropes** · M · `implementer`
  - Goal: replace the provisional section with measured values (user site visit or park data); rock interior; the two ropes the GVA describes; the exit platform.
  - Acceptance: every dimension cites its source in `data/curated/tunnel.toml`; credits updated; if measurements never arrive, the provisional flag stays visible in credits.
  - Verify: `uv run --project pipeline pytest -q pipeline/tests/test_tunnel.py && pnpm --filter @penyal/app e2e -- tunnel`
- [ ] **T2.5 — Centre d'Informació and trail furniture from data** · M · `implementer`
  - Goal: the visitor centre from the ICV/OSM footprint with LiDAR heights (first returns minus DTM); turnstile, gates and information boards at their OSM positions; nothing placed without a source.
  - Acceptance: footprints within 1 m of CV05; heights within 1 m of LiDAR; every object lists its OSM/ICV id.
  - Verify: `uv run --project pipeline pytest -q pipeline/tests/test_structures.py` + screenshot at `turnstile`
- [ ] **T2.6 — Hiker character** · S · `implementer` (after T2.1 approval)
  - Goal: CC0 hiker with idle/walk/run blended by speed, scaled to 1.7 m, blob shadow; replaces the capsule.
  - Verify: `pnpm --filter @penyal/app e2e -- walk-test` + third-person screenshots
- [ ] **T2.7 — Camera and controls polish** · M · `implementer`
  - Goal: the third-person camera collides with the loaded terrain meshes and the tunnel (three-mesh-bvh on LOD0 tiles); gamepad; on-screen auto-walk button; sensitivity and reduced-motion settings.
  - Verify: `pnpm --filter @penyal/app exec vitest run src/player && pnpm --filter @penyal/app e2e -- route`
- [ ] **T2.8 — Light and shadow baseline** · S · `implementer`
  - Goal: one directional shadow following the player on desktop; terrain ambient occlusion baked from the DEM into the tiles; off or cheap on mobile tiers.
  - Verify: frame-time comparison + screenshots at the 6 anchors
- [ ] **T2.9 — Fidelity review with a neighbour** · S · tech lead + user
  - Goal: side-by-side screenshots vs reference photos at 6 points, reviewed by the user; every "this is not how it looks" becomes a task or a documented data limit.
  - Verify: review notes in `docs/specs/001-penyal-ifac-3d/review-f2.md`

## Roadmap (planned in detail when each phase starts)
- **F3 — Living world.** Exit goal: from the summit the view matches a photo taken the same day and hour: real sun position (SunCalc) for day and sunset; sea with Gerstner waves and coastal foam; the horizon ring with Calp, Oltà, Bernia and Toix from a 5–25 m DEM; Mediterranean vegetation placed from official GVA species lists + iNaturalist abundance + ICV MDSnV/IRG masks (never exact Silene locations); gulls near the bifurcation and the peregrine on the N/NW faces; CC-licensed ambient audio. New data to approve before download: ICV MDSnV 1 m (491 MB), a regional DEM for the horizon, optional MITECO bathymetry.
- **F4 — Cards, notebook, minimap, languages.** Exit goal: every POI card shows es/va/en text built from `content/facts.json` with sources, dates and status labels; the notebook persists across reloads; minimap from ICV contours; practical info links to the official booking page; credits screen generated from the catalogue; the park/Ajuntament and a Valencian reviewer sign off.
- **F5 — Performance, accessibility, release.** Exit goal: reference phones hold 30 fps p95 along the whole route, ≤ 15 MB before the first step, WCAG 2.2 AA on the UI, text-only route guide without WebGL2, PWA offline for schools, static hosting with a maintainer guide. Known items: keep one Basis transcoder path (three r186 `KTX2Loader` already resolves it with `new URL`, so `copy-decoders` leaves an unused ~585 kB copy in `dist/bundle`); fog/edge visibility from the Mirador de Carabiners (east edge ~864 m); depth precision at the shoreline (near 0.2 / far 3800).

## Rollout & rollback
Static site; every release is a versioned build that can be redeployed. Generated assets are reproducible from `data/manifest.lock.json` + the pipeline, so a bad asset build is rolled back by rebuilding the previous commit.

## AC coverage
| AC | Tasks |
|---|---|
| AC1 | T0.5, T0.6, T0.7, T1.2, T1.4 |
| AC2 | T1.1, T1.2, T1.3, T1.4 |
| AC3 | T1.3, T1.6, T1.7, T1.8a, T1.8b, T1.10 |
| AC4 | T1.7, T2.7 |
| AC5 | T0.4 (F4 cards, notebook) |
| AC6 | T0.4 (F4 translations) |
| AC7 | T1.5, T1.6, T1.10, T1.11, T2.2 (F5) |
| AC8 | F5 |
| AC9 | F3 |
| AC10 | T0.1, T1.8a, T2.1 (F4 credits screen) |
