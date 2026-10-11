// Measures how long the production build takes to show a poster, show the terrain and let the
// visitor walk, under the network profiles used by Lighthouse. Not part of `pnpm e2e`: it is a
// measurement tool, run by hand.
//
//   node scripts/measure-load.mjs --build --profile fast4g --compress br
//   node scripts/measure-load.mjs --dist /path/to/dist --profile slow4g --runs 3
//
// --build        build this tree into a temp directory first (VITE_E2E=true publishes
//                window.__appState, which the marks below read; a plain production build does not)
// --dist <dir>   measure an existing build instead (for before/after comparisons)
// --profile      slow4g (150 ms RTT, 1.6 Mbps down) | fast4g (40 ms, 9 Mbps) | none
// --compress     none | gzip | br: the static server compresses html/js/json/wasm/css/bin with
//                zlib on the fly (glb and ktx2 are already compressed and are served as they are)
// --runs N       repeat and print every run plus the median (default 1)
// --viewport WxH default 412x915 at device scale factor 1
//
// Times are milliseconds since navigation start, in headless Chromium on SwiftShader, so the
// CPU-bound part (parsing, transcoding, software rendering) is slower than on a phone GPU.
import { execFileSync } from "node:child_process";
import { createReadStream, mkdtempSync, readFileSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { extname, join, normalize, resolve } from "node:path";
import { brotliCompressSync, constants, gzipSync } from "node:zlib";
import { chromium } from "@playwright/test";

const APP = resolve(import.meta.dirname, "..");

const PROFILES = {
  slow4g: { latency: 150, downloadThroughput: (1.6 * 1e6) / 8, uploadThroughput: (0.75 * 1e6) / 8 },
  fast4g: { latency: 40, downloadThroughput: (9 * 1e6) / 8, uploadThroughput: (9 * 1e6) / 8 },
  none: null,
};

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript",
  ".mjs": "text/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".wasm": "application/wasm",
  ".glb": "model/gltf-binary",
  ".ktx2": "image/ktx2",
  ".bin": "application/octet-stream",
  ".svg": "image/svg+xml",
};
const COMPRESSIBLE = new Set([".html", ".js", ".mjs", ".css", ".json", ".wasm", ".bin", ".svg"]);

function parseArgs(argv) {
  const args = { profile: "none", compress: "none", runs: 1, viewport: "412x915" };
  for (let i = 0; i < argv.length; i++) {
    const flag = argv[i];
    if (flag === "--build") args.build = true;
    else if (["--dist", "--profile", "--compress", "--runs", "--viewport"].includes(flag)) {
      args[flag.slice(2)] = argv[++i];
    } else throw new Error(`Unknown option ${flag}`);
  }
  args.runs = Number(args.runs);
  if (!(args.profile in PROFILES)) throw new Error(`Unknown profile ${args.profile}`);
  if (!["none", "gzip", "br"].includes(args.compress)) throw new Error("--compress: none|gzip|br");
  return args;
}

function buildInto(directory) {
  execFileSync("node", ["scripts/copy-decoders.mjs"], { cwd: APP, stdio: "inherit" });
  execFileSync("pnpm", ["exec", "vite", "build", "--outDir", directory, "--emptyOutDir"], {
    cwd: APP,
    stdio: "inherit",
    env: { ...process.env, VITE_E2E: "true" },
  });
}

function startServer(root, compress) {
  const cache = new Map();
  const served = { requests: 0, bytes: 0 };
  const server = createServer((request, response) => {
    const path = normalize(decodeURIComponent(new URL(request.url ?? "/", "http://x").pathname));
    let file = join(root, path.endsWith("/") ? `${path}index.html` : path);
    if (!file.startsWith(root)) {
      response.writeHead(403).end();
      return;
    }
    try {
      if (statSync(file).isDirectory()) file = join(file, "index.html");
      const extension = extname(file);
      const headers = { "content-type": TYPES[extension] ?? "application/octet-stream" };
      const wantsCompression = compress !== "none" && COMPRESSIBLE.has(extension);
      if (!wantsCompression) {
        headers["content-length"] = statSync(file).size;
        served.requests++;
        served.bytes += statSync(file).size;
        response.writeHead(200, headers);
        createReadStream(file).pipe(response);
        return;
      }
      const key = `${compress}:${file}`;
      if (!cache.has(key)) {
        const raw = readFileSync(file);
        cache.set(
          key,
          compress === "br"
            ? brotliCompressSync(raw, { params: { [constants.BROTLI_PARAM_QUALITY]: 5 } })
            : gzipSync(raw, { level: 6 }),
        );
      }
      const body = cache.get(key);
      headers["content-encoding"] = compress === "br" ? "br" : "gzip";
      headers["content-length"] = body.length;
      served.requests++;
      served.bytes += body.length;
      response.writeHead(200, headers);
      response.end(body);
    } catch {
      response.writeHead(404).end();
    }
  });
  return new Promise((done) =>
    server.listen(0, "127.0.0.1", () => done({ server, served, port: server.address().port })),
  );
}

