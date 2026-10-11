import { describe, expect, it } from "vitest";
import { countWords, numbersIn, type Poi, validatePois } from "./poi";
import type { Fact, Source } from "./schema";

const source = (id: string): Source => ({
  id,
  publisher: "Generalitat Valenciana",
  kind: "official-gva",
  title: id,
  url: "https://example.org/x",
  accessed: "2026-10-10",
});

const sources = [source("gva-a"), source("gva-b")];

const fact = (overrides: Partial<Fact> & Pick<Fact, "id">): Fact => ({
  topic: "access",
  statement: "s",
  status: "verified",
  values: [{ value: "300", unit: "personas al día", sources: ["gva-a"] }],
  checked: "2026-10-10",
  ...overrides,
});

const facts: Fact[] = [
  fact({ id: "capacity" }),
  fact({
    id: "area",
    values: [{ value: "53,3", unit: "ha", sources: ["gva-a"], note: "Decreto 40/2015" }],
    note: "Antes eran 45 ha.",
  }),
  fact({ id: "big", values: [{ value: "Más de 70.000 m²", sources: ["gva-a"] }] }),
  fact({
    id: "founding",
    status: "conflict",
    values: [
      { value: "Después de 1359", sources: ["gva-a"] },
      { value: "Hacia 1400", sources: ["gva-b"] },
    ],
  }),
  fact({
    id: "visits",
    status: "unverified",
    note: "Pending",
    values: [{ value: "Sin visitas regulares desde 2019", sources: ["gva-a"] }],
  }),
];

function card(overrides: Partial<Poi> = {}): Poi {
  return {
    id: "centre",
    status: "draft",
    anchor: "centre",
    discoveryRadius: 15,
    title: { es: "Centro" },
    summary: [{ text: { es: "El aforo es de 300 personas al día." }, facts: ["capacity"] }],
    expand: [],
    images: [],
    translations: { va: { status: "missing" }, en: { status: "missing" } },
    ...overrides,
  };
}

const ANCHORS = new Set(["centre", "summit"]);
const check = (cards: unknown[]): string[] => validatePois(cards, facts, sources, ANCHORS);
const expectError = (errors: string[], fragment: string): void => {
  expect(
    errors.some((error) => error.includes(fragment)),
    errors.join("\n"),
  ).toBe(true);
};

