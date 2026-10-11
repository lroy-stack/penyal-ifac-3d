import type { Corridor, Enclosure, GroundSurface, HeightField } from "../world/ground";

/** Capsule radius (m). */
export const CAPSULE_RADIUS = 0.3;
/** Capsule height (m); the eye sits 0.1 m below its top. */
export const CAPSULE_HEIGHT = 1.7;
/** Eye height above the feet (m). */
export const EYE_HEIGHT = 1.6;
/** Walking speed (m/s). */
export const WALK_SPEED = 1.4;
/** Running speed (m/s). */
export const RUN_SPEED = 2.6;
/** Highest rise (m) the player steps up in one go; the trail has stone steps. */
export const STEP_HEIGHT = 0.4;
/** Steepest walkable slope (degrees). */
export const MAX_SLOPE_DEG = 50;
/** Gravity (m/s^2). */
export const GRAVITY = 9.81;
/** Descending ground within this distance (m) below the feet is followed, not fallen from. */
export const SNAP_DISTANCE = 0.5;
/** Largest simulation step (s); longer frames are split so behaviour is frame-rate independent. */
export const MAX_SUBSTEP = 1 / 30;
/** A frame longer than this (s) is treated as a stall and truncated. */
export const MAX_FRAME_DT = 0.25;
/**
 * How far ahead (m) the slope probe looks: the distance over which a rise of STEP_HEIGHT equals
 * the maximum slope. Anything that climbs more than a step within it is a wall.
 */
export const SLOPE_PROBE_DISTANCE = STEP_HEIGHT / Math.tan((MAX_SLOPE_DEG * Math.PI) / 180);

export type ControllerInput = {
  /** Strafe right (+1) / left (-1). */
  readonly moveX: number;
  /** Forward (+1) / backward (-1). */
  readonly moveY: number;
  readonly run: boolean;
  /** Camera yaw (rad, 0 looks along -Z, positive turns left). */
  readonly yaw: number;
};

export type ControllerState = {
  /** Feet position. */
  x: number;
  y: number;
  z: number;
  vy: number;
  grounded: boolean;
  /** True when the corridor altered the motion during the last update (for the UI message). */
  corridorHit: boolean;
};

export type ControllerOptions = {
  readonly heightField: HeightField;
  readonly groundSurfaces: readonly GroundSurface[];
  /**
   * Volumes that are hollow in reality although the height field fills them (the DEM knows the
   * rock over the tunnel, not the tunnel): height-field points inside them are not ground.
   */
  readonly hollows?: readonly Enclosure[];
  readonly corridor: Corridor;
  /** Feet start; when `y` is omitted the player starts on the height field. */
  readonly start: { readonly x: number; readonly z: number; readonly y?: number };
};

/**
 * Kinematic walker (no physics engine). Ground under (x, z) is the highest of the height field
 * and the ground surfaces that is not higher than feet + STEP_HEIGHT. A spot with no such ground
 * (terrain more than a step up and nothing walkable there, or outside the height field) is a
 * wall. A height-field point inside a hollow (the tunnel volume) is not ground at all. This is what lets the player walk in a tunnel whose rock roof is part of the height
 * field: the tunnel floor supports the player, the roof is ignored.
 */
export class PlayerController {
  readonly state: ControllerState;
  private readonly heightField: HeightField;
  private readonly groundSurfaces: readonly GroundSurface[];
  private readonly hollows: readonly Enclosure[];
  private readonly corridor: Corridor;

  constructor(options: ControllerOptions) {
    this.heightField = options.heightField;
    this.groundSurfaces = options.groundSurfaces;
    this.hollows = options.hollows ?? [];
    this.corridor = options.corridor;
    const startY =
      options.start.y ?? options.heightField.heightAt(options.start.x, options.start.z);
    if (startY === null) {
      throw new Error(
        `Player start (${options.start.x}, ${options.start.z}) is outside the height field.`,
      );
    }
    this.state = {
      x: options.start.x,
      y: startY,
      z: options.start.z,
      vy: 0,
      grounded: false,
      corridorHit: false,
    };
    this.settle();
  }

