import { describe, expect, it } from "vitest";
import {
  cameraFar,
  distanceToWorkAreaEdge,
  WORK_AREA,
  workAreaCentre,
  workAreaDiagonal,
} from "./workArea";

describe("work area", () => {
  it("is centred between its extents", () => {
    expect(workAreaCentre()).toEqual({ x: 700, z: -725 });
  });

  it("sizes the far plane to contain the whole area", () => {
    expect(cameraFar()).toBeGreaterThanOrEqual(workAreaDiagonal());
    expect(cameraFar() % 100).toBe(0);
  });

  it("measures the distance to the nearest edge", () => {
    expect(distanceToWorkAreaEdge(614, -754)).toBe(1214);
    expect(distanceToWorkAreaEdge(WORK_AREA.minX, 0)).toBe(0);
    expect(distanceToWorkAreaEdge(5000, 0)).toBe(0);
  });
});
