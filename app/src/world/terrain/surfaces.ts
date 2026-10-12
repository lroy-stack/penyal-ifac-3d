import {
  ClampToEdgeWrapping,
  type IUniform,
  type Material,
  Mesh,
  MeshStandardMaterial,
  NoColorSpace,
  type Object3D,
  RepeatWrapping,
  type Texture,
} from "three";
import { z } from "zod";
import { fetchChecked, NotFoundError } from "../../core/http";
import { addShaderPatch, type ShaderPatch } from "../../core/shaderPatch";
import { resolveAssetUrl } from "./manifest";

/**
 * Painted path surfaces (E1.3): the pipeline's per-tile class masks (`surfaces/t_*.ktx2`, linear
 * RGBA = cobblestone, compacted, paving stones, asphalt) are blended over the terrain colour by a
 * second shader patch. One patch, one program (all tiles share it by key), one uniform set per
 * tile material, zero extra draw calls.
 *
 * Colours (sRGB), sampled from the reference photo of the Ruta Roja
 * (`data/manual/fotos-referencia/commons/26-Le-sentier-du-penon-de-ifach-panoramio.jpg`):
 * - stone (cobblestone, paving): the sunlit slabs average (236, 228, 215) in the photo, which is
 *   exposure, not albedo; the albedo used is (214, 205, 188), a light limestone.
 * - compacted: the photo's earth (135, 107, 86) is shaded pine litter; the albedo used is the
 *   lighter dry earth (178, 150, 118).
 * - asphalt: mid-grey (107, 107, 107); no photo reference.
 * The structure on stone and earth is the provisional `rocks_ground_05` map (CREDITS.md), its
 * luminance relative to its own mean, near the camera only. Approximations, not surveyed.
 */
export const SURFACE_STONE_SRGB: readonly [number, number, number] = [214, 205, 188];
export const SURFACE_EARTH_SRGB: readonly [number, number, number] = [178, 150, 118];
export const SURFACE_ASPHALT_SRGB: readonly [number, number, number] = [107, 107, 107];
/** Coverage below `PAINT_LOW` is not painted: UASTC leaks up to 48/255 into neighbouring classes. */
export const PAINT_LOW = 0.2;
export const PAINT_HIGH = 0.7;
/** One repeat of the detail map (m). */
export const SURFACE_DETAIL_TILE_M = 2;
/** Detail strength on stone and on earth, and the camera distances (m) it fades out between. */
export const SURFACE_STONE_DETAIL = 0.9;
export const SURFACE_EARTH_DETAIL = 0.4;
export const SURFACE_FADE_START_M = 14;
export const SURFACE_FADE_END_M = 30;
export const SURFACE_PROGRAM_KEY = "penyal-surfaces-v1";
export const SURFACES_DETAIL_FILE = "rocks_ground_05_diff_1k.ktx2";

export type Rgb = readonly [number, number, number];

export function srgbToLinear(channel255: number): number {
  const c = channel255 / 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

const linear = (rgb: Rgb): Rgb => [
  srgbToLinear(rgb[0]),
  srgbToLinear(rgb[1]),
  srgbToLinear(rgb[2]),
];

function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = Math.min(1, Math.max(0, (x - edge0) / (edge1 - edge0)));
  return t * t * (3 - 2 * t);
}

export type SurfaceBlend = {
  /** The four class weights after the sum is clamped to 1 (cobblestone, compacted, paving, asphalt). */
  readonly weights: readonly [number, number, number, number];
  /** Clamped coverage, the sum of the weights. */
  readonly coverage: number;
  /** Share of the painted colour over the terrain colour: smooth in coverage, 0 for leaks. */
  readonly paint: number;
};

/**
 * Weights of a sampled mask pixel (each channel 0..1). The sum is clamped to 1 by scaling the
 * channels (consumerRequirement of the surfaces manifest). The GLSL does the same.
 */
