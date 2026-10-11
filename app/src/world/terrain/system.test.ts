import { Group } from "three";
import { describe, expect, it, vi } from "vitest";
import { profileFor } from "../../core/quality";
import { makeWorldDeps } from "../fixtures";
import { createWorld, type FrameInfo } from "../systems";
import { makeTile } from "./fixtures";
import { TERRAIN_STALL_LIMIT_MS } from "./gate";
import type { TerrainManifest } from "./manifest";
import type { TerrainStats, TerrainStreamer } from "./streamer";
import { createTerrainSystem, type TerrainSystemDeps } from "./system";

const MANIFEST: TerrainManifest = {
  version: 1,
  far: { url: "far.glb", bytes: 1, triangles: 1 },
  near: { tileSize: 256, tiles: [makeTile(0, 0)] },
} as unknown as TerrainManifest;

function stats(overrides: Partial<TerrainStats> = {}): TerrainStats {
  return {
    resident: {},
    displayed: {},
    farLoaded: false,
    coverage: { required: 4, loaded: 0 },
    visible: false,
    gaveUp: false,
    bytesLoaded: 0,
    pending: 0,
    inFlight: 0,
    failed: 0,
    lastError: null,
    quality: "low",
    detail: "procedural",
    ...overrides,
  };
}

function frame(n: number, realMs = 16): FrameInfo {
  return { frame: n, dt: 0.016, time: n * 0.016, realMs, drawingBufferHeight: 720, player: null };
}

function setup(manifest: Awaited<ReturnType<TerrainSystemDeps["loadManifest"]>>) {
  let current = stats();
  const streamer = {
    root: new Group(),
    update: vi.fn(),
    setDetailEnabled: vi.fn(),
    stats: vi.fn(() => current),
    dispose: vi.fn(),
  };
  const createStreamer = vi.fn(
    (_options: Record<string, unknown>) => streamer as unknown as TerrainStreamer,
  );
  const { system, handle } = createTerrainSystem({
    createStreamer: createStreamer as unknown as TerrainSystemDeps["createStreamer"],
    loadManifest: async () => manifest,
  });
  const { deps } = makeWorldDeps();
  const world = createWorld([system], deps);
  return {
    world,
    handle,
    streamer,
    createStreamer,
    deps,
    set: (next: TerrainStats) => {
      current = next;
    },
  };
}

describe("terrain system init", () => {
  it("is missing when the terrain has not been generated", async () => {
    const { world, handle } = setup({ status: "missing" });
    await world.init("critical");
    expect(world.status().terrain?.state).toBe("missing");
    expect(handle.available()).toBe(false);
    expect(world.isSettled()).toBe(true);
  });

  it("fails with the manifest's message when the file is invalid", async () => {
    const { world, handle } = setup({ status: "error", message: "bad manifest" });
    await world.init("critical");
    expect(world.status().terrain).toEqual({
      state: "failed",
      message: "init failed: bad manifest",
    });
    expect(handle.error()).toBe("bad manifest");
    expect(world.isSettled()).toBe(true);
  });

  it("starts the streamer on the critical path only, with the profile's options", async () => {
    const { world, handle, createStreamer } = setup({ status: "ready", manifest: MANIFEST });
    await world.init("critical");
    expect(world.status().terrain?.state).toBe("ready");
    expect(handle.available()).toBe(true);
    const options = createStreamer.mock.calls[0]?.[0] ?? {};
    const expected = profileFor("medium", { coarsePointer: false, softwareRenderer: false });
    expect(options.detailEnabled).toBe(false);
    expect(options.quality).toBe("high");
    expect(options.detailSet).toBe(expected.terrain.detail);
    expect(options.sseThreshold).toBe(expected.terrain.sseThresholdPx);
    expect(options.manifestUrl).toBe("/assets/generated/terrain/manifest.json");
  });
});

