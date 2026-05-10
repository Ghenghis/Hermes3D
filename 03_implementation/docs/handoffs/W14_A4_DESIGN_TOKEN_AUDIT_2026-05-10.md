# W14 - A4: Design Token Audit (Read-Only)

**Date:** 2026-05-10
**Agent:** Wave 14 - Agent 4 (Design Token Auditor)
**Mode:** READ-ONLY. No token edits. Reference comparison only.

---

## 1. Current Tokens

Sources audited (verbatim):

- `03_implementation/ui/src/theme/tokens.ts` (W8-3 theme system)
- `03_implementation/ui/src/styles/globals.css`
- `03_implementation/ui/tailwind.config.ts`
- `03_implementation/ui/src/app/AppShell.tsx`
- `03_implementation/ui/src/components/layout/TopBar.tsx`
- `03_implementation/ui/src/components/layout/Sidebar.tsx`

### 1.1 Color Palette - Dark (live tailwind.config.ts + tokens.ts)

| Token | Hex | CSS var | Tailwind alias |
|---|---|---|---|
| background | `#0a0e1a` | `--h3d-color-background` | `bg-bg`, `bg-h3d-background` |
| surface | `#0f1626` | `--h3d-color-surface` | `bg-surface`, `bg-h3d-surface` |
| surface2 | `#141d33` | `--h3d-color-surface-2` | `bg-surface2`, `bg-h3d-surface-2` |
| border | `#1f2a44` | `--h3d-color-border` | `border-border`, `border-h3d-border` |
| textPrimary (fg) | `#e6edf7` | `--h3d-color-text-primary` | `text-fg` |
| textSecondary (muted) | `#7c8aa8` | `--h3d-color-text-secondary` | `text-muted` |
| primary (accent.cyan) | `#22d3ee` | `--h3d-color-primary` | `text-accent-cyan` |
| secondary (accent.blue) | `#3b82f6` | `--h3d-color-secondary` | `text-accent-blue` |
| accent (purple) | `#a78bfa` | `--h3d-color-accent` | `text-h3d-accent` |
| error (accent.red) | `#ef4444` | `--h3d-color-error` | `text-accent-red` |
| warning (accent.amber) | `#f59e0b` | `--h3d-color-warning` | `text-accent-amber` |
| success (accent.green) | `#22c55e` | `--h3d-color-success` | `text-accent-green` |
| info | `#3b82f6` | `--h3d-color-info` | `text-h3d-info` |

### 1.2 Color Palette - Light (tokens.ts)

| Token | Hex |
|---|---|
| background | `#ffffff` |
| surface | `#f6f8fc` |
| surface2 | `#eef2f9` |
| border | `#d4dbe7` |
| textPrimary | `#0a0e1a` |
| textSecondary | `#475569` |
| primary | `#0e7490` |
| secondary | `#1d4ed8` |
| accent | `#6d28d9` |
| error | `#b91c1c` |
| warning | `#b45309` |
| success | `#15803d` |
| info | `#1d4ed8` |

### 1.3 Spacing scale (tokens.spacing, px)

`xs=4, sm=8, md=12, lg=16, xl=24, 2xl=32, 3xl=48`

### 1.4 Font sizes (tokens.fontSize)

`xs=11, sm=13, md=15, lg=18, xl=22, 2xl=28` (px)
Body baseline: `font-size: 13px` on `html, body` in `globals.css`.
Font family: `Inter, ui-sans-serif, system-ui, sans-serif` (sans); `JetBrains Mono, ui-monospace, monospace` (mono).

### 1.5 Radius (tokens.radius / tailwind extend)

| Token | Value |
|---|---|
| xs | 4px |
| sm | 6px |
| card | 8px |
| lg | 12px |
| xl | 20px |
| chip | 999px (pill) |

Tailwind extends only `card` and `chip`.

### 1.6 Layout structurals (from components, in CSS px / rem)

