#!/usr/bin/env node
/**
 * Downloads the Stockfish WASM engine into `public/stockfish/`.
 *
 * We deliberately do NOT add `stockfish` as an npm dependency: the published
 * package weighs ~240 MB because it embeds the full NNUE nets, while the only
 * builds usable in a browser are the two "lite" ones (~7 MB each). This script
 * pulls just those from the CDN and checks them against pinned hashes.
 *
 * Two builds are fetched:
 *   - lite-single : single-threaded, works everywhere.
 *   - lite        : multi-threaded, much stronger, but requires the page to be
 *                   cross-origin isolated (COOP/COEP headers, see vite.config).
 *
 * The runtime picks the multi-threaded build when `crossOriginIsolated` is true
 * and falls back to the single-threaded one otherwise.
 */
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const VERSION = "18.0.8";

/** Tried in order; some networks block one CDN but not the other. */
const MIRRORS = [
  `https://unpkg.com/stockfish@${VERSION}/bin`,
  `https://cdn.jsdelivr.net/npm/stockfish@${VERSION}/bin`,
];

/** sha256 of each file as published in stockfish@18.0.8. */
const FILES = {
  "stockfish-18-lite-single.js":
    "5243fd9b276cab7dfe3ad1d43ab9ead73568fac76468c614242977a210c4a391",
  "stockfish-18-lite-single.wasm":
    "a8fbc05ec6920b56d7485826dcb02c5ffd2826bcbf751cf973046f237a9096f1",
  "stockfish-18-lite.js":
    "6e64f417a642c2f2a27d33c09f069522366d1bc33ed7ee8712afcc347e109af4",
  "stockfish-18-lite.wasm":
    "d50136919dcd90e75eb8df78b255d47d618962b670028b38961343f6eb409174",
};

const outDir = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "public",
  "stockfish"
);

const sha256 = (buf) => createHash("sha256").update(buf).digest("hex");

async function alreadyValid(dest, expected) {
  try {
    return sha256(await readFile(dest)) === expected;
  } catch {
    return false;
  }
}

async function download(name) {
  const failures = [];
  for (const base of MIRRORS) {
    try {
      const res = await fetch(`${base}/${name}`);
      if (!res.ok) {
        failures.push(`${base}: HTTP ${res.status} ${res.statusText}`);
        continue;
      }
      return Buffer.from(await res.arrayBuffer());
    } catch (err) {
      failures.push(`${base}: ${err.message}`);
    }
  }
  throw new Error(`${name} could not be downloaded\n    ${failures.join("\n    ")}`);
}

async function fetchOne(name, expected) {
  const dest = path.join(outDir, name);
  if (await alreadyValid(dest, expected)) {
    console.log(`  ✓ ${name} (cached)`);
    return;
  }
  const buf = await download(name);
  const got = sha256(buf);
  if (got !== expected) {
    throw new Error(
      `${name}: checksum mismatch\n  expected ${expected}\n  got      ${got}`
    );
  }
  await writeFile(dest, buf);
  console.log(`  ✓ ${name} (${(buf.length / 1e6).toFixed(1)} MB)`);
}

async function main() {
  await mkdir(outDir, { recursive: true });
  console.log(`Fetching Stockfish ${VERSION} into public/stockfish/`);
  for (const [name, hash] of Object.entries(FILES)) {
    await fetchOne(name, hash);
  }
}

main().catch((err) => {
  console.error("\nFailed to fetch the Stockfish engine:");
  console.error(`  ${err.message}`);
  console.error(
    "\nThe app still runs; the analysis panel will just report the engine as unavailable."
  );
  console.error(`Retry later with: npm run engine:fetch\n`);
  // Do not fail `npm install` over an offline/blocked CDN.
  process.exit(0);
});
