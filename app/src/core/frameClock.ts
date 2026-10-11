/** Longest real interval (ms) a frame counts for, so one long stall does not end a deadline. */
export const MAX_REAL_FRAME_MS = 1000;

export type Tick = {
  readonly frame: number;
  /** Simulated seconds this frame: the clamped delta times the timescale; 0 while frozen. */
  readonly dt: number;
  /** Simulated seconds since boot; the frozen value while frozen. */
  readonly time: number;
  /** Real milliseconds since the previous frame, capped; 0 when there is none to measure. */
  readonly realMs: number;
};

export interface FrameClock {
  /** `rawMs` is the loop's real interval, null for the first frame after a start or a hidden tab. */
  next(deltaSeconds: number, rawMs: number | null): Tick;
  /** Test hook: holds `time` at `seconds` and `dt` at 0; null releases it. */
  freeze(seconds: number | null): void;
}

export function createFrameClock(timescale: () => number): FrameClock {
  let frame = 0;
  let time = 0;
  let frozenAt: number | null = null;
  return {
    next(deltaSeconds, rawMs) {
      frame++;
      const realMs = rawMs === null ? 0 : Math.min(rawMs, MAX_REAL_FRAME_MS);
      if (frozenAt !== null) return { frame, dt: 0, time: frozenAt, realMs };
      const dt = Math.max(deltaSeconds, 0) * timescale();
      time += dt;
      return { frame, dt, time, realMs };
    },
    freeze(seconds) {
      frozenAt = seconds;
      if (seconds === null) return;
      time = seconds;
    },
  };
}
