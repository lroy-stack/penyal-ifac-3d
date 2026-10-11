export type QualityTier = "low" | "medium" | "high";

export type DeviceInfo = {
  /** `(pointer: coarse)` matches: a phone or tablet. */
  readonly coarsePointer: boolean;
  /** `navigator.deviceMemory` (GB, capped at 8 by browsers); absent on Safari and Firefox. */
  readonly deviceMemoryGb?: number | undefined;
  /** `navigator.hardwareConcurrency`. */
  readonly cores?: number | undefined;
  /** The GPU is a software rasteriser (SwiftShader, llvmpipe, WARP): always `low`. */
  readonly softwareRenderer: boolean;
};

export type QualityProfile = {
  readonly tier: QualityTier;
  readonly source: "heuristic" | "override" | "startup" | "downgrade";
  readonly resolution: {
    readonly maxPixelRatio: number;
    /** Share of the pixel ratio actually rendered; 1 until the governor lowers it. */
    readonly scale: number;
    readonly minScale: number;
  };
  readonly terrain: {
    /** Marble map set of the terrain detail shading: none, 1k or 2k. */
    readonly detail: "off" | "1k" | "2k";
    readonly sseThresholdPx: number;
  };
  readonly shadows: "none" | "baked" | "cascaded";
  readonly vegetation: { readonly density: number; readonly maxDistanceM: number };
  readonly sea: "flat" | "waves" | "waves-foam";
  readonly textures: "1k" | "2k";
};

/** Phones need at least this much reported memory and this many cores to get `medium`. */
export const MOBILE_MEDIUM_MIN_MEMORY_GB = 6;
export const MOBILE_MEDIUM_MIN_CORES = 6;
/** Below either of these a desktop falls back to `low` as well. */
export const DESKTOP_LOW_MAX_MEMORY_GB = 2;
export const DESKTOP_LOW_MAX_CORES = 2;

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

/** What this browser reports about the device. The only effectful function of this module. */
export function probeDevice(): DeviceInfo {
  const nav = navigator as Navigator & { deviceMemory?: number };
  return {
    coarsePointer: window.matchMedia("(pointer: coarse)").matches,
    deviceMemoryGb: nav.deviceMemory,
    cores: nav.hardwareConcurrency,
    softwareRenderer: isSoftwareRenderer(probeRendererName() ?? ""),
  };
}

/**
 * The tier a device starts in. Conservative on touch devices: a browser that does not report its
 * memory (Safari) is treated as weak, because the real phone cost is not measured yet (T1.11).
 */
export function selectInitialTier(device: DeviceInfo): QualityTier {
  const { coarsePointer, deviceMemoryGb, cores, softwareRenderer } = device;
  if (softwareRenderer) return "low";
  if (coarsePointer) {
    const strong =
      deviceMemoryGb !== undefined &&
      deviceMemoryGb >= MOBILE_MEDIUM_MIN_MEMORY_GB &&
      cores !== undefined &&
      cores >= MOBILE_MEDIUM_MIN_CORES;
    return strong ? "medium" : "low";
  }
  const weak =
    (deviceMemoryGb !== undefined && deviceMemoryGb <= DESKTOP_LOW_MAX_MEMORY_GB) ||
    (cores !== undefined && cores <= DESKTOP_LOW_MAX_CORES);
  return weak ? "low" : "high";
}

type TierKnobs = Pick<QualityProfile, "shadows" | "vegetation" | "sea"> & {
  readonly minScale: number;
};

/** Per-tier knobs that do not depend on the device. Vegetation and sea values are provisional (L3, L4). */
const TIER_KNOBS: Readonly<Record<QualityTier, TierKnobs>> = {
  low: {
    minScale: 0.6,
    shadows: "none",
    vegetation: { density: 0.35, maxDistanceM: 60 },
    sea: "flat",
  },
  medium: {
    minScale: 0.7,
    shadows: "baked",
    vegetation: { density: 0.7, maxDistanceM: 120 },
    sea: "waves",
  },
  high: {
    minScale: 0.8,
    shadows: "cascaded",
    vegetation: { density: 1, maxDistanceM: 200 },
    sea: "waves-foam",
  },
};

/** Marble maps: none in `low`; 1k on touch devices (less memory and download); 2k on desktops. */
function terrainDetail(tier: QualityTier, coarsePointer: boolean): "off" | "1k" | "2k" {
  if (tier === "low") return "off";
  if (tier === "medium") return "1k";
  return coarsePointer ? "1k" : "2k";
}

export function profileFor(tier: QualityTier, device: DeviceInfo): QualityProfile {
  const knobs = TIER_KNOBS[tier];
  return {
    tier,
    source: "heuristic",
    resolution: {
      maxPixelRatio: device.coarsePointer ? 1.5 : 2,
      scale: 1,
      minScale: knobs.minScale,
    },
    terrain: {
      detail: terrainDetail(tier, device.coarsePointer),
      sseThresholdPx: device.coarsePointer ? 4 : 2,
    },
    shadows: knobs.shadows,
    vegetation: knobs.vegetation,
    sea: knobs.sea,
    textures: tier === "high" && !device.coarsePointer ? "2k" : "1k",
  };
}

function tierParameter(search: string, name: string): string | null {
  return new URLSearchParams(search).get(name);
}

/** Reads `?quality=low|medium|high`; anything else is no override. */
export function tierFromSearch(search: string): QualityTier | null {
  const value = tierParameter(search, "quality");
  return value === "low" || value === "medium" || value === "high" ? value : null;
}

/**
 * The profile for this load: the heuristic tier or the `?quality=` override. `?terrain=low|high`
 * keeps its terrain-only meaning and wins over the tier for the terrain detail.
 */
export function resolveInitialProfile(device: DeviceInfo, search: string): QualityProfile {
  const requested = tierFromSearch(search);
  const base = profileFor(requested ?? selectInitialTier(device), device);
  const terrain = tierParameter(search, "terrain");
  const detail =
    terrain === "low"
      ? "off"
      : terrain === "high"
        ? terrainDetail("high", device.coarsePointer)
        : base.terrain.detail;
  const overridden = requested !== null || terrain === "low" || terrain === "high";
  return {
    ...base,
    source: overridden ? "override" : "heuristic",
    terrain: { ...base.terrain, detail },
  };
}

export type GovernorDecision =
  | { readonly kind: "keep" }
  | { readonly kind: "scale"; readonly scale: number }
  | {
      readonly kind: "tier";
      readonly tier: QualityTier;
      readonly source: "startup" | "downgrade";
    };

export type GovernorOptions = {
  /** Walking time ignored at the start (ms). */
  readonly skipMs: number;
  /** Startup measurement window (ms) and the p50 frame time (ms) above which one tier is dropped. */
  readonly startupMs: number;
  readonly startupP50Ms: number;
  /** Minimum time between changes (ms) and the most tier changes per session. */
  readonly cooldownMs: number;
  readonly maxTierChanges: number;
};

/** Implemented with B11, after the first real-phone measurement (A7). */
export interface QualityGovernor {
  /** Raw rAF interval of a visible walking frame; pure. */
  push(frameMs: number, nowMs: number): GovernorDecision;
  readonly snapshot: {
    readonly tier: QualityTier;
    readonly scale: number;
    readonly downgrades: number;
  };
}
