import { describe, expect, it } from "vitest";
import { TERRAIN_GATE_TIMEOUT_MS, terrainGateOutcome } from "./gate";

describe("terrainGateOutcome", () => {
  it("waits while the terrain is neither visible nor given up and time remains", () => {
    expect(terrainGateOutcome({ visible: false, gaveUp: false }, 1000)).toBe("waiting");
  });

  it("opens when the terrain is visible, even after the deadline", () => {
    expect(terrainGateOutcome({ visible: true, gaveUp: false }, TERRAIN_GATE_TIMEOUT_MS * 2)).toBe(
      "visible",
    );
  });

  it("fails when the streamer gave up", () => {
    expect(terrainGateOutcome({ visible: false, gaveUp: true }, 1000)).toBe("failed");
  });

  it("fails at the wall-clock deadline when nothing else settled", () => {
    expect(terrainGateOutcome({ visible: false, gaveUp: false }, TERRAIN_GATE_TIMEOUT_MS - 1)).toBe(
      "waiting",
    );
    expect(terrainGateOutcome({ visible: false, gaveUp: false }, TERRAIN_GATE_TIMEOUT_MS)).toBe(
      "failed",
    );
  });
});
