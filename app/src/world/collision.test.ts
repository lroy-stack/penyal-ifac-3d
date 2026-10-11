import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { COLLISION_ATTEMPTS, loadCollisionField } from "./collision";

const META = { width: 2, height: 2, cellSize: 1, x0: 0, z0: 0, heightOffset: 0, heightScale: 1 };

function respond(url: string): Response {
  if (url.endsWith(".json")) {
    return new Response(JSON.stringify(META), { headers: { "content-type": "application/json" } });
  }
  return new Response(new Uint16Array([1, 2, 3, 4]), {
    headers: { "content-type": "application/octet-stream" },
  });
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("loadCollisionField", () => {
  it("retries a failed request with a backoff and then succeeds", async () => {
    let binaryCalls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.endsWith(".bin") && ++binaryCalls === 1) return new Response("", { status: 500 });
        return respond(url);
      }),
    );

    const loading = loadCollisionField("/collision");
    await vi.advanceTimersByTimeAsync(10_000);

    expect((await loading).heightAt(0, 0)).toBe(1);
    expect(binaryCalls).toBe(2);
  });

  it("rejects with the last error once every attempt failed", async () => {
    const fetchMock = vi.fn(async (_url: string) => new Response("", { status: 503 }));
    vi.stubGlobal("fetch", fetchMock);

    const loading = loadCollisionField("/collision");
    const assertion = expect(loading).rejects.toMatchObject({ status: 503 });
    await vi.advanceTimersByTimeAsync(60_000);

    await assertion;
    expect(fetchMock.mock.calls.filter(([url]) => String(url).endsWith(".bin"))).toHaveLength(
      COLLISION_ATTEMPTS,
    );
  });

  it("does not retry once the caller aborted", async () => {
    const fetchMock = vi.fn(async (_url: string) => new Response("", { status: 500 }));
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();
    controller.abort();

    const assertion = expect(loadCollisionField("/collision", controller.signal)).rejects.toThrow();
    await vi.advanceTimersByTimeAsync(60_000);

    await assertion;
    expect(fetchMock.mock.calls.length).toBeLessThanOrEqual(2);
  });
});
