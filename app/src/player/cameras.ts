import { Euler, type PerspectiveCamera, Quaternion } from "three";
import type { Look } from "../input/mapping";
import type { Enclosure, GroundSurface, HeightField } from "../world/ground";
import { CAPSULE_HEIGHT, EYE_HEIGHT } from "./controller";

export type Vec3 = { x: number; y: number; z: number };
export type CameraMode = "first" | "third";

/** Third-person camera distance behind the player (m). */
export const THIRD_PERSON_DISTANCE = 4.0;
/** Third-person camera lift above the eye line (m). */
export const THIRD_PERSON_LIFT = 1.2;
/** The camera never goes closer than this to the ground (m). */
export const CAMERA_CLEARANCE = 0.3;
/** Inside an enclosure (the tunnel) the camera keeps this far (m) from its walls and ceiling. */
export const CAMERA_WALL_MARGIN = 0.2;
/** Smoothing time (s) of the first/third-person transition and of camera recovery after a pull-in. */
export const TRANSITION_SMOOTH_TIME = 0.25;
/** Smoothing time (s) of the eye height, which hides step-ups. */
export const EYE_HEIGHT_SMOOTH_TIME = 0.08;

const PULL_IN_SAMPLES = 24;
const PULL_IN_REFINEMENTS = 10;
/** Surfaces this far below the camera are looked up; anything lower cannot hide the player. */
const CAMERA_SURFACE_REACH = 4;

/** Highest ground at-or-below (x, y, z) for camera purposes, or null when there is none. */
export type GroundProbe = (x: number, y: number, z: number) => number | null;

/** First-person eye: EYE_HEIGHT above the feet, 0.1 m below the top of the capsule. */
export function eyePosition(feet: Vec3): Vec3 {
  return { x: feet.x, y: feet.y + EYE_HEIGHT, z: feet.z };
}

/** Unit view direction for a yaw/pitch (yaw 0 looks along -Z, positive yaw turns left). */
export function viewDirection(yaw: number, pitch: number): Vec3 {
  const cosPitch = Math.cos(pitch);
  return { x: -Math.sin(yaw) * cosPitch, y: Math.sin(pitch), z: -Math.cos(yaw) * cosPitch };
}

/** Ideal third-person camera position: behind the view direction, lifted above the eye line. */
export function thirdPersonTarget(eye: Vec3, yaw: number, pitch: number): Vec3 {
  const forward = viewDirection(yaw, pitch);
  return {
    x: eye.x - forward.x * THIRD_PERSON_DISTANCE,
    y: eye.y - forward.y * THIRD_PERSON_DISTANCE + THIRD_PERSON_LIFT,
    z: eye.z - forward.z * THIRD_PERSON_DISTANCE,
  };
}

/**
 * Fraction (0..1) of the eye-to-desired segment the camera may travel before the ground would
 * hide the player. The ray is sampled and the first violation is refined by bisection, so the
 * camera stays at least `clearance` above the ground and, when `allowed` is given, only at
 * points it accepts. 0 means even the eye is too low (or outside).
 */
export function pullInFraction(
  eye: Vec3,
  desired: Vec3,
  probe: GroundProbe,
  clearance: number = CAMERA_CLEARANCE,
  allowed?: (x: number, y: number, z: number) => boolean,
): number {
  const hidden = (t: number): boolean => {
    const x = eye.x + (desired.x - eye.x) * t;
    const y = eye.y + (desired.y - eye.y) * t;
    const z = eye.z + (desired.z - eye.z) * t;
    if (allowed !== undefined && !allowed(x, y, z)) return true;
    const ground = probe(x, y, z);
    return ground !== null && y < ground + clearance;
  };

  if (hidden(0)) return 0;
  for (let i = 1; i <= PULL_IN_SAMPLES; i++) {
    const t = i / PULL_IN_SAMPLES;
    if (!hidden(t)) continue;
    let safe = (i - 1) / PULL_IN_SAMPLES;
    let blocked = t;
    for (let k = 0; k < PULL_IN_REFINEMENTS; k++) {
      const mid = (safe + blocked) / 2;
      if (hidden(mid)) blocked = mid;
      else safe = mid;
    }
    return safe;
  }
  return 1;
}

/**
 * Ground as the camera sees it. With `roofAbove` (tunnel, overhang) the height field is the roof
 * over the player, not a floor, so only ground surfaces count.
 */
export function createCameraGroundProbe(
  heightField: HeightField,
  groundSurfaces: readonly GroundSurface[],
  roofAbove: boolean,
): GroundProbe {
  return (x, y, z) => {
    const terrain = roofAbove ? null : heightField.heightAt(x, z);
    let best = terrain;
    for (const surface of groundSurfaces) {
      const height = surface.surfaceBelow(
        x,
        y + CAMERA_CLEARANCE,
        z,
        CAMERA_SURFACE_REACH + CAMERA_CLEARANCE,
      );
      if (height !== null && (best === null || height > best)) best = height;
    }
    return best;
  };
}

