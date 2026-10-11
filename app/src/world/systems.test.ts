import { PerspectiveCamera, Scene, type WebGLRenderer } from "three";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { JSON_TIMEOUT_MS } from "../core/http";
import { profileFor, type QualityProfile } from "../core/quality";
import { createAtmosphere } from "./atmosphere";
import type { GroundSurface } from "./ground";
import {
  createGroundRegistry,
  createWorld,
  DEFAULT_INIT_TIMEOUT_MS,
  DEFAULT_SETTLE_TIMEOUT_MS,
  type FrameInfo,
  type InitOutcome,
  type LoadPriority,
  type SystemContext,
  type UpdatePhase,
  type World,
  type WorldDeps,
  type WorldSystem,
} from "./systems";
import { TERRAIN_STALL_LIMIT_MS } from "./terrain/gate";

const DEVICE = { coarsePointer: false, softwareRenderer: false } as const;
const FRAME: FrameInfo = {
  frame: 1,
  dt: 0.016,
  time: 1,
  realMs: 16,
  drawingBufferHeight: 720,
  player: null,
};

type Fake = WorldSystem & { readonly log: string[]; ctx: SystemContext | null };

type FakeOptions = {
  readonly phase?: UpdatePhase;
  readonly load?: LoadPriority;
  readonly init?: (ctx: SystemContext) => Promise<InitOutcome>;
  readonly update?: (frame: FrameInfo) => void;
  readonly settled?: () => boolean;
  readonly initTimeoutMs?: number;
  readonly settleTimeoutMs?: number;
  readonly dispose?: () => void;
};

function fake(id: string, shared: string[], options: FakeOptions = {}): Fake {
  const log: string[] = [];
  const system: Fake = {
    id,
    phase: options.phase ?? "postPlayer",
    load: options.load ?? "critical",
    ...(options.initTimeoutMs === undefined ? {} : { initTimeoutMs: options.initTimeoutMs }),
    ...(options.settleTimeoutMs === undefined ? {} : { settleTimeoutMs: options.settleTimeoutMs }),
    log,
    ctx: null,
    init: async (ctx) => {
      system.ctx = ctx;
      shared.push(`init:${id}`);
      return options.init === undefined ? { status: "ready" } : options.init(ctx);
    },
    update: (frame) => {
      shared.push(`update:${id}`);
      options.update?.(frame);
    },
    onWalkStart: () => shared.push(`walk:${id}`),
    onQualityChange: (next, previous) => shared.push(`quality:${id}:${previous.tier}>${next.tier}`),
    setEnabled: (enabled) => shared.push(`enabled:${id}:${enabled}`),
    dispose: () => {
      shared.push(`dispose:${id}`);
      options.dispose?.();
    },
  };
  if (options.settled !== undefined) system.isSettled = options.settled;
  return system;
}

function setup(systems: readonly WorldSystem[], testHooks = false) {
  const scene = new Scene();
  const profile = profileFor("medium", DEVICE);
  const ground = createGroundRegistry();
  const deps: WorldDeps = {
    scene,
    camera: new PerspectiveCamera(),
    renderer: {} as WebGLRenderer,
    assets: { gltf: () => ({}) as never, url: (path) => `/${path}` },
    atmosphere: createAtmosphere({
      preset: "day",
      sun: { direction: { x: 0, y: 1, z: 0 }, color: { r: 1, g: 1, b: 1 }, intensity: 1 },
      ambient: { sky: { r: 1, g: 1, b: 1 }, ground: { r: 0, g: 0, b: 0 }, intensity: 1 },
      horizon: { r: 1, g: 1, b: 1 },
      zenith: { r: 0, g: 0, b: 1 },
      fog: { color: { r: 1, g: 1, b: 1 }, near: 1, far: 10, sunScatter: 0 },
      toneMapping: "aces",
      exposure: 1,
    }),
    quality: { current: profile },
    ground,
    pois: { list: () => [], onDiscover: () => () => undefined },
    route: new Promise(() => undefined),
    collision: new Promise(() => undefined),
    params: new URLSearchParams(),
    testHooks,
  };
  const world: World = createWorld(systems, deps);
  return { world, scene, deps, ground };
}

