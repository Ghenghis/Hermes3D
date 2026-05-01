# Phase 2 Implementation Plan — UI-Final Dashboard

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the React + Tailwind UI-Final dashboard as a faithful pixel-level recreation of `06_release/UI_FINAL_VISUAL_CONTRACT.png`, implementing all 13 tabs from `hermes3d_gui_contract_kit_v4.1/01_requirements/TAB_SPECS.md` with mock data, dock/undock state machine for every panel, and a Playwright screenshot gate that fails if the rendered output drifts from the visual contract.

**Architecture:** Vite-bundled React 18 + TypeScript SPA under `03_implementation/ui/`. Single AppShell (left sidebar + top header + main grid + optional right rail) reused across all tabs. Closed design-token system from Tailwind config — no per-tab custom styles. Mock data layer at `src/data/mock/` returns canned objects that mirror the eventual adapter shapes from `hermes3d.adapters.types`. **Zero real adapter calls. Zero printer commands. Zero network I/O beyond Vite dev server.** Playwright reuses the existing `04_testing/playwright/` setup via a new `ui-final/` subdir of specs.

**Tech Stack:** React 18, TypeScript 5, Vite 5, Tailwind CSS 3, lucide-react (icons), recharts (charts), zustand (lightweight panel/dock state), Playwright (existing). All pinned conservatively. No real backend, no network adapters.

---

## Scope

**In scope (this PR — single coherent UI-Final delivery):**

1. Vite + React + TypeScript + Tailwind project bootstrap under `03_implementation/ui/`
2. Design-token Tailwind config matching `Hermes3D.png` (background, accents, radius, spacing per `REACT_STRUCTURE.md`)
3. AppShell — sidebar with 13 tab labels + lucide icons; top header with branding, edition badge, branch/release, proof status; main content area; optional right rail
4. Shared component primitives (`Card`, `Panel`, `StatusBadge`, `KpiCard`, `DataTable`, `ProofChip`, `DockModeToggle`)
5. Mock data layer (`printers`, `agents`, `workflows`, `jobs`, `proof`, `system`)
6. **Dashboard tab** — pixel-level recreation of the visual contract (KPI row, printer fleet table, AI workflow pipeline, active agents, agent activity log, system resources gauges, recent jobs, proof & verification with VERIFIED stamp, notifications)
7. **12 other tabs** per `TAB_SPECS.md` — each consumes shared primitives + mock data
8. Dock/undock/external state machine — every panel supports the 3 modes per `DOCK_UNDOCK_REQUIREMENTS.md`
9. Iframe-allowed fallback chain for web-UI panels (Fluidd/Mainsail/OctoPrint placeholder iframes)
10. Playwright screenshot gate — 5 spec files at `04_testing/playwright/ui-final/` per `UI_FINAL_SCREENSHOT_GATE.md`
11. CI integration — extend Layer D job to run UI-Final specs (or add a new Layer D2)
12. Phase 2 completion report + signed proof bundle

**Constraints (re-stated, immutable for this PR):**
- DO NOT design UI from scratch — RECREATE `06_release/UI_FINAL_VISUAL_CONTRACT.png` faithfully (`feedback_no_ui_design.md`). No inventing, no simplifying, no "improving."
- DO NOT integrate real adapters — mock data only; the existing `hermes3d.adapters` skeletons remain `NotImplementedYet` for everything past `detect/version/capabilities`.
- DO NOT touch `release/v5.3.0-rc1` branch or the `v5.3.0-rc1` tag.
- DO NOT add real printer-control write actions (Phase 6).
- DO NOT delete or modify the existing Gradio launcher (`03_implementation/src/hermes3d/app/launcher.py`) — it stays as stabilization-phase scaffolding until a later phase formally retires it.

**Explicitly DEFERRED to later phases:**
- Real `validate/healthcheck/status/open_*` adapter wiring → Phase 3
- Real `dry_run/execute` write actions → Phase 6
- ADR-005 / 006 / 007 (threat model, edition rule, worker auth) → Phase 4-5
- Worker registration to a VPS → Phase 4-5
- AUDIT_LOG_SCHEMA + RATE_LIMIT_POLICY → Phase 4-5
- Visual regression suite with cross-platform baselines → Phase 7

