import type { ZodType } from "zod";

export class HttpError extends Error {
  constructor(
    readonly url: string,
    readonly status: number,
  ) {
    super(`Request for ${url} failed with HTTP ${status}.`);
    this.name = "HttpError";
  }
}

/** A 200 whose body is HTML is the dev server's SPA fallback for a file that does not exist. */
export class NotFoundError extends Error {
  constructor(readonly url: string) {
    super(`${url} does not exist.`);
    this.name = "NotFoundError";
  }
}

/** Small JSON files: a request that has not finished in this long is hung, not slow. */
export const JSON_TIMEOUT_MS = 30_000;
/** Multi-MB binaries (terrain tiles, collision field) must survive a slow 4G link. */
export const BINARY_TIMEOUT_MS = 90_000;

export class RequestTimeoutError extends Error {
  constructor(
    readonly url: string,
    readonly timeoutMs: number,
  ) {
    super(`Request for ${url} timed out after ${Math.round(timeoutMs / 1000)} s.`);
    this.name = "RequestTimeoutError";
  }
}

/** An answered request; the timeout keeps running until `read` has finished with the body. */
export type OpenResponse = {
  readonly response: Response;
  /** Reads the body, then stops the timeout. A timeout surfaces as `RequestTimeoutError`. */
  readonly read: <T>(reader: (response: Response) => Promise<T>) => Promise<T>;
};

/**
 * Starts a request that is aborted when `signal` fires or `timeoutMs` elapses, so a hung request
 * rejects into the caller's retry path. The signals are composed by hand: `AbortSignal.any` needs
 * Safari 17.4. The timer also covers reading the body. Some engines reject an aborted fetch or
 * body read with a generic AbortError instead of `signal.reason`; the timeout is rethrown as
 * such, so callers can tell it from a cancellation.
 */
async function open(
  url: string,
  signal: AbortSignal | undefined,
  timeoutMs: number,
): Promise<OpenResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => {
    controller.abort(new RequestTimeoutError(url, timeoutMs));
  }, timeoutMs);
  const onAbort = (): void => controller.abort(signal?.reason);
  if (signal?.aborted === true) onAbort();
  signal?.addEventListener("abort", onAbort, { once: true });
  const release = (): void => {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onAbort);
  };
  const surface = (error: unknown): unknown =>
    controller.signal.reason instanceof RequestTimeoutError ? controller.signal.reason : error;
  try {
    const response = await fetch(url, { signal: controller.signal });
    if (response.status === 404) throw new NotFoundError(url);
    if (!response.ok) throw new HttpError(url, response.status);
    if ((response.headers.get("content-type") ?? "").includes("text/html")) {
      throw new NotFoundError(url);
    }
    const read = async <T>(reader: (body: Response) => Promise<T>): Promise<T> => {
      try {
        return await reader(response);
      } catch (error) {
        throw surface(error);
      } finally {
        release();
      }
    };
    return { response, read };
  } catch (error) {
    release();
    throw surface(error);
  }
}

/** For callers that parse the body themselves: they must go through `read`. */
export async function fetchChecked(
  url: string,
  signal?: AbortSignal,
  timeoutMs: number = JSON_TIMEOUT_MS,
): Promise<OpenResponse> {
  return open(url, signal, timeoutMs);
}

/** Fetches JSON and validates it at the boundary. */
export async function fetchJson<T>(
  url: string,
  schema: ZodType<T>,
  signal?: AbortSignal,
): Promise<T> {
  const opened = await open(url, signal, JSON_TIMEOUT_MS);
  const body: unknown = await opened.read((response) => response.json());
  const parsed = schema.safeParse(body);
  if (!parsed.success) {
    throw new Error(`${url} is not valid: ${parsed.error.message}`);
  }
  return parsed.data;
}

export async function fetchBuffer(url: string, signal?: AbortSignal): Promise<ArrayBuffer> {
  const opened = await open(url, signal, BINARY_TIMEOUT_MS);
  return opened.read((response) => response.arrayBuffer());
}
