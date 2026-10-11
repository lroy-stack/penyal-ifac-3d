import { fetchBuffer, fetchJson } from "../core/http";
import { QuantizedHeightField, quantizedHeightFieldMetaSchema } from "./ground";

export const COLLISION_PATH = "assets/generated/terrain/collision";

/** Loads `<basePath>.json` + `<basePath>.bin` (the walkable-area height field). */
export async function loadCollisionField(
  basePath: string,
  signal?: AbortSignal,
): Promise<QuantizedHeightField> {
  const [meta, buffer] = await Promise.all([
    fetchJson(`${basePath}.json`, quantizedHeightFieldMetaSchema, signal),
    fetchBuffer(`${basePath}.bin`, signal),
  ]);
  return QuantizedHeightField.fromBuffer(meta, buffer);
}
