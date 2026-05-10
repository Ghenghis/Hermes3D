/**
 * W15-A9 cap 5 — DOM "no-fake" marker scanner.
 *
 * Greps the rendered page for tell-tale strings + attributes that indicate
 * fixture / mock data leaked into a production-mode screenshot. The W15-A5
 * gap analysis flagged this as the biggest false-positive risk: the harness
 * could pass a target whose UI is fully styled but whose data is fake — a
 * "looks-right" green that hides a regression.
 *
 * Markers checked (case-insensitive substring on innerText, exact match
 * on data-* attributes):
 *   - "mockData", "fakeData"
 *   - "lorem ipsum"
 *   - "placeholder" (text-only — `data-placeholder` attribute is allowed
 *      because it is a legitimate accessibility hook in input fields)
 *   - "__test_" (e2e-only prefix; never in production HTML)
 *   - data-mock="*"
 *   - data-fixture="*"
 *   - data-placeholder="true" (only this exact value is a marker; React
 *     leaves `data-placeholder` on aria-labelled inputs which is benign)
 *
 * The scanner returns the list of hits so the spec can attach them to the
 * reporter row and fail the test. It does NOT throw; the caller decides.
 *
 * No-fake / no-paid contract:
 *  - Scanner runs entirely in-page (Playwright evaluate); no network egress.
 *  - All markers are matched literally; no remote dictionary, no LLM.
 *
 * Sources cited:
 *  1. Playwright Page.evaluate reference:
 *     https://playwright.dev/docs/api/class-page#page-evaluate
 *  2. Chromatic / Percy visual-test pattern — "no fake content" gate is
 *     part of the recommended visual-oracle recipe:
 *     https://www.chromatic.com/docs/visual-tests/
 */
import type { Page } from "@playwright/test";

export interface NoFakeHit {
  /** Which marker matched. */
  marker: string;
  /** How it matched: "text" | "attribute". */
  kind: "text" | "attribute";
  /**
   * A short context snippet so the reporter has actionable evidence
   * (capped to 200 chars to keep the JSON readable).
   */
  snippet: string;
}

/**
 * Substring markers. innerText / outerHTML is lowercased before matching,
 * so values here are already lower-case. Anchored where ambiguity would
 * produce false positives (e.g. "placeholder" must be free-standing text
 * to avoid matching `data-placeholder` attributes, which we match below).
 */
const TEXT_MARKERS = [
  "mockdata",
  "fakedata",
  "lorem ipsum",
  "__test_",
];

/**
 * Word-boundary text marker. Matches the literal "placeholder" only when
 * it appears as visible page text (not as a substring of CSS class names
 * or attribute names like "data-placeholder").
 */
const PLACEHOLDER_WORD = /\bplaceholder\b/;

/**
 * Attribute-name markers — any element carrying these attributes is a hit
 * regardless of value, because they are e2e/test-only hooks.
 */
const ATTRIBUTE_MARKERS = ["data-mock", "data-fixture"];

/**
 * Exact-value attribute markers — only this attribute=value combo is a hit.
 */
const ATTRIBUTE_VALUE_MARKERS: { name: string; value: string }[] = [
  { name: "data-placeholder", value: "true" },
];

/**
 * Run the no-fake marker scan inside the page context.
 *
 * Returns the list of hits. An empty list means the page passed; one or
 * more entries means the test should fail.
 */
export async function scanForFakeMarkers(page: Page): Promise<NoFakeHit[]> {
  const result = await page.evaluate(
    ({ textMarkers, attrMarkers, attrValueMarkers, placeholderPattern }) => {
      const hits: { marker: string; kind: "text" | "attribute"; snippet: string }[] = [];
      const innerText = (document.body?.innerText ?? "").toLowerCase();

      for (const marker of textMarkers) {
        const at = innerText.indexOf(marker);
        if (at !== -1) {
          const start = Math.max(0, at - 40);
          const end = Math.min(innerText.length, at + marker.length + 40);
          hits.push({
            marker,
            kind: "text",
            snippet: innerText.slice(start, end),
          });
        }
      }

      const re = new RegExp(placeholderPattern, "i");
      const placeholderMatch = re.exec(innerText);
      if (placeholderMatch) {
        const idx = placeholderMatch.index;
        const start = Math.max(0, idx - 40);
        const end = Math.min(innerText.length, idx + placeholderMatch[0].length + 40);
        hits.push({
          marker: "placeholder",
          kind: "text",
          snippet: innerText.slice(start, end),
        });
      }

      for (const attr of attrMarkers) {
        const nodes = document.querySelectorAll(`[${attr}]`);
        nodes.forEach((node) => {
          hits.push({
            marker: attr,
            kind: "attribute",
            snippet: (node as Element).outerHTML.slice(0, 200),
          });
        });
      }

      for (const { name, value } of attrValueMarkers) {
        const nodes = document.querySelectorAll(`[${name}="${value}"]`);
        nodes.forEach((node) => {
          hits.push({
            marker: `${name}="${value}"`,
            kind: "attribute",
            snippet: (node as Element).outerHTML.slice(0, 200),
          });
        });
      }

      return hits;
    },
    {
      textMarkers: TEXT_MARKERS,
      attrMarkers: ATTRIBUTE_MARKERS,
      attrValueMarkers: ATTRIBUTE_VALUE_MARKERS,
      placeholderPattern: PLACEHOLDER_WORD.source,
    },
  );

  return result;
}

/**
 * Convenience helper: scan and format a stable, deduped summary string for
 * an annotation payload. Hits are sorted by (marker, kind) and capped at
 * 20 to keep the JSON manageable.
 */
export function summarizeFakeHits(hits: NoFakeHit[]): string {
  if (hits.length === 0) return "";
  const sorted = hits
    .slice()
    .sort((a, b) =>
      a.marker === b.marker
        ? a.kind.localeCompare(b.kind)
        : a.marker.localeCompare(b.marker),
    )
    .slice(0, 20);
  return sorted.map((h) => `${h.kind}:${h.marker}`).join(", ");
}
