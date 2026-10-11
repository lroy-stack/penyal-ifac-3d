import { describe, expect, it } from "vitest";
import {
  applyLookDelta,
  combineMoves,
  dragToLookDelta,
  joystickToMove,
  keysToMove,
  MAX_PITCH,
} from "./mapping";

describe("keysToMove", () => {
  it("is zero with no keys and with opposite keys", () => {
    expect(keysToMove(new Set())).toEqual({ x: 0, y: 0 });
    expect(keysToMove(new Set(["KeyW", "KeyS"]))).toEqual({ x: 0, y: 0 });
  });

  it("maps WASD and arrows by physical key code", () => {
    expect(keysToMove(new Set(["KeyW"]))).toEqual({ x: 0, y: 1 });
    expect(keysToMove(new Set(["ArrowDown"]))).toEqual({ x: 0, y: -1 });
    expect(keysToMove(new Set(["KeyA"]))).toEqual({ x: -1, y: 0 });
    expect(keysToMove(new Set(["ArrowRight"]))).toEqual({ x: 1, y: 0 });
  });

  it("normalises diagonals so they are not faster", () => {
    const move = keysToMove(new Set(["KeyW", "KeyD"]));
    expect(Math.hypot(move.x, move.y)).toBeCloseTo(1, 12);
    expect(move.x).toBeCloseTo(Math.SQRT1_2, 12);
  });

  it("treats WASD and arrows as the same axis", () => {
    expect(keysToMove(new Set(["KeyW", "ArrowUp"]))).toEqual({ x: 0, y: 1 });
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
