import { describe, expect, it } from "vitest";
import type { Anchor, RoutePoint } from "../world/trail";
import {
  ARRIVAL_DISTANCE,
  type AutoWalkCommand,
  AutoWalker,
  type AutoWalkRoute,
  BEND_SPEED,
  buildAutoWalkRoute,
  headingOf,
  LOOK_AHEAD,
  MAX_TURN_RATE,
  type RouteSegment,
  STEEP_SPEED,
} from "./autowalk";
import { PlayerController, WALK_SPEED } from "./controller";

function line(from: RoutePoint, to: RoutePoint, steps: number): RoutePoint[] {
  return Array.from({ length: steps + 1 }, (_, i) => {
    const t = i / steps;
    return [
      from[0] + (to[0] - from[0]) * t,
      from[1] + (to[1] - from[1]) * t,
      from[2] + (to[2] - from[2]) * t,
    ] as const;
  });
}

function join(...parts: RoutePoint[][]): RoutePoint[] {
  return parts.flatMap((part, i) => (i === 0 ? part : part.slice(1)));
}

function anchor(x: number, y: number, z: number): Anchor {
  return { x, y, z };
}

// A trunk running east, then a fork: the north branch ends at "summit", the east one at
// "carabiners". "mid" sits on the trunk.
const TRUNK: RouteSegment = { id: "trunk", points: line([0, 0, 0], [100, 10, 0], 100) };
const NORTH: RouteSegment = { id: "north", points: line([100, 10, 0], [100, 40, -80], 80) };
const EAST: RouteSegment = { id: "east", points: line([100, 10, 0], [180, 10, 0], 80) };
const ANCHORS = {
  start: anchor(0, 0, 0),
  mid: anchor(50, 5, 0),
  summit: anchor(100, 40, -80),
  carabiners: anchor(180, 10, 0),
  elsewhere: anchor(500, 0, 500),
};

function routeTo(target: string): AutoWalkRoute {
  return buildAutoWalkRoute([TRUNK, NORTH, EAST], ANCHORS, target);
}

describe("buildAutoWalkRoute", () => {
  it("follows the trunk and the right branch to each target", () => {
    const summit = routeTo("summit");
    expect(summit.points[0]).toEqual([0, 0, 0]);
    expect(summit.points[summit.points.length - 1]).toEqual([100, 40, -80]);
    expect(summit.length).toBeCloseTo(100 + 80, 6);
    expect(summit.points).not.toContainEqual([150, 10, 0]);

    const carabiners = routeTo("carabiners");
    expect(carabiners.points[carabiners.points.length - 1]).toEqual([180, 10, 0]);
    expect(carabiners.length).toBeCloseTo(180, 6);
  });

  it("stops at an anchor in the middle of the trunk and drops duplicate joints", () => {
    const mid = routeTo("mid");
    expect(mid.points[mid.points.length - 1]).toEqual([50, 5, 0]);
    const joined = routeTo("summit").points;
    expect(new Set(joined.map((p) => p.join(","))).size).toBe(joined.length);
  });

  it("accepts an anchor mapped a few metres off the end of its branch", () => {
    const route = buildAutoWalkRoute(
      [TRUNK, NORTH, EAST],
      { ...ANCHORS, offset: anchor(183, 10, 2) },
      "offset",
    );
    expect(route.points[route.points.length - 1]).toEqual([180, 10, 0]);
  });

  it("explains an unknown target and an anchor off the route", () => {
    expect(() => routeTo("nowhere")).toThrow(/Unknown auto-walk target "nowhere".*summit/);
    expect(() => routeTo("elsewhere")).toThrow(/"elsewhere" is not on the walking route/);
    expect(() => routeTo("start")).toThrow(/nothing to walk/);
  });
});

type Walk = { controller: PlayerController; yaw: number; commands: AutoWalkCommand[] };