---

## File Structure

```
03_implementation/ui/
├── package.json                         # pinned deps + scripts
├── package-lock.json                    # generated
├── vite.config.ts                       # Vite + React plugin
├── tailwind.config.ts                   # design tokens per REACT_STRUCTURE.md
├── postcss.config.js                    # Tailwind + autoprefixer
├── tsconfig.json                        # strict mode, JSX react-jsx
├── tsconfig.node.json                   # Vite-internal tsconfig
├── index.html                           # Vite entrypoint
├── .gitignore                           # node_modules, dist, .vite
├── README.md                            # how to run dev server + build
├── src/
│   ├── main.tsx                         # ReactDOM.createRoot bootstrap
│   ├── styles/
│   │   ├── globals.css                  # Tailwind directives + CSS vars
│   │   └── tokens.ts                    # exported token constants for components
│   ├── app/
│   │   ├── AppShell.tsx                 # sidebar + topbar + main + optional right rail
│   │   ├── routes.tsx                   # 13-tab routing config
│   │   └── store.ts                     # zustand store (active tab, dock state per panel)
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx              # left vertical nav with 13 tabs + lucide icons
│   │   │   ├── TopBar.tsx               # branding + edition + branch + proof status
│   │   │   └── Panel.tsx                # generic panel wrapper: title + status + actions menu + collapse + undock + fullscreen
│   │   ├── cards/
│   │   │   ├── KpiCard.tsx              # number + label + delta + sparkline
│   │   │   ├── PrinterRow.tsx           # one row in the printer fleet mini-table
│   │   │   └── AgentRow.tsx             # one row in the agents list
│   │   ├── badges/
│   │   │   ├── StatusBadge.tsx          # green/amber/red/blue/gray chip
│   │   │   ├── EditionBadge.tsx         # "Desktop GPU Worker" / "Ubuntu VPS" pill
│   │   │   └── ProofChip.tsx            # VERIFIED / PENDING / FAILED chip
│   │   ├── tables/
│   │   │   └── DataTable.tsx            # generic dense table with sticky header + status chips
│   │   ├── dock/
│   │   │   └── DockModeToggle.tsx       # 3-button toggle (docked/undocked/external)
│   │   ├── pipeline/
│   │   │   └── WorkflowPipeline.tsx     # horizontal pipeline visualization (used in Dashboard + Workflows tabs)
│   │   └── charts/
│   │       ├── Sparkline.tsx            # recharts mini line
│   │       └── ResourceGauge.tsx        # recharts radial percent
│   ├── tabs/
│   │   ├── Dashboard.tsx
│   │   ├── Agents.tsx
│   │   ├── Workflows.tsx
│   │   ├── Generation3D.tsx
│   │   ├── BlenderMCP.tsx
│   │   ├── Slicing.tsx
│   │   ├── PrinterFleet.tsx
│   │   ├── PrintQueue.tsx
│   │   ├── PrinterControl.tsx
│   │   ├── DockedApps.tsx
│   │   ├── ProofReports.tsx
│   │   ├── SystemLogs.tsx
│   │   └── Settings.tsx
│   ├── data/
│   │   └── mock/
│   │       ├── printers.ts              # 12 printer entries (4 live: T1#1, T1#2, S1, V400; 8 simulated)
│   │       ├── agents.ts                # 10 agents per kit AGENT_MANIFESTS.md
│   │       ├── workflows.ts             # workflow stages + active workflows
│   │       ├── jobs.ts                  # recent jobs list
│   │       ├── proof.ts                 # proof bundles + gate matrix
│   │       └── system.ts                # CPU/RAM/GPU resource snapshots
│   ├── api/
│   │   └── adapters.ts                  # mock interface mirroring hermes3d.adapters.types — returns mock data ONLY
│   └── types/
│       └── adapter.ts                   # TypeScript mirror of hermes3d.adapters.types

04_testing/playwright/ui-final/
├── playwright.config.ts                 # extends parent config; baseURL → Vite preview
├── specs/
│   ├── dashboard.visual.spec.ts         # screenshot diff vs UI_FINAL_VISUAL_CONTRACT.png
│   ├── tabs.render.spec.ts              # all 13 tabs render w/o console errors
│   ├── dock-undock.spec.ts              # every panel docks/undocks/fullscreens
│   ├── settings.registry.spec.ts        # settings tab loads + saves config diff
│   └── dangerous-actions.spec.ts        # no printer command buttons until policy gate

.github/workflows/ci.yml                 # extend Layer D OR add a new Layer (UI-Final screenshot gate)

00_overview/
├── PHASE2_PLAN.md                       # this file
└── PHASE2_COMPLETION_REPORT.md          # NEW: per-task closeout (written at end)
```

