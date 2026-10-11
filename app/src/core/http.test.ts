import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import {
  BINARY_TIMEOUT_MS,
  fetchBuffer,
  fetchChecked,
  fetchJson,
  JSON_TIMEOUT_MS,
  RequestTimeoutError,
} from "./http";

/** A fetch that never answers; it only rejects when its signal aborts, like the real one. */
function hangingFetch(): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      (_url: string, init?: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => reject(init.signal?.reason), {
            once: true,
          });
        }),
    ),
  );
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("fetch timeouts", () => {
  it("rejects a JSON request that never resolves after the JSON timeout", async () => {
    hangingFetch();
    const result = fetchJson("/a.json", z.object({}));
    const assertion = expect(result).rejects.toBeInstanceOf(RequestTimeoutError);

    await vi.advanceTimersByTimeAsync(JSON_TIMEOUT_MS);

    await assertion;
  });

  it("gives a binary request the longer budget", async () => {
    hangingFetch();
    let state = "pending";
    fetchBuffer("/a.bin").catch(() => {
      state = "rejected";
    });

    await vi.advanceTimersByTimeAsync(JSON_TIMEOUT_MS + 1);
    expect(state).toBe("pending");
    await vi.advanceTimersByTimeAsync(BINARY_TIMEOUT_MS - JSON_TIMEOUT_MS);

    expect(state).toBe("rejected");
  });

  it("still rejects with the caller's reason when the caller aborts first", async () => {
    hangingFetch();
    const controller = new AbortController();
    const result = fetchChecked("/a.json", controller.signal);
    const assertion = expect(result).rejects.toBe(controller.signal.reason);

    controller.abort();

    await assertion;
  });

  it("returns the body of a request that answers in time and leaves no timer behind", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { headers: { "content-type": "application/json" } })),
    );

    await expect(fetchJson("/a.json", z.object({}))).resolves.toEqual({});
    expect(vi.getTimerCount()).toBe(0);
  });
});
