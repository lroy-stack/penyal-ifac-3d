import { PerspectiveCamera, Vector3 } from "three";
import { describe, expect, it } from "vitest";
import type { GroundSurface, HeightField } from "../world/ground";
import { TunnelGroundSurface } from "../world/tunnel";
import {
  CAMERA_CLEARANCE,
  CAMERA_WALL_MARGIN,
  CameraRig,
  createCameraGroundProbe,
  eyePosition,
  pullInFraction,
  smoothDamp,
  THIRD_PERSON_DISTANCE,
  THIRD_PERSON_LIFT,
  thirdPersonTarget,
} from "./cameras";
import { EYE_HEIGHT } from "./controller";

const FEET = { x: 10, y: 5, z: -20 };
const flatGround = (height: number) => () => height;

describe("camera geometry", () => {
  it("puts the eye 0.1 m below the capsule top", () => {
    expect(eyePosition(FEET)).toEqual({ x: 10, y: 5 + EYE_HEIGHT, z: -20 });
  });

  it("places the third-person camera 4 m behind and 1.2 m above the eye line", () => {
    const eye = eyePosition(FEET);
    const behind = thirdPersonTarget(eye, 0, 0);
    expect(behind.x).toBeCloseTo(eye.x, 12);
    expect(behind.z).toBeCloseTo(eye.z + THIRD_PERSON_DISTANCE, 12);
    expect(behind.y).toBeCloseTo(eye.y + THIRD_PERSON_LIFT, 12);

    const facingWest = thirdPersonTarget(eye, Math.PI / 2, 0);
    expect(facingWest.x).toBeCloseTo(eye.x + THIRD_PERSON_DISTANCE, 12);
    expect(facingWest.z).toBeCloseTo(eye.z, 12);
  });
});

describe("pullInFraction", () => {
  const eye = eyePosition({ x: 0, y: 0, z: 0 });
  const desired = thirdPersonTarget(eye, 0, 0);

  it("keeps the full distance over open ground", () => {
    expect(pullInFraction(eye, desired, flatGround(0))).toBe(1);
  });

  it("pulls in when a bank rises behind the player and stays 0.3 m above it", () => {
    // Ground rises 1 m per metre of distance behind the player (z > 0), starting at 1 m.
    const bank = (_x: number, _y: number, z: number): number | null => (z > 1 ? z - 1 : null);
    const t = pullInFraction(eye, desired, bank);
    expect(t).toBeGreaterThan(0);
    expect(t).toBeLessThan(1);
    const z = desired.z * t;
    const y = eye.y + (desired.y - eye.y) * t;
    expect(y).toBeGreaterThanOrEqual((bank(0, y, z) as number) + CAMERA_CLEARANCE - 1e-3);
    expect(y - ((bank(0, y, z) as number) + CAMERA_CLEARANCE)).toBeLessThan(0.01);
  });

  it("returns 0 when even the eye is hidden", () => {
    expect(pullInFraction(eye, desired, flatGround(eye.y))).toBe(0);
  });

  it("ignores a null probe (outside the height field)", () => {
    expect(pullInFraction(eye, desired, () => null)).toBe(1);
  });
});

describe("camera ground probe", () => {
  const rock: HeightField = { heightAt: () => 30 };
  const tunnelFloor: GroundSurface = {
    surfaceBelow: (_x, top, _z, maxDrop) => (top >= 0 && top - maxDrop <= 0 ? 0 : null),
  };

  it("treats the height field as a roof inside a tunnel, so the camera is not pulled in", () => {
    const eye = { x: 0, y: 1.6, z: 0 };
    const desired = thirdPersonTarget(eye, 0, 0);
    const underRock = createCameraGroundProbe(rock, [tunnelFloor], true);
    expect(pullInFraction(eye, desired, underRock)).toBe(1);

    const treatedAsFloor = createCameraGroundProbe(rock, [tunnelFloor], false);
    expect(pullInFraction(eye, desired, treatedAsFloor)).toBe(0);
  });

  it("pulls the camera in when it would sink to a ground surface", () => {
    const ledge: GroundSurface = {
      surfaceBelow: (_x, top, z, maxDrop) => (z > 2 && top >= 2 && top - maxDrop <= 2 ? 2 : null),
    };
    const probe = createCameraGroundProbe({ heightAt: () => null }, [ledge], false);
    const eye = { x: 0, y: 3, z: 0 };
    const t = pullInFraction(eye, { x: 0, y: 2, z: 5 }, probe);
    expect(t).toBeGreaterThan(0);
    expect(t).toBeLessThan(1);
  });
});

