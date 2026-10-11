import type { DetailSet } from "./detailTextures";

export type QualityTier = "high" | "low";

export type QualityInputs = {
  /** The GPU is a software rasteriser (SwiftShader, llvmpipe, WARP): always `low`. */
  readonly softwareRenderer?: boolean | undefined;
  /** `(pointer: coarse)` matches: a phone or tablet. */
  readonly coarsePointer: boolean;
  /** `navigator.deviceMemory` (GB, capped at 8 by browsers); absent on Safari and Firefox. */
  readonly deviceMemoryGb?: number | undefined;
  /** `navigator.hardwareConcurrency`. */
  readonly cores?: number | undefined;
};

/** Phones need at least this much reported memory and this many cores to get `high`. */
export const MOBILE_HIGH_MIN_MEMORY_GB = 6;
export const MOBILE_HIGH_MIN_CORES = 6;
/** Below either of these a desktop falls back to `low` as well. */
export const DESKTOP_LOW_MAX_MEMORY_GB = 2;
export const DESKTOP_LOW_MAX_CORES = 2;

/**
 * Picks the terrain material tier. Conservative on touch devices: a browser that does not report
 * its memory (Safari) is treated as weak, because the real phone cost is not measured yet (T1.11).
 */
export function selectQualityTier(input: QualityInputs): QualityTier {
  const { coarsePointer, deviceMemoryGb, cores, softwareRenderer } = input;
  if (softwareRenderer === true) return "low";
  if (coarsePointer) {
    const strong =
      deviceMemoryGb !== undefined &&
      deviceMemoryGb >= MOBILE_HIGH_MIN_MEMORY_GB &&
      cores !== undefined &&
      cores >= MOBILE_HIGH_MIN_CORES;
    return strong ? "high" : "low";
  }
  const weak =
    (deviceMemoryGb !== undefined && deviceMemoryGb <= DESKTOP_LOW_MAX_MEMORY_GB) ||
    (cores !== undefined && cores <= DESKTOP_LOW_MAX_CORES);
  return weak ? "low" : "high";
}

const SOFTWARE_RENDERER = /swiftshader|llvmpipe|softpipe|software|basic render/i;

/** True for the unmasked renderer strings of CPU rasterisers. */
export function isSoftwareRenderer(rendererName: string): boolean {
  return SOFTWARE_RENDERER.test(rendererName);
}

/** Reads the unmasked WebGL2 renderer name on a throwaway canvas; null when unavailable. */
function probeRendererName(): string | null {
  const gl = document.createElement("canvas").getContext("webgl2");
  if (gl === null) return null;
  const info = gl.getExtension("WEBGL_debug_renderer_info");
  const name = info === null ? null : String(gl.getParameter(info.UNMASKED_RENDERER_WEBGL));
  gl.getExtension("WEBGL_lose_context")?.loseContext();
  return name;
}

/** Reads `?terrain=high|low` from a query string; anything else is no override. */
export function tierFromSearch(search: string): QualityTier | null {
  const value = new URLSearchParams(search).get("terrain");
  return value === "high" || value === "low" ? value : null;
}

/** The tier for this browser: the `?terrain=` override, else `selectQualityTier` on what it reports and the GPU. */
export function defaultQualityTier(): QualityTier {
  if (typeof window === "undefined") return "high";
  const override = tierFromSearch(window.location.search);
  if (override !== null) return override;
  const nav = navigator as Navigator & { deviceMemory?: number };
  return selectQualityTier({
    coarsePointer: window.matchMedia("(pointer: coarse)").matches,
    deviceMemoryGb: nav.deviceMemory,
    cores: nav.hardwareConcurrency,
    softwareRenderer: isSoftwareRenderer(probeRendererName() ?? ""),
  });
}

/**
 * Which marble map set a tier uses: none for `low`; 1k on touch devices (less memory and
 * download); 2k, loaded after the terrain settles, on desktops.
 */
export function selectDetailSet(tier: QualityTier, coarsePointer: boolean): DetailSet {
  if (tier === "low") return "off";
  return coarsePointer ? "1k" : "2k";
}

/** `selectDetailSet` for this browser. */
export function defaultDetailSet(tier: QualityTier): DetailSet {
  const coarse = typeof window !== "undefined" && window.matchMedia("(pointer: coarse)").matches;
  return selectDetailSet(tier, coarse);
}
