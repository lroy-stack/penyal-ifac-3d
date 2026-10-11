import type { Anchor, RoutePoint } from "../world/trail";

/** Distance (m) ahead on the route that the walker steers towards. */
export const LOOK_AHEAD = 3;
/** Shortest look-ahead (m), used on tight bends so the path does not cut the corner. */
export const MIN_LOOK_AHEAD = 1;
/** The steering chord may stray this far (m) from the route polyline. */
export const MAX_CHORD_DEVIATION = 0.35;
/** Fastest turn (rad/s) of the heading. */
export const MAX_TURN_RATE = 2.4;
/** The walk ends when the remaining route is shorter than this (m). */
export const ARRIVAL_DISTANCE = 0.6;
/** Within this distance (m) of the end the walker eases off. */
export const BRAKING_DISTANCE = 2;
/** Route gradient (rise over run) from which the walker treats the ground as steps and slows. */
export const STEEP_GRADIENT = 0.3;
/** Fraction of the walking speed on steps. */
export const STEEP_SPEED = 0.75;
/** Slowest fraction of the walking speed on the sharpest bends. */
export const BEND_SPEED = 0.5;
/** Tolerance (m) for two segments to count as joined end to start. */
const JOINT_TOLERANCE = 0.5;
/**
 * An anchor farther than this (m) from every route vertex is not on the route. The mirador is
 * mapped 3.1 m off the end of its branch; the app counts an anchor as reached within 6 m.
 */
const ANCHOR_TOLERANCE = 6;
/** The search for the walker's place on the route covers this stretch (m) behind and ahead. */
const WINDOW_BEHIND = 2;
const WINDOW_AHEAD = 25;

export type RouteSegment = { readonly id: string; readonly points: readonly RoutePoint[] };

export type AutoWalkRoute = {
  readonly target: string;
  readonly points: readonly RoutePoint[];
  /** Horizontal distance (m) from the first point to each point. */
  readonly arc: readonly number[];
  readonly length: number;
};

/** The walker's output for one update; `moveX`/`moveY`/`run` match the controller's input. */
export type AutoWalkCommand = {
  readonly moveX: number;
  readonly moveY: number;
  readonly run: boolean;
  /** New camera yaw (rad, 0 looks along -Z, positive turns left). */
  readonly yaw: number;
  readonly done: boolean;
};

function horizontal(a: RoutePoint, b: RoutePoint): number {
  return Math.hypot(a[0] - b[0], a[2] - b[2]);
}

function toRoute(target: string, points: readonly RoutePoint[]): AutoWalkRoute {
  if (points.length < 2) {
    throw new Error(
      `The route to "${target}" has fewer than two points; there is nothing to walk.`,
    );
  }
  const arc = [0];
  for (let i = 1; i < points.length; i++) {
    arc.push(
      (arc[i - 1] as number) + horizontal(points[i - 1] as RoutePoint, points[i] as RoutePoint),
    );
  }
  return { target, points, arc, length: arc[arc.length - 1] as number };
}

/** Every chain of segments that starts at a segment nothing leads into and ends at a leaf. */
function segmentChains(segments: readonly RouteSegment[]): RoutePoint[][] {
  const first = (s: RouteSegment): RoutePoint => s.points[0] as RoutePoint;
  const last = (s: RouteSegment): RoutePoint => s.points[s.points.length - 1] as RoutePoint;
  const next = (s: RouteSegment): RouteSegment[] =>
    segments.filter((o) => o !== s && horizontal(last(s), first(o)) <= JOINT_TOLERANCE);
  const isRoot = (s: RouteSegment): boolean =>
    !segments.some((o) => o !== s && next(o).includes(s));

  const chains: RoutePoint[][] = [];
  const walk = (
    segment: RouteSegment,
    points: RoutePoint[],
    seen: readonly RouteSegment[],
  ): void => {
    const joined = [...points, ...segment.points.slice(points.length === 0 ? 0 : 1)];
    const onward = next(segment).filter((s) => !seen.includes(s));
    if (onward.length === 0) chains.push(joined);
    for (const s of onward) walk(s, joined, [...seen, s]);
  };
  const roots = segments.filter(isRoot);
  for (const root of roots.length > 0 ? roots : segments.slice(0, 1)) walk(root, [], [root]);
  return chains;
}