| Token | Value | Source |
|---|---|---|
| Sidebar default width | `260px` | `Sidebar.tsx` -> `ResizablePane defaultWidth={260}` |
| Sidebar min width | `200px` | `Sidebar.tsx` -> `minWidth={200}` |
| Sidebar max width | `560px` | `Sidebar.tsx` -> `maxWidth={560}` |
| TopBar min height | `56px` (`min-h-14`) | `TopBar.tsx` |
| TopBar padding | `px-3 py-2` mobile, `md:px-6` desktop | `TopBar.tsx` |
| Main content padding | `p-2.5` (10px) | `AppShell.tsx` |
| Sidebar nav row padding | `px-4 py-2.5` | `Sidebar.tsx` SidebarRow |
| Sidebar header padding | `px-4 py-4` | `Sidebar.tsx` |
| Active row indicator | `border-l-2 border-accent-cyan` | `Sidebar.tsx` |
| Sidebar nav text size | `text-[13px]` | `Sidebar.tsx` |
| Topbar status pill text | `text-xs` (12px) | `TopBar.tsx` |
| Time pill radius | `rounded-chip` (999px) | `TopBar.tsx` TimePill |
| Bell/Gear button radius | `rounded-md` (6px Tailwind default) | `TopBar.tsx` |
| Avatar size | `h-8 w-8` (32x32) | `TopBar.tsx` |
| Glow shadow | `0 0 0 1px rgba(34,211,238,0.18)` | `tokens.ts` |
| Overlay shadow | `0 8px 32px rgba(0,0,0,0.45)` | `tokens.ts` |

**Total tokens in current system: ~58** (13 dark colors + 13 light + 7 spacing + 6 fontSize + 6 radius + 3 iconSize + 2 shadow + 6 chartColors + structurals).

---

## 2. Reference Tokens (sampled from PNGs)

Methodology: PIL `Image.getpixel((x,y))` with dominant-color polling over 50-9000 pixel boxes per region. Multiple regions per token role; medians selected. Layout dims from luma-step-detection in row/column scans. Sources: 7 reference PNGs from `Images-GUI/` (advanced-dashboard-a, advanced-dashboard-b, simple-dashboard-a, custom-dashboard-a, action-window-advanced-tools, action-window-core-apps, theme-variants-reference).

### 2.1 Reference colors (sampled)

| Role | Reference RGB / Hex | Confidence | Sample source |
|---|---|---|---|
| Page background (deep) | `rgb(0,8-12,17-22)` -> ~`#000c14` | HIGH (411 hits at top edge of advanced-dashboard-a; 411/1520 = 27%) | adv-dash-a top edge y=0..3 |
| Sidebar/panel surface | `rgb(1,15-17,25-28)` -> ~`#01101a` | HIGH (1000+ hits across panels) | adv-dash-a panel-A,B,C medians |
| Surface2 (raised card / action-window body) | `rgb(0,20,32)` -> `#001420` | HIGH | action-window body 2216 hits |
| Border / divider (visible at panel top edge) | est. `rgb(14-25,29-37,38-50)` -> ~`#1a2230..#19232e` | MED (visible as luma-step at panel top edge) | luma-step at y=158-162 of card |
| Text-primary (sidebar/topbar text) | white-grey ~`rgb(210-240,210-240,210-240)` -> ~`#d2d4d8` | HIGH | topbar text glyphs y=20 |
| Text-secondary | dim grey ~`rgb(110,120,128)` -> `#6f7780` | MED | dim text glyphs in sidebar gaps |
| Accent-green (VERIFIED badge / success) | `rgb(42-50,170-187,80-110)` -> ~`#2aad4c..#32ae55` | HIGH (123 hits in default-dark cell) | theme-variants cell 1 |
| Accent-blue (button/badge) | `rgb(40-60,120-130,217-244)` -> ~`#3b80f4` | HIGH (206 cluster hits) | adv-dash-a accent hunt |
| Accent-amber (warning/orange) | `rgb(214-243,131-163,22-90)` -> ~`#f3821b` | HIGH (78 hits) | adv-dash-a accent hunt |
| Accent-red (error) | `rgb(210-252,58-95,53-77)` -> ~`#e23a35..#fc564c` | MED (4 distinct hits, image has few error states) | adv-dash-a |
| Accent-cyan (active highlight) | `rgb(76,153,251)` -> sparse, only 3 hits | LOW (cyan likely under-represented in this single image; dominant accent is BLUE) | adv-dash-a |

