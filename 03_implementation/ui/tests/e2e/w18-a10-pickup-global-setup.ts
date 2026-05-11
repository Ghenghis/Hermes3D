/**
 * W18-A10 PICKUP — visual oracle globalSetup.
 *
 * Mirrors `Images-GUI/*.png` (the source of truth) into
 * `03_implementation/ui/tests/e2e/__refs_pickup__/Images-GUI/` so future
 * harness extensions can use `snapshotPathTemplate: "{arg}{ext}"` resolution
 * inside the test root. We NEVER write back to `Images-GUI/`. Mirror is
 * idempotent (size + mtime check) and prunes orphans whose source PNG was
 * deleted.
 *
 * No-recapture contract: setup never copies in the reverse direction. The
 * pickup config also sets `updateSnapshots: "none"`.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const UI_ROOT = path.resolve(HERE, "..", "..");
const REPO_ROOT = path.resolve(UI_ROOT, "..", "..");
const SRC = path.join(REPO_ROOT, "Images-GUI");
const DST = path.join(HERE, "__refs_pickup__", "Images-GUI");

type Entry = { src: string; dst: string; rel: string };

function* walk(root: string, rel = ""): Generator<Entry> {
  const here = rel ? path.join(root, rel) : root;
  let entries: fs.Dirent[];
  try {
    entries = fs.readdirSync(here, { withFileTypes: true });
  } catch {
    return;
  }
  for (const e of entries) {
    const childRel = rel ? path.join(rel, e.name) : e.name;
    if (e.isDirectory()) {
      yield* walk(root, childRel);
    } else if (e.isFile() && /\.png$/i.test(e.name)) {
      yield { src: path.join(root, childRel), dst: path.join(DST, childRel), rel: childRel };
    }
  }
}

function shouldCopy(src: string, dst: string): boolean {
  let dstStat: fs.Stats;
  try {
    dstStat = fs.statSync(dst);
  } catch {
    return true;
  }
  const srcStat = fs.statSync(src);
  if (srcStat.size !== dstStat.size) return true;
  return Math.abs(srcStat.mtimeMs - dstStat.mtimeMs) > 1_000;
}

async function globalSetup(): Promise<void> {
  if (!fs.existsSync(SRC)) {
    throw new Error(`[w18-a10-pickup globalSetup] Reference pack not found at ${SRC}`);
  }
  let copied = 0;
  let skipped = 0;
  const expected = new Set<string>();
  for (const entry of walk(SRC)) {
    expected.add(entry.dst);
    if (!shouldCopy(entry.src, entry.dst)) {
      skipped++;
      continue;
    }
    fs.mkdirSync(path.dirname(entry.dst), { recursive: true });
    fs.copyFileSync(entry.src, entry.dst);
    const st = fs.statSync(entry.src);
    fs.utimesSync(entry.dst, st.atime, st.mtime);
    copied++;
  }
  let pruned = 0;
  if (fs.existsSync(DST)) {
    const stack: string[] = [DST];
    while (stack.length) {
      const d = stack.pop()!;
      for (const e of fs.readdirSync(d, { withFileTypes: true })) {
        const p = path.join(d, e.name);
        if (e.isDirectory()) {
          stack.push(p);
        } else if (e.isFile() && /\.png$/i.test(e.name) && !expected.has(p)) {
          fs.unlinkSync(p);
          pruned++;
        }
      }
    }
  }
  // eslint-disable-next-line no-console
  console.log(
    `[w18-a10-pickup globalSetup] mirror Images-GUI: copied=${copied} skipped=${skipped} pruned=${pruned}`,
  );
}

export default globalSetup;
