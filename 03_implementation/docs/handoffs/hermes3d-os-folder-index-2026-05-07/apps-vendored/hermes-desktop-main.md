# hermes-desktop-main

## Purpose

Hermes Desktop is the Electron-based native desktop GUI for installing, configuring, and chatting with the Hermes Agent (NousResearch hermes-agent). Inside Hermes3D OS it is the human-facing front door: it walks users through Hermes Agent install, manages providers/profiles/sessions/skills/tools, and hosts the "Hermes Office (Claw3d)" 3D interface that fronts the slicing/printing pipeline.

This vendored snapshot is the source-of-record for the desktop shell that the Source OS module registry calls into for chat, tool dispatch, and 3D office workflows. It bundles SQLite (better-sqlite3) for full-text session search and uses electron-updater for self-updates.

## Tech stack

- Language: TypeScript
- Runtime: Electron 39 (electron-vite, electron-builder)
- UI: React 19, Tailwind v4, lucide-react, react-markdown, react-syntax-highlighter
- Storage: better-sqlite3 (FTS5 session search)
- Tests: Vitest, @testing-library/react, jsdom
- Lint/format: ESLint 9, Prettier 3
- License: MIT

## Status

Vendored snapshot, not a git repo.
- Last write time of folder: 2026-04-14 05:12:11
- Version per `package.json`: `0.2.2`
- Author: `fathah`; upstream: `github.com/fathah/hermes-desktop`

## Top-level layout

- `src/` — Electron sources (`main/`, `preload/`, `renderer/`, `shared/`)
- `resources/` — assets, icons
- `build/` — build output staging
- `tests/` — Vitest specs
- `.agents/`, `.claude/`, `.github/` — agent / IDE / CI metadata
- `package.json`, `package-lock.json` — npm manifest (Electron 39, React 19, TS 5.9)
- `electron.vite.config.ts`, `electron-builder.yml`, `dev-app-update.yml`
- `tsconfig*.json`, `eslint.config.mjs`, `vitest.config.ts`
- `skills-lock.json` — pinned skills manifest
- `README.md`, `CONTRIBUTING.md`, `LICENSE`
- `.gitattributes`, `.gitignore`

## Hermes3D integration

This is the GUI consumer that sits on top of the rest of the apps in this index. The Source OS module registry exposes the slicer/modeler/printer modules through Hermes Agent tools; Hermes Desktop renders those tools and mediates user input.

- **Module kind**: `electron-app` (renderer-side host)
- **Verifier**: `npm run typecheck && npm run test` for build-time; runtime probe via electron-updater + IPC handshake
- **Slash commands** (22 documented) include `/code`, `/shell`, `/tools`, `/skills` — these route to Hermes Agent tools that in turn call the slicer/printer modules indexed in this directory
- **Hermes Office (Claw3d)** — the 3D-specific surface that ties to Blender → Slicer → Printrun
- 16 messaging gateways enable remote control of print jobs

## Disk size

16.79 MB

## SVG diagram

<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200">
  <rect x="0" y="0" width="400" height="200" fill="#fafafa" stroke="#ddd"/>
  <rect x="20" y="70" width="100" height="60" fill="#ffd700" stroke="#222"/>
  <text x="70" y="95" text-anchor="middle" font-family="sans-serif" font-size="13">Hermes Desktop</text>
  <text x="70" y="113" text-anchor="middle" font-family="sans-serif" font-size="10">Electron GUI</text>
  <rect x="160" y="20" width="100" height="50" fill="#a78bfa" stroke="#222"/>
  <text x="210" y="40" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#fff">Hermes Agent</text>
  <text x="210" y="58" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#fff">~/.hermes</text>
  <rect x="160" y="80" width="100" height="40" fill="#86efac" stroke="#222"/>
  <text x="210" y="105" text-anchor="middle" font-family="sans-serif" font-size="11">Source OS modules</text>
  <rect x="160" y="130" width="100" height="40" fill="#fbcfe8" stroke="#222"/>
  <text x="210" y="155" text-anchor="middle" font-family="sans-serif" font-size="11">Claw3d / Office</text>
  <rect x="290" y="80" width="90" height="40" fill="#5a8dee" stroke="#222"/>
  <text x="335" y="105" text-anchor="middle" font-family="sans-serif" font-size="11" fill="#fff">slicer / printer</text>
  <line x1="120" y1="100" x2="160" y2="100" stroke="#222" stroke-width="2" marker-end="url(#a3)"/>
  <line x1="120" y1="90" x2="160" y2="50" stroke="#222" stroke-width="2" marker-end="url(#a3)"/>
  <line x1="120" y1="115" x2="160" y2="150" stroke="#222" stroke-width="2" marker-end="url(#a3)"/>
  <line x1="260" y1="100" x2="290" y2="100" stroke="#222" stroke-width="2" marker-end="url(#a3)"/>
  <defs>
    <marker id="a3" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#222"/>
    </marker>
  </defs>
  <text x="200" y="195" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#666">GUI shell hosting Hermes Agent + 3D pipeline</text>
</svg>