### 2.2 Reference layout dims (measured)

| Token | Reference | Confidence | Method |
|---|---|---|---|
| Image canvas | 1536x1024 (most), 1672x941 (simple-dash-a) | HIGH | PIL `.size` |
| TopBar height | **56 px** | HIGH | luma-step at y=56-57 in adv-dash-a (col x=600 clear) |
| Sidebar width | **~183 px** in 1536-wide image -> ratio 11.9% (== 183/1536); for a 1280-wide app that scales to **~152 px**, for 1920 -> **~228 px** | HIGH | luma-step at x=183 in adv-dash-a y=720..820 |
| Card border-radius (action-window outer) | ~6 px | MED | corner arc spans 6 px diagonal in action-window-core-apps top-left |
| Card border-radius (panel inner) | ~4-6 px | MED | top-left arc of panel at (185,158) shows 2-3 px arc |
| Sidebar nav row pitch | ~36 px | HIGH | text-band starts every 35-36 px y in adv-dash-a col x=70 |
| Sidebar nav text height | ~7-9 px glyph cap-height | HIGH | -> ~13 px font-size (matches current `text-[13px]`) |
| Action-window standalone size | ~768x512 cell in 2x2 1536x1024 mosaic; matches **1024x768** at 75% scale OR native 768x512 | MED | 2x2 grid splits exactly at x=768, y=512 |
| Inter-window gutter | ~3 px | HIGH | gap at x=765-768 only 3 px wide |

### 2.3 Reference typography

- Cannot extract specific font name from PNG. Cap-heights and stroke widths are consistent with **Inter** (already in tokens) or any modern grotesque sans (Geist, IBM Plex). No mismatch flagged.
- Body text size: estimated 13 px (matches current `font-size: 13px` baseline).
- Header/title: ~16-18 px in topbar branding. Matches current `text-base` (16 px).

---

## 3. Token Delta Table