/** Runs the walker against the real controller on flat ground. */
function simulate(
  route: AutoWalkRoute,
  start: { x: number; z: number; yaw: number },
  seconds: number,
  fps = 30,
  onFrame?: (walk: Walk) => void,
): Walk {
  const walker = new AutoWalker(route);
  const controller = new PlayerController({
    heightField: { heightAt: () => 0 },
    groundSurfaces: [],
    corridor: { contains: () => true, clamp: (_a, _b, x, z) => ({ x, z }) },
    start: { x: start.x, z: start.z, y: 0 },
  });
  const walk: Walk = { controller, yaw: start.yaw, commands: [] };
  const dt = 1 / fps;
  for (let i = 0; i < seconds * fps; i++) {
    const command = walker.update(dt, controller.state, walk.yaw);
    walk.commands.push(command);
    walk.yaw = command.yaw;
    controller.update(dt, {
      moveX: command.moveX,
      moveY: command.moveY,
      run: command.run,
      yaw: command.yaw,
    });
    onFrame?.(walk);
    if (command.done) break;
  }
  return walk;
}

function distanceToRoute(route: AutoWalkRoute, x: number, z: number): number {
  let best = Number.POSITIVE_INFINITY;
  for (let i = 0; i + 1 < route.points.length; i++) {
    const a = route.points[i] as RoutePoint;
    const b = route.points[i + 1] as RoutePoint;
    const abx = b[0] - a[0];
    const abz = b[2] - a[2];
    const t = Math.max(
      0,
      Math.min(1, ((x - a[0]) * abx + (z - a[2]) * abz) / (abx * abx + abz * abz)),
    );
    best = Math.min(best, Math.hypot(x - (a[0] + abx * t), z - (a[2] + abz * t)));
  }
  return best;
}

const EAST_YAW = headingOf(1, 0);

