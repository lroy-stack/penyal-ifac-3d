import { describe, expect, it } from "vitest";
import { CORRIDOR_COOLDOWN_MS, CorridorNotice } from "./notices";

describe("CorridorNotice", () => {
  it("shows the message when the player first hits the corridor edge", () => {
    const notice = new CorridorNotice();

    expect(notice.update(false, 0)).toBe(false);
    expect(notice.update(true, 1000)).toBe(true);
  });

  it("does not repeat it every frame while the player keeps pushing", () => {
    const notice = new CorridorNotice();
    notice.update(true, 1000);

    expect(notice.update(true, 1016)).toBe(false);
    expect(notice.update(true, 1000 + CORRIDOR_COOLDOWN_MS - 1)).toBe(false);
  });

  it("says it again after the cooldown if the player is still at the edge", () => {
    const notice = new CorridorNotice();
    notice.update(true, 1000);

    expect(notice.update(true, 1000 + CORRIDOR_COOLDOWN_MS)).toBe(true);
  });

  it("stays quiet for the cooldown even if the player steps away and back", () => {
    const notice = new CorridorNotice();
    notice.update(true, 1000);
    notice.update(false, 2000);

    expect(notice.update(true, 3000)).toBe(false);
    expect(notice.update(false, 4000)).toBe(false);
    expect(notice.update(true, 1000 + CORRIDOR_COOLDOWN_MS + 1)).toBe(true);
  });

  it("uses a cooldown of a few seconds, longer than the time the message stays", () => {
    expect(CORRIDOR_COOLDOWN_MS).toBeGreaterThanOrEqual(5000);
    expect(CORRIDOR_COOLDOWN_MS).toBeLessThanOrEqual(15_000);
  });
});
