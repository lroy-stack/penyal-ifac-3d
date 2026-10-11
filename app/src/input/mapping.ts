/** Pure input mapping: no DOM, no three. Adapters feed these functions. */

export type MoveVector = { readonly x: number; readonly y: number };
export type LookDelta = { readonly yaw: number; readonly pitch: number };
export type Look = { readonly yaw: number; readonly pitch: number };

/** Move axes: x = strafe right (+), y = forward (+). */
export const KEY_CODES = {
  forward: ["KeyW", "ArrowUp"],
  backward: ["KeyS", "ArrowDown"],
  left: ["KeyA", "KeyQ"],
  right: ["KeyD", "KeyE"],
  turnLeft: ["ArrowLeft"],
  turnRight: ["ArrowRight"],
  run: ["ShiftLeft", "ShiftRight"],
  toggleCamera: ["KeyC"],
  interact: ["KeyF"],
  toggleAutoWalk: ["KeyP"],
} as const;

/** `event.code` is the physical key, so WASD works on AZERTY and QWERTZ layouts. */
export function isKeyCode(group: readonly string[], code: string): boolean {
  return group.includes(code);
}

export function isHandledKeyCode(code: string): boolean {
  return Object.values(KEY_CODES).some((group) => isKeyCode(group, code));
}

function anyPressed(pressed: ReadonlySet<string>, group: readonly string[]): boolean {
  return group.some((code) => pressed.has(code));
}

/** Pressed key codes to a move vector; diagonals are normalised to length 1. */
export function keysToMove(pressed: ReadonlySet<string>): MoveVector {
  const x =
    (anyPressed(pressed, KEY_CODES.right) ? 1 : 0) - (anyPressed(pressed, KEY_CODES.left) ? 1 : 0);
  const y =
    (anyPressed(pressed, KEY_CODES.forward) ? 1 : 0) -
    (anyPressed(pressed, KEY_CODES.backward) ? 1 : 0);
  const length = Math.hypot(x, y);
  return length === 0 ? { x: 0, y: 0 } : { x: x / length, y: y / length };
}

/** Keyboard turn: +1 turns left (positive yaw), -1 right; opposite keys cancel. */
export function keysToTurn(pressed: ReadonlySet<string>): number {
  return (
    (anyPressed(pressed, KEY_CODES.turnLeft) ? 1 : 0) -
    (anyPressed(pressed, KEY_CODES.turnRight) ? 1 : 0)
  );
}

/** Full-speed keyboard turn (rad/s); the player takes it as an option so it can be changed. */
export const TURN_RATE = (90 * Math.PI) / 180;
/** Time constant (s) with which the turn speed follows the keys, so a tap is not a jolt. */
export const TURN_SMOOTH_TIME = 0.1;

/**
 * Exponential approach of the turn speed (fraction of full rate, -1..1) to the key target. The
 * factor depends on `dt` only through exp(-dt / smoothTime), so the result does not depend on
 * how the time is split into frames.
 */
export function smoothTurn(
  current: number,
  target: number,
  dt: number,
  smoothTime: number = TURN_SMOOTH_TIME,
): number {
  if (dt <= 0) return current;
  if (smoothTime <= 0) return target;
  return target + (current - target) * Math.exp(-dt / smoothTime);
}

/**
 * One frame of keyboard turning: the new turn speed (fraction of `rate`) and the yaw change in
 * radians over `dt`, integrating the speed with the trapezoid rule so frame splitting hardly
 * matters.
 */
export function stepKeyboardTurn(
  velocity: number,
  target: number,
  dt: number,
  rate: number = TURN_RATE,
): { velocity: number; yawDelta: number } {
  const next = smoothTurn(velocity, target, dt);
  return { velocity: next, yawDelta: ((velocity + next) / 2) * rate * Math.max(dt, 0) };
}

export const JOYSTICK_MAX_RADIUS_PX = 60;
export const JOYSTICK_DEAD_ZONE = 0.1;

/**
 * Joystick displacement in screen pixels (dy positive = down) to a move vector. Inside the dead
 * zone (fraction of the max radius) the output is zero; outside it ramps from 0 to 1 so there is
 * no jump at the dead-zone edge.
 */
export function joystickToMove(
  dxPx: number,
  dyPx: number,
  maxRadiusPx: number = JOYSTICK_MAX_RADIUS_PX,
  deadZone: number = JOYSTICK_DEAD_ZONE,
): MoveVector {
  const distance = Math.hypot(dxPx, dyPx);
  if (distance === 0) return { x: 0, y: 0 };
  const fraction = Math.min(distance / maxRadiusPx, 1);
  if (fraction < deadZone) return { x: 0, y: 0 };
  const strength = (fraction - deadZone) / (1 - deadZone);
  return { x: (dxPx / distance) * strength, y: (-dyPx / distance) * strength };
}

export const MOUSE_SENSITIVITY = 0.0022;
export const TOUCH_SENSITIVITY = 0.005;
export const MAX_PITCH = (85 * Math.PI) / 180;

/** Pointer drag in pixels to yaw/pitch deltas in radians (drag right turns right, down looks down). */
export function dragToLookDelta(dxPx: number, dyPx: number, sensitivity: number): LookDelta {
  return { yaw: -dxPx * sensitivity, pitch: -dyPx * sensitivity };
}

export function applyLookDelta(look: Look, delta: LookDelta): Look {
  return {
    yaw: look.yaw + delta.yaw,
    pitch: Math.max(-MAX_PITCH, Math.min(MAX_PITCH, look.pitch + delta.pitch)),
  };
}

/** Sum of the active sources, clamped to the unit disc. */
export function combineMoves(...moves: readonly MoveVector[]): MoveVector {
  const x = moves.reduce((sum, move) => sum + move.x, 0);
  const y = moves.reduce((sum, move) => sum + move.y, 0);
  const length = Math.hypot(x, y);
  return length > 1 ? { x: x / length, y: y / length } : { x, y };
}