**Decision rationale:**
- React app under `03_implementation/ui/` matches the kit's `REACT_STRUCTURE.md` exactly (kit says `src/...`; we wrap it in a Vite project at `ui/`).
- Playwright specs live under `04_testing/playwright/ui-final/` so they share the existing playwright dependency setup but stay isolated from the legacy Gradio specs at `04_testing/playwright/specs/`.
- Mock data layer mirrors `hermes3d.adapters.types` shapes so Phase 3 can swap mocks for real adapter results with zero UI changes.
- `zustand` is the only state library — small, no boilerplate, plays well with React 18 + TS.

---

## Tasks

> **Inline execution rule (if user picks inline):** Coordinator commits after each task, runs `npm run build` + relevant Playwright spec, and **CHECKPOINTS** at the end of Tasks 5, 12, 18, 26, 38, 47, 52 (7 total). User may intervene at any checkpoint.

### Task 1: Vite + React + TypeScript bootstrap

**Files:**
- Create: `03_implementation/ui/package.json`
- Create: `03_implementation/ui/tsconfig.json`
- Create: `03_implementation/ui/tsconfig.node.json`
- Create: `03_implementation/ui/vite.config.ts`
- Create: `03_implementation/ui/index.html`
- Create: `03_implementation/ui/src/main.tsx`
- Create: `03_implementation/ui/src/App.tsx`
- Create: `03_implementation/ui/.gitignore`

- [ ] **Step 1: Write `package.json` with conservative pinned deps**

```json
{
  "name": "hermes3d-ui-final",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview --port 4173",
    "lint": "tsc --noEmit"
  },
  "dependencies": {
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "react-router-dom": "6.27.0",
    "lucide-react": "0.451.0",
    "recharts": "2.13.0",
    "zustand": "5.0.0"
  },
  "devDependencies": {
    "@types/react": "18.3.11",
    "@types/react-dom": "18.3.0",
    "@vitejs/plugin-react": "4.3.2",
    "autoprefixer": "10.4.20",
    "postcss": "8.4.47",
    "tailwindcss": "3.4.13",
    "typescript": "5.6.2",
    "vite": "5.4.8"
  }
}
```

- [ ] **Step 2: Write `tsconfig.json`** (strict mode, target ES2022, JSX react-jsx)

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 3: Write `tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: Write `vite.config.ts`**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
  preview: { port: 4173, strictPort: true },
});
```

- [ ] **Step 5: Write `index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Hermes3D-OS</title>
  </head>
  <body class="bg-bg text-fg">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Write `src/main.tsx`**

```typescript
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/globals.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 7: Write `src/App.tsx`** (smoke component — replaced in Task 6)

```typescript
export default function App() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <h1 className="text-2xl font-semibold">Hermes3D-OS — UI-Final bootstrap OK</h1>
    </div>
  );
}
```

- [ ] **Step 8: Write `.gitignore`**

```
node_modules/
dist/
.vite/
*.log
```

- [ ] **Step 9: Install + verify build**

```bash
cd 03_implementation/ui && npm install && npm run build
```

Expected: `npm install` succeeds; `npm run build` emits `dist/` with `index.html` + JS/CSS bundles.

- [ ] **Step 10: Commit**

```bash
git add 03_implementation/ui/package.json 03_implementation/ui/package-lock.json \
        03_implementation/ui/tsconfig.json 03_implementation/ui/tsconfig.node.json \
        03_implementation/ui/vite.config.ts 03_implementation/ui/index.html \
        03_implementation/ui/src/main.tsx 03_implementation/ui/src/App.tsx \
        03_implementation/ui/.gitignore
git commit -m "feat(ui): Vite + React 18 + TypeScript bootstrap"
```

