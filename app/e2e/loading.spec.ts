import { expect, type Page, test } from "@playwright/test";
import type { AppState } from "../src/appState";

async function readState(page: Page): Promise<AppState | undefined> {
  return page.evaluate(() => window.__appState);
}

test("shows a poster at once and walks only after the terrain is visible, fetching it before the collision field", async ({
  page,
}, info) => {
  const order: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url()).pathname;
    if (url.endsWith("terrain/far.glb")) order.push("far");
    else if (url.endsWith("terrain/collision.bin")) order.push("collision");
    else if (/terrain\/tiles\/.*_lod2\.glb$/.test(url)) order.push("coarse");
  });

  // Hold the far mesh back so the loading state can be observed.
  let releaseFar: () => void = () => undefined;
  const farHeld = new Promise<void>((resolve) => {
    releaseFar = resolve;
  });
  await page.route("**/terrain/far.glb", async (route) => {
    await farHeld;
    await route.continue();
  });

  await page.goto("/?start=turnstile", { waitUntil: "commit" });

  const poster = page.locator("#poster");
  await expect(poster).toBeVisible();
  await expect(poster.locator("h1")).toHaveText("Penyal d'Ifac 3D");
  // Assistive technology sees the title and the progress while loading, not an empty page.
  await expect(poster).not.toHaveAttribute("aria-hidden", /.*/);
  await expect(page.getByRole("heading", { level: 1, name: "Penyal d'Ifac 3D" })).toBeVisible();
  const progress = page.getByRole("progressbar", { name: "Progreso de la carga" });
  await expect(progress).toHaveAttribute("aria-valuemin", "0");
  await expect(progress).toHaveAttribute("aria-valuemax", "100");
  await expect(progress).toHaveAttribute("aria-valuenow", /^\d+$/);
  await expect(page.locator("#poster-message")).toHaveText("Cargando el terreno…", {
    timeout: 30_000,
  });
  await expect(page.locator("#status")).not.toBeEmpty();
  await page.screenshot({ path: info.outputPath("loading-poster.png") });

  // Coarse tiles are requested alongside the far mesh; the collision field waits for them.
  await expect.poll(() => order.includes("coarse")).toBe(true);
  await page.waitForTimeout(1500);
  expect(order).not.toContain("collision");
  const held = await readState(page);
  expect(held?.ready).toBe(false);
  expect(held?.frames).toBe(0);
  expect(held?.loading.terrainVisibleMs).toBeNull();
  await expect(poster).toBeVisible();

  releaseFar();
  await expect.poll(async () => (await readState(page))?.ready, { timeout: 60_000 }).toBe(true);

  const done = await readState(page);
  expect(done?.loading.terrainVisibleMs).not.toBeNull();
  expect(done?.loading.readyMs ?? 0).toBeGreaterThanOrEqual(done?.loading.terrainVisibleMs ?? 0);
  expect(done?.terrain.stats?.visible).toBe(true);
  expect(done?.terrain.stats?.farLoaded).toBe(true);
  expect(order.indexOf("far")).toBeLessThan(order.indexOf("collision"));
  expect(order.indexOf("coarse")).toBeLessThan(order.indexOf("collision"));
  await expect(poster).toBeHidden();
  await expect(page.locator("#status")).toHaveText("Listo. Ya puedes caminar.");
});

test("stops waiting and says so when the far mesh never loads", async ({ page }) => {
  await page.route("**/terrain/far.glb", (route) => route.fulfill({ status: 500, body: "" }));

  await page.goto("/?start=turnstile");

  await expect(page.locator("#poster-message")).toHaveText("El terreno no está disponible.", {
    timeout: 60_000,
  });
  const state = await readState(page);
  expect(state?.terrain.status).toBe("error");
  expect(state?.loading.terrainVisibleMs).toBeNull();

  // Once the walk starts, detail tiles keep arriving. They are not the far mesh coming back, so
  // the failure must stay reported and nothing may claim the terrain is loading again.
  await expect.poll(async () => (await readState(page))?.ready, { timeout: 60_000 }).toBe(true);
  const bytesAtWalk = (await readState(page))?.terrain.stats?.bytesLoaded ?? 0;
  await expect
    .poll(async () => (await readState(page))?.terrain.stats?.bytesLoaded ?? 0, { timeout: 60_000 })
    .toBeGreaterThan(bytesAtWalk);
  await page.waitForTimeout(1_000);
  const walking = await readState(page);
  expect(walking?.terrain.status).toBe("error");
  expect(walking?.loading.terrainVisibleMs).toBeNull();
  await expect(page.locator("#notice")).not.toContainText("Cargando");
  await expect(page.locator("#status")).not.toContainText("Cargando");
});

test("a failed collision field leaves only the fatal message on top, with no notice behind it", async ({
  page,
}) => {
  await page.route("**/terrain/collision.bin", (route) => route.fulfill({ status: 500, body: "" }));

  await page.goto("/?start=turnstile");

  const fatal = page.locator("#fatal");
  await expect(fatal).toHaveAttribute("data-visible", "true", { timeout: 60_000 });
  await expect(page.locator("#notice")).toHaveAttribute("data-visible", "false");
  const topmost = await page.evaluate(
    () => document.elementFromPoint(innerWidth / 2, innerHeight / 2)?.id,
  );
  expect(topmost).toBe("fatal");
});

test.describe("on a touch device", () => {
  test.use({ hasTouch: true, isMobile: true });

  test("the fatal screen covers the touch controls", async ({ page }) => {
    await page.goto("/?start=turnstile");
    await expect.poll(async () => (await readState(page))?.ready, { timeout: 60_000 }).toBe(true);
    const button = page.getByRole("button", { name: "Cambiar cámara" });
    await expect(button).toBeVisible();
    const box = await button.boundingBox();
    expect(box).not.toBeNull();

    await page.evaluate(() => {
      const fatal = document.getElementById("fatal");
      if (fatal !== null) fatal.dataset.visible = "true";
    });

    const topmost = await page.evaluate(({ x, y }) => document.elementFromPoint(x, y)?.id, {
      x: (box?.x ?? 0) + (box?.width ?? 0) / 2,
      y: (box?.y ?? 0) + (box?.height ?? 0) / 2,
    });
    expect(topmost).toBe("fatal");
  });
});