describe("smoothDamp", () => {
  it("snaps with a zero smooth time", () => {
    expect(smoothDamp(0, 5, 3, 0, 0.016)).toEqual({ value: 5, velocity: 0 });
  });

  it("approaches the target monotonically without overshoot", () => {
    let value = 0;
    let velocity = 0;
    let previous = 0;
    let overshoot = false;
    for (let i = 0; i < 120; i++) {
      ({ value, velocity } = smoothDamp(value, 1, velocity, 0.25, 1 / 60));
      if (value < previous || value > 1) overshoot = true;
      previous = value;
    }
    expect(overshoot).toBe(false);
    expect(value).toBeGreaterThan(0.999);
  });

  it("gives nearly the same result at 60 fps and 20 fps", () => {
    const at = (fps: number): number => {
      let value = 0;
      let velocity = 0;
      for (let i = 0; i < fps / 4; i++)
        ({ value, velocity } = smoothDamp(value, 1, velocity, 0.25, 1 / fps));
      return value;
    };
    expect(Math.abs(at(60) - at(20))).toBeLessThan(0.02);
  });
});

describe("CameraRig", () => {
  const flat: HeightField = { heightAt: () => 0 };
  const rig = (reduced: boolean): { camera: PerspectiveCamera; rig: CameraRig } => {
    const camera = new PerspectiveCamera();
    return {
      camera,
      rig: new CameraRig(camera, {
        heightField: flat,
        groundSurfaces: [],
        prefersReducedMotion: () => reduced,
      }),
    };
  };
  const feet = { x: 0, y: 0, z: 0 };
  const look = { yaw: 0, pitch: 0 };

  it("sits at the eye in first person looking along -Z", () => {
    const { camera, rig: r } = rig(false);
    r.update(1 / 60, feet, look);
    expect(camera.position.toArray()).toEqual([0, EYE_HEIGHT, 0]);
    const forward = new Vector3(0, 0, -1).applyQuaternion(camera.quaternion);
    expect(forward.z).toBeCloseTo(-1, 9);
  });

  it("jumps straight to the third-person position when motion is reduced", () => {
    const { camera, rig: r } = rig(true);
    r.toggle();
    r.update(1 / 60, feet, look);
    expect(camera.position.z).toBeCloseTo(THIRD_PERSON_DISTANCE, 9);
    expect(camera.position.y).toBeCloseTo(EYE_HEIGHT + THIRD_PERSON_LIFT, 9);
    const toPlayer = new Vector3(0, 0, -1).applyQuaternion(camera.quaternion);
    const expected = new Vector3(0, -THIRD_PERSON_LIFT, -THIRD_PERSON_DISTANCE).normalize();
    expect(toPlayer.distanceTo(expected)).toBeLessThan(1e-9);
  });

  it("glides to the third-person position otherwise", () => {
    const { camera, rig: r } = rig(false);
    r.toggle();
    r.update(1 / 60, feet, look);
    expect(camera.position.z).toBeGreaterThan(0);
    expect(camera.position.z).toBeLessThan(THIRD_PERSON_DISTANCE / 2);
    for (let i = 0; i < 180; i++) r.update(1 / 60, feet, look);
    expect(camera.position.z).toBeCloseTo(THIRD_PERSON_DISTANCE, 2);
  });

  it("pulls in near a wall of terrain and recovers slowly", () => {
    const camera = new PerspectiveCamera();
    const bankField: HeightField = { heightAt: (_x, z) => (z > 1.5 ? 6 : 0) };
    const r = new CameraRig(camera, {
      heightField: bankField,
      groundSurfaces: [],
      prefersReducedMotion: () => true,
    });
    r.toggle();
    r.update(1 / 60, feet, look);
    expect(camera.position.z).toBeLessThan(2);
    expect(camera.position.z).toBeGreaterThan(0);
  });
});