describe("AutoWalker", () => {
  it("reaches the target and stops there", () => {
    const route = routeTo("carabiners");
    const walk = simulate(route, { x: 0, z: 0, yaw: EAST_YAW }, 400);
    const last = walk.commands[walk.commands.length - 1] as AutoWalkCommand;
    expect(last.done).toBe(true);
    expect(last.moveY).toBe(0);
    expect(Math.hypot(walk.controller.state.x - 180, walk.controller.state.z)).toBeLessThan(
      ARRIVAL_DISTANCE + 0.5,
    );
  });

  it("reports progress from 0 to 1", () => {
    const route = routeTo("carabiners");
    const walker = new AutoWalker(route);
    expect(walker.progress).toBe(0);
    walker.update(1 / 30, { x: 90, y: 9, z: 0 }, EAST_YAW);
    expect(walker.progress).toBeCloseTo(0.5, 2);
    walker.update(1 / 30, { x: 180, y: 10, z: 0 }, EAST_YAW);
    expect(walker.done).toBe(true);
    expect(walker.progress).toBe(1);
  });

  it("starts anywhere on the route: snaps to the nearest point and heads onward", () => {
    const route = routeTo("summit");
    const command = new AutoWalker(route).update(
      1 / 30,
      { x: 100, y: 10, z: -40 },
      headingOf(0, -1),
    );
    expect(command.done).toBe(false);
    // The north branch climbs 30 m in 80 m: steep enough to count as steps.
    expect(command.moveY).toBeCloseTo(STEEP_SPEED, 6);
    expect(command.yaw).toBeCloseTo(headingOf(0, -1), 2);
  });

  it("prefers the stretch at the player's height when the route doubles back over itself", () => {
    const loop = [
      ...line([0, 0, 0], [20, 0, 0], 20),
      ...line([20, 0, 0], [20, 10, 3], 6).slice(1),
      ...line([20, 10, 3], [0, 10, 3], 20).slice(1),
    ] as RoutePoint[];
    const route = buildAutoWalkRoute(
      [{ id: "loop", points: loop }],
      { top: anchor(0, 10, 3) },
      "top",
    );
    const walker = new AutoWalker(route);
    walker.update(1 / 30, { x: 10, y: 10, z: 3 }, 0);
    expect(walker.progress).toBeGreaterThan(0.5);
  });

  it("stays centred: an offset start converges onto the route", () => {
    const route = routeTo("carabiners");
    const walk = simulate(route, { x: 20, z: 1.5, yaw: EAST_YAW }, 30);
    expect(distanceToRoute(route, walk.controller.state.x, walk.controller.state.z)).toBeLessThan(
      0.15,
    );
  });

  it("walks at the controller's walking speed on a straight", () => {
    const route = routeTo("carabiners");
    const walk = simulate(route, { x: 0, z: 0, yaw: EAST_YAW }, 10);
    expect(walk.controller.state.x).toBeGreaterThan(WALK_SPEED * 10 * 0.95);
  });

  it("turns no faster than the maximum turn rate", () => {
    const route = routeTo("summit");
    const walker = new AutoWalker(route);
    const dt = 1 / 30;
    const command = walker.update(dt, { x: 100, y: 10, z: -20 }, headingOf(1, 0));
    expect(Math.abs(command.yaw - headingOf(1, 0))).toBeLessThanOrEqual(MAX_TURN_RATE * dt + 1e-9);
    // Facing across the route it hardly advances until it has turned.
    expect(command.moveY).toBeLessThan(0.2);
  });

  it("slows on a sharp bend and on steps, and eases off before the end", () => {
    const bend: AutoWalkRoute = buildAutoWalkRoute(
      [
        {
          id: "b",
          points: join(line([0, 0, 0], [30, 0, 0], 30), line([30, 0, 0], [30, 0, -30], 30)),
        },
      ],
      { end: anchor(30, 0, -30) },
      "end",
    );
    const flat = routeTo("carabiners");
    const steps = buildAutoWalkRoute(
      [{ id: "s", points: line([0, 0, 0], [60, 30, 0], 60) }],
      { end: anchor(60, 30, 0) },
      "end",
    );
    const speedAt = (r: AutoWalkRoute, x: number, y: number, z: number, yaw: number): number =>
      new AutoWalker(r).update(1 / 30, { x, y, z }, yaw).moveY;
    const open = speedAt(flat, 20, 2, 0, EAST_YAW);
    expect(open).toBeCloseTo(1, 6);
    expect(speedAt(bend, 29 - LOOK_AHEAD / 2, 0, 0, EAST_YAW)).toBeLessThan(open - 0.1);
    expect(speedAt(bend, 29 - LOOK_AHEAD / 2, 0, 0, EAST_YAW)).toBeGreaterThanOrEqual(
      BEND_SPEED * 0.25,
    );
    expect(speedAt(steps, 20, 10, 0, EAST_YAW)).toBeLessThan(open - 0.1);
    expect(speedAt(flat, 179, 10, 0, EAST_YAW)).toBeLessThan(0.7);
  });

  it("does not cut a right-angle corner by more than half a metre", () => {
    const corner = buildAutoWalkRoute(
      [
        {
          id: "c",
          points: join(line([0, 0, 0], [40, 0, 0], 40), line([40, 0, 0], [40, 0, -40], 40)),
        },
      ],
      { end: anchor(40, 0, -40) },
      "end",
    );
    let worst = 0;
    simulate(corner, { x: 0, z: 0, yaw: EAST_YAW }, 120, 30, (walk) => {
      worst = Math.max(
        worst,
        distanceToRoute(corner, walk.controller.state.x, walk.controller.state.z),
      );
    });
    expect(worst).toBeLessThan(0.5);
  });

  it("is frame-rate independent: 20 and 60 fps end within a few centimetres", () => {
    const route = routeTo("summit");
    const slow = simulate(route, { x: 0, z: 0, yaw: EAST_YAW }, 60, 20);
    const fast = simulate(route, { x: 0, z: 0, yaw: EAST_YAW }, 60, 60);
    expect(
      Math.hypot(
        slow.controller.state.x - fast.controller.state.x,
        slow.controller.state.z - fast.controller.state.z,
      ),
    ).toBeLessThan(0.3);
  });

  it("stays put once done", () => {
    const route = routeTo("mid");
    const walker = new AutoWalker(route);
    walker.update(1 / 30, { x: 50, y: 5, z: 0 }, EAST_YAW);
    const again = walker.update(1 / 30, { x: 10, y: 1, z: 0 }, EAST_YAW);
    expect(again).toMatchObject({ done: true, moveY: 0, moveX: 0, yaw: EAST_YAW });
  });
});
