# Phase 2 asset shortlist — T2.1 (research only)

Task: [plan.md T2.1](plan.md) · Spec: [spec.md](spec.md) · Licence rule: [ADR 0007](../../adr/0007-licensing.md) · Date: 2026-10-11
Status: **proposal, nothing downloaded.** Wait for user approval of the list at the end before running `penyal fetch --phase 2`.

## Summary

- **Limestone (cliffs + near detail):** Poly Haven `marble_cliff_05` (CC0, 20 m tile, pale beige-grey). Alternatives `rock_boulder_dry` and `marble_rock_01`; fallback `rocks_ground_04`. `rock_face` and `cliff_side` are confirmed too orange and dark.
- **Trail:** Poly Haven `rocks_ground_05` (CC0, neutral grey-beige gravel). Alternative `rocky_trail` (warmer brown-grey).
- **Hiker:** no verified CC0 package yet covers mesh + idle + walk + run. Best candidate pair: Quaternius Universal Base Characters (mesh, CC0 per listing) + Universal Animation Library Standard (animations, CC0 per listing). Clip names and the free-tier mesh are **not verified** (sources blocked).
- **Rope and handrail:** no external asset needed. Poly Haven has no rope texture; build tube geometry and metal material procedurally.
- **Budget:** estimated KTX2 for the 1k set (limestone + trail + hiker) ≈ 5 MB. The 2k set for both textures ≈ 13–14 MB, which by itself nearly reaches the 15 MB pre-first-step limit (AC7). Load the 2k set after the first step or only on desktop.

## Network and verification status (checked 2026-10-11)

| Host | Status | Impact |
|---|---|---|
| `api.polyhaven.com`, `dl.polyhaven.org`, `cdn.polyhaven.com` | Reachable (HTTP 200, HEAD checked) | Poly Haven fully verified via API and files JSON |
| `terramapas.icv.gva.es` (ICV WMS/WFS) | Unreachable (000) | **Ifac orthophoto colour could not be sampled** |
| `ambientcg.com` | Unreachable (000) | ambientCG candidates (Rock030 from notes) **not verified** |
| `quaternius.com`, `quaternius.itch.io`, `kenney.nl`, `kenney-assets.itch.io` | Unreachable or 403 (itch.io blocks bots) | Quaternius/Kenney facts come from store and search snippets only |
| `opengameart.org`, `github.com`, `raw.githubusercontent.com`, `cdn.jsdelivr.net`, `sketchfab.com` | Unreachable (000 or ECONNREFUSED) | No mirror checks |
| `poly.pizza` | Reachable over IPv6 | No Quaternius listing checked; one generic model showed CC BY 3.0 (not used) |
| `store.godotengine.org` (WebFetch) | Reachable | Universal Animation Library Standard: licence and size |

## 1. Limestone and rock (cliffs and near-ground)

### Colour evidence

Method: mean colour of the 256 px Poly Haven preview (lit render, not albedo). The values are **relative only**. Lum is relative luminance of the mean. R−B is the warmth proxy (higher = more orange). Target from the brief: light, slightly warm grey limestone. **The Ifac reference colour was not measured** (ICV unreachable). A measured target is still needed before final sign-off.

| Asset | Lum (rel.) | R−B (warmth) | Read |
|---|---|---|---|
| `rock_boulder_dry` | 0.234 | 12.6 | Lightest and neutral. "pale sandy-gray", object scan at 1.8 m |
| `marble_cliff_05` | 0.131 | 11.3 | Light beige-grey, neutral-warm. Chosen |
| `marble_rock_01` | 0.143 | 18.5 | Light grey-beige, a little warmer |
| `rocks_ground_04` | 0.121 | 13.4 | Neutral ground with smooth faces and gravel |
| `marble_cliff_01` | 0.127 | 30.8 | Creamy-tan, warm |
| `rock_face` (rejected) | 0.040 | 24.6 | Dark, brown-orange. Confirmed too orange |
| `cliff_side` (rejected) | 0.046 | 34.9 | Dark, orange. Confirmed too orange |
| `rock_pitted_mossy`, `worn_rock_natural_01` (rejected) | 0.233 / 0.140 | 37.2 / 38.3 | Orange-red and yellow sandstone, not limestone |
| `seaside_rock` (rejected) | 0.035 | 7.1 | Dark grey-brown, wet look |

