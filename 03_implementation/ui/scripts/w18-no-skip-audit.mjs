#!/usr/bin/env node
/**
 * W18-A14-PICKUP — No-Skip Audit (CI gate)
 *
 * Scans every Playwright spec under `03_implementation/ui/tests/**\/*.spec.ts`
 * for skip tokens. Exits non-zero if any are found, so CI cannot pass while
 * the test corpus contains:
 *
 *   - `test.skip(`        — Playwright test-level skip
 *   - `test.fixme(`       — Playwright test-level fixme (functionally a skip)
 *   - `describe.skip(`    — suite-level skip
 *   - `describe.fixme(`   — suite-level fixme
 *   - `it.skip(`          — alias used in some Jest-style specs
 *   - `it.fixme(`         — alias used in some Jest-style specs
 *   - `test.skip.`        — chained variants (e.g. `test.skip.only`)
 *
 * Vitest unit-test specs under `tests/unit/**` are explicitly OUT OF SCOPE
 * (this is a Playwright-only audit). They use `.test.tsx`/`.test.ts` and
 * are excluded by the glob.
 *
 * Allow-list contract:
 *   - The script accepts the literal substring `@hardware-not-authorized`
 *     adjacent to a skip token only on the SAME LINE. This mirrors the
 *     reporter's allowance and lets future printer/camera/sensor lanes
 *     opt-in honestly.
 *   - There is NO `// w18-allow-skip` escape hatch. A skipped test is a fail.
 *
 * Exit codes:
 *   0  — zero forbidden skips found
 *   1  — at least one forbidden skip found (CI fails)
 *   2  — internal error (e.g. tests directory missing)
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const UI_ROOT = path.resolve(HERE, "..");
const TESTS_ROOT = path.join(UI_ROOT, "tests");

/** Patterns that must never appear in a spec without the hardware marker. */
const SKIP_PATTERNS = [
  /\btest\.skip\s*\(/,
  /\btest\.fixme\s*\(/,
  /\bdescribe\.skip\s*\(/,
  /\bdescribe\.fixme\s*\(/,
  /\bit\.skip\s*\(/,
  /\bit\.fixme\s*\(/,
  /\btest\.skip\./,
  /\btest\.fixme\./,
];

const ALLOW_MARKER = "@hardware-not-authorized";

/** Recursively collect .spec.ts files under root. */
function walk(root) {
  const out = [];
  if (!fs.existsSync(root)) {
    return out;
  }
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const full = path.join(root, entry.name);
    if (entry.isDirectory()) {
      // node_modules and test-results sanity guard.
      if (entry.name === "node_modules" || entry.name === "test-results") {
        continue;
      }
      out.push(...walk(full));
    } else if (entry.isFile() && /\.spec\.ts$/i.test(entry.name)) {
      out.push(full);
    }
  }
  return out;
}

function scanFile(file) {
  const text = fs.readFileSync(file, "utf-8");
  const lines = text.split(/\r?\n/);
  const hits = [];
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    // Skip pure-comment lines so docstring references like "this used to call
    // test.skip(...)" do not trip the audit. We treat as a comment any line
    // whose first non-whitespace characters are //, /*, or *.
    const trimmed = line.trimStart();
    if (
      trimmed.startsWith("//") ||
      trimmed.startsWith("/*") ||
      trimmed.startsWith("*")
    ) {
      continue;
    }
    for (const pat of SKIP_PATTERNS) {
      if (pat.test(line)) {
        // Hardware allow-list: same-line marker exempts.
        if (line.includes(ALLOW_MARKER)) {
          continue;
        }
        hits.push({
          file: path.relative(UI_ROOT, file).replace(/\\/g, "/"),
          line: i + 1,
          pattern: pat.source,
          text: line.trim(),
        });
        break;
      }
    }
  }
  return hits;
}

function main() {
  if (!fs.existsSync(TESTS_ROOT)) {
    console.error(`[W18-PICKUP][NO_SKIP_AUDIT] tests root missing: ${TESTS_ROOT}`);
    process.exit(2);
  }
  // Playwright specs live anywhere under tests/, but unit specs use .test.ts.
  // We rely on the .spec.ts suffix to exclude Vitest unit tests by convention.
  const files = walk(TESTS_ROOT);
  let totalHits = 0;
  const offenders = [];
  for (const file of files) {
    const hits = scanFile(file);
    if (hits.length > 0) {
      totalHits += hits.length;
      offenders.push(...hits);
    }
  }
  if (totalHits === 0) {
    console.log(
      `[W18-PICKUP][NO_SKIP_AUDIT] OK — scanned ${files.length} spec(s), 0 forbidden skips`,
    );
    process.exit(0);
  }
  console.error(
    `[W18-PICKUP][NO_SKIP_AUDIT] FAIL — ${totalHits} forbidden skip(s) across ${files.length} spec(s)`,
  );
  for (const o of offenders) {
    console.error(
      `  ${o.file}:${o.line}  /${o.pattern}/  ${o.text}`,
    );
  }
  console.error(
    "Resolution: convert the skip into a real assertion, delete the test, or " +
      "if (and ONLY if) the test depends on hardware the operator has not " +
      "authorized, add the literal marker `@hardware-not-authorized` on the " +
      "same line. A skipped test is a fail.",
  );
  process.exit(1);
}

main();
