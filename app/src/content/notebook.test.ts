import { describe, expect, it, vi } from "vitest";
import { browserStorage, createNotebook, NOTEBOOK_KEY } from "./notebook";

function memoryStorage(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial));
  return {
    data,
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => {
      data.set(key, value);
    },
  };
}

const at = (iso: string) => () => new Date(iso);

describe("createNotebook", () => {
  it("starts empty and saves a card with the time it was saved", () => {
    const storage = memoryStorage();
    const notebook = createNotebook(storage, at("2026-10-11T10:00:00.000Z"));
    expect(notebook.list()).toEqual([]);
    expect(notebook.has("centre")).toBe(false);
    expect(notebook.add("centre")).toEqual({ ok: true });
    expect(notebook.has("centre")).toBe(true);
    expect(notebook.list()).toEqual([{ poiId: "centre", savedAt: "2026-10-11T10:00:00.000Z" }]);
    expect(JSON.parse(storage.data.get(NOTEBOOK_KEY) ?? "null")).toEqual({
      version: 1,
      entries: [{ poiId: "centre", savedAt: "2026-10-11T10:00:00.000Z" }],
    });
  });

  it("is idempotent and keeps the first savedAt", () => {
    let current = "2026-10-11T10:00:00.000Z";
    const notebook = createNotebook(memoryStorage(), () => new Date(current));
    notebook.add("centre");
    current = "2026-10-12T10:00:00.000Z";
    expect(notebook.add("centre")).toEqual({ ok: true });
    expect(notebook.list()).toEqual([{ poiId: "centre", savedAt: "2026-10-11T10:00:00.000Z" }]);
  });

  it("lists the cards in the order they were saved", () => {
    const notebook = createNotebook(memoryStorage(), at("2026-10-11T10:00:00.000Z"));
    notebook.add("b");
    notebook.add("a");
    notebook.add("c");
    expect(notebook.list().map((entry) => entry.poiId)).toEqual(["b", "a", "c"]);
  });

  it("reads what a previous visit saved", () => {
    const stored = JSON.stringify({
      version: 1,
      entries: [{ poiId: "centre", savedAt: "2026-10-01T08:00:00.000Z" }],
    });
    const notebook = createNotebook(
      memoryStorage({ [NOTEBOOK_KEY]: stored }),
      at("2026-10-11T10:00:00.000Z"),
    );
    expect(notebook.has("centre")).toBe(true);
    expect(notebook.persistent).toBe(true);
  });

  it.each([
    ["not JSON", "{oops"],
    ["a wrong version", JSON.stringify({ version: 2, entries: [] })],
    ["extra keys", JSON.stringify({ version: 1, entries: [], note: "x" })],
    ["a wrong entry", JSON.stringify({ version: 1, entries: [{ poiId: 3 }] })],
    [
      "an impossible date",
      JSON.stringify({ version: 1, entries: [{ poiId: "a", savedAt: "2026-13-45T00:00:00Z" }] }),
    ],
  ])("starts empty on %s and replaces it on the next add", (_name, raw) => {
    const storage = memoryStorage({ [NOTEBOOK_KEY]: raw });
    const notebook = createNotebook(storage, at("2026-10-11T10:00:00.000Z"));
    expect(notebook.list()).toEqual([]);
    notebook.add("centre");
    expect(JSON.parse(storage.data.get(NOTEBOOK_KEY) ?? "null").entries).toHaveLength(1);
  });

  it("works for this visit when storage is blocked, and says it is not persistent", () => {
    const notebook = createNotebook(null, at("2026-10-11T10:00:00.000Z"));
    expect(notebook.persistent).toBe(false);
    expect(notebook.add("centre")).toEqual({ ok: false, reason: "unavailable" });
    expect(notebook.has("centre")).toBe(true);
    expect(notebook.list()).toHaveLength(1);
  });

  it("reports a full storage as quota and keeps the entry for this visit", () => {
    const storage = {
      getItem: () => null,
      setItem: () => {
        throw new DOMException("full", "QuotaExceededError");
      },
    };
    const notebook = createNotebook(storage, at("2026-10-11T10:00:00.000Z"));
    expect(notebook.add("centre")).toEqual({ ok: false, reason: "quota" });
    expect(notebook.has("centre")).toBe(true);
    expect(notebook.persistent).toBe(false);
  });

  it("reports any other write failure as an error", () => {
    const storage = {
      getItem: () => null,
      setItem: () => {
        throw new Error("denied");
      },
    };
    const notebook = createNotebook(storage, at("2026-10-11T10:00:00.000Z"));
    expect(notebook.add("centre")).toEqual({ ok: false, reason: "error" });
  });

  it("survives a read that throws", () => {
    const storage = {
      getItem: () => {
        throw new Error("denied");
      },
      setItem: () => undefined,
    };
    const notebook = createNotebook(storage, at("2026-10-11T10:00:00.000Z"));
    expect(notebook.list()).toEqual([]);
    expect(notebook.add("centre")).toEqual({ ok: true });
  });
});

describe("browserStorage", () => {
  it("returns window.localStorage", () => {
    const local = memoryStorage();
    vi.stubGlobal("window", { localStorage: local });
    expect(browserStorage()).toBe(local);
    vi.unstubAllGlobals();
  });

  it("returns null when reading the property throws", () => {
    vi.stubGlobal("window", {
      get localStorage(): never {
        throw new DOMException("blocked", "SecurityError");
      },
    });
    expect(browserStorage()).toBeNull();
    vi.unstubAllGlobals();
  });

  it("returns null without a window", () => {
    expect(browserStorage()).toBeNull();
  });
});
