import { type Matrix4, Quaternion, Vector3 } from "three";

/** Height of the modelled pine (m); the pipeline scales y by `height / TREE_NOMINAL_HEIGHT`. */
export const TREE_NOMINAL_HEIGHT = 10;

export type TreeInstance = {
  readonly x: number;
  readonly y: number;
  readonly z: number;
  readonly height: number;
  /** Absolute horizontal scale (crown radius / 3.2), not relative to the vertical one. */
  readonly scaleXZ: number;
  readonly yaw: number;
  readonly leanX: number;
  readonly leanZ: number;
  readonly apexY: number;
};

const UP = new Vector3(0, 1, 0);
const DEG = Math.PI / 180;
const position = new Vector3();
const scale = new Vector3();
const toApex = new Vector3();
const tilt = new Quaternion();
const spin = new Quaternion();

/** Below this horizontal lean (m) or vertical rise (m) the tree stands upright. */
const MIN_LEAN = 1e-3;
const MIN_RISE = 0.1;

/**
 * Local matrix of a tree: translate to the foot (on the rendered ground when `groundY` is given,
 * else the measured y), yaw, and scale in the tree's own frame so the lean never shears it. An
 * upright tree is `height` tall. A leaning one is tilted from the foot towards the measured apex
 * (x + leanX, apexY, z + leanZ) and scaled along its trunk to reach it: the measured apex wins
 * over `height`, which would leave the crown up to 0.89 m short of it (`vegetation.json` leans
 * up to 0.6 x height).
 */
export function treeMatrix(target: Matrix4, tree: TreeInstance, groundY: number | null): Matrix4 {
  const footY = groundY ?? tree.y;
  position.set(tree.x, footY, tree.z);
  let length = tree.height;
  spin.setFromAxisAngle(UP, tree.yaw * DEG);
  const rise = tree.apexY - footY;
  if (Math.hypot(tree.leanX, tree.leanZ) >= MIN_LEAN && rise >= MIN_RISE) {
    toApex.set(tree.leanX, rise, tree.leanZ);
    length = toApex.length();
    tilt.setFromUnitVectors(UP, toApex.normalize());
    spin.premultiply(tilt);
  }
  scale.set(tree.scaleXZ, length / TREE_NOMINAL_HEIGHT, tree.scaleXZ);
  return target.compose(position, spin, scale);
}

export type PlantInstance = {
  readonly x: number;
  readonly y: number;
  readonly z: number;
  /** Uniform scale of the model. */
  readonly scale: number;
  readonly yaw: number;
};

/** Local matrix of an understory plant: foot, yaw, uniform scale. */
export function plantMatrix(
  target: Matrix4,
  plant: PlantInstance,
  groundY: number | null,
): Matrix4 {
  position.set(plant.x, groundY ?? plant.y, plant.z);
  spin.setFromAxisAngle(UP, plant.yaw * DEG);
  scale.setScalar(plant.scale);
  return target.compose(position, spin, scale);
}
