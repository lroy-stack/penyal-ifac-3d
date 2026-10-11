import {
  Box3,
  Color,
  DirectionalLight,
  HemisphereLight,
  type Material,
  type Mesh,
  type Object3D,
  PerspectiveCamera,
  Scene,
  type Texture,
  Vector3,
} from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { GLTF } from "three/addons/loaders/GLTFLoader.js";
import { createGltfLoader } from "../src/core/assets";
import { createLoop } from "../src/core/loop";
import { createRenderer } from "../src/core/renderer";

const DEFAULT_SRC = "/assets/generated/spike/spike.glb";

export type TextureStat = {
  readonly kind: string;
  readonly format: number;
  readonly colorSpace: string;
  readonly width: number;
  readonly height: number;
};

export type AssetStats = {
  readonly src: string;
  readonly status: "loading" | "ready" | "error";
  readonly error: string | null;
  readonly loadMs: number | null;
  readonly triangles: number | null;
  readonly drawCalls: number | null;
  readonly textures: readonly TextureStat[];
  readonly extensionsUsed: readonly string[];
};

declare global {
  interface Window {
    __assetStats?: AssetStats;
  }
}

function requireElement<T extends HTMLElement>(id: string, type: new () => T): T {
  const element = document.getElementById(id);
  if (!(element instanceof type)) {
    throw new Error(`asset-viewer.html is missing the #${id} element.`);
  }
  return element;
}

function collectTextures(root: Object3D): Texture[] {
  const found = new Set<Texture>();
  root.traverse((object) => {
    const materials = (object as Mesh).material as Material | Material[] | undefined;
    if (materials === undefined) return;
    for (const material of Array.isArray(materials) ? materials : [materials]) {
      for (const value of Object.values(material)) {
        if (value && typeof value === "object" && (value as Texture).isTexture === true) {
          found.add(value as Texture);
        }
      }
    }
  });
  return [...found];
}

function describeTexture(texture: Texture): TextureStat {
  const compressed = (texture as { isCompressedTexture?: boolean }).isCompressedTexture === true;
  const level = compressed
    ? (texture as { mipmaps?: { width: number; height: number }[] }).mipmaps?.[0]
    : (texture.image as { width?: number; height?: number } | null);
  return {
    kind: compressed ? "CompressedTexture" : "Texture",
    format: texture.format,
    colorSpace: texture.colorSpace,
    width: level?.width ?? 0,
    height: level?.height ?? 0,
  };
}

function renderStats(stats: AssetStats): void {
  const list = requireElement("stats-list", HTMLDListElement);
  list.replaceChildren();
  const rows: [string, string, boolean?][] = [
    ["Source", stats.src],
    ["Status", stats.status],
    ["Load time", stats.loadMs === null ? "-" : `${stats.loadMs.toFixed(0)} ms`],
    ["Triangles", stats.triangles === null ? "-" : String(stats.triangles)],
    ["Draw calls", stats.drawCalls === null ? "-" : String(stats.drawCalls)],
    [
      "Textures",
      stats.textures.length === 0
        ? "none"
        : stats.textures
            .map((t) => `${t.kind} ${t.width}x${t.height} format ${t.format} ${t.colorSpace}`)
            .join("; "),
    ],
    [
      "extensionsUsed",
      stats.extensionsUsed.length === 0 ? "none" : stats.extensionsUsed.join(", "),
    ],
  ];
  if (stats.error !== null) rows.push(["Error", stats.error, true]);
  for (const [label, value, isError] of rows) {
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = value;
    if (isError) detail.dataset.error = "true";
    list.append(term, detail);
  }
}

function publish(stats: AssetStats): void {
  window.__assetStats = stats;
  renderStats(stats);
}

function frameModel(camera: PerspectiveCamera, controls: OrbitControls, model: Object3D): void {
  const box = new Box3().setFromObject(model);
  const center = box.getCenter(new Vector3());
  const radius = Math.max(box.getSize(new Vector3()).length() / 2, 0.001);
  const distance = radius / Math.sin((camera.fov * Math.PI) / 360);
  camera.near = radius / 100;
  camera.far = radius * 100;
  camera.position.copy(center).add(new Vector3(0.6, 0.5, 1).normalize().multiplyScalar(distance));
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  controls.update();
}

async function main(): Promise<void> {
  const src = new URLSearchParams(window.location.search).get("src") ?? DEFAULT_SRC;
  const base = { src, error: null, loadMs: null, triangles: null, drawCalls: null } as const;
  publish({ ...base, status: "loading", textures: [], extensionsUsed: [] });

  const canvas = requireElement("scene", HTMLCanvasElement);
  const camera = new PerspectiveCamera(50, 1, 0.1, 5000);
  const handle = createRenderer(canvas, (width, height) => {
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  });
  if (!handle.ok) {
    publish({ ...base, status: "error", error: handle.message, textures: [], extensionsUsed: [] });
    return;
  }
  const { renderer } = handle;

  const scene = new Scene();
  scene.background = new Color(0x9ec9ee);
  scene.add(new HemisphereLight(0xcfe6ff, 0x6b5a3c, 1.2));
  const sun = new DirectionalLight(0xfff1d6, 2.5);
  sun.position.set(200, 300, 100);
  scene.add(sun);

  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;

  const started = performance.now();
  let gltf: GLTF;
  const assets = createGltfLoader(renderer);
  try {
    gltf = await assets.loader.loadAsync(src);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    publish({ ...base, status: "error", error: message, textures: [], extensionsUsed: [] });
    return;
  }
  const loadMs = performance.now() - started;
  scene.add(gltf.scene);
  frameModel(camera, controls, gltf.scene);

  const extensionsUsed = (gltf.parser.json as { extensionsUsed?: string[] }).extensionsUsed ?? [];
  const textures = collectTextures(gltf.scene).map(describeTexture);

  let reported = false;
  createLoop(() => {
    controls.update();
    renderer.render(scene, camera);
    if (reported) return;
    reported = true;
    publish({
      ...base,
      status: "ready",
      loadMs,
      triangles: renderer.info.render.triangles,
      drawCalls: renderer.info.render.calls,
      textures,
      extensionsUsed,
    });
  }).start();
}

void main();
