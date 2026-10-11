import { describe, expect, it } from "vitest";
import { InputHub } from "./state";

describe("InputHub", () => {
  it("accumulates look deltas and clears them once consumed", () => {
    const hub = new InputHub();
    hub.addLook(0.1, -0.2);
    hub.addLook(0.1, 0.05);
    const first = hub.consume();
    expect(first.lookYaw).toBeCloseTo(0.2, 12);
    expect(first.lookPitch).toBeCloseTo(-0.15, 12);
    expect(hub.consume().lookYaw).toBe(0);
  });

  it("reports one-shot presses for exactly one frame", () => {
    const hub = new InputHub();
    hub.requestToggleCamera();
    hub.requestInteract();
    hub.requestToggleAutoWalk();
    expect(hub.consume()).toMatchObject({
      toggleCamera: true,
      interact: true,
      toggleAutoWalk: true,
    });
    expect(hub.consume()).toMatchObject({
      toggleCamera: false,
      interact: false,
      toggleAutoWalk: false,
    });
  });

  it("merges keyboard and touch movement without exceeding unit length", () => {
    const hub = new InputHub();
    hub.keyboardMove = { x: 0, y: 1 };
    hub.touchMove = { x: 1, y: 0 };
    const input = hub.consume();
    expect(Math.hypot(input.moveX, input.moveY)).toBeCloseTo(1, 12);
  });

  it("keeps held state across frames and drops it on reset", () => {
    const hub = new InputHub();
    hub.keyboardMove = { x: 0, y: 1 };
    hub.run = true;
    expect(hub.consume()).toMatchObject({ moveY: 1, run: true });
    expect(hub.consume()).toMatchObject({ moveY: 1, run: true });
    hub.reset();
    expect(hub.consume()).toMatchObject({ moveY: 0, run: false });
  });
});
