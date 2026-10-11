import {
  dragToLookDelta,
  JOYSTICK_MAX_RADIUS_PX,
  joystickToMove,
  TOUCH_SENSITIVITY,
} from "./mapping";
import type { InputHub } from "./state";

type Origin = { readonly id: number; readonly x: number; readonly y: number };
type LookPointer = { readonly id: number; x: number; y: number };

const CAMERA_BUTTON_LABEL = "Cambiar cámara";

function styled<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  css: string,
  parent: HTMLElement,
): HTMLElementTagNameMap[K] {
  const element = document.createElement(tag);
  element.style.cssText = css;
  parent.append(element);
  return element;
}

/**
 * Touch controls: left half of the canvas is a floating virtual joystick (max radius 60 px,
 * 10 % dead zone), right half is drag-to-look, plus a visible camera-toggle button.
 */
export function attachTouch(hub: InputHub, canvas: HTMLCanvasElement): () => void {
  const host = canvas.parentElement ?? document.body;
  canvas.style.touchAction = "none";

  const overlay = styled("div", "position:fixed;inset:0;pointer-events:none;z-index:10;", host);
  overlay.dataset.touchControls = "true";
  const base = styled(
    "div",
    `position:absolute;display:none;width:${JOYSTICK_MAX_RADIUS_PX * 2}px;height:${JOYSTICK_MAX_RADIUS_PX * 2}px;` +
      "margin:-60px 0 0 -60px;border:2px solid rgb(255 255 255 / 0.6);border-radius:50%;background:rgb(255 255 255 / 0.12);",
    overlay,
  );
  const thumb = styled(
    "div",
    "position:absolute;left:50%;top:50%;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;background:rgb(255 255 255 / 0.55);",
    base,
  );
  const button = styled(
    "button",
    "position:absolute;right:max(1rem,env(safe-area-inset-right));bottom:max(1rem,env(safe-area-inset-bottom));" +
      "width:56px;height:56px;border:2px solid rgb(255 255 255 / 0.8);border-radius:50%;" +
      "background:rgb(0 0 0 / 0.5);color:#fff;font:600 1.5rem/1 system-ui,sans-serif;pointer-events:auto;touch-action:none;",
    overlay,
  );
  button.type = "button";
  button.textContent = "\u{1F4F7}";
  button.setAttribute("aria-label", CAMERA_BUTTON_LABEL);
  button.dataset.action = "toggle-camera";
  button.style.display = navigator.maxTouchPoints > 0 ? "block" : "none";

  let joystick: Origin | null = null;
  let look: LookPointer | null = null;

  const showTouchControls = (): void => {
    button.style.display = "block";
  };

  const onPointerDown = (event: PointerEvent): void => {
    if (event.pointerType !== "touch") return;
    showTouchControls();
    canvas.setPointerCapture(event.pointerId);
    const rect = canvas.getBoundingClientRect();
    const leftHalf = event.clientX - rect.left < rect.width / 2;
    if (leftHalf && joystick === null) {
      joystick = { id: event.pointerId, x: event.clientX, y: event.clientY };
      base.style.left = `${event.clientX}px`;
      base.style.top = `${event.clientY}px`;
      base.style.display = "block";
      thumb.style.transform = "translate(0, 0)";
    } else if (!leftHalf && look === null) {
      look = { id: event.pointerId, x: event.clientX, y: event.clientY };
    }
  };

  const onPointerMove = (event: PointerEvent): void => {
    if (joystick !== null && event.pointerId === joystick.id) {
      const dx = event.clientX - joystick.x;
      const dy = event.clientY - joystick.y;
      hub.touchMove = joystickToMove(dx, dy);
      const distance = Math.hypot(dx, dy);
      const scale = distance > JOYSTICK_MAX_RADIUS_PX ? JOYSTICK_MAX_RADIUS_PX / distance : 1;
      thumb.style.transform = `translate(${dx * scale}px, ${dy * scale}px)`;
    } else if (look !== null && event.pointerId === look.id) {
      const delta = dragToLookDelta(
        event.clientX - look.x,
        event.clientY - look.y,
        TOUCH_SENSITIVITY,
      );
      hub.addLook(delta.yaw, delta.pitch);
      look.x = event.clientX;
      look.y = event.clientY;
    }
  };

  const onPointerEnd = (event: PointerEvent): void => {
    if (joystick !== null && event.pointerId === joystick.id) {
      joystick = null;
      hub.touchMove = { x: 0, y: 0 };
      base.style.display = "none";
    } else if (look !== null && event.pointerId === look.id) {
      look = null;
    }
  };

  const onButtonClick = (): void => hub.requestToggleCamera();

  canvas.addEventListener("pointerdown", onPointerDown);
  canvas.addEventListener("pointermove", onPointerMove);
  canvas.addEventListener("pointerup", onPointerEnd);
  canvas.addEventListener("pointercancel", onPointerEnd);
  button.addEventListener("click", onButtonClick);

  return () => {
    canvas.removeEventListener("pointerdown", onPointerDown);
    canvas.removeEventListener("pointermove", onPointerMove);
    canvas.removeEventListener("pointerup", onPointerEnd);
    canvas.removeEventListener("pointercancel", onPointerEnd);
    button.removeEventListener("click", onButtonClick);
    hub.touchMove = { x: 0, y: 0 };
    overlay.remove();
  };
}
