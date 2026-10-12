import { BoxGeometry, Group, Mesh, MeshStandardMaterial, Texture } from "three";
import { afterEach, describe, expect, it, vi } from "vitest";
import { disposeObject } from "./disposal";

describe("disposeObject", () => {
  afterEach(() => vi.restoreAllMocks());

  it("disposes geometries, materials and the textures the materials hold", () => {
    const spy = vi.spyOn(Texture.prototype, "dispose");
    const map = new Texture();
    const normal = new Texture();
    const material = new MeshStandardMaterial({ map, normalMap: normal });
    const geometry = new BoxGeometry(1, 1, 1);
    const root = new Group();
    root.add(new Mesh(geometry, material));
    const events: string[] = [];
    geometry.addEventListener("dispose", () => events.push("geometry"));
    material.addEventListener("dispose", () => events.push("material"));

    disposeObject(root);

    expect(spy.mock.contexts).toEqual(expect.arrayContaining([map, normal]));
    expect(spy).toHaveBeenCalledTimes(2);
    expect(events.sort()).toEqual(["geometry", "material"]);
  });
});
