import { BoxGeometry, DoubleSide, Group, Mesh, MeshStandardMaterial, Texture } from "three";
import { describe, expect, it, vi } from "vitest";
import { makeManifest, makeTile } from "./fixtures";
import { TERRAIN_PROGRAM_KEY } from "./material";
import type { View } from "./selection";
import {
  createTerrainStreamer,
  type LoadedTile,
  type TerrainStreamerOptions,
  type TileLoader,
} from "./streamer";

const FOV = (60 * Math.PI) / 180;

const viewAt = (x: number, z: number, y = 50): View => ({
  position: { x, y, z },
  forward: { x: 0, y: 0, z: -1 },
  fovY: FOV,
  viewportHeight: 1080,
});

type Pending = {
  readonly url: string;
  readonly signal: AbortSignal;
  resolve: () => void;
  reject: (error: unknown) => void;
  readonly object: Group;
  readonly geometry: BoxGeometry;
  readonly material: MeshStandardMaterial;
  readonly texture: Texture;
};

/** A loader whose requests stay pending until the test settles them. */
function manualLoader() {
  const requests: Pending[] = [];
  const load: TileLoader = (url, signal) =>
    new Promise<LoadedTile>((resolvePromise, rejectPromise) => {
      const geometry = new BoxGeometry(1, 1, 1);
      const texture = new Texture();
      const material = new MeshStandardMaterial({ map: texture, side: DoubleSide });
      const object = new Group();
      object.add(new Mesh(geometry, material));
      const pending: Pending = {
        url,
        signal,
        object,
        geometry,
        material,
        texture,
        resolve: () => resolvePromise({ object, bytes: 1000 }),
        reject: rejectPromise,
      };
      signal.addEventListener("abort", () =>
        rejectPromise(new DOMException("aborted", "AbortError")),
      );
      requests.push(pending);
    });
  return { load, requests };
}

const flush = async (): Promise<void> => {
  for (let i = 0; i < 5; i++) await Promise.resolve();
};

function setup(overrides: Partial<TerrainStreamerOptions> = {}, tileCount = 1) {
  const tiles = Array.from({ length: tileCount }, (_, i) => makeTile(i, 0));
  const loader = manualLoader();
  let time = 0;
  const streamer = createTerrainStreamer({
    manifest: makeManifest(tiles),
    manifestUrl: "/assets/generated/terrain/manifest.json",
    load: loader.load,
    sseThreshold: 2,
    now: () => time,
    ...overrides,
  });
  return {
    streamer,
    requests: loader.requests,
    tiles,
    advance: (ms: number) => {
      time += ms;
    },
  };
}

const urls = (requests: Pending[]): string[] => requests.map((r) => r.url.split("/").pop() ?? "");

describe("createTerrainStreamer loading order", () => {
  it("requests far first and never more than two at once", async () => {
    const { streamer, requests } = setup({}, 4);

    streamer.update(viewAt(128, 128));

    expect(urls(requests)).toEqual(["far.glb", "t_0_0_lod2.glb"]);
    expect(streamer.stats().inFlight).toBe(2);
    expect(streamer.stats().pending).toBeGreaterThanOrEqual(2);

    requests[0]?.resolve();
    await flush();
    streamer.update(viewAt(128, 128));
    expect(urls(requests)).toEqual(["far.glb", "t_0_0_lod2.glb", "t_1_0_lod2.glb"]);
  });

  it("loads the coarsest LOD of every tile before any finer one", async () => {
    const { streamer, requests } = setup({}, 3);
    const view = viewAt(128, 128);

    for (let round = 0; round < 6; round++) {
      streamer.update(view);
      for (const r of requests) if (r.object.parent === null) r.resolve();
      await flush();
    }
    streamer.update(view);

    const order = urls(requests);
    const firstFine = order.findIndex((u) => !u.endsWith("lod2.glb") && u !== "far.glb");
    expect(order.slice(0, firstFine).filter((u) => u.endsWith("lod2.glb"))).toHaveLength(3);
    expect(order).toContain("t_0_0_lod0.glb");
  });

  it("resolves tile URLs relative to the manifest", () => {
    const { streamer, requests } = setup();

    streamer.update(viewAt(128, 128));

    expect(requests[0]?.url).toBe("/assets/generated/terrain/far.glb");
    expect(requests[1]?.url).toBe("/assets/generated/terrain/tiles/t_0_0_lod2.glb");
  });
});

