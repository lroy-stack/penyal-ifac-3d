/** How often the walk gate looks at the world while the frame loop is not running (ms). */
export const WALK_GATE_POLL_MS = 250;

export type WalkGate = {
  /** Resolves once the world is settled. */
  readonly opened: Promise<void>;
  /** The frame loop calls it every few frames. */
  poll(): void;
  dispose(): void;
};

/**
 * The gate the walk waits on. The frame loop polls it; when the loop is not running (no terrain
 * to draw) a timer does, so a beforeWalk system that settles late cannot block the walk forever.
 */
export function createWalkGate(
  isSettled: () => boolean,
  options: { readonly loopRunning: () => boolean },
): WalkGate {
  let open: () => void = () => undefined;
  const opened = new Promise<void>((resolve) => {
    open = resolve;
  });
  let timer: ReturnType<typeof setInterval> | null = null;
  const dispose = (): void => {
    if (timer !== null) clearInterval(timer);
    timer = null;
  };
  const poll = (): void => {
    if (!isSettled()) return;
    dispose();
    open();
  };
  timer = setInterval(() => {
    if (!options.loopRunning()) poll();
  }, WALK_GATE_POLL_MS);
  return { opened, poll, dispose };
}

export type BootSteps = {
  readonly critical: Promise<void>;
  readonly beforeWalk: Promise<void>;
  readonly walkGate: Promise<void>;
  /** Reads the critical systems' outcome and starts the preview loop. */
  startPreview(): void;
};

/**
 * ADR 0010, section 1: await `critical`, start the preview, and only then wait for `beforeWalk`
 * and the walk gate, so a slow beforeWalk system never delays the first frame, the poster or the
 * terrain stall gate.
 */
export async function runBoot(steps: BootSteps): Promise<void> {
  await steps.critical;
  steps.startPreview();
  await Promise.all([steps.beforeWalk, steps.walkGate]);
}
