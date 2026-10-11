import { describe, expect, it } from "vitest";
import { simulationSteps } from "../core/timescale";
import {
  type Corridor,
  type GroundSurface,
  type HeightField,
  PolygonCorridor,
} from "../world/ground";
import {
  type ControllerInput,
  MAX_FRAME_DT,
  PlayerController,
  RUN_SPEED,
  SLOPE_PROBE_DISTANCE,
  STEP_HEIGHT,
  WALK_SPEED,
} from "./controller";

const FORWARD: ControllerInput = { moveX: 0, moveY: 1, run: false, yaw: 0 };
const OPEN: Corridor = {
  contains: () => true,
  clamp: (_fx, _fz, tx, tz) => ({ x: tx, z: tz }),
};

function field(heightAt: (x: number, z: number) => number | null): HeightField {
  return { heightAt };
}

function floor(y: number, xMax: number, zMin: number, zMax: number): GroundSurface {
  return {
    surfaceBelow: (x, top, z, maxDrop) =>
      Math.abs(x) <= xMax && z >= zMin && z <= zMax && y <= top && y >= top - maxDrop ? y : null,
  };
}

function walker(
  heightField: HeightField,
  options: {
    surfaces?: GroundSurface[];
    corridor?: Corridor;
    y?: number;
    x?: number;
    z?: number;
  } = {},
): PlayerController {
  const start = { x: options.x ?? 0, z: options.z ?? 0 };
  return new PlayerController({
    heightField,
    groundSurfaces: options.surfaces ?? [],
    corridor: options.corridor ?? OPEN,
    start: options.y === undefined ? start : { ...start, y: options.y },
  });
}

function run(
  controller: PlayerController,
  seconds: number,
  fps: number,
  input: ControllerInput,
): void {
  const frames = Math.round(seconds * fps);
  for (let i = 0; i < frames; i++) controller.update(1 / fps, input);
}

describe("flat ground", () => {
  const flat = field(() => 0);

  it("walks at 1.4 m/s and runs at 2.6 m/s", () => {
    const walking = walker(flat);
    run(walking, 2, 60, FORWARD);
    expect(-walking.state.z).toBeCloseTo(2 * WALK_SPEED, 6);

    const running = walker(flat);
    run(running, 2, 60, { ...FORWARD, run: true });
    expect(-running.state.z).toBeCloseTo(2 * RUN_SPEED, 6);
  });

  it("moves in camera-yaw space and does not speed up on diagonals", () => {
    const left = walker(flat);
    run(left, 1, 60, { ...FORWARD, yaw: Math.PI / 2 });
    expect(left.state.x).toBeCloseTo(-WALK_SPEED, 6);
    expect(left.state.z).toBeCloseTo(0, 6);

    const diagonal = walker(flat);
    run(diagonal, 1, 60, { moveX: 5, moveY: 5, run: false, yaw: 0 });
    expect(Math.hypot(diagonal.state.x, diagonal.state.z)).toBeCloseTo(WALK_SPEED, 6);
    expect(diagonal.state.x).toBeGreaterThan(0);
  });

  it("stays put without input and starts grounded on the height field", () => {
    const controller = walker(field(() => 12.5));
    run(controller, 1, 60, { moveX: 0, moveY: 0, run: false, yaw: 0 });
    expect(controller.state).toMatchObject({ x: 0, y: 12.5, z: 0, grounded: true });
  });

  it("refuses to start outside the height field", () => {
    expect(() => walker(field(() => null))).toThrow(/outside the height field/);
  });

  it("treats the edge of the height field as a wall", () => {
    const controller = walker(field((_x, z) => (z > -3 ? 0 : null)));
    run(controller, 5, 60, FORWARD);
    expect(controller.state.z).toBeGreaterThan(-3);
    expect(controller.state.grounded).toBe(true);
  });

  it("truncates a stalled frame instead of teleporting", () => {
    const controller = walker(flat);
    controller.update(30, FORWARD);
    expect(-controller.state.z).toBeCloseTo(MAX_FRAME_DT * WALK_SPEED, 6);
  });
});

