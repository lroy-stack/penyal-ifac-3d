import { Timer } from "three";

export type FrameCallback = (deltaSeconds: number) => void;

export type Loop = {
  readonly start: () => void;
  readonly stop: () => void;
};

/**
 * Longest delta (s) handed to the frame callback. A stall (slow tile parse, GC, throttled
 * background tab) must not turn into one huge simulation step that tunnels the player through
 * the terrain.
 */
export const MAX_FRAME_DELTA = 0.1;

/**
 * Animation loop driven by three's Timer. The timer is reset on every start and whenever the tab
 * becomes visible again (Timer.connect), so the first frame after a pause never sees a large
 * delta; the delta is clamped to MAX_FRAME_DELTA as a second line of defence.
 */
export function createLoop(onFrame: FrameCallback): Loop {
  const timer = new Timer();
  let handle: number | null = null;
  let running = false;

  const tick = (timestamp: number): void => {
    handle = requestAnimationFrame(tick);
    timer.update(timestamp);
    onFrame(Math.min(timer.getDelta(), MAX_FRAME_DELTA));
  };

  const schedule = (): void => {
    if (handle === null) handle = requestAnimationFrame(tick);
  };

  const cancel = (): void => {
    if (handle !== null) {
      cancelAnimationFrame(handle);
      handle = null;
    }
  };

  const onVisibilityChange = (): void => {
    if (!running) return;
    if (document.hidden) cancel();
    else schedule();
  };

  return {
    start: () => {
      if (running) return;
      running = true;
      timer.reset();
      timer.connect(document);
      document.addEventListener("visibilitychange", onVisibilityChange);
      if (!document.hidden) schedule();
    },
    stop: () => {
      if (!running) return;
      running = false;
      cancel();
      document.removeEventListener("visibilitychange", onVisibilityChange);
      timer.disconnect();
    },
  };
}
