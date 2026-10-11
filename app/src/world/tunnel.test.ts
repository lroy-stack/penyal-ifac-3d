import { afterEach, describe, expect, it, vi } from "vitest";
import { PolygonCorridor } from "./ground";
import {
  loadTunnel,
  PORTAL_OVERRUN,
  parseTunnel,
  TunnelGroundSurface,
  tunnelSchema,
} from "./tunnel";

// Contract fixture (plan.md, "Interfaces & data"): a straight tunnel along +X from x = 100 to
// x = 140 that climbs from 171 m to 191 m, 2.4 m wide and 2.6 m high.
function straightAxis(): [number, number, number][] {
  const axis: [number, number, number][] = [];
  for (let i = 0; i <= 80; i++) axis.push([100 + i * 0.5, 171 + i * 0.25, 50]);
  return axis;
}

const FIXTURE = {
  version: 1,
  licence: "ODbL-1.0",
  attribution: "© OpenStreetMap contributors",
  status: "approximate",
  axis: straightAxis(),
  width: 2.4,
  height: 2.6,
  sectionBasis: "fixture",
  portals: { west: { x: 100, y: 171, z: 50 }, east: { x: 140, y: 191, z: 50 } },
  sources: { axis: "osm:way/26330275", portalHeights: "data/curated/tunnel.toml" },
  mesh: "tunnel.glb",
  extraKey: "ignored",
};

describe("parseTunnel", () => {
  it("accepts the contract and ignores extra keys", () => {
    const tunnel = parseTunnel(FIXTURE);
    expect(tunnel.axis).toHaveLength(81);
    expect(tunnel.mesh).toBe("tunnel.glb");
  });

  it("rejects a malformed file with a message naming the field", () => {
    expect(() => parseTunnel({ ...FIXTURE, width: -1 })).toThrow(/width/);
    expect(() => parseTunnel({ ...FIXTURE, axis: [[0, 0, 0]] })).toThrow(/axis/);
    expect(() => parseTunnel({ ...FIXTURE, version: 2 })).toThrow(/version/);
    expect(tunnelSchema.safeParse({}).success).toBe(false);
  });
});

