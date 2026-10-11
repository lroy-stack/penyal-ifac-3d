/** Lane number (1 to 8) when `appDirectory` is `<repo>/.worktrees/l<n>/app`, else null. */
export function laneOf(appDirectory: string): number | null {
  const match = /[\\/]\.worktrees[\\/]l([1-8])[\\/]app$/.exec(appDirectory);
  return match === null ? null : Number(match[1]);
}

export type LaneDefaults = {
  readonly port: number;
  readonly outputDir: string;
  /** One worker in a lane: the machine runs several lanes at once. */
  readonly workers: number | undefined;
};

/**
 * Port, artifacts directory and workers of an E2E run (ADR 0010, section 6). The main checkout
 * keeps 5175; lane `l<n>` gets 5180 + n and `test-results/l<n>`. Explicit variables win.
 */
export function laneDefaults(
  appDirectory: string,
  env: { readonly E2E_PORT?: string | undefined; readonly E2E_OUTPUT_DIR?: string | undefined },
): LaneDefaults {
  const lane = laneOf(appDirectory);
  return {
    port: Number(env.E2E_PORT ?? (lane === null ? 5175 : 5180 + lane)),
    outputDir: env.E2E_OUTPUT_DIR ?? (lane === null ? "test-results" : `test-results/l${lane}`),
    workers: lane === null ? undefined : 1,
  };
}