let errors: ReturnType<typeof vi.spyOn>;
beforeEach(() => {
  errors = vi.spyOn(console, "error").mockImplementation(() => undefined);
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("composition", () => {
  it("rejects two systems with the same id", () => {
    const log: string[] = [];
    expect(() => setup([fake("a", log), fake("a", log)])).toThrow(/"a"/);
  });

  it("gives each system a root named system:<id> inside the scene", async () => {
    const log: string[] = [];
    const a = fake("sea", log);
    const { world, scene } = setup([a]);
    await world.init("critical");
    expect(a.ctx?.root.name).toBe("system:sea");
    expect(a.ctx?.root.parent).toBe(scene);
  });

  it("updates by phase, then in list order, whatever order the inits finished in", async () => {
    const log: string[] = [];
    let releaseFirst: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      releaseFirst = resolve;
    });
    const systems = [
      fake("a", log, {
        phase: "postPlayer",
        init: async () => {
          await held;
          return { status: "ready" };
        },
      }),
      fake("b", log, { phase: "preRender" }),
      fake("c", log, { phase: "prePlayer" }),
      fake("d", log, { phase: "postPlayer" }),
    ];
    const { world } = setup(systems);
    const initialised = world.init("critical");
    await Promise.resolve();
    releaseFirst();
    await initialised;
    log.length = 0;
    world.update("prePlayer", FRAME);
    world.update("postPlayer", FRAME);
    world.update("preRender", FRAME);
    expect(log).toEqual(["update:c", "update:a", "update:d", "update:b"]);
  });

  it("starts the inits of one priority in list order and none of the others", async () => {
    const log: string[] = [];
    const { world } = setup([
      fake("a", log, { load: "critical" }),
      fake("b", log, { load: "beforeWalk" }),
      fake("c", log, { load: "critical" }),
      fake("d", log, { load: "background" }),
    ]);
    await world.init("critical");
    expect(log).toEqual(["init:a", "init:c"]);
    await world.init("beforeWalk");
    expect(log).toEqual(["init:a", "init:c", "init:b"]);
  });

  it("does not update a system before its init has finished", async () => {
    const log: string[] = [];
    const { world } = setup([fake("a", log)]);
    world.update("postPlayer", FRAME);
    expect(log).toEqual([]);
    expect(world.status().a).toEqual({ state: "pending" });
  });
});

describe("status", () => {
  it("goes from loading to ready", async () => {
    const log: string[] = [];
    const { world } = setup([fake("a", log)]);
    const done = world.init("critical");
    expect(world.status().a).toEqual({ state: "loading" });
    await done;
    expect(world.status().a).toEqual({ state: "ready" });
  });

  it("records missing as a status, not an error", async () => {
    const log: string[] = [];
    const { world } = setup([
      fake("a", log, { init: async () => ({ status: "missing", message: "no file" }) }),
    ]);
    await world.init("critical");
    expect(world.status().a).toEqual({ state: "missing", message: "no file" });
    expect(errors).not.toHaveBeenCalled();
    world.update("postPlayer", FRAME);
    expect(log).not.toContain("update:a");
  });

  it("keeps a problem reported by the system", async () => {
    const log: string[] = [];
    const { world } = setup([
      fake("a", log, {
        init: async (ctx) => {
          ctx.report({ state: "degraded", message: "mesh missing" });
          return { status: "ready" };
        },
      }),
    ]);
    await world.init("critical");
    expect(world.status().a).toEqual({ state: "degraded", message: "mesh missing" });
    world.update("postPlayer", FRAME);
    expect(log).toContain("update:a");
  });

  it("lets a ready system degrade later, and fail by itself", async () => {
    const log: string[] = [];
    const a = fake("a", log);
    const { world } = setup([a]);
    await world.init("critical");
    a.ctx?.report({ state: "degraded", message: "slow" });
    expect(world.status().a).toEqual({ state: "degraded", message: "slow" });
    a.ctx?.report({ state: "failed", message: "gone" });
    expect(world.status().a).toEqual({ state: "failed", message: "gone" });
    expect(a.ctx?.root.visible).toBe(false);
    world.update("postPlayer", FRAME);
    expect(log).not.toContain("update:a");
  });
});

