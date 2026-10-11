import { describe, expect, it } from "vitest";
import { BINARY_TIMEOUT_MS } from "../../core/http";
import {
  INITIAL_TERRAIN_GATE,
  stepTerrainGate,
  TERRAIN_STALL_LIMIT_MS,
  type TerrainGateProbe,
} from "./gate";

const probe = (overrides: Partial<TerrainGateProbe> = {}): TerrainGateProbe => ({
  visible: false,
  gaveUp: false,
  bytesLoaded: 0,
  loadedTiles: 0,
  ...overrides,
});

describe("stepTerrainGate", () => {
  it("waits while the terrain is neither visible nor given up and the stall limit is far", () => {
    expect(stepTerrainGate(INITIAL_TERRAIN_GATE, probe(), 1000).outcome).toBe("waiting");
  });

  it("is visible as soon as the terrain is, even after a stall", () => {
    const stalled = stepTerrainGate(INITIAL_TERRAIN_GATE, probe(), TERRAIN_STALL_LIMIT_MS);
    expect(stalled.outcome).toBe("failed");
    expect(stepTerrainGate(stalled.state, probe({ visible: true }), 16).outcome).toBe("visible");
  });

  it("fails when the streamer gave up", () => {
    expect(stepTerrainGate(INITIAL_TERRAIN_GATE, probe({ gaveUp: true }), 16).outcome).toBe(
      "failed",
    );
  });

  it("fails once the time without progress reaches the stall limit", () => {
    const almost = stepTerrainGate(INITIAL_TERRAIN_GATE, probe(), TERRAIN_STALL_LIMIT_MS - 1);
    expect(almost.outcome).toBe("waiting");
    expect(stepTerrainGate(almost.state, probe(), 1).outcome).toBe("failed");
  });

  it("does not count time that did not elapse (a hidden tab hands in dt 0)", () => {
    let current = INITIAL_TERRAIN_GATE;
    for (let frame = 0; frame < 100; frame++) {
      current = stepTerrainGate(current, probe(), 0).state;
    }
    expect(stepTerrainGate(current, probe(), TERRAIN_STALL_LIMIT_MS - 1).outcome).toBe("waiting");
  });

  it("restarts the stall clock whenever bytes arrive", () => {
    const first = stepTerrainGate(INITIAL_TERRAIN_GATE, probe(), TERRAIN_STALL_LIMIT_MS - 1);
    const progressed = stepTerrainGate(first.state, probe({ bytesLoaded: 1000 }), 500);
    expect(progressed.outcome).toBe("waiting");
    expect(stepTerrainGate(progressed.state, probe({ bytesLoaded: 1000 }), 1000).outcome).toBe(
      "waiting",
    );
  });

  it("restarts the stall clock whenever a required tile appears", () => {
    const first = stepTerrainGate(INITIAL_TERRAIN_GATE, probe(), TERRAIN_STALL_LIMIT_MS - 1);
    const progressed = stepTerrainGate(first.state, probe({ loadedTiles: 1 }), 500);
    expect(stepTerrainGate(progressed.state, probe({ loadedTiles: 1 }), 1000).outcome).toBe(
      "waiting",
    );
  });

  it("leaves the failed outcome when progress resumes", () => {
    const failed = stepTerrainGate(INITIAL_TERRAIN_GATE, probe(), TERRAIN_STALL_LIMIT_MS);
    expect(stepTerrainGate(failed.state, probe({ bytesLoaded: 5 }), 16).outcome).toBe("waiting");
  });

  it("lets a hung request time out and retry once before it gives up", () => {
    const firstRetryDelayMs = 2000;
    expect(TERRAIN_STALL_LIMIT_MS).toBeGreaterThan(BINARY_TIMEOUT_MS + firstRetryDelayMs);
  });
});
