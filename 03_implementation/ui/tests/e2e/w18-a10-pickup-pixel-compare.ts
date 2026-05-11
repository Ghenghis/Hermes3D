/**
 * W18-A10 PICKUP — pixel-comparator helper.
 *
 * Pickup-suffixed fork of the dead `w18-a10-pixel-compare.ts` so this branch
 * does not collide with the locks held by the dead `w18-a10` agent. Same
 * logic; standalone module. Wraps playwright-core's bundled `pixelmatch` +
 * `pngjs` (loaded via the workspace's own `playwright-core`) so the spec can
 * record an exact diff-pixel count for every target and emit a diff PNG when
 * the count is non-zero.
 *
 * Why not just `expect(buffer).toMatchSnapshot(...)`?
 *  - `toMatchSnapshot` swallows the exact pixel count on PASS — we get only
 *    a binary verdict.
 *  - The pickup contract requires per-target diffPixels + diff PNG for the
 *    fix-it loop. The reporter prints them in the verdict table.
 *
 * No-fake / no-paid contract:
 *  - Pure-Node, no network, no telemetry.
 *  - Never mutates the reference PNG. Only reads.
 *  - Never recaptures baselines.
 *
 * Sources cited:
 *  1. Mapbox pixelmatch — https://github.com/mapbox/pixelmatch
 *  2. pngjs sync API — https://github.com/lukeapage/pngjs
 *  3. Playwright bundles both under `playwright-core/lib/third_party/` and
 *     `playwright-core/lib/utilsBundle.js`.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const UI_ROOT = path.resolve(HERE, "..", "..");
const requireFromUi = createRequire(path.join(UI_ROOT, "package.json"));

interface PngImage {
  width: number;
  height: number;
  data: Buffer;
}

interface PngLib {
  sync: {
    read: (buf: Buffer) => PngImage;
    write: (img: PngImage) => Buffer;
  };
  new (opts: { width: number; height: number }): PngImage;
}

// Resolve the bundled CommonJS payloads through playwright-core's own
// internal resolver (which ignores the package's exports map for relative
// paths within the same package).
const PLAYWRIGHT_CORE_LIB = path.dirname(
  requireFromUi.resolve("playwright-core/lib/utilsBundle"),
);
const requireFromPlaywrightLib = createRequire(
  path.join(PLAYWRIGHT_CORE_LIB, "utilsBundle.js"),
);
const utilsBundle = requireFromPlaywrightLib("./utilsBundle") as { PNG: PngLib };
const pixelmatch = requireFromPlaywrightLib("./third_party/pixelmatch.js") as (
  expected: Buffer,
  actual: Buffer,
  diff: Buffer,
  width: number,
  height: number,
  options?: { threshold?: number; includeAA?: boolean },
) => number;
void requireFromUi;

const PNG = utilsBundle.PNG;

export interface PickupPixelCompareResult {
  /** Number of mismatched pixels reported by pixelmatch. */
  diffPixels: number;
  /** diffPixels / (compare_width * compare_height). */
  diffRatio: number;
  /** Expected (reference) image dimensions. */
  expected: { width: number; height: number };
  /** Observed (live) screenshot dimensions. */
  observed: { width: number; height: number };
  /** True when dimensions differ — both images are padded to max bounds. */
  sizeMismatch: boolean;
  /** Path the diff PNG was written to (only when diffPixels > 0). */
  diffPath?: string;
  /** Path the observed PNG was persisted to. */
  observedPath: string;
  /** Pixelmatch threshold (0..1). */
  threshold: number;
}

interface CompareOptions {
  threshold?: number;
  observedDir: string;
  diffDir: string;
  /** Stable name used for observed and diff PNGs (no extension). */
  artifactStem: string;
}

function padImageToSize(img: PngImage, width: number, height: number): PngImage {
  if (img.width === width && img.height === height) return img;
  const out = new PNG({ width, height });
  // Transparent fill: pixelmatch will flag padding bytes as a diff, giving
  // an honest "different shape" signal rather than masking it.
  for (let i = 0; i < out.data.length; i++) out.data[i] = 0;
  for (let y = 0; y < img.height; y++) {
    for (let x = 0; x < img.width; x++) {
      const srcIdx = (y * img.width + x) * 4;
      const dstIdx = (y * width + x) * 4;
      out.data[dstIdx] = img.data[srcIdx];
      out.data[dstIdx + 1] = img.data[srcIdx + 1];
      out.data[dstIdx + 2] = img.data[srcIdx + 2];
      out.data[dstIdx + 3] = img.data[srcIdx + 3];
    }
  }
  return out;
}

export function comparePickupPng(
  expectedBuf: Buffer,
  observedBuf: Buffer,
  opts: CompareOptions,
): PickupPixelCompareResult {
  const threshold = opts.threshold ?? 0.2;
  const expectedRaw = PNG.sync.read(expectedBuf);
  const observedRaw = PNG.sync.read(observedBuf);
  const sizeMismatch =
    expectedRaw.width !== observedRaw.width || expectedRaw.height !== observedRaw.height;
  const width = Math.max(expectedRaw.width, observedRaw.width);
  const height = Math.max(expectedRaw.height, observedRaw.height);
  const expected = sizeMismatch ? padImageToSize(expectedRaw, width, height) : expectedRaw;
  const observed = sizeMismatch ? padImageToSize(observedRaw, width, height) : observedRaw;

  const diff = new PNG({ width, height });
  const diffPixels = pixelmatch(
    expected.data,
    observed.data,
    diff.data,
    width,
    height,
    { threshold },
  );
  const diffRatio = diffPixels / (width * height);

  fs.mkdirSync(opts.observedDir, { recursive: true });
  const observedPath = path.join(opts.observedDir, `${opts.artifactStem}.observed.png`);
  fs.writeFileSync(observedPath, observedBuf);

  let diffPath: string | undefined;
  if (diffPixels > 0) {
    fs.mkdirSync(opts.diffDir, { recursive: true });
    diffPath = path.join(opts.diffDir, `${opts.artifactStem}.diff.png`);
    fs.writeFileSync(diffPath, PNG.sync.write(diff));
  }

  return {
    diffPixels,
    diffRatio,
    expected: { width: expectedRaw.width, height: expectedRaw.height },
    observed: { width: observedRaw.width, height: observedRaw.height },
    sizeMismatch,
    diffPath,
    observedPath,
    threshold,
  };
}

export function readPickupReference(refAbs: string): Buffer {
  return fs.readFileSync(refAbs);
}
