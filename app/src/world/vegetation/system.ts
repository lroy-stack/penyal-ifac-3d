import {
  type BufferGeometry,
  InstancedMesh,
  type Material,
  Matrix4,
  type Mesh,
  type Object3D,
  type Texture,
  type WebGLRenderer,
} from "three";
import { fetchJson, NotFoundError } from "../../core/http";
import type { QualityProfile } from "../../core/quality";
import { TEST_HOOKS_ENABLED } from "../../core/testHooks";
import { attachAtmosphere } from "../atmosphere";
import type { WorldSystem } from "../systems";
import { bakeTransform } from "./bake";
import {
  assertConsistent,
  PINE_CARD,
  PINE_PATH,
  PLANTS_PATH,
  pineMeshName,
  tierParams,
  VEGETATION_PATH,
  type VegetationData,
  vegetationSchema,
} from "./data";
import { LEVEL_UNSET, type LodBands, selectLevels } from "./lod";
import { plantMatrix, treeMatrix } from "./transform";

/** Frames between two looks at the camera distance; the camera must also have moved. */
export const REBUCKET_EVERY_FRAMES = 6;
/** Metres the camera moves before the levels are chosen again. */
export const REBUCKET_MIN_MOVE_M = 1;

export type VegetationCounts = {
  /** Drawn instances per level (lod0, lod1, far card). */
  readonly trees: readonly [number, number, number];
  readonly understory: readonly [number, number, number];
  /** InstancedMeshes with at least one instance. */
  readonly drawn: number;
};

declare global {
  interface Window {
    /** Test hook (dev and E2E builds): instance counts of the vegetation system. */
    __vegetation?: { counts(): VegetationCounts };
  }
}

export type VegetationSystemDeps = {
  readonly loadData: (url: string, signal: AbortSignal) => Promise<VegetationData>;
};

const DEFAULT_DEPS: VegetationSystemDeps = {
  loadData: (url, signal) => fetchJson(url, vegetationSchema, signal),
};

/** A set of instances with their precomputed matrices and the mesh class of each. */
type InstanceSet = {
  readonly count: number;
  readonly x: Float32Array;
  readonly y: Float32Array;
  readonly z: Float32Array;
  readonly keep: Uint8Array;
  /** Index into `targets[level]`. */
  readonly cls: Uint8Array;
  readonly matrices: Float32Array;
  readonly levels: Int8Array;
  /** The distinct meshes the set draws into; the far-card level of the trees shares one. */
  readonly meshes: readonly InstancedMesh[];
  /** `slots[level][cls]`: index into `meshes`. */
  readonly slots: readonly [Uint8Array, Uint8Array, Uint8Array];
  /** Instances written into each of `meshes` by the current rebucket (preallocated). */
  readonly filled: Int32Array;
  readonly bands: (tier: QualityProfile["tier"]) => LodBands;
};

type Targets = [InstancedMesh[], InstancedMesh[], InstancedMesh[]];

/** The distinct meshes of `targets[level][cls]` and the slot of each (level, cls) among them. */
function slotsOf(targets: Targets): Pick<InstanceSet, "meshes" | "slots" | "filled"> {
  const meshes: InstancedMesh[] = [];
  const slot = (mesh: InstancedMesh): number => {
    const found = meshes.indexOf(mesh);
    return found >= 0 ? found : meshes.push(mesh) - 1;
  };
  const slots = targets.map((level) => Uint8Array.from(level, slot)) as [
    Uint8Array,
    Uint8Array,
    Uint8Array,
  ];
  if (meshes.length > 256) {
    throw new Error(`${meshes.length} vegetation meshes in one set: the slots hold 256 at most.`);
  }
  return { meshes, slots, filled: new Int32Array(meshes.length) };
}

function meshNamed(root: Object3D, name: string): Mesh {
  const found = root.getObjectByName(name);
  const mesh = found?.type === "Mesh" ? found : found?.children.find((c) => c.type === "Mesh");
  if (mesh === undefined) throw new Error(`The vegetation model has no mesh named "${name}".`);
  return mesh as Mesh;
}

