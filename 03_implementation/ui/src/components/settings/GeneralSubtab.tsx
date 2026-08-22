/**
 * Settings → General subtab (W8-2 GUI breadth pages).
 *
 * Hosts user preferences that don't belong to the other subtabs:
 *   - Theme       · stored at backend GET/PUT /api/settings (AppSettings.theme)
 *   - Language    · localStorage-only (no backend route exists yet)
 *   - Default UI  · localStorage-only; the global topbar mode toggle is the
 *                   source of truth for the live session, this just sets
 *                   what `simple|full` is restored on next load
 *   - Default Dashboard mode · localStorage-only; mirrors the
 *                   `dashboardModeStore` default that W6-3 ships
 *
 * Why localStorage for non-theme prefs:
 *   The backend AppSettings shape (types/settings.ts) does not yet expose
 *   language / default-mode fields. Until W6-7 lands a richer schema, we
 *   write to `window.localStorage` so the preference survives reload while
 *   keeping the UI honest about what's persistent vs ephemeral.
 *
 * Form discipline:
 *   - Save button is disabled when no field has changed.
 *   - The Save handler awaits the live backend call and surfaces an honest
 *     error toast on failure — we never claim success on a 4xx/5xx.
 *
 * Sources consulted:
 *   - WAI-ARIA APG, "Form" pattern · https://www.w3.org/WAI/ARIA/apg/patterns/form/
 *     for the labelled-control + status-message structure used below.
 *   - React Router DOM "Working with the URL"
 *     https://reactrouter.com/en/main/start/concepts (we DO NOT add
 *     react-router; the existing AppShell uses hash routing, this subtab
 *     is internal state).
 */
import { useEffect, useState } from "react";
import { Languages, Moon, MonitorCog, Palette, Save } from "lucide-react";
import { adapters } from "../../api/adapters";
import type { AppSettings, ThemeName } from "../../types/settings";
import {
  applyPalette,
  DEFAULT_PALETTE_ID,
  isNamedPaletteId,
  NAMED_PALETTES,
  PALETTE_STORAGE_KEY,
  readStoredPaletteId,
  writeStoredPaletteId,
  type NamedPaletteId,
} from "../../theme/palettes";

type DashboardModePref = "simple" | "advanced" | "factory" | "creator" | "inspector" | "custom";
type UIModePref = "full" | "simple";
type LanguagePref = "en" | "es" | "de" | "fr" | "ja" | "zh";

const THEME_OPTIONS: { value: ThemeName; label: string }[] = [
  { value: "midnight", label: "Midnight" },
  { value: "alloy", label: "Alloy" },
  { value: "ember", label: "Ember" },
  { value: "forest", label: "Forest" },
];

const LANGUAGE_OPTIONS: { value: LanguagePref; label: string }[] = [
  { value: "en", label: "English" },
  { value: "es", label: "Español" },
  { value: "de", label: "Deutsch" },
  { value: "fr", label: "Français" },
  { value: "ja", label: "日本語" },
  { value: "zh", label: "中文" },
];

const UI_MODE_OPTIONS: { value: UIModePref; label: string; help: string }[] = [
  { value: "full", label: "Full Workbench", help: "All tabs visible by default" },
  { value: "simple", label: "Simple", help: "Single-pane, no sidebar" },
];

const DASHBOARD_MODE_OPTIONS: { value: DashboardModePref; label: string; help: string }[] = [
  { value: "simple", label: "Simple", help: "Status pills + key metrics" },
  { value: "advanced", label: "Advanced", help: "All panels, default" },
  { value: "factory", label: "Factory", help: "Cameras, console, jobs" },
  { value: "creator", label: "Create", help: "Idea/image to printable model" },
  { value: "inspector", label: "Inspect", help: "Software + live surfaces" },
  { value: "custom", label: "Custom", help: "User-curated layout" },
];

const LS_LANGUAGE = "h3d.settings.general.language";
const LS_UI_MODE = "h3d.settings.general.defaultUiMode";
const LS_DASHBOARD_MODE = "h3d.settings.general.defaultDashboardMode";

