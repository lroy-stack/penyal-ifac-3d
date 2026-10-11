# 0011. Allow CC BY-SA audio, kept as separate share-alike files

- Status: accepted (amends 0007 for audio)
- Date: 2026-10-11
- Deciders: lr0y (product owner), tech lead

## Context
Phase B adds an ambient soundscape to the pilot stretch (plan 002, B4; lane L2). The licence research (`docs/specs/002/sonido-licencias.md`, 2026-10-11) found clean CC0, CC BY or public-domain recordings for three layers: sea on rock, cicadas and a footstep. It found none for the other three: the yellow-legged gull (*Larus michahellis*), wind in pines and a passerine listed by the park (black wheatear or Dartford warbler). The only candidates for those three, all on Wikimedia Commons, are CC BY-SA 4.0.

The rules disagreed:
- ADR 0007 excludes only CC BY-SA *photos used as textures*.
- `CLAUDE.md` summarised the policy as "CC0 / CC BY assets only".
- The phase B plan allowed BY-SA audio "as is", but the app will trim, loop-crossfade and re-encode each file (Opus). That is an adaptation, so the result must itself be licensed CC BY-SA.

## Options considered
1. **Allow BY-SA audio as separate files.** Each adapted file stays a distinct work under CC BY-SA 4.0, credited, next to the app, like the OSM extract under ODbL. The app is a collection that plays the file, not an adaptation of it, so EUPL code and other assets are unaffected. Cost to reverse: low (swap the file).
2. **CC0 and CC BY only.** The missing layers wait for our own CC0 recording. That needs the park's permission and, for the gull colony, spring, when recording near nests disturbs breeding.
3. **Both.** BY-SA now, replaced by our own recording when one exists.

## Decision
Option 1, chosen by the product owner on 2026-10-11, with these rules:
- **Scope.** It applies to audio only. CC BY-SA photos as textures stay excluded (ADR 0007).
- **Catalogue.** Every BY-SA audio input has `share_alike = true` in `data/catalog.toml` and its exact licence and attribution.
- **One file per recording.** Each derived audio file is its own file, licensed CC BY-SA 4.0. It is never mixed into one file with other recordings. A mix that includes a BY-SA recording is an adaptation of it, so the whole mix would have to be licensed BY-SA.
- **Credits.** `CREDITS.md` and the in-app credits screen list, for each such file:
  - the author and the original title;
  - the licence and its link;
  - that it was modified (trimmed and re-encoded).
- **Original.** The original remains reachable through its Commons page, which the credits link.
- **No exceptions.** NC, ND and unknown licences remain excluded.

## Consequences
- `CLAUDE.md` states the licence rule with this exception.
- The audio system (lane L2) loads each layer from its own file. Layering happens at runtime with Web Audio, never by baking several recordings into one file.
- A recording of our own released under CC0 can replace any BY-SA layer later without changing code.
