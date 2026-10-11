/** The corridor message is not repeated within this time (ms), however long the player pushes. */
export const CORRIDOR_COOLDOWN_MS = 8000;
/** How long the corridor message stays on screen (ms). */
export const CORRIDOR_VISIBLE_MS = 4000;
/** First-time hints stay at most this long (ms); the first input removes them sooner. */
export const HINT_DURATION_MS = 3000;

/**
 * Decides when to say "stay on the trail" (ADR 0006): when the corridor limits the player's
 * motion and the message has not been shown during the last `CORRIDOR_COOLDOWN_MS`.
 */
export class CorridorNotice {
  private lastShown = Number.NEGATIVE_INFINITY;

  /** True when the message should be shown now. Call every frame. */
  update(corridorHit: boolean, nowMs: number): boolean {
    if (!corridorHit || nowMs - this.lastShown < CORRIDOR_COOLDOWN_MS) return false;
    this.lastShown = nowMs;
    return true;
  }
}
