import { describe, expect, it } from "vitest";
import { formatPerf, isPerfRequested } from "./perfOverlay";

describe("isPerfRequested", () => {
  it("is on only when ?perf is in the URL", () => {
    expect(isPerfRequested("")).toBe(false);
    expect(isPerfRequested("?start=summit")).toBe(false);
    expect(isPerfRequested("?perf")).toBe(true);
    expect(isPerfRequested("?start=summit&perf=1")).toBe(true);
  });

  it("can be switched off explicitly", () => {
    expect(isPerfRequested("?perf=0")).toBe(false);
    expect(isPerfRequested("?perf=false")).toBe(false);
  });
});

describe("formatPerf", () => {
  it("says it is waiting before the first frame", () => {
    expect(formatPerf(null, { calls: 0, triangles: 0 })).toBe("waiting for frames");
  });

  it("prints the percentiles, the hitch count and the draw load", () => {
    const text = formatPerf(
      { samples: 600, p50: 16.7, p95: 33.34, p99: 51.2, max: 180, over50: 4 },
      { calls: 18, triangles: 296001 },
    );

    expect(text).toBe(
      "p50 16.7 | p95 33.3 | p99 51.2 ms\n>50 ms: 4 of 600 (max 180 ms)\n18 calls | 296k tris",
    );
  });
});
