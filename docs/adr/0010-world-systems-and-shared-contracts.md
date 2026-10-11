# 0010. Compose the world from registered systems that share atmosphere, quality, budget and POI contracts

- Status: accepted; amendment 1 (2026-10-11) adds a GPU texture-memory budget
- Date: 2026-10-11
- Deciders: tech lead (architect); accepted by lr0y (product owner) on 2026-10-11
- Scope: B0 of `docs/specs/002-fase-b-paralelizacion.md`; implemented after phase A closes.

## Context
- **The bottleneck.** Phase B runs up to eight lanes in parallel worktrees. `app/src/main.ts` (~410 lines with the uncommitted A3/A4/A6 work) owns the loading order, the scene, the frame loop and the UI wiring, so every lane would edit it.
- **Shared state.** The sun (terrain, sea, vegetation, shadows), the quality tier (everyone), the walkable surfaces (the tunnel today, the steps from L5) and the POIs (UI, audio).
- **Loading order today.** `trail.json`, the terrain manifest and `tunnel.json` load in parallel. The terrain critical path follows (far mesh plus coarsest LOD near the camera, `detailEnabled: false`), drawn as a preview. Then come the collision field, the player and `setDetailEnabled(true)`. The tunnel mesh starts as soon as `tunnel.json` arrives.
- **Frame order today.** Player sub-steps → tunnel lamp → sky dome recentred → terrain `update` → one `renderer.render`. `PlayerController` and `CameraRig` keep the `groundSurfaces` and `enclosures` arrays by reference (`controller.ts:81`, `cameras.ts:221`).
- **Quality today covers only the terrain.** `selectQualityTier` returns `high` or `low`, and `?terrain=` overrides it. `high` means 1k maps on touch devices and 2k on desktop. `sseThreshold` is 4/2 px and `maxPixelRatio` 1.5/2 (touch/desktop). The detail is an `onBeforeCompile` patch with shared uniforms and the key `"penyal-terrain-detail-v4"` (`terrain/material.ts:314-324`).
- **Checked in the installed three 0.186.1 source.** `UniformsGroup` is documented for `ShaderMaterial` only (`src/core/UniformsGroup.js:9-11`), yet `WebGLRenderer` binds `material.uniformsGroups` on any material once per frame (`WebGLRenderer.js:2816-2826`). `customProgramCacheKey()` defaults to `onBeforeCompile.toString()` (`Material.js:544-546`). `_currentMaterialId` resets after each `render()` (`WebGLRenderer.js:1821`), so a changed shared uniform reaches every program on the next frame. `toneMapping` and `shadowMapEnabled` are program parameters, so changing them recompiles (`WebGLPrograms.js:363-366`). `ShaderMaterial.clone()` deep-copies the uniforms (`ShaderMaterial.js:285`).
- **Pilot baseline.** 18 draw calls and 296k triangles at `turnstile` (`docs/audits/002-capturas/metrics.json`, SwiftShader, `low`).
- **Viewpoint test gap.** `app/e2e/viewpoints.spec.ts` saves screenshots but compares nothing, and under SwiftShader it always runs at `low`, so the terrain patch is never exercised.

