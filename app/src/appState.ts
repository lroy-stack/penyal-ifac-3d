import type { FrameSnapshot } from "./core/frameStats";
import type { CameraMode } from "./player/cameras";
import type { TerrainStats } from "./world/terrain";

export type TerrainStatus = "loading" | "ready" | "missing" | "error";
export type TunnelStatus = TerrainStatus;

/** Snapshot published on `window.__appState` for automated checks (Playwright, manual console). */
export type AppState = {
  /**
   * True once the terrain is visible and the visitor can walk: the player exists, which happens
   * only after the far mesh and the coarse tiles around the start are showing (or the terrain
   * is missing or failed for good). Not merely "a frame was rendered".
   */
  ready: boolean;
  frames: number;
  player: {
    x: number;
    y: number;
    z: number;
    yaw: number;
    grounded: boolean;
    cameraMode: CameraMode;
    corridorHit: boolean;
    /** Simulated seconds since the player was created. */
    elapsed: number;
  };
  /** Names of the trail anchors the player has come within reach of. */
  anchorsReached: string[];
  terrain: {
    status: TerrainStatus;
    message: string | null;
    stats: TerrainStats | null;
  };
  render: { calls: number; triangles: number };
  /** Camera position in the local frame (for checks that it stays inside the tunnel). */
  camera: { x: number; y: number; z: number };
  tunnel: { status: TunnelStatus; message: string | null; meshLoaded: boolean };
  autowalk: { active: boolean; target: string | null; progress: number };
  /** Milliseconds since navigation start (performance.now) at which each loading milestone was reached. */
  loading: { terrainVisibleMs: number | null; readyMs: number | null };
  /** Test-only simulation speed (`?timescale=N`); 1 in normal use. */
  timescale: number;
  /** p95 of the raw requestAnimationFrame interval (ms), null before the first measured frame. */
  frameTimeP95Ms: number | null;
  /**
   * Rolling statistics of the raw frame interval (not the clamped simulation step): p50/p95/p99
   * and the number of frames over 50 ms, recomputed every few frames. Null until measured.
   */
  frameStats: FrameSnapshot | null;
};

declare global {
  interface Window {
    __appState?: AppState;
  }
}

export function createAppState(): AppState {
  return {
    ready: false,
    frames: 0,
    player: {
      x: 0,
      y: 0,
      z: 0,
      yaw: 0,
      grounded: false,
      cameraMode: "first",
      corridorHit: false,
      elapsed: 0,
    },
    anchorsReached: [],
    terrain: { status: "loading", message: null, stats: null },
    render: { calls: 0, triangles: 0 },
    camera: { x: 0, y: 0, z: 0 },
    tunnel: { status: "loading", message: null, meshLoaded: false },
    autowalk: { active: false, target: null, progress: 0 },
    loading: { terrainVisibleMs: null, readyMs: null },
    timescale: 1,
    frameTimeP95Ms: null,
    frameStats: null,
  };
}
