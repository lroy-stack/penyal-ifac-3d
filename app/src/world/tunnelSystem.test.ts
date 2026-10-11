import { Object3D } from "three";
import { describe, expect, it, vi } from "vitest";
import type { PlayerState } from "../player";
import { makeWorldDeps } from "./fixtures";
import { createWorld, type FrameInfo } from "./systems";
import type { Tunnel, TunnelResult } from "./tunnel";
import { createTunnelSystem, type TunnelMeshResult, type TunnelSystemDeps } from "./tunnelSystem";

const TUNNEL: Tunnel = {
  version: 1,
  licence: "ODbL",
  attribution: "OSM",
  status: "approximate",
  axis: [
    [0, 10, 0],
    [20, 10, 0],
  ],
  width: 3,
  height: 3,
  sectionBasis: "test",
  portals: {
    west: { x: 0, y: 10, z: 0 },
    east: { x: 20, y: 10, z: 0 },
  },
  sources: { axis: "osm", portalHeights: "dem" },
  mesh: "tunnel.glb",
};

function player(x: number, y: number, z: number): PlayerState {
  return { position: { x, y, z } } as unknown as PlayerState;
}

function frame(who: PlayerState | null): FrameInfo {
  return { frame: 1, dt: 0.016, time: 0, realMs: 16, drawingBufferHeight: 720, player: who };
}

function setup(file: TunnelResult, view: TunnelSystemDeps["loadView"]) {
  const { system, handle } = createTunnelSystem({ loadTunnel: async () => file, loadView: view });
  const made = makeWorldDeps();
  const world = createWorld([system], made.deps);
  return { world, handle, ground: made.deps.ground, scene: made.deps.scene };
}

const never: TunnelSystemDeps["loadView"] = () => new Promise(() => undefined);

describe("tunnel system init", () => {
  it("is missing when tunnel.json does not exist", async () => {
    const { world, handle, ground } = setup({ status: "missing" }, never);
    await world.init("critical");
    expect(world.status().tunnel?.state).toBe("missing");
    expect(handle.available()).toBe(false);
    expect(ground.surfaces).toHaveLength(0);
  });

  it("fails with the file's message when tunnel.json is invalid", async () => {
    const { world, handle } = setup({ status: "error", message: "bad json" }, never);
    await world.init("critical");
    expect(world.status().tunnel?.state).toBe("failed");
    expect(handle.error()).toBe("bad json");
  });

  it("registers the floor and the enclosure with the ground before the walk", async () => {
    const { world, handle, ground } = setup({ status: "ready", tunnel: TUNNEL }, never);
    await world.init("critical");
    expect(handle.available()).toBe(true);
    expect(ground.surfaces).toHaveLength(1);
    expect(ground.enclosures).toEqual(ground.surfaces);
    expect(ground.startFloor(10, 0)).toBe(10);
    expect(ground.startFloor(10, 50)).toBeNull();
  });

  it("is ready before the mesh arrives, and puts the mesh under its root when it does", async () => {
    let finish: (loaded: { object: Object3D; dispose: () => void }) => void = () => undefined;
    const { world, handle, scene } = setup(
      { status: "ready", tunnel: TUNNEL },
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const results: TunnelMeshResult[] = [];
    handle.onMesh = (result) => results.push(result);
    await world.init("critical");
    expect(world.status().tunnel?.state).toBe("ready");
    expect(results).toEqual([]);
    const mesh = new Object3D();
    finish({ object: mesh, dispose: () => undefined });
    await Promise.resolve();
    await Promise.resolve();
    expect(results).toEqual([{ ok: true }]);
    expect(mesh.parent).toBe(scene.getObjectByName("system:tunnel"));
  });

  it("reports a mesh failure as degraded without failing the walk", async () => {
    const { world, handle } = setup({ status: "ready", tunnel: TUNNEL }, async () => {
      throw new Error("404");
    });
    const results: TunnelMeshResult[] = [];
    handle.onMesh = (result) => results.push(result);
    await world.init("critical");
    await Promise.resolve();
    await Promise.resolve();
    expect(results).toEqual([
      { ok: false, message: "The tunnel interior could not be loaded. 404" },
    ]);
    expect(world.status().tunnel).toEqual({
      state: "degraded",
      message: "The tunnel interior could not be loaded. 404",
    });
    expect(world.isSettled()).toBe(true);
  });

  it("disposes a mesh that arrives after the world was disposed", async () => {
    let finish: (loaded: { object: Object3D; dispose: () => void }) => void = () => undefined;
    const { world } = setup(
      { status: "ready", tunnel: TUNNEL },
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    await world.init("critical");
    world.dispose();
    const dispose = vi.fn();
    finish({ object: new Object3D(), dispose });
    await Promise.resolve();
    await Promise.resolve();
    expect(dispose).toHaveBeenCalledOnce();
  });
});

describe("tunnel system lamp", () => {
  async function lampAt(who: PlayerState | null) {
    const { world, scene } = setup({ status: "ready", tunnel: TUNNEL }, never);
    await world.init("critical");
    world.update("postPlayer", frame(who));
    const lamp = scene.getObjectByName("system:tunnel")?.children[0] as unknown as {
      intensity: number;
      position: { toArray(): number[] };
    };
    return lamp;
  }

  it("is off while previewing, before the player exists", async () => {
    const lamp = await lampAt(null);
    expect(lamp.intensity).toBe(0);
  });

  it("is on inside the tunnel, one metre and a bit above the feet", async () => {
    const lamp = await lampAt(player(10, 10, 0));
    expect(lamp.intensity).toBe(7);
    expect(lamp.position.toArray()).toEqual([10, 11.2, 0]);
  });

  it("is off outside it", async () => {
    const lamp = await lampAt(player(10, 10, 30));
    expect(lamp.intensity).toBe(0);
  });
});