/** Runs in the page: records the first time each condition holds. */
function installMarks() {
  const marks = {};
  window.__marks = marks;
  const mark = (name) => {
    if (marks[name] === undefined) marks[name] = Math.round(performance.now());
  };
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (entry.name === "first-contentful-paint") mark("fcp");
    }
  }).observe({ type: "paint", buffered: true });
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      marks.lcp = Math.round(entry.startTime);
      marks.lcpElement = entry.element ? entry.element.id || entry.element.tagName : null;
    }
  }).observe({ type: "largest-contentful-paint", buffered: true });
  setInterval(() => {
    const poster = document.getElementById("poster");
    if (poster && !poster.hidden && poster.textContent.trim() !== "") mark("poster");
    const state = window.__appState;
    if (!state) return;
    if (state.terrain?.stats?.farLoaded) mark("farLoaded");
    if (state.loading?.terrainVisibleMs != null) mark("terrainVisible");
    if (state.ready) mark("walk");
  }, 20);
}

async function measureOnce(url, profile, viewport) {
  const [width, height] = viewport.split("x").map(Number);
  const browser = await chromium.launch({
    channel: "chromium-headless-shell",
    args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
  });
  try {
    const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1 });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const client = await context.newCDPSession(page);
    await client.send("Network.enable");
    await client.send("Network.setCacheDisabled", { cacheDisabled: true });
    const conditions = PROFILES[profile];
    if (conditions !== null) {
      await client.send("Network.emulateNetworkConditions", { offline: false, ...conditions });
    }
    let bytes = 0;
    client.on("Network.loadingFinished", (event) => {
      bytes += event.encodedDataLength;
    });
    await page.addInitScript(installMarks);
    await page.goto(url, { waitUntil: "commit" });
    await page.waitForFunction(() => window.__marks?.walk !== undefined, undefined, {
      timeout: 120_000,
      polling: 100,
    });
    await page.waitForFunction(() => window.__marks?.farLoaded !== undefined, undefined, {
      timeout: 120_000,
      polling: 100,
    });
    const marks = await page.evaluate(() => ({ ...window.__marks }));
    return { ...marks, transferredMB: Number((bytes / 1e6).toFixed(2)), errors };
  } finally {
    await browser.close();
  }
}

const median = (values) => {
  const sorted = values.filter((v) => v !== undefined).sort((a, b) => a - b);
  return sorted.length === 0 ? null : sorted[Math.floor(sorted.length / 2)];
};

const args = parseArgs(process.argv.slice(2));
let dist = args.dist;
if (args.build) {
  dist = mkdtempSync(join(tmpdir(), "penyal-dist-"));
  buildInto(dist);
}
if (!dist) throw new Error("Pass --build or --dist <dir>.");
const { server, served, port } = await startServer(resolve(dist), args.compress);
const runs = [];
try {
  for (let i = 0; i < args.runs; i++) {
    runs.push(await measureOnce(`http://127.0.0.1:${port}/`, args.profile, args.viewport));
    console.log(
      JSON.stringify({ run: i + 1, profile: args.profile, compress: args.compress, ...runs[i] }),
    );
  }
} finally {
  server.close();
}
const summary = Object.fromEntries(
  ["fcp", "lcp", "poster", "terrainVisible", "farLoaded", "walk", "transferredMB"].map((k) => [
    k,
    median(runs.map((r) => r[k])),
  ]),
);
console.log(
  `median over ${runs.length} run(s): ${JSON.stringify({ profile: args.profile, compress: args.compress, ...summary })}`,
);
console.log(`server sent ${served.requests} responses, ${(served.bytes / 1e6).toFixed(2)} MB`);