## Options considered
| Decision | Chosen | Rejected (why) |
|---|---|---|
| Composition | `WorldSystem` interface, one explicit list, three update phases | ECS library (new dependency and pattern for ~10 coarse systems); numeric priorities or a dependency graph (implicit order, lanes collide); keep editing `main.ts` (constant conflicts) |
| Shared uniforms | One `IUniform` object referenced from `onBeforeCompile` and `ShaderMaterial.uniforms`, as the terrain does | UBO (documented for `ShaderMaterial` only, but tiles are glTF `MeshStandardMaterial`; std140 by hand; no measurable gain for ~5 values; can be adopted later behind `attachAtmosphere`); per-material copies (O(materials) writes, drift) |
| Atmosphere change signal | Polled `version` number | Listeners (subscription lifecycle, re-entrancy, hidden ordering) |
| Quality | One profile with per-system knobs, derived from the tier | Each system probes the device, as the terrain does today (inconsistent tiers, no coordinated downgrade) |
| Budget | Static table plus an E2E that toggles systems | Runtime guard that disables systems (non-deterministic visuals, hides regressions) |
| POI content | JSON per POI; fact ids per sentence; numbers checked against the registry | Markdown with inline refs (needs a parser, weak validation); prose generated from facts (untranslatable) |
| Worktrees | `.worktrees/<lane>` inside the repo; inputs symlinked, outputs APFS-cloned | Sibling folders (break "one project = one folder"); symlink everything (lanes overwrite each other's generated assets) |

## Decision
The chosen column throughout. **Deciding factor: lanes add files and never edit shared ones.** The only exceptions are one line in the system list and the one edit allowed in §2.

### 1. World systems (`app/src/world/systems.ts`; list in `app/src/world/index.ts`)
```ts
export type UpdatePhase = "prePlayer" | "postPlayer" | "preRender";
/** critical: awaited before the first frame (small JSON only; the only place lights may be added).
 *  beforeWalk: awaited before the player exists (ground surfaces). background: started after the walk starts. */
export type LoadPriority = "critical" | "beforeWalk" | "background";
export type InitOutcome = { readonly status: "ready" } | { readonly status: "missing"; readonly message: string };
export type SystemStatus =
  | { readonly state: "pending" | "loading" | "ready" | "disabled" }
  | { readonly state: "missing" | "degraded" | "failed"; readonly message: string };
export type FrameInfo = {
  readonly frame: number; readonly dt: number;  // dt: simulated s this frame (clamped delta x timescale)
  readonly time: number;                        // simulated s since boot; frozen by the test hook
  readonly drawingBufferHeight: number; readonly player: PlayerState | null; // player null while previewing
};
export type Route = { readonly trail: Trail; readonly corridor: Corridor; readonly start: Anchor; readonly startYaw: number };
export interface SystemContext {
  readonly scene: Scene; readonly root: Group;  // add objects only under root (`system:<id>`, already in the scene)
  readonly camera: PerspectiveCamera; readonly renderer: WebGLRenderer;
  readonly assets: { gltf(): GLTFLoader; url(path: string): string }; // one lazy GLTF+KTX2 loader per page
  readonly atmosphere: AtmosphereReader; readonly quality: { readonly current: QualityProfile };
  readonly ground: GroundRegistry; readonly pois: PoiRegistry;
  readonly route: Promise<Route>; readonly collision: Promise<HeightField>; // collision: after the walk gate
  readonly params: URLSearchParams;
  readonly signal: AbortSignal;                 // aborted on init timeout and on dispose
  report(problem: { readonly state: "degraded" | "failed"; readonly message: string }): void;
}
export interface WorldSystem {
  readonly id: string;                          // kebab-case, unique, key in budget.ts
  readonly phase: UpdatePhase;
  readonly load: LoadPriority;
  readonly initTimeoutMs?: number;              // default 20 000 (critical, beforeWalk), 60 000 (background)
  readonly notices?: { readonly missing?: StringKey; readonly failed?: StringKey };
  init(ctx: SystemContext): Promise<InitOutcome>;
  isSettled?(): boolean;                        // walk gate, polled every 6 frames; default: init resolved
  onWalkStart?(): void;
  update(frame: FrameInfo): void;
  onQualityChange?(next: QualityProfile, previous: QualityProfile): void;
  setEnabled?(enabled: boolean): void;          // test hook for effects outside root; root.visible is the registry's
  dispose(): void;
}
export interface GroundRegistry {
  addSurface(surface: GroundSurface): void;     // both add* throw once the walk has started
  addEnclosure(enclosure: Enclosure): void;
  readonly surfaces: readonly GroundSurface[]; readonly enclosures: readonly Enclosure[]; // live, given to createPlayer
  startFloor(x: number, z: number): number | null; // highest optional GroundSurface.floorAt(x, z) (tunnel)
}
export interface World {
  init(priority: LoadPriority): Promise<void>;  // never rejects; failures become statuses
  isSettled(): boolean;                         // every critical/beforeWalk system settled, missing or failed
  startWalk(): void;                            // locks ground, onWalkStart, background inits in list order
  update(phase: UpdatePhase, frame: FrameInfo): void;
  setQuality(next: QualityProfile): void;
  status(): Readonly<Record<string, SystemStatus>>;
  dispose(): void;                              // reverse list order
}
export type WorldDeps = Omit<SystemContext, "root" | "signal" | "report"> & { readonly testHooks: boolean };
export function createWorld(systems: readonly WorldSystem[], deps: WorldDeps): World;
```
- **Order.** Systems update by phase, then in list order; init completion order never matters. `createWorldSystems(deps)` is the only list: a lane adds one import and one entry, and the integrator resolves the rebase. `prePlayer` holds camera-independent state (atmosphere); the player sub-steps follow unchanged; `postPlayer` holds what follows the camera or player (sky dome, terrain selection, tunnel lamp, vegetation culling, character, POI discovery, audio); `preRender` holds the shadow cascades. One `renderer.render` per frame, so `renderer.info` counts shadow passes.
- **Isolation.** Each system's `init`, `update`, `onQualityChange` and `dispose` runs in its own `try/catch`. A throwing `update` marks it `failed`, hides its root, skips it from then on and logs one `console.error("[world:<id>] …")`. A rejected or timed-out `init` marks it `failed` and aborts `ctx.signal`. `missing` is a status, not an error (today's behaviour for ungenerated assets). Systems catch their own async errors and call `ctx.report`. `trail.json` and the collision field are not systems: the walk needs them, so the bootstrap keeps their fatal screen. E2E specs fail on console errors, so isolation hides no bug.
- **Loading order (keeps A3/A4).** (1) Start `trail.json` and all `critical` and `beforeWalk` inits together, the same parallel requests as today. (2) Await route and critical inits, place the camera, run the preview loop. (3) Poll `isSettled()` every 6 frames (terrain: visible or gave up). (4) Await `beforeWalk`, then collision, then create the player. (5) `startWalk()` releases the terrain detail. Nothing the first step does not need is requested before the walk; background inits follow in list order, with at most 2 requests in flight per system.
- **Lights and scene.** Lights may be added only in `critical` inits, because a change in light count recompiles every lit material; only L1 adds lights. Objects go only under `ctx.root`. `scene.fog`, `scene.background` and tone mapping belong to the atmosphere writer.
- **Test hooks** (only with `TEST_HOOKS_ENABLED`): `window.__world = { setEnabled(id, on), freezeTime(s | null), setQuality(tier) }`, plus `__appState.systems[id] = { status, cpuMs }` (`cpuMs` is the rolling median of `update`) and `__appState.quality`. `__appState.terrain` and `__appState.tunnel` keep their shape, fed from typed handles that `createWorldSystems` returns.
- **Migration.** Systems keep today's creation order, so material ids, and with them three's opaque sort, stay unchanged.

