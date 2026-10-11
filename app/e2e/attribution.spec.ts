import { expect, test } from "@playwright/test";
import { waitForApp } from "./support/frames";

// The attribution line is static HTML and the dialog is wired before the data loads, so these
// checks do not need the generated terrain.

test("shows the licence attribution on screen and clear of the touch controls", async ({
  browser,
}, info) => {
  const context = await browser.newContext({
    viewport: { width: 390, height: 780 },
    hasTouch: true,
    isMobile: true,
  });
  const page = await context.newPage();
  await page.goto("/?start=turnstile");

  const line = page.locator("#attribution");
  await expect(line).toBeVisible();
  for (const text of [
    "Institut Cartogràfic Valencià (CC BY 4.0)",
    "PNOA-LiDAR (CC BY 4.0 scne.es)",
    "OpenStreetMap (ODbL)",
    "Poly Haven (CC0)",
  ]) {
    await expect(line).toContainText(text);
  }
  await expect(page.getByRole("button", { name: "Créditos" })).toBeVisible();

  const colour = await line.evaluate((node) => {
    const style = getComputedStyle(node);
    return { color: style.color, background: style.backgroundColor, size: style.fontSize };
  });
  expect(colour.color).toBe("rgb(255, 255, 255)");
  expect(colour.background).toMatch(/^rgba\(0, 0, 0, 0\.[5-9]/);
  expect(Number.parseFloat(colour.size)).toBeGreaterThanOrEqual(12);

  const touchButton = page.locator('[data-action="toggle-camera"]');
  await expect(touchButton).toBeVisible();
  const [attribution, camera] = await Promise.all([line.boundingBox(), touchButton.boundingBox()]);
  if (attribution === null || camera === null) throw new Error("no bounding boxes");
  expect(attribution.x + attribution.width).toBeLessThanOrEqual(camera.x);
  expect(attribution.y + attribution.height).toBeLessThanOrEqual(780);
  await page.screenshot({ path: info.outputPath("attribution-mobile.png") });
  await context.close();
});

test("opens the credits dialog with the keyboard and closes it with Escape", async ({
  page,
}, info) => {
  await page.goto("/?start=turnstile");
  const opener = page.getByRole("button", { name: "Créditos" });
  await expect(opener).toBeVisible();

  await page.keyboard.press("Tab");
  await expect(opener).toBeFocused();
  await page.keyboard.press("Enter");

  const dialog = page.getByRole("dialog", { name: "Créditos y licencias" });
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("CC BY 4.0");
  await expect(dialog).toContainText("ODbL 1.0");
  await expect(dialog).toContainText("CC0 1.0");
  await expect(dialog).toContainText("Tunnel cross-section");
  await expect(dialog).toContainText("Seabed");
  await expect(dialog).toContainText("Limestone stand-in");
  await expect(dialog).toContainText("three.js");
  await expect(dialog.getByRole("link", { name: "CC BY 4.0" }).first()).toHaveAttribute(
    "href",
    "https://creativecommons.org/licenses/by/4.0/",
  );
  await expect(dialog.getByRole("button", { name: "Cerrar" })).toBeFocused();
  await page.screenshot({ path: info.outputPath("credits-dialog.png") });

  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(opener).toBeFocused();
});

test("the walker ignores the keyboard while the dialog is open", async ({ page }) => {
  await page.goto("/?start=turnstile");
  await waitForApp(page);
  await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog")).toBeVisible();
  const before = await page.evaluate(() => window.__appState?.player);

  await page.keyboard.down("KeyW");
  await page.waitForTimeout(800);
  await page.keyboard.up("KeyW");

  const after = await page.evaluate(() => window.__appState?.player);
  expect(after?.x).toBeCloseTo(before?.x ?? Number.NaN, 3);
  expect(after?.z).toBeCloseTo(before?.z ?? Number.NaN, 3);
});
