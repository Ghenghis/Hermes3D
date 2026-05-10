/**
 * W8-14 / W15-A9 Playwright globalSetup for the visual-oracle harness.
 *
 * Why this file exists
 * --------------------
 * W6-6 originally pointed `snapshotPathTemplate` at `Images-GUI/` which lives
 * two directories ABOVE the Playwright config dir (UI_ROOT). Playwright's
 * snapshot machinery refuses any output path that escapes the parent
 * directory of the test root with the error:
 *   "The outputPath is not allowed outside of the parent directory."
 * That safety check is documented as part of the snapshotPathTemplate
 * resolution rules and cannot be disabled (see source links below).
 *
 * Fix
 * ---
 * On every visual-proof run, mirror the repo's `Images-GUI/` reference pack
 * into `03_implementation/ui/tests/visual/__refs__/` (LOCAL to the test
 * root). The visual-proof spec then resolves snapshot paths to those local
 * copies, which keeps Playwright happy AND keeps the actual reference PNGs
 * as the source of truth (we only ever copy from Images-GUI/, never the
 * other way around).
 *
 * W15-A9 keeps this contract verbatim — the harness now also writes
 * region-suffixed snapshots (`<ref-stem>.<region>.png`) into the same
 * __refs__/ tree, but those are written by the spec on its FIRST run
 * (a no-op for return runs because updateSnapshots is "none"). global-setup
 * only owns the Images-GUI -> __refs__/ mirror.
 *
 * Idempotent + cheap: a per-file mtime + size check skips copies when the
 * destination is already current. First run does the full copy; subsequent
 * runs are effectively a no-op walk.
 *
 * No-fake / no-paid contract:
 *  - Copies ONLY from `Images-GUI/` -> `__refs__/`. Never the reverse.
 *  - Never deletes a Images-GUI/ reference; orphan __refs__/ files are
 *    pruned only if they no longer exist in `Images-GUI/`.
 *  - All-local; no network, no paid services.
 *
 * Sources cited (per W15-A9 contract):
 *  1. Playwright snapshotPathTemplate reference (parent-dir safety check):
 *     https://playwright.dev/docs/api/class-testconfig#test-config-snapshot-path-template
 *  2. Playwright globalSetup reference:
 *     https://playwright.dev/docs/test-global-setup-teardown
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const UI_ROOT = path.resolve(HERE, "..", "..");
const REPO_ROOT = path.resolve(UI_ROOT, "..", "..");
const SRC_REFS_ROOT = path.join(REPO_ROOT, "Images-GUI");
const DST_REFS_ROOT = path.join(HERE, "__refs__");

type FileEntry = { srcAbs: string; dstAbs: string; rel: string };

function* walkPng(srcRoot: string, rel: string = ""): Generator<FileEntry> {
  const here = rel ? path.join(srcRoot, rel) : srcRoot;
  let entries: fs.Dirent[];
  try {
    entries = fs.readdirSync(here, { withFileTypes: true });
  } catch {
    return;
  }
  for (const entry of entries) {
    const childRel = rel ? path.join(rel, entry.name) : entry.name;
    if (entry.isDirectory()) {
      yield* walkPng(srcRoot, childRel);
    } else if (entry.isFile() && /\.png$/i.test(entry.name)) {
      yield {
        srcAbs: path.join(srcRoot, childRel),
        dstAbs: path.join(DST_REFS_ROOT, childRel),
        rel: childRel,
      };
    }
  }
}

function shouldCopy(srcAbs: string, dstAbs: string): boolean {
  let dstStat: fs.Stats;
  try {
    dstStat = fs.statSync(dstAbs);
  } catch {
    return true;
  }
  const srcStat = fs.statSync(srcAbs);
  if (srcStat.size !== dstStat.size) return true;
  // mtime equality with a 1s tolerance to absorb FS rounding (NTFS vs ext4).
  return Math.abs(srcStat.mtimeMs - dstStat.mtimeMs) > 1_000;
}

function ensureDir(dir: string): void {
  fs.mkdirSync(dir, { recursive: true });
}

function syncRefs(): { copied: number; skipped: number; pruned: number; total: number } {
  if (!fs.existsSync(SRC_REFS_ROOT)) {
    throw new Error(
      `[visual-proof globalSetup] Reference pack not found at ${SRC_REFS_ROOT}. ` +
        `Cannot mirror references into ${DST_REFS_ROOT}. Verify Images-GUI/ exists at repo root.`,
    );
  }
  ensureDir(DST_REFS_ROOT);

  const present = new Set<string>();
  let copied = 0;
  let skipped = 0;
  let total = 0;
  for (const file of walkPng(SRC_REFS_ROOT)) {
    total += 1;
    present.add(file.rel.replace(/\\/g, "/"));
    if (shouldCopy(file.srcAbs, file.dstAbs)) {
      ensureDir(path.dirname(file.dstAbs));
      fs.copyFileSync(file.srcAbs, file.dstAbs);
      // Preserve mtime so subsequent runs hit the skip path.
      const srcStat = fs.statSync(file.srcAbs);
      fs.utimesSync(file.dstAbs, srcStat.atime, srcStat.mtime);
      copied += 1;
    } else {
      skipped += 1;
    }
  }

  // Prune orphan PNGs in __refs__/ that no longer have a Images-GUI/ source.
  // Empty directories are also removed bottom-up.
  let pruned = 0;
  for (const file of walkPng(DST_REFS_ROOT)) {
    const rel = path
      .relative(DST_REFS_ROOT, file.srcAbs)
      .replace(/\\/g, "/");
    if (!present.has(rel)) {
      try {
        fs.unlinkSync(file.srcAbs);
        pruned += 1;
      } catch {
        // ignore
      }
    }
  }

  return { copied, skipped, pruned, total };
}

export default async function globalSetup(): Promise<void> {
  const t0 = Date.now();
  const result = syncRefs();
  const ms = Date.now() - t0;
  process.stdout.write(
    `[visual-proof globalSetup] mirrored ${result.total} PNGs from Images-GUI/ to ` +
      `${path.relative(REPO_ROOT, DST_REFS_ROOT).replace(/\\/g, "/")}/ ` +
      `(copied=${result.copied} skipped=${result.skipped} pruned=${result.pruned}) in ${ms}ms\n`,
  );
}