describe("camera inside the tunnel", () => {
  // A tunnel 2.4 m wide and 3 m high with a right-angle bend at (0, 0), under 40 m of rock.
  const tunnel = new TunnelGroundSurface({
    axis: [
      [-20, 0, 0],
      [0, 0, 0],
      [0, 0, -20],
    ],
    width: 2.4,
    height: 3,
  });
  const rock: HeightField = { heightAt: () => 40 };

  it("pullInFraction stops at the first point the enclosure refuses", () => {
    const eye = { x: 0, y: 1.6, z: -10 };
    const behind = { x: 0, y: 1.6, z: 5 };
    const inside = (x: number, y: number, z: number): boolean =>
      tunnel.contains(x, y, z, CAMERA_WALL_MARGIN);
    const t = pullInFraction(eye, behind, () => null, CAMERA_CLEARANCE, inside);
    expect(t).toBeGreaterThan(0);
    expect(t).toBeLessThan(1);
    expect(eye.z + (behind.z - eye.z) * t).toBeLessThanOrEqual(1.1);
  });

  it("keeps the third-person camera inside the tunnel at the bend, whichever way it looks", () => {
    const camera = new PerspectiveCamera();
    const rig = new CameraRig(camera, {
      heightField: rock,
      groundSurfaces: [tunnel],
      enclosures: [tunnel],
      prefersReducedMotion: () => true,
    });
    rig.toggle();
    for (const feet of [
      { x: 0.3, y: 0, z: -2 },
      { x: -2, y: 0, z: 0.2 },
      { x: 0, y: 0, z: 0 },
      { x: 0, y: 0, z: -12 },
    ]) {
      for (let yaw = 0; yaw < Math.PI * 2; yaw += Math.PI / 8) {
        rig.update(1 / 60, feet, { yaw, pitch: 0.2 });
        const { x, y, z } = camera.position;
        expect(tunnel.contains(x, y, z, 0)).toBe(true);
      }
    }
  });

  it("treats the height field as the roof, not the floor, while inside the tunnel", () => {
    // The DEM puts a rock skin 1.1 m above the floor along the tunnel.
    const camera = new PerspectiveCamera();
    const rig = new CameraRig(camera, {
      heightField: { heightAt: () => 1.1 },
      groundSurfaces: [tunnel],
      enclosures: [tunnel],
      prefersReducedMotion: () => true,
    });
    rig.toggle();
    rig.update(1 / 60, { x: -10, y: 0, z: 0 }, { yaw: -Math.PI / 2, pitch: 0 });
    expect(camera.position.x).toBeLessThan(-12);
    expect(camera.position.x).toBeGreaterThan(-15);
  });

  it("does not confine the camera when the player is outside the tunnel", () => {
    const camera = new PerspectiveCamera();
    const rig = new CameraRig(camera, {
      heightField: { heightAt: () => 0 },
      groundSurfaces: [tunnel],
      enclosures: [tunnel],
      prefersReducedMotion: () => true,
    });
    rig.toggle();
    rig.update(1 / 60, { x: 50, y: 0, z: 50 }, { yaw: 0, pitch: 0 });
    expect(camera.position.z).toBeCloseTo(50 + THIRD_PERSON_DISTANCE, 9);
  });
});