/**
 * The walking route from the start of the trail to `target`: `"summit"`, `"carabiners"` or any
 * anchor lying on the route. Branches of the trail are separate chains of segments; the route
 * follows the chain that passes closest to the anchor and stops at its nearest vertex.
 */
export function buildAutoWalkRoute(
  segments: readonly RouteSegment[],
  anchors: Readonly<Record<string, Anchor>>,
  target: string,
): AutoWalkRoute {
  const anchor = anchors[target];
  if (anchor === undefined) {
    throw new Error(
      `Unknown auto-walk target "${target}". Available: ${Object.keys(anchors).join(", ")}.`,
    );
  }
  let best: { points: RoutePoint[]; index: number; distance: number } | null = null;
  for (const points of segmentChains(segments)) {
    points.forEach((p, index) => {
      const distance = Math.hypot(p[0] - anchor.x, p[2] - anchor.z);
      if (best === null || distance < best.distance) best = { points, index, distance };
    });
  }
  const found = best as { points: RoutePoint[]; index: number; distance: number } | null;
  if (found === null || found.distance > ANCHOR_TOLERANCE) {
    throw new Error(`The anchor "${target}" is not on the walking route.`);
  }
  return toRoute(target, found.points.slice(0, found.index + 1));
}

/** Heading (rad, player convention) of the direction (dx, dz). */
export function headingOf(dx: number, dz: number): number {
  return Math.atan2(-dx, -dz);
}

function wrapAngle(angle: number): number {
  return Math.atan2(Math.sin(angle), Math.cos(angle));
}

type Place = { arc: number; x: number; y: number; z: number; index: number };

/** Follows a route: where the walker is on it, where to steer, how fast to go. */
export class AutoWalker {
  readonly route: AutoWalkRoute;
  private arcPosition: number | null = null;
  private finished = false;

  constructor(route: AutoWalkRoute) {
    this.route = route;
  }

  /** 0 at the first point of the route, 1 at the target. */
  get progress(): number {
    if (this.finished) return 1;
    return this.arcPosition === null ? 0 : Math.min(1, this.arcPosition / this.route.length);
  }

  get done(): boolean {
    return this.finished;
  }

  update(
    dt: number,
    position: { readonly x: number; readonly y: number; readonly z: number },
    yaw: number,
  ): AutoWalkCommand {
    if (this.finished) return { moveX: 0, moveY: 0, run: false, yaw, done: true };
    const here = this.locate(position);
    this.arcPosition = here.arc;
    const remaining = this.route.length - here.arc;
    const end = this.route.points[this.route.points.length - 1] as RoutePoint;
    if (
      remaining <= ARRIVAL_DISTANCE ||
      Math.hypot(end[0] - position.x, end[2] - position.z) <= ARRIVAL_DISTANCE
    ) {
      this.finished = true;
      return { moveX: 0, moveY: 0, run: false, yaw, done: true };
    }

    const lookAhead = this.pickLookAhead(here);
    const aim = this.pointAt(Math.min(this.route.length, here.arc + lookAhead));
    const wanted = headingOf(aim.x - position.x, aim.z - position.z);
    const turn = wrapAngle(wanted - yaw);
    const step = MAX_TURN_RATE * Math.max(dt, 0);
    const nextYaw = yaw + Math.max(-step, Math.min(step, turn));

    const misalignment = Math.abs(wrapAngle(wanted - nextYaw));
    const aligned = Math.max(0, 1 - misalignment / (Math.PI / 2));
    return {
      moveX: 0,
      moveY: aligned * this.speedFactor(here.arc, remaining),
      run: false,
      yaw: nextYaw,
      done: false,
    };
  }

  /** Slower on bends and steps, and easing off before the end. */
  private speedFactor(arc: number, remaining: number): number {
    const ahead = this.pointAt(Math.min(this.route.length, arc + LOOK_AHEAD));
    const now = this.pointAt(arc);
    const run = Math.hypot(ahead.x - now.x, ahead.z - now.z);
    const gradient = run > 0.1 ? Math.abs(ahead.y - now.y) / run : 0;
    const steps = gradient >= STEEP_GRADIENT ? STEEP_SPEED : 1;

    const farther = this.pointAt(Math.min(this.route.length, arc + 2 * LOOK_AHEAD));
    const bend = Math.abs(
      wrapAngle(
        headingOf(farther.x - ahead.x, farther.z - ahead.z) -
          headingOf(ahead.x - now.x, ahead.z - now.z),
      ),
    );
    const turning = 1 - (1 - BEND_SPEED) * Math.min(1, bend / (Math.PI / 2));

    const braking = Math.max(0.25, Math.min(1, remaining / BRAKING_DISTANCE));
    return steps * turning * braking;
  }

