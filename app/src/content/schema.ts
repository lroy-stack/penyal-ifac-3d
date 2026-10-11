import { z } from "zod";

export const SOURCE_KINDS = [
  "official-gva",
  "official-calp",
  "official-state",
  "official-other",
  "community",
  "derived",
] as const;

export const FACT_TOPICS = [
  "park",
  "visitor-centre",
  "trail",
  "tunnel",
  "carabiners",
  "pobla",
  "summit",
  "silene",
  "birds",
  "flora",
  "fauna",
  "toponymy",
  "access",
] as const;

export const FACT_STATUSES = ["verified", "conflict", "unverified"] as const;

const KEBAB_CASE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export function isKebabCase(value: string): boolean {
  return KEBAB_CASE.test(value);
}

export function isValidIsoDate(value: string): boolean {
  if (!ISO_DATE.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

export const kebabId = z
  .string()
  .refine(isKebabCase, { message: "must be kebab-case (a-z, 0-9, '-')" });
export const isoDate = z
  .string()
  .refine(isValidIsoDate, { message: "must be a real calendar date formatted YYYY-MM-DD" });
export const httpsUrl = z.url({ protocol: /^https$/ });

export const sourceSchema = z.strictObject({
  id: kebabId,
  publisher: z.string().min(1),
  kind: z.enum(SOURCE_KINDS),
  title: z.string().min(1),
  url: httpsUrl,
  accessed: isoDate,
  archivedCopy: httpsUrl.optional(),
  note: z.string().min(1).optional(),
});

export const factValueSchema = z.strictObject({
  value: z.string().min(1),
  unit: z.string().min(1).optional(),
  sources: z.array(kebabId),
  note: z.string().min(1).optional(),
});

export const factSchema = z.strictObject({
  id: kebabId,
  topic: z.enum(FACT_TOPICS),
  statement: z.string().min(1),
  status: z.enum(FACT_STATUSES),
  values: z.array(factValueSchema),
  checked: isoDate,
  note: z.string().optional(),
});

export const sourcesFileSchema = z.strictObject({ sources: z.array(sourceSchema) });
export const factsFileSchema = z.strictObject({ facts: z.array(factSchema) });

export type Source = z.infer<typeof sourceSchema>;
export type FactValue = z.infer<typeof factValueSchema>;
export type Fact = z.infer<typeof factSchema>;

function formatIssues(file: string, error: z.ZodError): string[] {
  return error.issues.map((issue) => {
    const path = issue.path.length > 0 ? issue.path.join(".") : "(root)";
    return `${file}: ${path}: ${issue.message}. Fix the entry to match the schema in app/src/content/schema.ts.`;
  });
}

function findDuplicates(ids: readonly string[]): string[] {
  const seen = new Set<string>();
  const duplicates = new Set<string>();
  for (const id of ids) {
    if (seen.has(id)) duplicates.add(id);
    seen.add(id);
  }
  return [...duplicates];
}

function checkSources(sources: readonly Source[], today: string): string[] {
  const errors: string[] = [];
  for (const id of findDuplicates(sources.map((source) => source.id))) {
    errors.push(`sources.json: duplicate source id "${id}". Ids must be unique; rename or merge.`);
  }
  for (const source of sources) {
    if (source.accessed > today) {
      errors.push(
        `sources.json: source "${source.id}" has accessed=${source.accessed}, which is after ${today}. Use the real access date.`,
      );
    }
  }
  return errors;
}

function checkFact(fact: Fact, kindById: ReadonlyMap<string, Source["kind"]>, today: string) {
  const errors: string[] = [];
  if (fact.checked > today) {
    errors.push(
      `facts.json: fact "${fact.id}" has checked=${fact.checked}, which is after ${today}. Use the real check date.`,
    );
  }

  for (const [index, value] of fact.values.entries()) {
    if (value.sources.length === 0) {
      errors.push(
        `facts.json: fact "${fact.id}" value #${index + 1} ("${value.value}") has no sources. Cite at least one source id.`,
      );
    }
    for (const sourceId of value.sources) {
      if (!kindById.has(sourceId)) {
        errors.push(
          `facts.json: fact "${fact.id}" value #${index + 1} cites unknown source "${sourceId}". Add it to sources.json or fix the id.`,
        );
      }
    }
  }

  if (fact.values.length === 0) {
    errors.push(
      `facts.json: fact "${fact.id}" has no values. Every fact needs at least one value with a source; for a missing figure, state what the sources say (e.g. "not published") and cite them.`,
    );
  }

  if (fact.status === "verified") {
    const isOfficial = (id: string) => kindById.get(id)?.startsWith("official-") === true;
    if (new Set(fact.values.map((value) => value.value)).size > 1) {
      errors.push(
        `facts.json: verified fact "${fact.id}" has more than one distinct value. Sources that disagree make it a "conflict".`,
      );
    }
    for (const [index, value] of fact.values.entries()) {
      if (!value.sources.some(isOfficial)) {
        errors.push(
          `facts.json: verified fact "${fact.id}" value #${index + 1} has no official source (kind "official-*"). Cite an official source or downgrade the status.`,
        );
      }
    }
  }

  if (fact.status === "conflict") {
    const distinct = new Set(fact.values.map((value) => value.value));
    if (fact.values.length < 2 || distinct.size < 2) {
      errors.push(
        `facts.json: conflict fact "${fact.id}" needs at least two values with different "value" strings. Add the competing value or change the status.`,
      );
    }
  }

  if (fact.status === "unverified" && (fact.note ?? "").trim() === "") {
    errors.push(
      `facts.json: unverified fact "${fact.id}" needs a non-empty note explaining what is missing.`,
    );
  }
  return errors;
}

/**
 * Validates the shape and the cross-file rules of the fact registry.
 * `today` (YYYY-MM-DD) is injected so callers control the clock.
 * Returns human-readable errors; an empty list means the registry is valid.
 */
export function validateRegistry(sources: unknown, facts: unknown, today: string): string[] {
  if (!isValidIsoDate(today)) {
    return [`validateRegistry: "today" must be a valid YYYY-MM-DD date, got "${today}".`];
  }
  const parsedSources = z.array(sourceSchema).safeParse(sources);
  const parsedFacts = z.array(factSchema).safeParse(facts);
  const errors: string[] = [];
  if (!parsedSources.success) errors.push(...formatIssues("sources.json", parsedSources.error));
  if (!parsedFacts.success) errors.push(...formatIssues("facts.json", parsedFacts.error));
  if (!parsedSources.success || !parsedFacts.success) return errors;

  const sourceList = parsedSources.data;
  const factList = parsedFacts.data;
  const kindById = new Map(sourceList.map((source) => [source.id, source.kind] as const));

  errors.push(...checkSources(sourceList, today));
  for (const id of findDuplicates(factList.map((fact) => fact.id))) {
    errors.push(`facts.json: duplicate fact id "${id}". Ids must be unique; rename or merge.`);
  }
  for (const fact of factList) errors.push(...checkFact(fact, kindById, today));

  const referenced = new Set(factList.flatMap((fact) => fact.values.flatMap((v) => v.sources)));
  for (const source of sourceList) {
    if (!referenced.has(source.id)) {
      errors.push(
        `sources.json: source "${source.id}" is not referenced by any fact. Cite it from a fact or remove it.`,
      );
    }
  }
  return errors;
}
