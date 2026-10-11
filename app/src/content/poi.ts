import { z } from "zod";
import type { LocalPoint } from "../geo/frame";
import {
  type Fact,
  factSchema,
  httpsUrl,
  isoDate,
  kebabId,
  type Source,
  sourceSchema,
} from "./schema";

export const LANGUAGES = ["es", "va", "en"] as const;
export type Language = (typeof LANGUAGES)[number];

/** Longest summary (words) per language present. */
export const MAX_SUMMARY_WORDS = 60;

const text = z.strictObject({
  es: z.string().min(1),
  va: z.string().min(1).optional(),
  en: z.string().min(1).optional(),
});
/** No sentence without a fact. */
const sentence = z.strictObject({ text, facts: z.array(kebabId).min(1) });
const block = z.discriminatedUnion("kind", [
  z.strictObject({ kind: z.literal("facts"), heading: text, items: z.array(sentence).min(1) }),
  z.strictObject({
    kind: z.literal("conflict"),
    fact: kebabId,
    heading: text,
    values: z.array(z.strictObject({ text })).min(2),
  }),
  z.strictObject({ kind: z.literal("unverified"), fact: kebabId, text }),
  z.strictObject({ kind: z.literal("notice"), text, source: kebabId }),
]);
const review = z.strictObject({
  status: z.enum(["missing", "draft", "team", "reviewed"]),
  by: z.string().min(1).optional(),
  date: isoDate.optional(),
});

export const poiSchema = z.strictObject({
  id: kebabId,
  status: z.enum(["draft", "published"]),
  /** Key in the `anchors` of trail.json. */
  anchor: z.string().min(1),
  /** Horizontal metres. */
  discoveryRadius: z.number().min(3).max(40),
  title: text,
  /** At most 60 words per language. */
  summary: z.array(sentence).min(1),
  expand: z.array(block),
  images: z
    .array(
      z.strictObject({
        file: z.string().regex(/^[a-z0-9-]+\.(?:avif|webp|jpg)$/),
        alt: text,
        author: z.string().min(1),
        licence: z.enum(["CC0-1.0", "CC-BY-4.0"]),
        source: httpsUrl,
        modified: z.boolean(),
      }),
    )
    .max(3),
  translations: z.strictObject({ va: review, en: review }),
});

export type Poi = z.infer<typeof poiSchema>;
type Text = z.infer<typeof text>;
type Block = z.infer<typeof block>;

/** Where discovery looks for the POIs and who hears about a discovered one. */
export interface PoiRegistry {
  list(): readonly { readonly poi: Poi; readonly position: LocalPoint }[];
  /** Once per POI per visit, by the 2D radius; listener errors are caught. Returns unsubscribe. */
  onDiscover(listener: (poi: Poi) => void): () => void;
}

/** A word is a whitespace-separated token with a letter or a digit. */
export function countWords(value: string): number {
  return value.split(/\s+/).filter((token) => /[\p{L}\p{N}]/u.test(token)).length;
}

/**
 * The numbers written as digits in `value`, normalised: es and va write `70.000` and `53,3`, en
 * writes `70,000` and `53.3`. `facts.json` uses the Spanish form. The result has no thousands
 * separators and a point as decimal separator.
 */
export function numbersIn(value: string, language: Language): string[] {
  const decimal = language === "en" ? "." : ",";
  const thousands = language === "en" ? "," : ".";
  return (value.match(/\d+(?:[.,]\d+)*/g) ?? []).map((token) =>
    token.split(thousands).join("").split(decimal).join("."),
  );
}

function formatIssues(file: string, error: z.ZodError): string[] {
  return error.issues.map((issue) => {
    const path = issue.path.length > 0 ? issue.path.join(".") : "(root)";
    return `${file}: ${path}: ${issue.message}. Fix the card to match the schema in app/src/content/poi.ts.`;
  });
}

/** Every number a fact sources: its values, units and value notes (not the fact-level note). */
function sourcedNumbers(fact: Fact, only?: number): Set<string> {
  const values = only === undefined ? fact.values : fact.values.slice(only, only + 1);
  const out = new Set<string>();
  for (const value of values) {
    for (const part of [value.value, value.unit ?? "", value.note ?? ""]) {
      for (const number of numbersIn(part, "es")) out.add(number);
    }
  }
  return out;
}

function languagesOf(value: Text): Language[] {
  return LANGUAGES.filter((language) => value[language] !== undefined);
}