/** Critically damped approach of `current` to `target`; smoothTime <= 0 snaps. */
export function smoothDamp(
  current: number,
  target: number,
  velocity: number,
  smoothTime: number,
  dt: number,
): { value: number; velocity: number } {
  if (smoothTime <= 0 || dt <= 0) return { value: target, velocity: 0 };
  const omega = 2 / smoothTime;
  const x = omega * dt;
  const decay = 1 / (1 + x + 0.48 * x * x + 0.235 * x * x * x);
  const change = current - target;
  const temp = (velocity + omega * change) * dt;
  let nextVelocity = (velocity - omega * temp) * decay;
  let value = target + (change + temp) * decay;
  if (target - current > 0 === value > target) {
    value = target;
    nextVelocity = 0;
  }
  return { value, velocity: nextVelocity };
}

const SNAP_EYE_DISTANCE = 2;
const scratchEuler = new Euler(0, 0, 0, "YXZ");

function lookQuaternion(yaw: number, pitch: number, out: Quaternion): Quaternion {
  scratchEuler.set(pitch, yaw, 0, "YXZ");
  return out.setFromEuler(scratchEuler);
}

export type CameraRigOptions = {
  readonly heightField: HeightField;
  readonly groundSurfaces: readonly GroundSurface[];
  /** Volumes the camera must not leave while the player is inside them (the tunnel). */
  readonly enclosures?: readonly Enclosure[];
  /** Read every frame so a change of the OS setting applies without reloading. */
  readonly prefersReducedMotion: () => boolean;
};

/** Drives a PerspectiveCamera in first or third person with a smooth transition. */
export class CameraRig {
  mode: CameraMode = "first";
  private readonly camera: PerspectiveCamera;
  private readonly options: CameraRigOptions;
  private blend = 0;
  private blendVelocity = 0;
  private reach = 1;
  private reachVelocity = 0;
  private eyeY: number | null = null;
  private eyeYVelocity = 0;
  private readonly firstQuat = new Quaternion();
  private readonly thirdQuat = new Quaternion();

  constructor(camera: PerspectiveCamera, options: CameraRigOptions) {
    this.camera = camera;
    this.options = options;
  }

  toggle(): CameraMode {
    this.mode = this.mode === "first" ? "third" : "first";
    return this.mode;
  }

  update(dt: number, feet: Vec3, look: Look): void {
    const smoothing = this.options.prefersReducedMotion() ? 0 : 1;
    const eye = eyePosition(feet);

    if (this.eyeY === null || Math.abs(this.eyeY - eye.y) > SNAP_EYE_DISTANCE) {
      this.eyeY = eye.y;
      this.eyeYVelocity = 0;
    } else {
      const next = smoothDamp(
        this.eyeY,
        eye.y,
        this.eyeYVelocity,
        EYE_HEIGHT_SMOOTH_TIME * smoothing,
        dt,
      );
      this.eyeY = next.value;
      this.eyeYVelocity = next.velocity;
    }
    eye.y = this.eyeY;

    const blendTarget = this.mode === "third" ? 1 : 0;
    const blend = smoothDamp(
      this.blend,
      blendTarget,
      this.blendVelocity,
      TRANSITION_SMOOTH_TIME * smoothing,
      dt,
    );
    this.blend = blend.value;
    this.blendVelocity = blend.velocity;

    lookQuaternion(look.yaw, look.pitch, this.firstQuat);
    if (this.blend === 0) {
      this.camera.position.set(eye.x, eye.y, eye.z);
      this.camera.quaternion.copy(this.firstQuat);
      return;
    }

    const desired = thirdPersonTarget(eye, look.yaw, look.pitch);
    const enclosure = this.enclosureAround(feet);
    const roofAbove = enclosure !== undefined || this.roofAbove(feet);
    const probe = createCameraGroundProbe(
      this.options.heightField,
      this.options.groundSurfaces,
      roofAbove,
    );
    const allowed = pullInFraction(
      eye,
      desired,
      probe,
      CAMERA_CLEARANCE,
      enclosure === undefined
        ? undefined
        : (x, y, z) => enclosure.contains(x, y, z, CAMERA_WALL_MARGIN),
    );
    if (allowed < this.reach) {
      this.reach = allowed;
      this.reachVelocity = 0;
    } else {
      const next = smoothDamp(
        this.reach,
        allowed,
        this.reachVelocity,
        TRANSITION_SMOOTH_TIME * smoothing,
        dt,
      );
      this.reach = next.value;
      this.reachVelocity = next.velocity;
    }

    const travel = this.reach * this.blend;
    this.camera.position.set(
      eye.x + (desired.x - eye.x) * travel,
      eye.y + (desired.y - eye.y) * travel,
      eye.z + (desired.z - eye.z) * travel,
    );

    const dx = eye.x - desired.x;
    const dy = eye.y - desired.y;
    const dz = eye.z - desired.z;
    lookQuaternion(Math.atan2(-dx, -dz), Math.atan2(dy, Math.hypot(dx, dz)), this.thirdQuat);
    this.camera.quaternion.copy(this.firstQuat).slerp(this.thirdQuat, this.blend);
  }

  private enclosureAround(feet: Vec3): Enclosure | undefined {
    return this.options.enclosures?.find((e) =>
      e.contains(feet.x, feet.y + EYE_HEIGHT / 2, feet.z, 0),
    );
  }

  private roofAbove(feet: Vec3): boolean {
    const terrain = this.options.heightField.heightAt(feet.x, feet.z);
    return terrain !== null && terrain > feet.y + CAPSULE_HEIGHT;
  }
}