export function surfaceBlend(mask: readonly [number, number, number, number]): SurfaceBlend {
  const sum = mask[0] + mask[1] + mask[2] + mask[3];
  const scale = 1 / Math.max(1, sum);
  const weights: [number, number, number, number] = [
    mask[0] * scale,
    mask[1] * scale,
    mask[2] * scale,
    mask[3] * scale,
  ];
  const coverage = weights[0] + weights[1] + weights[2] + weights[3];
  return { weights, coverage, paint: smoothstep(PAINT_LOW, PAINT_HIGH, coverage) };
}

/** Linear colour of a blend before the detail: the weighted mean of the class colours. */
export function surfaceColor(blend: SurfaceBlend): Rgb {
  const stone = linear(SURFACE_STONE_SRGB);
  const earth = linear(SURFACE_EARTH_SRGB);
  const asphalt = linear(SURFACE_ASPHALT_SRGB);
  const [cobble, compacted, paving, tarmac] = blend.weights;
  const divisor = Math.max(blend.coverage, 1e-4);
  const channel = (i: 0 | 1 | 2): number =>
    ((cobble + paving) * stone[i] + compacted * earth[i] + tarmac * asphalt[i]) / divisor;
  return [channel(0), channel(1), channel(2)];
}

const f = (value: number): string => value.toFixed(6);
const vec3 = (rgb: Rgb): string => `vec3( ${f(rgb[0])}, ${f(rgb[1])}, ${f(rgb[2])} )`;

const VERTEX_PARS = /* glsl */ `
varying highp vec2 vSurfXZ;
`;

const VERTEX_END = /* glsl */ `
	vSurfXZ = ( modelMatrix * vec4( transformed, 1.0 ) ).xz;
`;

const FRAGMENT_PARS = /* glsl */ `
varying highp vec2 vSurfXZ;
uniform sampler2D uSurfMask;
uniform float uSurfOn;
uniform sampler2D uSurfDetail;
uniform float uSurfDetailOn;
`;

const FRAGMENT_PAINT = /* glsl */ `
	#ifdef USE_MAP
	if ( uSurfOn > 0.5 ) {
		vec4 sMask = texture( uSurfMask, vMapUv );
		sMask /= max( 1.0, sMask.r + sMask.g + sMask.b + sMask.a );
		float sCover = sMask.r + sMask.g + sMask.b + sMask.a;
		float sPaint = smoothstep( ${f(PAINT_LOW)}, ${f(PAINT_HIGH)}, sCover );
		vec3 sColor = ( ( sMask.r + sMask.b ) * ${vec3(linear(SURFACE_STONE_SRGB))}
			+ sMask.g * ${vec3(linear(SURFACE_EARTH_SRGB))}
			+ sMask.a * ${vec3(linear(SURFACE_ASPHALT_SRGB))} ) / max( sCover, 1e-4 );
		if ( uSurfDetailOn > 0.5 ) {
			float sNear = 1.0 - smoothstep( ${f(SURFACE_FADE_START_M)}, ${f(SURFACE_FADE_END_M)}, length( vViewPosition ) );
			vec3 sTex = texture( uSurfDetail, vSurfXZ / ${f(SURFACE_DETAIL_TILE_M)} ).rgb;
			vec3 sMean = textureLod( uSurfDetail, vec2( 0.5 ), 16.0 ).rgb;
			float sRatio = clamp( dot( sTex, vec3( 0.2126, 0.7152, 0.0722 ) ) / ( dot( sMean, vec3( 0.2126, 0.7152, 0.0722 ) ) + 1e-4 ), 0.55, 1.5 );
			float sStrength = ( ( sMask.r + sMask.b ) * ${f(SURFACE_STONE_DETAIL)} + sMask.g * ${f(SURFACE_EARTH_DETAIL)} ) / max( sCover, 1e-4 );
			sColor *= mix( 1.0, sRatio, sStrength * sNear );
		}
		diffuseColor.rgb = mix( diffuseColor.rgb, sColor, sPaint );
	}
	#endif
`;

function replaceOnce(source: string, chunk: string, addition: string): string {
  const token = `#include <${chunk}>`;
  if (!source.includes(token)) {
    throw new Error(
      `three shader is missing #include <${chunk}>; the surfaces patch needs updating.`,
    );
  }
  return source.replace(token, `${token}\n${addition}`);
}

