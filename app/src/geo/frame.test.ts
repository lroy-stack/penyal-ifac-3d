import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { z } from "zod";
import { fromLocal, toLocal } from "./frame";

const fixtureSchema = z.object({
  points: z
    .array(
      z.object({
        name: z.string(),
        lat: z.number(),
        lon: z.number(),
        e: z.number(),
        n: z.number(),
        h: z.number(),
        x: z.number(),
        y: z.number(),
        z: z.number(),
      }),
    )
    .min(1),
});

const fixture = fixtureSchema.parse(
  JSON.parse(readFileSync(new URL("../../../fixtures/geo/frame.json", import.meta.url), "utf8")),
);

const ONE_MM = 0.001;

describe("local frame (shared fixture, ADR 0004)", () => {
  for (const point of fixture.points) {
    it(`${point.name}: toLocal matches the pipeline to 1 mm`, () => {
      const local = toLocal(point.e, point.n, point.h);
      expect(Math.abs(local.x - point.x)).toBeLessThan(ONE_MM);
      expect(Math.abs(local.y - point.y)).toBeLessThan(ONE_MM);
      expect(Math.abs(local.z - point.z)).toBeLessThan(ONE_MM);
    });

    it(`${point.name}: fromLocal inverts the fixture to 1 mm`, () => {
      const utm = fromLocal(point.x, point.y, point.z);
      expect(Math.abs(utm.e - point.e)).toBeLessThan(ONE_MM);
      expect(Math.abs(utm.n - point.n)).toBeLessThan(ONE_MM);
      expect(Math.abs(utm.h - point.h)).toBeLessThan(ONE_MM);
    });
  }

  it("puts north on -Z and east on +X", () => {
    const origin = toLocal(767000, 4280000, 0);
    const north = toLocal(767000, 4280010, 0);
    const east = toLocal(767010, 4280000, 0);
    expect(north.z - origin.z).toBe(-10);
    expect(east.x - origin.x).toBe(10);
  });
});
