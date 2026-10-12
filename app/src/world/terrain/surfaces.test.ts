import { Mesh, MeshStandardMaterial, Object3D, type Texture } from "three";
import { afterEach, describe, expect, it, vi } from "vitest";
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

  describe("races and failures", () => {
    const MANIFEST_URL = "http://x/assets/generated/surfaces/manifest.json";
    const jsonResponse = (body: unknown): Response =>
      new Response(JSON.stringify(body), { headers: { "content-type": "application/json" } });
    const manifestWith = (...ids: string[]): Response =>
      jsonResponse({ version: 1, tiles: ids.map((id) => ({ id, url: `${id}.ktx2` })) });

    afterEach(() => vi.unstubAllGlobals());

    it("counts the manifest, the detail map and the masks in flight as pending until they settle", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(async () => manifestWith("t_1_1", "t_2_2")),
      );
      const detail = fakeTexture();
      const arrivals: Array<(texture: Texture) => void> = [];
      const loadAsync = vi.fn(() => new Promise<Texture>((resolve) => arrivals.push(resolve)));
      const masks = createSurfaceMasks({
        loader: { loadAsync },
        manifestUrl: MANIFEST_URL,
        detail: true,
      });
      masks.attach("t_1_1", 0, tileObject().object);
      expect(masks.stats().pending).toBe(2);
      await flush();
      // detail map, then the mask of t_1_1
      expect(masks.stats().pending).toBe(2);
      arrivals[0]?.(detail);
      await flush();
      expect(masks.stats().pending).toBe(1);
      arrivals[1]?.(fakeTexture());
      await flush();
      expect(masks.stats()).toMatchObject({ pending: 0, loaded: 1, error: null });
    });

    it("is not pending after a failure", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(async () => manifestWith("t_1_1")),
      );
      const masks = createSurfaceMasks({
        loader: { loadAsync: vi.fn(async () => Promise.reject(new Error("bad"))) },
        manifestUrl: MANIFEST_URL,
        detail: false,
      });
      masks.attach("t_1_1", 0, tileObject().object);
      await flush();
      expect(masks.stats()).toMatchObject({ pending: 0, loaded: 0 });
      expect(masks.stats().error).not.toBeNull();
    });

    it("drops a mask that arrives after its tile was released", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(async () => manifestWith("t_1_1")),
      );
      const mask = fakeTexture();
      let arrive: (texture: Texture) => void = () => undefined;
      const loadAsync = vi.fn(() => new Promise<Texture>((resolve) => (arrive = resolve)));
      const masks = createSurfaceMasks({
        loader: { loadAsync },
        manifestUrl: MANIFEST_URL,
        detail: false,
      });
      const tile = tileObject();
      masks.attach("t_1_1", 0, tile.object);
      await flush();
      expect(loadAsync).toHaveBeenCalledTimes(1);

      masks.release("t_1_1", 0);
      arrive(mask);
      await flush();

      expect(mask.disposed).toBe(1);
      expect(shaderPatchUniforms(tile.material).uSurfOn?.value).toBe(0);
      expect(masks.stats()).toMatchObject({ resident: 0, loaded: 0, error: null });
    });

    it("aborts the manifest request on dispose and disposes a mask that arrives afterwards", async () => {
      let requestSignal: AbortSignal | undefined;
      vi.stubGlobal(
        "fetch",
        vi.fn(
          (_url: string, init?: RequestInit) =>
            new Promise<Response>((_resolve, reject) => {
              requestSignal = init?.signal ?? undefined;
              requestSignal?.addEventListener("abort", () =>
                reject(new DOMException("x", "AbortError")),
              );
            }),
        ),
      );
      const onError = vi.fn();
      const masks = createSurfaceMasks({
        loader: { loadAsync: vi.fn(async () => fakeTexture()) },
        manifestUrl: MANIFEST_URL,
        detail: false,
        onError,
      });
      masks.attach("t_1_1", 0, tileObject().object);
      masks.dispose();
      await flush();

      expect(requestSignal?.aborted).toBe(true);
      expect(onError).not.toHaveBeenCalled();
      expect(masks.stats().error).toBeNull();
    });

    it("aborts the manifest request when the caller's signal aborts", async () => {
      let requestSignal: AbortSignal | undefined;
      vi.stubGlobal(
        "fetch",
        vi.fn(
          (_url: string, init?: RequestInit) =>
            new Promise<Response>((_resolve, reject) => {
              requestSignal = init?.signal ?? undefined;
              requestSignal?.addEventListener("abort", () =>
                reject(new DOMException("x", "AbortError")),
              );
            }),
        ),
      );
      const caller = new AbortController();
      const onError = vi.fn();
      createSurfaceMasks({
        loader: { loadAsync: vi.fn() },
        manifestUrl: MANIFEST_URL,
        detail: false,
        signal: caller.signal,
        onError,
      });
      caller.abort();
      await flush();

      expect(requestSignal?.aborted).toBe(true);
      expect(onError).not.toHaveBeenCalled();
    });

    it("reports a failed mask once, retries it when another LOD arrives and clears the error", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(async () => manifestWith("t_1_1")),
      );
      const mask = fakeTexture();
      const loadAsync = vi
        .fn<(url: string) => Promise<Texture>>()
        .mockRejectedValueOnce(new Error("decode failed"))
        .mockResolvedValue(mask);
      const onError = vi.fn();
      const masks = createSurfaceMasks({
        loader: { loadAsync },
        manifestUrl: MANIFEST_URL,
        detail: false,
        onError,
      });
      masks.attach("t_1_1", 2, tileObject().object);
      await flush();

      expect(onError).toHaveBeenCalledTimes(1);
      expect(onError.mock.calls[0]?.[0]).toMatch(/mask of tile t_1_1 failed \(decode failed\)/);
      expect(masks.stats().error).toBe(onError.mock.calls[0]?.[0]);

      const finer = tileObject();
      masks.attach("t_1_1", 0, finer.object);
      await flush();

      expect(loadAsync).toHaveBeenCalledTimes(2);
      expect(onError).toHaveBeenCalledTimes(1);
      expect(masks.stats()).toMatchObject({ loaded: 1, error: null });
      expect(shaderPatchUniforms(finer.material).uSurfOn?.value).toBe(1);
    });

    it("reports a manifest that fails validation and leaves the tiles unpainted", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(async () => jsonResponse({ version: 2, tiles: [] })),
      );
      const loadAsync = vi.fn();
      const onError = vi.fn();
      const masks = createSurfaceMasks({
        loader: { loadAsync },
        manifestUrl: MANIFEST_URL,
        detail: false,
        onError,
      });
      const tile = tileObject();
      masks.attach("t_1_1", 0, tile.object);
      await flush();

      expect(onError).toHaveBeenCalledTimes(1);
      expect(onError.mock.calls[0]?.[0]).toMatch(/the manifest failed/);
      expect(masks.stats().error).not.toBeNull();
      expect(loadAsync).not.toHaveBeenCalled();
      expect(shaderPatchUniforms(tile.material).uSurfOn?.value).toBe(0);
    });

    it("reports a failed detail map", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(async () => manifestWith()),
      );
      const onError = vi.fn();
      createSurfaceMasks({
        loader: { loadAsync: vi.fn(async () => Promise.reject(new Error("no ktx2"))) },
        manifestUrl: MANIFEST_URL,
        detail: true,
        onError,
      });
      await flush();
      expect(onError).toHaveBeenCalledTimes(1);
      expect(onError.mock.calls[0]?.[0]).toMatch(/the detail map failed \(no ktx2\)/);
    });

    it("treats a manifest that does not exist as no surfaces, not as an error", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(async () => new Response("", { status: 404 })),
      );
      const onError = vi.fn();
      const masks = createSurfaceMasks({
        loader: { loadAsync: vi.fn() },
        manifestUrl: MANIFEST_URL,
        detail: false,
        onError,
      });
      masks.attach("t_1_1", 0, tileObject().object);
      await flush();
      expect(onError).not.toHaveBeenCalled();
      expect(masks.stats().error).toBeNull();
    });
  });
});
