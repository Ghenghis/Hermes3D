/**
 * console-strict fixture: fails the test if the page emits any of:
 *   - a `pageerror` (uncaught JS exception)
 *   - a `console.error(...)` message
 *   - a `requestfailed` network event
 *   - an HTTP response with status >= 400 (excluding /favicon* + Gradio internal
 *     polling endpoints that legitimately 404 between Gradio versions)
 *
 * Rubric note: this is the BLOCKING gate. A spec that passes its own
 * assertions but logged a console error or fetched a 500 still fails.
 *
 * Excluded URL patterns are documented in README.md under "Known excluded
 * paths".
 */
import { test as base, expect } from '@playwright/test';

const EXCLUDED_URL_PATTERNS: RegExp[] = [
  /\/favicon/i,
  /\.well-known\//,
  // Gradio's optional manifest poll — harmless 404 across versions.
  /\/manifest\.json(\?|$)/,
  // Gradio reload heartbeat that intermittently 404s in dev (not in launcher).
  /\/gradio_api\/queue\/data/,
];

function isExcluded(url: string): boolean {
  return EXCLUDED_URL_PATTERNS.some((re) => re.test(url));
}

export const test = base.extend<{ strictPage: void }>({
  strictPage: [
    async ({ page }, use, testInfo) => {
      const errors: string[] = [];

      page.on('pageerror', (err) => {
        errors.push(`pageerror: ${err.message}`);
      });

      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          // Filter out CORS preflight noise from cross-origin probes Gradio makes;
          // genuine app errors still surface.
          const text = msg.text();
          if (/CORS|net::ERR_ABORTED/i.test(text) && isExcluded(msg.location().url)) {
            return;
          }
          errors.push(`console.error: ${text}`);
        }
      });

      page.on('requestfailed', (req) => {
        if (isExcluded(req.url())) return;
        const failure = req.failure();
        errors.push(`requestfailed: ${req.url()} (${failure?.errorText ?? 'unknown'})`);
      });

      page.on('response', (res) => {
        const status = res.status();
        if (status >= 400 && !isExcluded(res.url())) {
          errors.push(`http ${status}: ${res.url()}`);
        }
      });

      await use();

      if (errors.length > 0) {
        await testInfo.attach('strict-mode-errors.txt', {
          body: errors.join('\n'),
          contentType: 'text/plain',
        });
        // Fail the test with the captured errors.
        expect(errors, `console-strict gate tripped:\n${errors.join('\n')}`).toEqual([]);
      }
    },
    { auto: true },
  ],
});

export { expect };