/** The geometry of a named mesh with its node transform baked in, so instances start at the origin. */
function geometryOf(
  root: Object3D,
  name: string,
): { geometry: BufferGeometry; material: Material } {
  const mesh = meshNamed(root, name);
  root.updateMatrixWorld(true);
  const geometry = mesh.geometry;
  if (!mesh.matrixWorld.equals(new Matrix4())) {
    return {
      geometry: bakeTransform(geometry, mesh.matrixWorld),
      material: mesh.material as Material,
    };
  }
  return { geometry, material: mesh.material as Material };
}

function hasMsaa(renderer: WebGLRenderer): boolean {
  try {
    return renderer.getContext().getContextAttributes()?.antialias === true;
  } catch {
    return false;
  }
}

function disposeMaterial(material: Material): void {
  for (const value of Object.values(material)) {
    if ((value as Texture | null)?.isTexture === true) (value as Texture).dispose();
  }
  material.dispose();
}

/**
 * Measured vegetation (E2.5): the LiDAR pines and the understory as InstancedMeshes, one per
 * (model, level) sharing the GLB geometry and material. Levels are chosen by the distance to the
 * camera with the bands the pipeline recorded per tier, a few frames apart and only after the
 * camera moved. Loads in the background and never delays the walk.
 */
export function createVegetationSystem(
  deps: VegetationSystemDeps = DEFAULT_DEPS,
): WorldSystem & { counts(): VegetationCounts } {
  let data: VegetationData | null = null;
  let treeSet: InstanceSet | null = null;
  let plantSet: InstanceSet | null = null;
  let profile: QualityProfile | null = null;
  let camera: { position: { x: number; y: number; z: number } } | null = null;
  let forced = true;
  let lastCamera = { x: Number.NaN, y: 0, z: 0 };
  let current: VegetationCounts = { trees: [0, 0, 0], understory: [0, 0, 0], drawn: 0 };
  const meshes: InstancedMesh[] = [];
  const geometries = new Set<BufferGeometry>();
  const materials = new Set<Material>();
  let hookInstalled = false;

  /** Builds one InstancedMesh per target and returns them with their capacity counts. */
  function makeMesh(
    root: Object3D,
    parent: Object3D,
    name: string,
    capacity: number,
    msaa: boolean,
    ctx: Parameters<WorldSystem["init"]>[0],
  ): InstancedMesh {
    const { geometry, material } = geometryOf(root, name);
    if (!materials.has(material)) {
      materials.add(material);
      // Foliage colour is a COLOR_0 multiplier: GLTFLoader enables vertexColors when present.
      const m = material as Material & { vertexColors: boolean; alphaToCoverage: boolean };
      m.vertexColors = geometry.hasAttribute("color");
      m.alphaToCoverage = msaa;
      m.needsUpdate = true;
      attachAtmosphere(material, ctx.atmosphere);
    }
    geometries.add(geometry);
    const mesh = new InstancedMesh(geometry, material, Math.max(1, capacity));
    mesh.name = `vegetation:${name}`;
    mesh.count = 0;
    mesh.frustumCulled = false;
    mesh.castShadow = false;
    mesh.receiveShadow = false;
    parent.add(mesh);
    meshes.push(mesh);
    return mesh;
  }

  function columnsFrom(
    count: number,
    x: readonly number[],
    z: readonly number[],
    keep: readonly number[],
  ): Pick<InstanceSet, "count" | "x" | "z" | "keep" | "y" | "levels"> {
    return {
      count,
      x: Float32Array.from(x),
      y: new Float32Array(count),
      z: Float32Array.from(z),
      keep: Uint8Array.from(keep),
      levels: new Int8Array(count).fill(LEVEL_UNSET),
    };
  }

  async function build(
    ctx: Parameters<WorldSystem["init"]>[0],
    parsed: VegetationData,
  ): Promise<void> {
    const msaa = hasMsaa(ctx.renderer);
    const loader = ctx.assets.gltf();
    const [pine, plants] = await Promise.all([
      loader.loadAsync(ctx.assets.url(PINE_PATH)),
      loader.loadAsync(ctx.assets.url(PLANTS_PATH)),
    ]);
    if (ctx.signal.aborted) return;
    const c = parsed.crowns;
    const u = parsed.understory;

    // Trees: lod0 and lod1 per variant, one far card shared by all variants.
    const variantCount = new Array<number>(parsed.variants).fill(0);
    for (let i = 0; i < c.count; i++) {
      const v = c.variant[i] as number;
      variantCount[v] = (variantCount[v] ?? 0) + 1;
    }
    const treeTargets: Targets = [[], [], []];
    for (let v = 0; v < parsed.variants; v++) {
      treeTargets[0].push(
        makeMesh(pine.scene, ctx.root, pineMeshName(v, 0), variantCount[v] ?? 0, msaa, ctx),
      );
      treeTargets[1].push(
        makeMesh(pine.scene, ctx.root, pineMeshName(v, 1), variantCount[v] ?? 0, msaa, ctx),
      );
    }
    const pineCard = makeMesh(pine.scene, ctx.root, PINE_CARD, c.count, msaa, ctx);
    for (let v = 0; v < parsed.variants; v++) treeTargets[2].push(pineCard);
    treeSet = {
      ...columnsFrom(c.count, c.x, c.z, c.keep),
      cls: Uint8Array.from(c.variant),
      matrices: new Float32Array(c.count * 16),
      ...slotsOf(treeTargets),
      bands: (tier) => tierParams(parsed, tier).treeLodM,
    };

    // Understory: three levels per model.
    const modelCount = new Array<number>(u.models.length).fill(0);
    for (let i = 0; i < u.count; i++) {
      const m = u.model[i] as number;
      modelCount[m] = (modelCount[m] ?? 0) + 1;
    }
    const plantTargets: Targets = [[], [], []];
    u.models.forEach((model, m) => {
      const n = modelCount[m] ?? 0;
      plantTargets[0].push(makeMesh(plants.scene, ctx.root, model.meshes.lod0, n, msaa, ctx));
      plantTargets[1].push(makeMesh(plants.scene, ctx.root, model.meshes.lod1, n, msaa, ctx));
      plantTargets[2].push(makeMesh(plants.scene, ctx.root, model.meshes.card, n, msaa, ctx));
    });
    plantSet = {
      ...columnsFrom(u.count, u.x, u.z, u.keep),
      cls: Uint8Array.from(u.model),
      matrices: new Float32Array(u.count * 16),
      ...slotsOf(plantTargets),
      bands: (tier) => tierParams(parsed, tier).understoryLodM,
    };
  }

  /** Places every instance on the rendered ground where it is known, else on the measured y. */
  function place(parsed: VegetationData, heightAt: (x: number, z: number) => number | null): void {
    const m = new Matrix4();
    const c = parsed.crowns;
    if (treeSet !== null) {
      for (let i = 0; i < c.count; i++) {
        const ground = heightAt(c.x[i] as number, c.z[i] as number);
        const foot = ground ?? (c.y[i] as number);
        treeSet.y[i] = foot;
        treeMatrix(
          m,
          {
            x: c.x[i] as number,
            y: c.y[i] as number,
            z: c.z[i] as number,
            height: c.height[i] as number,
            scaleXZ: c.scaleXZ[i] as number,
            yaw: c.yaw[i] as number,
            leanX: c.leanX[i] as number,
            leanZ: c.leanZ[i] as number,
            apexY: c.apexY[i] as number,
          },
          ground,
        ).toArray(treeSet.matrices, i * 16);
      }
    }
    const u = parsed.understory;
    if (plantSet !== null) {
      for (let i = 0; i < u.count; i++) {
        const ground = heightAt(u.x[i] as number, u.z[i] as number);
        plantSet.y[i] = ground ?? (u.y[i] as number);
        plantMatrix(
          m,
          {
            x: u.x[i] as number,
            y: u.y[i] as number,
            z: u.z[i] as number,
            scale: u.scale[i] as number,
            yaw: u.yaw[i] as number,
          },
          ground,
        ).toArray(plantSet.matrices, i * 16);
      }
    }
    forced = true;
  }

  /**
   * Chooses the level of every instance and copies the matrices of the drawn ones. Runs while
   * walking (every few frames once the camera moved), so it allocates nothing per instance.
   */
  function rebucket(
    set: InstanceSet,
    tier: QualityProfile["tier"],
    density: number,
  ): [number, number, number] {
    const camPos = camera?.position ?? { x: 0, y: 0, z: 0 };
    selectLevels(set, camPos, density, set.bands(tier), set.levels);
    const { meshes: targets, slots, filled, matrices, levels, cls } = set;
    filled.fill(0);
    const counts: [number, number, number] = [0, 0, 0];
    for (let i = 0; i < set.count; i++) {
      const level = levels[i] as number;
      if (level < 0) continue;
      const slot = slots[level as 0 | 1 | 2][cls[i] as number];
      if (slot === undefined) continue;
      const mesh = targets[slot] as InstancedMesh;
      const n = filled[slot] as number;
      if (n >= mesh.instanceMatrix.count) continue;
      const out = mesh.instanceMatrix.array;
      const from = i * 16;
      const to = n * 16;
      for (let k = 0; k < 16; k++) out[to + k] = matrices[from + k] as number;
      filled[slot] = n + 1;
      counts[level as 0 | 1 | 2]++;
    }
    for (let slot = 0; slot < targets.length; slot++) {
      const mesh = targets[slot] as InstancedMesh;
      const n = filled[slot] as number;
      mesh.count = n;
      mesh.instanceMatrix.clearUpdateRanges();
      mesh.instanceMatrix.addUpdateRange(0, n * 16);
      mesh.instanceMatrix.needsUpdate = true;
    }
    return counts;
  }

  function drawnMeshes(): number {
    let drawn = 0;
    for (const mesh of meshes) if (mesh.count > 0) drawn++;
    return drawn;
  }

  function refresh(): void {
    if (profile === null || treeSet === null || plantSet === null) return;
    const density = tierParamsFor(profile).density;
    const trees = rebucket(treeSet, profile.tier, density);
    const understory = rebucket(plantSet, profile.tier, density);
    current = {
      trees,
      understory,
      drawn: drawnMeshes(),
    };
    forced = false;
  }

  const tierParamsFor = (p: QualityProfile): { density: number } =>
    data === null ? { density: p.vegetation.density } : tierParams(data, p.tier);

  return {
    id: "vegetation",
    phase: "postPlayer",
    load: "background",
    async init(ctx) {
      let parsed: VegetationData;
      try {
        parsed = await deps.loadData(ctx.assets.url(VEGETATION_PATH), ctx.signal);
      } catch (error) {
        if (error instanceof NotFoundError) {
          return { status: "missing", message: "vegetation.json is not generated" };
        }
        throw error;
      }
      assertConsistent(parsed);
      data = parsed;
      profile = ctx.quality.current;
      camera = ctx.camera;
      await build(ctx, parsed);
      if (ctx.signal.aborted) return { status: "ready" };
      // The collision field resolves at the walk gate; on failure the measured y is kept.
      const heightAt = await ctx.collision.then(
        (field) => (x: number, z: number) => field.heightAt(x, z),
        () => () => null,
      );
      place(parsed, heightAt);
      refresh();
      if (TEST_HOOKS_ENABLED && !hookInstalled && typeof window !== "undefined") {
        hookInstalled = true;
        window.__vegetation = { counts: () => current };
      }
      return { status: "ready" };
    },
    update(frame) {
      if (profile === null || camera === null) return;
      if (!forced) {
        if (frame.frame % REBUCKET_EVERY_FRAMES !== 0) return;
        const p = camera.position;
        const dx = p.x - lastCamera.x;
        const dy = p.y - lastCamera.y;
        const dz = p.z - lastCamera.z;
        if (dx * dx + dy * dy + dz * dz < REBUCKET_MIN_MOVE_M ** 2) return;
      }
      lastCamera = { x: camera.position.x, y: camera.position.y, z: camera.position.z };
      refresh();
    },
    onQualityChange(next) {
      profile = next;
      forced = true;
    },
    counts: () => current,
    dispose() {
      for (const mesh of meshes) {
        mesh.parent?.remove(mesh);
        mesh.dispose();
      }
      meshes.length = 0;
      for (const geometry of geometries) geometry.dispose();
      for (const material of materials) disposeMaterial(material);
      geometries.clear();
      materials.clear();
      treeSet = null;
      plantSet = null;
      if (hookInstalled && typeof window !== "undefined") delete window.__vegetation;
      hookInstalled = false;
    },
  };
}
