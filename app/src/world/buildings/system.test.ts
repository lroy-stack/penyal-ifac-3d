import { BoxGeometry, Group, Mesh, MeshStandardMaterial, Texture } from "three";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HttpError, NotFoundError } from "../../core/http";
import { shaderPatchUniforms } from "../../core/shaderPatch";
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
  afterEach(() => vi.restoreAllMocks());

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

  it("attaches the shared atmosphere to every material", async () => {
    const { deps } = makeWorldDeps();
    const scene = fakeScene();
    const world = createWorld([createBuildingsSystem({ load: async () => scene })], deps);
    world.startWalk();
    await world.init("background");
    for (const child of scene.children as Mesh[]) {
      expect(shaderPatchUniforms(child.material as MeshStandardMaterial).uAtmoSunDirection).toBe(
        deps.atmosphere.uniforms.uAtmoSunDirection,
      );
    }
  });

  it("reports a file that does not exist as missing", async () => {
    const { deps } = makeWorldDeps();
    const system = createBuildingsSystem({
      load: async (_loader, url) => {
        throw new NotFoundError(url);
      },
    });
    const world = createWorld([system], deps);
    world.startWalk();
    await world.init("background");
    expect(world.status().buildings).toMatchObject({ state: "missing" });
  });

  it("fails loudly on any other load error instead of calling it missing", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const { deps } = makeWorldDeps();
    const system = createBuildingsSystem({
      load: async (_loader, url) => {
        throw new HttpError(url, 500);
      },
    });
    const world = createWorld([system], deps);
    world.startWalk();
    await world.init("background");
    expect(world.status().buildings).toMatchObject({ state: "failed" });
    expect(error).toHaveBeenCalledWith(expect.stringContaining("HTTP 500"));
  });

  it("disposes geometries, materials and textures", async () => {
    const { deps } = makeWorldDeps();
    const scene = fakeScene();
    const map = new Texture();
    ((scene.children[0] as Mesh).material as MeshStandardMaterial).map = map;
    const textureDispose = vi.spyOn(Texture.prototype, "dispose");
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
    expect(textureDispose.mock.contexts).toContain(map);
  });

  it("disposes a scene that finishes loading after the system was disposed", async () => {
    const { deps } = makeWorldDeps();
    const scene = fakeScene();
    const map = new Texture();
    ((scene.children[0] as Mesh).material as MeshStandardMaterial).map = map;
    const textureDispose = vi.spyOn(Texture.prototype, "dispose");
    let arrive: (scene: Group) => void = () => undefined;
    const system = createBuildingsSystem({
      load: () => new Promise<Group>((resolve) => (arrive = resolve)),
    });
    const world = createWorld([system], deps);
    world.startWalk();
    const init = world.init("background");
    world.dispose();
    arrive(scene);
    await init;
    expect(textureDispose.mock.contexts).toContain(map);
    expect(deps.scene.getObjectByName("building_centre")).toBeUndefined();
  });
});
