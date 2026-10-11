import type { WorldSystem } from "../systems";
import { INITIAL_TERRAIN_GATE, stepTerrainGate, type TerrainGateOutcome } from "./gate";
import { loadTerrainManifest } from "./manifest";
import { terrainOptions } from "./quality";
import {
  createGltfTileLoader,
  createTerrainStreamer,
  type TerrainStats,
  type TerrainStreamer,
  viewFromCamera,
} from "./streamer";

/** The manifest request has its own 30 s limit; the init must not give up before it does. */
export const TERRAIN_MANIFEST_PATH = "assets/generated/terrain/manifest.json";
/** While the terrain loads, its readiness is checked every N frames. */
export const GATE_CHECK_FRAMES = 6;

/** One step of the stall gate: what it saw and what it decided. */
export type TerrainGateStep = {
  readonly outcome: TerrainGateOutcome;
  readonly stats: TerrainStats;
};

/** What the bootstrap reads from the terrain system: the typed handle `createWorldSystems` returns. */
export type TerrainHandle = {
  /** The streamer exists: the manifest was found and valid. */
  readonly available: () => boolean;
  /** Why the manifest could not be used, when it was present but invalid. */
  readonly error: () => string | null;
  /** Statistics of the live streamer, or null without one. */
  readonly stats: () => TerrainStats | null;
  /** The gate step taken since the last call, or null. Steps run every few frames until visible. */
  readonly takeGateStep: () => TerrainGateStep | null;
};

export type TerrainSystemDeps = {
  readonly createStreamer: typeof createTerrainStreamer;
  readonly loadManifest: typeof loadTerrainManifest;
};

const DEFAULT_DEPS: TerrainSystemDeps = {
  createStreamer: createTerrainStreamer,
  loadManifest: loadTerrainManifest,
};

/**
 * The terrain as a world system. Its init is the critical path (manifest, far mesh and coarse
 * tiles are the streamer's first loads); the walk gate waits until the terrain is visible or has
 * given up. The gate counts real frame time, every `GATE_CHECK_FRAMES` frames, until the terrain
 * is first seen: after a failure it keeps running, because a slow link may still deliver it.
 */
export function createTerrainSystem(deps: TerrainSystemDeps = DEFAULT_DEPS): {
  readonly system: WorldSystem;
  readonly handle: TerrainHandle;
} {
  let streamer: TerrainStreamer | null = null;
  let error: string | null = null;
  let camera: Parameters<typeof viewFromCamera>[0] | null = null;
  let gate = INITIAL_TERRAIN_GATE;
  let gateElapsedMs = 0;
  let gateFrames = 0;
  let seenVisible = false;
  let settled = false;
  let step: TerrainGateStep | null = null;

  const system: WorldSystem = {
    id: "terrain",
    phase: "postPlayer",
    load: "critical",
    async init(ctx) {
      const manifestUrl = ctx.assets.url(TERRAIN_MANIFEST_PATH);
      const manifest = await deps.loadManifest(manifestUrl, ctx.signal);
      if (manifest.status === "missing") {
        return { status: "missing", message: "The terrain has not been generated." };
      }
      if (manifest.status === "error") {
        error = manifest.message;
        throw new Error(manifest.message);
      }
      camera = ctx.camera;
      streamer = deps.createStreamer({
        manifest: manifest.manifest,
        manifestUrl,
        load: createGltfTileLoader(ctx.assets.gltf()),
        ...terrainOptions(ctx.quality.current),
        detailEnabled: false,
      });
      ctx.root.add(streamer.root);
      return { status: "ready" };
    },
    // Latched: a later retry that makes progress does not take the walk back.
    isSettled: () => settled,
    onWalkStart: () => streamer?.setDetailEnabled(true),
    update(frame) {
      if (streamer === null || camera === null) return;
      streamer.update(viewFromCamera(camera, frame.drawingBufferHeight));
      if (seenVisible) return;
      gateElapsedMs += frame.realMs;
      gateFrames++;
      if (gateFrames % GATE_CHECK_FRAMES !== 1) return;
      const stats = streamer.stats();
      const next = stepTerrainGate(
        gate,
        {
          visible: stats.visible,
          gaveUp: stats.gaveUp,
          bytesLoaded: stats.bytesLoaded,
          loadedTiles: stats.coverage.loaded,
        },
        gateElapsedMs,
      );
      gate = next.state;
      gateElapsedMs = 0;
      if (next.outcome !== "waiting") settled = true;
      if (next.outcome === "visible") seenVisible = true;
      step = { outcome: next.outcome, stats };
    },
    dispose() {
      streamer?.dispose();
      streamer = null;
    },
  };

  const handle: TerrainHandle = {
    available: () => streamer !== null,
    error: () => error,
    stats: () => streamer?.stats() ?? null,
    takeGateStep: () => {
      const taken = step;
      step = null;
      return taken;
    },
  };
  return { system, handle };
}
