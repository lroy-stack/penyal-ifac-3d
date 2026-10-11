import { ACESFilmicToneMapping, AgXToneMapping, Color, Fog } from "three";
import { describe, expect, it } from "vitest";
import { makeWorldDeps } from "../fixtures";
import { fogRangeFor } from "../sky";
import { createWorld, type FrameInfo } from "../systems";
import { dayAtmosphere } from "./defaults";
import { createAtmosphereSystem } from "./system";

const FRAME: FrameInfo = {
  frame: 1,
  dt: 0.016,
  time: 0,
  realMs: 16,
  drawingBufferHeight: 720,
  player: null,
};
const START = { x: 0, y: 0, z: 0 };
const SUMMIT = { x: 613.893, y: 325, z: -754.184 };

function routeTo(summit: typeof SUMMIT | undefined) {
  return Promise.resolve({
    trail: { anchors: summit === undefined ? {} : { summit } },
    corridor: { contains: () => true, clamp: () => ({ x: 0, z: 0 }) },
    start: START,
    startYaw: 0,
  }) as never;
}

describe("dayAtmosphere", () => {
  it("passes today's constants through Color so the values are bit-identical", () => {
    const state = dayAtmosphere({ x: 613.893, z: -754.184 });
    const expected = new Color(0xbcd6ea);
    expect(state.horizon).toEqual({ r: expected.r, g: expected.g, b: expected.b });
    expect(state.fog.color).toEqual(state.horizon);
    const sun = new Color(0xfff1d6);
    expect(state.sun.color).toEqual({ r: sun.r, g: sun.g, b: sun.b });
    expect(state.sun.intensity).toBe(2.6);
    expect(state.ambient.intensity).toBe(1.1);
    expect(state.toneMapping).toBe("aces");
    expect(state.exposure).toBe(1);
    expect(state.fog.sunScatter).toBe(0);
    expect(state.fog.far).toBeCloseTo(1213.893, 3);
    expect(
      Math.hypot(state.sun.direction.x, state.sun.direction.y, state.sun.direction.z),
    ).toBeCloseTo(1, 12);
  });
});

describe("createAtmosphereSystem", () => {
  it("sets the fog for the summit view, the background and the tone mapping once the route is known", async () => {
    const { deps, writer } = makeWorldDeps({ route: routeTo(SUMMIT) });
    const world = createWorld([createAtmosphereSystem(writer)], deps);
    await world.init("critical");

    const { near, far } = fogRangeFor(SUMMIT);
    expect(deps.scene.fog).toBeInstanceOf(Fog);
    const fog = deps.scene.fog as Fog;
    expect([fog.near, fog.far]).toEqual([near, far]);
    expect(fog.color.getHex()).toBe(new Color(0xbcd6ea).getHex());
    expect((deps.scene.background as Color).getHex()).toBe(new Color(0xbcd6ea).getHex());
    expect(deps.renderer.toneMapping).toBe(ACESFilmicToneMapping);
    expect(deps.renderer.toneMappingExposure).toBe(1);
  });

  it("falls back to the start when the trail has no summit", async () => {
    const { deps, writer } = makeWorldDeps({ route: routeTo(undefined) });
    const world = createWorld([createAtmosphereSystem(writer)], deps);
    await world.init("critical");
    expect((deps.scene.fog as Fog).far).toBe(fogRangeFor(START).far);
  });

  it("applies a new state in the next prePlayer update, in place, and only then", async () => {
    const { deps, writer } = makeWorldDeps({ route: routeTo(SUMMIT) });
    const world = createWorld([createAtmosphereSystem(writer)], deps);
    await world.init("critical");
    const fog = deps.scene.fog as Fog;
    const background = deps.scene.background as Color;

    writer.set({
      toneMapping: "agx",
      exposure: 0.8,
      horizon: { r: 0.1, g: 0.2, b: 0.3 },
      fog: { color: { r: 0.4, g: 0.5, b: 0.6 }, near: 5, far: 50, sunScatter: 0 },
    });
    expect(deps.renderer.toneMapping).toBe(ACESFilmicToneMapping);
    world.update("prePlayer", FRAME);
    expect(deps.scene.fog).toBe(fog);
    expect(deps.scene.background).toBe(background);
    expect([fog.near, fog.far]).toEqual([5, 50]);
    expect(fog.color.toArray()).toEqual([0.4, 0.5, 0.6]);
    expect(background.toArray()).toEqual([0.1, 0.2, 0.3]);
    expect(deps.renderer.toneMapping).toBe(AgXToneMapping);
    expect(deps.renderer.toneMappingExposure).toBe(0.8);
  });

  it("does not touch the scene when the version has not changed", async () => {
    const { deps, writer } = makeWorldDeps({ route: routeTo(SUMMIT) });
    const world = createWorld([createAtmosphereSystem(writer)], deps);
    await world.init("critical");
    (deps.scene.fog as Fog).near = 123;
    world.update("prePlayer", FRAME);
    expect((deps.scene.fog as Fog).near).toBe(123);
  });
});
