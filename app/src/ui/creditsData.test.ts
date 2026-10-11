import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { buildCredits, parseCatalog, parseCreditsMarkdown } from "./creditsData";
import { STRINGS } from "./strings";

const ROOT = resolve(import.meta.dirname, "../../..");
const catalog = readFileSync(resolve(ROOT, "data/catalog.toml"), "utf8");
const creditsMd = readFileSync(resolve(ROOT, "CREDITS.md"), "utf8");

describe("parseCatalog", () => {
  it("reads the string fields of every [[source]] table and ignores the other tables", () => {
    const toml = [
      "# comment",
      "[[source]]",
      'id = "a"',
      "phase = 1",
      'licence = "CC BY 4.0"',
      'attribution = "© A \\"quoted\\" · B"  # trailing comment',
      "bbox = [1, 2, 3, 4]",
      "[[source.layers]]",
      'name = "ignored"',
      "[[source]]",
      'id = "b"',
      "phase = 2",
      'licence = "ODbL 1.0"',
      'attribution = "© B"',
    ].join("\n");

    expect(parseCatalog(toml)).toEqual([
      { id: "a", phase: 1, licence: "CC BY 4.0", attribution: '© A "quoted" · B' },
      { id: "b", phase: 2, licence: "ODbL 1.0", attribution: "© B" },
    ]);
  });

  it("fails loudly on TOML it does not understand", () => {
    expect(() => parseCatalog('[[source]]\nid = """multi\nline"""')).toThrow(/line 2/);
    expect(() => parseCatalog("[[source]]\nthis is not toml")).toThrow(/line 2/);
  });

  it("parses the real catalogue", () => {
    const sources = parseCatalog(catalog);
    expect(sources.length).toBeGreaterThan(10);
    for (const source of sources) {
      expect(source.licence, source.id).not.toBe("");
      expect(source.attribution, source.id).not.toBe("");
    }
  });
});

describe("parseCreditsMarkdown", () => {
  it("turns the approximation bullets and the software table into plain text", () => {
    const md = [
      "# Credits",
      "Code: © the contributors, licensed under the [EUPL-1.2](LICENSE).",
      "## Approximations",
      "Intro that is not a bullet.",
      "- **Seabed**: constant `-3.0 m`, see [ADR](x). More.",
      "- **Other** (with a note, spec Q2): text",
      "## Third-party software shipped in the app",
      "| Component | Version | Licence |",
      "|---|---|---|",
      "| three.js | 0.186.1 | MIT |",
    ].join("\n");

    expect(parseCreditsMarkdown(md)).toEqual({
      code: "© the contributors, licensed under the EUPL-1.2.",
      approximations: [
        { title: "Seabed", text: "constant -3.0 m, see ADR. More." },
        { title: "Other (with a note, spec Q2)", text: "text" },
      ],
      software: [{ component: "three.js", version: "0.186.1", licence: "MIT" }],
    });
  });

  it("refuses a bullet it cannot split instead of dropping it", () => {
    const md = "## Approximations\n- Not bold: text\n## Third-party software shipped in the app\n";
    expect(() => parseCreditsMarkdown(md)).toThrow(/Not bold/);
  });

  it("requires the sections it reads", () => {
    expect(() => parseCreditsMarkdown("# Credits\n")).toThrow(/Approximations/);
  });
});

describe("parseCatalog escapes", () => {
  const source = (attribution: string): string =>
    [
      "[[source]]",
      'id = "a"',
      "phase = 1",
      'licence = "CC0"',
      `attribution = "${attribution}"`,
    ].join("\n");

  it("decodes the escapes TOML basic strings define that the catalogue may use", () => {
    expect(parseCatalog(source("a\\tb\\u00e9")).at(0)?.attribution).toBe("a\tb\u00e9");
  });

  it.each(["\\b", "\\f", "\\U0001F600", "\\x41", "\\u12"])(
    "throws on the escape %s instead of keeping it as text",
    (sequence) => {
      expect(() => parseCatalog(source(`x${sequence}y`))).toThrow(/escape/);
    },
  );
});

describe("buildCredits from the real files", () => {
  const credits = buildCredits(catalog, creditsMd);

  it("lists each credit line once, with its licence link, and skips unlicensed or later-phase data", () => {
    const attributions = credits.sources.map((s) => s.attribution);
    expect(new Set(attributions).size).toBe(attributions.length);
    expect(attributions.join("\n")).toContain("Institut Cartogràfic Valencià");
    expect(attributions.join("\n")).toContain("OpenStreetMap");
    expect(attributions.join("\n")).toContain("Poly Haven");
    expect(attributions.join("\n")).not.toContain("MITECO");
    for (const source of credits.sources) expect(source.licenceUrl).toMatch(/^https:\/\//);
  });

  it("carries the approximations the app depends on", () => {
    const titles = credits.approximations.map((a) => a.title.toLowerCase());
    expect(titles.filter((t) => t.includes("tunnel")).length).toBeGreaterThanOrEqual(3);
    expect(titles.some((t) => t.includes("seabed"))).toBe(true);
    expect(titles.some((t) => t.includes("limestone"))).toBe(true);
  });

  it("lists the shipped third-party software", () => {
    expect(credits.software.map((s) => s.component).join(" ")).toContain("three.js");
    expect(credits.code).toContain("EUPL-1.2");
  });

  it.each(["es", "va", "en"] as const)(
    "keeps the on-screen attribution line (%s) in step with the licences of the data in use",
    (locale) => {
      const line = STRINGS[locale].attributionLine;
      for (const licence of new Set(credits.sources.map((s) => s.licence.replace(/ 1\.0$/, "")))) {
        expect(line, `attribution line mentions ${licence}`).toContain(licence);
      }
      expect(line).toContain("OpenStreetMap");
      expect(line).toContain("Poly Haven");
      expect(line).toContain("Institut Cartogràfic Valencià");
    },
  );
});