  update(dt: number, input: ControllerInput): void {
    const frame = Math.min(Math.max(dt, 0), MAX_FRAME_DT);
    if (frame === 0) return;
    const steps = Math.ceil(frame / MAX_SUBSTEP);
    const h = frame / steps;
    this.state.corridorHit = false;
    for (let i = 0; i < steps; i++) this.step(h, input);
  }

  /** Highest supporting ground at (x, z) for feet at feetY, or null when it is a wall or off-map. */
  private groundAt(x: number, z: number, feetY: number, surfaceDrop: number): number | null {
    const terrain = this.heightField.heightAt(x, z);
    if (terrain === null) return null;
    const reach = feetY + STEP_HEIGHT;
    const solid = terrain <= reach && !this.hollows.some((h) => h.contains(x, terrain, z, 0));
    let best = solid ? terrain : Number.NEGATIVE_INFINITY;
    for (const surface of this.groundSurfaces) {
      const height = surface.surfaceBelow(x, reach, z, STEP_HEIGHT + surfaceDrop);
      if (height !== null && height > best) best = height;
    }
    return best === Number.NEGATIVE_INFINITY ? null : best;
  }

  /** Whether the feet can be at (x, z) coming from direction (dirX, dirZ) at height feetY. */
  private walkable(x: number, z: number, feetY: number, dirX: number, dirZ: number): boolean {
    const here = this.groundAt(x, z, feetY, SNAP_DISTANCE);
    if (here === null) return false;
    const standY = Math.max(here, feetY - SNAP_DISTANCE);
    const length = Math.hypot(dirX, dirZ);
    if (length === 0) return true;
    const ahead = this.groundAt(
      x + (dirX / length) * SLOPE_PROBE_DISTANCE,
      z + (dirZ / length) * SLOPE_PROBE_DISTANCE,
      standY,
      SNAP_DISTANCE,
    );
    return ahead !== null;
  }

  private tryMove(dx: number, dz: number): boolean {
    const s = this.state;
    const target = this.corridor.clamp(s.x, s.z, s.x + dx, s.z + dz);
    if (target.x !== s.x + dx || target.z !== s.z + dz) s.corridorHit = true;
    const mx = target.x - s.x;
    const mz = target.z - s.z;
    if (mx === 0 && mz === 0) return false;
    if (!this.walkable(target.x, target.z, s.y, mx, mz)) return false;
    s.x = target.x;
    s.z = target.z;
    return true;
  }

  private step(h: number, input: ControllerInput): void {
    const length = Math.hypot(input.moveX, input.moveY);
    if (length > 0) {
      const scale = Math.min(length, 1) / length;
      const strafe = input.moveX * scale;
      const forward = input.moveY * scale;
      const speed = (input.run ? RUN_SPEED : WALK_SPEED) * h;
      const sin = Math.sin(input.yaw);
      const cos = Math.cos(input.yaw);
      const dx = (strafe * cos - forward * sin) * speed;
      const dz = (-strafe * sin - forward * cos) * speed;
      // Full move first; when a wall blocks it, slide along each axis in turn.
      if (!this.tryMove(dx, dz)) {
        this.tryMove(dx, 0);
        this.tryMove(0, dz);
      }
    }
    this.applyVertical(h);
  }

  private applyVertical(h: number): void {
    const s = this.state;
    if (s.grounded) {
      const ground = this.groundAt(s.x, s.z, s.y, SNAP_DISTANCE);
      if (ground !== null && ground >= s.y - SNAP_DISTANCE) {
        s.y = ground;
        s.vy = 0;
        return;
      }
      s.grounded = false;
      s.vy = 0;
    }
    s.vy -= GRAVITY * h;
    const nextY = s.y + s.vy * h;
    const ground = this.groundAt(s.x, s.z, s.y, Math.max(0, s.y - nextY));
    if (ground !== null && nextY <= ground) {
      s.y = ground;
      s.vy = 0;
      s.grounded = true;
    } else {
      s.y = nextY;
    }
  }

  /** Drops the player onto the ground below the start without simulating a long fall. */
  private settle(): void {
    for (let i = 0; i < 600 && !this.state.grounded; i++) this.applyVertical(MAX_SUBSTEP);
  }
}
