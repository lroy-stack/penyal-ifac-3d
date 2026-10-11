# penyal-ifac-3d

## What this is
A free web 3D walk along the Ruta Roja of the Parc Natural del Penyal d'Ifac (Calp), from the Centre d'Informació to the summit through the tunnel, gifted to the town for neighbours, schools and visitors. **Geographic fidelity and factual accuracy beat feature count.** Must run smoothly on a mid-range phone and a desktop browser with nothing to install. Spec: `docs/specs/001-penyal-ifac-3d/`.

## Stack
- App: TypeScript 7 (strict) · Vite 8 · three r186 `WebGLRenderer` (WebGL2) · zod 4 · vitest 5 · Biome 2 (lint + format). Node 24 (`.node-version`, fnm), pnpm 12 workspace.
- Pipeline: Python 3.13 (uv, `pipeline/`) · `bpy` 5.2.2 (Blender as a module, ADR 0003) · rasterio · laspy[lazrs] · pyproj · numpy · ruff · basedpyright · pytest. Asset optimisation with `@gltf-transform` (meshopt + KTX2) and KTX-Software `ktx` in `tools/bin`.
- No backend, no accounts, no cookies, no analytics.

## Commands
| Task | Command |
|---|---|
| Install | `pnpm install --frozen-lockfile && uv sync --project pipeline --locked` (then `tools/install-ktx.sh <pkg>`, see `tools/README.md`) |
| Dev server | `pnpm --filter @penyal/app dev` (port 5173) |
| Lint | `pnpm lint` |
| Typecheck | `pnpm typecheck` |
| Test (all / one file) | `pnpm test` · `pnpm --filter @penyal/app exec vitest run src/content/registry.test.ts` · `uv run --project pipeline pytest -q tests/test_fetch.py` |
| Build | `pnpm --filter @penyal/app build` |
| E2E (headless Chromium) | `pnpm --filter @penyal/app e2e` |
| Load timing under network profiles (by hand, not CI) | `cd app && node scripts/measure-load.mjs --build --profile slow4g --compress br --runs 3` |
| Frame-time overlay (p50/p95/p99, frames > 50 ms) | open the app with `?perf` |
| Pipeline health | `uv run --project pipeline penyal doctor` |
| Rebuild generated data | `uv run --project pipeline penyal dem && … penyal trail && … penyal terrain` (`penyal tunnel` re-cuts only the tiles touching the portals) |
| Generated assets up to date with their inputs | `uv run --project pipeline penyal verify-generated` (exit 1 if a manifest's recorded `inputs` no longer match) |
| Data-dependent tests must run, not skip | `PENYAL_REQUIRE_DATA=1 uv run --project pipeline pytest -q` (default on a clean clone: they skip) |
| Asset spike (bpy → glTF → meshopt, deterministic) | `pnpm spike`; view at `http://localhost:5173/dev/asset-viewer.html?src=<url>` (dev server only) |
| Data (show before downloading) | `uv run --project pipeline penyal fetch --phase 1 --dry-run`, then without `--dry-run` |

## Architecture
- `app/` — static web app. `src/core` (renderer, loop, asset loaders), later `world/`, `player/`, `poi/`, `ui/`. Decoders copied to `app/public/decoders/` by `scripts/copy-decoders.mjs` (gitignored).
- `content/` — fact registry: `sources.json` + `facts.json`, validated by `app/src/content/registry.test.ts` (ADR 0005).
- `pipeline/` — `penyal` CLI: `doctor`, `fetch`, then `dem`, `trail`, `terrain`… Blender code in `src/penyal_pipeline/blender/`.
- `data/catalog.toml` (what to fetch, licence, attribution) → `data/raw/` (gitignored) → `data/manifest.lock.json` (sha256, committed).
- `build/` — intermediate pipeline outputs (gitignored). Generated web assets go to `app/public/assets/`.
- Coordinates: EPSG:25830, local origin (767000, 4280000), `x=E−767000`, `y=H`, `z=−(N−4280000)` (ADR 0004).

## Conventions
- Branch policy: `trunk` · Conventional Commits (enforced by hook).
- Specs live in `docs/specs/NNN-slug/`, decisions in `docs/adr/`, session handoffs in `docs/handoff/`.
- Code, comments, commits and docs in English; user-facing text in es / va / en from the content files.
- Never invent geometry or facts. Missing data → ask for the file. Approximations are flagged in code and `CREDITS.md`.
- Never adjust the terrain to match a published figure (summit is 332 m officially, ~326–328 m in the data). The only allowed terrain edits are evidence-backed local corrections of 2.5D limits (ADR 0009), defined in `data/curated/` and listed in `CREDITS.md`.
- Every fact shown in the UI comes from `content/facts.json` with its sources and status.
- Do not reveal locations of real Silene hifacensis plants.
- Licences: CC0 / CC BY assets only, with two exceptions: the Quaternius hiker under QAL (ADR 0008) and CC BY-SA audio kept as one separate share-alike file per recording (ADR 0011). No Mixamo, no Google 3D Tiles, no CC BY-SA photos as textures; OSM-derived data stays in separate ODbL files (ADR 0007).
- Exact dependency versions (no `^`); verify APIs against installed packages, not memory.

## Gotchas
- `GLTFLoader` (r186) has no `MSFT_lod`, and `THREE.LOD` measures distance to the tile centre (wrong for 256 m tiles): terrain LOD uses our own screen-space-error selection against each tile's AABB (`app/src/world/terrain/selection.ts`).
- `KTX2Loader.detectSupport(renderer)` is called as a separate statement after `setTranscoderPath`.
- `bpy` 5.2.2 needs Python 3.13 exactly.
- ICV MDT/MDS sheets are whole MTN50 files (~825 MB, not COG): download once, clip locally.
- On an IPv6-only uplink (e.g. iPhone hotspot on an IPv6-only carrier) IPv4-only hosts (GitHub, ICV, CNIG) are unreachable: use `PENYAL_NAT64_PREFIX=2a00:1098:2c::5:0:0/96` (public nat64.net relay) with `penyal fetch`. macOS answers AF_INET6 lookups with `::ffff:` IPv4-mapped addresses — they are IPv4, not IPv6.
- `ktx` lives in `tools/` (install with `tools/install-ktx.sh`, see `tools/README.md`); `scripts/optimize.mjs` puts `tools/bin` on PATH.
- The built-in browser pane pauses `requestAnimationFrame` while hidden; for automated visual checks use `pnpm --filter @penyal/app e2e` (Playwright, headless shell + SwiftShader). The Playwright MCP needs a system Chrome and is not used.
- Vite answers `504 Outdated Optimize Dep` after new imports; reload the page.
- Test hooks (`window.__appState`, `?timescale`) exist only in the dev server and in builds made with `VITE_E2E=true` (`app/src/core/testHooks.ts`); a plain `pnpm --filter @penyal/app build` has none. E2E runs on the dev server (`app/playwright.config.ts`); `measure-load.mjs --build` builds with the flag.
- GVA park pages were read from Internet Archive copies; re-check live before release.

## Definition of Done
- Acceptance criteria of the active spec/task met and demonstrated (test, screenshot or command output).
- Studio gates green (lint · typecheck · test), no placeholders, no skipped tests.
- Phase work verified in a real browser before moving on.
- Docs touched when behaviour or setup changed (README, ADR, CLAUDE.md, CREDITS.md).
