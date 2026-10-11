import { fetchBuffer, fetchJson } from "../core/http";
import { QuantizedHeightField, quantizedHeightFieldMetaSchema } from "./ground";

export const COLLISION_PATH = "assets/generated/terrain/collision";
/** The walk cannot start without the field: one 5xx or timeout must not end the visit. */
export const COLLISION_ATTEMPTS = 3;
/** Delay (ms) before the second attempt; doubles for the next. */
const COLLISION_RETRY_DELAY_MS = 1000;

function wait(ms: number, signal: AbortSignal | undefined): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted === true) {
      reject(signal.reason);
      return;
    }
    const onAbort = (): void => {
      clearTimeout(timer);
      reject(signal?.reason);
    };
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

/**
 * Loads `<basePath>.json` + `<basePath>.bin` (the walkable-area height field), trying up to
 * `COLLISION_ATTEMPTS` times with a doubling backoff. A caller abort is never retried.
 */
export async function loadCollisionField(
  basePath: string,
  signal?: AbortSignal,
): Promise<QuantizedHeightField> {
  for (let attempt = 1; ; attempt++) {
    try {
      const [meta, buffer] = await Promise.all([
        fetchJson(`${basePath}.json`, quantizedHeightFieldMetaSchema, signal),
        fetchBuffer(`${basePath}.bin`, signal),
      ]);
      return QuantizedHeightField.fromBuffer(meta, buffer);
    } catch (error) {
      if (signal?.aborted === true || attempt >= COLLISION_ATTEMPTS) throw error;
      await wait(COLLISION_RETRY_DELAY_MS * 2 ** (attempt - 1), signal);
    }
  }
}
