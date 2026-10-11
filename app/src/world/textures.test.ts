import {
  CompressedTexture,
  DataTexture,
  Group,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  PlaneGeometry,
  RGB_ETC2_Format,
  ShaderMaterial,
  SRGBColorSpace,
  Texture,
} from "three";
import { describe, expect, it } from "vitest";
import { addShaderPatch } from "../core/shaderPatch";
import { collectTextures } from "./textures";

const geometry = new PlaneGeometry();

function data(width: number, height: number): DataTexture {
  const texture = new DataTexture(new Uint8Array(width * height * 4), width, height);
  texture.colorSpace = SRGBColorSpace;
  return texture;
}

describe("collectTextures", () => {
  it("reads the size and format of material maps", () => {
    const root = new Group();
    root.add(new Mesh(geometry, new MeshBasicMaterial({ map: data(8, 4) })));
    const [sample] = collectTextures(root);
    expect(sample).toMatchObject({ width: 8, height: 4, compressed: false });
  });

  it("reads compressed textures from their first mip level", () => {
    const texture = new CompressedTexture(
      [
        { data: new Uint8Array(8), width: 8, height: 8 },
        { data: new Uint8Array(2), width: 4, height: 4 },
      ],
      8,
      8,
      RGB_ETC2_Format,
    );
    const root = new Group();
    root.add(new Mesh(geometry, new MeshStandardMaterial({ map: texture })));
    expect(collectTextures(root)).toEqual([
      { width: 8, height: 8, format: RGB_ETC2_Format, compressed: true, mips: true },
    ]);
  });

  it("counts a texture shared by two materials once", () => {
    const shared = data(4, 4);
    const root = new Group();
    root.add(new Mesh(geometry, new MeshBasicMaterial({ map: shared })));
    root.add(new Mesh(geometry, new MeshBasicMaterial({ map: shared })));
    expect(collectTextures(root)).toHaveLength(1);
  });

  it("finds the textures of ShaderMaterial uniforms and of shared shader-patch uniforms", () => {
    const root = new Group();
    const detail = data(16, 16);
    const material = new MeshStandardMaterial();
    addShaderPatch(material, {
      key: "test-v1",
      uniforms: { uDetail: { value: detail }, uNumber: { value: 3 } },
      apply: (vertexShader, fragmentShader) => ({ vertexShader, fragmentShader }),
    });
    root.add(new Mesh(geometry, material));
    root.add(new Mesh(geometry, new ShaderMaterial({ uniforms: { uMap: { value: data(2, 2) } } })));
    const sizes = collectTextures(root)
      .map((sample) => sample.width)
      .sort((a, b) => a - b);
    expect(sizes).toEqual([2, 16]);
  });

  it("skips textures with no image yet", () => {
    const root = new Group();
    root.add(new Mesh(geometry, new MeshBasicMaterial({ map: new Texture() })));
    expect(collectTextures(root)).toEqual([]);
  });

  it("ignores objects without a material", () => {
    const root = new Group();
    root.add(new Group());
    expect(collectTextures(root)).toEqual([]);
  });
});
