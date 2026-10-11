/**
 * Credits for the in-app dialog, derived at build time from `data/catalog.toml` (what data is
 * used and under which licence) and `CREDITS.md` (approximations, software). Pure functions on
 * strings: the Vite plugin reads the files and exposes the result as `virtual:credits`.
 */

export type CatalogSource = {
  id: string;
  phase: number;
  licence: string;
  attribution: string;
};

export type CreditSource = {
  attribution: string;
  licence: string;
  licenceUrl: string;
};

export type Credits = {
  /** Licence line of the project's own code. */
  code: string;
  sources: CreditSource[];
  approximations: { title: string; text: string }[];
  software: { component: string; version: string; licence: string }[];
};

/** Data up to this phase is shipped in the app; later phases are not used yet. */
export const SHIPPED_PHASE = 2;

const LICENCE_URLS: Readonly<Record<string, string>> = {
  "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
  "ODbL 1.0": "https://opendatacommons.org/licenses/odbl/1-0/",
  "CC0 1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
};

const STRING_FIELD = /^([A-Za-z_][\w-]*)\s*=\s*"((?:[^"\\]|\\.)*)"\s*(?:#.*)?$/;
const SCALAR_FIELD = /^([A-Za-z_][\w-]*)\s*=\s*(-?[\d.]+|true|false|\[[^\]"]*\])\s*(?:#.*)?$/;

function unescapeBasic(value: string): string {
  return value.replace(/\\(["\\ntr]|u[0-9a-fA-F]{4})/g, (_match, code: string) => {
    if (code.startsWith("u")) return String.fromCharCode(Number.parseInt(code.slice(1), 16));
    return { '"': '"', "\\": "\\", n: "\n", t: "\t", r: "\r" }[code] as string;
  });
}

/**
 * Reads `id`, `phase`, `licence` and `attribution` of every `[[source]]` table. It understands
 * only the TOML the catalogue uses (single-line strings, numbers, booleans, flat arrays) and
 * throws on anything else, so a change of style cannot silently drop a credit.
 */
export function parseCatalog(toml: string): CatalogSource[] {
  const sources: Record<string, string | number>[] = [];
  let current: Record<string, string | number> | null = null;
  toml.split(/\r?\n/).forEach((raw, index) => {
    const line = raw.trim();
    if (line === "" || line.startsWith("#")) return;
    if (line === "[[source]]") {
      current = {};
      sources.push(current);
      return;
    }
    if (line.startsWith("[")) {
      current = null;
      return;
    }
    const text = STRING_FIELD.exec(line);
    if (text !== null) {
      if (current !== null) current[text[1] as string] = unescapeBasic(text[2] as string);
      return;
    }
    const scalar = SCALAR_FIELD.exec(line);
    if (scalar !== null) {
      const value = scalar[2] as string;
      if (current !== null && /^-?[\d.]+$/.test(value)) {
        current[scalar[1] as string] = Number(value);
      }
      return;
    }
    throw new Error(
      `data/catalog.toml line ${index + 1} is not supported by parseCatalog: ${line}`,
    );
  });
  return sources.map((fields) => {
    const { id, phase, licence, attribution } = fields;
    if (
      typeof id !== "string" ||
      typeof phase !== "number" ||
      typeof licence !== "string" ||
      typeof attribution !== "string"
    ) {
      throw new Error(`A [[source]] in data/catalog.toml lacks id, phase, licence or attribution.`);
    }
    return { id, phase, licence, attribution };
  });
}

function plain(markdown: string): string {
  return markdown
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .trim();
}

function sectionLines(lines: readonly string[], heading: string): string[] {
  const start = lines.findIndex((line) => line.trim() === `## ${heading}`);
  if (start < 0) throw new Error(`CREDITS.md has no "## ${heading}" section.`);
  const rest = lines.slice(start + 1);
  const end = rest.findIndex((line) => line.startsWith("## "));
  return end < 0 ? rest : rest.slice(0, end);
}

function tableRows(lines: readonly string[]): string[][] {
  return lines
    .filter((line) => line.trim().startsWith("|"))
    .map((line) =>
      line
        .trim()
        .replace(/^\||\|$/g, "")
        .split("|")
        .map((cell) => plain(cell)),
    )
    .filter((cells) => !cells.every((cell) => /^:?-+:?$/.test(cell)))
    .slice(1);
}

export function parseCreditsMarkdown(markdown: string): Omit<Credits, "sources"> {
  const lines = markdown.split(/\r?\n/);
  const codeLine = lines.find((line) => line.startsWith("Code:"));
  const approximations = sectionLines(lines, "Approximations")
    .filter((line) => line.startsWith("- "))
    .map((line) => {
      const match = /^- \*\*(.+?)\*\*(\s*\([^)]*\))?:\s*(.+)$/.exec(line);
      if (match === null) {
        throw new Error(
          `CREDITS.md approximation is not "- **Title**: text": ${line.slice(0, 60)}`,
        );
      }
      return {
        title: plain(`${match[1] as string}${match[2] ?? ""}`),
        text: plain(match[3] as string),
      };
    });
  const software = tableRows(sectionLines(lines, "Third-party software shipped in the app")).map(
    ([component, version, licence]) => ({
      component: component ?? "",
      version: version ?? "",
      licence: licence ?? "",
    }),
  );
  return {
    code: plain((codeLine ?? "").replace(/^Code:\s*/, "")),
    approximations,
    software,
  };
}

export function buildCredits(catalogToml: string, creditsMarkdown: string): Credits {
  const seen = new Set<string>();
  const sources: CreditSource[] = [];
  for (const source of parseCatalog(catalogToml)) {
    if (source.phase > SHIPPED_PHASE || source.licence.startsWith("unknown")) continue;
    const key = `${source.licence}\n${source.attribution}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const licenceUrl = LICENCE_URLS[source.licence];
    if (licenceUrl === undefined) {
      throw new Error(
        `No licence link for "${source.licence}" (${source.id}); add it to LICENCE_URLS.`,
      );
    }
    sources.push({ attribution: source.attribution, licence: source.licence, licenceUrl });
  }
  return { ...parseCreditsMarkdown(creditsMarkdown), sources };
}