### Ranked options

1. **`marble_cliff_05`** (primary, cliffs). Poly Haven, CC0. Pale beige and grey, veining, heavy weathering. 20 m physical tile, so it tiles little on long faces. Maps: Diffuse, nor_gl, Rough, AO, Displacement, ARM (AO/Rough/Metal packed).
2. **`rock_boulder_dry`** (alternative, lightest). CC0. Pale sandy-grey, cracked and pitted, 1.8 m tile, 16K source. Good colour match but tiles fast on cliffs. Use a 1/8–1/10 UV scale on cliffs or limit it to near-ground detail.
3. **`marble_rock_01`** (alternative, near-ground detail). CC0. Light grey-beige, dark striations and pits, 2 m tile. Warmer than 1 and 2.
- **Fallback:** `rocks_ground_04`. CC0. Neutral ground with smooth stone faces and gravel. Small, but it is a ground texture, so it is weak on steep faces.

Naming risk: the "marble" Poly Haven series is metamorphic. Ifac is Eocene nummulitic limestone (sedimentary). The veining and "marble" label are a look-alike, not a geological match. Check at the 6 anchors (T2.9) before accepting.

### Asset details

| Id | Page / API | Licence | Maps (1k, 2k) | Phys. size | Source JPG 1k / 2k (bytes) |
|---|---|---|---|---|---|
| `marble_cliff_05` | https://polyhaven.com/a/marble_cliff_05 · https://api.polyhaven.com/files/marble_cliff_05 | CC0 | Diffuse, nor_gl, Rough, AO, Displacement, ARM; 1k/2k/4k/8k | 20 m | 2,637,926 (diff+nor+arm) / 9,395,229 |
| `rock_boulder_dry` | https://polyhaven.com/a/rock_boulder_dry | CC0 | same; 16K source | 1.8 m | 2,446,436 / 9,909,760 |
| `marble_rock_01` | https://polyhaven.com/a/marble_rock_01 | CC0 | same; 8K source | 2 m | 2,577,649 / 9,725,441 |
| `rocks_ground_04` | https://polyhaven.com/a/rocks_ground_04 | CC0 | same; 8K source | 2 m | 1,920,106 / 7,336,842 |

Attribution: CC0, no attribution required. Credit line for CREDITS.md (courtesy): "Textures: Amal Kumar, Poly Haven (polyhaven.com), CC0".

File URLs for `marble_cliff_05` (pattern verified from `files` JSON; the 1k paths follow the same pattern):
- `https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/marble_cliff_05/marble_cliff_05_diff_1k.jpg` (987,798 B)
- `…/marble_cliff_05_nor_gl_1k.jpg` (997,297 B) · `…/marble_cliff_05_arm_1k.jpg` (652,831 B) · optional `…/marble_cliff_05_disp_1k.jpg` (208,997 B; not needed at runtime)
- 2k: same pattern under `jpg/2k/` (diff 3,540,217 · nor 3,524,582 · arm 2,330,430 B)

Risks: veining may read as "marble" on the cliffs. Mitigate with a colour-multiply tint from the orthophoto macro map. Uneven weathering may need a stronger triplanar blend near the trail.

## 2. Trail surface

| Rank | Id | Page | Licence | Maps | Phys. size | 1k / 2k JPG bytes | Read |
|---|---|---|---|---|---|---|---|
| Primary | `rocks_ground_05` | https://polyhaven.com/a/rocks_ground_05 | CC0 (author Rob Tuytel) | Diffuse, nor_gl, Rough, AO, Displacement, ARM | 3 m | 2,379,123 / 9,040,321 | Dry uneven soil, coarse gravel, scattered pebbles. Neutral grey-beige, closest to pale limestone rubble |
| Alternative | `rocky_trail` | https://polyhaven.com/a/rocky_trail | CC0 (author Amal Kumar) | same | 2 m | 3,560,455 / 13,721,565 | "Compacted earth, mixed gravel, chipped stones" in warm brown-grey. Warmer and heavier |

