/** A frame longer than this (ms) is a visible hitch. */
export const SLOW_FRAME_MS = 50;

export type FrameStatsOptions = {
  /** Number of recent frames the statistics cover; default 600 (about 10 s at 60 fps). */
  readonly window?: number;
  /** The percentiles are recomputed every N frames; default 30. */
  readonly recomputeEvery?: number;
};

export type FrameSnapshot = {
  /** Frames in the window. */
  readonly samples: number;
  readonly p50: number;
  readonly p95: number;
  readonly p99: number;
  readonly max: number;
  /** Frames in the window longer than SLOW_FRAME_MS. */
  readonly over50: number;
};

function nearestRank(sorted: Float64Array, p: number): number {
  const rank = Math.ceil((p / 100) * sorted.length);
  return sorted[Math.min(Math.max(rank, 1), sorted.length) - 1] as number;
}

/**
 * Rolling statistics over the raw `requestAnimationFrame` deltas (ms), not the clamped
 * simulation step. The window is a ring buffer; the slow-frame count is kept incrementally and
 * the percentiles are recomputed (one sort of a preallocated copy) every `recomputeEvery`
 * frames (and once at the very first frame), so the per-frame cost is O(1).
 */
export class FrameStats {
  private readonly ring: Float64Array;
  private readonly scratch: Float64Array;
  private readonly every: number;
  private count = 0;
  private next = 0;
  private slow = 0;
  private total = 0;
  private current: FrameSnapshot | null = null;
  private recomputed = 0;

  constructor(options: FrameStatsOptions = {}) {
    const window = options.window ?? 600;
    this.every = options.recomputeEvery ?? 30;
    if (!Number.isInteger(window) || window < 1) {
      throw new Error(`FrameStats needs a window of at least 1 frame, got ${window}.`);
    }
    if (!Number.isInteger(this.every) || this.every < 1) {
      throw new Error(`FrameStats needs recomputeEvery of at least 1, got ${this.every}.`);
    }
    this.ring = new Float64Array(window);
    this.scratch = new Float64Array(window);
  }

  /** Records one frame time in ms; values that are not finite and positive are ignored. */
  push(milliseconds: number): void {
    if (!Number.isFinite(milliseconds) || milliseconds < 0) return;
    if (this.count === this.ring.length) {
      if ((this.ring[this.next] as number) > SLOW_FRAME_MS) this.slow--;
    } else {
      this.count++;
    }
    this.ring[this.next] = milliseconds;
    if (milliseconds > SLOW_FRAME_MS) this.slow++;
    this.next = (this.next + 1) % this.ring.length;

    this.total++;
    if (this.total === 1 || this.total % this.every === 0) this.recompute();
  }

  /** Statistics as of the last recomputation, or null before the first frame. */
  get snapshot(): FrameSnapshot | null {
    return this.current;
  }

  /** How many times the percentiles were sorted out (for tests and the overlay). */
  get recomputations(): number {
    return this.recomputed;
  }

  private recompute(): void {
    const sorted = this.scratch.subarray(0, this.count);
    sorted.set(this.ring.subarray(0, this.count));
    sorted.sort();
    this.current = {
      samples: this.count,
      p50: nearestRank(sorted, 50),
      p95: nearestRank(sorted, 95),
      p99: nearestRank(sorted, 99),
      max: sorted[sorted.length - 1] as number,
      over50: this.slow,
    };
    this.recomputed++;
  }
}
