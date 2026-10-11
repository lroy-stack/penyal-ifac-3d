import { Group, type PerspectiveCamera, type Scene, type WebGLRenderer } from "three";
import type { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import type { PoiRegistry } from "../content/poi";
import type { QualityProfile } from "../core/quality";
import type { PlayerState } from "../player";
import type { StringKey } from "../ui/strings";
import type { AtmosphereReader } from "./atmosphere";
import type { Corridor, Enclosure, GroundSurface, HeightField } from "./ground";
import type { Anchor, Trail } from "./trail";

export type UpdatePhase = "prePlayer" | "postPlayer" | "preRender";

/**
 * critical: awaited before the first frame (small JSON only; the only place lights may be added).
 * beforeWalk: awaited before the player exists (ground surfaces).
 * background: started after the walk starts.
 */
export type LoadPriority = "critical" | "beforeWalk" | "background";

export type InitOutcome =
  | { readonly status: "ready" }
  | { readonly status: "missing"; readonly message: string };

export type SystemStatus =
  | { readonly state: "pending" | "loading" | "ready" | "disabled" }
  | { readonly state: "missing" | "degraded" | "failed"; readonly message: string };

export type FrameInfo = {
  readonly frame: number;
  /** Simulated seconds this frame: the clamped delta times the timescale. */
  readonly dt: number;
  /** Simulated seconds since boot; frozen by the test hook. */
  readonly time: number;
  /**
   * Real milliseconds since the previous frame, capped at 1000 and 0 for the first frame after a
   * start or after the tab was hidden. The terrain gate counts real time, not simulated time.
   */
  readonly realMs: number;
  readonly drawingBufferHeight: number;
  /** Null while previewing, before the player exists. */
  readonly player: PlayerState | null;
};

export type Route = {
  readonly trail: Trail;
  readonly corridor: Corridor;
  readonly start: Anchor;
  readonly startYaw: number;
};

export interface GroundRegistry {
  /** Both add* throw once the walk has started. */
  addSurface(surface: GroundSurface): void;
  addEnclosure(enclosure: Enclosure): void;
  /** Live arrays, given to `createPlayer`. */
  readonly surfaces: readonly GroundSurface[];
  readonly enclosures: readonly Enclosure[];
  /** Highest `floorAt(x, z)` of the surfaces that have one (the tunnel), or null. */
  startFloor(x: number, z: number): number | null;
}

/** The registry the world owns; `lock` is called by `startWalk`. */
export type LockableGround = GroundRegistry & { lock(): void };

export function createGroundRegistry(): LockableGround {
  const surfaces: GroundSurface[] = [];
  const enclosures: Enclosure[] = [];
  let locked = false;
  const requireOpen = (what: string): void => {
    if (locked) {
      throw new Error(
        `Cannot add a ${what} after the walk has started: the player keeps these lists. Add it in a critical or beforeWalk init.`,
      );
    }
  };
  return {
    addSurface(surface) {
      requireOpen("ground surface");
      surfaces.push(surface);
    },
    addEnclosure(enclosure) {
      requireOpen("enclosure");
      enclosures.push(enclosure);
    },
    surfaces,
    enclosures,
    startFloor(x, z) {
      let best: number | null = null;
      for (const surface of surfaces) {
        const floor = surface.floorAt?.(x, z) ?? null;
        if (floor !== null && (best === null || floor > best)) best = floor;
      }
      return best;
    },
    lock() {
      locked = true;
    },
  };
}

export interface SystemContext {
  readonly scene: Scene;
  /** Add objects only under `root` (named `system:<id>`, already in the scene). */
  readonly root: Group;
  readonly camera: PerspectiveCamera;
  readonly renderer: WebGLRenderer;
  /** One lazy GLTF + KTX2 loader per page. */
  readonly assets: { gltf(): GLTFLoader; url(path: string): string };
  readonly atmosphere: AtmosphereReader;
  readonly quality: { readonly current: QualityProfile };
  readonly ground: GroundRegistry;
  readonly pois: PoiRegistry;
  readonly route: Promise<Route>;
  /** Resolves after the walk gate. */
  readonly collision: Promise<HeightField>;
  readonly params: URLSearchParams;
  /** Aborted on init timeout and on dispose. */
  readonly signal: AbortSignal;
  report(problem: { readonly state: "degraded" | "failed"; readonly message: string }): void;
}

export interface WorldSystem {
  /** kebab-case, unique, key in budget.ts. */
  readonly id: string;
  readonly phase: UpdatePhase;
  readonly load: LoadPriority;
  /** Default 20 000 (critical, beforeWalk) and 60 000 (background). */
  readonly initTimeoutMs?: number;
  readonly notices?: { readonly missing?: StringKey; readonly failed?: StringKey };
  init(ctx: SystemContext): Promise<InitOutcome>;
  /** Walk gate, polled every 6 frames; default: init resolved. */
  isSettled?(): boolean;
  onWalkStart?(): void;
  update(frame: FrameInfo): void;
  onQualityChange?(next: QualityProfile, previous: QualityProfile): void;
  /** Test hook for effects outside root; `root.visible` is the registry's. */
  setEnabled?(enabled: boolean): void;
  dispose(): void;
}

export interface World {
  /** Never rejects; failures become statuses. */
  init(priority: LoadPriority): Promise<void>;
  /** Every critical and beforeWalk system has settled, was missing or failed. */
  isSettled(): boolean;
  /** Locks the ground, calls `onWalkStart` and starts the background inits in list order. */
  startWalk(): void;
  update(phase: UpdatePhase, frame: FrameInfo): void;
  setQuality(next: QualityProfile): void;
  /** Test hook: switches a system's root and effects off and on. Throws for an unknown id. */
  setEnabled(id: string, enabled: boolean): void;
  status(): Readonly<Record<string, SystemStatus>>;
  /** Rolling median (ms) of each system's `update`; measured only with test hooks, else empty. */
  cpuMs(): Readonly<Record<string, number>>;
  /** Reverse list order. */
  dispose(): void;
}

export type WorldDeps = Omit<SystemContext, "root" | "signal" | "report" | "quality" | "ground"> & {
  /** The holder is shared with the bootstrap; `setQuality` replaces `current`. */
  readonly quality: { current: QualityProfile };
  readonly ground: LockableGround;
  readonly testHooks: boolean;
};

export const DEFAULT_INIT_TIMEOUT_MS = 20_000;
export const DEFAULT_BACKGROUND_INIT_TIMEOUT_MS = 60_000;
/** Samples kept for the rolling median of a system's update time. */
const CPU_SAMPLES = 60;

type Entry = {
  readonly system: WorldSystem;
  readonly root: Group;
  readonly abort: AbortController;
  readonly samples: number[];
  status: SystemStatus;
  /** Status to return to when a disabled system is enabled again. */
  beforeDisabled: SystemStatus | null;
  /** A problem a system reported while it was still initialising. */
  reported: SystemStatus | null;
  started: boolean;
  initDone: boolean;
  enabled: boolean;
  cancelInit: () => void;
};

const describeError = (error: unknown): string =>
  error instanceof Error ? error.message : String(error);

function median(values: readonly number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  if (sorted.length === 0) return 0;
  return sorted.length % 2 === 1
    ? (sorted[middle] as number)
    : ((sorted[middle - 1] as number) + (sorted[middle] as number)) / 2;
}

export function createWorld(systems: readonly WorldSystem[], deps: WorldDeps): World {
  const ids = new Set<string>();
  for (const system of systems) {
    if (ids.has(system.id)) {
      throw new Error(`Two world systems share the id "${system.id}". Ids must be unique.`);
    }
    ids.add(system.id);
  }
  const { testHooks, ...shared } = deps;

  const entries: Entry[] = systems.map((system) => {
    const root = new Group();
    root.name = `system:${system.id}`;
    deps.scene.add(root);
    return {
      system,
      root,
      abort: new AbortController(),
      samples: [],
      status: { state: "pending" },
      beforeDisabled: null,
      reported: null,
      started: false,
      initDone: false,
      enabled: true,
      cancelInit: () => undefined,
    };
  });

  const isLive = (entry: Entry): boolean =>
    entry.status.state === "ready" || entry.status.state === "degraded";

  /** Applies a status; a disabled system keeps showing `disabled` and remembers the real one. */
  const setStatus = (entry: Entry, status: SystemStatus): void => {
    if (entry.enabled || status.state === "failed") entry.status = status;
    else entry.beforeDisabled = status;
  };

  const fail = (entry: Entry, message: string): void => {
    if (entry.status.state === "failed" || entry.beforeDisabled?.state === "failed") return;
    entry.status = { state: "failed", message };
    entry.beforeDisabled = null;
    entry.root.visible = false;
    entry.abort.abort(new Error(message));
    console.error(`[world:${entry.system.id}] ${message}`);
  };

  /** Runs one call into a system; a throw marks the system failed instead of escaping. */
  const guarded = <T>(entry: Entry, what: string, call: () => T): T | undefined => {
    try {
      return call();
    } catch (error) {
      fail(entry, `${what} failed: ${describeError(error)}`);
      return undefined;
    }
  };

  const contextFor = (entry: Entry): SystemContext => ({
    ...shared,
    root: entry.root,
    signal: entry.abort.signal,
    report: (problem) => {
      if (entry.status.state === "failed") return;
      const status: SystemStatus = { state: problem.state, message: problem.message };
      if (problem.state === "failed") {
        entry.status = status;
        entry.root.visible = false;
        return;
      }
      if (entry.initDone) setStatus(entry, status);
      else entry.reported = status;
    },
  });

  const startInit = (entry: Entry): Promise<void> => {
    entry.started = true;
    entry.status = { state: "loading" };
    const { system } = entry;
    const timeoutMs =
      system.initTimeoutMs ??
      (system.load === "background" ? DEFAULT_BACKGROUND_INIT_TIMEOUT_MS : DEFAULT_INIT_TIMEOUT_MS);
    return new Promise<void>((resolve) => {
      let settled = false;
      const finish = (apply: () => void): void => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        entry.initDone = true;
        apply();
        resolve();
      };
      const timer = setTimeout(
        () => finish(() => fail(entry, `init timed out after ${timeoutMs} ms`)),
        timeoutMs,
      );
      entry.cancelInit = () => finish(() => undefined);
      let pending: Promise<InitOutcome>;
      try {
        pending = system.init(contextFor(entry));
      } catch (error) {
        pending = Promise.reject(error);
      }
      pending.then(
        (outcome) =>
          finish(() => {
            if (entry.status.state === "failed") return;
            if (outcome.status === "missing") {
              setStatus(entry, { state: "missing", message: outcome.message });
            } else {
              setStatus(entry, entry.reported ?? { state: "ready" });
            }
          }),
        (error: unknown) => finish(() => fail(entry, `init failed: ${describeError(error)}`)),
      );
    });
  };

  const requireEntry = (id: string): Entry => {
    const entry = entries.find((candidate) => candidate.system.id === id);
    if (entry === undefined) throw new Error(`No world system has the id "${id}".`);
    return entry;
  };

  const settledOf = (entry: Entry): boolean => {
    if (!entry.initDone) return false;
    if (entry.status.state === "failed" || entry.status.state === "missing") return true;
    const settled = entry.system.isSettled;
    if (settled === undefined) return true;
    return guarded(entry, "isSettled", () => settled.call(entry.system)) ?? true;
  };

  return {
    init(priority) {
      const started = entries
        .filter((entry) => entry.system.load === priority && !entry.started)
        .map(startInit);
      return Promise.all(started).then(() => undefined);
    },
    isSettled() {
      return entries.filter((entry) => entry.system.load !== "background").every(settledOf);
    },
    startWalk() {
      deps.ground.lock();
      for (const entry of entries) {
        if (isLive(entry)) guarded(entry, "onWalkStart", () => entry.system.onWalkStart?.());
      }
      for (const entry of entries) {
        if (entry.system.load === "background" && !entry.started) void startInit(entry);
      }
    },
    update(phase, frame) {
      for (const entry of entries) {
        if (entry.system.phase !== phase || !isLive(entry)) continue;
        if (!testHooks) {
          guarded(entry, "update", () => entry.system.update(frame));
          continue;
        }
        const began = performance.now();
        guarded(entry, "update", () => entry.system.update(frame));
        entry.samples.push(performance.now() - began);
        if (entry.samples.length > CPU_SAMPLES) entry.samples.shift();
      }
    },
    setQuality(next) {
      const previous = deps.quality.current;
      deps.quality.current = next;
      for (const entry of entries) {
        if (isLive(entry)) {
          guarded(entry, "onQualityChange", () => entry.system.onQualityChange?.(next, previous));
        }
      }
    },
    setEnabled(id, enabled) {
      const entry = requireEntry(id);
      if (entry.enabled === enabled) return;
      entry.enabled = enabled;
      entry.root.visible = enabled && entry.status.state !== "failed";
      if (enabled) {
        if (entry.status.state === "disabled" && entry.beforeDisabled !== null) {
          entry.status = entry.beforeDisabled;
        }
        entry.beforeDisabled = null;
      } else if (entry.status.state !== "failed") {
        entry.beforeDisabled = entry.status;
        entry.status = { state: "disabled" };
      }
      guarded(entry, "setEnabled", () => entry.system.setEnabled?.(enabled));
    },
    status() {
      return Object.fromEntries(entries.map((entry) => [entry.system.id, entry.status]));
    },
    cpuMs() {
      return Object.fromEntries(
        entries
          .filter((entry) => entry.samples.length > 0)
          .map((entry) => [entry.system.id, median(entry.samples)]),
      );
    },
    dispose() {
      for (const entry of [...entries].reverse()) {
        entry.cancelInit();
        entry.abort.abort(new Error("The world was disposed."));
        guarded(entry, "dispose", () => entry.system.dispose());
        deps.scene.remove(entry.root);
      }
    },
  };
}