/** Pure text transform of the two stages; exported for tests. */
export function patchSurfacesShader(
  vertexShader: string,
  fragmentShader: string,
): { vertexShader: string; fragmentShader: string } {
  let vertex = replaceOnce(vertexShader, "common", VERTEX_PARS);
  vertex = replaceOnce(vertex, "fog_vertex", VERTEX_END);
  let fragment = replaceOnce(fragmentShader, "common", FRAGMENT_PARS);
  // After the terrain detail (which runs at color_fragment) so the paint covers its noise.
  fragment = replaceOnce(fragment, "roughnessmap_fragment", FRAGMENT_PAINT);
  return { vertexShader: vertex, fragmentShader: fragment };
}

export type SurfaceUniforms = {
  uSurfMask: IUniform<Texture | null>;
  uSurfOn: IUniform<number>;
  readonly uSurfDetail: IUniform<Texture | null>;
  readonly uSurfDetailOn: IUniform<number>;
};

export function surfacesPatch(uniforms: SurfaceUniforms): ShaderPatch {
  return { key: SURFACE_PROGRAM_KEY, uniforms, apply: patchSurfacesShader };
}

const manifestSchema = z.object({
  version: z.literal(1),
  tiles: z.array(z.object({ id: z.string(), url: z.string() })),
});

export type SurfaceStats = {
  /** Tiles with a LOD in the scene that the surfaces manifest has a mask for. */
  readonly resident: number;
  /** Of those, the masks that have loaded. */
  readonly loaded: number;
  readonly detail: boolean;
  /** The first unresolved failure (manifest, detail map or a tile mask), or null. */
  readonly error: string | null;
};

export type SurfaceMasks = {
  /** Patches the materials of a freshly loaded tile LOD and starts its tile's mask when needed. */
  readonly attach: (tileId: string, level: number, object: Object3D) => void;
  /** Call when a LOD leaves the scene; the mask is disposed with the tile's last LOD. */
  readonly release: (tileId: string, level: number) => void;
  readonly stats: () => SurfaceStats;
  readonly dispose: () => void;
};

export type SurfaceMasksOptions = {
  readonly loader: { readonly loadAsync: (url: string) => Promise<Texture> };
  /** URL of `surfaces/manifest.json`; tile masks are relative to it. */
  readonly manifestUrl: string;
  /** Load the detail map (not at the `low` tier: colour only). */
  readonly detail: boolean;
  /** Aborts the manifest request; `dispose` aborts it too. */
  readonly signal?: AbortSignal;
  /**
   * Called once for each new failure, with an actionable message. A mask that failed is tried
   * again when another LOD of its tile arrives, and its error clears when that load succeeds.
   */
  readonly onError?: (message: string) => void;
};

type TileRecord = {
  readonly lods: Map<number, SurfaceUniforms[]>;
  texture: Texture | null;
  started: boolean;
};

/**
 * Owns the masks of the resident tiles. A tile's mask loads when its first LOD becomes resident
 * (they are small: 1-50 KB each) and is disposed with its last. The detail map is shared. A
 * missing manifest or a failed load leaves the tile unpainted and records the error.
 */
