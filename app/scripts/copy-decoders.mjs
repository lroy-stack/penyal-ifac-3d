import { copyFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const appRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(join(appRoot, "package.json"));
const threeRoot = join(dirname(require.resolve("three")), "..");
const sourceDir = join(threeRoot, "examples", "jsm", "libs", "basis");
const targetDir = join(appRoot, "public", "decoders", "basis");

mkdirSync(targetDir, { recursive: true });
for (const file of ["basis_transcoder.js", "basis_transcoder.wasm"]) {
  copyFileSync(join(sourceDir, file), join(targetDir, file));
}
console.log(`copy-decoders: basis transcoder -> ${targetDir}`);
