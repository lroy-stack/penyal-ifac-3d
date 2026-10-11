import { describe, expect, it } from "vitest";
import { MAX_TIMESCALE, parseTimescale, simulationSteps } from "./timescale";

describe("parseTimescale", () => {
  it("defaults to 1 and reads ?timescale=N", () => {
    expect(parseTimescale("")).toBe(1);
    expect(parseTimescale("?start=turnstile")).toBe(1);
    expect(parseTimescale("?timescale=8")).toBe(8);
    expect(parseTimescale("?autowalk=summit&timescale=2.5")).toBe(2.5);
  });

  it("clamps to 1..16 and ignores garbage", () => {
    expect(parseTimescale("?timescale=0.2")).toBe(1);
    expect(parseTimescale("?timescale=-4")).toBe(1);
    expect(parseTimescale("?timescale=99")).toBe(MAX_TIMESCALE);
    expect(parseTimescale("?timescale=fast")).toBe(1);
    expect(parseTimescale("?timescale=")).toBe(1);
    expect(parseTimescale("?timescale=Infinity")).toBe(1);
  });
});

describe("simulationSteps", () => {
  it("is one step at timescale 1 and keeps the total", () => {
    expect(simulationSteps(0.016, 1, 0.25)).toEqual([0.016]);
    const steps = simulationSteps(0.1, 16, 0.25);
    expect(steps.every((s) => s <= 0.25)).toBe(true);
    expect(steps.reduce((a, b) => a + b, 0)).toBeCloseTo(1.6, 12);
  });

  it("has no steps for a zero or negative delta", () => {
    expect(simulationSteps(0, 8, 0.25)).toEqual([]);
    expect(simulationSteps(-1, 8, 0.25)).toEqual([]);
  });
});
