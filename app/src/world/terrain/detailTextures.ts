import { RepeatWrapping, type Texture } from "three";
import type { TerrainDetailUniforms } from "./material";

/** `off`: procedural noise only. `1k` / `2k`: the marble maps at that resolution. */
export type DetailSet = "off" | "1k" | "2k";
export type DetailSource = "procedural" | "1k" | "2k";

export const DETAIL_ANISOTROPY = 8;

/** The one external loader this needs; `KTX2Loader` satisfies it. */
export type TextureLoader = { readonly loadAsync: (url: string) => Promise<Texture> };

type Maps = { readonly diff: Texture; readonly nor: Texture; readonly arm: Texture };

/** File name of a map, as written by `scripts/make-material-textures.mjs`. */
export function detailFileName(map: "diff" | "nor_gl" | "arm", size: "1k" | "2k"): string {
  return `marble_cliff_05_${map}_${size}.ktx2`;
}

export type DetailTextures = {
  /** What the shader is using right now. */
  readonly source: () => DetailSource;
  /** Call every frame with whether the terrain has settled; starts the 2k load once it has. */
  readonly settled: (isSettled: boolean) => void;
  readonly dispose: () => void;
  readonly lastError: () => string | null;
};

export type DetailTexturesOptions = {
  readonly loader: TextureLoader | null;
  /** URL of a file from `detailFileName`. */
  readonly urlFor: (fileName: string) => string;
  readonly uniforms: TerrainDetailUniforms;
  readonly set: DetailSet;
};

function configure(texture: Texture): Texture {
  texture.wrapS = RepeatWrapping;
  texture.wrapT = RepeatWrapping;
  texture.anisotropy = DETAIL_ANISOTROPY;
  return texture;
}

/**
 * Loads the marble maps and hands them to the shared terrain uniforms. The 1k set starts at once;
 * the 2k set (`set === "2k"`) starts only after the terrain has settled so it never competes with
 * tile streaming, then replaces the 1k set. A failed load keeps whatever is already in use (at
 * worst the procedural noise) and records the error.
 */
export function createDetailTextures(options: DetailTexturesOptions): DetailTextures {
  const { loader, urlFor, uniforms, set } = options;
  let current: Maps | null = null;
  let source: DetailSource = "procedural";
  let error: string | null = null;
  let disposed = false;
  let upgradeStarted = false;

  const loadSet = async (size: "1k" | "2k"): Promise<Maps> => {
    if (loader === null) throw new Error("no KTX2 loader");
    const [diff, nor, arm] = await Promise.all([
      loader.loadAsync(urlFor(detailFileName("diff", size))),
      loader.loadAsync(urlFor(detailFileName("nor_gl", size))),
      loader.loadAsync(urlFor(detailFileName("arm", size))),
    ]);
    return { diff: configure(diff), nor: configure(nor), arm: configure(arm) };
  };

  const install = (maps: Maps, size: "1k" | "2k"): void => {
    if (disposed) {
      for (const t of Object.values(maps)) t.dispose();
      return;
    }
    const previous = current;
    current = maps;
    uniforms.uRockDiff.value = maps.diff;
    uniforms.uRockNor.value = maps.nor;
    uniforms.uRockArm.value = maps.arm;
    uniforms.uRockMode.value = 1;
    source = size;
    if (previous !== null) for (const t of Object.values(previous)) t.dispose();
  };

  const start = (size: "1k" | "2k"): void => {
    loadSet(size).then(
      (maps) => install(maps, size),
      (cause: unknown) => {
        error = `detail textures ${size}: ${cause instanceof Error ? cause.message : String(cause)}`;
      },
    );
  };

  if (set !== "off" && loader !== null) start("1k");

  return {
    source: () => source,
    lastError: () => error,
    settled: (isSettled) => {
      if (!isSettled || set !== "2k" || upgradeStarted || loader === null || source !== "1k")
        return;
      upgradeStarted = true;
      start("2k");
    },
    dispose: () => {
      disposed = true;
      if (current !== null) for (const t of Object.values(current)) t.dispose();
      current = null;
      uniforms.uRockMode.value = 0;
      uniforms.uRockDiff.value = null;
      uniforms.uRockNor.value = null;
      uniforms.uRockArm.value = null;
    },
  };
}
