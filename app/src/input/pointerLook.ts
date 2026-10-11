import { dragToLookDelta, MOUSE_SENSITIVITY } from "./mapping";
import type { InputHub } from "./state";

/** A mouse press that moves further than this (px) is a drag, not a click. */
const DRAG_THRESHOLD_PX = 4;

/**
 * Mouse look. Dragging with the primary button looks around right away, with no Pointer Lock
 * and no permission prompt. Pointer Lock stays available and optional: a plain click (no drag)
 * on the canvas requests it, and while it is held the mouse looks without a button; Escape
 * releases it (handled by the browser). Touch is handled by `attachTouch`, so touch pointers
 * are ignored here.
 */
export function attachPointerLook(hub: InputHub, canvas: HTMLCanvasElement): () => void {
  let drag: { id: number; x: number; y: number; travelled: number } | null = null;
  let suppressClick = false;

  const onPointerDown = (event: PointerEvent): void => {
    if (event.pointerType !== "mouse" || event.button !== 0) return;
    if (document.pointerLockElement === canvas) return;
    drag = { id: event.pointerId, x: event.clientX, y: event.clientY, travelled: 0 };
    suppressClick = false;
    canvas.setPointerCapture(event.pointerId);
  };
  const onPointerMove = (event: PointerEvent): void => {
    if (drag === null || event.pointerId !== drag.id) return;
    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    drag.x = event.clientX;
    drag.y = event.clientY;
    drag.travelled += Math.hypot(dx, dy);
    if (drag.travelled <= DRAG_THRESHOLD_PX) return;
    suppressClick = true;
    const delta = dragToLookDelta(dx, dy, MOUSE_SENSITIVITY);
    hub.addLook(delta.yaw, delta.pitch);
  };
  const onPointerEnd = (event: PointerEvent): void => {
    if (drag !== null && event.pointerId === drag.id) drag = null;
  };
  const onClick = (event: MouseEvent): void => {
    if (event instanceof PointerEvent && event.pointerType !== "mouse") return;
    if (suppressClick) {
      suppressClick = false;
      return;
    }
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

  canvas.addEventListener("pointerdown", onPointerDown);
  canvas.addEventListener("pointermove", onPointerMove);
  canvas.addEventListener("pointerup", onPointerEnd);
  canvas.addEventListener("pointercancel", onPointerEnd);
  canvas.addEventListener("click", onClick);
  document.addEventListener("mousemove", onMouseMove);
  return () => {
    canvas.removeEventListener("pointerdown", onPointerDown);
    canvas.removeEventListener("pointermove", onPointerMove);
    canvas.removeEventListener("pointerup", onPointerEnd);
    canvas.removeEventListener("pointercancel", onPointerEnd);
    canvas.removeEventListener("click", onClick);
    document.removeEventListener("mousemove", onMouseMove);
    if (document.pointerLockElement === canvas) document.exitPointerLock();
  };
}
