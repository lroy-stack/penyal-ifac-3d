import {
  RGB_ETC1_Format,
  RGB_ETC2_Format,
  RGB_S3TC_DXT1_Format,
  RGBA_ASTC_4x4_Format,
  RGBA_BPTC_Format,
  RGBA_ETC2_EAC_Format,
  RGBA_S3TC_DXT3_Format,
  RGBA_S3TC_DXT5_Format,
} from "three";
import type { QualityTier } from "./quality";

/**
 * Per-system budget (ADR 0010, section 4 and Amendment 1), for the `medium` tier on the
 * reference phone. A static table the E2E (`budget.spec.ts`) checks by switching systems off;
 * production code never reads it.
 */
export type SystemBudget = {
  readonly drawCalls: number;
  readonly triangles: number;
  /** GPU time per frame (ms). Reported, and enforced only once `MS_CALIBRATION` is set. */
  readonly ms: number;
  /** Estimated resident texture memory, mips included, in the worst resident set (MiB). */
  readonly textureMiB: number;
};

export type FrameBudget = {
  readonly drawCallsTarget: number;
  readonly drawCallsCap: number;
  readonly trianglesCap: number;
  /** Provisional until A7: WebGL has no GPU-memory query, so this is a design ceiling. */
  readonly textureMiBCap: number;
};

export const FRAME_BUDGET: Readonly<Record<QualityTier, FrameBudget>> = {
  low: { drawCallsTarget: 100, drawCallsCap: 200, trianglesCap: 1_000_000, textureMiBCap: 32 },
  medium: { drawCallsTarget: 100, drawCallsCap: 200, trianglesCap: 1_000_000, textureMiBCap: 48 },
  high: { drawCallsTarget: 100, drawCallsCap: 200, trianglesCap: 1_500_000, textureMiBCap: 160 },
};

const b = (drawCalls: number, triangles: number, ms: number, textureMiB: number): SystemBudget => ({
  drawCalls,
  triangles,
  ms,
  textureMiB,
});

/**
 * Calls, triangles and ms follow the spec and the ADR; the triangle figures and every texture
 * figure are provisional. Texture rows: terrain is its near tiles (10.7 MiB if all 16 are at
 * LOD0), the far ring (2.7), the surface masks (10.7 worst) and the detail maps (5.3 at 1k, 21.3
 * at 2k); the rest are placeholders sized for their lane until it measures.
 */
export const SYSTEM_BUDGETS: Readonly<Record<QualityTier, Readonly<Record<string, SystemBudget>>>> =
  {
    low: {
      atmosphere: b(0, 0, 0.1, 0),
      sky: b(2, 5_000, 1, 0),
      terrain: b(25, 350_000, 6, 20),
      tunnel: b(3, 10_000, 0.5, 1),
      sea: b(1, 2, 3, 1),
      vegetation: b(20, 100_000, 6, 2),
      structures: b(13, 58_000, 1, 3),
      buildings: b(2, 2_000, 0, 0),
      character: b(5, 20_000, 1, 1),
      shadows: b(0, 0, 0, 0),
      poi: b(2, 2_000, 0.2, 1),
      audio: b(0, 0, 0.5, 0),
    },
    medium: {
      atmosphere: b(0, 0, 0.1, 0),
      sky: b(2, 5_000, 1, 0),
      terrain: b(25, 350_000, 6, 30),
      tunnel: b(3, 10_000, 0.5, 2),
      sea: b(3, 50_000, 3, 1),
      vegetation: b(40, 250_000, 6, 4),
      structures: b(13, 58_000, 1, 4),
      buildings: b(2, 2_000, 0, 0),
      character: b(5, 20_000, 1, 2),
      shadows: b(0, 0, 0, 0),
      poi: b(2, 2_000, 0.2, 1),
      audio: b(0, 0, 0.5, 0),
    },
    high: {
      atmosphere: b(0, 0, 0.1, 0),
      sky: b(2, 5_000, 1, 0),
      terrain: b(25, 350_000, 6, 48),
      tunnel: b(3, 10_000, 0.5, 4),
      sea: b(3, 50_000, 3, 4),
      vegetation: b(50, 400_000, 6, 8),
      structures: b(13, 58_000, 1, 8),
      buildings: b(2, 2_000, 0, 0),
      character: b(5, 20_000, 1, 4),
      shadows: b(60, 400_000, 5, 40),
      poi: b(2, 2_000, 0.2, 2),
      audio: b(0, 0, 0.5, 0),
    },
  };

