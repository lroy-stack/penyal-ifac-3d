export type PageLifecycleActions = {
  /** Pause rendering and simulation; the page may be resumed from the back/forward cache. */
  readonly suspend: () => void;
  /** Resume rendering after a back/forward cache restore. */
  readonly resume: () => void;
  /** Release the renderer, loaders and listeners; the page is really going away. */
  readonly dispose: () => void;
};

export type PageLifecycleHandlers = {
  readonly onPageHide: (event: { readonly persisted: boolean }) => void;
  readonly onPageShow: (event: { readonly persisted: boolean }) => void;
};

/**
 * `pagehide` fires both when the page is unloaded and when it enters the bfcache. Disposing the
 * renderer in the second case leaves a frozen canvas after Back (iOS Safari), so the page is
 * only suspended there and resumed on `pageshow`. `pageshow` also fires on the initial load
 * (persisted = false), which must not restart anything.
 */
export function createPageLifecycle(actions: PageLifecycleActions): PageLifecycleHandlers {
  return {
    onPageHide: (event) => {
      if (event.persisted) actions.suspend();
      else {
        actions.suspend();
        actions.dispose();
      }
    },
    onPageShow: (event) => {
      if (event.persisted) actions.resume();
    },
  };
}