describe("TunnelGroundSurface", () => {
  const tunnel = new TunnelGroundSurface(parseTunnel(FIXTURE));
  const high = 400;

  it("gives the interpolated floor on the axis", () => {
    expect(tunnel.floorAt(100, 50)).toBeCloseTo(171, 9);
    expect(tunnel.floorAt(120, 50)).toBeCloseTo(181, 9);
    expect(tunnel.floorAt(120.25, 50)).toBeCloseTo(181.125, 9);
    expect(tunnel.floorAt(140, 50)).toBeCloseTo(191, 9);
  });

  it("interpolates the slope between axis vertices", () => {
    const sloped = new TunnelGroundSurface({
      axis: [
        [0, 10, 0],
        [10, 10, 0],
        [20, 12, 0],
      ],
      width: 2,
      height: 3,
    });
    expect(sloped.floorAt(5, 0)).toBeCloseTo(10, 9);
    expect(sloped.floorAt(15, 0)).toBeCloseTo(11, 9);
    expect(sloped.floorAt(15, 0.5)).toBeCloseTo(11, 9);
  });

  it("stops at half the width on either side of the axis", () => {
    expect(tunnel.floorAt(120, 50 + 1.19)).not.toBeNull();
    expect(tunnel.floorAt(120, 50 - 1.19)).not.toBeNull();
    expect(tunnel.floorAt(120, 50 + 1.21)).toBeNull();
    expect(tunnel.floorAt(120, 50 - 1.21)).toBeNull();
  });

  it("extends one metre beyond each portal at the portal height, and no further", () => {
    expect(PORTAL_OVERRUN).toBe(1);
    expect(tunnel.floorAt(99.2, 50)).toBeCloseTo(171, 9);
    expect(tunnel.floorAt(140.9, 50)).toBeCloseTo(191, 9);
    expect(tunnel.floorAt(98.9, 50)).toBeNull();
    expect(tunnel.floorAt(141.1, 50)).toBeNull();
    // The end cap is square: no rounded corner beyond the strip.
    expect(tunnel.floorAt(98.9, 50.5)).toBeNull();
  });

  it("follows a bend without gaps on the inside or outside of the corner", () => {
    const bend = new TunnelGroundSurface({
      axis: [
        [0, 0, 0],
        [10, 0, 0],
        [10, 1, 10],
      ],
      width: 2,
      height: 3,
    });
    expect(bend.floorAt(10.9, 0.1)).not.toBeNull();
    expect(bend.floorAt(9.1, 0.9)).not.toBeNull();
    expect(bend.floorAt(10, 5)).toBeCloseTo(0.5, 9);
  });

  it("returns the floor from surfaceBelow only inside the reach window", () => {
    expect(tunnel.surfaceBelow(120, 181.4, 50, 0.9)).toBeCloseTo(181, 9);
    expect(tunnel.surfaceBelow(120, 180.9, 50, 0.9)).toBeNull();
    expect(tunnel.surfaceBelow(120, 182.5, 50, 0.9)).toBeNull();
    expect(tunnel.surfaceBelow(120, 181.4, 52, 0.9)).toBeNull();
  });

  it("still gives the floor under rock that the height field puts far above", () => {
    const rockSurface = (x: number, z: number): number | null => {
      const floor = tunnel.floorAt(x, z);
      return floor === null ? null : floor + 40;
    };
    expect(rockSurface(120, 50)).toBeGreaterThan(200);
    expect(tunnel.surfaceBelow(120, 181 + 0.4, 50, 0.9)).toBeCloseTo(181, 9);
    expect(high).toBeGreaterThan(191);
  });

  it("is an enclosure between the floor and the ceiling, inset by the margin", () => {
    expect(tunnel.contains(120, 182, 50, 0.2)).toBe(true);
    expect(tunnel.contains(120, 181 + 2.5, 50, 0.2)).toBe(false);
    expect(tunnel.contains(120, 181 + 1.0, 50 + 1.1, 0.2)).toBe(false);
    expect(tunnel.contains(120, 181 + 1.0, 50 + 0.9, 0.2)).toBe(true);
    expect(tunnel.contains(120, 181 - 0.5, 50, 0.2)).toBe(false);
  });

  it("keeps a corridor narrower than the tunnel on the floor everywhere along it", () => {
    const corridor = new PolygonCorridor([
      [99, 49.3],
      [141, 49.3],
      [141, 50.7],
      [99, 50.7],
    ]);
    for (let x = 99.5; x <= 140.5; x += 0.37) {
      for (const z of [49.31, 50, 50.69]) {
        expect(corridor.contains(x, z)).toBe(true);
        expect(tunnel.floorAt(x, z)).not.toBeNull();
      }
    }
  });
});

describe("loadTunnel", () => {
  afterEach(() => vi.unstubAllGlobals());

  function respond(body: BodyInit, init: ResponseInit): void {
    vi.stubGlobal("fetch", async () => new Response(body, init));
  }

  it("returns the parsed tunnel", async () => {
    respond(JSON.stringify(FIXTURE), { headers: { "content-type": "application/json" } });
    const result = await loadTunnel("/tunnel.json");
    expect(result.status).toBe("ready");
  });

  it("reports a missing file (404 or the SPA fallback) as missing", async () => {
    respond("nope", { status: 404 });
    expect(await loadTunnel("/tunnel.json")).toEqual({ status: "missing" });
    respond("<html></html>", { headers: { "content-type": "text/html" } });
    expect(await loadTunnel("/tunnel.json")).toEqual({ status: "missing" });
  });

  it("reports an invalid file and a server error with a message", async () => {
    respond(JSON.stringify({ ...FIXTURE, width: 0 }), {
      headers: { "content-type": "application/json" },
    });
    const invalid = await loadTunnel("/tunnel.json");
    expect(invalid).toMatchObject({ status: "error", message: expect.stringContaining("width") });
    respond("boom", { status: 500 });
    expect(await loadTunnel("/tunnel.json")).toMatchObject({
      status: "error",
      message: expect.stringContaining("500"),
    });
  });
});
