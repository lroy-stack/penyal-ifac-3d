import {
  type BufferGeometry,
  FrontSide,
  Group,
  type Material,
  Mesh,
  type Object3D,
  type PerspectiveCamera,
  Texture,
  Vector3,
} from "three";
import type { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import type { KTX2Loader } from "three/addons/loaders/KTX2Loader.js";
import { fetchBuffer } from "../../core/http";
import { createDetailTextures, type DetailSet, type DetailSource } from "./detailTextures";
import { resolveAssetUrl, type TerrainManifest, type TerrainTile } from "./manifest";
import { applyTerrainDetail, createTerrainDetailUniforms } from "./material";
import { defaultDetailSet, defaultQualityTier, type QualityTier } from "./quality";
import {
  chooseEvictions,
  DEFAULT_BUDGET,
  EVICTION_GRACE_MS,
  type ResidentBudget,
  type ResidentEntry,
} from "./residency";
import {
  chooseDisplayed,
  coarsestLevel,
  constrainLodSteps,
  DEFAULT_MAX_LOD_STEP,
  FAR_ID,
  type LoadRequest,
  loadRequests,
  planTiles,
  requiredTiles,
  type View,
} from "./selection";

export type LoadedTile = {
  /** Scene content of the glTF; the streamer owns and eventually disposes it. */
  readonly object: Object3D;
  /** Size on the wire, for the statistics. */
  readonly bytes: number;
};

/**
 * Fetches and parses one tile; must reject when `signal` aborts. `ktx2Loader` is the KTX2 loader
 * behind it, when there is one; the detail textures are loaded through it so the page keeps one
 * transcoder worker pool.
 */
export type TileLoader = ((url: string, signal: AbortSignal) => Promise<LoadedTile>) & {
  readonly ktx2Loader?: KTX2Loader | null;
};

/** Fetch with an AbortSignal (GLTFLoader.load cannot cancel one request), then parse. */
export function createGltfTileLoader(loader: GLTFLoader): TileLoader {
  const tileLoader: TileLoader = async (url, signal) => {
    const buffer = await fetchBuffer(url, signal);
    const path = url.slice(0, url.lastIndexOf("/") + 1);
    const gltf = await loader.parseAsync(buffer, path);
    signal.throwIfAborted();
    return { object: gltf.scene, bytes: buffer.byteLength };
  };
  return Object.assign(tileLoader, { ktx2Loader: loader.ktx2Loader });
}

export type TerrainStreamerOptions = {
  readonly manifest: TerrainManifest;
  /** URL the manifest was loaded from; tile URLs are relative to it. */
  readonly manifestUrl: string;
  readonly load: TileLoader;
  /** Screen-space error budget in pixels (see `sseThreshold`). */
  readonly sseThreshold: number;
  readonly maxConcurrent?: number;
  readonly budget?: ResidentBudget;
  readonly evictionGraceMs?: number;
  readonly now?: () => number;
  /** Delay (ms) before the first retry of a failed load; doubles each time. */
  readonly retryDelayMs?: number;
  readonly maxRetries?: number;
  /**
   * `high` adds triplanar limestone on cliffs and a near-ground detail layer; `low` keeps the
   * plain orthophoto. Defaults to `defaultQualityTier()` (URL override, pointer type, hardware).
   */
  readonly quality?: QualityTier;
  /**
   * Marble map set for the `high` tier; default from `defaultDetailSet`. Maps load through the
   * KTX2 loader of `load` (see `TileLoader`) from `materialsUrl`; without one the procedural
   * noise stays in use.
   */
  readonly detailSet?: DetailSet;
  /** Directory of the KTX2 maps, relative to the manifest; default `../materials/`. */
  readonly materialsPath?: string;
  /**
   * When false, only the critical path is fetched: the far mesh and the coarse LOD of the tiles
   * around the camera. Everything else waits for `setDetailEnabled(true)`, so the walk can start
   * before the rest of the terrain competes for the connection. Default true.
   */
  readonly detailEnabled?: boolean;
  /** Largest LOD-level difference allowed between edge-adjacent tiles; default 1. */
  readonly maxLodStep?: number;
};

export type TerrainStats = {
  /** Tiles held in memory per LOD level. */
  readonly resident: Readonly<Record<number, number>>;
  /** Tiles shown per LOD level. */
  readonly displayed: Readonly<Record<number, number>>;
  readonly farLoaded: boolean;
  /**
   * Near tiles that must be showing for the terrain to count as visible (those within
   * `REQUIRED_RADIUS` of the camera at the last update) and how many already have a LOD.
   */
  readonly coverage: { readonly required: number; readonly loaded: number };
  /** The far mesh and every required tile are loaded: the visitor sees terrain, not sky and sea. */
  readonly visible: boolean;
  /** Loading stopped (every retry failed) before the terrain became visible. */
  readonly gaveUp: boolean;
  readonly bytesLoaded: number;
  /** Requests in flight plus those waiting for a free slot. */
  readonly pending: number;
  readonly inFlight: number;
  /** Loads that failed and are waiting to retry or have been given up. */
  readonly failed: number;
  readonly lastError: string | null;
  readonly quality: QualityTier;
  /** What the detail shading uses: procedural noise or the marble maps at this size. */
  readonly detail: DetailSource;
};

export type TerrainStreamer = {
  /** Add to the scene. */
  readonly root: Group;
  /** Call once per frame. */
  readonly update: (view: View) => void;
  /** Releases (or holds again) the loads that are not on the critical path; see the option. */
  readonly setDetailEnabled: (enabled: boolean) => void;
  readonly stats: () => TerrainStats;
  readonly dispose: () => void;
};

const scratchForward = new Vector3();

/** Builds the selection view from a perspective camera and the drawing-buffer height in pixels. */
export function viewFromCamera(camera: PerspectiveCamera, viewportHeight: number): View {
  camera.getWorldDirection(scratchForward);
  return {
    position: { x: camera.position.x, y: camera.position.y, z: camera.position.z },
    forward: { x: scratchForward.x, y: scratchForward.y, z: scratchForward.z },
    fovY: (camera.fov * Math.PI) / 180,
    viewportHeight,
  };
}

type Entry = {
  readonly id: string;
  readonly level: number;
  readonly object: Object3D;
  lastNeeded: number;
};

type InFlight = { readonly request: LoadRequest; readonly controller: AbortController };
type Failure = { count: number; retryAt: number };

const keyOf = (id: string, level: number): string => `${id}:${level}`;

function disposeMaterial(material: Material): void {
  for (const value of Object.values(material)) {
    if (value instanceof Texture) value.dispose();
  }
  material.dispose();
}

/** Frees the GPU resources behind an object loaded from glTF. */
export function disposeObject(object: Object3D): void {
  object.traverse((child) => {
    if (!(child instanceof Mesh)) return;
    (child.geometry as BufferGeometry).dispose();
    const materials = Array.isArray(child.material) ? child.material : [child.material];
    for (const material of materials as Material[]) disposeMaterial(material);
  });
}

/** Terrain is opaque and single-sided; culling needs bounding volumes on every geometry. */
function prepareTerrainObject(object: Object3D, detail: ((m: Material) => void) | null): void {
  object.traverse((child) => {
    if (!(child instanceof Mesh)) return;
    child.frustumCulled = true;
    const geometry = child.geometry as BufferGeometry;
    if (geometry.boundingSphere === null) geometry.computeBoundingSphere();
    if (geometry.boundingBox === null) geometry.computeBoundingBox();
    const materials = Array.isArray(child.material) ? child.material : [child.material];
    for (const material of materials as Material[]) {
      material.side = FrontSide;
      detail?.(material);
    }
  });
  object.updateMatrixWorld(true);
}

function isAbort(error: unknown, signal: AbortSignal): boolean {
  return signal.aborted || (error instanceof DOMException && error.name === "AbortError");
}

/**
 * Streams the terrain tiles of a manifest. Order: the far mesh, then the coarsest LOD of every
 * near tile, then finer LODs nearest first; at most `maxConcurrent` requests at a time. A tile
 * keeps showing its current LOD until the wanted one is loaded, so there are never holes. Levels
 * above their resident budget are evicted after `evictionGraceMs` without use. Selection is our
 * own (screen-space error to the tile's box) because THREE.LOD measures to the object position,
 * which is wrong for 256 m tiles.
 */
export function createTerrainStreamer(options: TerrainStreamerOptions): TerrainStreamer {
  const { manifest, manifestUrl, load, sseThreshold } = options;
  const maxConcurrent = options.maxConcurrent ?? 2;
  const budget = options.budget ?? DEFAULT_BUDGET;
  const graceMs = options.evictionGraceMs ?? EVICTION_GRACE_MS;
  const clock = options.now ?? (() => performance.now());
  const maxLodStep = options.maxLodStep ?? DEFAULT_MAX_LOD_STEP;
  const quality = options.quality ?? defaultQualityTier();
  const detailUniforms = createTerrainDetailUniforms();
  const applyDetail =
    quality === "high" ? (m: Material) => applyTerrainDetail(m, detailUniforms) : null;
  const materialsPath = options.materialsPath ?? "../materials/";
  const detailTextures = createDetailTextures({
    loader: quality === "high" ? (load.ktx2Loader ?? null) : null,
    urlFor: (fileName) => resolveAssetUrl(manifestUrl, `${materialsPath}${fileName}`),
    uniforms: detailUniforms,
    set: quality === "high" ? (options.detailSet ?? defaultDetailSet(quality)) : "off",
  });
  const retryDelayMs = options.retryDelayMs ?? 2000;
  const maxRetries = options.maxRetries ?? 3;

  const root = new Group();
  root.name = "terrain";
  const tiles = manifest.near.tiles;
  const tileById = new Map<string, TerrainTile>(tiles.map((t) => [t.id, t]));
  const entries = new Map<string, Entry>();
  const residentLevels = new Map<string, Set<number>>();
  const inFlight = new Map<string, InFlight>();
  const failures = new Map<string, Failure>();
  const wantedPrevious = new Map<string, number>();
  const displayed = new Map<string, number>();
  let bytesLoaded = 0;
  let queued = 0;
  let lastError: string | null = null;
  let disposed = false;
  let required: readonly string[] = [];
  let detailEnabled = options.detailEnabled ?? true;

  const isResident = (id: string, level: number): boolean => entries.has(keyOf(id, level));

  const urlFor = (request: LoadRequest): string => {
    if (request.id === FAR_ID) return resolveAssetUrl(manifestUrl, manifest.far.url);
    const lod = tileById.get(request.id)?.lods.find((l) => l.level === request.level);
    if (lod === undefined) throw new Error(`Tile ${request.id} has no LOD ${request.level}.`);
    return resolveAssetUrl(manifestUrl, lod.url);
  };

  const track = (id: string, level: number, present: boolean): void => {
    const levels = residentLevels.get(id) ?? new Set<number>();
    if (present) levels.add(level);
    else levels.delete(level);
    residentLevels.set(id, levels);
  };

  const remove = (entry: Entry): void => {
    root.remove(entry.object);
    disposeObject(entry.object);
    entries.delete(keyOf(entry.id, entry.level));
    track(entry.id, entry.level, false);
  };

  const onLoaded = (request: LoadRequest, loaded: LoadedTile): void => {
    prepareTerrainObject(loaded.object, applyDetail);
    loaded.object.visible = request.id === FAR_ID;
    root.add(loaded.object);
    entries.set(keyOf(request.id, request.level), {
      id: request.id,
      level: request.level,
      object: loaded.object,
      lastNeeded: clock(),
    });
    track(request.id, request.level, true);
    bytesLoaded += loaded.bytes;
    failures.delete(keyOf(request.id, request.level));
  };

  const start = (request: LoadRequest): void => {
    const key = keyOf(request.id, request.level);
    const controller = new AbortController();
    inFlight.set(key, { request, controller });
    load(urlFor(request), controller.signal).then(
      (loaded) => {
        if (inFlight.get(key)?.controller === controller) inFlight.delete(key);
        if (disposed || controller.signal.aborted) disposeObject(loaded.object);
        else onLoaded(request, loaded);
      },
      (error: unknown) => {
        if (inFlight.get(key)?.controller === controller) inFlight.delete(key);
        if (isAbort(error, controller.signal)) return;
        const previous = failures.get(key);
        const count = (previous?.count ?? 0) + 1;
        failures.set(key, { count, retryAt: clock() + retryDelayMs * 2 ** (count - 1) });
        lastError = `${key}: ${error instanceof Error ? error.message : String(error)}`;
      },
    );
  };

  /** The far mesh and the coarsest LOD of a tile near the camera. */
  const isCritical = (request: LoadRequest, requiredSet: ReadonlySet<string>): boolean => {
    if (request.id === FAR_ID) return true;
    const tile = tileById.get(request.id);
    return (
      tile !== undefined && requiredSet.has(request.id) && request.level === coarsestLevel(tile)
    );
  };

  const canRequest = (request: LoadRequest, now: number): boolean => {
    const key = keyOf(request.id, request.level);
    if (inFlight.has(key)) return false;
    const failure = failures.get(key);
    return failure === undefined || (failure.count <= maxRetries && now >= failure.retryAt);
  };

  const update = (view: View): void => {
    if (disposed) return;
    const now = clock();
    const selected = planTiles(tiles, view, sseThreshold, wantedPrevious);
    const plans = constrainLodSteps(tiles, selected, maxLodStep);
    const inUse = new Set<string>();
    required = requiredTiles(tiles, view);

    for (const plan of selected) wantedPrevious.set(plan.id, plan.wanted);
    for (const plan of plans) {
      const levels = residentLevels.get(plan.id) ?? new Set<number>();
      const show = chooseDisplayed(plan.wanted, displayed.get(plan.id), levels);
      if (show === undefined) displayed.delete(plan.id);
      else displayed.set(plan.id, show);
      for (const level of levels) {
        const entry = entries.get(keyOf(plan.id, level));
        if (entry === undefined) continue;
        entry.object.visible = level === show;
        if (level === show || level === plan.wanted) {
          entry.lastNeeded = now;
          inUse.add(keyOf(plan.id, level));
        }
      }
    }
    const farEntry = entries.get(keyOf(FAR_ID, 0));
    if (farEntry !== undefined) farEntry.lastNeeded = now;

    const wantedByTile = new Map(plans.map((p) => [p.id, p.wanted]));
    for (const [key, flight] of inFlight) {
      const { id, level } = flight.request;
      if (id === FAR_ID) continue;
      const tile = tileById.get(id);
      if (tile === undefined || level === coarsestLevel(tile)) continue;
      if (wantedByTile.get(id) !== level) {
        flight.controller.abort();
        inFlight.delete(key);
      }
    }

    const outstanding = loadRequests(tiles, plans, isResident).filter(
      (r) => (failures.get(keyOf(r.id, r.level))?.count ?? 0) <= maxRetries,
    );
    queued = outstanding.length;
    detailTextures.settled(farEntry !== undefined && inFlight.size === 0 && queued === 0);
    const requiredSet = new Set(required);
    for (const request of outstanding) {
      if (inFlight.size >= maxConcurrent) break;
      if (!detailEnabled && !isCritical(request, requiredSet)) continue;
      if (canRequest(request, now)) start(request);
    }

    const evictable: ResidentEntry[] = [];
    for (const [key, entry] of entries) {
      const tile = tileById.get(entry.id);
      if (tile === undefined || entry.level === coarsestLevel(tile) || inUse.has(key)) continue;
      evictable.push({ id: entry.id, level: entry.level, lastNeeded: entry.lastNeeded });
    }
    for (const victim of chooseEvictions(evictable, budget, now, graceMs)) {
      const entry = entries.get(keyOf(victim.id, victim.level));
      if (entry !== undefined) remove(entry);
    }
  };

  const stats = (): TerrainStats => {
    const resident: Record<number, number> = {};
    for (const entry of entries.values()) {
      if (entry.id !== FAR_ID) resident[entry.level] = (resident[entry.level] ?? 0) + 1;
    }
    const shown: Record<number, number> = {};
    for (const level of displayed.values()) shown[level] = (shown[level] ?? 0) + 1;
    const farLoaded = entries.has(keyOf(FAR_ID, 0));
    const loaded = required.filter((id) => (residentLevels.get(id)?.size ?? 0) > 0).length;
    const visible = farLoaded && loaded === required.length;
    const pending = Math.max(queued, inFlight.size);
    return {
      resident,
      displayed: shown,
      farLoaded,
      coverage: { required: required.length, loaded },
      visible,
      gaveUp: !visible && pending === 0 && failures.size > 0,
      bytesLoaded,
      pending,
      inFlight: inFlight.size,
      failed: failures.size,
      lastError: lastError ?? detailTextures.lastError(),
      quality,
      detail: detailTextures.source(),
    };
  };

  return {
    root,
    update,
    setDetailEnabled: (enabled) => {
      detailEnabled = enabled;
    },
    stats,
    dispose: () => {
      disposed = true;
      detailTextures.dispose();
      for (const flight of inFlight.values()) flight.controller.abort();
      inFlight.clear();
      for (const entry of [...entries.values()]) remove(entry);
    },
  };
}