describe("reported problems", () => {
  it("treats a reported failure like any other: logged once, root hidden, signal aborted", async () => {
    const log: string[] = [];
    const a = fake("a", log);
    const { world } = setup([a]);
    await world.init("critical");
    a.ctx?.report({ state: "failed", message: "gone" });
    a.ctx?.report({ state: "failed", message: "gone again" });
    expect(world.status().a).toEqual({ state: "failed", message: "gone" });
    expect(errors).toHaveBeenCalledTimes(1);
    expect(errors).toHaveBeenCalledWith("[world:a] gone");
    expect(a.ctx?.signal.aborted).toBe(true);
    expect(a.ctx?.root.visible).toBe(false);
  });

  it("logs a reported degradation once as a warning, not as an error", async () => {
    const log: string[] = [];
    const warnings = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const a = fake("a", log);
    const { world } = setup([a]);
    await world.init("critical");
    a.ctx?.report({ state: "degraded", message: "slow" });
    a.ctx?.report({ state: "degraded", message: "slow" });
    expect(warnings).toHaveBeenCalledTimes(1);
    expect(warnings).toHaveBeenCalledWith("[world:a] slow");
    expect(errors).not.toHaveBeenCalled();
    expect(a.ctx?.signal.aborted).toBe(false);
  });

  it("logs a degradation reported during init", async () => {
    const warnings = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const { world } = setup([
      fake("a", [], {
        init: async (ctx) => {
          ctx.report({ state: "degraded", message: "mesh missing" });
          return { status: "ready" };
        },
      }),
    ]);
    await world.init("critical");
    expect(warnings).toHaveBeenCalledWith("[world:a] mesh missing");
  });
});

describe("settle deadline", () => {
  it("lets the gate proceed with a degraded status and one logged error when a system never settles", async () => {
    vi.useFakeTimers();
    const { world } = setup([
      fake("stuck", [], { load: "beforeWalk", settled: () => false, settleTimeoutMs: 1_000 }),
    ]);
    await world.init("beforeWalk");
    expect(world.isSettled()).toBe(false);
    await vi.advanceTimersByTimeAsync(999);
    expect(world.isSettled()).toBe(false);
    await vi.advanceTimersByTimeAsync(2);
    expect(world.isSettled()).toBe(true);
    expect(world.status().stuck).toEqual({
      state: "degraded",
      message: "did not settle within 1000 ms",
    });
    expect(errors).toHaveBeenCalledTimes(1);
    expect(errors).toHaveBeenCalledWith("[world:stuck] did not settle within 1000 ms");
  });

  it("does nothing for a system that settled in time", async () => {
    vi.useFakeTimers();
    let done = false;
    const { world } = setup([fake("a", [], { settled: () => done, settleTimeoutMs: 1_000 })]);
    await world.init("critical");
    done = true;
    await vi.advanceTimersByTimeAsync(5_000);
    expect(world.status().a).toEqual({ state: "ready" });
    expect(errors).not.toHaveBeenCalled();
  });

  it("does not run for systems without isSettled, nor after dispose", async () => {
    vi.useFakeTimers();
    const { world } = setup([
      fake("plain", [], { settleTimeoutMs: 100 }),
      fake("stuck", [], { settled: () => false, settleTimeoutMs: 100 }),
    ]);
    await world.init("critical");
    world.dispose();
    await vi.advanceTimersByTimeAsync(5_000);
    expect(errors).not.toHaveBeenCalled();
  });

  it("has a default longer than the terrain stall limit", () => {
    expect(DEFAULT_SETTLE_TIMEOUT_MS).toBeGreaterThan(TERRAIN_STALL_LIMIT_MS);
  });
});

describe("init timeout default", () => {
  it("is longer than the JSON timeout so the request fails first", () => {
    expect(DEFAULT_INIT_TIMEOUT_MS).toBe(JSON_TIMEOUT_MS + 5_000);
  });
});

