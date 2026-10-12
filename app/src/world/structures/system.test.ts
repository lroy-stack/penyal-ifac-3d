import { BoxGeometry, Group, Mesh, MeshStandardMaterial, Object3D } from "three";
import { describe, expect, it } from "vitest";
import { shaderPatchUniforms } from "../../core/shaderPatch";
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
    await world.init("beforeWalk");
    expect(world.status().structures?.state).toBe("ready");
    expect(ground.surfaces).toHaveLength(1);
    expect(ground.surfaces[0]?.surfaceBelow(0.5, 3.2, 0.5, 0.4)).toBe(3);
  });

  it("adds the meshes under its root when they load", async () => {
    const object = new Object3D();
    const { world } = setup(FILE, async () => ({ object, dispose: () => undefined }));
    await world.init("beforeWalk");
    await Promise.resolve();
    await Promise.resolve();
    expect(object.parent?.name).toBe("system:structures");
  });

  it("is missing when structures.json does not exist", async () => {
    const { world, ground } = setup({ status: "missing" }, never);
    await world.init("beforeWalk");
    expect(world.status().structures?.state).toBe("missing");
    expect(ground.surfaces).toHaveLength(0);
  });

  it("fails with the file's message when structures.json is invalid", async () => {
    const { world } = setup({ status: "error", message: "bad" }, never);
    await world.init("beforeWalk");
    expect(world.status().structures?.state).toBe("failed");
  });

  it("loads before the walk, not on the critical path", () => {
    expect(createStructuresSystem().load).toBe("beforeWalk");
  });

  it("keeps the walk gate closed until the treads are registered", async () => {
    let arrive: (file: StructuresResult) => void = () => undefined;
    const system = createStructuresSystem({
      loadStructures: () => new Promise<StructuresResult>((resolve) => (arrive = resolve)),
      loadView: never,
    });
    const made = makeWorldDeps();
    const world = createWorld([system], made.deps);
    const init = world.init("beforeWalk");
    expect(world.isSettled()).toBe(false);
    expect(made.deps.ground.surfaces).toHaveLength(0);
    arrive(FILE);
    await init;
    expect(world.isSettled()).toBe(true);
    expect(made.deps.ground.surfaces).toHaveLength(1);
  });

  it("attaches the shared atmosphere to the materials of the meshes", async () => {
    const material = new MeshStandardMaterial();
    const object = new Group();
    object.add(new Mesh(new BoxGeometry(1, 1, 1), material));
    const system = createStructuresSystem({
      loadStructures: async () => FILE,
      loadView: async () => ({ object, dispose: () => undefined }),
    });
    const made = makeWorldDeps();
    const world = createWorld([system], made.deps);
    await world.init("beforeWalk");
    await Promise.resolve();
    await Promise.resolve();
    expect(shaderPatchUniforms(material).uAtmoSunDirection).toBe(
      made.deps.atmosphere.uniforms.uAtmoSunDirection,
    );
  });
});
