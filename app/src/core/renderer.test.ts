import { afterEach, describe, expect, it, vi } from "vitest";
import { profileFor } from "./quality";
import { isWebGL2Available, pixelRatioFor } from "./renderer";

describe("pixelRatioFor", () => {
  const resolution = profileFor("medium", {
    coarsePointer: true,
    softwareRenderer: false,
  }).resolution;

  it("caps the screen's ratio at the profile's maximum", () => {
    expect(pixelRatioFor(3, resolution)).toBe(1.5);
    expect(pixelRatioFor(1, resolution)).toBe(1);
  });

  it("keeps the ratio exactly when the scale is 1", () => {
    expect(pixelRatioFor(2.625, { ...resolution, maxPixelRatio: 2 })).toBe(2);
  });

  it("multiplies by the scale the governor chose", () => {
    expect(pixelRatioFor(2, { maxPixelRatio: 2, scale: 0.8, minScale: 0.7 })).toBeCloseTo(1.6, 9);
  });
});

describe("isWebGL2Available", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("releases the probe context so it does not stay alive", () => {
    const loseContext = vi.fn();
    const gl = { getExtension: vi.fn(() => ({ loseContext })) };
    vi.stubGlobal("document", { createElement: () => ({ getContext: () => gl }) });

    expect(isWebGL2Available()).toBe(true);
    expect(gl.getExtension).toHaveBeenCalledWith("WEBGL_lose_context");
    expect(loseContext).toHaveBeenCalledOnce();
  });

  it("reports false when no context can be created", () => {
    vi.stubGlobal("document", { createElement: () => ({ getContext: () => null }) });

    expect(isWebGL2Available()).toBe(false);
  });

  it("tolerates a context without the lose-context extension", () => {
    const gl = { getExtension: () => null };
    vi.stubGlobal("document", { createElement: () => ({ getContext: () => gl }) });

    expect(isWebGL2Available()).toBe(true);
  });
});
