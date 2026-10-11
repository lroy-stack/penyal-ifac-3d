import { isHandledKeyCode, isKeyCode, KEY_CODES, keysToMove, keysToTurn } from "./mapping";
import type { InputHub } from "./state";

function isEditable(target: EventTarget | null): boolean {
  const element = target as { isContentEditable?: boolean; tagName?: string } | null;
  return (
    element?.isContentEditable === true ||
    ["INPUT", "TEXTAREA", "SELECT"].includes(element?.tagName ?? "")
  );
}

/** Tells the keyboard when a modal dialog (the credits) is open, so the keys belong to it. */
export type DialogWatcher = {
  readonly isOpen: () => boolean;
  /** Calls `listener` each time a dialog opens; returns the function that stops watching. */
  readonly onOpen: (listener: () => void) => () => void;
};

/** `<dialog open>` has no open event everywhere, so the `open` attribute is observed. */
export function domDialogWatcher(): DialogWatcher {
  const isOpen = (): boolean => document.querySelector("dialog[open]") !== null;
  return {
    isOpen,
    onOpen: (listener) => {
      const observer = new MutationObserver(() => {
        if (isOpen()) listener();
      });
      observer.observe(document.body, {
        subtree: true,
        attributes: true,
        attributeFilter: ["open"],
      });
      return () => observer.disconnect();
    },
  };
}

/**
 * W/S and Up/Down walk, A/Q and D/E strafe, Left/Right turn, Shift runs, C toggles the camera, F
 * interacts, P toggles auto-walk; by `event.code`.
 */
export function attachKeyboard(
  hub: InputHub,
  target: Pick<Window, "addEventListener" | "removeEventListener"> = window,
  dialogs: DialogWatcher = domDialogWatcher(),
): () => void {
  const pressed = new Set<string>();

  const sync = (): void => {
    hub.keyboardMove = keysToMove(pressed);
    hub.keyboardTurn = keysToTurn(pressed);
    hub.run = KEY_CODES.run.some((code) => pressed.has(code));
  };

  const onKeyDown = (event: KeyboardEvent): void => {
    if (
      isEditable(event.target) ||
      dialogs.isOpen() ||
      event.ctrlKey ||
      event.metaKey ||
      event.altKey
    )
      return;
    if (!isHandledKeyCode(event.code)) return;
    event.preventDefault();
    if (event.repeat) return;
    pressed.add(event.code);
    if (isKeyCode(KEY_CODES.toggleCamera, event.code)) hub.requestToggleCamera();
    if (isKeyCode(KEY_CODES.interact, event.code)) hub.requestInteract();
    if (isKeyCode(KEY_CODES.toggleAutoWalk, event.code)) hub.requestToggleAutoWalk();
    sync();
  };

  const onKeyUp = (event: KeyboardEvent): void => {
    if (!pressed.delete(event.code)) return;
    sync();
  };

  const onBlur = (): void => {
    pressed.clear();
    sync();
  };

  // Keys held when a dialog opens would otherwise keep walking behind it: their keyup goes to the dialog.
  const stopWatching = dialogs.onOpen(onBlur);
  target.addEventListener("keydown", onKeyDown);
  target.addEventListener("keyup", onKeyUp);
  target.addEventListener("blur", onBlur);
  return () => {
    target.removeEventListener("keydown", onKeyDown);
    target.removeEventListener("keyup", onKeyUp);
    target.removeEventListener("blur", onBlur);
    stopWatching();
    onBlur();
  };
}
