---
id: 001
title: Penyal d'Ifac 3D — walkable, sourced 3D experience of the Ruta Roja
status: in-progress
created: 2026-10-11
owner: lr0y
---

# 001 — Penyal d'Ifac 3D

## Problem
Neighbours, school groups and visitors of Calp only meet the Parc Natural del Penyal d'Ifac on the day they climb it, and the climb needs a booking (300 places a day) and reasonable fitness. There is no free, faithful way to explore the official trail beforehand or from a classroom, and the information that circulates online is often wrong (e.g. "first natural park of the Comunitat", conflicting tunnel lengths). We will build a free web experience, gifted to the town, that feels like walking the real rock and where every fact is cited. Geographic fidelity and accuracy of information matter more than the number of features.

## Users & jobs
- **Neighbours of Calp** — rediscover the rock and its history from home, on a phone.
- **Teachers and pupils** — explore the trail, flora, fauna and the Pobla in class; keep a notebook of discoveries.
- **Visitors** — preview the route (tunnel, ropes, viewpoints) and learn the rules before booking.

## Goals
- Walk the official Ruta Roja from the Centre d'Informació to the summit through the tunnel on terrain built from official elevation data and orthophoto.
- Every fact shown carries its source; unverified or conflicting facts are labelled as such.
- Smooth on a mid-range phone and a desktop browser, with nothing to install.

## Scope
- Terrain from official DEM/LiDAR + 2024 orthophoto, limestone cliff detail, Mediterranean vegetation, sea, distant horizon.
- Player walking the trail with terrain collision; first/third-person camera toggle; keyboard, mouse and touch controls.
- Points of interest with short cards: Pobla medieval d'Ifac, the tunnel, Mirador de Carabiners, the summit, Silene d'Ifac, yellow-legged gull, peregrine falcon (more from the official trail stops).
- Notebook of discoveries persisted on the device; minimap; day and sunset lighting with the real sun position.
- UI and content in Spanish, Valencian and English.
- Reproducible asset pipeline: headless Blender (bpy) + Python, exporting optimised glTF with LOD and compressed textures.

## Out of scope
- Free roaming off the trail corridor (decision: walking is limited to the trail and viewpoints, as in the park rules).
- Accounts, backend, analytics, cookies.
- Reconstructions that are not documented (e.g. a rebuilt medieval Pobla); we show what exists today.
- Exact locations of protected plants (conservation).
- Native apps.

## Acceptance criteria
- [ ] AC1 — Given the official data in `data/raw`, when the pipeline runs, then it produces the terrain assets reproducibly (same inputs → same checksums) and every input is listed in `data/manifest.lock.json` with URL, licence and sha256.
- [ ] AC2 — Given the generated terrain, when compared with the source DEM, then sampled heights match within ±0.5 m and the summit, tunnel portals and Centre d'Informació sit within ±2 m of their surveyed/OSM positions.
- [ ] AC3 — Given the app on desktop, when the player walks from the Centre d'Informació, then they can reach the summit through the tunnel and the Mirador de Carabiners without falling through the terrain or leaving the trail corridor.
- [ ] AC4 — Given keyboard+mouse, touch, or gamepad, when the user moves and looks, then the player responds; the camera toggles between first and third person and never shows the inside of the rock in third person.
- [ ] AC5 — Given a point of interest, when the player reaches it, then a card opens with text in the active language, its sources, the date checked and a visible label for unverified or conflicting facts; the discovery is stored in the notebook and survives a reload.
- [ ] AC6 — Given any language (es, va, en), when the content is built, then no string is missing and no fact lacks a source (build fails otherwise).
- [ ] AC7 — Non-functional: on the reference mid-range phone the experience holds 30 fps for ≥ 95 % of frames along the full route, downloads ≤ 15 MB before the first step, and runs in current mobile Safari and Chrome without installation; desktop holds 60 fps.
- [ ] AC8 — Non-functional: UI meets WCAG 2.2 AA (contrast, keyboard, focus, reduced motion); a text-only route guide is offered when WebGL2 is unavailable.
- [ ] AC9 — Day and sunset lighting use the real sun position for Calp (38.635 N, 0.075 E) for the chosen date.
- [ ] AC10 — Credits screen lists every data source and asset with its licence and required attribution.

## Constraints
- Three.js with WebGL (WebGLRenderer), TypeScript, Vite. Blender headless with Python scripts for the asset pipeline.
- No invented geometry: if data is missing, ask for the file. Approximations (e.g. tunnel cross-section) are flagged in credits and code.
- Facts checked against Generalitat Valenciana and Ajuntament de Calp; cite the source; mark what cannot be verified.
- Licences: CC BY 4.0 (IGN/CNIG, ICV), ODbL (OSM, kept as a separate file), CC0/CC BY assets only.

## Risks & open questions
- Q1 — Reference mid-range phone(s) for AC7 — user, before end of F1.
- Q2 — Tunnel cross-section measurements or phone LiDAR scan — user/town; otherwise provisional section flagged as approximate.
- Q3 — Conflicting official facts (tunnel length, route length, minors past the tunnel, Pobla BIC, church date, Silene category) — to be resolved with the park (ifac_cma@gva.es) and MARQ before F4 ships.
- Q4 — CNIG 3rd-coverage LiDAR / MDT50cm availability for this area — check when CNIG is reachable.
- Q5 — Git identity not configured on this machine; commits wait until it is.
- Q6 — Tunnel floor heights: the DEM gives the west portal 182.9 m, but that is the rock wall; LiDAR and the 6 OSM steps point to ≈171 m (170–172.5), east portal 193.0 m (±0.7). That implies ~22 m of climb inside the 49 m tunnel (~24°). To confirm with the park or a site visit before F2 closes; until then the value is curated and flagged as approximate.

## Verification
Each phase is demonstrated in a real browser (built-in browser / Playwright): screenshots from known viewpoints compared with reference photos, console clean, `renderer.info` and frame-time logs, a Playwright E2E "auto-walk reaches the summit", and a measurement on the reference phone. Research and proposal: https://claude.ai/artifact/3Hf99ecPeJhcp4WSftym7K
