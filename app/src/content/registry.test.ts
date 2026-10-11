import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  type Fact,
  factsFileSchema,
  type Source,
  sourcesFileSchema,
  validateRegistry,
} from "./schema";

const TODAY = "2026-10-11";

function source(overrides: Partial<Source> = {}): Source {
  return {
    id: "gva-ruta-roja",
    publisher: "Generalitat Valenciana",
    kind: "official-gva",
    title: "Ruta Roja – descripció",
    url: "https://example.org/ruta-roja",
    accessed: "2026-10-10",
    ...overrides,
  };
}

function fact(overrides: Partial<Fact> = {}): Fact {
  return {
    id: "summit-altitude",
    topic: "summit",
    statement: "Altitud máxima del Penyal",
    status: "verified",
    values: [{ value: "332", unit: "m", sources: ["gva-ruta-roja"] }],
    checked: "2026-10-10",
    ...overrides,
  };
}

function expectError(errors: string[], fragment: string): void {
  expect(errors.some((error) => error.includes(fragment))).toBe(true);
}

describe("validateRegistry", () => {
  it("accepts a consistent registry", () => {
    expect(validateRegistry([source()], [fact()], TODAY)).toEqual([]);
  });

  describe("ids and references", () => {
    it("rejects duplicate source ids", () => {
      const errors = validateRegistry([source(), source()], [fact()], TODAY);
      expectError(errors, 'duplicate source id "gva-ruta-roja"');
    });

    it("rejects duplicate fact ids", () => {
      const errors = validateRegistry([source()], [fact(), fact()], TODAY);
      expectError(errors, 'duplicate fact id "summit-altitude"');
    });

    it("rejects ids that are not kebab-case", () => {
      const errors = validateRegistry(
        [source({ id: "GVA_ruta" })],
        [fact({ id: "Summit Altitude" })],
        TODAY,
      );
      expectError(errors, "sources.json");
      expectError(errors, "facts.json");
      expectError(errors, "kebab-case");
    });

    it("rejects a value that cites an unknown source", () => {
      const errors = validateRegistry(
        [source()],
        [fact({ values: [{ value: "332", sources: ["gva-ruta-roja", "ghost"] }] })],
        TODAY,
      );
      expectError(errors, 'unknown source "ghost"');
    });

    it("rejects a value without sources", () => {
      const errors = validateRegistry(
        [source()],
        [fact({ status: "unverified", note: "pending", values: [{ value: "332", sources: [] }] })],
        TODAY,
      );
      expectError(errors, "has no sources");
    });

    it("rejects orphan sources", () => {
      const errors = validateRegistry([source(), source({ id: "orphan" })], [fact()], TODAY);
      expectError(errors, 'source "orphan" is not referenced by any fact');
    });
  });

  describe("verified", () => {
    it("requires at least one value", () => {
      const errors = validateRegistry([source()], [fact({ values: [] })], TODAY);
      expectError(errors, 'fact "summit-altitude" has no values');
    });

    it("requires an official source", () => {
      const errors = validateRegistry([source({ kind: "community" })], [fact()], TODAY);
      expectError(errors, 'verified fact "summit-altitude" value #1 has no official source');
    });

    it("accepts any official-* kind", () => {
      const errors = validateRegistry([source({ kind: "official-calp" })], [fact()], TODAY);
      expect(errors).toEqual([]);
    });

    it("accepts a mix of official and community sources", () => {
      const errors = validateRegistry(
        [source(), source({ id: "blog", kind: "community" })],
        [fact({ values: [{ value: "332", sources: ["blog", "gva-ruta-roja"] }] })],
        TODAY,
      );
      expect(errors).toEqual([]);
    });
  });

  describe("conflict", () => {
    const sources = [source(), source({ id: "calp-web", kind: "official-calp" })];

    it("accepts two sourced values that differ", () => {
      const errors = validateRegistry(
        sources,
        [
          fact({
            status: "conflict",
            values: [
              { value: "332", sources: ["gva-ruta-roja"] },
              { value: "328", sources: ["calp-web"] },
            ],
          }),
        ],
        TODAY,
      );
      expect(errors).toEqual([]);
    });

    it("rejects a single value", () => {
      const errors = validateRegistry([source()], [fact({ status: "conflict" })], TODAY);
      expectError(errors, 'conflict fact "summit-altitude" needs at least two values');
    });

    it("rejects two values that are equal", () => {
      const errors = validateRegistry(
        sources,
        [
          fact({
            status: "conflict",
            values: [
              { value: "332", sources: ["gva-ruta-roja"] },
              { value: "332", sources: ["calp-web"] },
            ],
          }),
        ],
        TODAY,
      );
      expectError(errors, "different");
    });

    it("rejects a conflicting value without sources", () => {
      const errors = validateRegistry(
        sources,
        [
          fact({
            status: "conflict",
            values: [
              { value: "332", sources: ["gva-ruta-roja", "calp-web"] },
              { value: "328", sources: [] },
            ],
          }),
        ],
        TODAY,
      );
      expectError(errors, 'value #2 ("328") has no sources');
    });
  });

  describe("unverified", () => {
    const unverified = (note?: string): Fact =>
      fact({
        status: "unverified",
        ...(note === undefined ? {} : { note }),
      });

    it("requires a note", () => {
      expectError(validateRegistry([source()], [unverified()], TODAY), "needs a non-empty note");
    });

    it("rejects a blank note", () => {
      expectError(
        validateRegistry([source()], [unverified("  ")], TODAY),
        "needs a non-empty note",
      );
    });

    it("accepts a note", () => {
      expect(
        validateRegistry([source()], [unverified("Pending park confirmation")], TODAY),
      ).toEqual([]);
    });

    it("still requires a sourced value (a fact without a source fails, AC6)", () => {
      const errors = validateRegistry(
        [source()],
        [fact({ status: "unverified", values: [], note: "No official figure" })],
        TODAY,
      );
      expectError(errors, 'fact "summit-altitude" has no values');
    });
  });

  describe("verified, stricter", () => {
    it("rejects two different values (that is a conflict)", () => {
      const errors = validateRegistry(
        [source()],
        [
          fact({
            values: [
              { value: "332", unit: "m", sources: ["gva-ruta-roja"] },
              { value: "328", unit: "m", sources: ["gva-ruta-roja"] },
            ],
          }),
        ],
        TODAY,
      );
      expectError(errors, "more than one distinct value");
    });

    it("rejects a value backed only by non-official sources", () => {
      const errors = validateRegistry(
        [source(), source({ id: "osm-way", kind: "community" })],
        [
          fact({
            values: [
              { value: "332", unit: "m", sources: ["gva-ruta-roja"] },
              { value: "332", unit: "m", sources: ["osm-way"] },
            ],
          }),
        ],
        TODAY,
      );
      expectError(errors, "value #2");
    });
  });

  describe("dates", () => {
    it("rejects malformed dates", () => {
      const errors = validateRegistry(
        [source({ accessed: "10/10/2026" })],
        [fact({ checked: "2026-13-40" })],
        TODAY,
      );
      expectError(errors, "YYYY-MM-DD");
      expect(errors.filter((error) => error.includes("YYYY-MM-DD"))).toHaveLength(2);
    });

    it("rejects impossible calendar dates", () => {
      const errors = validateRegistry([source()], [fact({ checked: "2026-02-30" })], TODAY);
      expectError(errors, "YYYY-MM-DD");
    });

    it("rejects dates in the future relative to the injected clock", () => {
      const errors = validateRegistry(
        [source({ accessed: "2026-10-12" })],
        [fact({ checked: "2026-10-12" })],
        TODAY,
      );
      expectError(errors, 'source "gva-ruta-roja" has accessed=2026-10-12');
      expectError(errors, 'fact "summit-altitude" has checked=2026-10-12');
    });

    it("accepts the injected day itself", () => {
      const errors = validateRegistry(
        [source({ accessed: TODAY })],
        [fact({ checked: TODAY })],
        TODAY,
      );
      expect(errors).toEqual([]);
    });
  });

  describe("shape", () => {
    it("rejects non-https urls", () => {
      const errors = validateRegistry([source({ url: "http://example.org" })], [fact()], TODAY);
      expectError(errors, "sources.json");
    });

    it("rejects unknown kinds, topics and statuses", () => {
      const errors = validateRegistry(
        [{ ...source(), kind: "blog" }],
        [{ ...fact(), topic: "weather", status: "maybe" }],
        TODAY,
      );
      expectError(errors, "sources.json: 0.kind");
      expectError(errors, "facts.json: 0.topic");
      expectError(errors, "facts.json: 0.status");
    });
  });
});

describe("real registry", () => {
  const read = (name: string): unknown =>
    JSON.parse(
      readFileSync(fileURLToPath(new URL(`../../../content/${name}`, import.meta.url)), "utf8"),
    );

  it("content/sources.json and content/facts.json pass every rule", () => {
    const sources = sourcesFileSchema.parse(read("sources.json")).sources;
    const facts = factsFileSchema.parse(read("facts.json")).facts;
    // The real registry is checked against today's date in Calp, so new entries never trip
    // the "date in the future" rule because of a stale constant.
    const today = new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Madrid" });

    expect(validateRegistry(sources, facts, today)).toEqual([]);
  });
});
