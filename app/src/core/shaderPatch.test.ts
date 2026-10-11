import { MeshBasicMaterial, MeshStandardMaterial, ShaderLib } from "three";
import { describe, expect, it } from "vitest";
import { addShaderPatch, type ShaderPatch } from "./shaderPatch";

type Compile = (shader: unknown, renderer: unknown) => void;

function patch(key: string, marker: string, uniforms: ShaderPatch["uniforms"] = {}): ShaderPatch {
  return {
    key,
    uniforms,
    apply: (vertexShader, fragmentShader) => ({
      vertexShader: `${vertexShader}\n// vertex ${marker}`,
      fragmentShader: `${fragmentShader}\n// fragment ${marker}`,
    }),
  };
}

function compile(material: MeshStandardMaterial) {
  const shader = {
    uniforms: {} as Record<string, unknown>,
    vertexShader: "// vertex base",
    fragmentShader: "// fragment base",
  };
  (material.onBeforeCompile as Compile)(shader, undefined);
  return shader;
}

describe("addShaderPatch", () => {
  it("keeps the patch key as the program cache key when there is one patch", () => {
    const material = new MeshStandardMaterial();
    addShaderPatch(material, patch("penyal-terrain-detail-v4", "a"));
    expect(material.customProgramCacheKey()).toBe("penyal-terrain-detail-v4");
  });

  it("joins the keys with a pipe, in the order the patches were added", () => {
    const material = new MeshStandardMaterial();
    addShaderPatch(material, patch("one-v1", "a"));
    addShaderPatch(material, patch("two-v1", "b"));
    expect(material.customProgramCacheKey()).toBe("one-v1|two-v1");
  });

  it("applies the patches in order inside a single onBeforeCompile", () => {
    const material = new MeshStandardMaterial();
    addShaderPatch(material, patch("one-v1", "a"));
    addShaderPatch(material, patch("two-v1", "b"));
    const shader = compile(material);
    expect(shader.vertexShader).toBe("// vertex base\n// vertex a\n// vertex b");
    expect(shader.fragmentShader).toBe("// fragment base\n// fragment a\n// fragment b");
  });

  it("shares the patch uniforms with the program by reference", () => {
    const material = new MeshStandardMaterial();
    const shared = { value: 1 };
    addShaderPatch(material, patch("one-v1", "a", { uShared: shared }));
    const shader = compile(material);
    expect(shader.uniforms.uShared).toBe(shared);
  });

  it("ignores a second patch with a key the material already has", () => {
    const material = new MeshStandardMaterial();
    const first = { value: 1 };
    addShaderPatch(material, patch("one-v1", "a", { uShared: first }));
    const handler = material.onBeforeCompile;
    addShaderPatch(material, patch("one-v1", "again", { uShared: { value: 2 } }));
    expect(material.customProgramCacheKey()).toBe("one-v1");
    expect(material.onBeforeCompile).toBe(handler);
    const shader = compile(material);
    expect(shader.fragmentShader).toBe("// fragment base\n// fragment a");
    expect(shader.uniforms.uShared).toBe(first);
  });

  it("gives materials with the same patches the same key so they share one program", () => {
    const a = new MeshStandardMaterial();
    const b = new MeshStandardMaterial();
    for (const material of [a, b]) {
      addShaderPatch(material, patch("one-v1", "a"));
      addShaderPatch(material, patch("two-v1", "b"));
    }
    expect(a.customProgramCacheKey()).toBe(b.customProgramCacheKey());
  });

  it("keeps the patches of each material separate", () => {
    const a = new MeshStandardMaterial();
    const b = new MeshStandardMaterial();
    addShaderPatch(a, patch("one-v1", "a"));
    addShaderPatch(b, patch("two-v1", "b"));
    expect(a.customProgramCacheKey()).toBe("one-v1");
    expect(b.customProgramCacheKey()).toBe("two-v1");
  });

  it("asks three to recompile the material", () => {
    const material = new MeshStandardMaterial();
    const before = material.version;
    addShaderPatch(material, patch("one-v1", "a"));
    expect(material.version).toBeGreaterThan(before);
  });

  it("works on any material, with the shader library stages as input", () => {
    const material = new MeshBasicMaterial();
    addShaderPatch(material, patch("one-v1", "a"));
    expect(material.customProgramCacheKey()).toBe("one-v1");
    const shader = {
      uniforms: {} as Record<string, unknown>,
      vertexShader: ShaderLib.basic.vertexShader,
      fragmentShader: ShaderLib.basic.fragmentShader,
    };
    (material.onBeforeCompile as Compile)(shader, undefined);
    expect(shader.fragmentShader.endsWith("// fragment a")).toBe(true);
  });
});
