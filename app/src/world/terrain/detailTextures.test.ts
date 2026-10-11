import { RepeatWrapping, Texture } from "three";
import { describe, expect, it, vi } from "vitest";
import { createDetailTextures, detailFileName, type TextureLoader } from "./detailTextures";
import { createTerrainDetailUniforms } from "./material";

const flush = async (): Promise<void> => {
  for (let i = 0; i < 10; i++) await Promise.resolve();
};

function fakeLoader(failOn?: string) {
  const loaded: { url: string; texture: Texture }[] = [];
  const loader: TextureLoader = {
    loadAsync: (url) => {
      if (failOn !== undefined && url.includes(failOn)) return Promise.reject(new Error("boom"));
      const texture = new Texture();
      loaded.push({ url, texture });
      return Promise.resolve(texture);
    },
  };
  return { loader, loaded };
}

const urlFor = (name: string) => `/m/${name}`;

describe("createDetailTextures", () => {
  it("stays procedural when there is no loader or the set is off", async () => {
    const uniforms = createTerrainDetailUniforms();
    const none = createDetailTextures({ loader: null, urlFor, uniforms, set: "2k" });
    const off = createDetailTextures({ loader: fakeLoader().loader, urlFor, uniforms, set: "off" });
    await flush();
    expect(none.source()).toBe("procedural");
    expect(off.source()).toBe("procedural");
    expect(uniforms.uRockMode.value).toBe(0);
  });

  it("loads the 1k maps at once, repeating and anisotropic, and switches the shader on", async () => {
    const uniforms = createTerrainDetailUniforms();
    const { loader, loaded } = fakeLoader();
    const detail = createDetailTextures({ loader, urlFor, uniforms, set: "1k" });
    await flush();

    expect(loaded.map((l) => l.url).sort()).toEqual(
      (["arm", "diff", "nor_gl"] as const).map((m) => `/m/${detailFileName(m, "1k")}`).sort(),
    );
    expect(detail.source()).toBe("1k");
    expect(uniforms.uRockMode.value).toBe(1);
    expect(uniforms.uRockDiff.value?.wrapS).toBe(RepeatWrapping);
    expect(uniforms.uRockDiff.value?.anisotropy).toBeGreaterThan(1);
  });

  it("loads 2k only after the terrain settles, then frees the 1k maps", async () => {
    const uniforms = createTerrainDetailUniforms();
    const { loader, loaded } = fakeLoader();
    const detail = createDetailTextures({ loader, urlFor, uniforms, set: "2k" });
    await flush();
    detail.settled(false);
    await flush();
    expect(detail.source()).toBe("1k");
    expect(loaded).toHaveLength(3);

    const first = loaded.map((l) => l.texture);
    const disposed = first.map((t) => vi.spyOn(t, "dispose"));
    detail.settled(true);
    detail.settled(true);
    await flush();

    expect(loaded).toHaveLength(6);
    expect(detail.source()).toBe("2k");
    for (const spy of disposed) expect(spy).toHaveBeenCalledTimes(1);
  });

  it("keeps the procedural noise and reports the error when a load fails", async () => {
    const uniforms = createTerrainDetailUniforms();
    const detail = createDetailTextures({
      loader: fakeLoader("nor_gl").loader,
      urlFor,
      uniforms,
      set: "1k",
    });
    await flush();
    expect(detail.source()).toBe("procedural");
    expect(uniforms.uRockMode.value).toBe(0);
    expect(detail.lastError()).toContain("boom");
  });

  it("disposes what it loaded and switches the shader back to procedural", async () => {
    const uniforms = createTerrainDetailUniforms();
    const { loader, loaded } = fakeLoader();
    const detail = createDetailTextures({ loader, urlFor, uniforms, set: "1k" });
    await flush();
    const spies = loaded.map((l) => vi.spyOn(l.texture, "dispose"));
    detail.dispose();
    for (const spy of spies) expect(spy).toHaveBeenCalledTimes(1);
    expect(uniforms.uRockMode.value).toBe(0);
    expect(uniforms.uRockDiff.value).toBeNull();
  });
});
