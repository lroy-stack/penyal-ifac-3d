import { MeshBasicMaterial, MeshStandardMaterial, ShaderLib } from "three";
import { describe, expect, it } from "vitest";
import {
  applyTerrainDetail,
  CLIFF_FULL_DEG,
  CLIFF_START_DEG,
  cliffWeight,
  createTerrainDetailUniforms,
  NEAR_FADE_END_M,
  NEAR_FADE_START_M,
  nearDetailWeight,
  patchTerrainShader,
  TERRAIN_PROGRAM_KEY,
} from "./material";

const normalYAt = (degrees: number): number => Math.cos((degrees * Math.PI) / 180);

describe("cliffWeight", () => {
  it("is 0 on flat and gentle ground and 1 from the full-cliff angle", () => {
    expect(cliffWeight(1)).toBe(0);
    expect(cliffWeight(normalYAt(30))).toBe(0);
    expect(cliffWeight(normalYAt(CLIFF_START_DEG))).toBeCloseTo(0, 9);
    expect(cliffWeight(normalYAt(CLIFF_FULL_DEG))).toBeCloseTo(1, 9);
    expect(cliffWeight(normalYAt(70))).toBe(1);
    expect(cliffWeight(0)).toBe(1);
  });

  it("rises monotonically and smoothly with the slope", () => {
    let previous = cliffWeight(normalYAt(0));
    for (let deg = 1; deg <= 90; deg += 1) {
      const w = cliffWeight(normalYAt(deg));
      expect(w).toBeGreaterThanOrEqual(previous);
      expect(w - previous).toBeLessThan(0.2);
      previous = w;
    }
  });

  it("covers every face steeper than 55 degrees completely", () => {
    for (let deg = 55; deg <= 90; deg += 5) expect(cliffWeight(normalYAt(deg))).toBeCloseTo(1, 9);
  });
});

describe("nearDetailWeight", () => {
  it("is full close to the camera and gone beyond the fade end", () => {
    expect(nearDetailWeight(0)).toBe(1);
    expect(nearDetailWeight(NEAR_FADE_START_M)).toBe(1);
    expect(nearDetailWeight(NEAR_FADE_END_M)).toBe(0);
    expect(nearDetailWeight(500)).toBe(0);
    expect(nearDetailWeight((NEAR_FADE_START_M + NEAR_FADE_END_M) / 2)).toBeCloseTo(0.5, 9);
  });
});

describe("patchTerrainShader", () => {
  const { vertexShader, fragmentShader } = ShaderLib.physical;
  const patched = patchTerrainShader(vertexShader, fragmentShader);

  it("hooks the world position and normal into the vertex stage", () => {
    expect(patched.vertexShader).toContain("vTerrainWorldPos = ( modelMatrix");
    expect(patched.vertexShader.indexOf("#include <fog_vertex>")).toBeLessThan(
      patched.vertexShader.indexOf("vTerrainWorldPos = "),
    );
  });

  it("adds the albedo block after color_fragment and the bump after normal_fragment_maps", () => {
    const f = patched.fragmentShader;
    expect(f.indexOf("#include <color_fragment>")).toBeLessThan(f.indexOf("float tCliff"));
    expect(f.indexOf("#include <normal_fragment_maps>")).toBeLessThan(
      f.indexOf("normal = terrainBump"),
    );
    expect(f.indexOf("#include <map_fragment>")).toBeLessThan(f.indexOf("float tCliff"));
  });

  it("uses the same slope thresholds as cliffWeight", () => {
    expect(patched.fragmentShader).toContain(normalYAt(CLIFF_START_DEG).toFixed(6));
    expect(patched.fragmentShader).toContain(normalYAt(CLIFF_FULL_DEG).toFixed(6));
  });

  it("fails loudly when a chunk it hooks into is missing", () => {
    expect(() => patchTerrainShader("void main() {}", fragmentShader)).toThrow(/common/);
  });
});

describe("applyTerrainDetail", () => {
  it("gives every patched material the same program key and shares the uniforms", () => {
    const uniforms = createTerrainDetailUniforms();
    const a = new MeshStandardMaterial();
    const b = new MeshStandardMaterial();
    applyTerrainDetail(a, uniforms);
    applyTerrainDetail(b, uniforms);
    expect(a.customProgramCacheKey()).toBe(TERRAIN_PROGRAM_KEY);
    expect(b.customProgramCacheKey()).toBe(a.customProgramCacheKey());

    const shader = {
      uniforms: {} as Record<string, unknown>,
      vertexShader: ShaderLib.physical.vertexShader,
      fragmentShader: ShaderLib.physical.fragmentShader,
    };
    // biome-ignore lint/suspicious/noExplicitAny: the callback is typed for the renderer's full parameters.
    a.onBeforeCompile(shader as any, undefined as any);
    expect(shader.uniforms.uTerrainCliffStrength).toBe(uniforms.uTerrainCliffStrength);
    expect(shader.fragmentShader).toContain("terrainRock");
  });

  it("leaves other materials untouched", () => {
    const basic = new MeshBasicMaterial();
    const before = basic.onBeforeCompile;
    applyTerrainDetail(basic, createTerrainDetailUniforms());
    expect(basic.onBeforeCompile).toBe(before);
  });
});
