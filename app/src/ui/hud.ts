import { CORRIDOR_VISIBLE_MS, CorridorNotice, HINT_DURATION_MS } from "./notices";

function requireElement(id: string): HTMLElement {
  const element = document.getElementById(id);
  if (element === null) throw new Error(`index.html is missing the #${id} element.`);
  return element;
}

export type Hud = {
  /** Shows the first-time controls hint for 3 s, or until the first key press or pointer down. */
  readonly showHints: (text: string) => void;
  /** Call every frame with whether the corridor limited the player; shows the notice when due. */
  readonly update: (corridorHit: boolean, nowMs: number, corridorText: string) => void;
  /** Shows a short message in the polite live region at the top; null clears it. */
  readonly notify: (text: string | null, durationMs?: number) => void;
  readonly dispose: () => void;
};

function show(element: HTMLElement, text: string): void {
  element.textContent = text;
  element.dataset.visible = "true";
}

function hide(element: HTMLElement): void {
  element.dataset.visible = "false";
}

/**
 * Two small polite live regions (`role="status"`, both in index.html): the first-time hints at
 * the bottom and the notices (corridor rule, "getting the walk ready") at the top. Neither takes
 * pointer events, neither animates for visitors who prefer reduced motion (the CSS only fades
 * under `prefers-reduced-motion: no-preference`).
 */
export function createHud(): Hud {
  const hints = requireElement("hints");
  const notice = requireElement("notice");
  const corridor = new CorridorNotice();
  let hintTimer: number | undefined;
  let noticeTimer: number | undefined;
  let removeDismiss: (() => void) | null = null;

  const dismissHints = (): void => {
    window.clearTimeout(hintTimer);
    removeDismiss?.();
    removeDismiss = null;
    hide(hints);
  };

  const notify = (text: string | null, durationMs?: number): void => {
    window.clearTimeout(noticeTimer);
    if (text === null) {
      hide(notice);
      return;
    }
    show(notice, text);
    if (durationMs !== undefined) {
      noticeTimer = window.setTimeout(() => hide(notice), durationMs);
    }
  };

  return {
    showHints: (text) => {
      dismissHints();
      show(hints, text);
      const onInput = (): void => dismissHints();
      window.addEventListener("keydown", onInput);
      window.addEventListener("pointerdown", onInput);
      removeDismiss = () => {
        window.removeEventListener("keydown", onInput);
        window.removeEventListener("pointerdown", onInput);
      };
      hintTimer = window.setTimeout(dismissHints, HINT_DURATION_MS);
    },
    update: (corridorHit, nowMs, corridorText) => {
      if (corridor.update(corridorHit, nowMs)) notify(corridorText, CORRIDOR_VISIBLE_MS);
    },
    notify,
    dispose: () => {
      dismissHints();
      window.clearTimeout(noticeTimer);
    },
  };
}
