import { expect, test } from "@playwright/test";
import {
  TAB_FIXTURES,
  assertNoErrors,
  assertNoFakeVisibleText,
  attachErrorCapture,
  openTab,
} from "./_helpers";

test.beforeEach(async ({ page }) => {
  await attachErrorCapture(page);
});

test("Voice tab mounts and respects STT runtime gating", async ({ page }) => {
  await page.goto("/");
  await openTab(page, TAB_FIXTURES.voice);
  const root = page.getByTestId(TAB_FIXTURES.voice.rootTestId);
  await expect(root).toBeVisible();
  // Voice must never claim STT works when runtime is missing - assert no fake/placeholder phrases.
  await assertNoFakeVisibleText(page, TAB_FIXTURES.voice.rootTestId);
  await assertNoErrors(page);
});

test("Voice tab exposes URL-addressable subtabs (#voice/browser, /transcript-history, /proof-review)", async ({
  page,
}) => {
  await page.goto("/#voice/browser");
  await expect(page.getByTestId("voice-root")).toHaveAttribute("data-active-subtab", "browser");
  // Either the Web Speech API surface or the honest-unsupported banner must
  // render — we never accept a blank state.
  const browserSurfaces = page
    .getByTestId("voice-browser-subtab")
    .or(page.getByTestId("voice-browser-unsupported"));
  await expect(browserSurfaces.first()).toBeVisible();

  await page.goto("/#voice/transcript-history");
  await expect(page.getByTestId("voice-root")).toHaveAttribute(
    "data-active-subtab",
    "transcript-history",
  );
  await expect(page.getByTestId("voice-transcript-history-subtab")).toBeVisible();

  await page.goto("/#voice/proof-review");
  await expect(page.getByTestId("voice-root")).toHaveAttribute(
    "data-active-subtab",
    "proof-review",
  );
  await expect(page.getByTestId("voice-proof-review-subtab")).toBeVisible();

  // Clicking the subtab nav button must also update the URL hash.
  await page.getByTestId("voice-subtab-browser").click();
  await expect(page).toHaveURL(/#voice\/browser$/);
});
