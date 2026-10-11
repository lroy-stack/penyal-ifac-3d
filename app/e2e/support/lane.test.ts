import { describe, expect, it } from "vitest";
import { laneDefaults, laneOf } from "./lane";

const MAIN = "/Users/x/penyal-ifac-3d/app";
const LANE = (n: number) => `/Users/x/penyal-ifac-3d/.worktrees/l${n}/app`;

describe("laneOf", () => {
  it("is the number of the lane when the app lives in .worktrees/l<n>", () => {
    expect(laneOf(LANE(1))).toBe(1);
    expect(laneOf(LANE(8))).toBe(8);
  });

  it("is null in the main checkout, in other worktrees and for other lane names", () => {
    expect(laneOf(MAIN)).toBeNull();
    expect(laneOf("/Users/x/penyal-ifac-3d/.claude/worktrees/agent-a/app")).toBeNull();
    expect(laneOf("/Users/x/penyal-ifac-3d/.worktrees/l9/app")).toBeNull();
    expect(laneOf("/Users/x/penyal-ifac-3d/.worktrees/l1x/app")).toBeNull();
    expect(laneOf("/Users/x/penyal-ifac-3d/.worktrees/lane1/app")).toBeNull();
  });

  it("accepts Windows separators", () => {
    expect(laneOf("C:\\work\\penyal\\.worktrees\\l3\\app")).toBe(3);
  });
});

describe("laneDefaults", () => {
  it("keeps 5175, test-results and the default workers in the main checkout", () => {
    expect(laneDefaults(MAIN, {})).toEqual({
      port: 5175,
      outputDir: "test-results",
      workers: undefined,
    });
  });

  it("gives lane n the port 5180 + n, its own output directory and one worker", () => {
    expect(laneDefaults(LANE(1), {})).toEqual({
      port: 5181,
      outputDir: "test-results/l1",
      workers: 1,
    });
    expect(laneDefaults(LANE(8), {})).toMatchObject({ port: 5188, outputDir: "test-results/l8" });
  });

  it("lets explicit variables win", () => {
    expect(laneDefaults(LANE(2), { E2E_PORT: "6000", E2E_OUTPUT_DIR: "/tmp/out" })).toEqual({
      port: 6000,
      outputDir: "/tmp/out",
      workers: 1,
    });
    expect(laneDefaults(MAIN, { E2E_PORT: "6000" }).port).toBe(6000);
  });
});
