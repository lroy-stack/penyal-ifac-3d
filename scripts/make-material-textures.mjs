#!/usr/bin/env node
// Convert the Poly Haven CC0 material maps in data/raw/ to KTX2 for the terrain detail layer.
// Usage: node scripts/make-material-textures.mjs
// Output: app/public/assets/generated/materials/<material>_<map>_<1k|2k>.ktx2
//   diff (sRGB colour) and arm (linear AO/roughness/metalness): ETC1S / BasisLZ.
//   nor-gl (linear normals, OpenGL +Y): UASTC with Zstandard, which keeps normals accurate.
// All have a full mip chain. `ktx` comes from tools/bin (see tools/README.md).
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const ktx = join(repoRoot, "tools", "bin", "ktx");
const outDir = join(repoRoot, "app", "public", "assets", "generated", "materials");

const MATERIALS = ["marble_cliff_05", "rocks_ground_05"];
const SIZES = ["1k", "2k"];
// map id in the directory name -> [file suffix, ktx create arguments]
const MAPS = {
  diff: [
    "diff",
    ["--format", "R8G8B8_SRGB", "--encode", "basis-lz", "--qlevel", "192", "--clevel", "4"],
  ],
  arm: [
    "arm",
    [
      "--format",
      "R8G8B8_UNORM",
      "--assign-tf",
      "linear",
      "--encode",
      "basis-lz",
      "--qlevel",
      "128",
      "--clevel",
      "3",
    ],
  ],
  "nor-gl": [
    "nor_gl",
    [
      "--format",
      "R8G8B8_UNORM",
      "--assign-tf",
      "linear",
      "--normalize",
      "--encode",
      "uastc",
      "--zstd",
      "19",
    ],
  ],
};

function fail(message) {
  console.error(`make-material-textures: ${message}`);
  process.exit(1);
}

if (!existsSync(ktx)) fail(`${ktx} not found; run tools/install-ktx.sh (see tools/README.md).`);
mkdirSync(outDir, { recursive: true });

let total = 0;
const rows = [];
for (const material of MATERIALS) {
  for (const size of SIZES) {
    for (const [dirId, [suffix, args]] of Object.entries(MAPS)) {
      const name = `${material}_${suffix}_${size}`;
      const input = join(
        repoRoot,
        "data",
        "raw",
        `polyhaven-${material.replace(/_/g, "-")}-${dirId}-${size}`,
        `${name}.jpg`,
      );
      if (!existsSync(input)) fail(`missing ${input}; run \`penyal fetch --phase 2\`.`);
      const output = join(outDir, `${name}.ktx2`);
      const result = spawnSync(ktx, ["create", ...args, "--generate-mipmap", input, output], {
        stdio: ["ignore", "inherit", "inherit"],
      });
      if (result.status !== 0) fail(`ktx create failed for ${name} (exit ${result.status}).`);
      const bytes = statSync(output).size;
      total += bytes;
      rows.push(`${name}.ktx2  ${(bytes / 1024).toFixed(0)} KiB`);
    }
  }
}
console.log(rows.join("\n"));
console.log(`total ${(total / 1024 / 1024).toFixed(2)} MiB in ${outDir}`);
