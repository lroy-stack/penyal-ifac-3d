import { describe, expect, it } from "vitest";
import { isSoftwareRenderer, selectDetailSet, selectQualityTier, tierFromSearch } from "./quality";

describe("selectQualityTier", () => {
  it("gives desktops with unreported or ample hardware the high tier", () => {
    expect(selectQualityTier({ coarsePointer: false })).toBe("high");
    expect(selectQualityTier({ coarsePointer: false, deviceMemoryGb: 8, cores: 8 })).toBe("high");
  });

  it("drops weak desktops to low", () => {
    expect(selectQualityTier({ coarsePointer: false, deviceMemoryGb: 2, cores: 8 })).toBe("low");
    expect(selectQualityTier({ coarsePointer: false, deviceMemoryGb: 8, cores: 2 })).toBe("low");
  });

  it("treats touch devices as low unless they report a strong machine", () => {
    expect(selectQualityTier({ coarsePointer: true })).toBe("low");
    expect(selectQualityTier({ coarsePointer: true, cores: 8 })).toBe("low");
    expect(selectQualityTier({ coarsePointer: true, deviceMemoryGb: 4, cores: 8 })).toBe("low");
    expect(selectQualityTier({ coarsePointer: true, deviceMemoryGb: 8, cores: 8 })).toBe("high");
  });
});

describe("software renderers", () => {
  it("recognises CPU rasterisers and forces the low tier", () => {
    expect(isSoftwareRenderer("ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero)))")).toBe(
      true,
    );
    expect(isSoftwareRenderer("llvmpipe (LLVM 15.0.7, 256 bits)")).toBe(true);
    expect(
      isSoftwareRenderer("ANGLE (Apple, ANGLE Metal Renderer: Apple M1 Pro, Unspecified Version)"),
    ).toBe(false);
    expect(selectQualityTier({ coarsePointer: false, cores: 16, softwareRenderer: true })).toBe(
      "low",
    );
  });
});

describe("tierFromSearch", () => {
  it("reads ?terrain=high|low and ignores anything else", () => {
    expect(tierFromSearch("?terrain=low")).toBe("low");
    expect(tierFromSearch("?start=summit&terrain=high")).toBe("high");
    expect(tierFromSearch("?terrain=ultra")).toBeNull();
    expect(tierFromSearch("")).toBeNull();
  });
});

describe("selectDetailSet", () => {
  it("uses no maps in low, 1k on touch devices and 2k on desktops", () => {
    expect(selectDetailSet("low", false)).toBe("off");
    expect(selectDetailSet("low", true)).toBe("off");
    expect(selectDetailSet("high", true)).toBe("1k");
    expect(selectDetailSet("high", false)).toBe("2k");
  });
});
