# HANDOFF_TO_CODEX — SOTA Marketing Site + README v2 (B5)

> **Status:** READY for Codex pickup after B2 / B3 / B4 ship and v5.3.0 is tagged.
>
> **Sequence position:** B5 in the queue. Picks up after B4 (local-secrets backup) merges.
>
> **Owner:** `codex-impl-04` (NOT -03 — that owner is reserved for B1/B2/B3/B4).
>
> **Scope:** enhance, expand, and SOTA-ize the marketing landing page (`site/`) + repo `README.md` to be a real e2e showoff of what Hermes3D-OS does. The user has explicitly requested **Codex's design instincts** — you have full creative latitude. The current v1 in PR #25 is your baseline; rewrite or replace any of it.
>
> The user has rotated all exposed tokens and wants this to be the artifact that makes someone visit the page and say "I need this."

---

## 0. Pre-flight

```text
hermes_doctor                          confirm ok=true
hermes_get_state                       confirm no codex-impl-04 locks
hermes_pick_task
  owner=codex-impl-04
  prefer_task_id=H3D-SOTA-MARKETING-V2
```

Branch: `feat/sota-marketing-v2` from `develop` (after B4 merges).

---

## 1. Architect's already-completed research — DO NOT redo this

Claude ran a 10-agent parallel research + audit pass before writing this brief. The findings are baked into §3 / §4 / §5 below. **You don't need to re-research the topics already covered here.** You may spawn your own research agents for *additional* angles (e.g., specific R3F implementation patterns, specific Awwwards 2026 references, specific gcode visualization libs you want to compare) but don't redo the broad-strokes work.

### Already-researched (use these conclusions, don't rediscover):