| # | Token | Current | Reference | Delta | Impact |
|---|---|---|---|---|---|
| 1 | **background** | `#0a0e1a` (rgb 10,14,26) | `#000c14` (rgb 0,12,20) | -10 / -2 / -6 (current is slightly bluer + lighter) | LOW. Visual diff <4% per channel; both register as "near-black deep navy". Acceptable as-is. |
| 2 | **surface (panel)** | `#0f1626` (rgb 15,22,38) | `#01101a` (rgb 1,16,26) | -14 / -6 / -12 (current ~30% lighter and more saturated blue) | MED. Current panels look slightly brighter than reference. Reduces contrast against background by ~50%. |
| 3 | **surface2** | `#141d33` (rgb 20,29,51) | `#001420` (rgb 0,20,32) | -20 / -9 / -19 (current is much lighter + bluer) | MED. Used for card hover/raised state; visual diff is noticeable. |
| 4 | **border** | `#1f2a44` (rgb 31,42,68) | est. `#19232e` (rgb 25,35,46) | -6 / -7 / -22 (current is bluer) | LOW-MED. Border visibility slightly higher in current; reference borders are more neutral. |
| 5 | **textPrimary** | `#e6edf7` (rgb 230,237,247) | `#d2d4d8` (rgb 210,212,216) | +20 / +25 / +31 (current is brighter, bluer-cool) | LOW. Both pass WCAG AA 4.5:1 against bg; current is higher-contrast. |
| 6 | **textSecondary** | `#7c8aa8` (rgb 124,138,168) | `#6f7780` (rgb 111,119,128) | +13 / +19 / +40 (current is bluer) | LOW. WCAG: current ~5.1:1 contrast, ref ~4.4:1; current safer. |
| 7 | **primary (cyan)** | `#22d3ee` (rgb 34,211,238) | sparse, blue-dominant `#3b80f4` (rgb 59,128,244) | -25 / +83 / -6 | **HIGH-INFO**. Reference shows **blue-not-cyan** as the dominant interactive accent. Current has cyan as primary; this is a brand-direction question, not just a hex shift. |
| 8 | **secondary (blue)** | `#3b82f6` (rgb 59,130,246) | `#3b80f4` (rgb 59,128,244) | -0 / +2 / +2 | NONE. Match within 1%. |
| 9 | **success (green)** | `#22c55e` (rgb 34,197,94) | `#2aad4c` (rgb 42,173,76) | -8 / +24 / +18 (current is brighter / more vivid) | LOW. Both pass color recognition; current is a touch more saturated. |
| 10 | **warning (amber)** | `#f59e0b` (rgb 245,158,11) | `#f3821b` (rgb 243,130,27) | +2 / +28 / -16 (current is more yellow, ref more orange) | LOW. Both register as "amber/orange". |
| 11 | **error (red)** | `#ef4444` (rgb 239,68,68) | `#e23a35` (rgb 226,58,53) | +13 / +10 / +15 (current is slightly pinker) | LOW. Within tolerance. |
| 12 | **accent (purple)** | `#a78bfa` (rgb 167,139,250) | not visible in dark-cell sample (no purple hits) | unknown | UNVERIFIED. Recommend keep current; theme-variants cell may include purple in cyberpunk/synthwave variants but not sampled. |
| 13 | **Sidebar default width** | `260 px` (Sidebar.tsx defaultWidth) | ~183/1536 = 11.9% of viewport. At common 1280 viewport: **~152 px**. At 1920: **~228 px** | -32 (at 1920) / -108 (at 1280) | **HIGH**. Current default is too wide for typical 1280-1440 displays. Reference uses ~12% of width; current uses ~14-20%. Recommend defaultWidth=200 for parity (still within current minWidth=200). |
| 14 | **TopBar min height** | `min-h-14` = 56 px | 56 px | 0 | **MATCH**. No change. |
| 15 | **Card border-radius** | `card=8px` | ~6 px (action-window outer); ~4-6 px (panels) | -2 to -4 | LOW-MED. User spec ("appears ~6px") confirms reference. Current 8px is slightly softer. |
| 16 | **Border-radius `sm`** | `6 px` | matches reference | 0 | MATCH. |
| 17 | **Body font-size** | 13 px (`html,body`) | ~13 px estimated | 0 | MATCH. |
| 18 | **Sidebar nav row pitch** | text + py-2.5 = ~36 px (13+10+10+~3 line) | 35-36 px sampled | 0 | MATCH. |
| 19 | **Glow shadow** | `0 0 0 1px rgba(34,211,238,0.18)` | not directly sampleable; current relies on cyan primary | dependent on #7 | LOW. If primary moves to blue per #7, recompute glow with blue rgba. |
| 20 | **Action window dims** | not in tokens (window manager owns) | ~1024x768 (4:3), or 768x512 cell at 75% | new token candidate | INFO. Reference suggests ~1024x768 native action-window canvas. Currently action-window-detached.tsx exists; not parameterized via tokens. |