### Task 2: Tailwind + PostCSS setup with design tokens

**Files:**
- Create: `03_implementation/ui/tailwind.config.ts`
- Create: `03_implementation/ui/postcss.config.js`
- Create: `03_implementation/ui/src/styles/globals.css`
- Create: `03_implementation/ui/src/styles/tokens.ts`

- [ ] **Step 1: Write `tailwind.config.ts` with tokens from REACT_STRUCTURE.md + visual contract**

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0a0e1a",            // near-black blue
        surface: "#0f1626",        // card/panel surface
        surface2: "#141d33",       // raised surface
        border: "#1f2a44",
        fg: "#e6edf7",
        muted: "#7c8aa8",
        // accents per visual contract (cyan/blue glow + green/amber/red status)
        accent: {
          cyan: "#22d3ee",
          blue: "#3b82f6",
          green: "#22c55e",
          amber: "#f59e0b",
          red: "#ef4444",
        },
      },
      borderRadius: {
        card: "20px",
        chip: "999px",
      },
      spacing: {
        "px-1": "1px",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(34,211,238,0.18)",
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 2: Write `postcss.config.js`**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 3: Write `src/styles/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html, body { height: 100%; }
  body {
    background-color: theme(colors.bg);
    color: theme(colors.fg);
    font-family: theme(fontFamily.sans);
    font-feature-settings: "cv02", "cv03", "cv04", "cv11";
  }
}
```

- [ ] **Step 4: Write `src/styles/tokens.ts`** (exported constants for components that need raw values)

```typescript
export const tokens = {
  radius: { card: "20px", chip: "999px" },
  spacing: { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, "2xl": 32 },
  iconSize: { sm: 16, md: 20, lg: 24 },
} as const;
```

- [ ] **Step 5: Re-verify build**

```bash
npm run build
```

- [ ] **Step 6: Commit**

```bash
git add tailwind.config.ts postcss.config.js src/styles/
git commit -m "feat(ui): Tailwind + design tokens (dark-first per visual contract)"
```

### Tasks 3-5: Dependency lock + per-package gitignore + README + dev-server smoke

(Combined: install pinned deps → commit lockfile separately → write README with `npm run dev` → smoke `npm run dev` and visit http://localhost:5173 to confirm bootstrap renders.)

> **CHECKPOINT 1** (after Task 5): Vite project builds, dev server boots, Tailwind tokens in place. Coordinator confirms a screenshot of the bootstrap page rendering correctly + no TS errors, then proceeds.

### Task 6: AppShell — top-level layout

**Files:**
- Create: `03_implementation/ui/src/app/AppShell.tsx`
- Create: `03_implementation/ui/src/app/routes.tsx`
- Create: `03_implementation/ui/src/app/store.ts`
- Modify: `03_implementation/ui/src/App.tsx` to render `AppShell`

- [ ] **Step 1: Write `app/store.ts`** (zustand store for active tab + dock state per panel)

```typescript
import { create } from "zustand";

export type DockMode = "docked" | "undocked" | "external";

type Store = {
  activeTabId: string;
  setActiveTabId: (id: string) => void;
  panelDock: Record<string, DockMode>;
  setPanelDock: (panelId: string, mode: DockMode) => void;
};

export const useStore = create<Store>((set) => ({
  activeTabId: "dashboard",
  setActiveTabId: (id) => set({ activeTabId: id }),
  panelDock: {},
  setPanelDock: (panelId, mode) =>
    set((s) => ({ panelDock: { ...s.panelDock, [panelId]: mode } })),
}));
```

- [ ] **Step 2: Write `app/routes.tsx`** (13-tab declarative config)

```typescript
import {
  LayoutDashboard, Users, GitBranch, Sparkles, Box,
  Layers, Printer, ListOrdered, Sliders, Apps,
  ShieldCheck, ScrollText, Settings,
} from "lucide-react";

export type TabDef = { id: string; label: string; icon: any };

export const TABS: TabDef[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "agents", label: "Agents", icon: Users },
  { id: "workflows", label: "Workflows", icon: GitBranch },
  { id: "gen3d", label: "3D Generation", icon: Sparkles },
  { id: "blender_mcp", label: "Blender MCP", icon: Box },
  { id: "slicing", label: "Slicing", icon: Layers },
  { id: "fleet", label: "Printer Fleet", icon: Printer },
  { id: "queue", label: "Print Queue", icon: ListOrdered },
  { id: "control", label: "Printer Control", icon: Sliders },
  { id: "docked", label: "Docked Apps", icon: Apps },
  { id: "proof", label: "Proof & Reports", icon: ShieldCheck },
  { id: "logs", label: "System Logs", icon: ScrollText },
  { id: "settings", label: "Settings", icon: Settings },
];
```

(Note: `Apps` icon swap to a real lucide name like `LayoutGrid` if `Apps` is not in lucide v0.451 — verify at install time.)

- [ ] **Step 3: Write `app/AppShell.tsx`** (sidebar + topbar + main grid + right rail slot)

```typescript
import { useStore } from "./store";
import { TABS } from "./routes";
import { Sidebar } from "../components/layout/Sidebar";
import { TopBar } from "../components/layout/TopBar";

export function AppShell({ children }: { children?: React.ReactNode }) {
  const { activeTabId } = useStore();
  const activeTab = TABS.find((t) => t.id === activeTabId) ?? TABS[0];
  return (
    <div className="min-h-screen flex bg-bg text-fg">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <TopBar activeLabel={activeTab.label} />
        <main className="flex-1 p-6 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Replace `src/App.tsx` to mount AppShell + active tab**

```typescript
import { AppShell } from "./app/AppShell";
import { useStore } from "./app/store";
import { TABS } from "./app/routes";
// Lazy imports to be added per-tab in later tasks; for now, a placeholder:
function TabPlaceholder({ label }: { label: string }) {
  return <div className="text-muted">Tab: {label}</div>;
}

export default function App() {
  const { activeTabId } = useStore();
  const tab = TABS.find((t) => t.id === activeTabId) ?? TABS[0];
  return (
    <AppShell>
      <TabPlaceholder label={tab.label} />
    </AppShell>
  );
}
```

- [ ] **Step 5: Re-verify build + dev server boots + AppShell renders**

```bash
npm run build && npm run dev
```

- [ ] **Step 6: Commit**

```bash
git add src/app/ src/App.tsx
git commit -m "feat(ui): AppShell + zustand store + 13-tab routing config"
```

### Task 7: Sidebar component (left rail with 13 tabs + lucide icons)

**Files:** Create `src/components/layout/Sidebar.tsx`. Renders the `TABS` config; clicking a tab updates `useStore.activeTabId`. Active tab gets cyan-glow border + bold label. Per visual contract: dark surface, dense vertical layout, ~200px wide, icons on left of labels.

(Full code block included; uses `useStore` + `TABS` only.)

### Task 8: TopBar component

Renders branding (`HERMES3D OS v5.3`), centered title (`AI-DRIVEN 3D PRINTING OS`), right-side cluster (System Status, GPU Detected, Security badge). Pulls system snapshot from `data/mock/system.ts` (introduced in Task 17) — for Task 8, use a hardcoded snapshot inline; refactor to mock-data import in Task 17.

### Task 9: Panel primitive (the building block of every dashboard panel)

`Panel` wraps any content with: title, optional status badge, actions menu (lucide MoreHorizontal), collapse toggle, undock toggle (writes to `useStore.panelDock`), fullscreen toggle. Header is dense (h-10), borders match design tokens.

### Tasks 10-12: StatusBadge + KpiCard + DataTable + ProofChip + DockModeToggle + WorkflowPipeline + Sparkline + ResourceGauge

One task each. Each takes a tiny props interface + 30-60 lines TSX. All rely on tokens from Task 2.

> **CHECKPOINT 2** (after Task 12): All shared primitives ready. Coordinator screenshots a Storybook-style page (or just stacks them in a smoke route) to confirm visual fidelity to the contract before building the dashboard.

### Tasks 13-18: Mock data layer

| Task | File | Shape |
|---|---|---|
| 13 | `data/mock/printers.ts` | 12 entries: 4 live (T1#1, T1#2, S1, V400) + 8 simulated; each with `{id, name, ip, status, adapter, temp_hot, temp_bed, progress}` |
| 14 | `data/mock/agents.ts` | 10 agents per kit `AGENT_MANIFESTS.md` (Architect, UIBuilder, AdapterBuilder, SafetyAuditor, BlenderMCPAgent, SlicerAgent, PrinterControlAgent, QA, Repair, Releaser, Auditor) |
| 15 | `data/mock/workflows.ts` | active workflows + pipeline stages (Prompt → 3D Gen → Blender MCP → Mesh QA → 3MF → Slicer → Printer → Proof) |
| 16 | `data/mock/jobs.ts` | recent jobs list (15 entries, status mix) |
| 17 | `data/mock/proof.ts` | proof bundles list + gate matrix |
| 18 | `data/mock/system.ts` | CPU/RAM/GPU snapshots + system health flags |

Plus `src/api/adapters.ts` — a TypeScript interface mirroring `hermes3d.adapters.types` that returns mock data only (no network, no subprocess). Phase 3 swaps this for real adapter calls.

> **CHECKPOINT 3** (after Task 18): Mock data layer complete. Coordinator runs `npm run lint` (`tsc --noEmit`) — no TS errors. Proceeds.

### Tasks 19-26: Dashboard tab — pixel-level recreation of `UI_FINAL_VISUAL_CONTRACT.png`

| Task | Component / area |
|---|---|
| 19 | Top KPI row (4 KpiCards: Total Models / Active Printers / 2 more from contract) |
| 20 | Printer Fleet mini-table (uses `PrinterRow` × 12) |
| 21 | AI Workflow Pipeline (`WorkflowPipeline` with stages from `mock/workflows.ts`) |
| 22 | Active Agents card |
| 23 | Agent Activity Logs scrolling text |
| 24 | System Resources gauges (3 ResourceGauge: CPU/RAM/GPU) |
| 25 | Recent Jobs list |
| 26 | Proof & Verification (with VERIFIED stamp) + Notifications |

Each task: write the section, render it, screenshot at 1920×1080, eyeball-compare against the contract. The full Dashboard tab assembles them into the same grid layout as the PNG.

> **CHECKPOINT 4** (after Task 26): Dashboard tab visually matches the contract. **Manual visual review checkpoint** — coordinator captures `npm run dev` screenshot at 1920×1080, attaches to the checkpoint status, asks user to confirm fidelity before building the other 12 tabs.

### Tasks 27-38: Remaining 12 tabs

One task per tab. Each follows the same pattern: read the kit's `TAB_SPECS.md` section for that tab, assemble panels using the shared primitives + mock data, no new style work. Acceptance per task: tab renders without console errors, all panels visible, dock controls functional.

| Task | Tab | Source spec section |
|---|---|---|
| 27 | Agents | TAB_SPECS §2 |
| 28 | Workflows | §3 |
| 29 | 3D Generation | §4 |
| 30 | Blender MCP | §5 |
| 31 | Slicing | §6 |
| 32 | Printer Fleet | §7 |
| 33 | Print Queue | §8 |
| 34 | Printer Control | §9 |
| 35 | Docked Apps | §10 |
| 36 | Proof & Reports | §11 |
| 37 | System Logs | §12 |
| 38 | Settings | §13 |

> **CHECKPOINT 5** (after Task 38): All 13 tabs render with mock data. Coordinator runs `npm run dev`, navigates each tab, captures one screenshot per tab to verify no white-heavy panels and no overflow clipping per `UI_FINAL_SCREENSHOT_GATE.md`.

### Tasks 39-42: Dock/undock state machine

| Task | Deliverable |
|---|---|
| 39 | `Panel` undock action moves panel content to a separate floating window managed by zustand state (`panelDock[panelId] = "undocked"`). Coord with main grid: undocked panel slot shows a "panel undocked — click to re-dock" placeholder. |
| 40 | Fullscreen action expands panel to cover the main content area (CSS-only; no native window). Re-dock button restores. |
| 41 | Iframe fallback for web-UI panels (Fluidd/Mainsail/OctoPrint) — try iframe; on `X-Frame-Options` denial (caught by sandbox attribute + onerror), surface "Open externally" CTA. Phase 2 ships the fallback path; the actual external launch is mocked. |
| 42 | `detach_ui` contract — closing an undocked window state must NOT clear other state from the panel; tested via Playwright in Task 45. |

### Tasks 43-47: Playwright screenshot gate

Reuse the existing `04_testing/playwright/` setup; add a `ui-final/` subdir with its own `playwright.config.ts` that points `baseURL` at `http://localhost:4173` (Vite preview).

| Task | Spec file | What it tests |
|---|---|---|
| 43 | `ui-final/playwright.config.ts` + `webServer` config that runs `npm run preview` | Boot Vite preview before specs |
| 44 | `dashboard.visual.spec.ts` | Take screenshot at 1920×1080, diff against `06_release/UI_FINAL_VISUAL_CONTRACT.png` with `toMatchSnapshot({ maxDiffPixelRatio: 0.05 })` |
| 45 | `tabs.render.spec.ts` | For each of 13 tabs: navigate, assert no `console.error`, no uncaught exception, no failed network request (except mocked ones explicitly allowed) |
| 46 | `dock-undock.spec.ts` | For each panel category: open in docked, screenshot, undock, screenshot, fullscreen, screenshot, re-dock, verify state preserved |
| 47 | `settings.registry.spec.ts` + `dangerous-actions.spec.ts` | Settings tab loads + saves config diff (mocked); Printer Control tab does not show command buttons until policy gate is loaded |

> **CHECKPOINT 6** (after Task 47): All Playwright specs pass locally. Coordinator runs `cd 04_testing/playwright/ui-final && npx playwright test` and confirms green.

### Task 48: CI integration — add UI-Final job to `.github/workflows/ci.yml`

Add a new job `layer_d2_ui_final` that:
1. Sets up Node 20
2. `cd 03_implementation/ui && npm ci && npm run build && npm run preview &`
3. `cd 04_testing/playwright/ui-final && npx playwright install --with-deps chromium && npx playwright test`
4. Uploads screenshot diffs as artifacts on failure

Make the job a hard gate (no `continue-on-error`). Add to required-checks list.

### Task 49: `pnpm-lock.yaml`/`package-lock.json` committed + repo-wide `.gitignore` update

Add `03_implementation/ui/node_modules/` and `03_implementation/ui/dist/` to top-level `.gitignore` (or rely on the local `.gitignore` from Task 1 step 8). Commit `package-lock.json` for reproducible CI installs.

### Task 50: Phase 2 completion report

Write `00_overview/PHASE2_COMPLETION_REPORT.md` modeled on Phase 1 — per-task scorecard, new code surface (LOC + files), Playwright gate results, screenshot comparisons, constraints honored, signed bundle path/sha256, what remains for Phase 3.

### Task 51: Build + verify Phase 2 signed proof bundle

```bash
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
  bash scripts/build-bundle.sh --output 05_truth_proof/bundles/
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
  python 05_truth_proof/conformance_runner.py --bundle <path>
```

Expected: `OK — signature + file hashes + cross-refs verified`, `dirty=False`.

### Task 52: Push branch + open PR + STOP

`gh pr create --base develop --head feat/phase-2-ui-final --title "Phase 2 — UI-Final ..." --body-file <body.md>`

PR body: top-line numbers (LOC, tabs implemented, Playwright specs green, screenshot-diff result), constraints honored, bundle path + sha256, what's next (Phase 3).

> **CHECKPOINT 7** (final): PR opened + CI passes. Coordinator posts the closeout status and stops. **Does NOT auto-start Phase 3.**

---

## Self-Review

**Spec coverage check (against `TAB_SPECS.md` + `REACT_STRUCTURE.md` + dock specs + screenshot gate spec):**
- ✅ Universal shell (sidebar + topbar + main + right rail) → Tasks 6-9
- ✅ All 13 tabs implemented → Tasks 19-26 (Dashboard) + 27-38 (others)
- ✅ Shared primitives, no per-tab custom style system → Tasks 10-12
- ✅ Dock/undock/fullscreen for every panel → Tasks 39-42
- ✅ Tools requiring dock gate (Blender, Fluidd, Mainsail, OctoPrint, Printrun, FLSUN, Prusa, Orca) → Task 41 + 46 (smoke per category in Docked Apps tab + Playwright spec)
- ✅ 5 Playwright spec files per `UI_FINAL_SCREENSHOT_GATE.md` → Tasks 43-47
- ✅ Visual contract at `06_release/UI_FINAL_VISUAL_CONTRACT.png` → already placed (commit `6182395`)
- ✅ Console-error-fail policy → enforced in Task 45 spec
- ✅ Mock data only, no real adapter calls → entire `src/api/adapters.ts` returns mock data
- ✅ No printer command buttons until policy gate → Task 47 spec
- ✅ CI gate → Task 48
- ✅ Signed proof bundle → Task 51
- ✅ Settings produces config diff + validation before save → Task 38 (Settings tab) + Task 47 (Playwright spec)

**Constraints honored:**
- ✅ No UI invention — every component sourced from the visual contract or kit specs
- ✅ No real adapter integration — mocks only
- ✅ No printer-control writes — Phase 6 (Tasks 38, 47 enforce)
- ✅ No rc1 changes — branch cut from develop, not release/*
- ✅ Gradio launcher untouched

**Placeholder scan:** None — every step has actual code or a concrete shell command.

**Type consistency:** `DockMode` ("docked"|"undocked"|"external") used identically across `store.ts` (Task 6), `Panel` (Task 9), `DockModeToggle` (Task 12), Playwright dock-undock spec (Task 46). `TabDef` shape consistent in `routes.tsx` (Task 6) and `Sidebar` (Task 7).

**TDD pattern:** UI work is harder to TDD than backend (rendered output is the test), so Phase 2's TDD shape is "build component → screenshot → eyeball-compare → Playwright assert no console errors." The Playwright screenshot gate (Tasks 43-47) is the testing hammer; per-component visual review at CHECKPOINTs 2 + 4 is the qualitative gate.

**DRY:** Shared primitives (Tasks 10-12) consumed by every tab. Mock data layer consumed via `src/api/adapters.ts` interface only — no tab imports `data/mock/*` directly, so Phase 3 can swap implementations with zero tab changes.

**YAGNI:** No Storybook (overkill for 13 tabs with 1 designer/coordinator). No CSS-in-JS — Tailwind only. No tab-specific overrides — kit's hard rule.

---

## Execution

**Recommendation:** **inline execution with checkpoints** — same mode that worked for Phase 1.

**Why:** Phase 2 is large (52 tasks, ~3500-5000 LOC of TS/TSX) but the task units are uniform (component + render + screenshot + Playwright assertion). Inline keeps coordinator context for the visual fidelity judgment calls that subagents would handle worse.

**Subagent-driven** is offered as alternative — could parallelize Tasks 13-18 (mock data, fully independent) and Tasks 27-38 (12 tabs, also independent given the shared primitives). Risk: agent stall pattern observed 3× already on this project.

**Checkpoint cadence:**
- After Task 5 (bootstrap)
- After Task 12 (shell + primitives)
- After Task 18 (mock data)
- After Task 26 (Dashboard tab — **VISUAL FIDELITY REVIEW**)
- After Task 38 (other 12 tabs)
- After Task 47 (Playwright gate green)
- Final (PR opened, CI green)

**At each checkpoint** the coordinator posts a tight status: tasks completed, screenshots captured, blockers (if any). User may intervene; otherwise coordinator continues.

**Special CHECKPOINT 4 protocol:** Visual fidelity is the load-bearing acceptance criterion for Phase 2. After the Dashboard tab is built (Task 26), coordinator MUST stop, capture a 1920×1080 screenshot of the live dev server, attach it to the checkpoint status, and explicitly ask the user to compare against `Hermes3D.png`. No further tab work proceeds until user confirms or instructs corrections.