  /** The longest look-ahead whose straight chord stays near the route (no corner cutting). */
  private pickLookAhead(here: Place): number {
    for (let look = LOOK_AHEAD; look > MIN_LOOK_AHEAD; look -= 0.5) {
      if (this.chordDeviation(here, here.arc + look) <= MAX_CHORD_DEVIATION) return look;
    }
    return MIN_LOOK_AHEAD;
  }

  private chordDeviation(from: Place, toArc: number): number {
    const to = this.pointAt(Math.min(this.route.length, toArc));
    const cx = to.x - from.x;
    const cz = to.z - from.z;
    const chord = Math.hypot(cx, cz);
    let worst = 0;
    const { points, arc } = this.route;
    for (let i = from.index + 1; i < points.length && (arc[i] as number) < to.arc; i++) {
      const p = points[i] as RoutePoint;
      const offset =
        chord === 0
          ? Math.hypot(p[0] - from.x, p[2] - from.z)
          : Math.abs((p[0] - from.x) * cz - (p[2] - from.z) * cx) / chord;
      worst = Math.max(worst, offset);
    }
    return worst;
  }

  /** Index of the last route point at or before `arc`. */
  private indexAt(arc: number): number {
    const values = this.route.arc;
    let low = 0;
    let high = values.length - 1;
    while (low < high) {
      const mid = (low + high + 1) >> 1;
      if ((values[mid] as number) <= arc) low = mid;
      else high = mid - 1;
    }
    return low;
  }

  private pointAt(arc: number): Place {
    const { points, arc: values } = this.route;
    const index = Math.min(this.indexAt(arc), points.length - 2);
    const a = points[index] as RoutePoint;
    const b = points[index + 1] as RoutePoint;
    const span = (values[index + 1] as number) - (values[index] as number);
    const t = span === 0 ? 0 : Math.max(0, Math.min(1, (arc - (values[index] as number)) / span));
    return {
      arc,
      index,
      x: a[0] + (b[0] - a[0]) * t,
      y: a[1] + (b[1] - a[1]) * t,
      z: a[2] + (b[2] - a[2]) * t,
    };
  }

  /**
   * The walker's place on the route. The first time, the nearest point of the whole route in 3D
   * (so a switchback above or below does not win); afterwards the nearest point within a window
   * around the last place; the place never moves backwards.
   */
  private locate(position: { readonly x: number; readonly y: number; readonly z: number }): Place {
    const { points, arc, length } = this.route;
    const previous = this.arcPosition;
    const from = previous === null ? 0 : this.indexAt(Math.max(0, previous - WINDOW_BEHIND));
    const to =
      previous === null
        ? points.length - 2
        : Math.min(points.length - 2, this.indexAt(Math.min(length, previous + WINDOW_AHEAD)));
    let best: Place | null = null;
    let bestDistance = Number.POSITIVE_INFINITY;
    for (let i = from; i <= to; i++) {
      const a = points[i] as RoutePoint;
      const b = points[i + 1] as RoutePoint;
      const abx = b[0] - a[0];
      const abz = b[2] - a[2];
      const lengthSq = abx * abx + abz * abz;
      const t =
        lengthSq === 0
          ? 0
          : Math.max(
              0,
              Math.min(1, ((position.x - a[0]) * abx + (position.z - a[2]) * abz) / lengthSq),
            );
      const x = a[0] + abx * t;
      const z = a[2] + abz * t;
      const y = a[1] + (b[1] - a[1]) * t;
      const distance =
        Math.hypot(position.x - x, position.z - z) +
        (previous === null ? Math.abs(position.y - y) : 0);
      if (distance < bestDistance) {
        bestDistance = distance;
        best = { arc: (arc[i] as number) + Math.sqrt(lengthSq) * t, x, y, z, index: i };
      }
    }
    if (best === null) throw new Error("The route has no segments to follow.");
    return this.pointAt(previous === null ? best.arc : Math.max(previous, best.arc));
  }
}
