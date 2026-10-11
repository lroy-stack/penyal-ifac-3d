import { expect, type Page, test } from "@playwright/test";
import type { AssetStats } from "../dev/asset-viewer";

// Requires the spike assets: `pnpm spike` and the KTX2 variant
// (`node scripts/optimize.mjs build/spike/spike.glb app/public/assets/generated/spike/spike-ktx2.glb --textures etc1s`).

async function loadInViewer(page: Page, src: string): Promise<AssetStats | undefined> {
  await page.goto(`/dev/asset-viewer.html?src=${encodeURIComponent(src)}`);
  await expect
    .poll(async () => page.evaluate(() => window.__assetStats?.status), {
      timeout: 30_000,
    })
    .not.toBe("loading");
  return page.evaluate(() => window.__assetStats);
}

test("bpy spike with KTX2 (ETC1S) and meshopt renders through the app loaders", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  page.on("pageerror", (error) => {
    errors.push(`pageerror: ${error.message}`);
  });

  const stats = await loadInViewer(page, "/assets/generated/spike/spike-ktx2.glb");

  expect(stats?.error).toBeNull();
  expect(stats?.status).toBe("ready");
  expect(stats?.extensionsUsed).toEqual(
    expect.arrayContaining(["EXT_meshopt_compression", "KHR_texture_basisu"]),
  );
  expect(stats?.textures).toEqual([
    expect.objectContaining({ kind: "CompressedTexture", width: 512, height: 512 }),
  ]);
  expect(stats?.triangles).toBe(32_768);
  expect(errors).toEqual([]);
  await page.screenshot({ path: "test-results/spike-ktx2.png" });
});
