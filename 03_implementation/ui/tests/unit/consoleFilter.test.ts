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
