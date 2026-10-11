import { describe, expect, it } from "vitest";
import {
  applyLookDelta,
  combineMoves,
  dragToLookDelta,
  isHandledKeyCode,
  joystickToMove,
  KEY_CODES,
  keysToMove,
  keysToTurn,
  MAX_PITCH,
  smoothTurn,
  stepKeyboardTurn,
  TURN_RATE,
  TURN_SMOOTH_TIME,
} from "./mapping";

describe("keysToMove", () => {
  it("is zero with no keys and with opposite keys", () => {
    expect(keysToMove(new Set())).toEqual({ x: 0, y: 0 });
    expect(keysToMove(new Set(["KeyW", "KeyS"]))).toEqual({ x: 0, y: 0 });
  });

  it("maps W/S and Up/Down to forward and backward, A/Q and D/E to strafing", () => {
    expect(keysToMove(new Set(["KeyW"]))).toEqual({ x: 0, y: 1 });
    expect(keysToMove(new Set(["ArrowUp"]))).toEqual({ x: 0, y: 1 });
    expect(keysToMove(new Set(["ArrowDown"]))).toEqual({ x: 0, y: -1 });
    expect(keysToMove(new Set(["KeyA"]))).toEqual({ x: -1, y: 0 });
    expect(keysToMove(new Set(["KeyQ"]))).toEqual({ x: -1, y: 0 });
    expect(keysToMove(new Set(["KeyD"]))).toEqual({ x: 1, y: 0 });
    expect(keysToMove(new Set(["KeyE"]))).toEqual({ x: 1, y: 0 });
  });

  it("does not strafe with the left and right arrows: they turn", () => {
    expect(keysToMove(new Set(["ArrowLeft"]))).toEqual({ x: 0, y: 0 });
    expect(keysToMove(new Set(["ArrowRight"]))).toEqual({ x: 0, y: 0 });
  });

  it("normalises diagonals so they are not faster", () => {
    const move = keysToMove(new Set(["KeyW", "KeyD"]));
    expect(Math.hypot(move.x, move.y)).toBeCloseTo(1, 12);
    expect(move.x).toBeCloseTo(Math.SQRT1_2, 12);
  });

  it("treats WASD and arrows as the same axis", () => {
    expect(keysToMove(new Set(["KeyW", "ArrowUp"]))).toEqual({ x: 0, y: 1 });
    expect(keysToMove(new Set(["KeyA", "KeyQ"]))).toEqual({ x: -1, y: 0 });
  });
});

describe("keysToTurn", () => {
  it("turns left (positive yaw) with ArrowLeft and right with ArrowRight", () => {
    expect(keysToTurn(new Set(["ArrowLeft"]))).toBe(1);
    expect(keysToTurn(new Set(["ArrowRight"]))).toBe(-1);
  });

  it("is zero with no keys, with both arrows and with unrelated keys", () => {
    expect(keysToTurn(new Set())).toBe(0);
    expect(keysToTurn(new Set(["ArrowLeft", "ArrowRight"]))).toBe(0);
    expect(keysToTurn(new Set(["KeyA", "KeyQ", "KeyW"]))).toBe(0);
  });
});

describe("smoothTurn", () => {
  it("accelerates towards the target without overshooting", () => {
    let velocity = 0;
    const history: number[] = [];
    for (let i = 0; i < 30; i++) {
      velocity = smoothTurn(velocity, 1, 1 / 60, TURN_SMOOTH_TIME);
      history.push(velocity);
    }
    expect(history[0]).toBeGreaterThan(0);
    expect(history[0]).toBeLessThan(0.3);
    expect(history.every((v, i) => i === 0 || v >= (history[i - 1] as number))).toBe(true);
    expect(Math.max(...history)).toBeLessThanOrEqual(1);
    expect(history[29]).toBeGreaterThan(0.95);
  });

  it("stops smoothly and reaches rest", () => {
    let velocity = 1;
    for (let i = 0; i < 120; i++) velocity = smoothTurn(velocity, 0, 1 / 60, TURN_SMOOTH_TIME);
    expect(velocity).toBeCloseTo(0, 6);
  });

  it("gives the same velocity whether a second is one step or sixty", () => {
    let stepped = 0;
    for (let i = 0; i < 60; i++) stepped = smoothTurn(stepped, 1, 1 / 60, TURN_SMOOTH_TIME);
    expect(smoothTurn(0, 1, 1, TURN_SMOOTH_TIME)).toBeCloseTo(stepped, 10);
  });

  it("snaps when the smoothing time is zero and ignores a non-positive step", () => {
    expect(smoothTurn(0, 1, 1 / 60, 0)).toBe(1);
    expect(smoothTurn(0.4, 1, 0, TURN_SMOOTH_TIME)).toBe(0.4);
  });
});

