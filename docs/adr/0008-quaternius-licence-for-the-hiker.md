# 0008. Allow the Quaternius Asset License for the hiker character only

- Status: accepted (amends 0007 for one asset)
- Date: 2026-10-11
- Deciders: lr0y (product owner), tech lead

## Context
ADR 0007 limits assets to CC0 and CC BY. F2 needs an animated hiker (idle, walk, run). The best candidate, Quaternius' Universal Animation Library (and, if needed, Universal Base Characters), is listed as "License CC0" on its pack page, but on 2026-10-11 quaternius.com/license.html shows the Quaternius Asset License (QAL) v1.0, last updated 2026-08-28. QAL allows free use in personal, educational and commercial products with no attribution, and forbids redistributing the assets "as a standalone asset, asset pack, stock file, template, or similar product", however modified. The version in effect when the assets are obtained governs. The pack is obtained through an itch.io pay-what-you-want page, so a person downloads it. No CC0 character with idle, walk and run was confirmed (Kenney's set lacks walk; RobotExpressive is a robot).

## Options considered
1. **Accept QAL for the hiker only** — best quality now; the app is a product that incorporates the asset, which QAL allows; the repository must never contain the asset files. Cost to reverse: low (swap the character).
2. **Model and animate our own hiker in Blender** — fully EUPL, more work, less polish.
3. **Keep the capsule** — no licence question, weaker experience.

## Decision
Option 1, chosen by the product owner on 2026-10-11, with these rules:
- The zip lives in `data/manual/quaternius/` (gitignored); its sha256 and the exact licence file found inside it are recorded in `data/manifest.lock.json`. If the zip's own licence is CC0, CC0 governs and this ADR's restrictions become unnecessary but harmless.
- Only the pipeline output (the hiker GLB, retargeted, trimmed to the clips we use, optimised) is served by the app, as part of the product. It is never published as a separate download, in the repository, or in an asset list.
- `CREDITS.md` and the credits screen name Quaternius and the licence as a courtesy.
- Every other asset still follows ADR 0007.

## Consequences
- Maintainers rebuilding the app must obtain the pack themselves (documented in `data/README.md`).
- If Quaternius' terms change, the version in effect at download time applies; keep the licence file with the manifest record.
- Revisit if a CC0 hiker with idle, walk and run becomes available.
