#!/usr/bin/env node
// Convert the Poly Haven CC0 material maps in data/raw/ to KTX2 for the terrain detail layer.
// Usage: node scripts/make-material-textures.mjs [--out-dir <dir>]
// Output: <out-dir>/<material>_<map>_<1k|2k>.ktx2 and <out-dir>/manifest.json
//   (default out-dir: app/public/assets/generated/materials)
//   manifest.json records, per texture, the Poly Haven input (id + sha256 from
//   data/manifest.lock.json), the exact `ktx create` arguments, the output bytes and sha256;
//   at the top level the union of the inputs and the tool versions (checked by
//   `penyal verify-generated`).
//   diff (sRGB colour) and arm (linear AO/roughness/metalness): ETC1S / BasisLZ.
//   nor-gl (linear normals, OpenGL +Y): UASTC with Zstandard, which keeps normals accurate.
// All have a full mip chain. `ktx` comes from tools/bin (see tools/README.md).
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const ktx = join(repoRoot, "tools", "bin", "ktx");
const USAGE = "Usage: node scripts/make-material-textures.mjs [--out-dir <dir>]";

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

function parseOutDir(argv) {
  let outDir = join(repoRoot, "app", "public", "assets", "generated", "materials");
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--out-dir") {
      if (argv[i + 1] === undefined) fail(`--out-dir needs a value\n${USAGE}`);
      outDir = resolve(argv[i + 1]);
      i += 1;
    } else if (arg.startsWith("--out-dir=")) {
      outDir = resolve(arg.slice("--out-dir=".length));
    } else {
      fail(`unknown argument ${arg}\n${USAGE}`);
    }
  }
  return outDir;
}

const sha256 = (path) => createHash("sha256").update(readFileSync(path)).digest("hex");

function lockedInput(lock, id, input) {
  const entry = lock.sources[id];
  const name = input.slice(input.lastIndexOf("/") + 1);
  const file = entry?.files.find((candidate) => candidate.name === name);
  if (file === undefined) fail(`${id} (${name}) is not in data/manifest.lock.json.`);
  return { id, file: relative(repoRoot, input).split("\\").join("/"), sha256: file.sha256 };
}

function toolVersion(command, args) {
  const run = spawnSync(command, args, { encoding: "utf8" });
  const line = (run.stdout || run.stderr || "").trim().split("\n")[0] ?? "";
  if (run.error !== undefined || run.status !== 0 || line === "") {
    fail(`cannot read the version of ${command}.`);
  }
  return line.split(/\s+/).at(-1).replace(/^v/, "");
}

const outDir = parseOutDir(process.argv.slice(2));
if (!existsSync(ktx)) fail(`${ktx} not found; run tools/install-ktx.sh (see tools/README.md).`);
mkdirSync(outDir, { recursive: true });
const lock = JSON.parse(readFileSync(join(repoRoot, "data", "manifest.lock.json"), "utf8"));
const tools = {
  ktx: toolVersion(ktx, ["--version"]),
  node: toolVersion(process.execPath, ["--version"]),
};

let total = 0;
const rows = [];
const files = [];
const inputs = [];
for (const material of MATERIALS) {
  for (const size of SIZES) {
    for (const [dirId, [suffix, args]] of Object.entries(MAPS)) {
      const name = `${material}_${suffix}_${size}`;
      const sourceId = `polyhaven-${material.replace(/_/g, "-")}-${dirId}-${size}`;
      const input = join(repoRoot, "data", "raw", sourceId, `${name}.jpg`);
      if (!existsSync(input)) fail(`missing ${input}; run \`penyal fetch --phase 2\`.`);
      const output = join(outDir, `${name}.ktx2`);
      const ktxArgs = ["create", ...args, "--generate-mipmap"];
      const result = spawnSync(ktx, [...ktxArgs, input, output], {
        stdio: ["ignore", "inherit", "inherit"],
      });
      if (result.status !== 0) fail(`ktx create failed for ${name} (exit ${result.status}).`);
      const bytes = statSync(output).size;
      total += bytes;
      const source = lockedInput(lock, sourceId, input);
      inputs.push(source);
      files.push({
        name: `${name}.ktx2`,
        inputs: [source],
        ktxArgs,
        bytes,
        sha256: sha256(output),
      });
      rows.push(`${name}.ktx2  ${(bytes / 1024).toFixed(0)} KiB`);
    }
  }
}
writeFileSync(
  join(outDir, "manifest.json"),
  `${JSON.stringify({ version: 1, inputs, tools, files }, null, 2)}\n`,
);
console.log(rows.join("\n"));
console.log(`total ${(total / 1024 / 1024).toFixed(2)} MiB in ${outDir}`);
