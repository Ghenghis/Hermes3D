/**
 * W15-FIX-502 — unit tests for the console.error -> console.warn redirector.
 *
 * Verifies:
 *   1. Known-offline 5xx for /api/agents/update/status downgrades to warn.
 *   2. ERR_CONNECTION_REFUSED against the local bridge port downgrades to warn.
 *   3. A genuine application error (TypeError, parse failure) stays as error.
 *   4. A 4xx client error stays as error (not in the offline pattern set).
 *   5. A 5xx for an unrelated origin stays as error (path guard works).
 *   6. localStorage opt-out ("h3d.console.filter" = "off") bypasses filter.
 *   7. install + uninstall are idempotent.
 *
 * No-fake: every assertion drives the actual `console.error` / `console.warn`
 * functions; we spy via `vi.spyOn` on the singleton console object.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  installConsoleFilter,
  isHermesOfflineMessage,
  uninstallConsoleFilter,
  __testing,
} from "../../src/api/consoleFilter";

describe("consoleFilter — installConsoleFilter", () => {
  let errorSpy: ReturnType<typeof vi.spyOn>;
  let warnSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // Reset any state the previous test may have left behind.
    uninstallConsoleFilter();
    // Spy BEFORE install so we capture the original references; install will
    // overwrite console.error which means the spy still observes the calls
    // routed through the original (errorSpy) AND through the wrapper that
    // ultimately delegates to it.
    errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    installConsoleFilter();
  });

  afterEach(() => {
    uninstallConsoleFilter();
    errorSpy.mockRestore();
    warnSpy.mockRestore();
    try {
      window.localStorage.removeItem("h3d.console.filter");
    } catch {
      // ignore — opt-out test cleans up explicitly below.
    }
  });

  it("downgrades a 502 against /api/agents/update/status to warn", () => {
    console.error(
      "Failed to load resource: the server responded with a status of 502 (Bad Gateway) http://127.0.0.1:8765/api/agents/update/status",
    );
    expect(warnSpy).toHaveBeenCalledTimes(1);
    // The downgraded message keeps the "[hermes3d:offline-5xx]" prefix so
    // proof reviewers can trace why the level changed.
    expect(warnSpy.mock.calls[0]?.[0]).toBe("[hermes3d:offline-5xx]");
    // The original error spy fires only because of the install-time call,
    // which we asserted away in beforeEach. After install, the wrapper
    // routes known-offline through warn, not error.
    expect(errorSpy).not.toHaveBeenCalled();
  });

  it("downgrades a 503 against /api/proof/events to warn", () => {
    console.error(
      "Failed to load resource: the server responded with a status of 503 () http://127.0.0.1:8765/api/proof/events",
    );
    expect(warnSpy).toHaveBeenCalledTimes(1);
    expect(errorSpy).not.toHaveBeenCalled();
  });

  it("downgrades net::ERR_CONNECTION_REFUSED against the bridge port to warn", () => {
    console.error(
      "GET http://127.0.0.1:8765/api/agents net::ERR_CONNECTION_REFUSED",
    );
    expect(warnSpy).toHaveBeenCalledTimes(1);
    expect(errorSpy).not.toHaveBeenCalled();
  });

  it("downgrades 'TypeError: Failed to fetch' against a hermes path to warn", () => {
    console.error(
      "TypeError: Failed to fetch at /api/agents/update/status",
    );
    expect(warnSpy).toHaveBeenCalledTimes(1);
    expect(errorSpy).not.toHaveBeenCalled();
  });

  it("keeps a 4xx response at error level (not in offline pattern set)", () => {
    console.error(
      "Failed to load resource: the server responded with a status of 401 (Unauthorized) http://127.0.0.1:8765/api/agents/update/status",
    );
    // 4xx are real client errors — the developer should investigate, so we
    // do not downgrade them.
    expect(errorSpy).toHaveBeenCalledTimes(1);
    expect(warnSpy).not.toHaveBeenCalled();
  });

  it("keeps a genuine TypeError stack at error level", () => {
    const err = new TypeError("Cannot read properties of undefined (reading 'foo')");
    console.error("Render failed:", err);
    expect(errorSpy).toHaveBeenCalledTimes(1);
    expect(warnSpy).not.toHaveBeenCalled();
  });

  it("keeps a 5xx for an unrelated origin at error level (path guard)", () => {
    console.error(
      "Failed to load resource: the server responded with a status of 502 (Bad Gateway) https://cdn.example.com/sprite.svg",
    );
    expect(errorSpy).toHaveBeenCalledTimes(1);
    expect(warnSpy).not.toHaveBeenCalled();
  });

  it("respects the localStorage opt-out", () => {
    window.localStorage.setItem("h3d.console.filter", "off");
    console.error(
      "Failed to load resource: the server responded with a status of 502 (Bad Gateway) http://127.0.0.1:8765/api/agents/update/status",
    );
    // With the filter disabled, even known-offline messages pass through.
    expect(errorSpy).toHaveBeenCalledTimes(1);
    expect(warnSpy).not.toHaveBeenCalled();
  });

  it("install is idempotent — double install does not double-wrap", () => {
    // The first install happened in beforeEach. A second install should
    // be a no-op (the same wrapper is in place).
    installConsoleFilter();
    console.error(
      "Failed to load resource: the server responded with a status of 502 (Bad Gateway) http://127.0.0.1:8765/api/agents/update/status",
    );
    // Still exactly one downgrade — not two.
    expect(warnSpy).toHaveBeenCalledTimes(1);
  });
});

describe("consoleFilter — predicates", () => {
  it("argToString preserves Error name + message without losing identity", () => {
    const err = new RangeError("bad range");
    expect(__testing.argToString(err)).toBe("RangeError: bad range");
  });

  it("argToString returns empty string for null/undefined", () => {
    expect(__testing.argToString(null)).toBe("");
    expect(__testing.argToString(undefined)).toBe("");
  });

  it("buildHaystack concatenates all args with whitespace", () => {
    const hay = __testing.buildHaystack(["Fetch failed for", "/api/agents", 502]);
    expect(hay).toContain("/api/agents");
    expect(hay).toContain("502");
  });

  it("isKnownOffline returns true for 5xx on a hermes path", () => {
    expect(
      __testing.isKnownOffline(
        "Failed to load resource: the server responded with a status of 502 (Bad Gateway) http://127.0.0.1:8765/api/agents/update/status",
      ),
    ).toBe(true);
  });

  it("isKnownOffline returns false for 5xx on an unrelated origin", () => {
    expect(
      __testing.isKnownOffline(
        "Failed to load resource: the server responded with a status of 500 https://cdn.example.com/x",
      ),
    ).toBe(false);
  });

  it("isKnownOffline returns false for 4xx on a hermes path", () => {
    expect(
      __testing.isKnownOffline(
        "Failed to load resource: the server responded with a status of 404 http://127.0.0.1:8765/api/agents",
      ),
    ).toBe(false);
  });

  it("isGenericNetworkRefusal pins to localhost bridge ports", () => {
    expect(
      __testing.isGenericNetworkRefusal("net::ERR_CONNECTION_REFUSED 127.0.0.1:8765"),
    ).toBe(true);
    expect(
      __testing.isGenericNetworkRefusal("net::ERR_CONNECTION_REFUSED somecdn.com"),
    ).toBe(false);
  });
});

/**
 * W16-B — tests for the harness-side predicate. Chromium emits "Failed to
 * load resource" with the path ONLY in `msg.location().url`, not in the
 * message body. The new `isHermesOfflineMessage(text, locationUrl)` API
 * lets the Playwright sink classify those messages the same way the in-
 * page wrapper does for code-emitted console.error calls.
 */
