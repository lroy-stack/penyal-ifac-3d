import type { QualityProfile } from "../../core/quality";
import type { DetailSet } from "./detailTextures";

/** `high` adds the detail shading to the tiles; `low` keeps the plain orthophoto. */
export type TerrainQuality = "high" | "low";

export type TerrainOptions = {
  readonly quality: TerrainQuality;
  /** Marble map set of the detail shading; `off` exactly when the quality is `low`. */
  readonly detailSet: DetailSet;
  /** Screen-space error budget (px). */
  readonly sseThreshold: number;
};

/** What the terrain streamer takes from the quality profile. Read once, at init. */
export function terrainOptions(profile: QualityProfile): TerrainOptions {
  const { detail, sseThresholdPx } = profile.terrain;
  return {
    quality: detail === "off" ? "low" : "high",
    detailSet: detail,
    sseThreshold: sseThresholdPx,
  };
}
