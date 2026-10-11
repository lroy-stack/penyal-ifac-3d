import { describe, expect, it, vi } from "vitest";
import type { Poi } from "../content/poi";
import type { PlayerState } from "../player";
import { makeWorldDeps } from "./fixtures";
import { createPoiRegistry, createPoiSystem } from "./poi";
import { createWorld, type FrameInfo, type Route } from "./systems";
import type { Trail } from "./trail";

function card(id: string, anchor: string, status: Poi["status"], radius = 15): Poi {
  return {
    id,
    status,
    anchor,
    discoveryRadius: radius,
    title: { es: id },
    summary: [{ text: { es: id }, facts: ["f"] }],
    expand: [],
    images: [],
    translations: { va: { status: "missing" }, en: { status: "missing" } },
  };
}

const TRAIL = {
  anchors: {
    centre: { x: 0, y: 5, z: 0 },
    summit: { x: 500, y: 300, z: -500 },
  },
} as unknown as Trail;

function frameAt(x: number, z: number): FrameInfo {
  return {
    frame: 1,
    dt: 0.016,
    time: 0,
    realMs: 16,
    drawingBufferHeight: 720,
    player: { position: { x, y: 0, z } } as unknown as PlayerState,
  };
}

async function setup(pois: Poi[], options: { showDrafts?: boolean; problems?: string[] } = {}) {
  const control = createPoiRegistry();
  const made = makeWorldDeps({
    route: Promise.resolve({ trail: TRAIL } as unknown as Route),
    pois: control.registry,
  });
  const world = createWorld(
    [
      createPoiSystem({
        control,
        load: async () => ({ pois, problems: options.problems ?? [] }),
        showDrafts: options.showDrafts ?? false,
      }),
    ],
    made.deps,
  );
  world.startWalk();
  await vi.waitFor(() => expect(world.status().poi?.state).not.toBe("loading"));
  return { world, control };
}

describe("poi registry", () => {
  it("lists what was placed and tells every listener, even after one throws", () => {
    const control = createPoiRegistry();
    const errors = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const heard: string[] = [];
    control.registry.onDiscover(() => {
      throw new Error("ui broke");
    });
    control.registry.onDiscover((poi) => heard.push(poi.id));
    const poi = card("a", "centre", "published");
    control.place([{ poi, position: { x: 0, y: 0, z: 0 } }]);
    control.discover(poi);
    expect(control.registry.list()).toHaveLength(1);
    expect(heard).toEqual(["a"]);
    expect(errors).toHaveBeenCalledOnce();
    errors.mockRestore();
  });

  it("stops telling a listener that unsubscribed", () => {
    const control = createPoiRegistry();
    const heard: string[] = [];
    const off = control.registry.onDiscover((poi) => heard.push(poi.id));
    off();
    control.discover(card("a", "centre", "published"));
    expect(heard).toEqual([]);
  });
});

describe("poi system", () => {
  it("places published cards at their anchors and is inert for drafts outside development", async () => {
    const { world, control } = await setup([
      card("pub", "centre", "published"),
      card("draft", "summit", "draft"),
    ]);
    expect(world.status().poi).toEqual({ state: "ready" });
    expect(control.registry.list().map((entry) => entry.poi.id)).toEqual(["pub"]);
    expect(control.registry.list()[0]?.position).toEqual({ x: 0, y: 5, z: 0 });
  });

  it("places drafts too in development", async () => {
    const { control } = await setup(
      [card("pub", "centre", "published"), card("draft", "summit", "draft")],
      { showDrafts: true },
    );
    expect(control.registry.list().map((entry) => entry.poi.id)).toEqual(["pub", "draft"]);
  });

  it("is inert with no cards", async () => {
    const { world, control } = await setup([]);
    expect(control.registry.list()).toEqual([]);
    world.update("postPlayer", frameAt(0, 0));
    expect(world.status().poi).toEqual({ state: "ready" });
  });

  it("discovers a card once, by the horizontal distance to its anchor", async () => {
    const { world, control } = await setup([card("pub", "centre", "published", 10)]);
    const heard: string[] = [];
    control.registry.onDiscover((poi) => heard.push(poi.id));
    world.update("postPlayer", frameAt(11, 0));
    expect(heard).toEqual([]);
    world.update("postPlayer", frameAt(6, 8));
    expect(heard).toEqual(["pub"]);
    world.update("postPlayer", frameAt(0, 0));
    world.update("postPlayer", frameAt(100, 0));
    world.update("postPlayer", frameAt(0, 0));
    expect(heard).toEqual(["pub"]);
  });

  it("ignores the height of the player", async () => {
    const { world, control } = await setup([card("pub", "centre", "published", 10)]);
    const heard: string[] = [];
    control.registry.onDiscover((poi) => heard.push(poi.id));
    const frame = frameAt(1, 1);
    world.update("postPlayer", {
      ...frame,
      player: { position: { x: 1, y: 900, z: 1 } } as unknown as PlayerState,
    });
    expect(heard).toEqual(["pub"]);
  });

  it("does nothing while previewing, before the player exists", async () => {
    const { world, control } = await setup([card("pub", "centre", "published")]);
    const heard: string[] = [];
    control.registry.onDiscover((poi) => heard.push(poi.id));
    world.update("postPlayer", { ...frameAt(0, 0), player: null });
    expect(heard).toEqual([]);
  });

  it("reports a card whose anchor is not on the trail, or that failed to parse, as degraded", async () => {
    const { world, control } = await setup([card("lost", "nowhere", "published")], {
      problems: ["bad.json: nope"],
    });
    expect(control.registry.list()).toEqual([]);
    expect(world.status().poi).toEqual({
      state: "degraded",
      message: 'bad.json: nope; lost: anchor "nowhere" is not in trail.json',
    });
  });

  it("clears the registry when disposed", async () => {
    const { world, control } = await setup([card("pub", "centre", "published")]);
    world.dispose();
    expect(control.registry.list()).toEqual([]);
  });
});
