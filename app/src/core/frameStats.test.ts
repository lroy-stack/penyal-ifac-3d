import { describe, expect, it } from "vitest";
import { FrameStats, SLOW_FRAME_MS } from "./frameStats";

function filled(values: number[], options?: ConstructorParameters<typeof FrameStats>[0]) {
  const stats = new FrameStats(options);
  for (const value of values) stats.push(value);
  return stats;
}

describe("FrameStats", () => {
  it("has no snapshot before the first sample", () => {
    expect(new FrameStats().snapshot).toBeNull();
  });

  it("computes nearest-rank p50, p95 and p99 over the window", () => {
    const stats = filled(
      Array.from({ length: 100 }, (_, i) => i + 1),
      { window: 100, recomputeEvery: 100 },
    );

    expect(stats.snapshot).toMatchObject({ samples: 100, p50: 50, p95: 95, p99: 99, max: 100 });
  });

  it("counts frames above 50 ms, and a frame of exactly 50 ms is not one of them", () => {
    const stats = filled([16, 50, 50.1, 120, 400], { window: 10, recomputeEvery: 5 });

    expect(SLOW_FRAME_MS).toBe(50);
    expect(stats.snapshot?.over50).toBe(3);
  });

  it("keeps raw spikes: nothing is clamped", () => {
    const stats = filled([16, 16, 2500], { window: 3, recomputeEvery: 3 });

    expect(stats.snapshot?.max).toBe(2500);
    expect(stats.snapshot?.p99).toBe(2500);
  });

  it("only looks at the most recent samples, and the slow-frame count follows the window", () => {
    const stats = new FrameStats({ window: 4, recomputeEvery: 1 });
    for (const value of [100, 100, 100, 100]) stats.push(value);
    expect(stats.snapshot?.over50).toBe(4);

    for (const value of [16, 16, 16]) stats.push(value);

    expect(stats.snapshot).toMatchObject({ samples: 4, over50: 1, p50: 16 });
    stats.push(16);
    expect(stats.snapshot).toMatchObject({ over50: 0, max: 16 });
  });

  it("recomputes only every N frames (the sort is not per frame)", () => {
    const stats = new FrameStats({ window: 100, recomputeEvery: 10 });
    for (let i = 0; i < 10; i++) stats.push(10);
    const first = stats.snapshot;
    expect(first?.p95).toBe(10);

    for (let i = 0; i < 9; i++) stats.push(200);
    expect(stats.snapshot).toBe(first);

    stats.push(200);
    expect(stats.snapshot).not.toBe(first);
    expect(stats.snapshot?.p95).toBe(200);
    expect(stats.recomputations).toBe(3);
  });

  it("publishes the first snapshot at the first frame so readers never wait N frames", () => {
    const stats = filled([20], { recomputeEvery: 60 });

    expect(stats.snapshot).toMatchObject({ samples: 1, p50: 20, p95: 20, p99: 20 });
  });

  it("rejects impossible settings and ignores non-finite samples", () => {
    expect(() => new FrameStats({ window: 0 })).toThrow(/window/);
    expect(() => new FrameStats({ recomputeEvery: 0 })).toThrow(/recomputeEvery/);

    const stats = filled([Number.NaN, Number.POSITIVE_INFINITY, -3, 16]);
    expect(stats.snapshot).toMatchObject({ samples: 1, p50: 16 });
  });
});