function readLocal<T extends string>(key: string, allowed: readonly T[], fallback: T): T {
  if (typeof window === "undefined") return fallback;
  const v = window.localStorage.getItem(key);
  return v && (allowed as readonly string[]).includes(v) ? (v as T) : fallback;
}

function writeLocal(key: string, value: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* quota or private mode — silently fall back to memory only */
  }
}

export function GeneralSubtab() {
  const [theme, setTheme] = useState<ThemeName>("midnight");
  const [serverTheme, setServerTheme] = useState<ThemeName | null>(null);
  const [language, setLanguage] = useState<LanguagePref>(() =>
    readLocal(LS_LANGUAGE, ["en", "es", "de", "fr", "ja", "zh"] as const, "en"),
  );
  const [uiMode, setUiMode] = useState<UIModePref>(() =>
    readLocal(LS_UI_MODE, ["full", "simple"] as const, "full"),
  );
  const [dashboardMode, setDashboardMode] = useState<DashboardModePref>(() =>
    readLocal(LS_DASHBOARD_MODE, ["simple", "advanced", "factory", "creator", "inspector", "custom"] as const, "advanced"),
  );
  // Named palette is persisted to localStorage under the dedicated
  // `h3d.theme.palette` key (W15-A17). Backend persistence is owned by
  // A20 (`/api/settings/themes`); until that endpoint exists, the
  // palette is preview-only and survives reload via local storage.
  const [palette, setPalette] = useState<NamedPaletteId>(() => readStoredPaletteId());
  const [savedPalette, setSavedPalette] = useState<NamedPaletteId>(palette);

  const [savedLanguage, setSavedLanguage] = useState<LanguagePref>(language);
  const [savedUiMode, setSavedUiMode] = useState<UIModePref>(uiMode);
  const [savedDashboardMode, setSavedDashboardMode] = useState<DashboardModePref>(dashboardMode);

  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<{ tone: "ok" | "err" | "info"; text: string } | null>(null);

  useEffect(() => {
    let mounted = true;
    void adapters
      .getSettings()
      .then((s: AppSettings) => {
        if (!mounted) return;
        setTheme(s.theme);
        setServerTheme(s.theme);
      })
      .catch(() => {
        if (!mounted) return;
        setStatus({
          tone: "info",
          text: "Settings backend unreachable; theme reflects local fallback.",
        });
      });
    return () => {
      mounted = false;
    };
  }, []);

  // Live preview: every palette change re-applies the CSS variables.
  // We intentionally do this BEFORE save — clicking a swatch should
  // preview immediately, like VS Code's theme picker, with the persist
  // step happening on Save (so revert == reload, or pick "default").
  useEffect(() => {
    applyPalette(palette);
  }, [palette]);

  const dirty =
    (serverTheme !== null && theme !== serverTheme) ||
    language !== savedLanguage ||
    uiMode !== savedUiMode ||
    dashboardMode !== savedDashboardMode ||
    palette !== savedPalette;

  const handleSave = async () => {
    if (!dirty || busy) return;
    setBusy(true);
    setStatus(null);
    try {
      // Theme is persisted via the live backend; the rest go to
      // localStorage so the GUI honours them on next load.
      if (serverTheme === null || theme !== serverTheme) {
        await adapters.saveSettings({ theme });
        setServerTheme(theme);
      }
      writeLocal(LS_LANGUAGE, language);
      writeLocal(LS_UI_MODE, uiMode);
      writeLocal(LS_DASHBOARD_MODE, dashboardMode);
      // The named palette has its own dedicated key (PALETTE_STORAGE_KEY)
      // because the W8-3 ThemeProvider already owns `h3d.theme` for
      // light/dark mode — keeping these orthogonal is the contract.
      writeStoredPaletteId(palette);
      setSavedLanguage(language);
      setSavedUiMode(uiMode);
      setSavedDashboardMode(dashboardMode);
      setSavedPalette(palette);
      await adapters.emitProofEvent("settings.general.saved", {
        theme,
        language,
        uiMode,
        dashboardMode,
        palette,
      });
      setStatus({ tone: "ok", text: "Preferences saved." });
    } catch (error) {
      setStatus({
        tone: "err",
        text: error instanceof Error ? error.message : "Save rejected by backend.",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <form
      data-testid="settings-general"
      className="flex flex-col gap-4 text-xs"
      onSubmit={(e) => {
        e.preventDefault();
        void handleSave();
      }}
      aria-busy={busy ? "true" : "false"}
    >
      <header className="flex items-center gap-2 text-muted">
        <MonitorCog size={14} />
        <span className="text-fg font-medium">General Preferences</span>
      </header>

      <fieldset className="flex flex-col gap-2 rounded border border-border bg-surface2/30 p-3">
        <legend className="px-1 text-[10px] uppercase tracking-wide text-muted">
          <Moon size={11} className="mr-1 inline" /> Theme
        </legend>
        <div role="radiogroup" aria-label="Theme" className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {THEME_OPTIONS.map((opt) => (
            <label
              key={opt.value}
              data-testid={`settings-general-theme-${opt.value}`}
              className={[
                "flex cursor-pointer items-center justify-between gap-2 rounded border px-2 py-1.5 text-[11px]",
                theme === opt.value
                  ? "border-accent-cyan bg-surface2 text-fg"
                  : "border-border text-muted hover:bg-surface2/60 hover:text-fg",
              ].join(" ")}
            >
              <input
                type="radio"
                name="general-theme"
                value={opt.value}
                checked={theme === opt.value}
                onChange={() => setTheme(opt.value)}
                className="sr-only"
              />
              <span>{opt.label}</span>
              <span className="font-mono text-[10px] text-muted">{opt.value}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset
        className="flex flex-col gap-2 rounded border border-border bg-surface2/30 p-3"
        data-testid="settings-general-palettes"
      >
        <legend className="px-1 text-[10px] uppercase tracking-wide text-muted">
          <Palette size={11} className="mr-1 inline" /> Theme Palette
        </legend>
        <p className="text-[10px] text-muted">
          Switches the live CSS variables. Saved to your browser
          (<code className="font-mono">{PALETTE_STORAGE_KEY}</code>); preview-only until the
          backend <code className="font-mono">/api/settings/themes</code> endpoint ships.
        </p>
        <div
          role="radiogroup"
          aria-label="Theme palette"
          className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3"
        >
          {NAMED_PALETTES.map((opt) => {
            const selected = palette === opt.id;
            return (
              <label
                key={opt.id}
                data-testid={`settings-general-palette-${opt.id}`}
                className={[
                  "flex cursor-pointer flex-col gap-1 rounded border px-2 py-1.5 text-[11px]",
                  selected
                    ? "border-accent-cyan bg-surface2 text-fg"
                    : "border-border text-muted hover:bg-surface2/60 hover:text-fg",
                ].join(" ")}
              >
                <input
                  type="radio"
                  name="general-palette"
                  value={opt.id}
                  checked={selected}
                  onChange={() => {
                    if (isNamedPaletteId(opt.id)) setPalette(opt.id);
                  }}
                  className="sr-only"
                />
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-fg">{opt.label}</span>
                  <span className="flex items-center gap-1">
                    <span
                      aria-hidden="true"
                      data-testid={`settings-general-palette-${opt.id}-swatch-bg`}
                      className="inline-block h-3 w-3 rounded-sm border border-border"
                      style={{ backgroundColor: opt.swatches.background }}
                    />
                    <span
                      aria-hidden="true"
                      data-testid={`settings-general-palette-${opt.id}-swatch-primary`}
                      className="inline-block h-3 w-3 rounded-sm border border-border"
                      style={{ backgroundColor: opt.swatches.primary }}
                    />
                  </span>
                </div>
                <span className="text-[10px] text-muted">{opt.blurb}</span>
                <span className="font-mono text-[10px] text-muted">{opt.id}</span>
              </label>
            );
          })}
        </div>
        {palette !== DEFAULT_PALETTE_ID && (
          <p
            className="text-[10px] text-muted"
            data-testid="settings-general-palette-reset-hint"
          >
            Pick <strong>{NAMED_PALETTES[0].label}</strong> to revert to the shipped baseline.
          </p>
        )}
      </fieldset>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <fieldset className="flex flex-col gap-2 rounded border border-border bg-surface2/30 p-3">
          <legend className="px-1 text-[10px] uppercase tracking-wide text-muted">
            <Languages size={11} className="mr-1 inline" /> Language
          </legend>
          <label className="flex flex-col gap-1">
            <span className="text-muted">Display language</span>
            <select
              data-testid="settings-general-language"
              value={language}
              onChange={(e) => setLanguage(e.target.value as LanguagePref)}
              className="rounded border border-border bg-bg px-2 py-1 text-fg"
            >
              {LANGUAGE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <span className="text-[10px] text-muted">
              Stored locally; UI strings are English-only until i18n bundles ship.
            </span>
          </label>
        </fieldset>

        <fieldset className="flex flex-col gap-2 rounded border border-border bg-surface2/30 p-3">
          <legend className="px-1 text-[10px] uppercase tracking-wide text-muted">
            UI Mode
          </legend>
          <div role="radiogroup" aria-label="Default UI mode" className="flex flex-col gap-1">
            {UI_MODE_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                data-testid={`settings-general-ui-mode-${opt.value}`}
                className="flex items-center gap-2"
              >
                <input
                  type="radio"
                  name="general-ui-mode"
                  value={opt.value}
                  checked={uiMode === opt.value}
                  onChange={() => setUiMode(opt.value)}
                />
                <span className="text-fg">{opt.label}</span>
                <span className="text-[10px] text-muted">{opt.help}</span>
              </label>
            ))}
          </div>
        </fieldset>
      </div>

      <fieldset className="flex flex-col gap-2 rounded border border-border bg-surface2/30 p-3">
        <legend className="px-1 text-[10px] uppercase tracking-wide text-muted">
          Default Dashboard Mode
        </legend>
        <div role="radiogroup" aria-label="Default dashboard mode" className="grid grid-cols-1 gap-1 sm:grid-cols-3 xl:grid-cols-6">
          {DASHBOARD_MODE_OPTIONS.map((opt) => (
            <label
              key={opt.value}
              data-testid={`settings-general-dashboard-mode-${opt.value}`}
              className={[
                "flex cursor-pointer items-center justify-between gap-2 rounded border px-2 py-1.5 text-[11px]",
                dashboardMode === opt.value
                  ? "border-accent-cyan bg-surface2 text-fg"
                  : "border-border text-muted hover:bg-surface2/60 hover:text-fg",
              ].join(" ")}
            >
              <input
                type="radio"
                name="general-dashboard-mode"
                value={opt.value}
                checked={dashboardMode === opt.value}
                onChange={() => setDashboardMode(opt.value)}
                className="sr-only"
              />
              <span className="flex flex-col">
                <span>{opt.label}</span>
                <span className="text-[10px] text-muted">{opt.help}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {status && (
        <div
          role={status.tone === "err" ? "alert" : "status"}
          data-testid="settings-general-status"
          className={[
            "rounded border px-3 py-2 text-[11px]",
            status.tone === "ok" && "border-green-700/50 bg-green-950/30 text-green-200",
            status.tone === "err" && "border-rose-700/50 bg-rose-950/30 text-rose-200",
            status.tone === "info" && "border-cyan-700/50 bg-cyan-950/30 text-cyan-200",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          {status.text}
        </div>
      )}

      <div className="flex items-center justify-end gap-2">
        <span className="text-[10px] text-muted">
          {dirty ? "Unsaved changes." : "All changes saved."}
        </span>
        <button
          type="submit"
          disabled={!dirty || busy}
          data-testid="settings-general-save"
          className="inline-flex items-center gap-1 rounded border border-border bg-surface2 px-3 py-1.5 text-[11px] text-fg hover:bg-surface2/80 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Save size={12} aria-hidden /> {busy ? "Saving…" : "Save preferences"}
        </button>
      </div>
    </form>
  );
}
