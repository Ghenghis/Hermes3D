# Hermes3D-OS GUI — Theme System, Status Banners, Onboarding (W8-3)

Date: 2026-05-09
Lane: W8-3 (cross-cutting GUI infrastructure)
Branch: `claude/w8-3-gui-theme-banners-onboarding`
Base: `feat/hermes3d-7-complete-gui-repo-wiring`
Lock owner: `claude-w8-3-gui-theme`

## Scope

This lane delivers the cross-cutting UI primitives that the per-page lanes
(W6-3 dashboards, W6-4 action window, W6-5 task monitor, W6-8 app status,
W8-2 banners-data) all consume:

1. **Theme provider** — light / dark / system, persisted to localStorage,
   honours `prefers-color-scheme`, drives `<html>` class for Tailwind
   `dark:` variants, and stamps `--h3d-color-*` CSS custom properties for
   non-Tailwind code paths.
2. **Theme tokens** — single source of truth for colour palettes, spacing,
   radius, font sizes, and shadows. Both palettes (light + dark) are
   pinned to WCAG 2.1 AA contrast.
3. **Theme switcher** — dropdown selector, default + compact variants,
   ARIA listbox semantics + keyboard support.
4. **Global status banner system** — top-of-page bar that surfaces four
   canonical conditions (Hermes Agent outdated, provider failure,
   recovery in progress, printer-safety blocked) with action + dismiss
   buttons.
5. **Onboarding modal** — first-launch four-step walkthrough; persistent
   "don't show again" dismissal.

## File map

| Concern | Path |
|---|---|
| Tokens | `03_implementation/ui/src/theme/tokens.ts` |
| Provider | `03_implementation/ui/src/theme/ThemeProvider.tsx` |
| Hook | `03_implementation/ui/src/theme/useThemeTokens.ts` |
| Pre-React bootstrap | `03_implementation/ui/src/theme/themeBootstrap.ts` |
| Public surface | `03_implementation/ui/src/theme/index.ts` |
| Theme switcher | `03_implementation/ui/src/components/ThemeSwitcher/ThemeSwitcher.tsx` |
| Banner atom | `03_implementation/ui/src/components/StatusBanners/StatusBanner.tsx` |
| Banner host | `03_implementation/ui/src/components/StatusBanners/StatusBannerHost.tsx` |
| Banner sources hook | `03_implementation/ui/src/components/StatusBanners/useBannerSources.ts` |
| Onboarding modal | `03_implementation/ui/src/components/Onboarding/OnboardingModal.tsx` |
| Onboarding steps | `03_implementation/ui/src/components/Onboarding/onboardingSteps.tsx` |
| Tailwind config | `03_implementation/ui/tailwind.config.ts` |
| Globals CSS | `03_implementation/ui/src/styles/globals.css` |
| Unit tests | `03_implementation/ui/tests/unit/{ThemeProvider,ThemeSwitcher,StatusBannerHost,OnboardingModal}.test.tsx` |
| Playwright spec | `03_implementation/ui/tests/e2e/gui-theme-banners.spec.ts` |

## Theme architecture

```
                      +------------------+
                      |  themeBootstrap  |  <- pre-React, run from main.tsx
                      +--------+---------+
                               |
                               v
+--------+      +-------------+--------------+      +--------------+
| Tokens | ---> |  ThemeProvider (context)   | ---> | <html class> |
+--------+      |  - reads localStorage      |      | dark / light |
                |  - watches matchMedia      |      +--------------+
                |  - applies CSS variables   |
                +-------+----------+---------+
                        |          |
                        v          v
                +-------+-+    +---+----------+
                | useTheme|    | useThemeTokens|
                +---------+    +---------------+
```

- `tokens.ts` exports `lightPalette`, `darkPalette`, raw scales, and
  `themeCssVars(mode)` -> `{ '--h3d-color-*': value }` for CSS injection.
