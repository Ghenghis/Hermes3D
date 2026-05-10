/**
 * Unit tests for the W15-A17 named-palette layer:
 *   - palette inventory matches the spec (6 entries, stable ids)
 *   - applyPalette stamps CSS variables for non-default ids
 *   - applyPalette is a no-op for the default id (does not overwrite vars)
 *   - localStorage round-trip via read/writeStoredPaletteId
 *   - every palette ships every required `--h3d-color-*` key
 *   - every palette meets WCAG AA contrast (body text 4.5:1, UI 3.0:1)
 */
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  applyPalette,
  DEFAULT_PALETTE_ID,
  isNamedPaletteId,
  NAMED_PALETTES,
  PALETTE_STORAGE_KEY,
  readStoredPaletteId,
  writeStoredPaletteId,
} from "../../src/theme/palettes";

const REQUIRED_KEYS = [
  "--h3d-color-background",
  "--h3d-color-surface",
  "--h3d-color-surface-2",
  "--h3d-color-border",
  "--h3d-color-text-primary",
  "--h3d-color-text-secondary",
  "--h3d-color-primary",
  "--h3d-color-secondary",
  "--h3d-color-accent",
  "--h3d-color-error",
  "--h3d-color-warning",
  "--h3d-color-success",
  "--h3d-color-info",
] as const;

// WCAG 2.1 relative luminance + contrast.
function hexChannels(hex: string): [number, number, number] {
  const m = hex.replace(/^#/, "");
  const r = parseInt(m.slice(0, 2), 16) / 255;
  const g = parseInt(m.slice(2, 4), 16) / 255;
  const b = parseInt(m.slice(4, 6), 16) / 255;
  return [r, g, b];
}
function linearise(c: number): number {
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}
function luminance([r, g, b]: [number, number, number]): number {
  return 0.2126 * linearise(r) + 0.7152 * linearise(g) + 0.0722 * linearise(b);
}
function contrast(a: string, b: string): number {
  const la = luminance(hexChannels(a));
  const lb = luminance(hexChannels(b));
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

describe("named palettes (W15-A17)", () => {
  beforeEach(() => {
    document.documentElement.removeAttribute("style");
    delete document.documentElement.dataset.h3dPalette;
    window.localStorage.removeItem(PALETTE_STORAGE_KEY);
  });

  afterEach(() => {
    document.documentElement.removeAttribute("style");
    delete document.documentElement.dataset.h3dPalette;
  });

  it("ships exactly six palettes with stable ids", () => {
    const ids = NAMED_PALETTES.map((p) => p.id);
    expect(ids).toEqual([
      "default",
      "cyberpunk",
      "matrix",
      "tron",
      "industrial-forge",
      "aurora-operator",
    ]);
  });

  it("every palette defines every required CSS variable", () => {
    for (const p of NAMED_PALETTES) {
      for (const key of REQUIRED_KEYS) {
        expect(p.cssVars[key], `${p.id} missing ${key}`).toMatch(/^#[0-9a-f]{6}$/i);
      }
    }
  });

  it("every palette meets WCAG AA contrast (body 4.5, UI 3.0)", () => {
    for (const p of NAMED_PALETTES) {
      const bg = p.cssVars["--h3d-color-background"]!;
      const fg = p.cssVars["--h3d-color-text-primary"]!;
      const muted = p.cssVars["--h3d-color-text-secondary"]!;
      const primary = p.cssVars["--h3d-color-primary"]!;
      expect(contrast(fg, bg), `${p.id} fg:bg`).toBeGreaterThanOrEqual(4.5);
      expect(contrast(muted, bg), `${p.id} muted:bg`).toBeGreaterThanOrEqual(4.5);
      expect(contrast(primary, bg), `${p.id} primary:bg`).toBeGreaterThanOrEqual(3.0);
    }
  });

  it("isNamedPaletteId guards membership", () => {
    expect(isNamedPaletteId("default")).toBe(true);
    expect(isNamedPaletteId("cyberpunk")).toBe(true);
    expect(isNamedPaletteId("not-a-palette")).toBe(false);
    expect(isNamedPaletteId(undefined)).toBe(false);
    expect(isNamedPaletteId(42)).toBe(false);
  });

  it("applyPalette stamps data-h3d-palette and CSS variables for non-default ids", () => {
    applyPalette("matrix");
    expect(document.documentElement.dataset.h3dPalette).toBe("matrix");
    expect(
      document.documentElement.style.getPropertyValue("--h3d-color-background"),
    ).toBe("#020a02");
    expect(
      document.documentElement.style.getPropertyValue("--h3d-color-primary"),
    ).toBe("#22ff7b");
  });

  it("applyPalette('default') stamps the attribute but does NOT touch CSS vars", () => {
    // Pre-stage with a non-default palette so we can detect the rollback.
    applyPalette("cyberpunk");
    expect(
      document.documentElement.style.getPropertyValue("--h3d-color-background"),
    ).toBe("#0b0014");

    applyPalette(DEFAULT_PALETTE_ID);
    expect(document.documentElement.dataset.h3dPalette).toBe("default");
    // Variables remain whatever was last stamped — ThemeProvider owns the
    // base values for the default selection. Crucially we must NOT have
    // rewritten background to the dark default (which would clobber light
    // mode).
    expect(
      document.documentElement.style.getPropertyValue("--h3d-color-background"),
    ).toBe("#0b0014");
  });

  it("localStorage round-trip via read/writeStoredPaletteId", () => {
    expect(readStoredPaletteId()).toBe("default");
    writeStoredPaletteId("tron");
    expect(window.localStorage.getItem(PALETTE_STORAGE_KEY)).toBe("tron");
    expect(readStoredPaletteId()).toBe("tron");
  });

  it("readStoredPaletteId falls back to default on garbage", () => {
    window.localStorage.setItem(PALETTE_STORAGE_KEY, "nonsense");
    expect(readStoredPaletteId()).toBe("default");
  });
});
