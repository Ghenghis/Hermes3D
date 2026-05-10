/**
 * Public surface of the W8-3 theme system. Adopters should import from
 * `@/theme` (or the relative path) instead of reaching into individual
 * files — this re-export is the contract for cross-lane consumers.
 */
export {
  ThemeProvider,
  useTheme,
  type ThemeContextValue,
  type ThemeProviderProps,
} from "./ThemeProvider";
export { useThemeTokens, type ThemeTokensValue } from "./useThemeTokens";
export {
  darkPalette,
  lightPalette,
  paletteFor,
  themeCssVars,
  tailwindThemeExtension,
  tokens,
  type ThemeMode,
  type ResolvedThemeMode,
  type ThemePalette,
  type Tokens,
} from "./tokens";
export { bootstrapTheme } from "./themeBootstrap";
