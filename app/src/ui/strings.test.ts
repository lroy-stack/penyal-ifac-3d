import { describe, expect, it } from "vitest";
import { DEFAULT_LOCALE, LOCALES, STRINGS, t } from "./strings";

describe("strings", () => {
  it("has the same non-empty keys in es, va and en", () => {
    const keys = Object.keys(STRINGS.es).sort();
    for (const locale of LOCALES) {
      expect(Object.keys(STRINGS[locale]).sort(), locale).toEqual(keys);
      for (const key of keys) {
        expect(STRINGS[locale][key as keyof typeof STRINGS.es].trim(), `${locale}.${key}`).not.toBe(
          "",
        );
      }
    }
  });

  it("shows Spanish by default", () => {
    expect(DEFAULT_LOCALE).toBe("es");
    expect(t("creditsButton")).toBe("Créditos");
    expect(t("creditsButton", "en")).toBe("Credits");
  });
});
