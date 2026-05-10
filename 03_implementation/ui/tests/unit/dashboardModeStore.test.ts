import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  ALL_CUSTOM_WIDGETS,
  DASHBOARD_MODES,
  DEFAULT_CUSTOM_LAYOUT,
  isDashboardMode,
  LS_CUSTOM_LAYOUT_KEY,
  modeFromHash,
  modeFromQueryString,
  readPersistedCustomLayout,
  readPersistedMode,
  resolveInitialMode,
  writePersistedCustomLayout,
} from "../../src/components/dashboard/dashboardModeStore";

class MemoryStorage {
  private store = new Map<string, string>();
  getItem(key: string): string | null {
    return this.store.has(key) ? this.store.get(key)! : null;
  }
  setItem(key: string, value: string): void {
    this.store.set(key, value);
  }
  clear(): void {
    this.store.clear();
  }
}

beforeEach(() => {
  // Reset only the keys this suite touches. Calling localStorage.clear() or
  // iterating with localStorage.length both break subsequent getItem calls
  // under jsdom 25 (Storage proxy quirk).
  window.localStorage.removeItem("h3d.dashboard.mode");
  window.localStorage.removeItem(LS_CUSTOM_LAYOUT_KEY);
});

afterEach(() => {
  // Reset only the keys this suite touches. Calling localStorage.clear() or
  // iterating with localStorage.length both break subsequent getItem calls
  // under jsdom 25 (Storage proxy quirk).
  window.localStorage.removeItem("h3d.dashboard.mode");
  window.localStorage.removeItem(LS_CUSTOM_LAYOUT_KEY);
});

describe("dashboardModeStore — pure helpers", () => {
  describe("isDashboardMode", () => {
    it("accepts each canonical mode", () => {
      for (const mode of DASHBOARD_MODES) {
        expect(isDashboardMode(mode)).toBe(true);
      }
    });
    it("rejects unknown values", () => {
      expect(isDashboardMode("super")).toBe(false);
      expect(isDashboardMode(undefined)).toBe(false);
      expect(isDashboardMode(null)).toBe(false);
      expect(isDashboardMode(42)).toBe(false);
    });
  });

  describe("modeFromQueryString", () => {
    it("returns the mode for a recognised value", () => {
      expect(modeFromQueryString("?mode=simple")).toBe("simple");
      expect(modeFromQueryString("mode=advanced")).toBe("advanced");
      expect(modeFromQueryString("?foo=bar&mode=custom")).toBe("custom");
    });
    it("returns null for missing or invalid values", () => {
      expect(modeFromQueryString("")).toBeNull();
      expect(modeFromQueryString("?mode=")).toBeNull();
      expect(modeFromQueryString("?mode=enterprise")).toBeNull();
      expect(modeFromQueryString("?other=advanced")).toBeNull();
    });
  });

  describe("modeFromHash", () => {
    it("parses each separator (`:`, `/`, `.`)", () => {
      expect(modeFromHash("#dashboard:simple")).toBe("simple");
      expect(modeFromHash("#dashboard/advanced")).toBe("advanced");
      expect(modeFromHash("#dashboard.custom")).toBe("custom");
    });
    it("is case-insensitive on the mode token", () => {
      expect(modeFromHash("#dashboard:SIMPLE")).toBe("simple");
    });
    it("returns null for unrelated hashes", () => {
      expect(modeFromHash("")).toBeNull();
      expect(modeFromHash("#agents")).toBeNull();
      expect(modeFromHash("#dashboard")).toBeNull();
      expect(modeFromHash("#dashboard:bogus")).toBeNull();
    });
  });

  describe("resolveInitialMode", () => {
    it("query string beats hash beats storage beats default", () => {
      const storage = new MemoryStorage();
      storage.setItem("h3d.dashboard.mode", "advanced");
      // 1) query string wins
      expect(resolveInitialMode({ search: "?mode=simple", hash: "#dashboard:custom", storage })).toBe("simple");
      // 2) hash beats storage
      expect(resolveInitialMode({ search: "", hash: "#dashboard:custom", storage })).toBe("custom");
      // 3) storage beats default
      expect(resolveInitialMode({ search: "", hash: "", storage })).toBe("advanced");
      // 4) default
      const empty = new MemoryStorage();
      expect(resolveInitialMode({ search: "", hash: "", storage: empty })).toBe("advanced");
    });

    it("ignores invalid persisted values", () => {
      const storage = new MemoryStorage();
      storage.setItem("h3d.dashboard.mode", "garbage");
      expect(resolveInitialMode({ search: "", hash: "", storage })).toBe("advanced");
    });
  });

  describe("readPersistedMode", () => {
    it("returns null when storage is unavailable", () => {
      expect(readPersistedMode(null)).toBeNull();
    });
    it("returns null for unknown values", () => {
      const storage = new MemoryStorage();
      storage.setItem("h3d.dashboard.mode", "not-a-mode");
      expect(readPersistedMode(storage)).toBeNull();
    });
    it("returns the persisted mode when valid", () => {
      const storage = new MemoryStorage();
      storage.setItem("h3d.dashboard.mode", "custom");
      expect(readPersistedMode(storage)).toBe("custom");
    });
  });

  describe("custom layout persistence", () => {
    it("returns null when nothing has been persisted", () => {
      expect(readPersistedCustomLayout(new MemoryStorage())).toBeNull();
    });
    it("filters out unknown widget ids and returns the survivors", () => {
      const storage = new MemoryStorage();
      storage.setItem(LS_CUSTOM_LAYOUT_KEY, JSON.stringify(["kpi", "garbage", "fleet"]));
      expect(readPersistedCustomLayout(storage)).toEqual(["kpi", "fleet"]);
    });
    it("returns null for non-array json", () => {
      const storage = new MemoryStorage();
      storage.setItem(LS_CUSTOM_LAYOUT_KEY, JSON.stringify({ foo: "bar" }));
      expect(readPersistedCustomLayout(storage)).toBeNull();
    });
    it("returns null for an array with no valid ids", () => {
      const storage = new MemoryStorage();
      storage.setItem(LS_CUSTOM_LAYOUT_KEY, JSON.stringify(["zzz", "aaa"]));
      expect(readPersistedCustomLayout(storage)).toBeNull();
    });
    it("write+read round-trips the default layout", () => {
      const storage = new MemoryStorage();
      writePersistedCustomLayout(DEFAULT_CUSTOM_LAYOUT, storage);
      expect(readPersistedCustomLayout(storage)).toEqual([...DEFAULT_CUSTOM_LAYOUT]);
    });
  });

  describe("default layout invariants", () => {
    it("only references known widget ids", () => {
      for (const id of DEFAULT_CUSTOM_LAYOUT) {
        expect(ALL_CUSTOM_WIDGETS).toContain(id);
      }
    });
    it("has at least the user-spec'd 5 widgets", () => {
      expect(DEFAULT_CUSTOM_LAYOUT.length).toBeGreaterThanOrEqual(5);
    });
  });
});
