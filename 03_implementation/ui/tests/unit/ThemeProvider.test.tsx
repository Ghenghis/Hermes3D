/**
 * W8-3 unit tests — ThemeProvider.
 *
 * Targets: persistence in localStorage, prefers-color-scheme follow-on,
 * `<html>` class toggling, and CSS custom property emission.
 *
 * Test framework: Vitest + jsdom (matches the rest of `tests/unit/*`).
 * The wider repo's vitest config mounts `tests/unit/setup.ts` which
 * pulls in `@testing-library/jest-dom/vitest`.
 */
import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeProvider, useTheme } from "../../src/theme/ThemeProvider";

const STORAGE_KEY = "h3d.theme";

function withProvider() {
  return ({ children }: { children: React.ReactNode }) => (
    <ThemeProvider>{children}</ThemeProvider>
  );
}

interface MediaListener {
  (event: MediaQueryListEvent): void;
}

function clearStorage() {
  // jsdom 25 + Node 25's built-in localStorage on the global window does
  // not implement `clear()`; explicit per-key removal is portable.
  window.localStorage.removeItem(STORAGE_KEY);
}

beforeEach(() => {
  clearStorage();
  document.documentElement.className = "";
  delete document.documentElement.dataset.h3dTheme;
});

afterEach(() => {
  cleanup();
  clearStorage();
});

describe("ThemeProvider", () => {
  it("defaults to 'system' and resolves to the prefers-color-scheme value", () => {
    const matchMediaSpy = vi.spyOn(window, "matchMedia").mockImplementation(
      (query: string) =>
        ({
          matches: query.includes("dark") ? true : false,
          media: query,
          onchange: null,
          addListener: () => undefined,
          removeListener: () => undefined,
          addEventListener: () => undefined,
          removeEventListener: () => undefined,
          dispatchEvent: () => false,
        }) as unknown as MediaQueryList,
    );

    const { result } = renderHook(() => useTheme(), { wrapper: withProvider() });
    expect(result.current.theme).toBe("system");
    expect(result.current.resolvedTheme).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    matchMediaSpy.mockRestore();
  });

  it("setTheme('light') persists to localStorage and toggles the html class", () => {
    const { result } = renderHook(() => useTheme(), { wrapper: withProvider() });
    act(() => result.current.setTheme("light"));
    expect(result.current.theme).toBe("light");
    expect(result.current.resolvedTheme).toBe("light");
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("light");
    expect(document.documentElement.classList.contains("light")).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
    expect(document.documentElement.dataset.h3dTheme).toBe("light");
    expect(
      document.documentElement.style.getPropertyValue("--h3d-color-background"),
    ).toBe("#ffffff");
  });

  it("setTheme('dark') flips back to dark with new CSS vars", () => {
    const { result } = renderHook(() => useTheme(), { wrapper: withProvider() });
    act(() => result.current.setTheme("light"));
    act(() => result.current.setTheme("dark"));
    expect(result.current.resolvedTheme).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(
      document.documentElement.style.getPropertyValue("--h3d-color-background"),
    ).toBe("#0a0e1a");
  });

  it("system mode reacts to matchMedia change events", () => {
    let capturedListener: MediaListener | null = null;
    const matches = { current: false };
    vi.spyOn(window, "matchMedia").mockImplementation(
      (query: string) =>
        ({
          get matches() {
            return matches.current;
          },
          media: query,
          onchange: null,
          addListener: () => undefined,
          removeListener: () => undefined,
          addEventListener: (_: string, listener: MediaListener) => {
            capturedListener = listener;
          },
          removeEventListener: () => undefined,
          dispatchEvent: () => false,
        }) as unknown as MediaQueryList,
    );

    const { result } = renderHook(() => useTheme(), { wrapper: withProvider() });
    expect(result.current.resolvedTheme).toBe("light");

    act(() => {
      matches.current = true;
      capturedListener?.({ matches: true } as MediaQueryListEvent);
    });
    expect(result.current.resolvedTheme).toBe("dark");
  });

  it("ignores invalid theme values", () => {
    const { result } = renderHook(() => useTheme(), { wrapper: withProvider() });
    act(() => {
      // @ts-expect-error — testing runtime guard
      result.current.setTheme("midnight");
    });
    expect(result.current.theme).toBe("system");
  });

  it("reads existing localStorage value on mount", () => {
    window.localStorage.setItem(STORAGE_KEY, "light");
    const { result } = renderHook(() => useTheme(), { wrapper: withProvider() });
    expect(result.current.theme).toBe("light");
    expect(result.current.resolvedTheme).toBe("light");
  });

  it("throws if useTheme is called outside the provider", () => {
    expect(() => renderHook(() => useTheme())).toThrow(/inside <ThemeProvider>/);
  });
});