export function createSurfaceMasks(options: SurfaceMasksOptions): SurfaceMasks {
  const { loader, manifestUrl, onError } = options;
  const controller = new AbortController();
  const abort = (): void => controller.abort(options.signal?.reason);
  if (options.signal?.aborted === true) abort();
  else options.signal?.addEventListener("abort", abort, { once: true });
  const { signal } = controller;
  const records = new Map<string, TileRecord>();
  const urls = new Map<string, string>();
  const shared = {
    uSurfDetail: { value: null as Texture | null },
    uSurfDetailOn: { value: 0 },
  };
  let detailTexture: Texture | null = null;
  const errors = new Map<string, string>();
  let disposed = false;
  let manifestReady = false;

  const fail = (key: string, what: string, cause: unknown): void => {
    if (signal.aborted || errors.has(key)) return;
    const reason = cause instanceof Error ? cause.message : String(cause);
    const message = `Painted path surfaces: ${what} failed (${reason}). The paths stay unpainted; check the files under assets/generated/surfaces/ or regenerate them with "penyal surfaces".`;
    errors.set(key, message);
    onError?.(message);
  };

  const startTile = (id: string, record: TileRecord): void => {
    const url = urls.get(id);
    if (record.started || url === undefined) return;
    record.started = true;
    loader.loadAsync(resolveAssetUrl(manifestUrl, url)).then(
      (texture) => {
        if (disposed || records.get(id) !== record) {
          texture.dispose();
          return;
        }
        texture.colorSpace = NoColorSpace;
        texture.wrapS = ClampToEdgeWrapping;
        texture.wrapT = ClampToEdgeWrapping;
        texture.flipY = false;
        errors.delete(`tile:${id}`);
        record.texture = texture;
        for (const sets of record.lods.values()) {
          for (const uniforms of sets) {
            uniforms.uSurfMask.value = texture;
            uniforms.uSurfOn.value = 1;
          }
        }
      },
      (cause: unknown) => {
        record.started = false;
        if (records.get(id) !== record) return;
        fail(`tile:${id}`, `the mask of tile ${id}`, cause);
      },
    );
  };

  const begin = async (): Promise<void> => {
    try {
      const opened = await fetchChecked(manifestUrl, signal);
      const manifest = manifestSchema.parse(await opened.read((r) => r.json()));
      for (const tile of manifest.tiles) urls.set(tile.id, tile.url);
    } catch (cause) {
      if (!(cause instanceof NotFoundError)) fail("manifest", "the manifest", cause);
      return;
    }
    if (disposed) return;
    manifestReady = true;
    for (const [id, record] of records) startTile(id, record);
  };

  if (options.detail) {
    const detailUrl = resolveAssetUrl(manifestUrl, `../materials/${SURFACES_DETAIL_FILE}`);
    loader.loadAsync(detailUrl).then(
      (texture) => {
        if (disposed) {
          texture.dispose();
          return;
        }
        texture.wrapS = RepeatWrapping;
        texture.wrapT = RepeatWrapping;
        texture.anisotropy = 8;
        detailTexture = texture;
        shared.uSurfDetail.value = texture;
        shared.uSurfDetailOn.value = 1;
      },
      (cause: unknown) => fail("detail", "the detail map", cause),
    );
  }
  void begin();

  return {
    attach(tileId, level, object) {
      if (disposed) return;
      let record = records.get(tileId);
      if (record === undefined) {
        record = { lods: new Map(), texture: null, started: false };
        records.set(tileId, record);
      }
      const current = record;
      const sets: SurfaceUniforms[] = [];
      object.traverse((child) => {
        if (!(child instanceof Mesh)) return;
        const materials = Array.isArray(child.material) ? child.material : [child.material];
        for (const material of materials as Material[]) {
          if (!(material instanceof MeshStandardMaterial)) continue;
          const uniforms: SurfaceUniforms = {
            uSurfMask: { value: current.texture },
            uSurfOn: { value: current.texture === null ? 0 : 1 },
            ...shared,
          };
          addShaderPatch(material, surfacesPatch(uniforms));
          sets.push(uniforms);
        }
      });
      current.lods.set(level, sets);
      if (manifestReady) startTile(tileId, current);
    },
    release(tileId, level) {
      const record = records.get(tileId);
      if (record === undefined) return;
      record.lods.delete(level);
      if (record.lods.size > 0) return;
      record.texture?.dispose();
      records.delete(tileId);
      errors.delete(`tile:${tileId}`);
    },
    stats() {
      const tracked = [...records.entries()].filter(([id]) => urls.has(id));
      return {
        resident: tracked.length,
        loaded: tracked.filter(([, record]) => record.texture !== null).length,
        detail: detailTexture !== null,
        error: errors.values().next().value ?? null,
      };
    },
    dispose() {
      disposed = true;
      options.signal?.removeEventListener("abort", abort);
      controller.abort();
      for (const record of records.values()) record.texture?.dispose();
      records.clear();
      detailTexture?.dispose();
      detailTexture = null;
      shared.uSurfDetail.value = null;
      shared.uSurfDetailOn.value = 0;
    },
  };
}