describe("steps and walls", () => {
  it("steps up onto a 0.3 m step", () => {
    const controller = walker(field((_x, z) => (z < -2 ? 0.3 : 0)));
    run(controller, 3, 60, FORWARD);
    expect(controller.state.z).toBeLessThan(-3);
    expect(controller.state.y).toBeCloseTo(0.3, 9);
    expect(controller.state.grounded).toBe(true);
  });

  it("is blocked by a 0.6 m wall, and keeps its height", () => {
    const controller = walker(field((_x, z) => (z < -2 ? 0.6 : 0)));
    run(controller, 5, 60, FORWARD);
    expect(controller.state.z).toBeGreaterThanOrEqual(-2 + SLOPE_PROBE_DISTANCE);
    expect(controller.state.z).toBeLessThanOrEqual(-2 + SLOPE_PROBE_DISTANCE + 0.03);
    expect(controller.state.y).toBe(0);
  });

  it("climbs a step of exactly the step height", () => {
    const controller = walker(field((_x, z) => (z < -2 ? STEP_HEIGHT : 0)));
    run(controller, 3, 60, FORWARD);
    expect(controller.state.y).toBeCloseTo(STEP_HEIGHT, 9);
  });
});

describe("slopes", () => {
  const ramp = (degrees: number): HeightField => {
    const tan = Math.tan((degrees * Math.PI) / 180);
    return field((_x, z) => Math.max(0, (-z - 1) * tan));
  };

  it("climbs a 45 degree slope following its surface", () => {
    const controller = walker(ramp(45));
    run(controller, 3, 60, FORWARD);
    expect(-controller.state.z).toBeCloseTo(3 * WALK_SPEED, 6);
    expect(controller.state.y).toBeCloseTo(-controller.state.z - 1, 6);
    expect(controller.state.grounded).toBe(true);
  });

  it("does not climb a 60 degree slope", () => {
    const controller = walker(ramp(60));
    run(controller, 5, 60, FORWARD);
    expect(controller.state.z).toBeGreaterThan(-1);
    expect(controller.state.y).toBe(0);
  });
});

describe("descending", () => {
  it("follows descending stairs without leaving the ground", () => {
    const stairs = field((_x, z) => 3 - 0.3 * Math.floor(Math.max(0, -z) / 0.5));
    const controller = walker(stairs, { y: 3 });
    let airborneFrames = 0;
    for (let i = 0; i < 240; i++) {
      controller.update(1 / 60, FORWARD);
      if (!controller.state.grounded) airborneFrames++;
    }
    expect(airborneFrames).toBe(0);
    expect(controller.state.y).toBeCloseTo(3 - 0.3 * Math.floor(-controller.state.z / 0.5), 9);
  });

  it("falls off a ledge higher than the snap distance and lands", () => {
    const controller = walker(field((_x, z) => (z < -1 ? -2 : 0)));
    run(controller, 3, 60, FORWARD);
    expect(controller.state.y).toBeCloseTo(-2, 9);
    expect(controller.state.grounded).toBe(true);
  });
});

describe("corridor", () => {
  const strip = new PolygonCorridor([
    [-1, 5],
    [1, 5],
    [1, -50],
    [-1, -50],
  ]);

  it("slides along the boundary instead of stopping", () => {
    const controller = walker(
      field(() => 0),
      { corridor: strip },
    );
    run(controller, 4, 60, { ...FORWARD, yaw: -Math.PI / 4 });
    expect(controller.state.x).toBeLessThanOrEqual(1 + 1e-9);
    expect(controller.state.x).toBeGreaterThan(0.99);
    expect(-controller.state.z).toBeGreaterThan(3);
    expect(controller.state.corridorHit).toBe(true);
  });

  it("never leaves the polygon when pushed straight at the boundary", () => {
    const controller = walker(
      field(() => 0),
      { corridor: strip },
    );
    run(controller, 3, 60, { moveX: 1, moveY: 0, run: true, yaw: 0 });
    expect(strip.contains(controller.state.x, controller.state.z)).toBe(true);
    expect(controller.state.corridorHit).toBe(true);
  });

  it("reports no hit while inside", () => {
    const controller = walker(
      field(() => 0),
      { corridor: strip },
    );
    run(controller, 1, 60, FORWARD);
    expect(controller.state.corridorHit).toBe(false);
  });
});

