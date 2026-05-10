/**
 * ThemeProvider — W8-3 lane.
 *
 * Provides a `{ theme, resolvedTheme, setTheme }` context to descendants and:
 *   1. Persists the user choice to `localStorage` under `h3d.theme`.
 *   2. Observes `prefers-color-scheme` when the choice is `"system"`.
 *   3. Updates `<html>` `class` so Tailwind `dark:` variants work.
 *   4. Stamps `--h3d-color-*` CSS custom properties so non-Tailwind code
 *      (recharts colours, inline styles, the lucide stroke colour) reads
 *      the active palette by name.
 *
 * Design references:
 *   - Tailwind dark-mode docs (https://tailwindcss.com/docs/dark-mode)
 *     -- using `class` strategy, attached to `<html>`.
 *   - WCAG 2.1 (https://www.w3.org/WAI/WCAG21/Understanding/) -- contrast
 *     pairs verified in tokens.ts.
 *
 * Provider must be mounted high in the tree (outside StrictMode is fine
 * but the package default is to mount under `<App />`). See
 * `themeBootstrap.ts` for an entry-point hook that adopters can call
 * before React renders, to avoid a flash of the wrong theme.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  themeCssVars,
  type ResolvedThemeMode,
  type ThemeMode,
} from "./tokens";

const STORAGE_KEY = "h3d.theme";
const VALID_MODES: readonly ThemeMode[] = ["light", "dark", "system"] as const;

export interface ThemeContextValue {
  /** The user's stored choice, including `"system"`. */
  theme: ThemeMode;
  /** The actually-applied palette after resolving `"system"`. */
  resolvedTheme: ResolvedThemeMode;
  /** Update the stored choice and re-apply the document class. */
  setTheme: (next: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export interface ThemeProviderProps {
  children?: ReactNode;
  /**
   * Initial theme to use before `localStorage` resolves. `"system"` is the
   * safe default — first paint will match the user's OS preference.
   */
  defaultTheme?: ThemeMode;
  /**
   * Storage key override — only useful for tests that want isolation. The
   * default `h3d.theme` is the production contract.
   */
  storageKey?: string;
}

function readStoredTheme(storageKey: string, fallback: ThemeMode): ThemeMode {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = window.localStorage.getItem(storageKey);
    if (raw && (VALID_MODES as readonly string[]).includes(raw)) {
      return raw as ThemeMode;
    }
  } catch {
    // Ignore — Safari private mode + sandboxed iframes throw on access.
  }
  return fallback;
}

function detectSystemTheme(): ResolvedThemeMode {
  if (typeof window === "undefined" || !window.matchMedia) return "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function resolveTheme(theme: ThemeMode): ResolvedThemeMode {
  return theme === "system" ? detectSystemTheme() : theme;
}

/**
 * Apply the resolved theme to the document. Called both on mount and on
 * every change so that hot-reloads stay consistent.
 */
function applyTheme(resolved: ResolvedThemeMode): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.classList.remove("light", "dark");
  root.classList.add(resolved);
  root.dataset.h3dTheme = resolved;

  const vars = themeCssVars(resolved);
  for (const [name, value] of Object.entries(vars)) {
    root.style.setProperty(name, value);
  }
}

export function ThemeProvider({
  children,
  defaultTheme = "system",
  storageKey = STORAGE_KEY,
}: ThemeProviderProps): JSX.Element {
  const [theme, setThemeState] = useState<ThemeMode>(() =>
    readStoredTheme(storageKey, defaultTheme),
  );
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedThemeMode>(() =>
    resolveTheme(readStoredTheme(storageKey, defaultTheme)),
  );

  // Keep a ref to the latest `theme` so the matchMedia listener does not
  // need to re-bind every render. matchMedia listeners are expensive to
  // re-bind because Safari adds a microtask delay.
  const themeRef = useRef(theme);
  themeRef.current = theme;

  // Apply on every theme change.
  useEffect(() => {
    const next = resolveTheme(theme);
    setResolvedTheme(next);
    applyTheme(next);
  }, [theme]);

  // Listen to system preference only while in "system" mode.
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const handle = () => {
      if (themeRef.current !== "system") return;
      const next: ResolvedThemeMode = media.matches ? "dark" : "light";
      setResolvedTheme(next);
      applyTheme(next);
    };
    // addEventListener is preferred; older Safari fell back to addListener.
    if (typeof media.addEventListener === "function") {
      media.addEventListener("change", handle);
      return () => media.removeEventListener("change", handle);
    }
    // Legacy fallback — kept for completeness.
    media.addListener(handle);
    return () => media.removeListener(handle);
  }, []);

  const setTheme = useCallback(
    (next: ThemeMode) => {
      if (!(VALID_MODES as readonly string[]).includes(next)) {
        // Ignore garbage in production; warn in dev so callers learn.
        // import.meta.env.DEV is Vite's compile-time dev flag; falls back
        // to a defensive `false` for non-Vite consumers.
        const isDev =
          typeof import.meta !== "undefined" &&
          (import.meta as { env?: { DEV?: boolean } }).env?.DEV === true;
        if (isDev) {
          // eslint-disable-next-line no-console
          console.warn(`ThemeProvider: ignoring invalid theme "${next}"`);
        }
        return;
      }
      setThemeState(next);
      try {
        window.localStorage.setItem(storageKey, next);
      } catch {
        // Storage may be disabled — non-fatal.
      }
    },
    [storageKey],
  );

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, resolvedTheme, setTheme }),
    [theme, resolvedTheme, setTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

/** Read the active theme + setter. Must be inside `<ThemeProvider>`. */
export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme: must be used inside <ThemeProvider>");
  }
  return ctx;
}

export const __testing = {
  STORAGE_KEY,
  applyTheme,
  resolveTheme,
  detectSystemTheme,
};
