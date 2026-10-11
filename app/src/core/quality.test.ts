import { describe, expect, it } from "vitest";
import {
  type DeviceInfo,
  isSoftwareRenderer,
  profileFor,
  type QualityTier,
  resolveInitialProfile,
  selectInitialTier,
  tierFromSearch,
} from "./quality";

const DESKTOP: DeviceInfo = { coarsePointer: false, softwareRenderer: false };
const PHONE: DeviceInfo = { coarsePointer: true, softwareRenderer: false };

describe("selectInitialTier", () => {
  it("gives desktops with unreported or ample hardware the high tier", () => {
    expect(selectInitialTier(DESKTOP)).toBe("high");
    expect(selectInitialTier({ ...DESKTOP, deviceMemoryGb: 8, cores: 8 })).toBe("high");
  });

  it("drops weak desktops to low", () => {
    expect(selectInitialTier({ ...DESKTOP, deviceMemoryGb: 2, cores: 8 })).toBe("low");
    expect(selectInitialTier({ ...DESKTOP, deviceMemoryGb: 8, cores: 2 })).toBe("low");
  });

  it("treats touch devices as low unless they report a strong machine, then medium", () => {
    expect(selectInitialTier(PHONE)).toBe("low");
    expect(selectInitialTier({ ...PHONE, cores: 8 })).toBe("low");
    expect(selectInitialTier({ ...PHONE, deviceMemoryGb: 4, cores: 8 })).toBe("low");
    expect(selectInitialTier({ ...PHONE, deviceMemoryGb: 8, cores: 8 })).toBe("medium");
  });

  it("never gives a phone the high tier", () => {
    expect(selectInitialTier({ ...PHONE, deviceMemoryGb: 8, cores: 16 })).toBe("medium");
  });

  it("is low on a software renderer whatever the hardware", () => {
    expect(selectInitialTier({ ...DESKTOP, cores: 16, softwareRenderer: true })).toBe("low");
  });
});

describe("isSoftwareRenderer", () => {
  it("recognises CPU rasterisers", () => {
    expect(isSoftwareRenderer("ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero)))")).toBe(
      true,
    );
    expect(isSoftwareRenderer("llvmpipe (LLVM 15.0.7, 256 bits)")).toBe(true);
    expect(
      isSoftwareRenderer("ANGLE (Apple, ANGLE Metal Renderer: Apple M1 Pro, Unspecified Version)"),
    ).toBe(false);
  });
});

describe("tierFromSearch", () => {
  it("reads ?quality=low|medium|high and ignores anything else", () => {
    expect(tierFromSearch("?quality=low")).toBe("low");
    expect(tierFromSearch("?start=summit&quality=medium")).toBe("medium");
    expect(tierFromSearch("?quality=high")).toBe("high");
    expect(tierFromSearch("?quality=ultra")).toBeNull();
    expect(tierFromSearch("?terrain=high")).toBeNull();
    expect(tierFromSearch("")).toBeNull();
  });
});

describe("profileFor", () => {
  it("fills the knob table of ADR 0010 for a desktop", () => {
    const [low, medium, high] = (["low", "medium", "high"] as const).map((tier) =>
      profileFor(tier, DESKTOP),
    );
    expect([low?.tier, medium?.tier, high?.tier]).toEqual(["low", "medium", "high"]);
    expect([low, medium, high].map((p) => p?.resolution.minScale)).toEqual([0.6, 0.7, 0.8]);
    expect([low, medium, high].map((p) => p?.resolution.scale)).toEqual([1, 1, 1]);
    expect([low, medium, high].map((p) => p?.terrain.detail)).toEqual(["off", "1k", "2k"]);
    expect([low, medium, high].map((p) => p?.shadows)).toEqual(["none", "baked", "cascaded"]);
    expect([low, medium, high].map((p) => p?.vegetation)).toEqual([
      { density: 0.35, maxDistanceM: 60 },
      { density: 0.7, maxDistanceM: 120 },
      { density: 1, maxDistanceM: 200 },
    ]);
    expect([low, medium, high].map((p) => p?.sea)).toEqual(["flat", "waves", "waves-foam"]);
    expect([low, medium, high].map((p) => p?.textures)).toEqual(["1k", "1k", "2k"]);
  });

  it("keeps 1k maps and textures on touch devices even in high", () => {
    const high = profileFor("high", PHONE);
    expect(high.terrain.detail).toBe("1k");
    expect(high.textures).toBe("1k");
  });

  it("caps the pixel ratio at 1.5 on touch devices and 2 on the others", () => {
    expect(profileFor("medium", PHONE).resolution.maxPixelRatio).toBe(1.5);
    expect(profileFor("medium", DESKTOP).resolution.maxPixelRatio).toBe(2);
  });

  it("allows 4 px of screen-space error on touch devices and 2 px on the others", () => {
    expect(profileFor("low", PHONE).terrain.sseThresholdPx).toBe(4);
    expect(profileFor("low", DESKTOP).terrain.sseThresholdPx).toBe(2);
  });

  it("is a heuristic profile", () => {
    expect(profileFor("low", DESKTOP).source).toBe("heuristic");
  });
});

