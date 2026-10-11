import type { IUniform, Material, WebGLProgramParametersWithUniforms } from "three";

/** A text transform of a built-in three shader, with the uniforms it reads. */
export type ShaderPatch = {
  /** Versioned (`penyal-<name>-v<n>`); bump it on any GLSL change so three builds a new program. */
  readonly key: string;
  /** Shared by reference with the compiled program: writing `value` reaches every material. */
  readonly uniforms: Readonly<Record<string, IUniform>>;
  readonly apply: (
    vertexShader: string,
    fragmentShader: string,
  ) => { vertexShader: string; fragmentShader: string };
};

const patchesOf = new WeakMap<Material, ShaderPatch[]>();

/**
 * Adds a patch to a material. A material has one `onBeforeCompile` that applies its patches in
 * the order they were added, and its program cache key is their keys joined by "|", so materials
 * with the same patches share one program (three's default key is the source of the callback,
 * which would be the same for every patch). Adding a key the material already has does nothing.
 */
export function addShaderPatch(material: Material, patch: ShaderPatch): void {
  const patches = patchesOf.get(material) ?? [];
  if (patches.some((existing) => existing.key === patch.key)) return;
  patches.push(patch);
  patchesOf.set(material, patches);

  material.onBeforeCompile = (shader: WebGLProgramParametersWithUniforms) => {
    for (const applied of patches) {
      Object.assign(shader.uniforms, applied.uniforms);
      const patched = applied.apply(shader.vertexShader, shader.fragmentShader);
      shader.vertexShader = patched.vertexShader;
      shader.fragmentShader = patched.fragmentShader;
    }
  };
  material.customProgramCacheKey = () => patches.map((applied) => applied.key).join("|");
  material.needsUpdate = true;
}

/** The uniforms of every patch of a material, shared by reference (the budget E2E reads textures from them). */
export function shaderPatchUniforms(material: Material): Record<string, IUniform> {
  return Object.assign({}, ...(patchesOf.get(material) ?? []).map((patch) => patch.uniforms));
}
