import { describe, expect, it } from "vitest";
import { type DeviceInfo, profileFor, resolveInitialProfile } from "../../core/quality";
import { terrainOptions } from "./quality";

const DESKTOP: DeviceInfo = { coarsePointer: false, softwareRenderer: false };
const PHONE: DeviceInfo = { coarsePointer: true, softwareRenderer: false };

describe("terrainOptions", () => {
  it("keeps the plain orthophoto and no maps in the low tier", () => {
    expect(terrainOptions(profileFor("low", DESKTOP))).toEqual({
      quality: "low",
      detailSet: "off",
      sseThreshold: 2,
    });
  });

  it("uses the 1k maps and 4 px of error on a phone", () => {
    expect(terrainOptions(profileFor("medium", PHONE))).toEqual({
      quality: "high",
      detailSet: "1k",
      sseThreshold: 4,
    });
  });

  it("uses the 2k maps on a desktop in the high tier", () => {
    expect(terrainOptions(profileFor("high", DESKTOP))).toEqual({
      quality: "high",
      detailSet: "2k",
      sseThreshold: 2,
    });
  });

  it("follows the ?terrain= override over the tier", () => {
    const software = { ...DESKTOP, softwareRenderer: true };
    expect(terrainOptions(resolveInitialProfile(software, "?terrain=high")).detailSet).toBe("2k");
    expect(terrainOptions(resolveInitialProfile(DESKTOP, "?terrain=low")).quality).toBe("low");
  });
});