| id | Phase | Load | Today in | Owner after B0 |
|---|---|---|---|---|
| `atmosphere` | prePlayer | critical | `sky.ts` constants, `createFog(summit)` | L1 |
| `sky` | postPlayer | critical | `sky.ts` (dome, hemisphere, sun) | L1 |
| `sea` | postPlayer | critical | `sea.ts` → `world/sea/system.ts` | L4 |
| `terrain` | postPlayer | critical; settled = visible or gave up; `onWalkStart` = `setDetailEnabled(true)` | `main.ts`, `terrain/` | integrator |
| `tunnel` | postPlayer | critical; surface, enclosure and lamp in init; mesh in background, failure via `report` | `main.ts`, `tunnel*.ts` | integrator |
| `debug-trail` | postPlayer | background, awaits `collision`; listed only with `?debug=trail` | `main.ts` | integrator |

`main.ts` ends as the bootstrap: device probe → profile → renderer, camera, scene → atmosphere → `createWorld(createWorldSystems(…))` → route → loop → walk gate → collision → player → governor. The poster, HUD and status texts come from `world.status()` and each system's `notices`.

### 2. Atmosphere (contract `app/src/world/atmosphere.ts`; L1 implements under `world/atmosphere/`, no `index.ts`)
```ts
export type Rgb = { readonly r: number; readonly g: number; readonly b: number }; // linear, three's working space
export type AtmosphereState = {
  readonly preset: "day" | "sunset";
  readonly sun: { readonly direction: Vec3; readonly color: Rgb; readonly intensity: number }; // unit, towards the sun
  readonly ambient: { readonly sky: Rgb; readonly ground: Rgb; readonly intensity: number };
  readonly horizon: Rgb; readonly zenith: Rgb;
  readonly fog: { readonly color: Rgb; readonly near: number; readonly far: number; readonly sunScatter: number }; // 0 = plain fog
  readonly toneMapping: "aces" | "agx"; readonly exposure: number;
};
export type AtmosphereUniforms = {
  readonly uAtmoSunDirection: IUniform<Vector3>; readonly uAtmoSunColor: IUniform<Color>; // colour x intensity
  readonly uAtmoHorizon: IUniform<Color>; readonly uAtmoZenith: IUniform<Color>;
  readonly uAtmoFog: IUniform<Vector4>;                                                    // near, far, sunScatter, 0
};
export interface AtmosphereReader {
  readonly state: AtmosphereState;
  readonly version: number;              // +1 per write; readers compare with the version they last applied
  readonly uniforms: AtmosphereUniforms; // live, shared by reference, never cloned
}
export interface AtmosphereWriter extends AtmosphereReader { set(next: Partial<AtmosphereState>): void } // in place, version++
export type AtmosphereSurface = { readonly kind: "generic" } | { readonly kind: "terrain-tile"; readonly tileId: string };
export function createAtmosphere(initial: AtmosphereState): AtmosphereWriter;
export const ATMOSPHERE_PATCH_KEY = "penyal-atmosphere-v1";
/** Adds the shared block to a lit material (L1 adds fog in-scattering and baked shadows). Idempotent. */
export function attachAtmosphere(material: Material, atmosphere: AtmosphereReader, surface?: AtmosphereSurface): void;
// app/src/core/shaderPatch.ts
export type ShaderPatch = {
  readonly key: string;                                  // versioned; bump on any GLSL change
  readonly uniforms: Readonly<Record<string, IUniform>>; // shared by reference
  readonly apply: (vertexShader: string, fragmentShader: string) => { vertexShader: string; fragmentShader: string };
};
/** One onBeforeCompile per material applies its patches in order; cache key = keys joined by "|". Idempotent per key. */
export function addShaderPatch(material: Material, patch: ShaderPatch): void;
```
- **Writer.** Only the `atmosphere` system (L1) gets the writer: `createWorldSystems` passes it to that factory alone, and every other system sees `ctx.atmosphere` as a reader. Writes happen only in `prePlayer`, at most once per frame. When `version` changes, the writer applies `scene.fog`, `scene.background`, `toneMapping` and the exposure, and the sky rebuilds its lights.
- **B0 defaults** are today's constants, passed through `new Color(hex)` so the values are bit-identical: sun (0.5, 0.75, 0.6) normalised, 0xfff1d6 × 2.6; hemisphere 0xcfe6ff/0x6b5a3c × 1.1; horizon 0xbcd6ea; zenith 0x4f8fd0; fog from `fogRangeFor(summit)`; ACES; exposure 1; `sunScatter` 0.
- **Shader patches.** `applyTerrainDetail` becomes `addShaderPatch(material, terrainDetailPatch(uniforms))` under the same key. With one patch, the cache key stays exactly `"penyal-terrain-detail-v4"`, so programs and captures are unchanged. Custom `ShaderMaterial`s (sky, sea) spread `atmosphere.uniforms` into their own `uniforms`, and a clone must call `attachAtmosphere` again.
- **B0 versus L1.** In B0, `attachAtmosphere` only declares the uniforms and the terrain does not use it. L1 adds the GLSL (in-scattering instead of `fog_fragment`, plus a baked-shadow lookup for `terrain-tile`) and bumps the key.
- **Only sanctioned cross-lane edit:** L1 adds the `attachAtmosphere` call in the terrain material hook. Other lanes call it on their own materials. Baked masks from `lightbake.py` go to `assets/generated/lightbake/<preset>/` with their own manifest and are looked up by `tileId`; the terrain manifest does not change.

