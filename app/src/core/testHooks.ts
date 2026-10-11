type HookEnv = { readonly DEV: boolean; readonly VITE_E2E?: string | undefined };

/** Pure rule behind `TEST_HOOKS_ENABLED`, separate so it can be tested with any environment. */
export function testHooksEnabled(env: HookEnv): boolean {
  return env.DEV || env.VITE_E2E === "true";
}

/**
 * `window.__appState` and `?timescale=N` exist to drive the app from Playwright. They are on in
 * the dev server and in builds made with `VITE_E2E=true`, and never in a normal production
 * build. The expression is written out so the bundler replaces both variables and drops the
 * hook code from a normal build.
 */
export const TEST_HOOKS_ENABLED: boolean =
  import.meta.env.DEV || import.meta.env.VITE_E2E === "true";
