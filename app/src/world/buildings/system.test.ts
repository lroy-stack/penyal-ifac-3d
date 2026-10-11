import { BoxGeometry, Group, Mesh, MeshStandardMaterial } from "three";
import { describe, expect, it } from "vitest";
import { makeWorldDeps } from "../fixtures";
import { createWorld } from "../systems";
import { BUILDINGS_PATH, createBuildingsSystem } from "./system";

function fakeScene(): Group {
  const scene = new Group();
  for (const name of ["building_centre", "building_annex"]) {
    const mesh = new Mesh(new BoxGeometry(1, 1, 1), new MeshStandardMaterial());
    mesh.name = name;
    scene.add(mesh);
  }
  return scene;
}

describe("buildings system", () => {
  it("loads the GLB in the background and adds it under its root", async () => {
    const { deps } = makeWorldDeps();
    const urls: string[] = [];
    const system = createBuildingsSystem({
      load: async (_loader, url) => {
        urls.push(url);
        return fakeScene();
      },
    });
    expect(system.load).toBe("background");
    const world = createWorld([system], deps);
    world.startWalk();
    await world.init("background");
    const root = deps.scene.getObjectByName("system:buildings");
    expect(urls).toEqual([`/${BUILDINGS_PATH}`]);
    expect(deps.scene.getObjectByName("building_centre")?.parent?.parent).toBe(root);
    expect(deps.scene.getObjectByName("building_annex")).toBeDefined();
    expect(world.status().buildings).toEqual({ state: "ready" });
  });

  it("reports a file that cannot be loaded as missing instead of failing", async () => {
    const { deps } = makeWorldDeps();
    const system = createBuildingsSystem({
      load: async () => {
        throw new Error("404");
      },
    });
    const world = createWorld([system], deps);
    world.startWalk();
    await world.init("background");
    expect(world.status().buildings).toMatchObject({ state: "missing" });
  });

  it("disposes geometries and materials", async () => {
    const { deps } = makeWorldDeps();
    const scene = fakeScene();
    const system = createBuildingsSystem({ load: async () => scene });
    const world = createWorld([system], deps);
    world.startWalk();
    await world.init("background");
    let disposed = 0;
    for (const child of scene.children as Mesh[]) {
      child.geometry.addEventListener("dispose", () => disposed++);
      (child.material as MeshStandardMaterial).addEventListener("dispose", () => disposed++);
    }
    world.dispose();
    expect(disposed).toBe(4);
  });
});