describe("createTerrainStreamer display", () => {
  async function loadCoarse() {
    const ctx = setup();
    const view = viewAt(128, 128);
    ctx.streamer.update(view);
    for (const r of ctx.requests) r.resolve();
    await flush();
    ctx.streamer.update(view);
    return { ...ctx, view };
  }

  it("keeps the coarse LOD visible until the finer one has loaded, then swaps", async () => {
    const { streamer, requests, view } = await loadCoarse();
    const coarse = requests.find((r) => r.url.endsWith("lod2.glb")) as Pending;
    const fine = requests.find((r) => r.url.endsWith("lod0.glb")) as Pending;
    expect(fine).toBeDefined();

    expect(coarse.object.visible).toBe(true);
    expect(streamer.stats().displayed).toEqual({ 2: 1 });

    fine.resolve();
    await flush();
    expect(coarse.object.visible).toBe(true);
    streamer.update(view);

    expect(fine.object.visible).toBe(true);
    expect(coarse.object.visible).toBe(false);
    expect(streamer.stats().displayed).toEqual({ 0: 1 });
  });

  it("sets FrontSide, frustum culling and bounding volumes on loaded meshes", async () => {
    const { requests } = await loadCoarse();
    const coarse = requests.find((r) => r.url.endsWith("lod2.glb")) as Pending;
    const mesh = coarse.object.children[0] as Mesh;

    expect(mesh.material).toHaveProperty("side", 0);
    expect(mesh.frustumCulled).toBe(true);
    expect(mesh.geometry.boundingSphere).not.toBeNull();
    expect(mesh.geometry.boundingBox).not.toBeNull();
  });

  it("adds loaded content under the streamer root and counts bytes", async () => {
    const { streamer } = await loadCoarse();

    expect(streamer.root.children.length).toBeGreaterThanOrEqual(2);
    expect(streamer.stats().bytesLoaded).toBeGreaterThanOrEqual(2000);
    expect(streamer.stats().farLoaded).toBe(true);
    expect(streamer.stats().resident).toEqual({ 2: 1 });
  });
});

describe("createTerrainStreamer cancellation", () => {
  it("aborts a finer load the camera no longer needs", async () => {
    const { streamer, requests } = setup();
    streamer.update(viewAt(128, 128));
    for (const r of requests) r.resolve();
    await flush();
    streamer.update(viewAt(128, 128));
    const fine = requests.find((r) => r.url.endsWith("lod0.glb")) as Pending;
    expect(fine.signal.aborted).toBe(false);

    streamer.update(viewAt(128, 128 + 5000));

    expect(fine.signal.aborted).toBe(true);
    await flush();
    expect(streamer.stats().inFlight).toBe(0);
    expect(streamer.stats().failed).toBe(0);
  });

  it("disposes content that arrives after an abort", async () => {
    const { streamer, requests } = setup();
    streamer.update(viewAt(128, 128));
    for (const r of requests) r.resolve();
    await flush();
    streamer.update(viewAt(128, 128));
    const fine = requests.find((r) => r.url.endsWith("lod0.glb")) as Pending;
    const geometryDispose = vi.spyOn(fine.geometry, "dispose");
    streamer.update(viewAt(128, 128 + 5000));

    fine.resolve();
    await flush();

    expect(streamer.root.children).not.toContain(fine.object);
    expect(geometryDispose).not.toHaveBeenCalled();
  });

  it("aborts everything on dispose and frees what is resident", async () => {
    const { streamer, requests } = setup();
    streamer.update(viewAt(128, 128));
    requests[0]?.resolve();
    await flush();
    const loaded = requests[0] as Pending;
    const dispose = vi.spyOn(loaded.geometry, "dispose");

    streamer.dispose();

    expect(requests[1]?.signal.aborted).toBe(true);
    expect(dispose).toHaveBeenCalled();
    expect(streamer.root.children).toHaveLength(0);
  });
});

