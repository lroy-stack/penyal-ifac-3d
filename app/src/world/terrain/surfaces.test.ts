import { Mesh, MeshStandardMaterial, Object3D, type Texture } from "three";
import { describe, expect, it, vi } from "vitest";
import { shaderPatchUniforms } from "../../core/shaderPatch";
import {
  createSurfaceMasks,
  PAINT_HIGH,
  PAINT_LOW,
  patchSurfacesShader,
  SURFACE_PROGRAM_KEY,
  srgbToLinear,
  surfaceBlend,
  surfaceColor,
} from "./surfaces";

describe("surfaceBlend", () => {
  it("clamps a channel sum above 1 by scaling the channels", () => {
    const blend = surfaceBlend([0.8, 0.4, 0.4, 0]);
    expect(blend.coverage).toBeCloseTo(1, 9);
    expect(blend.weights[0]).toBeCloseTo(0.5, 9);
    expect(blend.weights[1]).toBeCloseTo(0.25, 9);
  });

  it("keeps a sum below 1 and leaves the rest to the terrain", () => {
    const blend = surfaceBlend([0.3, 0, 0, 0.2]);
    expect(blend.coverage).toBeCloseTo(0.5, 9);
    expect(blend.paint).toBeGreaterThan(0);
    expect(blend.paint).toBeLessThan(1);
  });

  it("does not paint UASTC leaks (48/255) and fully paints solid coverage", () => {
    expect(surfaceBlend([48 / 255, 0, 0, 0]).paint).toBe(0);
    expect(surfaceBlend([PAINT_LOW, 0, 0, 0]).paint).toBe(0);
    expect(surfaceBlend([PAINT_HIGH, 0, 0, 0]).paint).toBe(1);
    expect(surfaceBlend([0, 0, 1, 0]).paint).toBe(1);
  });

  it("is monotonic in coverage", () => {
    const paints = [0, 0.1, 0.25, 0.4, 0.55, 0.7, 0.85, 1].map(
      (c) => surfaceBlend([c, 0, 0, 0]).paint,
    );
    expect(paints).toEqual([...paints].sort((a, b) => a - b));
  });
});

describe("surfaceColor", () => {
  it("gives the class colour for a pure class and treats paving like cobblestone", () => {
    const cobble = surfaceColor(surfaceBlend([1, 0, 0, 0]));
    const paving = surfaceColor(surfaceBlend([0, 0, 1, 0]));
    expect(cobble).toEqual(paving);
    expect(cobble[0]).toBeCloseTo(srgbToLinear(214), 9);
  });

  it("mixes classes by weight", () => {
    const grey = surfaceColor(surfaceBlend([0, 0, 0, 1]));
    const earth = surfaceColor(surfaceBlend([0, 1, 0, 0]));
    const half = surfaceColor(surfaceBlend([0, 0.5, 0, 0.5]));
    expect(half[0]).toBeCloseTo((grey[0] + earth[0]) / 2, 9);
  });
});

describe("patchSurfacesShader", () => {
  const vertex = "#include <common>\n#include <fog_vertex>";
  const fragment = "#include <common>\n#include <roughnessmap_fragment>";

  it("adds the mask sampling and clamps the sum in the fragment stage", () => {
    const out = patchSurfacesShader(vertex, fragment);
    expect(out.fragmentShader).toContain("uniform sampler2D uSurfMask;");
    expect(out.fragmentShader).toContain("max( 1.0, sMask.r + sMask.g + sMask.b + sMask.a )");
    expect(out.vertexShader).toContain("vSurfXZ =");
  });

  it("fails loudly when three drops a chunk", () => {
    expect(() => patchSurfacesShader("#include <common>", fragment)).toThrow(/fog_vertex/);
  });
});

function tileObject(): { object: Object3D; material: MeshStandardMaterial } {
  const material = new MeshStandardMaterial();
  const object = new Object3D();
  object.add(new Mesh(undefined, material));
  return { object, material };
}

function fakeTexture(): Texture & { disposed: number } {
  const t = {
    disposed: 0,
    dispose() {
      t.disposed++;
    },
  };
  return t as unknown as Texture & { disposed: number };
}

async function flush(): Promise<void> {
  for (let i = 0; i < 20; i++) await Promise.resolve();
}

describe("createSurfaceMasks", () => {
  it("patches the materials, loads the mask of a resident tile once and disposes it with the last LOD", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({ version: 1, tiles: [{ id: "t_1_-2", url: "t_1_-2.ktx2" }] }),
            { headers: { "content-type": "application/json" } },
          ),
      ),
    );
    const mask = fakeTexture();
    const loadAsync = vi.fn(async () => mask);
    const masks = createSurfaceMasks({
      loader: { loadAsync },
      manifestUrl: "http://x/assets/generated/surfaces/manifest.json",
      detail: false,
    });
    const a = tileObject();
    const b = tileObject();
    masks.attach("t_1_-2", 2, a.object);
    masks.attach("t_9_9", 2, tileObject().object);
    await flush();
    masks.attach("t_1_-2", 0, b.object);
    await flush();

    expect(a.material.customProgramCacheKey()).toBe(SURFACE_PROGRAM_KEY);
    expect(loadAsync).toHaveBeenCalledTimes(1);
    expect(loadAsync).toHaveBeenCalledWith("/assets/generated/surfaces/t_1_-2.ktx2");
    expect(shaderPatchUniforms(a.material).uSurfMask?.value).toBe(mask);
    expect(shaderPatchUniforms(b.material).uSurfOn?.value).toBe(1);
    expect(masks.stats()).toMatchObject({ resident: 1, loaded: 1 });

    masks.release("t_1_-2", 2);
    expect(mask.disposed).toBe(0);
    masks.release("t_1_-2", 0);
    expect(mask.disposed).toBe(1);
    expect(masks.stats().resident).toBe(0);
    vi.unstubAllGlobals();
  });
});
