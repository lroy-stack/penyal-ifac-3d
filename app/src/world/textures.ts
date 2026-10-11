import { CompressedTexture, type Material, type Mesh, type Object3D, Texture } from "three";
import { shaderPatchUniforms } from "../core/shaderPatch";

/** What the texture-memory estimate needs of one GPU texture. */
export type TextureSample = {
  readonly width: number;
  readonly height: number;
  /** three's texture format constant. */
  readonly format: number;
  readonly compressed: boolean;
  readonly mips: boolean;
};

function sampleOf(texture: Texture): TextureSample | null {
  if (texture instanceof CompressedTexture) {
    const level = texture.mipmaps[0];
    if (level === undefined) return null;
    return {
      width: level.width,
      height: level.height,
      format: texture.format,
      compressed: true,
      mips: texture.mipmaps.length > 1,
    };
  }
  const image = texture.image as { width?: number; height?: number } | null;
  if (image?.width === undefined || image.height === undefined) return null;
  return {
    width: image.width,
    height: image.height,
    format: texture.format,
    compressed: false,
    mips: texture.generateMipmaps,
  };
}

function texturesOf(material: Material, found: Set<Texture>): void {
  for (const value of Object.values(material)) if (value instanceof Texture) found.add(value);
  const uniforms = (material as { uniforms?: Record<string, { value: unknown }> }).uniforms;
  for (const uniform of Object.values(uniforms ?? {})) {
    if (uniform.value instanceof Texture) found.add(uniform.value);
  }
  for (const uniform of Object.values(shaderPatchUniforms(material))) {
    if (uniform.value instanceof Texture) found.add(uniform.value);
  }
}

/**
 * The distinct textures under `root` (material maps, shader uniforms and the uniforms shared by
 * shader patches, such as the terrain detail maps), for the budget E2E. Textures with no image
 * yet are skipped.
 */
export function collectTextures(root: Object3D): TextureSample[] {
  const found = new Set<Texture>();
  root.traverse((object) => {
    const material = (object as Mesh).material as Material | Material[] | undefined;
    if (material === undefined) return;
    for (const entry of Array.isArray(material) ? material : [material]) texturesOf(entry, found);
  });
  const samples: TextureSample[] = [];
  for (const texture of found) {
    const sample = sampleOf(texture);
    if (sample !== null) samples.push(sample);
  }
  return samples;
}
