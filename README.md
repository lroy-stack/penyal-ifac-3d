# penyal-ifac-3d — a free web 3D walk of the Ruta Roja, Penyal d'Ifac

No public demo yet; a private preview runs on Cloudflare Pages for testers (ADR 0012).

## What it is

A web 3D walk along the Ruta Roja of the Parc Natural del Penyal d'Ifac in Calp, Spain, from the visitor centre to
the summit through the tunnel. Started in October 2026 as a gift to the town, for neighbours, schools and
visitors. It runs in a browser with nothing to install, on a mid-range phone or a desktop, with no backend, no
accounts, no cookies and no analytics. Geographic fidelity and factual accuracy come before feature count.

## How it is made

- A Python pipeline (`penyal` CLI) fetches open data and generates the terrain and assets: ICV and PNOA elevation
  models and LiDAR (CC BY 4.0), the 2024 orthophoto, and OpenStreetMap trail, steps and buildings (ODbL, kept in
  separate files). Blender runs as a Python module (`bpy`) to build meshes; glTF is optimised with meshopt and KTX2.
- A static TypeScript web app renders the result with three.js, with its own screen-space-error terrain LOD.
- Every fact shown in the UI comes from `content/facts.json` with its sources and status. Missing geometry is
  never invented; approximations are listed in `CREDITS.md`.
- Texts are in Spanish, Valencian and English.

## Built with

TypeScript, Vite, three.js, zod, Vitest, Biome and Playwright for the app; Python 3.13 with uv, bpy, rasterio,
laspy, pyproj, numpy, ruff and pytest for the pipeline; pnpm workspace; Cloudflare Pages for the preview.

## Run it locally

Requires Node 24 (`.node-version`), pnpm, uv, and the KTX-Software `ktx` tool installed with
`tools/install-ktx.sh` (see `tools/README.md`).

```bash
pnpm install --frozen-lockfile && uv sync --project pipeline --locked
uv run --project pipeline penyal doctor                 # pipeline health check
uv run --project pipeline penyal fetch --phase 1 --dry-run   # show what would be downloaded, then run without --dry-run
pnpm --filter @penyal/app dev                           # app on http://localhost:5173
pnpm lint && pnpm typecheck && pnpm test
pnpm --filter @penyal/app e2e                           # Playwright, headless Chromium
```

Generated terrain and assets are not committed; rebuild them with the `penyal dem`, `trail`, `terrain` and related
commands listed in `CLAUDE.md`. `pnpm deploy:preview` runs a dry run of the preview deployment, and
`pnpm deploy:preview --yes` deploys it.

## Layout

```
app/        static web app (renderer, world, player, UI)
pipeline/   penyal CLI: data fetch, terrain, trail, vegetation, Blender scripts
content/    fact registry: sources and facts
data/       data catalog, curated corrections, checksums
docs/       ADRs, specs, research, audits
fixtures/   small geo and vegetation test fixtures
```

Code under the EUPL-1.2. Data and asset credits and licences are in `CREDITS.md`.

---

Versión en español: paseo web en 3D por la Ruta Roja del Parc Natural del Penyal d'Ifac (Calp), pensado como regalo
para el pueblo. Funciona en el navegador sin instalar nada, con datos abiertos (ICV, PNOA, OpenStreetMap) y sin
cookies ni analítica. Licencia EUPL-1.2.
