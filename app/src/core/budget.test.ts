import { describe, expect, it } from "vitest";
import {
  assertBudgeted,
  budgetTotals,
  classifyTexture,
  FRAME_BUDGET,
  MS_CALIBRATION,
  missingBudgetRows,
  SYSTEM_BUDGETS,
  textureBytes,
  toMiB,
} from "./budget";
import type { QualityTier } from "./quality";

const TIERS: readonly QualityTier[] = ["low", "medium", "high"];

describe("system budgets", () => {
  it("sums to 95 calls, 747k triangles and 19.3 ms in medium", () => {
    const totals = budgetTotals("medium");
    expect(totals.drawCalls).toBe(95);
    expect(totals.triangles).toBe(747_000);
    expect(totals.ms).toBeCloseTo(19.3, 9);
  });

  it("sums to 73 calls in low and 165 in high", () => {
    expect(budgetTotals("low").drawCalls).toBe(73);
    expect(budgetTotals("high").drawCalls).toBe(165);
  });

  it("changes only vegetation, sea and shadows between tiers (calls and triangles)", () => {
    const { low, medium, high } = SYSTEM_BUDGETS;
    expect(low.vegetation).toMatchObject({ drawCalls: 20, triangles: 100_000 });
    expect(low.sea).toMatchObject({ drawCalls: 1, triangles: 2 });
    expect(high.vegetation).toMatchObject({ drawCalls: 50, triangles: 400_000 });
    expect(high.shadows).toMatchObject({ drawCalls: 60, triangles: 400_000, ms: 5 });
    for (const id of Object.keys(medium)) {
      if (["vegetation", "sea", "shadows"].includes(id)) continue;
      for (const tier of [low, high]) {
        expect(tier[id]?.drawCalls, id).toBe(medium[id]?.drawCalls);
        expect(tier[id]?.triangles, id).toBe(medium[id]?.triangles);
      }
    }
  });

  it("has the same systems in every tier", () => {
    const ids = Object.keys(SYSTEM_BUDGETS.medium).sort();
    for (const tier of TIERS) expect(Object.keys(SYSTEM_BUDGETS[tier]).sort()).toEqual(ids);
  });

  it("stays under the frame caps in every tier", () => {
    for (const tier of TIERS) {
      const totals = budgetTotals(tier);
      const cap = FRAME_BUDGET[tier];
      expect(totals.drawCalls, tier).toBeLessThanOrEqual(cap.drawCallsCap);
      expect(totals.triangles, tier).toBeLessThanOrEqual(cap.trianglesCap);
      expect(totals.textureMiB, tier).toBeLessThanOrEqual(cap.textureMiBCap);
    }
  });

  it("targets 100 calls with a cap of 200, and 1M triangles (1.5M in high)", () => {
    for (const tier of TIERS) {
      expect(FRAME_BUDGET[tier].drawCallsTarget).toBe(100);
      expect(FRAME_BUDGET[tier].drawCallsCap).toBe(200);
    }
    expect(FRAME_BUDGET.low.trianglesCap).toBe(1_000_000);
    expect(FRAME_BUDGET.medium.trianglesCap).toBe(1_000_000);
    expect(FRAME_BUDGET.high.trianglesCap).toBe(1_500_000);
  });

  it("caps texture memory at 32, 48 and 160 MiB (provisional until A7)", () => {
    expect(TIERS.map((tier) => FRAME_BUDGET[tier].textureMiBCap)).toEqual([32, 48, 160]);
  });

  it("keeps the calls target for medium and leaves headroom under it", () => {
    expect(budgetTotals("medium").drawCalls).toBeLessThanOrEqual(
      FRAME_BUDGET.medium.drawCallsTarget,
    );
  });

  it("leaves ms uncalibrated until A7", () => {
    expect(MS_CALIBRATION).toBeNull();
  });
});

describe("registry check", () => {
  it("finds ids without a row and exempts debug systems", () => {
    expect(missingBudgetRows(["sky", "terrain", "debug-trail", "grass"])).toEqual(["grass"]);
  });

  it("throws, naming the id and the file to edit", () => {
    expect(() => assertBudgeted(["sky", "grass"])).toThrow(/"grass".*SYSTEM_BUDGETS/);
    expect(() => assertBudgeted(["sky", "debug-trail"])).not.toThrow();
  });

  it("has a row for every system the world registers today", () => {
    expect(missingBudgetRows(["atmosphere", "sky", "sea", "terrain", "tunnel", "poi"])).toEqual([]);
  });
});

describe("textureBytes", () => {
  const side = 1024;

  it("is half a byte per pixel for ETC1S RGB", () => {
    expect(textureBytes(side, side, "etc1s-rgb", false)).toBe(side * side * 0.5);
  });

  it("is one byte per pixel for ETC1S RGBA and for UASTC", () => {
    expect(textureBytes(side, side, "etc1s-rgba", false)).toBe(side * side);
    expect(textureBytes(side, side, "uastc", false)).toBe(side * side);
  });

  it("is four bytes per pixel for uncompressed RGBA8", () => {
    expect(textureBytes(side, side, "rgba8", false)).toBe(side * side * 4);
  });

  it("adds a third for the mip chain", () => {
    expect(textureBytes(side, side, "rgba8", true)).toBeCloseTo(side * side * 4 * (4 / 3), 6);
  });

  it("reproduces the amendment's figures", () => {
    // 16 near tiles at LOD0 1024x1024 ETC1S RGB, mips included: 10.7 MiB.
    expect(toMiB(16 * textureBytes(1024, 1024, "etc1s-rgb", true))).toBeCloseTo(10.67, 2);
    // Detail maps at 1k: four 1024x1024 maps of 1 B/px, mips included: 5.3 MiB (the amendment's
    // 21.3 MiB at 2k is four times that).
    expect(toMiB(4 * textureBytes(1024, 1024, "etc1s-rgba", true))).toBeCloseTo(5.33, 2);
    expect(toMiB(4 * textureBytes(2048, 2048, "etc1s-rgba", true))).toBeCloseTo(21.33, 2);
  });
});

describe("classifyTexture", () => {
  it("maps the compressed formats by their bits per pixel", () => {
    expect(classifyTexture(33776, true)).toBe("etc1s-rgb"); // RGB_S3TC_DXT1
    expect(classifyTexture(37492, true)).toBe("etc1s-rgb"); // RGB_ETC2
    expect(classifyTexture(37496, true)).toBe("uastc"); // RGBA_ETC2_EAC
    expect(classifyTexture(37808, true)).toBe("uastc"); // RGBA_ASTC_4x4
  });

  it("counts everything else as uncompressed", () => {
    expect(classifyTexture(1023, false)).toBe("rgba8");
    expect(classifyTexture(37496, false)).toBe("rgba8");
  });
});
