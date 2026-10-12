#!/usr/bin/env node
// Publish the private preview to Cloudflare Pages (ADR 0012).
// Usage: node scripts/deploy-preview.mjs [--yes] [--allow-dirty]
//   Without --yes it verifies, builds and checks the limits, prints the deploy command and stops.
// Environment:
//   PENYAL_PAGES_PROJECT  Pages project name (default "penyal-ifac-3d")
//   PENYAL_PAGES_BRANCH   branch the deployment is filed under (default "preview"; never the
//                         project's production branch, so the Access policy for previews applies)
// Authentication is wrangler's own (`pnpm exec wrangler login`); this script never reads credentials.
import { spawnSync } from "node:child_process";
import { existsSync, lstatSync, readdirSync, readFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const distDir = join(repoRoot, "app", "dist");

// https://developers.cloudflare.com/pages/platform/limits/ (Free plan, checked 2026-10-12)
export const LIMITS = {
  maxFiles: 20_000,
  maxFileBytes: 25 * 1024 * 1024,
  maxHeaderRules: 100,
  maxHeaderLineChars: 2_000,
};

const PRODUCTION_BRANCHES = ["main", "master", "trunk"];

class DeployError extends Error {}

function listFiles(dir) {
  const files = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) files.push(...listFiles(path));
    else files.push(path);
  }
  return files;
}

/** Checks the built directory against the Pages limits; returns stats or throws with the cause. */
export function checkDist(dir, limits = LIMITS) {
  if (!existsSync(join(dir, "index.html"))) {
    throw new DeployError(`${dir} has no index.html: the build did not produce a site.`);
  }
  const files = listFiles(dir);
  const problems = [];
  let totalBytes = 0;
  let largest = { path: "", bytes: 0 };
  for (const path of files) {
    const stat = lstatSync(path);
    if (stat.isSymbolicLink()) problems.push(`symlink in dist: ${relative(dir, path)}`);
    totalBytes += stat.size;
    if (stat.size > largest.bytes) largest = { path: relative(dir, path), bytes: stat.size };
    if (stat.size > limits.maxFileBytes) {
      problems.push(
        `${relative(dir, path)} is ${mib(stat.size)} MiB; Pages allows ${mib(limits.maxFileBytes)} MiB per file. Shrink or split it.`,
      );
    }
  }
  if (files.length > limits.maxFiles) {
    problems.push(
      `${files.length} files; Pages (Free) allows ${limits.maxFiles}. Merge or drop assets.`,
    );
  }
  for (const required of ["_headers", "robots.txt"]) {
    if (!existsSync(join(dir, required)))
      problems.push(`dist/${required} is missing (it comes from app/public/).`);
  }
  const headersPath = join(dir, "_headers");
  if (existsSync(headersPath)) {
    const lines = readFileSync(headersPath, "utf8").split("\n");
    const rules = lines.filter((l) => l.trim() && !l.startsWith("#") && !/^\s/.test(l)).length;
    if (rules > limits.maxHeaderRules)
      problems.push(`_headers has ${rules} rules; the limit is ${limits.maxHeaderRules}.`);
    const long = lines.findIndex((l) => l.length > limits.maxHeaderLineChars);
    if (long >= 0)
      problems.push(
        `_headers line ${long + 1} is longer than ${limits.maxHeaderLineChars} characters.`,
      );
  }
  if (problems.length > 0) {
    throw new DeployError(`dist does not fit Cloudflare Pages:\n  - ${problems.join("\n  - ")}`);
  }
  return { fileCount: files.length, totalBytes, largest };
}

/** The production bundle must not carry the Playwright hooks (app/src/core/testHooks.ts). */
export function assertNoTestHooks(dir) {
  const offenders = listFiles(join(dir, "bundle"))
    .filter((p) => p.endsWith(".js"))
    .filter((p) => readFileSync(p, "utf8").includes("__appState"));
  if (offenders.length > 0) {
    throw new DeployError(
      `test hooks (__appState) found in ${offenders.map((p) => relative(dir, p)).join(", ")}: the build was made with VITE_E2E=true. Rebuild without it.`,
    );
  }
}

function mib(bytes) {
  return (bytes / 1024 / 1024).toFixed(2);
}

function run(label, command, args, env = process.env) {
  console.log(`\n> ${label}: ${[command, ...args].join(" ")}`);
  const result = spawnSync(command, args, { cwd: repoRoot, stdio: "inherit", env });
  if (result.status !== 0) {
    throw new DeployError(
      `${label} failed (exit ${result.status ?? result.signal}). Nothing was deployed.`,
    );
  }
}

function capture(command, args) {
  const result = spawnSync(command, args, { cwd: repoRoot, encoding: "utf8" });
  return result.status === 0 ? result.stdout.trim() : "";
}

function main(argv) {
  const yes = argv.includes("--yes");
  const allowDirty = argv.includes("--allow-dirty");
  const project = process.env.PENYAL_PAGES_PROJECT || "penyal-ifac-3d";
  const branch = process.env.PENYAL_PAGES_BRANCH || "preview";

  if (PRODUCTION_BRANCHES.includes(branch)) {
    throw new DeployError(
      `PENYAL_PAGES_BRANCH=${branch} would publish to production. The private preview always goes to a non-production branch (default "preview").`,
    );
  }
  const commit = capture("git", ["rev-parse", "HEAD"]);
  const dirty = capture("git", ["status", "--porcelain"]) !== "";
  if (dirty && !allowDirty) {
    throw new DeployError(
      "the working tree has uncommitted changes; commit them or pass --allow-dirty.",
    );
  }

  // The plain production build: VITE_E2E must not leak in from the shell.
  const buildEnv = { ...process.env, WRANGLER_SEND_METRICS: "false" };
  delete buildEnv.VITE_E2E;

  run("verify generated assets", "uv", [
    "run",
    "--project",
    "pipeline",
    "penyal",
    "verify-generated",
  ]);
  run("build", "pnpm", ["--filter", "@penyal/app", "build"], buildEnv);
  assertNoTestHooks(distDir);
  const stats = checkDist(distDir);

  const message = capture("git", ["log", "-1", "--pretty=%s"]);
  const deployArgs = [
    "exec",
    "wrangler",
    "pages",
    "deploy",
    distDir,
    "--project-name",
    project,
    "--branch",
    branch,
    "--commit-hash",
    commit,
    "--commit-message",
    message,
    ...(dirty ? ["--commit-dirty", "true"] : []),
  ];

  console.log("\nPlan");
  console.log(`  project : ${project}`);
  console.log(`  branch  : ${branch}  (preview URL: https://${branch}.${project}.pages.dev)`);
  console.log(`  commit  : ${commit.slice(0, 12)}${dirty ? " (dirty)" : ""}`);
  console.log(
    `  dist    : ${stats.fileCount} files, ${mib(stats.totalBytes)} MiB, largest ${stats.largest.path} (${mib(stats.largest.bytes)} MiB)`,
  );
  console.log(`  command : pnpm ${deployArgs.join(" ")}`);
  if (!yes) {
    console.log("\nDry run: nothing was deployed. Pass --yes to deploy.");
    return;
  }
  run("deploy", "pnpm", deployArgs, buildEnv);
}

if (process.argv[1] && import.meta.url === new URL(`file://${process.argv[1]}`).href) {
  try {
    main(process.argv.slice(2));
  } catch (error) {
    if (!(error instanceof DeployError)) throw error;
    console.error(`deploy-preview: ${error.message}`);
    process.exit(1);
  }
}
