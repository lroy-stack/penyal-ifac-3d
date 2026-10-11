import { z } from "zod";
import { fetchChecked, NotFoundError } from "../../core/http";

export const SUPPORTED_MANIFEST_VERSION = 1;

const boundsSchema = z
  .object({
    minX: z.number(),
    maxX: z.number(),
    minZ: z.number(),
    maxZ: z.number(),
    minY: z.number(),
    maxY: z.number(),
  })
  .refine((b) => b.minX < b.maxX && b.minZ < b.maxZ && b.minY <= b.maxY, {
    message: "bounds must have min < max on every axis",
  });

const lodSchema = z.object({
  /** 0 is the finest level. */
  level: z.number().int().min(0),
  /** Relative to the manifest URL. */
  url: z.string().min(1),
  /** Largest vertical deviation (m) from the reference surface; drives screen-space error. */
  maxError: z.number().positive(),
  texture: z.number().int().positive(),
  triangles: z.number().int().min(0),
  bytes: z.number().int().min(0),
});

const tileSchema = z
  .object({
    id: z.string().min(1),
    bounds: boundsSchema,
    lods: z.array(lodSchema).min(1),
  })
  .superRefine((tile, ctx) => {
    const levels = new Set(tile.lods.map((lod) => lod.level));
    if (levels.size !== tile.lods.length) {
      ctx.addIssue({ code: "custom", message: `tile ${tile.id} repeats an LOD level` });
    }
    const ordered = [...tile.lods].sort((a, b) => a.level - b.level);
    for (let i = 1; i < ordered.length; i++) {
      if (
        (ordered[i] as { maxError: number }).maxError <
        (ordered[i - 1] as { maxError: number }).maxError
      ) {
        ctx.addIssue({
          code: "custom",
          message: `tile ${tile.id}: coarser LODs must not have a smaller maxError`,
        });
      }
    }
  });

export const terrainManifestSchema = z.object({
  version: z.literal(SUPPORTED_MANIFEST_VERSION),
  frame: z.object({
    crs: z.string(),
    origin: z.object({ e: z.number(), n: z.number() }),
  }),
  source: z.record(z.string(), z.object({ id: z.string(), sha256: z.string() })).optional(),
  near: z.object({
    tileSize: z.number().positive(),
    tiles: z.array(tileSchema).min(1),
  }),
  far: z.object({
    url: z.string().min(1),
    maxError: z.number().positive(),
    texture: z.number().int().positive(),
    bounds: boundsSchema,
    triangles: z.number().int().min(0),
    bytes: z.number().int().min(0),
  }),
});

export type TerrainManifest = z.infer<typeof terrainManifestSchema>;
export type TerrainTile = TerrainManifest["near"]["tiles"][number];
export type TileLod = TerrainTile["lods"][number];
export type TileBounds = z.infer<typeof boundsSchema>;

/** Validates the manifest; an unknown `version` gets a message that says what to do. */
export function parseTerrainManifest(json: unknown): TerrainManifest {
  const version =
    typeof json === "object" && json !== null ? (json as { version?: unknown }).version : undefined;
  if (version !== SUPPORTED_MANIFEST_VERSION) {
    throw new Error(
      `Terrain manifest version ${JSON.stringify(version)} is not supported (this app reads version ` +
        `${SUPPORTED_MANIFEST_VERSION}). Rebuild the app or regenerate the terrain with a matching pipeline.`,
    );
  }
  const parsed = terrainManifestSchema.safeParse(json);
  if (!parsed.success) {
    throw new Error(`Terrain manifest is invalid: ${z.prettifyError(parsed.error)}`);
  }
  return parsed.data;
}

/** Resolves a manifest-relative URL. */
export function resolveAssetUrl(manifestUrl: string, relative: string): string {
  return new URL(relative, new URL(manifestUrl, "http://base.invalid/")).pathname;
}

export type ManifestResult =
  | { readonly status: "ready"; readonly manifest: TerrainManifest }
  | { readonly status: "missing" }
  | { readonly status: "error"; readonly message: string };

/** Never throws: a missing manifest means the terrain is not generated yet. */
export async function loadTerrainManifest(
  url: string,
  signal?: AbortSignal,
): Promise<ManifestResult> {
  try {
    const opened = await fetchChecked(url, signal);
    const json: unknown = await opened.read((response) => response.json());
    return { status: "ready", manifest: parseTerrainManifest(json) };
  } catch (error) {
    if (error instanceof NotFoundError) return { status: "missing" };
    if (signal?.aborted) throw error;
    return { status: "error", message: error instanceof Error ? error.message : String(error) };
  }
}