describe("isolation", () => {
  it("marks a system whose init rejects as failed and keeps the others", async () => {
    const log: string[] = [];
    const bad = fake("bad", log, {
      init: async () => {
        throw new Error("boom");
      },
    });
    const { world } = setup([bad, fake("good", log)]);
    await world.init("critical");
    expect(world.status().bad).toEqual({ state: "failed", message: "init failed: boom" });
    expect(world.status().good).toEqual({ state: "ready" });
    expect(bad.ctx?.root.visible).toBe(false);
    expect(bad.ctx?.signal.aborted).toBe(true);
    expect(errors).toHaveBeenCalledOnce();
    expect(String(errors.mock.calls[0]?.[0])).toContain("[world:bad]");
  });

  it("catches an init that throws before returning a promise", async () => {
    const log: string[] = [];
    const bad = fake("bad", log);
    bad.init = () => {
      throw new Error("sync");
    };
    const { world } = setup([bad]);
    await world.init("critical");
    expect(world.status().bad).toEqual({ state: "failed", message: "init failed: sync" });
  });

  it("times an init out, aborts its signal and ignores a late result", async () => {
    vi.useFakeTimers();
    const log: string[] = [];
    let resolveInit: (outcome: InitOutcome) => void = () => undefined;
    const slow = fake("slow", log, {
      initTimeoutMs: 5_000,
      init: () =>
        new Promise<InitOutcome>((resolve) => {
          resolveInit = resolve;
        }),
    });
    const { world } = setup([slow]);
    const done = world.init("critical");
    await vi.advanceTimersByTimeAsync(5_000);
    await done;
    expect(world.status().slow).toEqual({
      state: "failed",
      message: "init timed out after 5000 ms",
    });
    expect(slow.ctx?.signal.aborted).toBe(true);
    resolveInit({ status: "ready" });
    await Promise.resolve();
    expect(world.status().slow?.state).toBe("failed");
  });

  it("uses the JSON timeout plus 5 s for critical and 60 s for background inits by default", async () => {
    vi.useFakeTimers();
    const log: string[] = [];
    const never = (): Promise<InitOutcome> => new Promise(() => undefined);
    const { world } = setup([
      fake("critical", log, { init: never }),
      fake("background", log, { load: "background", init: never }),
    ]);
    const critical = world.init("critical");
    await vi.advanceTimersByTimeAsync(DEFAULT_INIT_TIMEOUT_MS - 1);
    expect(world.status().critical?.state).toBe("loading");
    await vi.advanceTimersByTimeAsync(1);
    await critical;
    expect(world.status().critical?.state).toBe("failed");
    world.startWalk();
    await vi.advanceTimersByTimeAsync(59_999);
    expect(world.status().background?.state).toBe("loading");
    await vi.advanceTimersByTimeAsync(1);
    expect(world.status().background?.state).toBe("failed");
  });

  it("hides a system whose update throws, logs once and skips it from then on", async () => {
    const log: string[] = [];
    const bad = fake("bad", log, {
      update: () => {
        throw new Error("draw");
      },
    });
    const { world } = setup([bad, fake("good", log)]);
    await world.init("critical");
    world.update("postPlayer", FRAME);
    world.update("postPlayer", FRAME);
    expect(log.filter((entry) => entry === "update:bad")).toHaveLength(1);
    expect(log.filter((entry) => entry === "update:good")).toHaveLength(2);
    expect(world.status().bad).toEqual({ state: "failed", message: "update failed: draw" });
    expect(bad.ctx?.root.visible).toBe(false);
    expect(errors).toHaveBeenCalledOnce();
  });

  it("isolates onQualityChange, onWalkStart, isSettled and dispose", async () => {
    const log: string[] = [];
    const thrower = (name: string) => () => {
      throw new Error(name);
    };
    const a = fake("a", log, { settled: thrower("settled"), dispose: thrower("dispose") });
    a.onWalkStart = thrower("walk");
    a.onQualityChange = thrower("quality");
    const { world } = setup([a, fake("b", log)]);
    await world.init("critical");
    expect(world.isSettled()).toBe(true);
    expect(world.status().a).toEqual({ state: "failed", message: "isSettled failed: settled" });

    const b = fake("c", log);
    b.onQualityChange = thrower("quality");
    b.onWalkStart = thrower("walk");
    b.dispose = thrower("dispose");
    const second = setup([b, fake("d", log)]);
    await second.world.init("critical");
    second.world.setQuality(profileFor("low", DEVICE));
    expect(second.world.status().c).toEqual({
      state: "failed",
      message: "onQualityChange failed: quality",
    });
    expect(log).toContain("quality:d:medium>low");
    expect(() => second.world.dispose()).not.toThrow();
    expect(log).toContain("dispose:d");
  });
});

