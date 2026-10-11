import { describe, expect, it } from "vitest";
import { createFrameClock } from "./frameClock";

describe("createFrameClock", () => {
  it("counts frames and accumulates simulated time at the timescale", () => {
    let scale = 1;
    const clock = createFrameClock(() => scale);
    expect(clock.next(0.016, 16)).toEqual({ frame: 1, dt: 0.016, time: 0.016, realMs: 16 });
    scale = 4;
    const second = clock.next(0.01, 10);
    expect(second.frame).toBe(2);
    expect(second.dt).toBeCloseTo(0.04, 12);
    expect(second.time).toBeCloseTo(0.056, 12);
  });

  it("gives 0 real milliseconds when there is no previous frame and caps long stalls", () => {
    const clock = createFrameClock(() => 1);
    expect(clock.next(0, null).realMs).toBe(0);
    expect(clock.next(0.1, 90_000).realMs).toBe(1000);
  });

  it("holds the time and the step while frozen, and resumes from the frozen time", () => {
    const clock = createFrameClock(() => 1);
    clock.next(0.5, 500);
    clock.freeze(10);
    const frozen = clock.next(0.1, 100);
    expect(frozen).toEqual({ frame: 2, dt: 0, time: 10, realMs: 100 });
    expect(clock.next(0.1, 100).time).toBe(10);
    clock.freeze(null);
    expect(clock.next(0.25, 250)).toEqual({ frame: 4, dt: 0.25, time: 10.25, realMs: 250 });
  });

  it("ignores a negative delta", () => {
    const clock = createFrameClock(() => 1);
    expect(clock.next(-1, 16).dt).toBe(0);
  });
});