/**
 * Desktop-Metal to reference-phone factor for the ms figures, from A7. While it is null the
 * E2E only reports ms.
 */
export const MS_CALIBRATION: number | null = null;

export type BudgetTotals = {
  readonly drawCalls: number;
  readonly triangles: number;
  readonly ms: number;
  readonly textureMiB: number;
};

/** Sum of every system's row for a tier. */
export function budgetTotals(tier: QualityTier): BudgetTotals {
  const rows = Object.values(SYSTEM_BUDGETS[tier]);
  const sum = (pick: (row: SystemBudget) => number): number =>
    rows.reduce((total, row) => total + pick(row), 0);
  return {
    drawCalls: sum((row) => row.drawCalls),
    triangles: sum((row) => row.triangles),
    ms: sum((row) => row.ms),
    textureMiB: sum((row) => row.textureMiB),
  };
}

/** Ids with no row in the tier tables. `debug-*` systems are exempt. */
export function missingBudgetRows(ids: readonly string[]): string[] {
  return ids.filter(
    (id) =>
      !id.startsWith("debug-") &&
      !(["low", "medium", "high"] as const).every((tier) => id in SYSTEM_BUDGETS[tier]),
  );
}

/** For dev and E2E builds: a registered system without a budget row stops the boot. */
export function assertBudgeted(ids: readonly string[]): void {
  const missing = missingBudgetRows(ids);
  if (missing.length > 0) {
    throw new Error(
      `No budget row for the world system(s) ${missing.map((id) => `"${id}"`).join(", ")}. Add a row per tier to SYSTEM_BUDGETS in app/src/core/budget.ts.`,
    );
  }
}

/** How a texture is stored on a phone: the transcode target decides the bytes per pixel. */
export type TextureFormat = "etc1s-rgb" | "etc1s-rgba" | "uastc" | "rgba8";

const BYTES_PER_PIXEL: Readonly<Record<TextureFormat, number>> = {
  "etc1s-rgb": 0.5,
  "etc1s-rgba": 1,
  uastc: 1,
  rgba8: 4,
};

/** A full mip chain adds a third on top of the base level. */
const MIP_FACTOR = 4 / 3;

/** Estimated GPU bytes of one texture: base level, times 4/3 with a mip chain. */
export function textureBytes(
  width: number,
  height: number,
  format: TextureFormat,
  mips: boolean,
): number {
  return width * height * BYTES_PER_PIXEL[format] * (mips ? MIP_FACTOR : 1);
}

const COMPRESSED_HALF_BYTE: ReadonlySet<number> = new Set([
  RGB_S3TC_DXT1_Format,
  RGB_ETC1_Format,
  RGB_ETC2_Format,
]);
const COMPRESSED_ONE_BYTE: ReadonlySet<number> = new Set([
  RGBA_S3TC_DXT3_Format,
  RGBA_S3TC_DXT5_Format,
  RGBA_ETC2_EAC_Format,
  RGBA_ASTC_4x4_Format,
  RGBA_BPTC_Format,
]);

/**
 * The storage class of a three texture: compressed formats of 4 bits per pixel are ETC1S RGB
 * (0.5 B/px), those of 8 bits are ETC1S RGBA or UASTC (1 B/px), anything else is counted as
 * uncompressed RGBA8. Estimating by bits per pixel keeps the figure the same on the transcode
 * target of the test machine and the phone's.
 */
export function classifyTexture(format: number, compressed: boolean): TextureFormat {
  if (compressed && COMPRESSED_HALF_BYTE.has(format)) return "etc1s-rgb";
  if (compressed && COMPRESSED_ONE_BYTE.has(format)) return "uastc";
  return "rgba8";
}

/** MiB of an estimate in bytes. */
export const toMiB = (bytes: number): number => bytes / (1024 * 1024);
