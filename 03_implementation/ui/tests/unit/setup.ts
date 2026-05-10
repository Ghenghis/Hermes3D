/**
 * Vitest setup — shared by W6-3, W6-8, W8-2 lanes.
 *
 * Provides:
 *   - `@testing-library/jest-dom` matchers
 *   - Auto-cleanup of mounted DOM nodes between tests
 *   - A working `localStorage` / `sessionStorage` polyfill. jsdom 25
 *     under Node 25 leaves `localStorage` as an empty object without the
 *     standard methods, so we install a minimal Storage shim.
 */
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach } from "vitest";

class InMemoryStorage implements Storage {
  private store = new Map<string, string>();
  get length(): number {
    return this.store.size;
  }
  clear(): void {
    this.store.clear();
  }
  getItem(key: string): string | null {
    return this.store.has(key) ? this.store.get(key)! : null;
  }
  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null;
  }
  removeItem(key: string): void {
    this.store.delete(key);
  }
  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }
}

function ensureStorage(): void {
  const w = globalThis as unknown as { window?: Window & { localStorage: Storage; sessionStorage: Storage } };
  if (typeof w.window === "undefined") return;
  const probe = w.window.localStorage as Partial<Storage> | undefined;
  if (!probe || typeof probe.setItem !== "function") {
    Object.defineProperty(w.window, "localStorage", {
      value: new InMemoryStorage(),
      configurable: true,
    });
  }
  const sprobe = w.window.sessionStorage as Partial<Storage> | undefined;
  if (!sprobe || typeof sprobe.setItem !== "function") {
    Object.defineProperty(w.window, "sessionStorage", {
      value: new InMemoryStorage(),
      configurable: true,
    });
  }
}

ensureStorage();

beforeEach(() => {
  ensureStorage();
});

afterEach(() => {
  cleanup();
});
