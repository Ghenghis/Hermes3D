/**
 * W18-A14 — No-Skip Test Harness reporter (canonical).
 *
 * Origin: The original `w18-a14` subagent died silently at 2026-05-11T10:37Z
 * before producing a PR. Its file locks expired at 12:07Z and were recovered
 * by `w18-a14-pickup`, which then claimed the canonical filenames and
 * landed this reporter under its original intended name.
 *
 * Contract (per W18-A14 no-skip mission, 2026-05-11):
 *   1. Any Playwright test whose final status is `skipped` MUST fail the run,
 *      unless that test is explicitly tagged or annotated as hardware-blocked.
 *   2. Hardware-blocked tests carry the marker `@hardware-not-authorized`
 *      (in `test.tags[]`, in any `annotations[].type` entry, or as the literal
 *      substring `@hardware-not-authorized` inside the test title). When that
 *      marker is present, the reporter emits a machine-readable line:
 *
 *          [W18][HARDWARE_NOT_AUTHORIZED] <test title>
 *
 *      and the run continues without penalty.
 *   3. Skipped tests without that marker emit a machine-readable failure line:
 *
 *          [W18][SKIPPED_PASS_FORBIDDEN] <test title>
 *
 *      The reporter forces the FullResult status to `failed` in `onEnd` so
 *      skipped runs cannot pass CI silently.
 *
 * Hard constraints from W18-A14:
 *   - Zero-config: no env-var toggles, no constructor options, no opt-out.
 *   - Deterministic: same inputs -> same outputs. We only inspect static
 *     metadata (`test.tags`, `test.annotations`, `result.annotations`) plus
 *     a literal scan of the test title for the marker. No reliance on test
 *     ordering, wall-clock, or shared state across runs.
 *   - No printer hardware writes — this reporter is pure metadata.
 *
 * Sources:
 *   - Playwright Reporter API (`onTestEnd`, `onEnd`, `FullResult.status`):
 *     https://playwright.dev/docs/api/class-reporter
 *   - Tag/annotation semantics:
 *     https://playwright.dev/docs/test-annotations#tag-tests
 */
import type {
  FullResult,
  Reporter,
  TestCase,
  TestResult,
} from "@playwright/test/reporter";

/**
 * Sole authorized marker that exempts a skipped test from failing the run.
 * The marker is recognized in four places:
 *   - `test.tags[]`               (e.g. `test("…", { tag: "@hardware-not-authorized" }, …)`)
 *   - `test.annotations[].type`   (static, set on the test definition)
 *   - `result.annotations[].type` (runtime, pushed inside the test body)
 *   - the literal title substring `@hardware-not-authorized`
 *
 * The bare form (without "@") is also recognized so annotation types can
 * follow the no-leading-symbol Playwright convention.
 */
const HARDWARE_MARKER = "@hardware-not-authorized";
const HARDWARE_MARKER_BARE = "hardware-not-authorized";

function hasHardwareMarker(test: TestCase, result: TestResult): boolean {
  if (test.tags?.some((tag) => tag === HARDWARE_MARKER)) {
    return true;
  }
  const staticHit = test.annotations?.some(
    (a) => a.type === HARDWARE_MARKER || a.type === HARDWARE_MARKER_BARE,
  );
  if (staticHit) {
    return true;
  }
  const runtimeHit = result.annotations?.some(
    (a) => a.type === HARDWARE_MARKER || a.type === HARDWARE_MARKER_BARE,
  );
  if (runtimeHit) {
    return true;
  }
  return test.title.includes(HARDWARE_MARKER);
}

/**
 * Build the fully-qualified path for a test (project > describe > … > test).
 * Used so machine-readable lines are unambiguous when the same title appears
 * in multiple files or projects.
 */
function fullTitle(test: TestCase): string {
  const segments = test.titlePath().filter((s) => s.length > 0);
  return segments.join(" > ");
}

export default class W18NoSkipReporter implements Reporter {
  private readonly forbiddenSkips: string[] = [];
  private readonly authorizedSkips: string[] = [];

  onTestEnd(test: TestCase, result: TestResult): void {
    if (result.status !== "skipped") {
      return;
    }
    const title = fullTitle(test);
    if (hasHardwareMarker(test, result)) {
      this.authorizedSkips.push(title);
      // Machine-readable line for CI tooling.
      // eslint-disable-next-line no-console
      console.log(`[W18][HARDWARE_NOT_AUTHORIZED] ${title}`);
      return;
    }
    this.forbiddenSkips.push(title);
    // Machine-readable line for CI tooling.
    // eslint-disable-next-line no-console
    console.error(`[W18][SKIPPED_PASS_FORBIDDEN] ${title}`);
  }

  async onEnd(
    result: FullResult,
  ): Promise<{ status?: FullResult["status"] } | undefined> {
    if (this.forbiddenSkips.length === 0) {
      if (this.authorizedSkips.length > 0) {
        // eslint-disable-next-line no-console
        console.log(
          `[W18][NO_SKIP_REPORT] forbidden_skips=0 authorized_hardware_skips=${this.authorizedSkips.length}`,
        );
      }
      return undefined;
    }
    // eslint-disable-next-line no-console
    console.error(
      `[W18][NO_SKIP_REPORT] forbidden_skips=${this.forbiddenSkips.length} authorized_hardware_skips=${this.authorizedSkips.length}`,
    );
    for (const title of this.forbiddenSkips) {
      // eslint-disable-next-line no-console
      console.error(`[W18][SKIPPED_PASS_FORBIDDEN] ${title}`);
    }
    // The contract says: "a skipped test is a fail". We can't throw out of
    // onTestEnd without aborting the rest of the run, so we mark the run
    // failed at onEnd via the documented return shape. If the run was
    // already failing for another reason, that status is preserved (no
    // downgrade of "failed" to "passed").
    if (result.status === "passed") {
      return { status: "failed" };
    }
    return undefined;
  }

  // The harness must produce output even when stdout is captured by another
  // reporter; printsToStdio=true keeps the list/html/json reporters informed
  // that this reporter writes to stdio (Playwright will not silently swallow
  // it).
  printsToStdio(): boolean {
    return true;
  }
}
