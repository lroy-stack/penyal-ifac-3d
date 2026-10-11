import { expect, type Page, test } from "@playwright/test";
import type { AppState } from "../src/appState";
import { waitForApp } from "./support/frames";

/** Hints last 3 s of wall time: look at them as soon as the walk is enabled, not a few frames later. */
async function waitForWalkReady(page: Page): Promise<void> {
  await page.waitForFunction(() => window.__appState?.ready === true, undefined, {
    timeout: 90_000,
    polling: 50,
  });
}

async function readState(page: Page): Promise<AppState> {
  const state = await page.evaluate(() => window.__appState);
  if (state === undefined) throw new Error("window.__appState is not published.");
  return state;
}

test.describe("first-time hints", () => {
  test("show the controls for 3 s at most and disappear on the first key", async ({
    page,
  }, info) => {
    await page.goto("/?start=turnstile");
    await waitForWalkReady(page);
    const hints = page.locator("#hints");

    await expect(hints).toHaveAttribute("data-visible", "true");
    await expect(hints).toContainText("W A S D para andar");
    await expect(hints).toHaveAttribute("aria-live", "polite");
    await page.screenshot({ path: info.outputPath("hints.png") });

    await page.keyboard.press("ArrowLeft");
    await expect(hints).toHaveAttribute("data-visible", "false");
  });

  test("go away on their own after 3 s", async ({ page }) => {
    await page.goto("/?start=turnstile");
    await waitForWalkReady(page);
    const hints = page.locator("#hints");

    await expect(hints).toHaveAttribute("data-visible", "true");
    await expect(hints).toHaveAttribute("data-visible", "false", { timeout: 5000 });
  });

  test("do not fade when the visitor prefers reduced motion", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/?start=turnstile");
    await waitForWalkReady(page);

    const transition = await page
      .locator("#hints")
      .evaluate((node) => getComputedStyle(node).transitionDuration);
    expect(transition).toBe("0s");
  });

  test("describe touch gestures on a touch device", async ({ browser }) => {
    const context = await browser.newContext({
      viewport: { width: 390, height: 780 },
      hasTouch: true,
      isMobile: true,
    });
    const page = await context.newPage();
    await page.goto("/?start=turnstile");
    await waitForWalkReady(page);

    await expect(page.locator("#hints")).toContainText("Arrastra a la izquierda");
    await context.close();
  });
});

for (const viewport of [
  { width: 390, height: 780 },
  { width: 320, height: 568 },
]) {
  test(`the hints sit clear of the attribution and the camera button at ${viewport.width}x${viewport.height}`, async ({
    browser,
  }) => {
    const context = await browser.newContext({ viewport, hasTouch: true, isMobile: true });
    const page = await context.newPage();
    await page.goto("/?start=turnstile");
    await waitForWalkReady(page);
    await expect(page.locator("#hints")).toHaveAttribute("data-visible", "true");

    const hints = await page.locator("#hints").boundingBox();
    const attribution = await page.locator("#attribution").boundingBox();
    const camera = await page.locator('[data-action="toggle-camera"]').boundingBox();
    if (hints === null || attribution === null || camera === null) {
      throw new Error("The hints, the attribution and the camera button must all be laid out.");
    }
    const overlaps = (a: typeof hints, b: typeof hints): boolean =>
      a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
    expect(overlaps(hints, attribution), "hints overlap the attribution").toBe(false);
    expect(overlaps(hints, camera), "hints overlap the camera button").toBe(false);
    await context.close();
  });
}

test("the arrow keys turn the view in the real app", async ({ page }) => {
  await page.goto("/?start=turnstile");
  await waitForApp(page);
  const before = await readState(page);

  await page.keyboard.down("ArrowLeft");
  await expect
    .poll(async () => (await readState(page)).player.elapsed - before.player.elapsed, {
      timeout: 30_000,
    })
    .toBeGreaterThanOrEqual(0.7);
  await page.keyboard.up("ArrowLeft");

  const after = await readState(page);
  expect(after.player.yaw).toBeGreaterThan(before.player.yaw + 0.5);
  expect(
    Math.hypot(after.player.x - before.player.x, after.player.z - before.player.z),
  ).toBeLessThan(0.05);
  expect(await page.evaluate(() => document.pointerLockElement)).toBeNull();
});

test("tells the visitor, politely and not repeatedly, to stay on the trail", async ({ page }) => {
  await page.goto("/?start=turnstile&timescale=8");
  await waitForApp(page);
  const notice = page.locator("#notice");
  await expect(notice).toHaveAttribute("aria-live", "polite");
  await expect(notice).toHaveAttribute("role", "status");

  await page.keyboard.down("KeyA");
  await expect
    .poll(async () => (await readState(page)).player.corridorHit, { timeout: 60_000 })
    .toBe(true);
  await expect(notice).toHaveAttribute("data-visible", "true");
  await expect(notice).toHaveText("Por tu seguridad y la del parque, no salgas del sendero.");
  const shownAt = Date.now();

  // It goes away by itself while the visitor keeps pushing, and is not repeated within the cooldown.
  await expect(notice).toHaveAttribute("data-visible", "false", { timeout: 8000 });
  let pushedAgain = false;
  while (Date.now() - shownAt < 7000) {
    pushedAgain ||= (await readState(page)).player.corridorHit;
    await expect(notice).toHaveAttribute("data-visible", "false", { timeout: 1 });
    await page.waitForTimeout(250);
  }
  expect(pushedAgain).toBe(true);
  await page.keyboard.up("KeyA");
});
