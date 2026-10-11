import { describe, expect, it } from "vitest";
import { testHooksEnabled } from "./testHooks";

describe("testHooksEnabled", () => {
  it("is on in the dev server", () => {
    expect(testHooksEnabled({ DEV: true })).toBe(true);
  });

  it("is on in a production build made for the Playwright runs", () => {
    expect(testHooksEnabled({ DEV: false, VITE_E2E: "true" })).toBe(true);
  });

  it("is off in a normal production build, whatever else is set", () => {
    expect(testHooksEnabled({ DEV: false })).toBe(false);
    expect(testHooksEnabled({ DEV: false, VITE_E2E: "false" })).toBe(false);
    expect(testHooksEnabled({ DEV: false, VITE_E2E: "1" })).toBe(false);
  });
});
