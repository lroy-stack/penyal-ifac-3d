import {
  ACESFilmicToneMapping,
  AgXToneMapping,
  Color,
  Fog,
  type Scene,
  type WebGLRenderer,
} from "three";
import type { AtmosphereState, AtmosphereWriter } from "../atmosphere";
import { fogRangeFor } from "../sky";
import type { WorldSystem } from "../systems";

/**
 * The atmosphere writer's system: the only one that writes `scene.fog`, `scene.background` and
 * the tone mapping. Once the route is known it sets the fog range for the summit view; when the
 * version changes it applies the state before anything else updates.
 */
export function createAtmosphereSystem(writer: AtmosphereWriter): WorldSystem {
  let applied = -1;
  let target: { readonly scene: Scene; readonly renderer: WebGLRenderer } | null = null;

  const apply = (state: AtmosphereState): void => {
    if (target === null) return;
    const { scene, renderer } = target;
    const { horizon, fog } = state;
    if (scene.background instanceof Color) scene.background.setRGB(horizon.r, horizon.g, horizon.b);
    else scene.background = new Color().setRGB(horizon.r, horizon.g, horizon.b);
    if (scene.fog instanceof Fog) {
      scene.fog.color.setRGB(fog.color.r, fog.color.g, fog.color.b);
      scene.fog.near = fog.near;
      scene.fog.far = fog.far;
    } else {
      scene.fog = new Fog(
        new Color().setRGB(fog.color.r, fog.color.g, fog.color.b),
        fog.near,
        fog.far,
      );
    }
    renderer.toneMapping = state.toneMapping === "agx" ? AgXToneMapping : ACESFilmicToneMapping;
    renderer.toneMappingExposure = state.exposure;
    applied = writer.version;
  };

  return {
    id: "atmosphere",
    phase: "prePlayer",
    load: "critical",
    async init(ctx) {
      target = { scene: ctx.scene, renderer: ctx.renderer };
      const route = await ctx.route;
      const summit = route.trail.anchors.summit ?? route.start;
      const { near, far } = fogRangeFor(summit);
      writer.set({ fog: { ...writer.state.fog, near, far } });
      apply(writer.state);
      return { status: "ready" };
    },
    update() {
      if (writer.version !== applied) apply(writer.state);
    },
    dispose() {
      target = null;
    },
  };
}
