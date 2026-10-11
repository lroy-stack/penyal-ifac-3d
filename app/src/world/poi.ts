import type { LoadedPois } from "../content/loadPois";
import type { Poi, PoiRegistry } from "../content/poi";
import type { LocalPoint } from "../geo/frame";
import type { WorldSystem } from "./systems";

type Placed = { readonly poi: Poi; readonly position: LocalPoint };

/** The registry plus the two calls only the poi system makes. */
export type PoiRegistryControl = {
  readonly registry: PoiRegistry;
  /** Replaces the placed cards; discovery starts over. */
  place(placed: readonly Placed[]): void;
  /** Tells the listeners; one that throws does not stop the others. */
  discover(poi: Poi): void;
};

export function createPoiRegistry(): PoiRegistryControl {
  let placed: readonly Placed[] = [];
  const listeners = new Set<(poi: Poi) => void>();
  return {
    registry: {
      list: () => placed,
      onDiscover(listener) {
        listeners.add(listener);
        return () => {
          listeners.delete(listener);
        };
      },
    },
    place(next) {
      placed = next;
    },
    discover(poi) {
      for (const listener of [...listeners]) {
        try {
          listener(poi);
        } catch (error) {
          console.error(
            `[world:poi] a discovery listener failed for "${poi.id}": ${
              error instanceof Error ? error.message : String(error)
            }`,
          );
        }
      }
    },
  };
}

export type PoiSystemOptions = {
  readonly control: PoiRegistryControl;
  readonly load: () => Promise<LoadedPois>;
  /** Drafts are placed only in development; the public build shows published cards. */
  readonly showDrafts: boolean;
};

/**
 * Finds the cards the player comes within reach of, once per card per visit, by the horizontal
 * distance to the card's trail anchor. Inert until a card is published (or, in development,
 * drafted), and silent until a listener, such as the card UI of L7, subscribes.
 */
export function createPoiSystem(options: PoiSystemOptions): WorldSystem {
  const discovered = new Set<string>();
  let placed: readonly Placed[] = [];
  return {
    id: "poi",
    phase: "postPlayer",
    load: "background",
    async init(ctx) {
      const [route, loaded] = await Promise.all([ctx.route, options.load()]);
      const problems = [...loaded.problems];
      const next: Placed[] = [];
      for (const poi of loaded.pois) {
        if (poi.status !== "published" && !options.showDrafts) continue;
        const anchor = route.trail.anchors[poi.anchor];
        if (anchor === undefined) {
          problems.push(`${poi.id}: anchor "${poi.anchor}" is not in trail.json`);
          continue;
        }
        next.push({ poi, position: { x: anchor.x, y: anchor.y, z: anchor.z } });
      }
      placed = next;
      options.control.place(next);
      if (problems.length > 0) {
        ctx.report({ state: "degraded", message: problems.join("; ") });
      }
      return { status: "ready" };
    },
    update(frame) {
      if (frame.player === null || placed.length === 0) return;
      const { x, z } = frame.player.position;
      for (const { poi, position } of placed) {
        if (discovered.has(poi.id)) continue;
        if (Math.hypot(position.x - x, position.z - z) <= poi.discoveryRadius) {
          discovered.add(poi.id);
          options.control.discover(poi);
        }
      }
    },
    dispose() {
      options.control.place([]);
      discovered.clear();
      placed = [];
    },
  };
}
