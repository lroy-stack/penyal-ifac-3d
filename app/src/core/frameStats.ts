/** Fixed-size ring of recent frame times (ms) with a nearest-rank percentile. */
export class FrameTimeWindow {
  private readonly samples: number[] = [];
  private next = 0;

  constructor(private readonly capacity: number = 120) {
    if (capacity < 1)
      throw new Error(`FrameTimeWindow needs a capacity of at least 1, got ${capacity}.`);
  }

  push(milliseconds: number): void {
    if (this.samples.length < this.capacity) this.samples.push(milliseconds);
    else this.samples[this.next] = milliseconds;
    this.next = (this.next + 1) % this.capacity;
  }

  get size(): number {
    return this.samples.length;
  }

  /** Nearest-rank percentile (0..100), or null before the first sample. */
  percentile(p: number): number | null {
    if (this.samples.length === 0) return null;
    const sorted = [...this.samples].sort((a, b) => a - b);
    const rank = Math.ceil((Math.min(Math.max(p, 0), 100) / 100) * sorted.length);
    return sorted[Math.max(rank, 1) - 1] as number;
  }
}
