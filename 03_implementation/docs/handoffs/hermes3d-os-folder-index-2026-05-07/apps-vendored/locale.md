# locale

## Purpose

A small standalone locale-data folder containing translation files (gettext) for Printrun's `pronterface` GUI. It ships as a sibling to the apps tree because Hermes3D OS bundles localized printer-host strings independently of the Printrun source folder, e.g. for runtime locale overlay or for centralized translation packaging across multiple H3D-bundled apps.

The folder mirrors a typical gettext layout: per-locale directories plus a master `.pot` template.

## Tech stack

- Format: gettext (`.pot` template, per-locale directories)
- Languages present: Arabic (`ar`), German (`de`), French (`fr`), Armenian (`hy`), Italian (`it`), Dutch (`nl`)
- No build system — pure data

## Status

Vendored snapshot, not a git repo.
- Last write time of folder: 2024-10-20 13:12:06
- No embedded version metadata; carries Printrun's translation template (`pronterface.pot`).

## Top-level layout

- `ar/`, `de/`, `fr/`, `hy/`, `it/`, `nl/` — locale subdirectories (each contains `.po`/`.mo`)
- `pronterface.pot` — gettext message template

## Hermes3D integration (INFERRED)

INFERRED: registered in the Source OS module registry as a passive `data` module (no executable):
- `kind: data`
- `consumer: printrun`
- `loader: gettext` — overlay-mounted into Printrun's runtime locale path
- `verifier: file-presence check on pronterface.pot + at least one locale dir`

This decoupling lets H3D update translations without touching the pinned Printrun source tree. It's also the reason the file size is tiny (<1 MB).

## Disk size

0.61 MB

## SVG diagram

<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200">
  <rect x="0" y="0" width="400" height="200" fill="#fafafa" stroke="#ddd"/>
  <rect x="20" y="60" width="100" height="80" fill="#fde68a" stroke="#222"/>
  <text x="70" y="85" text-anchor="middle" font-family="sans-serif" font-size="12">locale/</text>
  <text x="70" y="103" text-anchor="middle" font-family="sans-serif" font-size="10">ar de fr hy</text>
  <text x="70" y="118" text-anchor="middle" font-family="sans-serif" font-size="10">it nl + .pot</text>
  <text x="70" y="133" text-anchor="middle" font-family="sans-serif" font-size="9" fill="#444">gettext catalogs</text>
  <rect x="170" y="60" width="100" height="80" fill="#fbbf24" stroke="#222"/>
  <text x="220" y="90" text-anchor="middle" font-family="sans-serif" font-size="12">overlay loader</text>
  <text x="220" y="108" text-anchor="middle" font-family="sans-serif" font-size="10">Source OS</text>
  <text x="220" y="125" text-anchor="middle" font-family="sans-serif" font-size="9" fill="#444">i18n module</text>
  <rect x="320" y="60" width="65" height="80" fill="#a3e635" stroke="#222"/>
  <text x="352" y="95" text-anchor="middle" font-family="sans-serif" font-size="12">Printrun</text>
  <text x="352" y="112" text-anchor="middle" font-family="sans-serif" font-size="10">pronterface</text>
  <line x1="120" y1="100" x2="170" y2="100" stroke="#222" stroke-width="2" marker-end="url(#a4)"/>
  <line x1="270" y1="100" x2="320" y2="100" stroke="#222" stroke-width="2" marker-end="url(#a4)"/>
  <defs>
    <marker id="a4" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#222"/>
    </marker>
  </defs>
  <text x="200" y="30" text-anchor="middle" font-family="sans-serif" font-size="14" font-weight="bold">Locale data overlay</text>
  <text x="200" y="170" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#666">Translations decoupled from pinned Printrun source</text>
</svg>
