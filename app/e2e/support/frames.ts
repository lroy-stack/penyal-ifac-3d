import type { Page } from "@playwright/test";

/** What is recorded after every rendered frame, so a check sees each frame and not a 1 Hz sample. */
export type FrameSample = {
  frames: number;
  elapsed: number;
  x: number;
  y: number;
  z: number;
  grounded: boolean;
  camera: { x: number; y: number; z: number };
  cameraMode: string;
};

declare global {
  interface Window {
    __frameSamples?: FrameSample[];
    /** PNG data URLs of the canvas, taken in the frame in which an anchor was first reached. */
    __anchorShots?: Record<string, string>;
  }
}

/**
 * Wraps requestAnimationFrame before the app starts: after each frame callback it records the
 * app state, and when a new anchor has been reached it grabs the canvas in the same task (the
 * drawing buffer is only readable until the frame is composited).
 */
export async function installFrameRecorder(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const samples: FrameSample[] = [];
    const shots: Record<string, string> = {};
    window.__frameSamples = samples;
    window.__anchorShots = shots;
    const original = window.requestAnimationFrame.bind(window);
    let lastFrames = -1;
    let knownAnchors = 0;
    window.requestAnimationFrame = (callback) =>
      original((time) => {
        callback(time);
        const state = window.__appState;
        if (state === undefined || !state.ready || state.frames === lastFrames) return;
        lastFrames = state.frames;
        samples.push({
          frames: state.frames,
          elapsed: state.player.elapsed,
          x: state.player.x,
          y: state.player.y,
          z: state.player.z,
          grounded: state.player.grounded,
          camera: { ...state.camera },
          cameraMode: state.player.cameraMode,
        });
        if (state.anchorsReached.length > knownAnchors) {
          const canvas = document.getElementById("scene");
          for (const name of state.anchorsReached.slice(knownAnchors)) {
            if (canvas instanceof HTMLCanvasElement) shots[name] = canvas.toDataURL("image/png");
          }
          knownAnchors = state.anchorsReached.length;
        }
      });
  });
}

/** Returns and clears the frames recorded since the last call. */
export function drainFrames(page: Page): Promise<FrameSample[]> {
  return page.evaluate(() => window.__frameSamples?.splice(0) ?? []);
}

/** Returns and clears the anchor screenshots (name to PNG data URL) taken since the last call. */
export function drainAnchorShots(page: Page): Promise<Record<string, string>> {
  return page.evaluate(() => {
    const shots = window.__anchorShots ?? {};
    const copy = { ...shots };
    for (const key of Object.keys(shots)) delete shots[key];
    return copy;
  });
}

export function dataUrlToBuffer(dataUrl: string): Buffer {
  return Buffer.from(dataUrl.slice(dataUrl.indexOf(",") + 1), "base64");
}

/** Waits until the app has published `window.__appState` and rendered a few frames. */
export async function waitForApp(page: Page, timeout = 90_000): Promise<void> {
  await page.waitForFunction(() => (window.__appState?.frames ?? 0) > 3, undefined, { timeout });
}