describe("terrain system walk gate", () => {
  it("updates the streamer every frame with the camera view", async () => {
    const { world, streamer } = setup({ status: "ready", manifest: MANIFEST });
    await world.init("critical");
    world.update("postPlayer", frame(1));
    world.update("postPlayer", frame(2));
    expect(streamer.update).toHaveBeenCalledTimes(2);
    expect(streamer.update.mock.calls[0]?.[0]).toMatchObject({ viewportHeight: 720 });
  });

  it("steps the gate on frames 1, 7, 13, ... and settles when the terrain is visible", async () => {
    const { world, handle, set } = setup({ status: "ready", manifest: MANIFEST });
    await world.init("critical");
    world.update("postPlayer", frame(1));
    expect(handle.takeGateStep()?.outcome).toBe("waiting");
    expect(world.isSettled()).toBe(false);
    set(stats({ visible: true, farLoaded: true }));
    for (let n = 2; n <= 6; n++) world.update("postPlayer", frame(n));
    expect(handle.takeGateStep()).toBeNull();
    world.update("postPlayer", frame(7));
    const step = handle.takeGateStep();
    expect(step?.outcome).toBe("visible");
    expect(step?.stats.visible).toBe(true);
    expect(world.isSettled()).toBe(true);
    expect(handle.takeGateStep()).toBeNull();
  });

  it("stops stepping once the terrain has been visible", async () => {
    const { world, handle, set, streamer } = setup({ status: "ready", manifest: MANIFEST });
    await world.init("critical");
    set(stats({ visible: true }));
    world.update("postPlayer", frame(1));
    handle.takeGateStep();
    streamer.stats.mockClear();
    for (let n = 2; n <= 20; n++) world.update("postPlayer", frame(n));
    expect(streamer.stats).not.toHaveBeenCalled();
    expect(handle.takeGateStep()).toBeNull();
  });

  it("gives up after the streamer does", async () => {
    const { world, handle, set } = setup({ status: "ready", manifest: MANIFEST });
    await world.init("critical");
    set(stats({ gaveUp: true, lastError: "net" }));
    world.update("postPlayer", frame(1));
    expect(handle.takeGateStep()?.outcome).toBe("failed");
    expect(world.isSettled()).toBe(true);
  });

  it("fails on a stall counted in real frame time, and keeps stepping after the failure", async () => {
    const { world, handle, set } = setup({ status: "ready", manifest: MANIFEST });
    await world.init("critical");
    set(stats({ bytesLoaded: 10 }));
    world.update("postPlayer", frame(1, 16));
    expect(handle.takeGateStep()?.outcome).toBe("waiting");
    // Six frames of 1 s each in between, then the check that crosses the stall limit.
    const perFrame = TERRAIN_STALL_LIMIT_MS / 6 + 1;
    for (let n = 2; n <= 6; n++) world.update("postPlayer", frame(n, perFrame));
    world.update("postPlayer", frame(7, perFrame));
    expect(handle.takeGateStep()?.outcome).toBe("failed");
    expect(world.isSettled()).toBe(true);

    set(stats({ visible: true }));
    for (let n = 8; n <= 13; n++) world.update("postPlayer", frame(n));
    expect(handle.takeGateStep()?.outcome).toBe("visible");
  });

  it("does not count frames with no real time (a hidden tab) towards the stall", async () => {
    const { world, handle } = setup({ status: "ready", manifest: MANIFEST });
    await world.init("critical");
    for (let n = 1; n <= 61; n++) world.update("postPlayer", frame(n, 0));
    expect(handle.takeGateStep()?.outcome).toBe("waiting");
  });

  it("stays settled after a failure even if progress makes the gate wait again", async () => {
    const { world, handle, set } = setup({ status: "ready", manifest: MANIFEST });
    await world.init("critical");
    set(stats({ gaveUp: true }));
    world.update("postPlayer", frame(1));
    handle.takeGateStep();
    set(stats({ bytesLoaded: 99 }));
    for (let n = 2; n <= 7; n++) world.update("postPlayer", frame(n));
    expect(handle.takeGateStep()?.outcome).toBe("waiting");
    expect(world.isSettled()).toBe(true);
  });
});

describe("terrain system life cycle", () => {
  it("releases the detail loads at the start of the walk", async () => {
    const { world, streamer } = setup({ status: "ready", manifest: MANIFEST });
    await world.init("critical");
    world.startWalk();
    expect(streamer.setDetailEnabled).toHaveBeenCalledWith(true);
  });

  it("disposes the streamer", async () => {
    const { world, streamer } = setup({ status: "ready", manifest: MANIFEST });
    await world.init("critical");
    world.dispose();
    expect(streamer.dispose).toHaveBeenCalledOnce();
  });
});
