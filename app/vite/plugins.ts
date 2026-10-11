import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { Plugin } from "vite";
import { buildCredits } from "../src/ui/creditsData";
import { DEFAULT_LOCALE, STRINGS } from "../src/ui/strings";

const CREDITS_MODULE = "virtual:credits";
const RESOLVED_CREDITS_MODULE = `\0${CREDITS_MODULE}`;

/**
 * `virtual:credits`: the credits dialog data, derived from `data/catalog.toml` and `CREDITS.md`
 * every time the app is built or served, so the dialog cannot drift from those files.
 */
export function creditsModule(): Plugin {
  let repoRoot = "";
  return {
    name: "penyal:credits",
    configResolved(config) {
      repoRoot = resolve(config.root, "..");
    },
    resolveId(source) {
      return source === CREDITS_MODULE ? RESOLVED_CREDITS_MODULE : null;
    },
    load(id) {
      if (id !== RESOLVED_CREDITS_MODULE) return null;
      const catalogPath = resolve(repoRoot, "data/catalog.toml");
      const creditsPath = resolve(repoRoot, "CREDITS.md");
      this.addWatchFile(catalogPath);
      this.addWatchFile(creditsPath);
      const credits = buildCredits(
        readFileSync(catalogPath, "utf8"),
        readFileSync(creditsPath, "utf8"),
      );
      return `export default ${JSON.stringify(credits)};`;
    },
  };
}

function escapeHtml(text: string): string {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

/**
 * Replaces `{{key}}` in index.html with the default-locale string, so the text that must be
 * painted before any script runs (poster, attribution) lives in `strings.ts` like the rest.
 */
export function htmlStrings(): Plugin {
  return {
    name: "penyal:html-strings",
    transformIndexHtml(html) {
      const table = STRINGS[DEFAULT_LOCALE] as Readonly<Record<string, string>>;
      return html.replace(/\{\{(\w+)\}\}/g, (_match, key: string) => {
        const value = table[key];
        if (value === undefined) throw new Error(`index.html uses the unknown string {{${key}}}.`);
        return escapeHtml(value);
      });
    },
  };
}
