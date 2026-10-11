import type { WebGLRenderer } from "three";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { KTX2Loader } from "three/addons/loaders/KTX2Loader.js";

/** Vite's `base` (always ends with "/"); the app may be hosted under a sub-path. */
export function baseUrl(): string {
  return import.meta.env.BASE_URL;
}

/** URL of a file under `public/`, honouring the deployment base path. */
export function publicUrl(path: string, base: string = baseUrl()): string {
  return `${base}${path.replace(/^\/+/, "")}`;
}

export function basisTranscoderPath(base: string = baseUrl()): string {
  return publicUrl("decoders/basis/", base);
}

export const BASIS_TRANSCODER_PATH = basisTranscoderPath();

export type GltfLoaderHandle = {
  readonly loader: GLTFLoader;
  /** Terminates the KTX2 worker pool. Call once, when the renderer goes away. */
  readonly dispose: () => void;
};

/**
 * One GLTFLoader backed by one KTX2Loader (one transcoder worker pool). Create it once per
 * renderer and share it; a second KTX2Loader would load the transcoder and spawn workers again.
 */
export function createGltfLoader(renderer: WebGLRenderer): GltfLoaderHandle {
  const ktx2Loader = new KTX2Loader();
  ktx2Loader.setTranscoderPath(BASIS_TRANSCODER_PATH);
  ktx2Loader.detectSupport(renderer);
  // Fetch the transcoder now instead of when the first tile is parsed: it downloads alongside
  // the far mesh and no round trip is spent waiting for it. Failures surface when a texture is
  // parsed, so the rejection is not handled here.
  ktx2Loader.init().catch(() => undefined);

  const loader = new GLTFLoader();
  loader.setKTX2Loader(ktx2Loader);
  loader.setMeshoptDecoder(MeshoptDecoder);
  return { loader, dispose: () => ktx2Loader.dispose() };
}

export type AssetProvider = {
  /** One lazy GLTF + KTX2 loader per page: created by the first system that asks. */
  readonly gltf: () => GLTFLoader;
  /** URL of a file under `public/`. */
  readonly url: (path: string) => string;
  /** Terminates the KTX2 workers when a loader was created; call once, with the renderer. */
  readonly dispose: () => void;
};

export function createAssetProvider(
  renderer: WebGLRenderer,
  base: string = baseUrl(),
): AssetProvider {
  let handle: GltfLoaderHandle | null = null;
  return {
    gltf: () => {
      handle ??= createGltfLoader(renderer);
      return handle.loader;
    },
    url: (path) => publicUrl(path, base),
    dispose: () => handle?.dispose(),
  };
}
