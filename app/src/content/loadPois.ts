import { type Poi, poiSchema } from "./poi";

/** The cards of `content/pois/*.json`; Vite turns the glob into one lazy chunk per file. */
const CARD_MODULES = import.meta.glob<unknown>("../../../content/pois/*.json", {
  import: "default",
});

export type LoadedPois = {
  readonly pois: readonly Poi[];
  /** Cards that do not match the schema, as readable messages. */
  readonly problems: readonly string[];
};

/** Loads and parses every card; an invalid card is reported and skipped, never shown. */
export async function loadPois(): Promise<LoadedPois> {
  const pois: Poi[] = [];
  const problems: string[] = [];
  for (const [path, load] of Object.entries(CARD_MODULES)) {
    const parsed = poiSchema.safeParse(await load());
    if (parsed.success) pois.push(parsed.data);
    else problems.push(`${path}: ${parsed.error.issues.map((issue) => issue.message).join("; ")}`);
  }
  return { pois, problems };
}