**2026 SOTA marketing-page idiom** (Agent #5 findings):
- WebGL is back, but cinematic and quiet. **R3F + drei + GSAP ScrollTrigger** is the canonical 2026 stack
- **Aceternity UI + shadcn + Motion (Framer)** for chrome (typewriters, magnetic buttons, beam backgrounds)
- **CSS View Transitions API** for navigation (2-3× perceived speed)
- **Type-as-product:** oversized variable fonts (Geist Mono, JetBrains Mono variable, Inter Display) carrying the hero
- **Anti-patterns to avoid:** bento grid hero (template-y in 2026), glassmorphism, generic AI B-roll, Lottie loops as hero centerpiece, "trusted by" logo bars above the fold

**3D-printing-native visual idioms** (Agent #8 findings):
- **`gcode-preview`** (xyz-tools, npm) — 80KB, TS-native, supports tube geometry, multi-color, G2/G3 arcs, PrusaSlicer thumbnails. Best 2026 lib for gcode visualization
- **`@google/model-viewer`** — 150KB web component, drop-in `<model-viewer src="x.glb" auto-rotate>` for STL/GLB embeds
- **R3F + drei** — for custom scenes (clipping planes, shaders, scroll-tied animation)
- **`gabotechs/react-stl-viewer`** — opinionated React STL wrapper
- **The killer Hermes-specific effect:** `Material.clippingPlanes` in three.js with animated `plane.constant` produces "growing layer-by-layer" reveal — single most "3D printing" effect on the web
- **Visual language:** macro shots of layer lines under raking light · hot-end orange glow at nozzle · saturated single-color hero models on dark backgrounds (NOT corporate-CAD gray) · PEI gold / garolite tan / glass build-plate textures

**README idiom in 2026** (Agent #6 findings):
- Theme-aware images via `<picture>` + `<source media>` (preferred) or URL fragment `#gh-dark-mode-only`
- Animated SMIL SVG > GIF (GitHub `<video>` tag does NOT render in READMEs, only issues/PRs)
- VHS tape recordings (charmbracelet/vhs) for CLI demos — `.tape` files render to GIF/MP4/WebM
- Mermaid fenced blocks render natively
- `<details>` / `<summary>` accordions universally supported, no JS
- **What does NOT work in READMEs:** inline `<style>`, custom CSS classes, JS, `<iframe>`, autoplay `<video>`, CSS `transform`/`filter` on `<img>` (stripped). Drop-shadows must be **baked** into the image via SVG `<filter><feDropShadow/></filter>` or pre-composited PNG.

**Reference set worth studying:**
- Dev-tool tier: Linear, Raycast, Vercel, Bun, Tauri, Astro, Cursor, Modal, Anthropic, Replit Agent 3, Devin
- 3D-printing tier: Bambu Studio (esp. their Color Mixer Studio interactive RGB-mix), OrcaSlicer, PrusaSlicer (embedded G-code viewer), OctoEverywhere, Obico (failure-detection before/after slider)
- README tier: charmbracelet/vhs, Scalar, biomejs/biome, withastro/astro, oven-sh/bun, open-webui/open-webui, ollama/ollama, SoftFever/OrcaSlicer, mainsail-crew/mainsail, Klipper3d/klipper, zed-industries/zed

**Three opinionated hero concepts** (Agents #5 + #8 converged):
- **Concept A (recommended):** "The Print Builds Itself While You Read" — full-bleed R3F canvas, hero STL prints itself layer-by-layer via animated clippingPlanes rising, GSAP ScrollTrigger pinned to headline. At ~50% scroll a slice plane sweeps and the model splits into colored toolpath segments (using `gcode-preview` rendered into the same canvas). At 100% the model "explodes" into the four Hermes surfaces (truth gate · organizer · pipeline · autonomous mode) as labeled chips. **~250KB gzipped, <1.5s render.**
- **Concept B:** "Toolpath Calligraphy" — looping `gcode-preview` drawing complex single-layer pattern (gyroid, lightning, or logo) line-by-line in saturated color on dark bg. ~120KB total.
- **Concept C:** "Live Print-Farm Wall" — grid of 6-9 fake printer cards with rotating GLB thumbnails (`<model-viewer>` per card, staggered auto-rotate), faux progress bars, status pills. Communicates orchestration multi-printer scale.

**Recommendation: A as hero, B as a scrolled-into section, C as the "what Hermes does" proof slot.** The user has confirmed they want SOTA / "real showoff." Concept A is the play.

**Performance discipline locked in:**
- IntersectionObserver-mount the canvas (40-70% initial-weight reduction)
- Static PNG poster fallback for `prefers-reduced-motion: reduce`
- Draco + KTX2 asset compression
- Target <100 draw calls, <200KB initial bundle gzipped, <2s full scene on 4G
- Hero LCP via `fetchpriority="high"` PNG poster, defer canvas mount until after LCP

---

## 2. Your baseline — site v1 (PR #25, will be merged before you start)

The current `site/` directory contains a v1 marketing pass Claude wrote. **Treat it as raw material. Replace, expand, or rewrite anything.** Specifically:

**v1 already includes** (use as-is OR enhance):
- `site/index.html` — full landing page with hero, 8 sections, install, releases, deploy, governance, footer (~420 lines)
- `site/css/styles.css` — dark Hermes design system (token-driven, ~640 lines, prefers-reduced-motion safe, mobile responsive)
- `site/js/app.js` — vanilla JS scroll-reveal + stat counters + terminal typewriter + screenshot lazy-swap + GH Releases auto-fetch (~280 lines)
- `site/diagrams/pipeline-9-stage.svg` — animated 9-stage pipeline (SMIL, WCAG 2.2 AA)
- `site/diagrams/truth-gate-verification.svg` — animated 6-check verification flow with signed envelope (SMIL, WCAG 2.2 AA)
- `site/diagrams/print-farm-orchestration.svg` — animated dispatcher → selected printer + parallel jobs (SMIL, WCAG 2.2 AA)
- `site/diagrams/mcp-coordination.svg` — animated 6-client MCP coordination (Claude · Codex · Cursor · Windsurf · VS Code Copilot · Kilo Code) (SMIL, WCAG 2.2 AA)
- `.github/workflows/pages.yml` — GH Pages deploy workflow (SHA-pinned, deploys on push to develop when site/ changes)

**v1 deliberately does NOT include** (your job to add):

| Missing | What's needed |
|---|---|
| **R3F hero scene** | Concept A — Benchy/Octocat/gear self-printing layer-by-layer, GSAP ScrollTrigger driven, ~250KB. Replaces the CSS-only "layer-stack" placeholder hero |
| **gcode visualization section** | Concept B — looping `gcode-preview` calligraphy showing toolpath for a curated 200-line gcode file. Mid-page section |
| **Live print-farm wall** | Concept C — 9 `<model-viewer>` cards in a grid with staggered rotation, faux progress bars, status pills |
| **Real screenshots** | All 22 screenshot slots are wired with `data-src` lazy-swap — capture them once Hermes3D runs locally and drop PNGs into `site/screenshots/` |
| **VHS-recorded CLI demo** | `.tape` script for `charmbracelet/vhs` showing `hermes3d truth-gate ./mymesh.stl → dispatch → proof verify` flow. Render to GIF (≤5MB) and MP4. Render hosted under `site/demos/` |
| **Mermaid diagrams** (README) | At least one `flowchart LR` of the pipeline at the top of README, native render |
| **Light theme variant** | Currently dark-only. Theme-aware via `<picture>` + prefers-color-scheme |
| **i18n hook** | Not required for v2, but consider structure that allows future translation |
| **Interactive truth-gate try-it form** | Stretch goal — embed an STL upload that runs analyze_mesh client-side via WebAssembly trimesh and shows the verdict matrix. Defer if scope grows |
| **Theme-aware logos / favicons** | `site/favicon.svg` + `site/favicon-light.svg` + `apple-touch-icon.png` |

**README v2** — Claude drafted a v2 in PR #25 but the user reverted it. The current `README.md` on develop is the dev-internal version. **Your job: write a NEW README v2 with Codex's design instincts**, keeping the dev-internal content accessible (in `<details>` accordions, or moved to `CONTRIBUTING.md` — your call). The user explicitly said they prefer your README design quality.

---

## 3. Authorization to spawn additional research agents

You have explicit authorization to use parallel agent research for any specific topic Claude's prior 10-agent pass didn't cover. Examples:

- Specific R3F + GSAP ScrollTrigger code patterns for the layer-clipping effect
- Specific Awwwards 2026 / Codrops articles published since the brief was written
- Specific maker-community visual references (Printables, /r/3Dprinting trending)
- Specific accessibility patterns for animated 3D content (WCAG 2.2 AA for WebGL is still maturing)
- Specific CDN strategies for shipping R3F to GH Pages without a build step
- Specific VHS tape script patterns for 3D-printing-OS CLI demos

**Do NOT spawn agents for:**
- General "what makes a marketing page good in 2026" — already covered
- General "what should a 3D-printing OS marketing page look like" — already covered
- General README idioms — already covered
- The reference set of 17 sites — already covered

If a research agent finds a 2026-current technique that contradicts something in §1, follow the new evidence and note the change in your PR description.

---

## 4. Lock list (broad — you own the marketing surface)

Marketing site is naturally large scope. Lock the entire marketing surface; CP5.1-E and B1/B2/B3/B4 are scope-disjoint (different directories).

```text
hermes_lock_files
  owner=codex-impl-04
  taskId=H3D-SOTA-MARKETING-V2
  ttlMinutes=240
  files=[
    "README.md",
    "site/index.html",
    "site/css/styles.css",
    "site/js/app.js",
    "site/diagrams/pipeline-9-stage.svg",
    "site/diagrams/truth-gate-verification.svg",
    "site/diagrams/print-farm-orchestration.svg",
    "site/diagrams/mcp-coordination.svg",
    "site/screenshots/.gitkeep",
    "site/demos/.gitkeep",
    "site/favicon.svg",
    "site/favicon-light.svg",
    "site/apple-touch-icon.png",
    "site/robots.txt",
    "site/sitemap.xml",
    ".github/workflows/pages.yml",
    "CONTRIBUTING.md"
  ]
```

If you decide to add a new file outside this list (e.g., `site/js/r3f-hero.js`, `site/data/hero-mesh.glb`, `site/demos/quickstart.tape`, `site/demos/quickstart.gif`, `site/css/light-theme.css`, etc.), update the lock list in your task before adding it.

**DO NOT touch anything outside `site/` or `README.md` or `CONTRIBUTING.md` or `.github/workflows/pages.yml`.** The implementation tree (`03_implementation/`, `04_testing/`, `00_overview/`, `02_architecture/`, `06_release/`) is entirely off-limits.

---

## 5. Implementation contract — the experience to build

You have full creative latitude on **how**. The **what** is:

### 5.1 Hero (Concept A — recommended)

When a visitor lands on `ghenghis.github.io/Hermes3D/`, in the first 3 seconds they should:

1. See a 3D model **printing itself** in real time, layer by layer — visible nozzle, hot-end orange glow at the active layer, build-plate texture
2. Read a tagline that's punchy enough to make them scroll: "An operating system for your print farm." (current v1) — or whatever you decide is sharper
3. See pills/badges that state the surface area (24 MCP tools, 17 truth gates, 77 real features)
4. Scroll, and the model should respond — slice plane sweeps, model shows toolpath colors, finally explodes into the four product surfaces as chips

**Stack candidates:** R3F (`@react-three/fiber` + `@react-three/drei`) + GSAP ScrollTrigger via CDN imports. No build step required (GitHub Pages serves static). Use `<script type="module">` and `import { ... } from "https://esm.sh/..."` if you need it. OR — if you want a build step, add Astro or Vite with the GH Pages workflow doing the build. Your call.

**Performance budget:** initial JS gzipped < 200KB, full scene load < 2s on 4G, IntersectionObserver-mount, static PNG poster fallback for `prefers-reduced-motion`. Lighthouse mobile score ≥ 92 for performance, ≥ 95 for accessibility.

### 5.2 Pipeline + Truth Gate + Print Farm + MCP sections

The v1 SVGs are usable as-is, but you may upgrade them. Worth considering:

- Replace static SVG with R3F + drei `<Stage>` for the print farm (live rotating GLB thumbnails per card, instead of static text cards)
- Add a Mermaid `flowchart LR` block under each section header for accessibility (works without JS, screen-reader friendly)
- Add scroll-pinned text-reveal for each step in the pipeline (GSAP ScrollTrigger)
- Add the killer effect: when scrolling past the truth-gate section, briefly highlight which check is "active" with a synced glow

### 5.3 Live launcher tour (currently screenshot slots)

Once the user runs Hermes3D locally and captures the 22 screenshots, the v1 JS lazy-swap will populate them automatically. **Don't block on screenshots.** Ship with placeholder slots that gracefully populate later.

For each Gradio tab and React route, the slot should:
- Show a styled placeholder until the PNG exists (current v1 does this)
- Lazy-load the real image when present (current v1 does this)
- On hover (desktop) or tap (mobile), zoom to a higher-res version OR open a lightbox

**Stretch goal:** embed a hosted iframe of an actual running Hermes3D instance on the marketing site (a read-only demo). Out of scope for B5 — defer.

### 5.4 CLI terminal section

The v1 has a vanilla-JS typewriter showing real CLI verbs. Upgrades worth considering:

- Replace with VHS-rendered GIF (charmbracelet/vhs) for pixel-perfect, deterministic, fast-loading playback
- Author the `.tape` file at `site/demos/quickstart.tape`. CI workflow renders to `site/demos/quickstart.gif` (≤5MB) and `quickstart.mp4`. Wire the `<picture>` element to use mp4 where supported.
- Cap GIF at 12 seconds, ~3MB target, looped

### 5.5 Releases section

Currently fetches from GitHub API and renders top 3 releases with asset table. Keep this. Possibly:
- Add download counter (GitHub API exposes `download_count` per asset)
- Add platform-specific recommendations (detect OS via `navigator.userAgent`, show the matching binary first)
- Add SBOM / Sigstore badge per release showing verified

### 5.6 Deploy story section

Current v1 has an ASCII topology diagram. Upgrade options:
- Animated SVG showing data flowing across Tailscale tailnet (similar shape to the existing 4 SVGs)
- A live cost calculator: "your fleet of N printers + M models running on your gaming PC = $X/month for VPS + $Y for B2 backup"
- Comparison table: HermesProof topology vs Bambu Cloud vs OctoEverywhere on (privacy / inference cost / vendor lock-in)

### 5.7 README v2

Your README design instincts are the explicit reason the user is asking you for this. Suggested skeleton (your call to depart):

1. Theme-aware logo via `<picture>` + 2-row badge constellation
2. Hero shot — wide product screenshot with drop-shadow baked in via SVG filter (CSS effects are stripped by GitHub)
3. 30-second pitch — 3 bold bullets
4. Mermaid `flowchart LR` of the 9-stage pipeline
5. VHS-generated GIF of the CLI doing a real lock+gate cycle
6. Install — fenced code per platform, one-liner each
7. Release downloads — table linking latest .msi/.dmg/.zip with size + sha
8. **Truth-gate proof accordion** — `<details>` block listing all 17 gates. Differentiator no other 3D-printing OS README has.
9. Customization gallery — 3-column `<table>` of screenshots
10. Composes-with — peer-MCP-server table
11. Self-host — VPS topology
12. Contributing — `<details>` with gitflow + CI gate map (preserves current dev-internal content)
13. License

Or completely your own structure. Just hit the "convince a viewer in 30 seconds" goal.

---

## 6. Tests + gates

```text
hermes_run_gate gateId=git-status      cwd=.
hermes_run_gate gateId=git-diff-check  cwd=.
```

Local validation:

- `xmllint --noout site/diagrams/*.svg` — all SVGs parse
- `python -c "import yaml; yaml.safe_load(open('.github/workflows/pages.yml'))"` — workflow valid
- `npx --yes html-validate site/index.html` — HTML5 valid
- `npx --yes pa11y-ci --sitemap site/sitemap.xml` — accessibility (or run pa11y on site/index.html if no sitemap yet)
- Lighthouse via `npx --yes @lhci/cli@0.13.x autorun --collect.url=http://localhost:8080` — performance ≥ 92, accessibility ≥ 95
- VHS tape (if shipped): `vhs site/demos/quickstart.tape` produces `site/demos/quickstart.gif` < 5MB
- prefers-reduced-motion smoke: emulate via DevTools, every animation should still be visible (just instant) and no element should be hidden

Add an optional CI job `layer-l-marketing-lint` (advisory, ubuntu-latest, runs on PR open against develop):
- HTML5 validation
- pa11y accessibility scan
- Lighthouse perf + a11y thresholds
- Image weight budget (< 1MB total per page load)

---

## 7. Done criteria

- [ ] R3F (or equivalent) hero scene shipped with prefers-reduced-motion fallback
- [ ] At least one of {gcode-preview section, live print-farm wall} shipped
- [ ] All 4 existing animated SVGs preserved or upgraded (don't regress accessibility)
- [ ] README v2 shipped with embedded animated SVG hero + Mermaid pipeline + truth-gate proof accordion
- [ ] VHS-rendered CLI demo at `site/demos/quickstart.gif`
- [ ] Theme-aware logos + favicons (`<picture>` swap)
- [ ] Light theme variant for the site (prefers-color-scheme)
- [ ] Lighthouse mobile: performance ≥ 92, accessibility ≥ 95
- [ ] Initial JS gzipped < 200KB
- [ ] All 4 SVGs WCAG 2.2 AA compliant (already are; preserve)
- [ ] All animations honor prefers-reduced-motion
- [ ] Screenshot slots remain wired for lazy-swap (so future PNG drops auto-populate)
- [ ] No new dependencies committed to `package.json` for the marketing site (CDN imports OK)
- [ ] All 17 lock list files (or whatever subset you used) committed
- [ ] PR body includes "Hermes evidence chain: PASS" + task id + at least one gate run
- [ ] CI green: Layer A + the new optional layer-l-marketing-lint
- [ ] No file outside §4 lock list modified

---

## 8. PR + close-out

```bash
git push -u origin feat/sota-marketing-v2
gh pr create --base develop \
  --title "feat(marketing): SOTA site + README v2 — R3F hero, gcode toolpath, VHS demo, theme-aware" \
  --body "[mirror PR #25 body shape; Hermes evidence chain: PASS; Task: H3D-SOTA-MARKETING-V2; Gate run via hermes_run_gate]"
```

Close-out:

```text
hermes_append_evidence
  owner=codex-impl-04
  taskId=H3D-SOTA-MARKETING-V2
  kind=checkpoint
  summary=SOTA marketing site + README v2 landed in PR #N at <commit>. R3F hero, gcode-preview, theme-aware, Lighthouse perf=<X> a11y=<Y>.

hermes_release_files  owner=codex-impl-04  files=[the lock list]
hermes_release_task   owner=codex-impl-04  taskId=H3D-SOTA-MARKETING-V2
```

---

## 9. Hard rules

- DO NOT add any external runtime dependencies that require credentials, telemetry, analytics, ad networks, or third-party fonts that don't honor `font-display: swap`. The site MUST be entirely self-hostable.
- DO NOT make the site functionally dependent on JavaScript. Core content (text, install commands, links, the SVG diagrams, the Mermaid blocks, the README) MUST render with JS disabled. JS is for enhancement only.
- DO NOT use any GIF, GLB, MP4, or PNG that you didn't generate yourself, license-clear, or whose source you can document.
- DO NOT bundle a stock 3D model with unclear licensing. If you use a hero model, generate it parametrically (e.g., a benchy or hex column you build in code), use the existing `core/design/desk_organizer` output, or use a CC0 model with attribution in the repo.
- DO NOT touch any file outside §4 lock list.
- DO NOT include any analytics, GA, GTM, Plausible, or telemetry of any kind. Privacy posture: zero outbound calls except the GitHub API for releases.
- DO NOT regress the existing 4 animated SVGs' WCAG 2.2 AA compliance (`<title>` + `<desc>` + `aria-labelledby` + `prefers-reduced-motion` stanza).
- DO NOT remove the dev-internal content from `README.md` — move it into a `<details>` accordion or relocate to `CONTRIBUTING.md`. Don't delete.
- DO NOT introduce any secret-scan-tripping patterns (no API key examples in code blocks beyond `sk-…` style placeholders that secret scanners explicitly recognize as fake).

---

## 10. Failure protocol

If any spec is ambiguous (the v1 baseline shipped 3 mistakes Claude already corrected), write `handoffs/HANDOFF_TO_CLAUDE_H3D-SOTA-MARKETING-V2_BLOCKED.md` with:
- Branch + tip SHA
- Locks held
- Files attempted
- Last 50 lines of error or the exact ambiguity (quote the section)
- Suggested fix or open question

Then release locks + task, append evidence with `kind=block`, stop.

If your research agents return contradictory recommendations, default to the one with the most recent (2026) evidence and a working public reference.

---

## 11. References (Claude's prior research transcripts)

The 10-agent research pass is in HermesProof's tasks transcripts (paths logged in PR #24's brief). The relevant agents for this work:

- `ad37bf03a500f1a2c` — 2026 SOTA marketing pages
- `a1d7b4d4530bd06bb` — 2026 README idioms
- `a2dc9cec2815a5675` — 3D-printing visual showcase
- `a4b844dc03f342aea` — screenshot shotlist (22 shots, 20 ready-today)
- `a13cf47da7b91e40d` — Hermes3D feature inventory (79 features cataloged)

The summaries are baked into §1 above. Full transcripts available if you need depth.

---

## 12. Architect contact

Claude (`owner=claude-lead`) reviews each PR. If a B5 contradiction looks like B2's three-strike pattern, file the path-fix request and Claude will turn it around within minutes. Cleaner brief next time is a goal — three blocked-handoffs in a row on B2 is not a pattern we want to repeat.