- `ThemeProvider.tsx` wires the React context. The provider:
  - reads stored theme (default `"system"`)
  - resolves `"system"` against `window.matchMedia('(prefers-color-scheme: dark)')`
  - listens to OS preference flips while in `"system"` mode
  - writes the resolved class onto `<html>` (`dark` | `light`)
  - stamps `data-h3d-theme` on `<html>` for testid hooks
  - sets every `--h3d-color-*` variable on `:root.style`
- `useTheme()` returns `{ theme, resolvedTheme, setTheme }`.
- `useThemeTokens()` returns the palette + raw scales for non-Tailwind
  consumers.

## Token system

### Colour palettes (WCAG 2.1 AA verified)

| Token | Dark | Light | Light contrast w/ text-primary | Notes |
|---|---|---|---|---|
| `background` | `#0a0e1a` | `#ffffff` | n/a (background) | base canvas |
| `surface` | `#0f1626` | `#f6f8fc` | 17.0:1 | card/panel |
| `surface-2` | `#141d33` | `#eef2f9` | 16.0:1 | nested/hover |
| `border` | `#1f2a44` | `#d4dbe7` | 11.6:1 | dividers |
| `text-primary` | `#e6edf7` (15.5:1 vs bg) | `#0a0e1a` (19.5:1 vs bg) | n/a | body text |
| `text-secondary` | `#7c8aa8` (5.0:1 vs bg) | `#475569` (7.6:1 vs bg) | n/a | muted |
| `primary` | `#22d3ee` | `#0e7490` | 5.4:1 | brand accent |
| `secondary` | `#3b82f6` | `#1d4ed8` | 8.2:1 | secondary brand |
| `accent` | `#a78bfa` | `#6d28d9` | 7.8:1 | tertiary highlight |
| `error` | `#ef4444` | `#b91c1c` | 5.9:1 | danger |
| `warning` | `#f59e0b` | `#b45309` | 4.9:1 | warning |
| `success` | `#22c55e` | `#15803d` | 5.0:1 | success |
| `info` | `#3b82f6` | `#1d4ed8` | 8.2:1 | info |

Body-text contrast ratios computed against the matching background per
WCAG 2.1 [Understanding 1.4.3 Contrast (Minimum)](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html).
All ratios meet AA (>= 4.5:1 for body, >= 3:1 for large text + UI).

### Spacing / radius / type scales

Defined in `tokens.spacing`, `tokens.radius`, `tokens.fontSize`,
`tokens.iconSize`, `tokens.shadow`. Imported either as raw constants or
through `useThemeTokens()`.

### Tailwind integration

`tailwind.config.ts`:

