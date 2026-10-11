import { attachKeyboard } from "./keyboard";
import { attachPointerLook } from "./pointerLook";
import { InputHub } from "./state";
import { attachTouch } from "./touch";

export type { InputState } from "./state";

export type InputHandle = {
  readonly hub: InputHub;
  readonly dispose: () => void;
};

/** Wires keyboard, mouse (Pointer Lock) and touch adapters to one InputHub. */
export function createInput(canvas: HTMLCanvasElement): InputHandle {
  const hub = new InputHub();
  const disposers = [attachKeyboard(hub), attachPointerLook(hub, canvas), attachTouch(hub, canvas)];
  return {
    hub,
    dispose: () => {
      for (const dispose of disposers) dispose();
    },
  };
}
