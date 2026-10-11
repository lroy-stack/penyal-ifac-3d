import { afterEach, describe, expect, it, vi } from "vitest";
import { isWebGL2Available, maxPixelRatio } from "./renderer";

describe("maxPixelRatio", () => {
  it("caps coarse-pointer devices at 1.5", () => {
    expect(maxPixelRatio(true)).toBe(1.5);
  });

  it("caps other devices at 2", () => {
    expect(maxPixelRatio(false)).toBe(2);
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
