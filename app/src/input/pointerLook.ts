import { dragToLookDelta, MOUSE_SENSITIVITY } from "./mapping";
import type { InputHub } from "./state";

/**
 * Mouse look with Pointer Lock: requested on a mouse click on the canvas, released by Escape
 * (handled by the browser). Touch is handled by `attachTouch`, so touch clicks are ignored here.
 */
export function attachPointerLook(hub: InputHub, canvas: HTMLCanvasElement): () => void {
  const onClick = (event: MouseEvent): void => {
    if (event instanceof PointerEvent && event.pointerType !== "mouse") return;
    if (document.pointerLockElement === canvas) return;
    // The promise rejects when the user leaves lock immediately or the page is not focused; the
    // next click simply tries again.
    Promise.resolve(canvas.requestPointerLock()).catch(() => undefined);
  };

  const onMouseMove = (event: MouseEvent): void => {
    if (document.pointerLockElement !== canvas) return;
    const delta = dragToLookDelta(event.movementX, event.movementY, MOUSE_SENSITIVITY);
    hub.addLook(delta.yaw, delta.pitch);
  };

  canvas.addEventListener("click", onClick);
  document.addEventListener("mousemove", onMouseMove);
  return () => {
    canvas.removeEventListener("click", onClick);
    document.removeEventListener("mousemove", onMouseMove);
    if (document.pointerLockElement === canvas) document.exitPointerLock();
  };
}