type Context = {
  readonly file: string;
  readonly poi: Poi;
  readonly facts: ReadonlyMap<string, Fact>;
  readonly sources: ReadonlySet<string>;
  readonly errors: string[];
};

function checkNumbers(
  context: Context,
  where: string,
  value: Text,
  allowed: ReadonlySet<string>,
  factIds: string,
): void {
  for (const language of languagesOf(value)) {
    for (const number of numbersIn(value[language] ?? "", language)) {
      if (!allowed.has(number)) {
        context.errors.push(
          `${context.file}: ${where} (${language}): the number ${number} is not in a value, unit or value note of ${factIds}. Source the number as a value in facts.json (fact-level notes do not count) or drop it.`,
        );
      }
    }
  }
}

function lookup(context: Context, where: string, id: string): Fact | undefined {
  const fact = context.facts.get(id);
  if (fact === undefined) {
    context.errors.push(
      `${context.file}: ${where} cites unknown fact "${id}". Add it to facts.json or fix the id.`,
    );
  }
  return fact;
}

function checkSentence(
  context: Context,
  where: string,
  item: { readonly text: Text; readonly facts: readonly string[] },
  summary: boolean,
): void {
  const allowed = new Set<string>();
  const cited: Fact[] = [];
  for (const id of item.facts) {
    const fact = lookup(context, where, id);
    if (fact === undefined) continue;
    cited.push(fact);
    for (const number of sourcedNumbers(fact)) allowed.add(number);
    if (summary && fact.status !== "verified") {
      context.errors.push(
        `${context.file}: ${where} cites ${fact.status} fact "${id}" in the summary. The summary cites verified facts only; show a ${fact.status} fact in a "${fact.status}" block of the expansion.`,
      );
    }
    if (!summary && fact.status !== "verified") {
      context.errors.push(
        `${context.file}: ${where} cites ${fact.status} fact "${id}" in a "facts" block. A ${fact.status} fact belongs in a block of kind "${fact.status}", where no side is picked.`,
      );
    }
  }
  if (cited.length === item.facts.length) {
    checkNumbers(context, where, item.text, allowed, item.facts.map((id) => `"${id}"`).join(", "));
  }
}

function checkBlock(context: Context, index: number, entry: Block): void {
  const where = `expand.${index}`;
  switch (entry.kind) {
    case "facts":
      entry.items.forEach((item, i) => {
        checkSentence(context, `${where}.items.${i}`, item, false);
      });
      return;
    case "conflict": {
      const fact = lookup(context, where, entry.fact);
      if (fact === undefined) return;
      if (fact.status !== "conflict") {
        context.errors.push(
          `${context.file}: ${where} is a "conflict" block for "${entry.fact}", whose status is ${fact.status}. Use a block of kind "${fact.status === "verified" ? "facts" : fact.status}".`,
        );
        return;
      }
      if (entry.values.length !== fact.values.length) {
        context.errors.push(
          `${context.file}: ${where} shows ${entry.values.length} values for "${entry.fact}", which has ${fact.values.length}. Show every value, in registry order.`,
        );
        return;
      }
      entry.values.forEach((item, i) => {
        checkNumbers(
          context,
          `${where}.values.${i}`,
          item.text,
          sourcedNumbers(fact, i),
          `value #${i + 1} of "${entry.fact}"`,
        );
      });
      return;
    }
    case "unverified": {
      const fact = lookup(context, where, entry.fact);
      if (fact === undefined) return;
      if (fact.status !== "unverified") {
        context.errors.push(
          `${context.file}: ${where} is an "unverified" block for "${entry.fact}", whose status is ${fact.status}. Use a block of kind "${fact.status === "verified" ? "facts" : fact.status}".`,
        );
        return;
      }
      checkNumbers(context, where, entry.text, sourcedNumbers(fact), `"${entry.fact}"`);
      return;
    }
    case "notice":
      if (!context.sources.has(entry.source)) {
        context.errors.push(
          `${context.file}: ${where} cites unknown source "${entry.source}". Add it to sources.json or fix the id.`,
        );
      }
      return;
    default: {
      const unreachable: never = entry;
      throw new Error(`Unknown block ${JSON.stringify(unreachable)}`);
    }
  }
}

