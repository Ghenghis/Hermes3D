/**
 * Vitest setup for the W6-4 lane (ActionWindow + TaskMonitor).
 *
 * Loads `@testing-library/jest-dom` matcher extensions so test files can use
 * `toBeInTheDocument`, `toHaveAttribute`, etc.
 *
 * Also patches `window.localStorage` with a working in-memory implementation
 * because Node 25 ships a native localStorage stub (under the experimental
 * `--localstorage-file` flag) that exposes `setItem`/`getItem` but is missing
 * `clear`/`removeItem`. The native stub shadows jsdom's full implementation
 * inside the vitest worker, breaking real test code. The shim below is
 * jsdom-compatible and only installed when the global is broken.
 *
 * Kept lane-scoped (`-w6-4` suffix) so it does not collide with whatever
 * global setup W6-3's dashboard suite ends up using when those land.
 */

import "@testing-library/jest-dom/vitest";

if (typeof window !== "undefined") {
  const ls = window.localStorage as unknown as { clear?: () => void } | undefined;
  if (!ls || typeof ls.clear !== "function") {
    const store = new Map<string, string>();
    const fullShim = {
      get length() {
        return store.size;
      },
      clear() {
        store.clear();
      },
      getItem(key: string) {
        return store.has(key) ? store.get(key)! : null;
      },
      key(index: number) {
        return Array.from(store.keys())[index] ?? null;
      },
      removeItem(key: string) {
        store.delete(key);
      },
      setItem(key: string, value: string) {
        store.set(key, String(value));
      },
    };
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      writable: true,
      value: fullShim,
    });
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      writable: true,
      value: fullShim,
    });
  }
}
