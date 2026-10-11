# 0002. Render with three.js WebGLRenderer, build with Vite and TypeScript, no UI framework

- Status: accepted
- Date: 2026-10-11
- Deciders: lr0y (product owner), tech lead

## Context
The experience must run smoothly on mid-range phones and desktop browsers without installing anything. The brief fixes Three.js with WebGL, TypeScript and Vite. As of 2026-10-10, three r186 is current; its migration guide does not deprecate `WebGLRenderer`, while most new work targets `WebGPURenderer`. `GLTFLoader` supports `EXT_meshopt_compression`, `KHR_texture_basisu`, `KHR_mesh_quantization` and `EXT_mesh_gpu_instancing`, but not `MSFT_lod`. The UI (cards, notebook, minimap, settings) is mostly text and must be accessible and translated.

## Options considered
1. **three r186 `WebGLRenderer` (WebGL2) + Vite 8 + TypeScript, DOM UI without a framework** — stable on mobile GPUs, small bundle, real text for screen readers. Cost to reverse: low for the UI, medium for the renderer.
2. **`WebGPURenderer` with WebGL fallback** — future-proof, but uneven support and performance on mid-range phones today; the fallback path doubles testing.
3. **React/Preact UI on top** — familiar component model, but adds bundle and a second render loop for an interface that is a handful of panels.

## Decision
Option 1. WebGL2 is the most reliable target on the phones the town will actually use, and a framework-free DOM UI keeps the bundle small and the text accessible. Terrain LOD is selected per tile by our own screen-space-error test against each tile's bounding box, because `GLTFLoader` does not support `MSFT_lod` and `THREE.LOD` measures distance to the tile centre, which is wrong for 256 m tiles.

## Consequences
- Imports come from `three` and `three/addons/...`; the basis transcoder is served from `/decoders/basis/`.
- Post-processing libraries are avoided on mobile (e.g. `postprocessing` 6.39 pins `three <0.187`).
- If the UI grows beyond simple panels, revisit with a new ADR (Preact would be the candidate).
- WebGPU can be evaluated later behind a quality tier without changing the asset pipeline.
