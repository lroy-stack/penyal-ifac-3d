import { isHandledKeyCode, isKeyCode, KEY_CODES, keysToMove } from "./mapping";
import type { InputHub } from "./state";

function isEditable(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
  );
}

/** WASD / arrows, Shift to run, C to toggle the camera, E to interact, P to toggle auto-walk; by `event.code`. */
export function attachKeyboard(hub: InputHub, target: Window = window): () => void {
  const pressed = new Set<string>();

  const sync = (): void => {
    hub.keyboardMove = keysToMove(pressed);
    hub.run = KEY_CODES.run.some((code) => pressed.has(code));
  };

  const onKeyDown = (event: KeyboardEvent): void => {
    if (isEditable(event.target) || event.ctrlKey || event.metaKey || event.altKey) return;
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

  target.addEventListener("keydown", onKeyDown);
  target.addEventListener("keyup", onKeyUp);
  target.addEventListener("blur", onBlur);
  return () => {
    target.removeEventListener("keydown", onKeyDown);
    target.removeEventListener("keyup", onKeyUp);
    target.removeEventListener("blur", onBlur);
    onBlur();
  };
}