### 3. Quality profile (`app/src/core/quality.ts`)
```ts
export type QualityTier = "low" | "medium" | "high";
export type DeviceInfo = { readonly coarsePointer: boolean; readonly deviceMemoryGb?: number; readonly cores?: number; readonly softwareRenderer: boolean };
export type QualityProfile = {
  readonly tier: QualityTier; readonly source: "heuristic" | "override" | "startup" | "downgrade";
  readonly resolution: { readonly maxPixelRatio: number; readonly scale: number; readonly minScale: number };
  readonly terrain: { readonly detail: "off" | "1k" | "2k"; readonly sseThresholdPx: number };
  readonly shadows: "none" | "baked" | "cascaded";
  readonly vegetation: { readonly density: number; readonly maxDistanceM: number };
  readonly sea: "flat" | "waves" | "waves-foam"; readonly textures: "1k" | "2k";
};
export function probeDevice(): DeviceInfo; // the only effectful function here
export function selectInitialTier(device: DeviceInfo): QualityTier;
export function profileFor(tier: QualityTier, device: DeviceInfo): QualityProfile;
export function resolveInitialProfile(device: DeviceInfo, search: string): QualityProfile; // ?quality=, then ?terrain=
export type GovernorDecision =
  | { readonly kind: "keep" } | { readonly kind: "scale"; readonly scale: number }
  | { readonly kind: "tier"; readonly tier: QualityTier; readonly source: "startup" | "downgrade" };
export interface QualityGovernor { // interface fixed in B0; implemented with B11 after A7
  push(frameMs: number, nowMs: number): GovernorDecision; // raw rAF interval of a visible walking frame; pure
  readonly snapshot: { readonly tier: QualityTier; readonly scale: number; readonly downgrades: number };
}
export function createQualityGovernor(initial: QualityProfile, options?: Partial<GovernorOptions>): QualityGovernor;
```
| Knob | low | medium | high | At runtime |
|---|---|---|---|---|
| `resolution.scale` start / floor | 1 / 0.6 | 1 / 0.7 | 1 / 0.8 | live (`setPixelRatio`) |
| `maxPixelRatio`, `sseThresholdPx` | today's device rule (1.5/2; 4/2 px) | same | same | live |
| `terrain.detail` | off | 1k | 1k touch, 2k desktop | next load |
| `shadows` | none | baked | cascaded | recompile (one hitch) |
| `vegetation` density / distance\* | 0.35 / 60 m | 0.7 / 120 m | 1 / 200 m | live |
| `sea`\* | flat | waves | waves-foam | recompile |
| `textures` (non-terrain) | 1k | 1k | 2k desktop, 1k touch | next load |
| `antialias` | desktop only (today) | same | same | reload |

