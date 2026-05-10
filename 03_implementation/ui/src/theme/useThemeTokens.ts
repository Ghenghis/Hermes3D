/**
 * `useThemeTokens` — convenience hook returning the active palette + raw
 * scales without forcing components to import both `useTheme` and the
 * token tables. Pair with `useTheme` for the setter.
 */
import { useMemo } from "react";
import { paletteFor, tokens, type ThemePalette } from "./tokens";
import { useTheme } from "./ThemeProvider";

export interface ThemeTokensValue {
  palette: ThemePalette;
  spacing: typeof tokens.spacing;
  fontSize: typeof tokens.fontSize;
  radius: typeof tokens.radius;
  iconSize: typeof tokens.iconSize;
  shadow: typeof tokens.shadow;
}

export function useThemeTokens(): ThemeTokensValue {
  const { resolvedTheme } = useTheme();
  return useMemo<ThemeTokensValue>(
    () => ({
      palette: paletteFor(resolvedTheme),
      spacing: tokens.spacing,
      fontSize: tokens.fontSize,
      radius: tokens.radius,
      iconSize: tokens.iconSize,
      shadow: tokens.shadow,
    }),
    [resolvedTheme],
  );
}