describe("resolveInitialProfile", () => {
  it("uses the heuristic tier without parameters", () => {
    const profile = resolveInitialProfile(DESKTOP, "");
    expect(profile.tier).toBe("high");
    expect(profile.source).toBe("heuristic");
  });

  it("lets ?quality= set the tier", () => {
    const profile = resolveInitialProfile(
      { ...DESKTOP, softwareRenderer: true },
      "?quality=medium",
    );
    expect(profile.tier).toBe("medium");
    expect(profile.source).toBe("override");
    expect(profile.terrain.detail).toBe("1k");
  });

  it("lets ?terrain= decide the terrain detail only", () => {
    const software = { ...DESKTOP, softwareRenderer: true };
    const high = resolveInitialProfile(software, "?terrain=high");
    expect(high.tier).toBe("low");
    expect(high.source).toBe("override");
    expect(high.terrain.detail).toBe("2k");
    expect(high.shadows).toBe("none");
    expect(resolveInitialProfile(PHONE, "?terrain=high").terrain.detail).toBe("1k");
    const low = resolveInitialProfile(DESKTOP, "?terrain=low");
    expect(low.tier).toBe("high");
    expect(low.terrain.detail).toBe("off");
  });

  it("gives ?terrain= priority over the detail of ?quality=", () => {
    const profile = resolveInitialProfile(DESKTOP, "?quality=high&terrain=low");
    expect(profile.tier).toBe("high");
    expect(profile.terrain.detail).toBe("off");
  });

  it("ignores values it does not know", () => {
    const profile = resolveInitialProfile(DESKTOP, "?quality=ultra&terrain=max");
    expect(profile.tier).toBe("high");
    expect(profile.source).toBe("heuristic");
  });
});

// The terrain quality before the three-tier profile, written out as the oracle of the refactor:
// the same inputs must give the same terrain shading, map size, error budget and pixel ratio.
type OldInputs = {
  softwareRenderer?: boolean | undefined;
  coarsePointer: boolean;
  deviceMemoryGb?: number | undefined;
  cores?: number | undefined;
};

function oldTier(input: OldInputs): "high" | "low" {
  const { coarsePointer, deviceMemoryGb, cores, softwareRenderer } = input;
  if (softwareRenderer === true) return "low";
  if (coarsePointer) {
    const strong =
      deviceMemoryGb !== undefined && deviceMemoryGb >= 6 && cores !== undefined && cores >= 6;
    return strong ? "high" : "low";
  }
  const weak =
    (deviceMemoryGb !== undefined && deviceMemoryGb <= 2) || (cores !== undefined && cores <= 2);
  return weak ? "low" : "high";
}

function oldDetailSet(tier: "high" | "low", coarsePointer: boolean): "off" | "1k" | "2k" {
  if (tier === "low") return "off";
  return coarsePointer ? "1k" : "2k";
}

describe("equivalence with the two-tier terrain quality", () => {
  const memories = [undefined, 0.5, 1, 2, 3, 4, 5, 6, 7, 8];
  const coreCounts = [undefined, 1, 2, 3, 4, 5, 6, 8, 16];
  const cases: DeviceInfo[] = [];
  for (const coarsePointer of [false, true]) {
    for (const softwareRenderer of [false, true]) {
      for (const deviceMemoryGb of memories) {
        for (const cores of coreCounts) {
          cases.push({ coarsePointer, softwareRenderer, deviceMemoryGb, cores });
        }
      }
    }
  }

  it("covers every combination of the inputs", () => {
    expect(cases).toHaveLength(2 * 2 * memories.length * coreCounts.length);
  });

  it("gives the same terrain detail set, error budget and pixel ratio", () => {
    for (const device of cases) {
      const old = oldTier(device);
      const profile = resolveInitialProfile(device, "");
      const label = JSON.stringify(device);
      expect(profile.terrain.detail, label).toBe(oldDetailSet(old, device.coarsePointer));
      expect(profile.terrain.sseThresholdPx, label).toBe(device.coarsePointer ? 4 : 2);
      expect(profile.resolution.maxPixelRatio, label).toBe(device.coarsePointer ? 1.5 : 2);
      expect(profile.resolution.scale, label).toBe(1);
    }
  });

  it("keeps the old override ?terrain=low|high", () => {
    for (const device of cases) {
      for (const tier of ["low", "high"] as const) {
        const profile = resolveInitialProfile(device, `?terrain=${tier}`);
        expect(profile.terrain.detail, JSON.stringify(device)).toBe(
          oldDetailSet(tier, device.coarsePointer),
        );
      }
    }
  });

  it("never gives a tier above what the old rule allowed", () => {
    const rank: Record<QualityTier, number> = { low: 0, medium: 1, high: 2 };
    for (const device of cases) {
      const tier = selectInitialTier(device);
      if (oldTier(device) === "low") expect(rank[tier], JSON.stringify(device)).toBe(0);
    }
  });
});
