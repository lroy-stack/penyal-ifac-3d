import { Object3D } from "three";
import { describe, expect, it } from "vitest";
import { makeWorldDeps } from "../fixtures";
import { createWorld } from "../systems";
import type { StructuresResult } from "./structures";
import { createStructuresSystem } from "./system";

const FILE: StructuresResult = {
  status: "ready",
  structures: {
    version: 1,
    licence: "ODbL",
    attribution: "OSM",
    glb: "structures.glb",
    constants: { status: "provisional" },
    staircases: [
      {
        id: "a",
        name: "A",
        stepCount: 1,
        collision: {
          kind: "treads",
          treads: [
            {
              top: 3,
              quad: [
                [0, 0],
                [1, 0],
                [1, 1],
                [0, 1],
              ],
            },
          ],
        },
      },
    ],
  },
};

type View = { object: Object3D; dispose: () => void };
const never = (): Promise<View> => new Promise(() => undefined);

function setup(file: StructuresResult, loadView: () => Promise<View>) {
  const system = createStructuresSystem({ loadStructures: async () => file, loadView });
  const made = makeWorldDeps();
  return { world: createWorld([system], made.deps), ground: made.deps.ground };
}

describe("structures system", () => {
  it("registers the treads as a ground surface before the walk", async () => {
    const { world, ground } = setup(FILE, never);
    await world.init("critical");
    expect(world.status().structures?.state).toBe("ready");
    expect(ground.surfaces).toHaveLength(1);
    expect(ground.surfaces[0]?.surfaceBelow(0.5, 3.2, 0.5, 0.4)).toBe(3);
  });

  it("adds the meshes under its root when they load", async () => {
    const object = new Object3D();
    const { world } = setup(FILE, async () => ({ object, dispose: () => undefined }));
    await world.init("critical");
    await Promise.resolve();
    await Promise.resolve();
    expect(object.parent?.name).toBe("system:structures");
  });

  it("is missing when structures.json does not exist", async () => {
    const { world, ground } = setup({ status: "missing" }, never);
    await world.init("critical");
    expect(world.status().structures?.state).toBe("missing");
    expect(ground.surfaces).toHaveLength(0);
  });

  it("fails with the file's message when structures.json is invalid", async () => {
    const { world } = setup({ status: "error", message: "bad" }, never);
    await world.init("critical");
    expect(world.status().structures?.state).toBe("failed");
  });
});