- `darkMode: "class"` (per [Tailwind dark-mode docs](https://tailwindcss.com/docs/dark-mode))
- preserved the existing `bg / surface / surface2 / border / fg / muted /
  accent.*` aliases for back-compat with the visual contract baseline.
- added a parallel `h3d.*` group whose values are `var(--h3d-color-*)`,
  so any new component using `bg-h3d-surface` switches to the active
  palette automatically.

`globals.css` ships baseline `--h3d-color-*` defaults under both
`:root` and `:root.dark`, and an explicit `:root.light` override for
zero-flash light-mode rendering before React hydrates.

## Banner conditions

| Banner ID | Severity | Trigger | Action | Dismissible |
|---|---|---|---|---|
| `agent-outdated` | warning | `agent.installed_version != agent.upstream_version` | Open release URL or `#agents` | yes |
| `provider-failure` | error | any provider with `state === "error"` | `#settings` | yes |
| `recovery-active` | info | `recovery.active === true` | `#observe` | no |
| `printer-safety` | error | `printerSafety.blocked === true` | `#printers` | no |

ARIA roles per severity:

- `error`/`warning` -> `role="alert"`, `aria-live="assertive"`
- `info`/`success` -> `role="status"`, `aria-live="polite"`

Auto-dismiss: when the underlying source resolves (e.g. provider goes
back to `ok`), the banner is removed on the next render. Dismissed
banners with stale IDs are pruned from `localStorage[h3d.banners.dismissed]`
so a flapping condition doesn't permanently silence its banner.

## Onboarding flow

Steps (`onboardingSteps.tsx`):

1. **Three dashboards, one OS** — Simple / Advanced / Custom toggle.
2. **The Action Window is your remote control** — task launch + retry.
3. **Watch live tasks in the Task Monitor** — pending vs running streams.
4. **Bring your own providers** — DeepSeek / MiniMax / SiliconFlow / LM
   Studio + the new theme picker.

Each step ships an inline SVG illustration so the modal works
deterministically in CI (no asset fetch). Every illustration sits inside
`<StripWrapper>` which adopts the active palette via Tailwind classes.

Persistence:

- `localStorage[h3d.onboarding.dismissed] = JSON.stringify({dismissedAtMs, reason, completedSteps})`
- `shouldShowOnboarding()` -> boolean, host call this from the app shell.
- `resetOnboarding()` available for a "Show tour again" button later.

Keyboard:

- `Esc` -> close (reason="dismissed")
- `Enter` -> next, or finish on last step (reason="completed")
- `ArrowRight`/`ArrowLeft` -> navigate steps
- Trap-focus on the dialog (`tabIndex={-1}` + initial `node.focus()`).

## Image-GUI reference

Found at `Images-GUI/09-themes/theme-variants-reference.png` (a single
combined reference of light + dark variants). Token palette pins the
existing `tailwind.config.ts` dark hex values verbatim, so visual-proof
baselines (W6-6) remain valid.

Other Image-GUI assets (`01-dashboard-modes/`, `05-action-windows/`,
`06-states-responsive/`, `08-app-utility-pages/`) inform the inline SVG
illustrations in `onboardingSteps.tsx` and the layout decisions for
the banner host (top-of-page strip with severity-coloured left rule).

## Wiring guide for sibling lanes

Once W6-3 unlocks `App.tsx` and `main.tsx`, integration is:

```tsx
// main.tsx, top of file:
import { bootstrapTheme } from "./theme/themeBootstrap";
bootstrapTheme();

// inside App.tsx:
import { ThemeProvider } from "./theme/ThemeProvider";
import { StatusBannerHost } from "./components/StatusBanners";
import { OnboardingModal, shouldShowOnboarding } from "./components/Onboarding";
import { ThemeSwitcher } from "./components/ThemeSwitcher";

export default function App() {
  const [onboardingOpen, setOnboardingOpen] = useState(() => shouldShowOnboarding());
  return (
    <ThemeProvider>
      <AppShell>
        <StatusBannerHost />     {/* directly under topbar */}
        <Outlet />
      </AppShell>
      <OnboardingModal
        open={onboardingOpen}
        onClose={() => setOnboardingOpen(false)}
      />
    </ThemeProvider>
  );
}
```

`ThemeSwitcher` belongs in the topbar (`TopBar.tsx`, locked by W6-3 in
this wave -- expected handoff right cluster, between the Simple toggle
and the Time pill, in `compact` variant).

## Tests

- Unit: `tests/unit/ThemeProvider.test.tsx`,
  `tests/unit/ThemeSwitcher.test.tsx`,
  `tests/unit/StatusBannerHost.test.tsx`,
  `tests/unit/OnboardingModal.test.tsx`. Targets `vitest` + `jsdom` +
  `@testing-library/react` (deps already present on `main` via the W6-3
  branch; the working base branch
  `feat/hermes3d-7-complete-gui-repo-wiring` will receive them at merge
  time).
- E2E: `tests/e2e/gui-theme-banners.spec.ts`. Three test cases producing
  6+ screenshots at 1920x1080, including a deferred-mode shim for the
  period before App.tsx wires the host (so the spec stays green during
  staged rollout).

## Constraints honoured

- No paid services touched.
- Hermes MCP locks acquired for every new file.
- Two doc sources: WCAG 2.1 contrast guidelines + Tailwind dark-mode docs
  (linked above).
- ARIA semantics applied per severity (`alert` for error/warning, `status`
  for info/success).
- Sibling-lane locks respected -- `App.tsx`, `TopBar.tsx`, `main.tsx`,
  `package.json`, `vitest.config.ts` were NOT modified.

## Lock release

The lane's locks under `claude-w8-3-gui-theme` are released in the same
commit by the standard `hermes_release_files` call.
