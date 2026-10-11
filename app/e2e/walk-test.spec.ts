import { expect, type Page, test } from "@playwright/test";

type WalkState = NonNullable<Window["__walkState"]>;

const WALK_SPEED = 1.4;

async function openCourse(page: Page, query = ""): Promise<WalkState> {
  await page.goto(`/dev/walk-test.html${query}`);
  await expect
    .poll(async () => page.evaluate(() => window.__walkState?.frames ?? 0), { timeout: 30_000 })
    .toBeGreaterThan(2);
  return readState(page);
}

async function readState(page: Page): Promise<WalkState> {
  const state = await page.evaluate(() => window.__walkState);
  if (state === undefined) throw new Error("window.__walkState is not published.");
  return state;
}

function horizontalDistance(from: WalkState, to: WalkState): number {
  return Math.hypot(to.x - from.x, to.z - from.z);
}

test.describe("keyboard and mouse", () => {
  test("holding W for 2 s walks about 2.8 m forward and stays grounded", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    page.on("pageerror", (error) => {
      errors.push(`pageerror: ${error.message}`);
    });
    const before = await openCourse(page);
    expect(before.cameraMode).toBe("first");

    await page.keyboard.down("KeyW");
    // The loop clamps each frame to 0.1 s, so on a slow renderer (SwiftShader) simulated time
    // runs behind the wall clock: wait for 2 s of simulated time, not 2 s of wall time.
    await expect
      .poll(async () => (await readState(page)).elapsed - before.elapsed, { timeout: 30_000 })
      .toBeGreaterThanOrEqual(2);
    await page.keyboard.up("KeyW");
    const after = await readState(page);

    expect(horizontalDistance(before, after)).toBeGreaterThan(2.8 - 0.4);
    // Polling may overshoot 2 s by a frame or two, so the upper bound follows simulated time.
    expect(horizontalDistance(before, after)).toBeLessThan(
      WALK_SPEED * (after.elapsed - before.elapsed) + 0.1,
    );
    expect(after.z).toBeLessThan(before.z);
    expect(after.grounded).toBe(true);
    // Speed against simulated time is independent of how fast SwiftShader renders frames.
    const speed = horizontalDistance(before, after) / (after.elapsed - before.elapsed);
    expect(speed).toBeCloseTo(WALK_SPEED, 1);
    expect(errors).toEqual([]);
  });

  test("C switches to third person and back", async ({ page }) => {
    await openCourse(page);
    await page.keyboard.press("KeyC");
    await expect.poll(async () => (await readState(page)).cameraMode).toBe("third");
    await page.keyboard.press("KeyC");
    await expect.poll(async () => (await readState(page)).cameraMode).toBe("first");
  });

  test("the 0.6 m wall stops the player while the 0.3 m steps do not", async ({ page }) => {
    await openCourse(page, "?z=-8");
    await page.keyboard.down("ShiftLeft");
    await page.keyboard.down("KeyW");
    await expect.poll(async () => (await readState(page)).z, { timeout: 20_000 }).toBeLessThan(-24);
    await page.waitForTimeout(1500);
    await page.keyboard.up("KeyW");
    await page.keyboard.up("ShiftLeft");
    const state = await readState(page);

    expect(state.z).toBeGreaterThan(-26);
    expect(state.grounded).toBe(true);
  });
});

test("walks through the tunnel floor under the rock", async ({ page }) => {
  await openCourse(page, "?z=-47");
  await page.keyboard.down("ShiftLeft");
  await page.keyboard.down("KeyW");
  await expect.poll(async () => (await readState(page)).z, { timeout: 20_000 }).toBeLessThan(-56);
  await page.keyboard.up("KeyW");
  await page.keyboard.up("ShiftLeft");
  const state = await readState(page);

  expect(state.grounded).toBe(true);
  expect(state.y).toBeCloseTo(2.4, 2);
});

test.describe("touch", () => {
  test.use({ viewport: { width: 412, height: 800 }, hasTouch: true, isMobile: true });

  test("dragging the left-half joystick walks forward and shows the camera button", async ({
    page,
  }) => {
    const before = await openCourse(page);
    await expect(page.getByRole("button", { name: "Cambiar cámara" })).toBeVisible();

    const client = await page.context().newCDPSession(page);
    const touch = (type: "touchStart" | "touchMove" | "touchEnd", y?: number) =>
      client.send("Input.dispatchTouchEvent", {
        type,
        touchPoints: y === undefined ? [] : [{ x: 100, y }],
      });
    await touch("touchStart", 600);
    await touch("touchMove", 540);
    await page.waitForTimeout(1500);
    await touch("touchEnd");
    const after = await readState(page);

    expect(horizontalDistance(before, after)).toBeGreaterThan(1);
    expect(after.z).toBeLessThan(before.z);
    expect(after.grounded).toBe(true);

    const stopped = await readState(page);
    await page.waitForTimeout(300);
    expect(horizontalDistance(stopped, await readState(page))).toBeLessThan(0.05);
  });

  test("the on-screen button toggles the camera", async ({ page }) => {
    await openCourse(page);
    await page.getByRole("button", { name: "Cambiar cámara" }).tap();
    await expect.poll(async () => (await readState(page)).cameraMode).toBe("third");
  });
});
