import {
  BoxGeometry,
  BufferAttribute,
  Group,
  type InstancedMesh,
  Mesh,
  MeshStandardMaterial,
} from "three";
import type { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { describe, expect, it } from "vitest";
import { profileFor } from "../../core/quality";
import { makeWorldDeps } from "../fixtures";
import { createWorld, type FrameInfo } from "../systems";
import type { VegetationData } from "./data";
import { createVegetationSystem } from "./system";

const TIERS: VegetationData["budget"]["tiers"] = {
  low: { density: 0.35, distanceM: 60, treeLodM: [15, 35, 60], understoryLodM: [4, 12, 30] },
  medium: { density: 0.7, distanceM: 120, treeLodM: [30, 70, 120], understoryLodM: [8, 24, 60] },
  high: { density: 1, distanceM: 200, treeLodM: [30, 70, 200], understoryLodM: [8, 24, 100] },
};

// Two trees (variants 0 and 1) 10 m and 100 m from the origin, and three plants.
const DATA: VegetationData = {
  version: 1,
  variants: 2,
  crowns: {
    count: 2,
    x: [10, 100],
    y: [0, 0],
    z: [0, 0],
    height: [10, 10],
    scaleXZ: [1, 1],
    keep: [0, 0],
    variant: [0, 1],
    yaw: [0, 0],
    leanX: [0, 0],
    leanZ: [0, 0],
    apexY: [10, 10],
  },
  understory: {
    count: 3,
    models: [{ id: "grass", meshes: { lod0: "g0", lod1: "g1", card: "gc" } }],
    x: [2, 2, 2],
    y: [0, 0, 0],
    z: [0, 0, 0],
    height: [1, 1, 1],
    scale: [1, 1, 1],
    yaw: [0, 0, 0],
    model: [0, 0, 0],
    keep: [0, 50, 90],
  },
  budget: { tiers: TIERS },
};

function fakeModel(names: readonly string[]): Group {
  const scene = new Group();
  const material = new MeshStandardMaterial();
  for (const name of names) {
    const geometry = new BoxGeometry(1, 1, 1);
    geometry.setAttribute("color", new BufferAttribute(new Float32Array(24 * 3).fill(1), 3));
    const mesh = new Mesh(geometry, material);
    mesh.name = name;
    scene.add(mesh);
  }
  return scene;
}

const frame = (n: number): FrameInfo => ({
  frame: n,
  dt: 0.016,
  time: n * 0.016,
  realMs: 16,
  drawingBufferHeight: 720,
  player: null,
});

async function setup(tier: "low" | "medium" | "high" = "medium") {
  const gltf = {
    loadAsync: async (url: string) => ({
      scene: url.includes("pine")
        ? fakeModel([
            "pine_v0_lod0",
            "pine_v0_lod1",
            "pine_v1_lod0",
            "pine_v1_lod1",
            "pine_far_card",
          ])
        : fakeModel(["g0", "g1", "gc"]),
    }),
  } as unknown as GLTFLoader;
  const { deps } = makeWorldDeps({
    assets: { gltf: () => gltf, url: (path) => `/${path}` },
    collision: Promise.resolve({ heightAt: () => 3 }),
    quality: { current: profileFor(tier, { coarsePointer: false, softwareRenderer: false }) },
  });
  const system = createVegetationSystem({ loadData: async () => DATA });
  const world = createWorld([system], deps);
  world.startWalk();
  await new Promise((resolve) => setTimeout(resolve, 0));
  await world.init("background");
  return { world, system, deps };
}

const meshesOf = (root: Group): InstancedMesh[] =>
  root.children.filter((c): c is InstancedMesh => (c as InstancedMesh).isInstancedMesh === true);

describe("vegetation system", () => {
  it("is ready and builds one instanced mesh per (model, level), the tree cards shared", async () => {
    const { world, deps } = await setup();
    expect(world.status().vegetation).toEqual({ state: "ready" });
    const root = deps.scene.getObjectByName("system:vegetation") as Group;
    expect(meshesOf(root)).toHaveLength(2 * 2 + 1 + 3);
  });

  it("draws an understory plant in the far band with its card", async () => {
    const { world, system, deps } = await setup("medium");
    // medium understory bands 8/24/60: the plants at x = 2 are 40 m away.
    deps.camera.position.set(42, 0, 0);
    world.update("postPlayer", frame(6));
    expect(system.counts().understory).toEqual([0, 0, 2]);
    const root = deps.scene.getObjectByName("system:vegetation") as Group;
    const card = meshesOf(root).find((m) => m.name === "vegetation:gc") as InstancedMesh;
    expect(card.count).toBe(2);
  });

  it("buckets by distance at the recorded bands and density of the tier", async () => {
    const { system } = await setup("medium");
    // medium: tree bands 30/70/120 and understory 8/24/60; density 0.7 drops keep 90 and 50 stays.
    expect(system.counts().trees).toEqual([1, 0, 1]);
    expect(system.counts().understory).toEqual([2, 0, 0]);
  });

  it("resamples the ground height where the collision field has one", async () => {
    const { deps } = await setup();
    const root = deps.scene.getObjectByName("system:vegetation") as Group;
    const near = meshesOf(root).find((m) => m.name === "vegetation:pine_v0_lod0") as InstancedMesh;
    expect(near.instanceMatrix.array[13]).toBe(3);
  });

  it("fills the far card shared by every variant with each tree's own matrix", async () => {
    const { world, system, deps } = await setup("medium");
    // Both trees (x = 10, variant 0; x = 100, variant 1) about 100.6 m away: the far card.
    deps.camera.position.set(55, 0, 90);
    world.update("postPlayer", frame(6));
    expect(system.counts().trees).toEqual([0, 0, 2]);
    const root = deps.scene.getObjectByName("system:vegetation") as Group;
    const card = meshesOf(root).find((m) => m.name === "vegetation:pine_far_card") as InstancedMesh;
    expect(card.count).toBe(2);
    const xs = [card.instanceMatrix.array[12], card.instanceMatrix.array[16 + 12]];
    expect(xs).toEqual([10, 100]);
    expect(system.counts().drawn).toBe(1);
  });

  it("re-buckets only every few frames and after the camera moved", async () => {
    const { world, system, deps } = await setup();
    expect(system.counts().trees).toEqual([1, 0, 1]);
    deps.camera.position.set(55, 0, 0);
    world.update("postPlayer", frame(1));
    expect(system.counts().trees).toEqual([1, 0, 1]);
    world.update("postPlayer", frame(6));
    // Both trees are now 45 m away: the mid level.
    expect(system.counts().trees).toEqual([0, 2, 0]);
  });

  it("re-buckets when the quality changes", async () => {
    const { world, system } = await setup("high");
    expect(system.counts().understory).toEqual([3, 0, 0]);
    world.setQuality(profileFor("low", { coarsePointer: false, softwareRenderer: false }));
    world.update("postPlayer", frame(6));
    // low: density 0.35 keeps only keep < 35; understory lod0 up to 4 m.
    expect(system.counts().understory).toEqual([1, 0, 0]);
  });

  it("turns missing when the data is not generated", async () => {
    const { NotFoundError } = await import("../../core/http");
    const { deps } = makeWorldDeps();
    const system = createVegetationSystem({
      loadData: async () => {
        throw new NotFoundError("/assets/generated/vegetation.json");
      },
    });
    const world = createWorld([system], deps);
    world.startWalk();
    await world.init("background");
    expect(world.status().vegetation?.state).toBe("missing");
  });

  it("disposes its meshes", async () => {
    const { world, deps } = await setup();
    const root = deps.scene.getObjectByName("system:vegetation") as Group;
    world.dispose();
    expect(meshesOf(root)).toHaveLength(0);
  });
});