describe("validatePois", () => {
  it("accepts a consistent card", () => {
    expect(check([card()])).toEqual([]);
  });

  describe("shape and ids", () => {
    it("rejects a card that does not match the schema", () => {
      expectError(check([{ ...card(), extra: 1 }]), 'Unrecognized key: "extra"');
      expectError(check([card({ discoveryRadius: 2 })]), "discoveryRadius");
      expectError(check([card({ summary: [] })]), "summary");
    });

    it("rejects a sentence with no fact", () => {
      expectError(check([card({ summary: [{ text: { es: "Hola" }, facts: [] }] })]), "summary");
    });

    it("rejects duplicate ids", () => {
      expectError(check([card(), card()]), 'duplicate POI id "centre"');
    });

    it("rejects an unknown fact in the summary, a block and a conflict", () => {
      expectError(
        check([card({ summary: [{ text: { es: "Hola" }, facts: ["ghost"] }] })]),
        'unknown fact "ghost"',
      );
    });

    it("rejects a notice that cites an unknown source", () => {
      const errors = check([
        card({ expand: [{ kind: "notice", text: { es: "Aviso" }, source: "ghost" }] }),
      ]);
      expectError(errors, 'unknown source "ghost"');
    });
  });

  describe("never pick a value", () => {
    it("rejects a conflict or unverified fact in the summary", () => {
      const errors = check([
        card({
          summary: [{ text: { es: "Hacia el siglo XIV." }, facts: ["founding", "visits"] }],
        }),
      ]);
      expectError(errors, 'cites conflict fact "founding" in the summary');
      expectError(errors, 'cites unverified fact "visits" in the summary');
    });

    it("rejects a conflict fact in a facts block", () => {
      const errors = check([
        card({
          expand: [
            {
              kind: "facts",
              heading: { es: "H" },
              items: [{ text: { es: "Hacia 1400." }, facts: ["founding"] }],
            },
          ],
        }),
      ]);
      expectError(errors, 'conflict fact "founding" in a "facts" block');
    });

    it("accepts a conflict block with every value, in registry order", () => {
      const errors = check([
        card({
          expand: [
            {
              kind: "conflict",
              fact: "founding",
              heading: { es: "Las fuentes no coinciden" },
              values: [{ text: { es: "Después de 1359" } }, { text: { es: "Hacia 1400" } }],
            },
          ],
        }),
      ]);
      expect(errors).toEqual([]);
    });

    it("rejects a conflict block that drops a value or is for a verified fact", () => {
      const heading = { es: "H" };
      const three = [{ text: { es: "a" } }, { text: { es: "b" } }, { text: { es: "c" } }];
      expectError(
        check([card({ expand: [{ kind: "conflict", fact: "founding", heading, values: three }] })]),
        "shows 3 values",
      );
      const two = [{ text: { es: "a" } }, { text: { es: "b" } }];
      expectError(
        check([card({ expand: [{ kind: "conflict", fact: "capacity", heading, values: two }] })]),
        'is a "conflict" block for "capacity"',
      );
    });

    it("checks each conflict value against the value at the same index", () => {
      const errors = check([
        card({
          expand: [
            {
              kind: "conflict",
              fact: "founding",
              heading: { es: "H" },
              values: [{ text: { es: "Hacia 1400" } }, { text: { es: "Después de 1359" } }],
            },
          ],
        }),
      ]);
      expectError(errors, "values.0");
      expectError(errors, "the number 1400");
      expectError(errors, "values.1");
      expectError(errors, "the number 1359");
    });

    it("accepts an unverified block only for an unverified fact", () => {
      const ok = card({
        expand: [{ kind: "unverified", fact: "visits", text: { es: "Sin visitas desde 2019" } }],
      });
      expect(check([ok])).toEqual([]);
      const wrong = card({
        expand: [{ kind: "unverified", fact: "capacity", text: { es: "300" } }],
      });
      expectError(check([wrong]), 'is an "unverified" block for "capacity"');
    });
  });

  describe("length", () => {
    const words = (count: number): string =>
      Array.from({ length: count }, () => "palabra").join(" ");

    it("counts tokens with a letter or a digit", () => {
      expect(countWords("a — 12 , b-c")).toBe(3);
      expect(countWords("  ")).toBe(0);
    });

    it("accepts 60 words and rejects 61, per language", () => {
      const at = (count: number) =>
        card({ summary: [{ text: { es: words(count) }, facts: ["capacity"] }] });
      expect(check([at(60)])).toEqual([]);
      expectError(check([at(61)]), "summary (es) has 61 words");
      const english = card({
        summary: [{ text: { es: words(10), en: words(61) }, facts: ["capacity"] }],
      });
      expectError(check([english]), "summary (en) has 61 words");
    });

    it("adds the sentences of the summary together", () => {
      const split = card({
        summary: [
          { text: { es: words(40) }, facts: ["capacity"] },
          { text: { es: words(21) }, facts: ["capacity"] },
        ],
      });
      expectError(check([split]), "has 61 words");
    });
  });

  describe("drift", () => {
    const withText = (es: string, factIds: string[], en?: string) =>
      card({
        summary: [{ text: en === undefined ? { es } : { es, en }, facts: factIds }],
      });

    it("normalises numbers per language", () => {
      expect(numbersIn("70.000 m² y 53,3 ha", "es")).toEqual(["70000", "53.3"]);
      expect(numbersIn("70.000 m² y 53,3 ha", "va")).toEqual(["70000", "53.3"]);
      expect(numbersIn("70,000 m² and 53.3 ha", "en")).toEqual(["70000", "53.3"]);
      expect(numbersIn("En 1987.", "es")).toEqual(["1987"]);
      expect(numbersIn("8:30 a 14:30", "es")).toEqual(["8", "30", "14", "30"]);
    });

    it("accepts numbers written in each language's form", () => {
      expect(check([withText("Más de 70.000 m².", ["big"])])).toEqual([]);
      expect(check([withText("Más de 70.000 m².", ["big"], "More than 70,000 m².")])).toEqual([]);
      expect(check([withText("Hay 53,3 ha.", ["area"], "It has 53.3 ha.")])).toEqual([]);
    });

    it("rejects a number the cited fact does not source", () => {
      expectError(
        check([withText("El aforo es de 400 personas.", ["capacity"])]),
        "the number 400",
      );
    });

    it("rejects a number that is right in another language form only", () => {
      expectError(check([withText("Hay 53.3 ha.", ["area"])]), "(es): the number 533");
      expectError(
        check([withText("Hay 53,3 ha.", ["area"], "It has 53,3 ha.")]),
        "(en): the number 533",
      );
    });

    it("counts a value note but not a fact-level note", () => {
      expect(check([withText("Desde la ampliación de 2015.", ["area"])])).toEqual([]);
      expectError(check([withText("Antes eran 45 ha.", ["area"])]), "the number 45");
    });

    it("takes the numbers of every fact a sentence cites", () => {
      expect(check([withText("300 y 53,3.", ["capacity", "area"])])).toEqual([]);
    });
  });

  describe("publish gate", () => {
    const complete = (): Poi =>
      card({
        status: "published",
        title: { es: "Centro", va: "Centre", en: "Centre" },
        summary: [
          {
            text: {
              es: "El aforo es de 300 personas al día.",
              va: "L'aforament és de 300 persones al dia.",
              en: "The limit is 300 people a day.",
            },
            facts: ["capacity"],
          },
        ],
        translations: {
          va: { status: "reviewed", by: "J. Soler", date: "2026-10-20" },
          en: { status: "team" },
        },
      });

    it("publishes a complete, reviewed card", () => {
      expect(check([complete()])).toEqual([]);
    });

    it("needs es, va and en everywhere", () => {
      const missing = { ...complete(), title: { es: "Centro", va: "Centre" } };
      expectError(check([missing]), "title has no en text");
    });

    it("needs the Valencian review, with who and when", () => {
      const draft = {
        ...complete(),
        translations: { ...complete().translations, va: { status: "draft" as const } },
      };
      expectError(check([draft]), "translations.va must be");
      const anonymous = {
        ...complete(),
        translations: { ...complete().translations, va: { status: "reviewed" as const } },
      };
      expectError(check([anonymous]), "translations.va must be");
    });

    it("needs the English to be at least a team translation", () => {
      const missing = {
        ...complete(),
        translations: { ...complete().translations, en: { status: "draft" as const } },
      };
      expectError(check([missing]), "translations.en must be");
    });

    it("does not ask a draft for any of it", () => {
      expect(check([card()])).toEqual([]);
    });
  });

  describe("anchor", () => {
    it("rejects an anchor that is not in trail.json", () => {
      expectError(check([card({ anchor: "nowhere" })]), 'anchor "nowhere" is not in trail.json');
    });

    it("skips the check when trail.json is absent", () => {
      expect(validatePois([card({ anchor: "nowhere" })], facts, sources, null)).toEqual([]);
    });
  });

  it("reports an invalid registry instead of checking against it", () => {
    expectError(validatePois([card()], [{ id: 3 }], sources, null), "facts.json");
    expectError(validatePois([card()], facts, [{ id: 3 }], null), "sources.json");
  });
});
