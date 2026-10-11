#!/usr/bin/env node
// Optimise a GLB for the web: KTX2 textures (etc1s | uastc) then Meshopt geometry compression.
// Usage: node scripts/optimize.mjs <in.glb> <out.glb> [--textures etc1s|uastc|keep] [--quality 1-255]
// --quality only applies to etc1s (gltf-transform default 128; higher = larger and better).
import { spawnSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const gltfTransform = join(repoRoot, "node_modules", ".bin", "gltf-transform");
const toolsBin = join(repoRoot, "tools", "bin");
const TEXTURE_MODES = ["etc1s", "uastc", "keep"];
const USAGE =
  "Usage: node scripts/optimize.mjs <in.glb> <out.glb> [--textures etc1s|uastc|keep] [--quality 1-255]";

function fail(message) {
  console.error(`optimize: ${message}`);
  process.exit(1);
}

function parseArgs(argv) {
  const positional = [];
  let textures = "etc1s";
  let quality = null;
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--textures") {
      textures = argv[i + 1] ?? "";
      i += 1;
    } else if (arg.startsWith("--textures=")) {
      textures = arg.slice("--textures=".length);
    } else if (arg === "--quality") {
      quality = argv[i + 1] ?? "";
      i += 1;
    } else if (arg.startsWith("--quality=")) {
      quality = arg.slice("--quality=".length);
    } else if (arg.startsWith("--")) {
      fail(`unknown option ${arg}\n${USAGE}`);
    } else {
      positional.push(arg);
    }
  }
  if (positional.length !== 2) fail(USAGE);
  if (!TEXTURE_MODES.includes(textures)) {
    fail(`--textures must be one of ${TEXTURE_MODES.join(", ")} (got "${textures}")\n${USAGE}`);
  }
  if (quality !== null) {
    const level = Number(quality);
    if (!Number.isInteger(level) || level < 1 || level > 255) {
      fail(`--quality must be an integer from 1 to 255 (got "${quality}")\n${USAGE}`);
    }
    if (textures !== "etc1s") fail("--quality only applies to --textures etc1s");
    quality = String(level);
  }
  return { input: resolve(positional[0]), output: resolve(positional[1]), textures, quality };
}

function hasKtx(env) {
  const probe = spawnSync("ktx", ["--version"], { env, stdio: "ignore" });
  return probe.error === undefined && probe.status === 0;
}

function transform(args, env) {
  const run = spawnSync(gltfTransform, args, { env, stdio: "inherit" });
  if (run.error !== undefined)
    throw new Error(`could not run ${gltfTransform}: ${run.error.message}`);
  if (run.status !== 0) throw new Error(`gltf-transform ${args[0]} failed (exit ${run.status}).`);
}

const kib = (path) => `${(statSync(path).size / 1024).toFixed(1)} KiB`;

const { input, output, textures, quality } = parseArgs(process.argv.slice(2));
if (!existsSync(input)) fail(`input not found: ${input}`);
if (!existsSync(gltfTransform)) fail("gltf-transform is missing. Run `pnpm install`.");

const env = { ...process.env, PATH: `${toolsBin}${delimiter}${process.env.PATH ?? ""}` };
if (textures !== "keep" && !hasKtx(env)) {
  fail(
    `KTX-Software \`ktx\` was not found in ${toolsBin} or on PATH, and --textures ${textures} needs it. ` +
      "Install it into tools/bin (see tools/README.md), or pass --textures keep.",
  );
}

mkdirSync(dirname(output), { recursive: true });
let failure = null;
const workDir = mkdtempSync(join(tmpdir(), "penyal-optimize-"));
try {
  let current = input;
  if (textures !== "keep") {
    const compressed = join(workDir, "textures.glb");
    const options = quality === null ? [] : ["--quality", quality];
    transform([textures, current, compressed, ...options], env);
    current = compressed;
  }
  const packed = join(workDir, "meshopt.glb");
  transform(["meshopt", current, packed, "--level", "medium"], env);
  copyFileSync(packed, output);
} catch (error) {
  failure = error instanceof Error ? error.message : String(error);
} finally {
  rmSync(workDir, { recursive: true, force: true });
}
if (failure !== null) fail(failure);
console.log(
  `optimize: ${input} (${kib(input)}) -> ${output} (${kib(output)}), textures: ${textures}`,
);
