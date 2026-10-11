import { existsSync, readdirSync, readFileSync } from "node:fs";
import { basename } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { type Poi, poiSchema, validatePois } from "./poi";
import { factsFileSchema, sourcesFileSchema } from "./schema";

const root = (path: string): string => fileURLToPath(new URL(`../../../${path}`, import.meta.url));
const POIS_DIRECTORY = root("content/pois");
const TRAIL = root("app/public/assets/generated/trail.json");
const IMAGES_DIRECTORY = root("app/public/content/images");
const readJson = (path: string): unknown => JSON.parse(readFileSync(path, "utf8"));

const files = readdirSync(POIS_DIRECTORY)
  .filter((name) => name.endsWith(".json"))
  .sort();
const cards = files.map((name) => readJson(`${POIS_DIRECTORY}/${name}`));
const facts = factsFileSchema.parse(readJson(root("content/facts.json"))).facts;
const sources = sourcesFileSchema.parse(readJson(root("content/sources.json"))).sources;

function trailAnchors(): ReadonlySet<string> | null {
  if (!existsSync(TRAIL)) return null;
  const trail = readJson(TRAIL) as { anchors: Record<string, unknown> };
  return new Set(Object.keys(trail.anchors));
}

describe("content/pois", () => {
  it("has at least one card", () => {
    expect(files.length).toBeGreaterThan(0);
  });

  it("passes every rule of the POI contract", () => {
    expect(validatePois(cards, facts, sources, trailAnchors())).toEqual([]);
  });

  it("names each file after the id of its card", () => {
    for (const [index, name] of files.entries()) {
      const id = (cards[index] as { id?: string }).id;
      expect(id, `${name} has the id it is named after`).toBe(basename(name, ".json"));
    }
  });

  it("checks the anchors against trail.json, which must be there when the data is required", () => {
    if (process.env.PENYAL_REQUIRE_DATA === "1") {
      expect(existsSync(TRAIL), `${TRAIL} is missing; run the pipeline (penyal trail).`).toBe(true);
    }
    const anchors = trailAnchors();
    if (anchors === null) return;
    for (const card of cards) expect(anchors.has((card as Poi).anchor)).toBe(true);
  });

  it("only uses images that exist and are licensed CC0 or CC BY 4.0", () => {
    for (const card of cards.map((raw) => poiSchema.parse(raw))) {
      for (const image of card.images) {
        expect(existsSync(`${IMAGES_DIRECTORY}/${image.file}`), `${card.id}: ${image.file}`).toBe(
          true,
        );
      }
    }
  });

  it("keeps drafts as drafts until the Valencian review is done", () => {
    for (const card of cards.map((raw) => poiSchema.parse(raw))) {
      if (card.translations.va.status !== "reviewed") expect(card.status).toBe("draft");
    }
  });
});
