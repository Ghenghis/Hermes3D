/**
 * Optional pre-React bootstrap — eliminates the flash-of-wrong-theme by
 * stamping the document class + CSS variables before React renders. Call
 * this at the top of the entry point (`main.tsx`) when integrating the
 * theme system, BEFORE `ReactDOM.createRoot`.
 *
 * Safe to call multiple times; mutations are idempotent.
 *
 * W15-A17 extension: after the base light/dark variables land, the
 * persisted named palette (`h3d.theme.palette`) is applied so its
 * `--h3d-color-*` overrides shadow the defaults on first paint.
 */
import { themeCssVars, type ThemeMode } from "./tokens";
import { applyPalette, readStoredPaletteId } from "./palettes";

const STORAGE_KEY = "h3d.theme";

export function bootstrapTheme(storageKey: string = STORAGE_KEY): void {
  if (typeof document === "undefined") return;
  let stored: ThemeMode | null = null;
  try {
    const raw = window.localStorage.getItem(storageKey);
    if (raw === "light" || raw === "dark" || raw === "system") {
      stored = raw;
    }
  } catch {
    // ignore
  }

  let resolved: "light" | "dark" = "dark";
  if (stored === "light") {
    resolved = "light";
  } else if (stored === "dark") {
    resolved = "dark";
  } else {
    // null or "system" — derive from the OS.
    if (typeof window !== "undefined" && window.matchMedia) {
      resolved = window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    }
  }

  const root = document.documentElement;
  root.classList.remove("light", "dark");
  root.classList.add(resolved);
  root.dataset.h3dTheme = resolved;

  const vars = themeCssVars(resolved);
  for (const [k, v] of Object.entries(vars)) {
    root.style.setProperty(k, v);
  }

  // Layer the named palette on top of the base variables so deep links
  // and reloads keep the user's chosen palette before React renders.
  // `applyPalette` is a no-op when the stored id is the default.
  applyPalette(readStoredPaletteId());
}
