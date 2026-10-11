# 0007. License the code under EUPL-1.2 and preserve every data licence

- Status: accepted; amended by 0008 for the hiker character only, and by 0011 for CC BY-SA audio
- Date: 2026-10-11
- Deciders: lr0y (product owner)

## Context
The project is a gift to the town of Calp; other administrations may want to reuse it. Inputs come with their own licences: CC BY 4.0 (IGN/CNIG, ICV), ODbL 1.0 (OpenStreetMap, share-alike for derived databases), CC0 and CC BY assets. Some reference photos are CC BY-SA.

## Options considered
1. **EUPL-1.2 for code** — the EU public licence, designed for public-sector reuse, compatible with GPL family licences.
2. **MIT for code** — simplest and most permissive, but no copyleft protection for the public investment.

## Decision
EUPL-1.2 for code. Data and assets keep their licences: attributions go in `CREDITS.md` and the in-app credits screen; the OSM extract and anything derived from it as a database are kept in separate files under ODbL; no CC BY-SA photo is used as a texture; no Mixamo or Google 3D Tiles content is used.

## Consequences
- `LICENSE` holds the EUPL-1.2 text; `CREDITS.md` is updated whenever a source or asset is added.
- `data/catalog.toml` records licence and attribution per source; the credits screen is generated from it.
