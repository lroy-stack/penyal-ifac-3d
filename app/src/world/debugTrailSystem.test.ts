import { afterEach, describe, expect, it, vi } from "vitest";
import { createTrailDebugSystem } from "./debugTrailSystem";
import { makeWorldDeps } from "./fixtures";
import type { HeightField } from "./ground";
import { createWorld, type Route } from "./systems";
import type { Trail } from "./trail";

const TRAIL: Trail = {
  licence: "ODbL",
  attribution: "OSM",
  route: {
    segments: [
      {
        id: "a",
        points: [
          [0, 1, 0],
          [10, 2, 0],
        ],
      },
    ],
  },
  corridor: {
    polygon: [
      [-5, -5],
      [15, -5],
      [15, 5],
    ],
  },
  anchors: { start: { x: 0, y: 1, z: 0 } },
};
const FLAT: HeightField = { heightAt: () => 1 };

const context2d = {
  font: "",
  textBaseline: "",
  lineWidth: 0,
  strokeStyle: "",
  fillStyle: "",
  strokeText: () => undefined,
  fillText: () => undefined,
};

describe("trail debug system", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("is a background system, so it starts only after the walk starts", () => {
    expect(createTrailDebugSystem().load).toBe("background");
  });

  it("waits for the collision field, then draws the overlay under its root", async () => {
    let release: (field: HeightField) => void = () => undefined;
    const collision = new Promise<HeightField>((resolve) => {
      release = resolve;
    });
    const route = Promise.resolve({
      trail: TRAIL,
      corridor: { contains: () => true, clamp: () => ({ x: 0, z: 0 }) },
      start: TRAIL.anchors.start,
      startYaw: 0,
    } as unknown as Route);
    // The anchor labels are drawn on a canvas, which node does not have.
    vi.stubGlobal("document", {
      createElement: () => ({ width: 0, height: 0, getContext: () => context2d }),
    });
    const { deps } = makeWorldDeps({ route, collision });
    const world = createWorld([createTrailDebugSystem()], deps);
    world.startWalk();
    await Promise.resolve();
    const root = deps.scene.getObjectByName("system:debug-trail");
    expect(root?.children).toHaveLength(0);
    release(FLAT);
    await vi.waitFor(() => expect(world.status()["debug-trail"]?.state).toBe("ready"));
    expect(root?.children).toHaveLength(1);
    expect(world.status()["debug-trail"]?.state).toBe("ready");
  });
});
