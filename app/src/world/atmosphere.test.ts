import { Color, MeshStandardMaterial, ShaderLib, ShaderMaterial } from "three";
import { describe, expect, it } from "vitest";
import { addShaderPatch } from "../core/shaderPatch";
import {
  ATMOSPHERE_PATCH_KEY,
  type AtmosphereState,
  attachAtmosphere,
  createAtmosphere,
  readOnlyAtmosphere,
} from "./atmosphere";
import { createTerrainDetailUniforms, terrainDetailPatch } from "./terrain/material";

const rgb = (hex: number) => {
  const c = new Color(hex);
  return { r: c.r, g: c.g, b: c.b };
};

function dayState(): AtmosphereState {
  return {
    preset: "day",
    sun: { direction: { x: 0.5, y: 0.75, z: 0.6 }, color: rgb(0xfff1d6), intensity: 2.6 },
    ambient: { sky: rgb(0xcfe6ff), ground: rgb(0x6b5a3c), intensity: 1.1 },
    horizon: rgb(0xbcd6ea),
    zenith: rgb(0x4f8fd0),
    fog: { color: rgb(0xbcd6ea), near: 242.8, far: 1214, sunScatter: 0 },
    toneMapping: "aces",
    exposure: 1,
  };
}

describe("createAtmosphere", () => {
  it("starts at version 0 with the uniforms written from the initial state", () => {
    const atmosphere = createAtmosphere(dayState());
    expect(atmosphere.version).toBe(0);
    expect(atmosphere.state.preset).toBe("day");
    const { uniforms } = atmosphere;
    expect(uniforms.uAtmoSunDirection.value.toArray()).toEqual([0.5, 0.75, 0.6]);
    expect(uniforms.uAtmoHorizon.value.getHex()).toBe(new Color(0xbcd6ea).getHex());
    expect(uniforms.uAtmoFog.value.toArray()).toEqual([242.8, 1214, 0, 0]);
  });

  it("stores the sun colour times its intensity", () => {
    const atmosphere = createAtmosphere(dayState());
    const expected = new Color(0xfff1d6).multiplyScalar(2.6);
    expect(atmosphere.uniforms.uAtmoSunColor.value.toArray()).toEqual(expected.toArray());
  });

  it("adds one to the version per write", () => {
    const atmosphere = createAtmosphere(dayState());
    atmosphere.set({ exposure: 1.2 });
    expect(atmosphere.version).toBe(1);
    atmosphere.set({ preset: "sunset" });
    atmosphere.set({});
    expect(atmosphere.version).toBe(3);
  });

  it("replaces only the fields it is given", () => {
    const atmosphere = createAtmosphere(dayState());
    atmosphere.set({ preset: "sunset", exposure: 0.8 });
    expect(atmosphere.state.preset).toBe("sunset");
    expect(atmosphere.state.exposure).toBe(0.8);
    expect(atmosphere.state.toneMapping).toBe("aces");
    expect(atmosphere.state.horizon).toEqual(rgb(0xbcd6ea));
  });

  it("updates the uniforms in place: same objects, new values", () => {
    const atmosphere = createAtmosphere(dayState());
    const before = { ...atmosphere.uniforms };
    const values = {
      sun: before.uAtmoSunDirection.value,
      colour: before.uAtmoSunColor.value,
      fog: before.uAtmoFog.value,
    };
    atmosphere.set({
      sun: { direction: { x: 0, y: 1, z: 0 }, color: { r: 1, g: 0.5, b: 0.25 }, intensity: 2 },
      fog: { color: rgb(0xffffff), near: 10, far: 100, sunScatter: 0.5 },
    });
    expect(atmosphere.uniforms.uAtmoSunDirection).toBe(before.uAtmoSunDirection);
    expect(atmosphere.uniforms.uAtmoSunColor).toBe(before.uAtmoSunColor);
    expect(atmosphere.uniforms.uAtmoFog).toBe(before.uAtmoFog);
    expect(before.uAtmoSunDirection.value).toBe(values.sun);
    expect(before.uAtmoSunColor.value).toBe(values.colour);
    expect(before.uAtmoFog.value).toBe(values.fog);
    expect(values.sun.toArray()).toEqual([0, 1, 0]);
    expect(values.colour.toArray()).toEqual([2, 1, 0.5]);
    expect(values.fog.toArray()).toEqual([10, 100, 0.5, 0]);
  });
});

describe("readOnlyAtmosphere", () => {
  it("follows the writer live but offers no way to write", () => {
    const writer = createAtmosphere(dayState());
    const view = readOnlyAtmosphere(writer);
    writer.set({ exposure: 2 });
    expect(view.state.exposure).toBe(2);
    expect(view.version).toBe(1);
    expect(view.uniforms).toBe(writer.uniforms);
    expect("set" in view).toBe(false);
    expect((view as unknown as { set?: unknown }).set).toBeUndefined();
  });
});

describe("attachAtmosphere", () => {
  it("composes after the terrain detail: the key is the two keys joined", () => {
    const material = new MeshStandardMaterial();
    addShaderPatch(material, terrainDetailPatch(createTerrainDetailUniforms()));
    attachAtmosphere(material, createAtmosphere(dayState()));
    expect(material.customProgramCacheKey()).toBe("penyal-terrain-detail-v4|penyal-atmosphere-v1");
    expect(ATMOSPHERE_PATCH_KEY).toBe("penyal-atmosphere-v1");
  });

  it("is idempotent", () => {
    const material = new MeshStandardMaterial();
    const atmosphere = createAtmosphere(dayState());
    attachAtmosphere(material, atmosphere);
    attachAtmosphere(material, atmosphere, { kind: "terrain-tile", tileId: "x" });
    expect(material.customProgramCacheKey()).toBe(ATMOSPHERE_PATCH_KEY);
  });

  it("shares the live uniforms with the compiled program, not copies", () => {
    const material = new MeshStandardMaterial();
    const atmosphere = createAtmosphere(dayState());
    attachAtmosphere(material, atmosphere);
    const shader = {
      uniforms: {} as Record<string, unknown>,
      vertexShader: ShaderLib.physical.vertexShader,
      fragmentShader: ShaderLib.physical.fragmentShader,
    };
    // biome-ignore lint/suspicious/noExplicitAny: the callback is typed for the renderer's full parameters.
    material.onBeforeCompile(shader as any, undefined as any);
    expect(shader.uniforms.uAtmoFog).toBe(atmosphere.uniforms.uAtmoFog);
    expect(shader.uniforms.uAtmoSunColor).toBe(atmosphere.uniforms.uAtmoSunColor);
    expect(shader.fragmentShader).toBe(ShaderLib.physical.fragmentShader);
  });

  it("puts the uniforms of a ShaderMaterial in its own table, and a clone attaches again", () => {
    const atmosphere = createAtmosphere(dayState());
    const material = new ShaderMaterial({ uniforms: {} });
    attachAtmosphere(material, atmosphere);
    expect(material.uniforms.uAtmoFog).toBe(atmosphere.uniforms.uAtmoFog);

    const clone = material.clone();
    expect(clone.uniforms.uAtmoFog).not.toBe(atmosphere.uniforms.uAtmoFog);
    attachAtmosphere(clone, atmosphere);
    expect(clone.uniforms.uAtmoFog).toBe(atmosphere.uniforms.uAtmoFog);
  });
});