/** Every `text` object of a card with its path, for the publish gate. */
function textsOf(poi: Poi): { readonly where: string; readonly value: Text }[] {
  const out: { where: string; value: Text }[] = [{ where: "title", value: poi.title }];
  for (const [i, item] of poi.summary.entries()) {
    out.push({ where: `summary.${i}`, value: item.text });
  }
  for (const [i, entry] of poi.expand.entries()) {
    const where = `expand.${i}`;
    if (entry.kind === "facts") {
      out.push({ where: `${where}.heading`, value: entry.heading });
      for (const [j, item] of entry.items.entries()) {
        out.push({ where: `${where}.items.${j}`, value: item.text });
      }
    } else if (entry.kind === "conflict") {
      out.push({ where: `${where}.heading`, value: entry.heading });
      for (const [j, item] of entry.values.entries()) {
        out.push({ where: `${where}.values.${j}`, value: item.text });
      }
    } else {
      out.push({ where, value: entry.text });
    }
  }
  for (const [i, image] of poi.images.entries()) {
    out.push({ where: `images.${i}.alt`, value: image.alt });
  }
  return out;
}

function checkLength(context: Context): void {
  for (const language of LANGUAGES) {
    const words = context.poi.summary
      .map((item) => item.text[language])
      .filter((value): value is string => value !== undefined)
      .reduce((total, value) => total + countWords(value), 0);
    if (words > MAX_SUMMARY_WORDS) {
      context.errors.push(
        `${context.file}: summary (${language}) has ${words} words, over ${MAX_SUMMARY_WORDS}. Shorten it or move sentences to the expansion.`,
      );
    }
  }
}

function checkPublishGate(context: Context): void {
  const { poi, file, errors } = context;
  if (poi.status !== "published") return;
  for (const { where, value } of textsOf(poi)) {
    for (const language of LANGUAGES) {
      if (value[language] === undefined) {
        errors.push(
          `${file}: ${where} has no ${language} text, and a published card needs es, va and en everywhere. Translate it or keep the card as a draft.`,
        );
      }
    }
  }
  const { va, en } = poi.translations;
  if (va.status !== "reviewed" || va.by === undefined || va.date === undefined) {
    errors.push(
      `${file}: translations.va must be "reviewed" with "by" and "date" to publish. Get the Valencian review first.`,
    );
  }
  if (en.status !== "team" && en.status !== "reviewed") {
    errors.push(
      `${file}: translations.en must be "team" or "reviewed" to publish, not "${en.status}".`,
    );
  }
}

/**
 * Validates the cards of `content/pois/*.json` against the schema and the registry. Rules: ids
 * unique and cited facts and sources exist; the summary cites verified facts only and conflicts
 * and unverified facts appear only in blocks of their kind; at most 60 words per language; every
 * number in a sentence is sourced by the cited fact; a published card is complete and reviewed;
 * the anchor exists in trail.json (`anchors` null skips that check). Returns readable errors.
 */
export function validatePois(
  pois: unknown[],
  facts: unknown,
  sources: unknown,
  anchors: ReadonlySet<string> | null,
): string[] {
  const parsedFacts = z.array(factSchema).safeParse(facts);
  const parsedSources = z.array(sourceSchema).safeParse(sources);
  const errors: string[] = [];
  if (!parsedFacts.success) errors.push(...formatIssues("facts.json", parsedFacts.error));
  if (!parsedSources.success) errors.push(...formatIssues("sources.json", parsedSources.error));
  if (!parsedFacts.success || !parsedSources.success) return errors;
  const factById = new Map(parsedFacts.data.map((fact) => [fact.id, fact] as const));
  const sourceIds = new Set<string>(parsedSources.data.map((source: Source) => source.id));

  const seen = new Set<string>();
  pois.forEach((raw, index) => {
    const parsed = poiSchema.safeParse(raw);
    const name = parsed.success ? parsed.data.id : `#${index + 1}`;
    const file = `pois/${name}.json`;
    if (!parsed.success) {
      errors.push(...formatIssues(file, parsed.error));
      return;
    }
    const poi = parsed.data;
    if (seen.has(poi.id)) {
      errors.push(`${file}: duplicate POI id "${poi.id}". Ids must be unique; rename one.`);
    }
    seen.add(poi.id);
    const context: Context = { file, poi, facts: factById, sources: sourceIds, errors };
    poi.summary.forEach((item, i) => {
      checkSentence(context, `summary.${i}`, item, true);
    });
    poi.expand.forEach((entry, i) => {
      checkBlock(context, i, entry);
    });
    checkLength(context);
    checkPublishGate(context);
    if (anchors !== null && !anchors.has(poi.anchor)) {
      errors.push(
        `${file}: anchor "${poi.anchor}" is not in trail.json. Use one of: ${[...anchors].join(", ")}.`,
      );
    }
  });
  return errors;
}
