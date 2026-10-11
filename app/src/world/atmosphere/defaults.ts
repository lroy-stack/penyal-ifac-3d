import { Color } from "three";
import type { AtmosphereState, Rgb } from "../atmosphere";
import { fogRangeFor, HORIZON_COLOR, SUN_DIRECTION, ZENITH_COLOR } from "../sky";

const linear = (hex: number): Rgb => {
  const { r, g, b } = new Color(hex);
  return { r, g, b };
};

/**
 * B0 defaults: the constants the scene used before the atmosphere existed (fixed daytime sun,
 * hemisphere light, horizon and zenith gradient, linear fog, ACES), passed through
 * `new Color(hex)` so every value is bit-identical. `viewpoint` sets the fog range.
 */
export function dayAtmosphere(viewpoint: {
  readonly x: number;
  readonly z: number;
}): AtmosphereState {
  const { near, far } = fogRangeFor(viewpoint);
  return {
    preset: "day",
    sun: {
      direction: { x: SUN_DIRECTION.x, y: SUN_DIRECTION.y, z: SUN_DIRECTION.z },
      color: linear(0xfff1d6),
      intensity: 2.6,
    },
    ambient: { sky: linear(0xcfe6ff), ground: linear(0x6b5a3c), intensity: 1.1 },
    horizon: linear(HORIZON_COLOR),
    zenith: linear(ZENITH_COLOR),
    fog: { color: linear(HORIZON_COLOR), near, far, sunScatter: 0 },
    toneMapping: "aces",
    exposure: 1,
  };
}