Rejected: `stony_dirt_path` (very dark, leaf litter); `rocky_trail_02` (16K, dusty, heavy); `gravel_ground_01` (warm brown).

Download files for the primary: `rocks_ground_05_diff_1k.jpg` (756,710 B), `_nor_gl_1k.jpg` (1,387,386 B), `_arm_1k.jpg` (235,027 B). Same names under `jpg/2k/` for desktop. Attribution: CC0, no attribution required.

Risks: the trail mask (T2.3) must blend in a warmer edge so the tread stands out from the cliff. Verify the path-to-cliff colour contrast in the T2.9 screenshots.

## 3. Hiker character

No package below was checked against its own file list. Facts come from store pages, poly.pizza, and search snippets.

| Candidate | Licence (as listed) | Free tier contents | Format | Size | Verified? |
|---|---|---|---|---|---|
| **Quaternius Universal Animation Library**, "Standard-1.0" (https://store.godotengine.org/asset/quaternius/universal-animation-library/ · https://quaternius.itch.io/universal-animation-library) | CC0 1.0 (store page, updated 10 June 2026) | "a portion of the models" and a subset of "120+ animations" (about 45 per search snippet). Categories: 8-direction locomotion, jog, sprint, push, crawling, swimming, sitting, death, combat, emotes | Not stated on store page (Quaternius lists OBJ, FBX, glTF; to confirm) | **14.54 MB** zip | Licence and size: yes. Clip names: **no**. Idle/walk/run: **not confirmed** |
| **Quaternius Universal Base Characters**, Standard (https://quaternius.itch.io/universal-base-characters) | CC0 (per itch listing via search snippet; itch blocked) | 6 rigged humanoids (Superhero, Regular, Teen; male and female), humanoid rig, about 13k tris average | Not confirmed | **122 MB** zip (Standard); 599 MB Source is paid | Partly (from snippet) |
| Kenney Animated Characters 1–3 (https://kenney-assets.itch.io/animated-characters-3) | CC0 1.0 (search snippet) | 4 skins, **3 animations: Idle, Jump, Running** (no walk) | GLB not stated; may be glTF/FBX | Not stated | Snippet only. Not sufficient on its own |
| Quaternius Ultimate Animated Character Pack | Quaternius Asset Licence QAL v1.0 claimed by third-party guides, **conflicts with CC0** | 50+ characters, FBX/OBJ/Blend per guide | Per guide | Unknown | No. Do not use until licence is read in the download |

Recommended path (to confirm after approval, not before):
1. Download the UAL Standard zip and the UBC Standard zip into `pipeline/` scratch (not `app/`), read each `LICENSE` file, and list the animation names and bone names in Blender (`bpy`).
2. Require idle, walk and run clips with a shared humanoid rig. If the walk and run clips are missing, use the Kenney idle/run pair plus a retargeted walk, or drop the candidate.
3. Pick a "Regular" male or female mesh. Recolour via material colour (jacket, trousers, boots) only if the mesh has separate material slots. Otherwise use a flat neutral tint.
4. Stair climbing: no verified "climb stairs" clip. Use the walk clip with a small vertical bob or foot IK on steps. Do not claim a climb animation until the clip list confirms it.

Estimated optimised GLB (not measured): mesh with meshopt ≈ 1–2 MB; 1k colour texture (ETC1S) ≈ 0.3 MB; animations ≈ 0.3–0.5 MB. Total ≈ 2 MB at mobile, ≈ 2.5 MB at desktop.

Risks: the free tier may lack the walk or run clips; Quaternius licence wording may have changed (see Conflicts); rig names may differ between UBC and UAL (retarget needed); 122 MB zip is large for a one-off conversion but is pipeline-only, not shipped.

## 4. Rope and handrail

| Need | Asset? | Decision |
|---|---|---|
| Rope | No CC0 rope texture found on Poly Haven (tags searched: rope, cord, twine, hemp; none) | **Procedural**: a helical stripe `CanvasTexture` or a tube (`TubeGeometry`) with a twist normal map generated in code. No download |
| Handrail | Poly Haven has metal textures (`metal_plate_02`, `rusty_metal_*`) but they are not needed | **Procedural**: `MeshStandardMaterial` with metalness 1 and roughness from a simple value. Optional `metal_plate_02` if the look is poor after T2.4 review |

Verify: the rope and handrail look is checked in the T2.4 screenshots; no download needed for either.

## 5. Budget

Method (estimates, not measured): colour (Diffuse) ETC1S ≈ 0.2 B/px; normal UASTC ≈ 0.8 B/px after zstd; ARM ETC1S ≈ 0.2 B/px; mips ×4/3. Result ≈ 0.28 MB (colour) + 1.1 MB (normal) + 0.28 MB (ARM) ≈ **1.7 MB per 1k set**; ≈ 6.7 MB per 2k set. Check with `ktx` (T0.8) and `@gltf-transform` once `tools/bin/ktx` exists.

Note: UASTC normals at 1k are larger than the JPG source (0.99 MB). If the budget is tight, try ETC1S for the normal map after a visual check.

| Set | Mobile (1k) est. | Desktop (2k) est. | Notes |
|---|---|---|---|
| Limestone `marble_cliff_05` | 1.7 MB | 6.7 MB | Source JPG 2.64 / 9.40 MB |
| Trail `rocks_ground_05` | 1.7 MB | 6.7 MB | Source JPG 2.38 / 9.04 MB |
| Hiker (mesh + anims + tex) | ~2 MB | ~2.5 MB | Estimate, see §3 |
| Rope, handrail | 0 | 0 | Procedural |
| **Total (textures + hiker)** | **≈ 5.4 MB** | **≈ 15.9 MB** | |

AC7 applies: downloads ≤ 15 MB before the first step. The 1k total leaves roughly 9–10 MB for terrain tiles and the rest before the first step (terrain budget not set here). The 2k total does not fit on its own, so load the 2k set after the first step or only when the device is desktop.

## Conflicts and unverified

- **Quaternius licence:** the Godot store page (UAL Standard) and the itch listing snippet say CC0. Third-party guides (cinevva.com, 2026) claim a newer "Quaternius Asset Licence (QAL v1.0)" for newer content, which also allows commercial use without attribution but adds terms (no resale as a standalone pack). Unverified. Read the `LICENSE` file in each download before approval. If QAL, route it through ADR 0007 review first.
- **Kenney clip counts:** search snippets say "Animated Characters" have 3 clips (idle, jump, run). A cinevva guide lists 25–32 clips for other Kenney packs (Character Human, Mini Characters). Different packs; not verified.
- **Universal Animation Library free content:** store page says "a portion of the models" and a subset of the 120 animations. Third-party text says 45 animations. Not confirmed from the download.
- **Ifac colour:** no RGB reference from the orthophoto (ICV unreachable). The ranking is relative to the brief, not to measured Ifac pixels.
- **ambientCG Rock030 (from notes.md):** not verified (ambientcg.com unreachable). Not in this list.
- **Poly Haven dimensions:** API `dimensions` are in mm (verified: `marble_rock_01` page states "2m"). `rock_ground` shows scale "2Mx2M" but dimensions 1500 mm; the page value was not checked.

## Proposed download list for user approval

Nothing below is downloaded yet. Pipeline-only items (hiker zips) stay out of `app/`. Only the optimised outputs ship.

| # | File(s) | Source host | Size (source) | Licence | Use | Priority |
|---|---|---|---|---|---|---|
| 1 | `marble_cliff_05_{diff,nor_gl,arm}_1k.jpg` | dl.polyhaven.org | 2.64 MB | CC0 | Limestone, mobile | Must |
| 2 | `marble_cliff_05_{diff,nor_gl,arm}_2k.jpg` | dl.polyhaven.org | 9.40 MB | CC0 | Limestone, desktop (lazy) | Must |
| 3 | `rocks_ground_05_{diff,nor_gl,arm}_1k.jpg` | dl.polyhaven.org | 2.38 MB | CC0 | Trail, mobile | Must |
| 4 | `rocks_ground_05_{diff,nor_gl,arm}_2k.jpg` | dl.polyhaven.org | 9.04 MB | CC0 | Trail, desktop (lazy) | Should |
| 5 | Universal Animation Library Standard zip | quaternius.itch.io or Quaternius site | 14.54 MB | CC0 (listed; verify `LICENSE`) | Hiker animations (pipeline only) | Must |
| 6 | Universal Base Characters Standard zip | quaternius.itch.io | 122 MB | CC0 (listed; verify `LICENSE`) | Hiker mesh (pipeline only) | Must |
| 7 | Alternatives (only if 1 fails visual check): `rock_boulder_dry`, `marble_rock_01` (1k) | dl.polyhaven.org | 2.45 / 2.58 MB | CC0 | Limestone alt | Optional |
| 8 | Fallback `rocks_ground_04` (1k) | dl.polyhaven.org | 1.92 MB | CC0 | Limestone fallback | Optional |
| 9 | Alternative trail `rocky_trail` (1k) | dl.polyhaven.org | 3.56 MB | CC0 | Trail alt | Optional |

Attribution to add to `CREDITS.md` (CC0 courtesy line; no attribution required): "Textures: Poly Haven (polyhaven.com), CC0, authors Amal Kumar and Rob Tuytel." Quaternius: add the exact attribution string after the licence check. None is required under CC0.

Not needed: rope, handrail, metal textures (procedural).

## Sources

- Poly Haven API, textures list and per-asset JSON (checked 2026-10-11): https://api.polyhaven.com/assets?t=textures · https://api.polyhaven.com/info/marble_cliff_05 · https://api.polyhaven.com/files/marble_cliff_05 (same pattern for other ids)
- Poly Haven licence: https://polyhaven.com/license (CC0, no attribution required)
- Poly Haven asset page, marble_rock_01 (2 m, CC0): https://polyhaven.com/a/marble_rock_01
- Poly Haven 256 px previews (colour check, relative only): https://cdn.polyhaven.com/asset_img/thumbs/<id>.png?width=256&height=256&format=webp
- Quaternius Universal Animation Library Standard (Godot store, CC0, 14.54 MB, updated 10 June 2026): https://store.godotengine.org/asset/quaternius/universal-animation-library/
- Quaternius Universal Animation Library itch page (blocked; content from search snippet): https://quaternius.itch.io/universal-animation-library
- Quaternius Universal Base Characters itch page (blocked; content from search snippet): https://quaternius.itch.io/universal-base-characters
- Kenney Animated Characters 3 (search snippet only): https://kenney-assets.itch.io/animated-characters-3
- Third-party guide (CC0 wording for a Quaternius pack, Kenney clip counts, QAL licence change claim; all unverified against originals): https://app.cinevva.com/game-assets/free-3d-character-models

## Decisions (2026-10-11)
- Approved and downloaded: the 12 Poly Haven files above (`marble_cliff_05` and `rocks_ground_05`, diff / nor_gl / arm, 1k and 2k, 23.45 MB), catalogue phase 2, sha256 locked and md5 checked against api.polyhaven.com.
- Hiker: the product owner accepted the Quaternius Asset License (QAL v1.0, quaternius.com/license.html, updated 2026-08-28) for the hiker only — ADR 0008. The pack page still says "License CC0"; the licence file inside the downloaded zip decides. The zip is downloaded by the user from itch.io into `data/manual/quaternius/` (gitignored) and never committed or redistributed as an asset.