describe("frame-rate independence", () => {
  const terrain = field((x, z) => 0.25 * Math.max(0, -z) + (x > 0.5 ? 0.2 : 0));
  const input: ControllerInput = { moveX: 0.4, moveY: 1, run: true, yaw: 0.3 };

  it("ends within 1 cm after 2 s at 60 fps and at 20 fps", () => {
    const fast = walker(terrain);
    const slow = walker(terrain);
    run(fast, 2, 60, input);
    run(slow, 2, 20, input);
    expect(Math.hypot(fast.state.x - slow.state.x, fast.state.z - slow.state.z)).toBeLessThan(0.01);
    expect(Math.abs(fast.state.y - slow.state.y)).toBeLessThan(0.01);
  });

  it("matches real time when a 60 fps loop runs at timescale 8 (test-only speed-up)", () => {
    const real = walker(terrain);
    const scaled = walker(terrain);
    run(real, 16, 60, input);
    for (let frame = 0; frame < 2 * 60; frame++) {
      for (const step of simulationSteps(1 / 60, 8, MAX_FRAME_DT)) scaled.update(step, input);
    }
    expect(Math.hypot(real.state.x - scaled.state.x, real.state.z - scaled.state.z)).toBeLessThan(
      0.05,
    );
    expect(Math.abs(real.state.y - scaled.state.y)).toBeLessThan(0.05);
  });

  it("stays stable on the loop's longest frame at timescale 16", () => {
    const scaled = walker(terrain);
    for (const step of simulationSteps(0.1, 16, MAX_FRAME_DT)) scaled.update(step, input);
    const real = walker(terrain);
    run(real, 1.6, 60, input);
    expect(Math.hypot(real.state.x - scaled.state.x, real.state.z - scaled.state.z)).toBeLessThan(
      0.05,
    );
    expect(scaled.state.grounded).toBe(true);
  });
});

describe("tunnel under rock", () => {
  // Rock 30 m high covers z in [-30, -5]; the tunnel floor at y = 0 is 1 m either side of x = 0.
  const rock = field((_x, z) => (z <= -5 && z >= -30 ? 30 : 0));
  const tunnelFloor = floor(0, 1, -30, -5);

  it("keeps the player on the tunnel floor far below the height field", () => {
    const controller = walker(rock, { surfaces: [tunnelFloor], y: 0, z: -10 });
    expect(controller.state).toMatchObject({ y: 0, grounded: true });
    run(controller, 5, 60, FORWARD);
    expect(controller.state.y).toBe(0);
    expect(controller.state.grounded).toBe(true);
    expect(controller.state.z).toBeLessThan(-16);
  });

  it("walks in from the portal and cannot step sideways into the rock", () => {
    const controller = walker(rock, { surfaces: [tunnelFloor] });
    run(controller, 10, 60, FORWARD);
    expect(controller.state.z).toBeLessThan(-10);
    expect(controller.state.y).toBe(0);

    run(controller, 3, 60, { moveX: 1, moveY: 0, run: true, yaw: 0 });
    expect(controller.state.x).toBeLessThanOrEqual(1 + 1e-9);
    expect(controller.state.y).toBe(0);
  });

  it("stands on top of the rock when starting there", () => {
    const controller = walker(rock, { surfaces: [tunnelFloor], z: -10 });
    expect(controller.state.y).toBe(30);
    run(controller, 2, 60, { moveX: 0, moveY: 0, run: false, yaw: 0 });
    expect(controller.state.y).toBe(30);
  });
});

describe("height field that fills a hollow", () => {
  // The DEM says rock at 1.1 m above the tunnel floor (y = 0) for z in [-30, -1] (a skin that is
  // steeper than the slope limit), although the tunnel is 2.8 m high there.
  const skin = field((_x, z) => (z <= -1 && z >= -30 ? 1.1 + (-z - 1) * 3 : 0));
  const tunnelFloor = floor(0, 1, -30, 0);
  const hollow = {
    contains: (x: number, y: number, z: number): boolean =>
      Math.abs(x) <= 1 && z <= 0 && z >= -30 && y >= 0 && y <= 2.8,
  };

  it("is a wall without the hollow", () => {
    // Starting on the skin (the height field at the start), 1.1 m above the floor.
    const controller = walker(skin, { surfaces: [tunnelFloor], z: -1 });
    expect(controller.state.y).toBeCloseTo(1.1, 9);
    run(controller, 5, 60, FORWARD);
    expect(controller.state.z).toBeGreaterThan(-2);
  });

  it("ignores the height field inside the hollow, so the floor carries the player", () => {
    const controller = new PlayerController({
      heightField: skin,
      groundSurfaces: [tunnelFloor],
      hollows: [hollow],
      corridor: OPEN,
      start: { x: 0, z: -1 },
    });
    run(controller, 10, 60, FORWARD);
    expect(controller.state.z).toBeLessThan(-12);
    expect(controller.state.y).toBe(0);
    expect(controller.state.grounded).toBe(true);
  });

  it("still stands on terrain above the hollow", () => {
    const rock = field(() => 30);
    const controller = new PlayerController({
      heightField: rock,
      groundSurfaces: [tunnelFloor],
      hollows: [hollow],
      corridor: OPEN,
      start: { x: 0, z: -10 },
    });
    expect(controller.state.y).toBe(30);
  });
});
