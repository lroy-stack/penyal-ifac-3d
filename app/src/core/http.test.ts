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

  it("still rejects as an abort, not a timeout, when the caller aborts first", async () => {
    hangingFetch();
    const controller = new AbortController();
    const result = fetchChecked("/a.json", controller.signal);
    const assertion = expect(result).rejects.toMatchObject({ name: "AbortError" });

    controller.abort();

    await assertion;
  });

  it("surfaces the timeout when the engine rejects with a generic AbortError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url: string, init?: RequestInit) =>
          new Promise<Response>((_resolve, reject) => {
            init?.signal?.addEventListener(
              "abort",
              () => reject(new DOMException("The operation was aborted.", "AbortError")),
              { once: true },
            );
          }),
      ),
    );
    const result = fetchBuffer("/a.bin");
    const assertion = expect(result).rejects.toBeInstanceOf(RequestTimeoutError);

    await vi.advanceTimersByTimeAsync(BINARY_TIMEOUT_MS);

    await assertion;
  });

  it("times out a body that never completes after the headers arrived", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url: string, init?: RequestInit) => {
        const body = new ReadableStream<Uint8Array>({
          start(controller) {
            init?.signal?.addEventListener("abort", () => controller.error(init.signal?.reason), {
              once: true,
            });
          },
        });
        return new Response(body, { headers: { "content-type": "application/octet-stream" } });
      }),
    );
    const result = fetchBuffer("/a.bin");
    const assertion = expect(result).rejects.toBeInstanceOf(RequestTimeoutError);

    await vi.advanceTimersByTimeAsync(BINARY_TIMEOUT_MS);

    await assertion;
    expect(vi.getTimerCount()).toBe(0);
  });

  it("releases the timer once the caller has read a checked response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("x", { headers: { "content-type": "text/plain" } })),
    );

    const opened = await fetchChecked("/a.txt");
    await opened.read((response) => response.text());

    expect(vi.getTimerCount()).toBe(0);
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
