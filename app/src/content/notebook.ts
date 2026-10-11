import { z } from "zod";
import { isoDate } from "./schema";

export const NOTEBOOK_KEY = "penyal.notebook.v1";

export type NotebookEntry = {
  readonly poiId: string;
  /** ISO 8601 date and time. */
  readonly savedAt: string;
};

export type NotebookResult =
  | { readonly ok: true }
  | { readonly ok: false; readonly reason: "unavailable" | "quota" | "error" };

export interface Notebook {
  /** Idempotent: keeps the first `savedAt`. */
  add(poiId: string): NotebookResult;
  has(poiId: string): boolean;
  /** In saving order. */
  list(): readonly NotebookEntry[];
  /** False when storage is blocked: the entries last for this visit only. */
  readonly persistent: boolean;
}

type Storage2 = Pick<Storage, "getItem" | "setItem">;

const storedSchema = z.strictObject({
  version: z.literal(1),
  entries: z.array(z.strictObject({ poiId: z.string().min(1), savedAt: z.string().min(1) })),
});

// The date part must be a real calendar date; the schema above only needs a string.
const savedAtDate = (value: string): boolean => isoDate.safeParse(value.slice(0, 10)).success;

/** `window.localStorage`, or null when the browser blocks it (reading the property can throw). */
export function browserStorage(): Storage2 | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function isQuotaError(error: unknown): boolean {
  return (
    error instanceof DOMException &&
    (error.name === "QuotaExceededError" || error.name === "NS_ERROR_DOM_QUOTA_REACHED")
  );
}

/**
 * The visitor's saved cards. Only ids and dates are stored, under one key, in localStorage: no
 * cookies, no network. The in-memory copy is the source of truth for the visit; an invalid
 * stored value starts the notebook empty and is replaced by the next `add`.
 */
export function createNotebook(storage: Storage2 | null, now: () => Date): Notebook {
  let entries: NotebookEntry[] = [];
  let persistent = storage !== null;

  if (storage !== null) {
    try {
      const raw = storage.getItem(NOTEBOOK_KEY);
      if (raw !== null) {
        const parsed = storedSchema.safeParse(JSON.parse(raw));
        if (parsed.success) {
          entries = parsed.data.entries.filter((entry) => savedAtDate(entry.savedAt));
        }
      }
    } catch {
      // A throwing or unparsable read starts empty; the next add writes a valid value.
    }
  }

  const save = (): NotebookResult => {
    if (storage === null) return { ok: false, reason: "unavailable" };
    try {
      storage.setItem(NOTEBOOK_KEY, JSON.stringify({ version: 1, entries }));
      return { ok: true };
    } catch (error) {
      persistent = false;
      return { ok: false, reason: isQuotaError(error) ? "quota" : "error" };
    }
  };

  return {
    add(poiId) {
      if (!entries.some((entry) => entry.poiId === poiId)) {
        entries = [...entries, { poiId, savedAt: now().toISOString() }];
      }
      return save();
    },
    has: (poiId) => entries.some((entry) => entry.poiId === poiId),
    list: () => entries,
    get persistent() {
      return persistent;
    },
  };
}
