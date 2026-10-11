import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createLoop, MAX_FRAME_DELTA } from "./loop";

type Listener = () => void;

class FakeDocument {
  hidden = false;
  private readonly listeners = new Map<string, Set<Listener>>();

  addEventListener(type: string, listener: Listener): void {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type)?.add(listener);
  }

  removeEventListener(type: string, listener: Listener): void {
    this.listeners.get(type)?.delete(listener);
  }

  setHidden(hidden: boolean): void {
    this.hidden = hidden;
    for (const listener of [...(this.listeners.get("visibilitychange") ?? [])]) listener();
  }

  listenerCount(type: string): number {
    return this.listeners.get(type)?.size ?? 0;
  }
}

describe("createLoop", () => {
  let doc: FakeDocument;
  let pending: Map<number, FrameRequestCallback>;
  let nextId: number;

  const runFrame = (): void => {
    const [id, callback] = [...pending.entries()][0] as [number, FrameRequestCallback];
    pending.delete(id);
    callback(performance.now());
  };

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["performance"] });
    vi.setSystemTime(0);
    doc = new FakeDocument();
    pending = new Map();
    nextId = 1;
    vi.stubGlobal("document", doc);
    vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
      const id = nextId++;
      pending.set(id, callback);
      return id;
    });
    vi.stubGlobal("cancelAnimationFrame", (id: number) => {
      pending.delete(id);
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("reports the time between frames in seconds", () => {
    const deltas: number[] = [];
    const loop = createLoop((dt) => deltas.push(dt));
    loop.start();

    vi.advanceTimersByTime(16);
    runFrame();
    vi.advanceTimersByTime(17);
    runFrame();

    expect(deltas[0]).toBeCloseTo(0.016, 6);
    expect(deltas[1]).toBeCloseTo(0.017, 6);
    loop.stop();
  });

  it("clamps a long stall to MAX_FRAME_DELTA", () => {
    const deltas: number[] = [];
    const loop = createLoop((dt) => deltas.push(dt));
    loop.start();
    vi.advanceTimersByTime(16);
    runFrame();

    vi.advanceTimersByTime(2500);
    runFrame();

    expect(deltas[1]).toBe(MAX_FRAME_DELTA);
    loop.stop();
  });

  it("resets the timer on start so a late start does not yield a large first delta", () => {
    const deltas: number[] = [];
    const loop = createLoop((dt) => deltas.push(dt));
    vi.advanceTimersByTime(5000);

    loop.start();
    vi.advanceTimersByTime(16);
    runFrame();

    expect(deltas[0]).toBeCloseTo(0.016, 6);
    loop.stop();
  });

  it("restarts cleanly: the pause between stop and start is not simulated", () => {
    const deltas: number[] = [];
    const loop = createLoop((dt) => deltas.push(dt));
    loop.start();
    vi.advanceTimersByTime(16);
    runFrame();
    loop.stop();
    expect(pending.size).toBe(0);

    vi.advanceTimersByTime(30_000);
    loop.start();
    vi.advanceTimersByTime(16);
    runFrame();

    expect(deltas[1]).toBeCloseTo(0.016, 6);
    loop.stop();
  });

  it("does not schedule frames while the document is hidden and resumes when visible", () => {
    const frames: number[] = [];
    const loop = createLoop((dt) => frames.push(dt));
    loop.start();
    doc.setHidden(true);
    expect(pending.size).toBe(0);

    vi.advanceTimersByTime(60_000);
    doc.setHidden(false);
    expect(pending.size).toBe(1);
    vi.advanceTimersByTime(16);
    runFrame();

    expect(frames).toHaveLength(1);
    expect(frames[0]).toBeLessThanOrEqual(MAX_FRAME_DELTA);
    expect(frames[0]).toBeCloseTo(0.016, 6);
    loop.stop();
  });

  it("stop removes the visibility listener and cancels the pending frame", () => {
    const loop = createLoop(() => undefined);
    loop.start();
    expect(doc.listenerCount("visibilitychange")).toBeGreaterThan(0);

    loop.stop();

    expect(pending.size).toBe(0);
    expect(doc.listenerCount("visibilitychange")).toBe(0);
  });
});