describe("walk gate", () => {
  it("is settled when every critical and beforeWalk init has finished", async () => {
    const log: string[] = [];
    const { world } = setup([
      fake("a", log, { load: "critical" }),
      fake("b", log, { load: "beforeWalk" }),
      fake("c", log, { load: "background" }),
    ]);
    expect(world.isSettled()).toBe(false);
    await world.init("critical");
    expect(world.isSettled()).toBe(false);
    await world.init("beforeWalk");
    expect(world.isSettled()).toBe(true);
  });

  it("waits for isSettled() of a system and polls it live", async () => {
    const log: string[] = [];
    let visible = false;
    const { world } = setup([fake("terrain", log, { settled: () => visible })]);
    await world.init("critical");
    expect(world.isSettled()).toBe(false);
    visible = true;
    expect(world.isSettled()).toBe(true);
  });

  it("counts missing and failed systems as settled", async () => {
    const log: string[] = [];
    const settledNever = (): boolean => false;
    const { world } = setup([
      fake("missing", log, {
        settled: settledNever,
        init: async () => ({ status: "missing", message: "none" }),
      }),
      fake("failed", log, {
        settled: settledNever,
        init: async () => {
          throw new Error("x");
        },
      }),
    ]);
    await world.init("critical");
    expect(world.isSettled()).toBe(true);
  });

  it("never fails to init: a rejected system does not reject world.init", async () => {
    const log: string[] = [];
    const { world } = setup([
      fake("a", log, {
        init: async () => {
          throw new Error("x");
        },
      }),
    ]);
    await expect(world.init("critical")).resolves.toBeUndefined();
  });
});

describe("walk start", () => {
  it("calls onWalkStart on live systems and starts the background inits in list order", async () => {
    const log: string[] = [];
    const { world } = setup([
      fake("a", log, { load: "background" }),
      fake("b", log),
      fake("c", log, { load: "background" }),
      fake("d", log, { init: async () => ({ status: "missing", message: "none" }) }),
    ]);
    await world.init("critical");
    log.length = 0;
    world.startWalk();
    expect(log).toEqual(["walk:b", "init:a", "init:c"]);
  });

  it("does not start a background init twice", async () => {
    const log: string[] = [];
    const { world } = setup([fake("a", log, { load: "background" })]);
    world.startWalk();
    world.startWalk();
    await world.init("background");
    expect(log.filter((entry) => entry === "init:a")).toHaveLength(1);
  });
});

describe("ground registry", () => {
  const surface = (floor: number | null): GroundSurface => ({
    surfaceBelow: () => null,
    floorAt: () => floor,
  });

  it("accepts surfaces and enclosures in an init, by reference", async () => {
    const log: string[] = [];
    const tunnel = surface(3);
    const enclosure = { contains: () => true };
    const { world, ground } = setup([
      fake("tunnel", log, {
        init: async (ctx) => {
          ctx.ground.addSurface(tunnel);
          ctx.ground.addEnclosure(enclosure);
          return { status: "ready" };
        },
      }),
    ]);
    const surfaces = ground.surfaces;
    await world.init("critical");
    expect(surfaces).toBe(ground.surfaces);
    expect(surfaces).toEqual([tunnel]);
    expect(ground.enclosures).toEqual([enclosure]);
  });

  it("throws on add after the walk has started", async () => {
    const log: string[] = [];
    const late = fake("late", log, { load: "background" });
    const { world, ground } = setup([late]);
    world.startWalk();
    expect(() => ground.addSurface(surface(1))).toThrow(/walk has started/);
    expect(() => ground.addEnclosure({ contains: () => true })).toThrow(/walk has started/);
  });

  it("reports the highest floor under the start, ignoring surfaces without one", () => {
    const ground = createGroundRegistry();
    expect(ground.startFloor(0, 0)).toBeNull();
    ground.addSurface({ surfaceBelow: () => null });
    ground.addSurface(surface(null));
    ground.addSurface(surface(4));
    ground.addSurface(surface(7));
    ground.addSurface(surface(5));
    expect(ground.startFloor(0, 0)).toBe(7);
  });
});

