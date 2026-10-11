import { PerspectiveCamera, Scene, type WebGLRenderer } from "three";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createAtmosphere } from "../world/atmosphere";
import { dayAtmosphere } from "../world/atmosphere/defaults";
import {
  createGroundRegistry,
  createWorld,
  type InitOutcome,
  type World,
  type WorldSystem,
} from "../world/systems";
import { createWalkGate, runBoot, WALK_GATE_POLL_MS } from "./boot";
import { profileFor } from "./quality";

function system(id: string, load: WorldSystem["load"], init: () => Promise<InitOutcome>) {
  return {
    id,
    phase: "postPlayer",
    load,
    init,
    update: () => undefined,
    dispose: () => undefined,
  } satisfies WorldSystem;
}

function worldOf(systems: readonly WorldSystem[]): World {
  return createWorld(systems, {
    scene: new Scene(),
    camera: new PerspectiveCamera(),
    renderer: {} as WebGLRenderer,
    assets: { gltf: () => ({}) as never, url: (path) => path },
    atmosphere: createAtmosphere(dayAtmosphere({ x: 0, z: 0 })),
    quality: { current: profileFor("medium", { coarsePointer: false, softwareRenderer: false }) },
    ground: createGroundRegistry(),
    pois: { list: () => [], onDiscover: () => () => undefined },
    route: new Promise(() => undefined),
    collision: new Promise(() => undefined),
    params: new URLSearchParams(),
    testHooks: false,
  });
}

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("runBoot", () => {
  it("starts the preview once the critical systems are in, without waiting for a slow beforeWalk one", async () => {
    const order: string[] = [];
    let releaseStaircases: () => void = () => undefined;
    const world = worldOf([
      system("critical", "critical", async () => ({ status: "ready" })),
      system(
        "staircases",
        "beforeWalk",
        () =>
          new Promise<InitOutcome>((resolve) => {
            releaseStaircases = () => resolve({ status: "ready" });
          }),
      ),
    ]);
    const critical = world.init("critical");
    const beforeWalk = world.init("beforeWalk");
    const gate = createWalkGate(() => world.isSettled(), { loopRunning: () => true });

    const booted = runBoot({
      critical,
      beforeWalk,
      walkGate: gate.opened,
      startPreview: () => order.push("preview"),
    }).then(() => order.push("walk"));

    await critical;
    await Promise.resolve();
    expect(order).toEqual(["preview"]);
    expect(world.status().staircases).toEqual({ state: "loading" });

    releaseStaircases();
    await beforeWalk;
    gate.poll();
    await booted;
    expect(order).toEqual(["preview", "walk"]);
    gate.dispose();
  });

  it("does not open the walk before the walk gate does, even when beforeWalk is done", async () => {
    const order: string[] = [];
    let open: () => void = () => undefined;
    const walkGate = new Promise<void>((resolve) => {
      open = resolve;
    });
    const booted = runBoot({
      critical: Promise.resolve(),
      beforeWalk: Promise.resolve(),
      walkGate,
      startPreview: () => undefined,
    }).then(() => order.push("walk"));
    await Promise.resolve();
    await Promise.resolve();
    expect(order).toEqual([]);
    open();
    await booted;
    expect(order).toEqual(["walk"]);
  });
});

describe("createWalkGate", () => {
  it("opens on the first poll that finds the world settled", async () => {
    let settled = false;
    const gate = createWalkGate(() => settled, { loopRunning: () => true });
    gate.poll();
    let opened = false;
    void gate.opened.then(() => {
      opened = true;
    });
    await Promise.resolve();
    expect(opened).toBe(false);
    settled = true;
    gate.poll();
    await gate.opened;
    gate.dispose();
  });

  it("polls by itself while the loop is not running, so a never-started loop cannot block the walk", async () => {
    vi.useFakeTimers();
    let settled = false;
    const gate = createWalkGate(() => settled, { loopRunning: () => false });
    let opened = false;
    void gate.opened.then(() => {
      opened = true;
    });
    await vi.advanceTimersByTimeAsync(WALK_GATE_POLL_MS * 3);
    expect(opened).toBe(false);
    settled = true;
    await vi.advanceTimersByTimeAsync(WALK_GATE_POLL_MS);
    expect(opened).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("leaves the polling to the frame loop while it runs", async () => {
    vi.useFakeTimers();
    const isSettled = vi.fn(() => true);
    const gate = createWalkGate(isSettled, { loopRunning: () => true });
    await vi.advanceTimersByTimeAsync(WALK_GATE_POLL_MS * 5);
    expect(isSettled).not.toHaveBeenCalled();
    gate.dispose();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("opens through a world whose beforeWalk system never settles, once its deadline passes", async () => {
    vi.useFakeTimers();
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const stuck = {
      ...system("stuck", "beforeWalk", async () => ({ status: "ready" })),
      isSettled: () => false,
      settleTimeoutMs: 2_000,
    } satisfies WorldSystem;
    const world = worldOf([stuck]);
    await world.init("beforeWalk");
    const gate = createWalkGate(() => world.isSettled(), { loopRunning: () => false });
    let opened = false;
    void gate.opened.then(() => {
      opened = true;
    });
    await vi.advanceTimersByTimeAsync(1_500);
    expect(opened).toBe(false);
    await vi.advanceTimersByTimeAsync(1_000);
    expect(opened).toBe(true);
    expect(world.status().stuck?.state).toBe("degraded");
  });
});
