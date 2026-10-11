import { Matrix4, Vector3 } from "three";
import { describe, expect, it } from "vitest";
import { plantMatrix, TREE_NOMINAL_HEIGHT, type TreeInstance, treeMatrix } from "./transform";

const tree: TreeInstance = {
  x: 100,
  y: 20,
  z: -300,
  height: 12,
  scaleXZ: 0.8,
  yaw: 0,
  leanX: 0,
  leanZ: 0,
  apexY: 32,
};

const apexOf = (instance: TreeInstance, groundY: number | null = null): Vector3 =>
  new Vector3(0, TREE_NOMINAL_HEIGHT, 0).applyMatrix4(treeMatrix(new Matrix4(), instance, groundY));

describe("tree matrix", () => {
  it("scales y by height / 10 and x, z by the absolute scaleXZ", () => {
    const m = treeMatrix(new Matrix4(), tree, null);
    const top = new Vector3(0, TREE_NOMINAL_HEIGHT, 0).applyMatrix4(m);
    expect(top.toArray()).toEqual([100, 32, -300].map((v, i) => (i === 1 ? 20 + 12 : v)));
    const side = new Vector3(3.2, 0, 0).applyMatrix4(m);
    expect(side.x - 100).toBeCloseTo(3.2 * 0.8, 6);
  });

  it("an unleaning tree stands upright on the measured foot", () => {
    const top = apexOf(tree);
    expect(top.x).toBeCloseTo(100, 6);
    expect(top.z).toBeCloseTo(-300, 6);
  });

  it("tilts the crown from the foot towards (x + leanX, apexY, z + leanZ)", () => {
    const leaning = { ...tree, leanX: 0.6, leanZ: -0.3 };
    const top = apexOf(leaning);
    const wanted = new Vector3(0.6, 12, -0.3).normalize().multiplyScalar(12);
    expect(top.x - 100).toBeCloseTo(wanted.x, 5);
    expect(top.y - 20).toBeCloseTo(wanted.y, 5);
    expect(top.z + 300).toBeCloseTo(wanted.z, 5);
  });

  it("the lean does not change the tree height or shear it", () => {
    const leaning = { ...tree, leanX: 0.6, yaw: 77 };
    const m = treeMatrix(new Matrix4(), leaning, null);
    const foot = new Vector3(0, 0, 0).applyMatrix4(m);
    const top = new Vector3(0, TREE_NOMINAL_HEIGHT, 0).applyMatrix4(m);
    expect(top.distanceTo(foot)).toBeCloseTo(12, 5);
    const a = new Vector3(1, 0, 0).transformDirection(m);
    const b = new Vector3(0, 1, 0).transformDirection(m);
    expect(a.dot(b)).toBeCloseTo(0, 6);
  });

  it("puts the foot on the resampled ground and leans towards the apex from there", () => {
    const m = treeMatrix(new Matrix4(), { ...tree, leanX: 0.5 }, 22);
    expect(new Vector3().applyMatrix4(m).y).toBeCloseTo(22, 6);
    const top = new Vector3(0, TREE_NOMINAL_HEIGHT, 0).applyMatrix4(m);
    const direction = top.sub(new Vector3(100, 22, -300)).normalize();
    expect(direction.equals(new Vector3(0.5, 10, 0).normalize())).toBe(false);
    expect(direction.x / direction.y).toBeCloseTo(0.5 / (32 - 22), 5);
  });

  it("ignores a lean when the apex is not above the foot", () => {
    const top = apexOf({ ...tree, leanX: 0.5, apexY: 19 });
    expect(top.x).toBeCloseTo(100, 6);
  });

  it("yaw is in degrees about the vertical", () => {
    const m = treeMatrix(new Matrix4(), { ...tree, yaw: 90, scaleXZ: 1 }, null);
    const x = new Vector3(1, 0, 0).transformDirection(m);
    expect(x.z).toBeCloseTo(-1, 6);
  });
});

describe("plant matrix", () => {
  const plant = { x: 5, y: 2, z: 7, scale: 0.5, yaw: 0 };

  it("scales uniformly from the foot", () => {
    const m = plantMatrix(new Matrix4(), plant, null);
    expect(new Vector3(0, 2, 0).applyMatrix4(m).toArray()).toEqual([5, 3, 7]);
  });

  it("uses the resampled ground when there is one", () => {
    const m = plantMatrix(new Matrix4(), plant, 4.5);
    expect(new Vector3().applyMatrix4(m).y).toBe(4.5);
  });
});