describe("stepKeyboardTurn", () => {
  const turnFor = (seconds: number, frame: number, target: number, rate = TURN_RATE) => {
    let velocity = 0;
    let yaw = 0;
    for (let t = 0; t < seconds - 1e-9; t += frame) {
      const step = stepKeyboardTurn(velocity, target, frame, rate);
      velocity = step.velocity;
      yaw += step.yawDelta;
    }
    return yaw;
  };

  it("turns at the configured rate once up to speed", () => {
    const settled = turnFor(3, 1 / 60, 1) - turnFor(2, 1 / 60, 1);
    expect(settled).toBeCloseTo(TURN_RATE, 2);
    expect(turnFor(3, 1 / 60, 1, Math.PI) - turnFor(2, 1 / 60, 1, Math.PI)).toBeCloseTo(Math.PI, 2);
  });

  it("turns the other way for a negative target and not at all for zero", () => {
    expect(turnFor(1, 1 / 60, -1)).toBeLessThan(0);
    expect(turnFor(1, 1 / 60, 0)).toBe(0);
  });

  it("covers nearly the same angle at 30 and 60 frames per second", () => {
    expect(turnFor(1, 1 / 30, 1)).toBeCloseTo(turnFor(1, 1 / 60, 1), 1);
  });
});

describe("key groups", () => {
  it("turn at a configurable base rate of 90 degrees per second", () => {
    expect(TURN_RATE).toBeCloseTo(Math.PI / 2, 12);
  });

  it("keeps E for strafing: interaction moved to F so no key does two things", () => {
    expect(KEY_CODES.interact).toEqual(["KeyF"]);
    expect(isHandledKeyCode("KeyE")).toBe(true);
    expect(isHandledKeyCode("ArrowLeft")).toBe(true);
    expect(isHandledKeyCode("Enter")).toBe(false);
    expect(isHandledKeyCode("Tab")).toBe(false);
  });
});

describe("joystickToMove", () => {
  it("ignores displacements inside the 10 % dead zone", () => {
    expect(joystickToMove(5, 0)).toEqual({ x: 0, y: 0 });
    expect(joystickToMove(0, -5.9)).toEqual({ x: 0, y: 0 });
  });

  it("maps screen up to forward at full strength from the max radius", () => {
    const move = joystickToMove(0, -60);
    expect(move.x).toBeCloseTo(0, 12);
    expect(move.y).toBeCloseTo(1, 12);
  });

  it("saturates beyond the max radius and keeps the direction", () => {
    const move = joystickToMove(300, 0);
    expect(move.x).toBeCloseTo(1, 12);
    expect(move.y).toBeCloseTo(0, 12);
  });

  it("ramps from zero at the dead-zone edge", () => {
    const move = joystickToMove(0, -33);
    expect(move.y).toBeCloseTo((0.55 - 0.1) / 0.9, 12);
  });

  it("maps screen down to backward", () => {
    expect(joystickToMove(0, 60).y).toBeCloseTo(-1, 12);
  });
});

describe("look mapping", () => {
  it("turns right when dragging right and looks down when dragging down", () => {
    const delta = dragToLookDelta(100, 50, 0.01);
    expect(delta.yaw).toBeCloseTo(-1, 12);
    expect(delta.pitch).toBeCloseTo(-0.5, 12);
  });

  it("clamps pitch to plus/minus 85 degrees and leaves yaw unbounded", () => {
    const up = applyLookDelta({ yaw: 0, pitch: 0 }, { yaw: 7, pitch: 10 });
    expect(up.pitch).toBe(MAX_PITCH);
    expect(up.yaw).toBe(7);
    expect(applyLookDelta(up, { yaw: 0, pitch: -100 }).pitch).toBe(-MAX_PITCH);
    expect(MAX_PITCH).toBeCloseTo((85 * Math.PI) / 180, 12);
  });
});

describe("combineMoves", () => {
  it("clamps the sum to the unit disc", () => {
    const move = combineMoves({ x: 1, y: 0 }, { x: 0, y: 1 });
    expect(Math.hypot(move.x, move.y)).toBeCloseTo(1, 12);
    expect(combineMoves({ x: 0.2, y: 0 }, { x: 0, y: 0.3 })).toEqual({ x: 0.2, y: 0.3 });
  });
});
