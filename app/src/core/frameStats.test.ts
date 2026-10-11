import { describe, expect, it } from "vitest";
import { FrameTimeWindow } from "./frameStats";

describe("FrameTimeWindow", () => {
  it("has no percentile before the first sample", () => {
    expect(new FrameTimeWindow().percentile(95)).toBeNull();
  });

  it("computes the nearest-rank p95", () => {
    const window = new FrameTimeWindow(100);
    for (let i = 1; i <= 100; i++) window.push(i);

    expect(window.percentile(95)).toBe(95);
    expect(window.percentile(50)).toBe(50);
    expect(window.percentile(100)).toBe(100);
  });

  it("keeps only the most recent samples", () => {
    const window = new FrameTimeWindow(3);
    for (const value of [100, 1, 2, 3]) window.push(value);

    expect(window.size).toBe(3);
    expect(window.percentile(100)).toBe(3);
  });

  it("rejects an empty window", () => {
    expect(() => new FrameTimeWindow(0)).toThrow(/capacity/);
  });
});