\* Provisional; L3 and L4 tune these values within the budget.

- **Initial tier** (reproduces today's terrain result): software renderer → `low`; touch device with ≥ 6 GB and ≥ 6 cores → `medium`, otherwise `low`; desktop with ≤ 2 GB or ≤ 2 cores → `low`, otherwise `high`.
- **Overrides.** `?quality=` sets the tier. `?terrain=low|high` keeps its current, terrain-only meaning and wins over the tier.
- **What moves.** `selectQualityTier`, `defaultQualityTier` and `tierFromSearch` move here with their tests, plus a table-driven equivalence test over every input combination. `terrain/quality.ts` keeps only `terrainOptions(profile)`.
- **Applying a change.** `world.setQuality` calls `onQualityChange` in list order. Each system applies its live and recompile knobs; the rest waits for the next load. In B0 the terrain reads the profile only at init.
- **Governor defaults** (provisional until A7). Startup: skip the first 1 s of walking, then measure 2.5 s; p50 > 22 ms drops one tier. Scale: −0.1 when the 3 s p95 > 30 ms, +0.1 when the 5 s p95 < 20 ms, never below the floor. Tier: drop one only at the scale floor when the 10 s p95 > 33.3 ms. At least 15 s between changes, at most 2 tier changes per session, never an automatic upgrade; hidden tabs and pre-walk frames are ignored.

### 4. Budget (`app/src/core/budget.ts`)
```ts
export type SystemBudget = { readonly drawCalls: number; readonly triangles: number; readonly ms: number };
export const FRAME_BUDGET: Readonly<Record<QualityTier, { readonly drawCallsTarget: number; readonly drawCallsCap: number; readonly trianglesCap: number }>>;
export const SYSTEM_BUDGETS: Readonly<Record<QualityTier, Readonly<Record<string, SystemBudget>>>>;
export const MS_CALIBRATION: number | null; // desktop-Metal to reference-phone ms factor from A7; null: ms only reported
```
`medium` on the reference phone. Calls and ms come from the spec; the triangle figures are new and provisional.

| id | atmosphere | sky | terrain | tunnel | sea | vegetation | structures | character | shadows | poi | audio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| calls | 0 | 2 | 25 | 3 | 3 | 40 | 15 | 5 | 0 | 2 | 0 |
| triangles | 0 | 5k | 350k | 10k | 50k | 250k | 60k | 20k | 0 | 2k | 0 |
| ms | 0.1 | 1 | 6 | 0.5 | 3 | 6 | 1 | 1 | 0 | 0.2 | 0.5 CPU |

- **Totals and caps.** `medium` sums to 95 calls, 747k triangles and 19.3 ms. The call target is 100 and the cap 200. Triangles are capped at 1M in `low`/`medium` and 1.5M in `high`.
- **Other tiers.**

  | Tier | vegetation | sea | shadows | Total calls |
  |---|---|---|---|---|
  | `low` | 20 calls / 100k triangles | 1 call / 2 triangles | — | 73 |
  | `high` | 50 calls / 400k | — | 60 calls / 400k / 5 ms | 165 |

  `debug-*` ids are exempt.
- **Static checks.** `budget.test.ts` checks the sums. In dev and E2E builds, the registry throws at boot if a registered id has no row.
- **E2E.** `app/e2e/budget.spec.ts` runs at `centre`, `turnstile` and `viewpoint-1795591637` (plus `tunnel-east` for `tunnel`), once per `?quality=` tier, with reduced motion and `freezeTime`. It settles and reads the totals; then, for each id, it calls `__world.setEnabled(id, false)`, waits 2 frames and asserts the difference against the id's row and the total against the cap. Counts do not depend on the GPU, so this runs in SwiftShader and in CI.
- **GPU timing.** With `PENYAL_E2E_GPU=metal` (the flags of `terrain-material.spec.ts`: no vsync, no frame cap), the spec also measures the median of 300 uncapped frames with each system on and off. It writes the result and `cpuMs` to `<E2E_OUTPUT_DIR>/budget.json`. The ms checks fail only once `MS_CALIBRATION` is set.
- **No runtime enforcement.** Production code never reads the budget.

### 5. POI and notebook (`app/src/content/poi.ts`, `notebook.ts`; discovery is the `poi` system, `app/src/world/poi.ts`)
```ts
// reuses kebabId, isoDate and httpsUrl, which schema.ts now exports
const text = z.strictObject({ es: z.string().min(1), va: z.string().min(1).optional(), en: z.string().min(1).optional() });
const sentence = z.strictObject({ text, facts: z.array(kebabId).min(1) }); // no sentence without a fact
const block = z.discriminatedUnion("kind", [
  z.strictObject({ kind: z.literal("facts"), heading: text, items: z.array(sentence).min(1) }),
  z.strictObject({ kind: z.literal("conflict"), fact: kebabId, heading: text, values: z.array(z.strictObject({ text })).min(2) }),
  z.strictObject({ kind: z.literal("unverified"), fact: kebabId, text }),
  z.strictObject({ kind: z.literal("notice"), text, source: kebabId }),
]);
const review = z.strictObject({ status: z.enum(["missing", "draft", "team", "reviewed"]), by: z.string().min(1).optional(), date: isoDate.optional() });
export const poiSchema = z.strictObject({
  id: kebabId, status: z.enum(["draft", "published"]),
  anchor: z.string().min(1), discoveryRadius: z.number().min(3).max(40), // trail.json anchor key; horizontal metres
  title: text, summary: z.array(sentence).min(1), expand: z.array(block),  // summary <= 60 words per language
  images: z.array(z.strictObject({ file: z.string().regex(/^[a-z0-9-]+\.(?:avif|webp|jpg)$/), alt: text,
    author: z.string().min(1), licence: z.enum(["CC0-1.0", "CC-BY-4.0"]), source: httpsUrl, modified: z.boolean() })).max(3),
  translations: z.strictObject({ va: review, en: review }),
});
export type Poi = z.infer<typeof poiSchema>;
export function validatePois(pois: unknown[], facts: unknown, sources: unknown, anchors: ReadonlySet<string> | null): string[];
export interface PoiRegistry {
  list(): readonly { readonly poi: Poi; readonly position: Vec3 }[];
  onDiscover(listener: (poi: Poi) => void): () => void; // once per POI per visit, 2D radius; listener errors caught
}
export const NOTEBOOK_KEY = "penyal.notebook.v1";      // { version: 1, entries }, parsed with zod on read
export type NotebookEntry = { readonly poiId: string; readonly savedAt: string }; // ISO 8601
export type NotebookResult = { readonly ok: true } | { readonly ok: false; readonly reason: "unavailable" | "quota" | "error" };
export interface Notebook {
  add(poiId: string): NotebookResult;  // idempotent: keeps the first savedAt
  has(poiId: string): boolean;
  list(): readonly NotebookEntry[];    // in saving order
  readonly persistent: boolean;        // false: storage blocked; entries last for this visit only
}
export function createNotebook(storage: Pick<Storage, "getItem" | "setItem"> | null, now: () => Date): Notebook;
export function browserStorage(): Pick<Storage, "getItem" | "setItem"> | null; // window.localStorage inside try/catch
```
`app/src/content/pois.test.ts` runs `validatePois` over `content/pois/*.json`. Its messages follow the style of `registry.test.ts`.
1. **Ids.** The id equals the file name and is unique. Every cited fact and source exists.
2. **Never pick a value.** `summary` cites only `verified` facts. `conflict` and `unverified` facts appear only in a block of their own kind. A `conflict` block has as many values as the fact, in registry order.
3. **Length.** At most 60 words per language present. A word is a whitespace-separated token with a letter or a digit; this gives the 56 and 53 words stated for ficha-piloto A and B.
4. **Drift.** Every number in a sentence must appear in the `value`, `unit` or value `note` of a cited fact; a fact-level `note` does not count, since it has no source. Numbers are normalised per language (es/va `70.000`, `53,3`; en `70,000`, `53.3`; `facts.json` uses the Spanish form) and always written as digits. A `conflict` value is checked against the value at the same index.
5. **Publish gate.** `published` requires es, va and en everywhere; `va` must be `reviewed`, with `by` and `date`; `en` must be `team` or `reviewed`. This makes the phase B exit criterion a test. Outside dev, only published POIs are shown.
6. **Anchor.** It must exist in `app/public/assets/generated/trail.json`. The check is skipped when that file is absent and fails under `PENYAL_REQUIRE_DATA=1`.
7. **Images.** The file must exist in `app/public/content/images/`. A licence other than CC0 or CC BY 4.0 needs an amendment to ADR 0007.

- **Sources and loading.** Cards list no sources of their own: they take the title, link, access date and archived copy from the cited facts, and show each fact's status. POIs load through `import.meta.glob` and facts through a dynamic import, both with the same schemas.
- **Notebook storage.** `browserStorage()` and every storage call run inside `try/catch`. Blocked storage gives `unavailable`; `QuotaExceededError` gives `quota`. The in-memory copy is the source of truth for the visit; an invalid stored value starts the notebook empty and is replaced on the next `add`. Only ids and dates are stored: no cookies, no network.

### 6. Worktrees (`scripts/worktree-setup.sh <l1..l8>`)
- **Guards.** The script refuses to run outside the main checkout, on a dirty tree, or with an unknown lane.
- **Worktree.** It runs `git worktree add .worktrees/<lane> -b feat/b-<lane> main`. `.worktrees/` is gitignored; Biome skips it through `vcs.useIgnoreFile`.
- **Inputs, symlinked** (read-only, absolute links): `data/raw` (1.0 GB), `data/manual` (the Quaternius zips, ADR 0008), `tools/bin`, `tools/ktx-*`.
- **Outputs, cloned** with APFS `cp -cR`, so each lane regenerates its own: `build/` (96 MB) and `app/public/assets/generated/` (29 MB).
- **Dependencies.** It then runs `pnpm install --frozen-lockfile` and `uv sync --project pipeline --locked`, and prints the port and the `git worktree remove` command.
- **Playwright.** `app/playwright.config.ts` derives lane defaults from its path `/.worktrees/l<n>/`: `E2E_PORT` = 5180 + n, `E2E_OUTPUT_DIR` = `test-results/l<n>`, `workers: 1`. Explicit env vars win. Main keeps 5175; lane dev servers use 5190 + n. Specs write through `testInfo.outputPath()`.
- **Docs.** `CLAUDE.md` documents the flow.

### 7. Migration plan (implementer, after phase A closes; one commit per row)
Precondition: main is green and `uv run --project pipeline penyal verify-generated` exits 0.

| # | Commit | Change | Verify |
|---|---|---|---|
| 1 | `test(e2e): compare the fixed viewpoints before and after a change` | `viewpoints.spec.ts`: `reducedMotion: "reduce"` (the camera snaps, `cameras.ts:179`); `toHaveScreenshot` at the 6 anchors at `low`, plus `turnstile` and `viewpoint-1795591637` with `?terrain=high`; a metrics JSON snapshot (calls, triangles, `renderer.info.programs.length`, `terrain.displayed`, player and camera positions); `snapshotPathTemplate` → `build/e2e-baselines/` (not committed); `AppState.render.programs` | `pnpm --filter @penyal/app e2e -- viewpoints --update-snapshots`, then twice without the flag: 0 differing pixels. Otherwise record the noise as the tolerance; above 0.1 %, investigate first |
| 2 | `refactor(app): compose shader patches and move the terrain detail onto them` | `core/shaderPatch.ts`, `terrain/material.ts` | `pnpm --filter @penyal/app exec vitest run src/core/shaderPatch.test.ts src/world/terrain/material.test.ts`; `pnpm --filter @penyal/app e2e -- viewpoints` |
| 3 | `refactor(app): select quality through a three-tier profile` | `core/quality.ts` with the equivalence test; `terrain/quality.ts`; streamer options; pixel ratio from the profile | `pnpm test`; `pnpm --filter @penyal/app e2e -- viewpoints terrain-material` |
| 4 | `feat(app): add the atmosphere contract` | `world/atmosphere.ts`; tests for the version, the in-place uniforms and the composed key `"penyal-terrain-detail-v4\|penyal-atmosphere-v1"` | `pnpm --filter @penyal/app exec vitest run src/world/atmosphere.test.ts` |
| 5 | `feat(app): add the world system registry` | `world/systems.ts`, tested with fake systems: phase and list order; isolation of init rejection, timeouts and update throws; walk gate; ground lock; reverse dispose; `setEnabled` | `pnpm --filter @penyal/app exec vitest run src/world/systems.test.ts` |
| 6 | `refactor(app): run atmosphere, sky and sea as world systems` | Hybrid `main.ts` | `pnpm lint && pnpm typecheck && pnpm test`; full `pnpm --filter @penyal/app e2e`; viewpoints identical |
| 7 | `refactor(app): run terrain, tunnel and trail debug as world systems` | `main.ts` becomes the bootstrap; `AppState.systems`; `__world` | As in 6, including `loading` and `tunnel`; captures and metrics identical |
| 8 | `feat(app): add the per-system budget and its E2E` | `core/budget.ts`, `e2e/budget.spec.ts` | `pnpm --filter @penyal/app e2e -- budget`; `PENYAL_E2E_GPU=metal pnpm --filter @penyal/app e2e -- budget` (report) |
| 9 | `feat(content): add the POI schema, notebook and drift test` | `content/poi.ts`, `content/notebook.ts`, `world/poi.ts` (registered; inert until a POI is published); ficha-piloto A and B in es as draft `content/pois/*.json` | `pnpm --filter @penyal/app exec vitest run src/content/` |
| 10 | `chore(scripts): set up one git worktree per phase B lane` | Script; Playwright lane defaults; `.gitignore`; `CLAUDE.md` | `scripts/worktree-setup.sh l1 && (cd .worktrees/l1 && pnpm --filter @penyal/app e2e -- viewpoints)` passes on 5181 while main's dev server runs |

## Consequences
- **Easier.** A lane adds one system file and one list entry. A failing optional system no longer ends the walk. Every system has measured draw calls, triangles and a toggle. A card cannot contradict `facts.json`, pick a side in a conflict, or ship without the valenciano review.
- **Harder.** There is one more indirection between `main.ts` and what is drawn. Ground surfaces must exist before the walk, and the light count is frozen after the critical init. B0 is 10 commits, which may take longer than the planned 1–1.5 days.
- **Follow-ups.** L6 needs `Player.setAvatar(object | null)` to replace the capsule; the integrator adds it when L6 starts. Identical captures are required only for refactors; lanes that change the look refresh the baseline on purpose and attach the captures to the review.
- **Tech-lead review notes (2026-10-11).**
  - Cascaded shadows (`high`) add and remove lights when the tier changes. The rule "lights only in `critical` inits" therefore has one exception: the shadows system may change its lights in `onQualityChange`, accepting the one recompile hitch listed in §3. No other system adds lights after the critical init.
  - `review.by` stores the name the reviewer agrees to be credited with. Ask the reviewer before writing it. A handle or initials are fine.
- **Not verified yet.**
  - Whether SwiftShader captures are pixel-identical from run to run (commit 1 measures it).
  - That `renderer.info.render.calls` includes the shadow passes: inferred from the single `render()`, and L1's toggle confirms it.
  - The Metal-to-phone ms ratio, every ms and triangle figure, and the governor thresholds (A7).
  - That `cp -c` clones on this APFS volume; otherwise it makes a full copy of about 125 MB.
- **Content problem found.** The ficha-piloto fails rule 4 twice. "en 1282 Pere III…" rests on the fact-level note of `pobla-founding`, and "inauguradas en 1992" on the note of `centre-name`. The content owner must turn each into a sourced value or drop it; commit 9 leaves both out of the drafts and says so.
- **Open.** Which `viewpoint-*` anchor is the Mirador de Ponent is pending the park; `pobla` is the site, not the viewpoint.

## Amendment 1 (2026-10-11): GPU texture-memory budget
- **Why.** §4 budgets draw calls, triangles and ms, not memory. E1 (surface masks) and E2 (vegetation atlases) add textures, and on phones texture memory, not triangles, is what kills a WebGL context.
- **Decision.** `SystemBudget` gains `textureMiB`: the estimated resident texture memory, including mips (×4/3). Bytes per pixel follow the mobile transcode target: ETC1S RGB → ETC1/ETC2 0.5 B/px; ETC1S RGBA and UASTC → ETC2 RGBA8 or ASTC 4×4, 1 B/px; uncompressed RGBA8 → 4 B/px.
  - `FRAME_BUDGET` gains `textureMiBCap` per tier: `low` 32, `medium` 48, `high` 160 MiB. High is desktop, with 2k detail.
  - These caps are **provisional until A7.** WebGL exposes no GPU-memory query and the phones' limits are not documented, so the caps are a design ceiling, not a measured limit.
- **Estimate today** (2026-10-11; dimensions and formats read from the generated KTX2 headers and the terrain manifest):
  - terrain near tiles: 10.7 MiB if all 16 are at LOD0 1024² ETC1S, 2.4 typical;
  - far ring 2.7;
  - detail at 1k: 5.3 on phones, 21.3 at 2k on desktop;
  - surface masks: 10.7 worst, with 8 resident UASTC tiles;
  - pine atlas 0.7.
  - Totals on a phone: about 15 MiB typical and 30 MiB worst, under the 48 MiB `medium` cap.
- **Measurement.** `budget.spec.ts` sums the estimate over the textures in use. It reads each texture's dimensions and format from three's texture objects and uses a pure `textureBytes(width, height, format, mips)` helper, unit-tested per format. The spec asserts the sum per system and in total against the tier row.
  - Production code still never reads the budget (§4).
- **Rule for lanes.** A system that streams textures, such as the masks or terrain tiles, loads them only for resident tiles and disposes them on eviction.
  - The budget row covers its worst resident set, not the whole map.
