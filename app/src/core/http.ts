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

export async function fetchChecked(url: string, signal?: AbortSignal): Promise<Response> {
  const response = await fetch(url, signal === undefined ? {} : { signal });
  if (response.status === 404) throw new NotFoundError(url);
  if (!response.ok) throw new HttpError(url, response.status);
  if ((response.headers.get("content-type") ?? "").includes("text/html")) {
    throw new NotFoundError(url);
  }
  return response;
}

/** Fetches JSON and validates it at the boundary. */
export async function fetchJson<T>(
  url: string,
  schema: ZodType<T>,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetchChecked(url, signal);
  const parsed = schema.safeParse(await response.json());
  if (!parsed.success) {
    throw new Error(`${url} is not valid: ${parsed.error.message}`);
  }
  return parsed.data;
}

export async function fetchBuffer(url: string, signal?: AbortSignal): Promise<ArrayBuffer> {
  const response = await fetchChecked(url, signal);
  return response.arrayBuffer();
}
