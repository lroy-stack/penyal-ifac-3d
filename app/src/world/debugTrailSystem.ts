import { createTrailDebug, type TrailDebug } from "./debugTrail";
import type { WorldSystem } from "./systems";

/**
 * The route and corridor overlay of `?debug=trail`, as a background system: it needs the
 * collision field to drape the lines, which exists only after the walk gate. Listed only when the
 * flag is present.
 */
export function createTrailDebugSystem(): WorldSystem {
  let debug: TrailDebug | null = null;
  return {
    id: "debug-trail",
    phase: "postPlayer",
    load: "background",
    async init(ctx) {
      const [route, collision] = await Promise.all([ctx.route, ctx.collision]);
      debug = createTrailDebug(route.trail, collision);
      ctx.root.add(debug.object);
      return { status: "ready" };
    },
    update: () => undefined,
    dispose() {
      debug?.dispose();
      debug = null;
    },
  };
}
