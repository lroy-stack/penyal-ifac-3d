import { Color, type IUniform, type Material, ShaderMaterial, Vector3, Vector4 } from "three";
import { addShaderPatch } from "../core/shaderPatch";
import type { LocalPoint } from "../geo/frame";

type Vec3 = LocalPoint;

/** Linear colour in three's working space (what `new Color(hex)` holds). */
export type Rgb = { readonly r: number; readonly g: number; readonly b: number };

export type AtmosphereState = {
  readonly preset: "day" | "sunset";
  /** `direction` is a unit vector towards the sun. */
  readonly sun: { readonly direction: Vec3; readonly color: Rgb; readonly intensity: number };
  readonly ambient: { readonly sky: Rgb; readonly ground: Rgb; readonly intensity: number };
  readonly horizon: Rgb;
  readonly zenith: Rgb;
  /** `sunScatter` 0 means plain fog. */
  readonly fog: {
    readonly color: Rgb;
    readonly near: number;
    readonly far: number;
    readonly sunScatter: number;
  };
  readonly toneMapping: "aces" | "agx";
  readonly exposure: number;
};

export type AtmosphereUniforms = {
  readonly uAtmoSunDirection: IUniform<Vector3>;
  /** Colour times intensity. */
  readonly uAtmoSunColor: IUniform<Color>;
  readonly uAtmoHorizon: IUniform<Color>;
  readonly uAtmoZenith: IUniform<Color>;
  /** near, far, sunScatter, 0. */
  readonly uAtmoFog: IUniform<Vector4>;
};

export interface AtmosphereReader {
  readonly state: AtmosphereState;
  /** +1 per write; readers compare it with the version they last applied. */
  readonly version: number;
  /** Live and shared by reference with every material that attached them; never cloned. */
  readonly uniforms: AtmosphereUniforms;
}

export interface AtmosphereWriter extends AtmosphereReader {
  /** Replaces the given fields, updates the uniforms in place and bumps `version`. */
  set(next: Partial<AtmosphereState>): void;
}

export type AtmosphereSurface =
  | { readonly kind: "generic" }
  | { readonly kind: "terrain-tile"; readonly tileId: string };

/** Identifies the atmosphere block in three's program cache; bump it whenever its GLSL changes. */
export const ATMOSPHERE_PATCH_KEY = "penyal-atmosphere-v1";

function createUniforms(): AtmosphereUniforms {
  return {
    uAtmoSunDirection: { value: new Vector3() },
    uAtmoSunColor: { value: new Color() },
    uAtmoHorizon: { value: new Color() },
    uAtmoZenith: { value: new Color() },
    uAtmoFog: { value: new Vector4() },
  };
}

function writeUniforms(uniforms: AtmosphereUniforms, state: AtmosphereState): void {
  const { direction, color, intensity } = state.sun;
  uniforms.uAtmoSunDirection.value.set(direction.x, direction.y, direction.z);
  uniforms.uAtmoSunColor.value.setRGB(color.r, color.g, color.b).multiplyScalar(intensity);
  uniforms.uAtmoHorizon.value.setRGB(state.horizon.r, state.horizon.g, state.horizon.b);
  uniforms.uAtmoZenith.value.setRGB(state.zenith.r, state.zenith.g, state.zenith.b);
  uniforms.uAtmoFog.value.set(state.fog.near, state.fog.far, state.fog.sunScatter, 0);
}

/**
 * The one atmosphere of the scene. Only the `atmosphere` system gets the writer; every other
 * system sees it as an {@link AtmosphereReader}.
 */
export function createAtmosphere(initial: AtmosphereState): AtmosphereWriter {
  let state = initial;
  let version = 0;
  const uniforms = createUniforms();
  writeUniforms(uniforms, state);
  return {
    get state() {
      return state;
    },
    get version() {
      return version;
    },
    uniforms,
    set(next) {
      state = { ...state, ...next };
      writeUniforms(uniforms, state);
      version++;
    },
  };
}

/**
 * Gives a lit material the shared atmosphere uniforms; idempotent. In B0 this only declares the
 * uniforms (the GLSL arrives with L1, which also bumps `ATMOSPHERE_PATCH_KEY`). A `ShaderMaterial`
 * takes them into its own `uniforms`, so a clone, which deep-copies them, must call this again.
 * `_surface` tells L1 which baked shadow lookup the material needs.
 */
export function attachAtmosphere(
  material: Material,
  atmosphere: AtmosphereReader,
  _surface: AtmosphereSurface = { kind: "generic" },
): void {
  if (material instanceof ShaderMaterial) {
    Object.assign(material.uniforms, atmosphere.uniforms);
    return;
  }
  addShaderPatch(material, {
    key: ATMOSPHERE_PATCH_KEY,
    uniforms: atmosphere.uniforms,
    apply: (vertexShader, fragmentShader) => ({ vertexShader, fragmentShader }),
  });
}