**Tokens with non-trivial delta vs reference: 8 of 20** (#1, #2, #3, #4, #7, #13, #15, #20).
**MATCH or trivial: 12 of 20.**

### 3.1 Top 5 deltas

| Rank | Token | Current | Reference | Delta magnitude |
|---|---|---|---|---|
| 1 | primary | `#22d3ee` (cyan) | `#3b80f4` (blue) | Hue shift, **brand-level** |
| 2 | Sidebar default width | 260 px | ~152-228 px (viewport-dependent) | -32 to -108 px |
| 3 | surface2 | `#141d33` | `#001420` | RGB delta = (-20,-9,-19) |
| 4 | surface | `#0f1626` | `#01101a` | RGB delta = (-14,-6,-12) |
| 5 | Card border-radius | 8 px | ~6 px | -2 px |

---

## 4. Implementation Plan (READ-ONLY audit; not executed)

### 4.1 CSS variable updates (low-risk, single file)

Edit `03_implementation/ui/src/styles/globals.css` and `03_implementation/ui/src/theme/tokens.ts` together (they must stay in sync per the W8-3 contract):

- `--h3d-color-background` -> `#000c14` (was `#0a0e1a`)
- `--h3d-color-surface` -> `#01101a` (was `#0f1626`)
- `--h3d-color-surface-2` -> `#001420` (was `#141d33`)
- `--h3d-color-border` -> `#19232e` (was `#1f2a44`)
- `--h3d-color-success` -> `#2aad4c` (was `#22c55e`) [optional, low-impact]
- `--h3d-color-warning` -> `#f3821b` (was `#f59e0b`) [optional, low-impact]

WCAG check required after change: every fg/bg pair must remain >= 4.5:1 for body text. Updated bg `#000c14` is darker so contrast actually IMPROVES against `#e6edf7` text (>15:1).

### 4.2 Tailwind theme extension changes

`03_implementation/ui/tailwind.config.ts` `theme.extend.colors` currently hardcodes the dark hex values. Two options:

- **Option A (recommended):** Replace the hardcoded `bg`, `surface`, `surface2`, `border` values with the new hexes; keep `h3d.*` group reading CSS vars.
- **Option B:** Drop the hardcoded aliases entirely and migrate all components from `bg-bg` -> `bg-h3d-background` (single source of truth = CSS vars). Larger blast radius (Sidebar.tsx, TopBar.tsx, every panel).

`borderRadius.card`: change from `8px` -> `6px` to match reference. Or add `borderRadius.panel: 6px` and migrate `rounded-card` usages selectively. **Search blast radius:** rg `rounded-card` across `src/`.

### 4.3 Component-level structural changes

| Change | File | Impact |
|---|---|---|
| `defaultWidth={260}` -> `defaultWidth={200}` | `src/components/layout/Sidebar.tsx:14` | Persisted user widths in localStorage (`h3d.mainSidebar.width`) override; only affects fresh users. Safe. |
| Verify `min-h-14` topbar matches 56 px | `src/components/layout/TopBar.tsx:57` | Already matches. No change. |
| Decide on primary cyan vs blue | tokens.ts dark + light | If switching, also update `box-shadow.glow`, `accent-cyan` Tailwind alias, and active-state `border-accent-cyan` in Sidebar.tsx. **Brand-level decision; recommend keeping cyan for v0.x and revisiting in v1.** |

### 4.4 Out-of-scope for token audit (note for downstream)

- Action-window canvas dims (~1024x768) are not in `tokens.ts`; if standardisation desired, add `tokens.layout.actionWindow = { width: 1024, height: 768 }` and consume in `action-window-detached.tsx`.
- Theme-variants cells beyond default-dark were sampled superficially; cyberpunk/matrix/tron/synthwave specific accents would need a per-theme variant audit (out of W14-A4 scope).

---

## 5. Sampling Methodology

### 5.1 Images sampled

| Image | Path | Used for |
|---|---|---|
| advanced-dashboard-a.png | `Images-GUI/01-dashboard-modes/` | Primary source for bg, sidebar, topbar, panel, accent |
| advanced-dashboard-b.png | `Images-GUI/01-dashboard-modes/` | Cross-check (not exhaustively sampled, similar palette) |
| simple-dashboard-a.png | `Images-GUI/01-dashboard-modes/` | Cross-check bg/sidebar (1672x941 variant) |
| custom-dashboard-a.png | `Images-GUI/01-dashboard-modes/` | Cross-check (similar) |
| action-window-advanced-tools.png | `Images-GUI/05-action-windows/` | Action window dims, surface2 (body color) |
| action-window-core-apps.png | `Images-GUI/05-action-windows/` | Action window corner radius (~6 px) |
| theme-variants-reference.png | `Images-GUI/09-themes/` | Default-dark cell isolation, accent green/amber confirmation |

### 5.2 Pixel coordinates and rationale

| Region | Coords | Rationale |
|---|---|---|
| Page background | (10..1525, 0..3) row | Outer frame: only the page bg sits here; topbar starts at y>=4. |
| Sidebar bg | (0..30, 200..900) col strip | Left margin column inside sidebar but past logo and before bottom drawer. |
| Topbar bg | (250..1100, 4..22) | Wide horizontal band inside topbar but below the 1-2 px outer pad and above text glyphs. |
| Card panel A | (200..350, 170..250) box | Center of a top metric tile, away from text. |
| Card panel B | (1080..1250, 200..360) box | Right-side card body. |
| Card panel C | (450..700, 600..750) box | Center-bottom card. |
| Card panel D | (1330..1500, 600..800) box | Action window region (raised surface2). |
| Gutter (between panels) | (770..790, 220..380) col | Vertical gutter between left-half and right-half cards. |
| Border-vertical | (140..145, 200..800) col | Sidebar->main divider zone. |

### 5.3 Layout-edge detection

- **Sidebar right edge:** scan each x=0..320, take median luma over y=720..820 (clear of nav text rows). Step at x=183 (delta -20.2 from x=173) -> sidebar width = 183 px in 1536 image = 11.9% of viewport.
- **Topbar bottom edge:** scan each y=0..100, take median luma over x=400..900 (clear of right-cluster icons and left brand text). Step at y=56-57 (delta -19.7) -> topbar height = 56 px.
- **Corner radius:** at suspected card top-left (185, 158) and action-window top-left (0,0), trace `#`/`.` mask at L>30. Action window: 6-pixel diagonal arc -> ~6 px radius. Panel: 2-3 pixel arc -> 4-6 px radius (less precise due to lower-contrast border).
- **Sidebar nav row pitch:** at x=70, find runs of L>25; row starts repeat every 35-36 px.

### 5.4 Confidence flags

- **HIGH:** Background, surface, action-window body, accent-green, accent-amber, sidebar width, topbar height, nav row pitch, body font-size match.
- **MED:** Border, surface2 saturation, card radius, accent-red.
- **LOW / UNVERIFIED:** Accent-cyan (only 3 hits in adv-dash-a; image is blue-dominant so cyan may be under-represented or the brand truly is moving toward blue), accent-purple (no purple region sampled cleanly).
- **Honest caveat:** Reference PNGs are 1536x1024 raster art; subpixel anti-aliasing means sampled hex values vary +/-3 per channel. Median-of-box smoothing reduces but does not eliminate this.

---

## 6. Sources

1. **WCAG 2.1 — Contrast (Minimum)** — Success Criterion 1.4.3 (Level AA): >=4.5:1 for normal text, >=3:1 for large text (>=18 pt or >=14 pt bold). https://www.w3.org/TR/WCAG21/#contrast-minimum
2. **Tailwind CSS — Theme Configuration / `theme.extend`** — official guidance on extending the default theme without overriding it, and on referencing CSS variables (`var(--token)`) inside Tailwind theme values for runtime token swaps. https://tailwindcss.com/docs/theme

---

## 7. Constraints satisfied

- READ-ONLY: no edits made to `tokens.ts`, `globals.css`, `tailwind.config.ts`, or any component.
- No secrets read or referenced.
- Honest confidence labels: HIGH / MED / LOW / UNVERIFIED.
- Free / open-source tooling only (PIL/Pillow, Python 3.14).
