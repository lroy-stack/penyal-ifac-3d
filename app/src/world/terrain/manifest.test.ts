import { afterEach, describe, expect, it, vi } from "vitest";
import { makeManifest, makeTile } from "./fixtures";
import { loadTerrainManifest, parseTerrainManifest, resolveAssetUrl } from "./manifest";

const valid = () => structuredClone(makeManifest([makeTile(1, -3)]));

describe("parseTerrainManifest", () => {
  it("accepts the contract of the plan", () => {
    const manifest = parseTerrainManifest(valid());

    expect(manifest.near.tiles[0]?.lods.map((l) => l.level)).toEqual([0, 1, 2]);
    expect(manifest.far.url).toBe("far.glb");
  });

  it("explains an unknown version", () => {
    expect(() => parseTerrainManifest({ ...valid(), version: 2 })).toThrow(
      /version 2 is not supported.*version 1/s,
    );
    expect(() => parseTerrainManifest({})).toThrow(/version undefined is not supported/);
    expect(() => parseTerrainManifest(null)).toThrow(/not supported/);
  });

  it("rejects a tile without LODs", () => {
    const manifest = valid();
    (manifest.near.tiles[0] as { lods: unknown[] }).lods = [];

    expect(() => parseTerrainManifest(manifest)).toThrow(/invalid/);
  });

  it("rejects inverted bounds", () => {
    const manifest = valid();
    const tile = manifest.near.tiles[0];
    if (tile !== undefined) tile.bounds.minX = tile.bounds.maxX + 1;

    expect(() => parseTerrainManifest(manifest)).toThrow(/min < max/);
  });

  it("rejects a coarser LOD with a smaller error than a finer one", () => {
    const manifest = valid();
    const lod2 = manifest.near.tiles[0]?.lods[2];
    if (lod2 !== undefined) lod2.maxError = 0.01;

    expect(() => parseTerrainManifest(manifest)).toThrow(/maxError/);
  });
});

describe("resolveAssetUrl", () => {
  it("resolves against the manifest directory", () => {
    expect(resolveAssetUrl("/assets/generated/terrain/manifest.json", "tiles/a.glb")).toBe(
      "/assets/generated/terrain/tiles/a.glb",
    );
    expect(resolveAssetUrl("/sub/assets/terrain/manifest.json", "far.glb")).toBe(
      "/sub/assets/terrain/far.glb",
    );
  });
});

describe("loadTerrainManifest", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const respond = (init: { status?: number; type?: string; body?: unknown }) =>
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: (init.status ?? 200) < 400,
        status: init.status ?? 200,
        headers: new Headers({ "content-type": init.type ?? "application/json" }),
        json: async () => init.body,
      })),
    );

  it("reports a 404 as missing", async () => {
    respond({ status: 404 });

    expect(await loadTerrainManifest("/m.json")).toEqual({ status: "missing" });
  });

  it("reports the dev server's HTML fallback as missing", async () => {
    respond({ type: "text/html", body: undefined });

    expect(await loadTerrainManifest("/m.json")).toEqual({ status: "missing" });
  });

  it("returns the manifest when present", async () => {
    respond({ body: valid() });

    const result = await loadTerrainManifest("/m.json");

    expect(result.status).toBe("ready");
  });

  it("returns a readable error for an unsupported version", async () => {
    respond({ body: { ...valid(), version: 9 } });

    const result = await loadTerrainManifest("/m.json");

    expect(result).toMatchObject({
      status: "error",
      message: expect.stringContaining("version 9"),
    });
  });

  it("returns an error for a server failure", async () => {
    respond({ status: 500 });

    expect(await loadTerrainManifest("/m.json")).toMatchObject({
      status: "error",
      message: expect.stringContaining("HTTP 500"),
    });
  });
});