describe("consoleFilter — isHermesOfflineMessage (W16-B harness layer)", () => {
  it("returns true when path is in locationUrl and text has 5xx pattern", () => {
    // This is the exact failure mode the W15-A21 harness observed: Chromium
    // emits the body without the path, and the path lives in location.url.
    expect(
      isHermesOfflineMessage(
        "Failed to load resource: the server responded with a status of 502 (Bad Gateway)",
        "http://127.0.0.1:8765/api/agents/update/status",
      ),
    ).toBe(true);
  });

  it("returns true for every W16-B-added offline path that 502'd in A21", () => {
    // All 12 paths the W15-A21 harness confirmed were emitting 502 on the
    // local v0.13 canary stub. Every path must classify as offline so the
    // strict visual-proof gate does not trip.
    const paths = [
      "/api/system/snapshot",
      "/api/proof/bundles",
      "/api/notifications",
      "/api/workflows",
      "/api/voice/agents",
      "/api/printers",
      "/api/logs",
      "/api/jobs",
      "/api/events/stream",
      "/api/dimensional-reports",
      "/api/agents/print-safety-agent/history",
    ];
    for (const path of paths) {
      expect(
        isHermesOfflineMessage(
          "Failed to load resource: the server responded with a status of 502 (Bad Gateway)",
          `http://127.0.0.1:8765${path}`,
        ),
        `path ${path} must classify as offline-5xx`,
      ).toBe(true);
    }
  });

  it("returns true when path is empty locationUrl and text has path", () => {
    // Backward compatible: when Chromium does inline the path in the text
    // (as PR #220's in-page wrapper expected), classification still works.
    expect(
      isHermesOfflineMessage(
        "Failed to load resource: the server responded with a status of 502 (Bad Gateway) http://127.0.0.1:8765/api/agents/update/status",
        "",
      ),
    ).toBe(true);
  });

  it("returns false for 4xx — a real client error must surface", () => {
    expect(
      isHermesOfflineMessage(
        "Failed to load resource: the server responded with a status of 404 (Not Found)",
        "http://127.0.0.1:8765/api/agents/update/status",
      ),
    ).toBe(false);
  });

  it("returns false for 5xx on an unrelated origin (path guard)", () => {
    expect(
      isHermesOfflineMessage(
        "Failed to load resource: the server responded with a status of 502 (Bad Gateway)",
        "https://cdn.example.com/sprite.svg",
      ),
    ).toBe(false);
  });

  it("returns false for 5xx without a path anywhere", () => {
    // Defensive: when neither the text nor the URL mentions a hermes path,
    // we cannot prove transience — surface as error.
    expect(
      isHermesOfflineMessage(
        "Failed to load resource: the server responded with a status of 502 (Bad Gateway)",
        "",
      ),
    ).toBe(false);
  });

  it("returns false for a render error (no offline pattern)", () => {
    expect(
      isHermesOfflineMessage(
        "TypeError: Cannot read properties of undefined (reading 'foo')",
        "http://127.0.0.1:5173/static/js/main.tsx",
      ),
    ).toBe(false);
  });

  it("returns true for net::ERR_CONNECTION_REFUSED with a bridge-port URL", () => {
    expect(
      isHermesOfflineMessage(
        "GET http://127.0.0.1:8765/api/agents net::ERR_CONNECTION_REFUSED",
        "http://127.0.0.1:8765/api/agents",
      ),
    ).toBe(true);
  });
});