describe("createTerrainStreamer eviction", () => {
  it("evicts an unused finer LOD over budget after the grace period and frees its resources", async () => {
    const { streamer, requests, advance } = setup({
      budget: { 0: 0, 1: 0 },
      evictionGraceMs: 10_000,
    });
    const near = viewAt(128, 128);
    streamer.update(near);
    for (const r of requests) r.resolve();
    await flush();
    streamer.update(near);
    const fine = requests.find((r) => r.url.endsWith("lod0.glb")) as Pending;
    fine.resolve();
    await flush();
    streamer.update(near);
    expect(streamer.stats().resident[0]).toBe(1);

    const far = viewAt(128, 128 + 5000);
    advance(1000);
    streamer.update(far);
    expect(streamer.stats().resident[0]).toBe(1);

    const geometryDispose = vi.spyOn(fine.geometry, "dispose");
    const materialDispose = vi.spyOn(fine.material, "dispose");
    const textureDispose = vi.spyOn(fine.texture, "dispose");
    advance(10_000);
    streamer.update(far);

    expect(streamer.stats().resident[0] ?? 0).toBe(0);
    expect(geometryDispose).toHaveBeenCalledOnce();
    expect(materialDispose).toHaveBeenCalledOnce();
    expect(textureDispose).toHaveBeenCalledOnce();
    expect(streamer.root.children).not.toContain(fine.object);
  });

  it("keeps unused LODs that fit the budget", async () => {
    const { streamer, requests, advance } = setup({ budget: { 0: 6, 1: 12 } });
    const near = viewAt(128, 128);
    streamer.update(near);
    for (const r of requests) r.resolve();
    await flush();
    streamer.update(near);
    requests.find((r) => r.url.endsWith("lod0.glb"))?.resolve();
    await flush();
    streamer.update(near);

    advance(60_000);
    streamer.update(viewAt(128, 128 + 5000));

    expect(streamer.stats().resident[0]).toBe(1);
  });

  it("never evicts the coarsest LOD", async () => {
    const { streamer, requests, advance } = setup({ budget: { 0: 0, 1: 0, 2: 0 } });
    streamer.update(viewAt(128, 128));
    for (const r of requests) r.resolve();
    await flush();

    advance(60_000);
    streamer.update(viewAt(128, 128 + 5000));

    expect(streamer.stats().resident[2]).toBe(1);
  });
});

describe("createTerrainStreamer failures", () => {
  it("records a failed load, backs off, then retries", async () => {
    const { streamer, requests, advance } = setup({ retryDelayMs: 1000 });
    const view = viewAt(128, 128 + 5000);
    streamer.update(view);
    requests[0]?.reject(new Error("HTTP 500"));
    await flush();

    streamer.update(view);
    expect(streamer.stats().failed).toBe(1);
    expect(streamer.stats().lastError).toContain("HTTP 500");
    expect(urls(requests).filter((u) => u === "far.glb")).toHaveLength(1);

    advance(1000);
    streamer.update(view);
    expect(urls(requests).filter((u) => u === "far.glb")).toHaveLength(2);
  });

  it("gives up after the retry limit", async () => {
    const { streamer, requests, advance } = setup({ retryDelayMs: 10, maxRetries: 1 });
    const view = viewAt(128, 128 + 5000);
    for (let attempt = 0; attempt < 4; attempt++) {
      streamer.update(view);
      const far = requests.filter((r) => r.url.endsWith("far.glb") && !r.signal.aborted).at(-1);
      far?.reject(new Error("HTTP 500"));
      await flush();
      advance(1000);
    }
    streamer.update(view);

    expect(urls(requests).filter((u) => u === "far.glb")).toHaveLength(2);
  });
});

describe("createTerrainStreamer terrain material", () => {
  async function loadedMaterial(quality: "high" | "low"): Promise<MeshStandardMaterial> {
    const { streamer, requests } = setup({ quality });
    streamer.update(viewAt(128, 128));
    const request = requests[1] as Pending;
    request.resolve();
    await flush();
    return request.material;
  }

  it("patches the tile material in the high tier only", async () => {
    const high = await loadedMaterial("high");
    expect(high.customProgramCacheKey()).toBe(TERRAIN_PROGRAM_KEY);
    const low = await loadedMaterial("low");
    expect(low.customProgramCacheKey()).not.toBe(TERRAIN_PROGRAM_KEY);
  });
});

describe("createTerrainStreamer LOD step constraint", () => {
  /** Tile 1 would pick its coarsest level (all errors are tiny) while tile 0 is under the camera. */
  function neighbours() {
    const flat = (tile: ReturnType<typeof makeTile>) => ({
      ...tile,
      lods: tile.lods.map((l) => ({ ...l, maxError: 0.25 })),
    });
    return [makeTile(0, 0), flat(makeTile(1, 0))];
  }

  async function requestedUrls(maxLodStep?: number): Promise<string[]> {
    const loader = manualLoader();
    const streamer = createTerrainStreamer({
      manifest: makeManifest(neighbours()),
      manifestUrl: "/assets/generated/terrain/manifest.json",
      load: loader.load,
      sseThreshold: 2,
      maxConcurrent: 8,
      quality: "low",
      ...(maxLodStep === undefined ? {} : { maxLodStep }),
    });
    const view = viewAt(128, 128);
    for (let round = 0; round < 4; round++) {
      streamer.update(view);
      for (const r of loader.requests) r.resolve();
      await flush();
    }
    return urls(loader.requests);
  }

  it("refines a tile that would sit two levels coarser than its neighbour", async () => {
    expect(await requestedUrls()).toContain("t_1_0_lod1.glb");
  });

  it("leaves the plan alone when the step is unlimited", async () => {
    expect(await requestedUrls(Number.POSITIVE_INFINITY)).not.toContain("t_1_0_lod1.glb");
  });
});