describe("quality", () => {
  it("passes next and previous to the systems in list order and updates the holder", async () => {
    const log: string[] = [];
    const { world, deps } = setup([fake("a", log), fake("b", log)]);
    await world.init("critical");
    const low: QualityProfile = profileFor("low", DEVICE);
    world.setQuality(low);
    expect(log.slice(-2)).toEqual(["quality:a:medium>low", "quality:b:medium>low"]);
    expect(deps.quality.current).toBe(low);
  });
});

describe("setEnabled", () => {
  it("hides the root, calls the hook, skips updates and restores everything", async () => {
    const log: string[] = [];
    const a = fake("a", log);
    const { world } = setup([a]);
    await world.init("critical");
    world.setEnabled("a", false);
    expect(a.ctx?.root.visible).toBe(false);
    expect(world.status().a).toEqual({ state: "disabled" });
    expect(log).toContain("enabled:a:false");
    log.length = 0;
    world.update("postPlayer", FRAME);
    expect(log).toEqual([]);
    world.setEnabled("a", true);
    expect(a.ctx?.root.visible).toBe(true);
    expect(world.status().a).toEqual({ state: "ready" });
    world.update("postPlayer", FRAME);
    expect(log).toEqual(["enabled:a:true", "update:a"]);
  });

  it("keeps a degraded status across a disable and enable", async () => {
    const log: string[] = [];
    const a = fake("a", log);
    const { world } = setup([a]);
    await world.init("critical");
    a.ctx?.report({ state: "degraded", message: "slow" });
    world.setEnabled("a", false);
    world.setEnabled("a", true);
    expect(world.status().a).toEqual({ state: "degraded", message: "slow" });
  });

  it("throws for an unknown id", () => {
    const { world } = setup([]);
    expect(() => world.setEnabled("ghost", false)).toThrow(/"ghost"/);
  });
});

describe("cpuMs", () => {
  it("is measured only with test hooks and is the median of the updates", async () => {
    const log: string[] = [];
    const off = setup([fake("a", log)], false);
    await off.world.init("critical");
    off.world.update("postPlayer", FRAME);
    expect(off.world.cpuMs()).toEqual({});

    const on = setup([fake("a", log)], true);
    await on.world.init("critical");
    on.world.update("postPlayer", FRAME);
    on.world.update("postPlayer", FRAME);
    on.world.update("postPlayer", FRAME);
    expect(Object.keys(on.world.cpuMs())).toEqual(["a"]);
    expect(on.world.cpuMs().a).toBeGreaterThanOrEqual(0);
  });
});

describe("dispose", () => {
  it("disposes in reverse list order, aborts signals and removes the roots", async () => {
    const log: string[] = [];
    const a = fake("a", log);
    const b = fake("b", log);
    const { world, scene } = setup([a, b]);
    await world.init("critical");
    log.length = 0;
    world.dispose();
    expect(log).toEqual(["dispose:b", "dispose:a"]);
    expect(a.ctx?.signal.aborted).toBe(true);
    expect(scene.children).toHaveLength(0);
  });

  it("ends an init that is still pending", async () => {
    const log: string[] = [];
    const { world } = setup([fake("a", log, { init: () => new Promise(() => undefined) })]);
    const pending = world.init("critical");
    world.dispose();
    await expect(pending).resolves.toBeUndefined();
  });
});
