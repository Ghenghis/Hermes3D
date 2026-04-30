# Hermes3D-OS — Quickstart for non-coders

**Goal:** From a clean Windows 11 (or Linux/macOS) machine, get the Hermes3D
control panel running in your browser in five clicks. No file editing.

> If anything in this guide doesn't match what you see on screen, that's a bug —
> please file an issue at <https://github.com/Ghenghis/Hermes3D/issues> and
> include the contents of `var/preflight/<latest>.json`.

---

## Step 1 — Install three free tools

You only need three things on your computer:

| Tool | Why | Where |
|---|---|---|
| **Python 3.11+** | runs Hermes3D | <https://www.python.org/downloads/> (check "Add to PATH" during install) |
| **Git** | downloads the kit | <https://git-scm.com/downloads> |
| **Node.js 20+** | runs the UI test suite | <https://nodejs.org/> |

Optional but recommended: **GitHub CLI** (`gh`) for opening pull requests
without leaving the terminal.

After install, open a fresh terminal (PowerShell on Windows, Terminal on Mac/Linux).

## Step 2 — Get the kit

```bash
git clone https://github.com/Ghenghis/Hermes3D.git
cd Hermes3D
```

## Step 3 — Run the wizard

**Windows (PowerShell):**
```powershell
.\scripts\wizard.ps1
```

**Mac / Linux / WSL / Git-Bash:**
```bash
bash scripts/wizard.sh
```

The wizard will guide you through five steps:

1. **Preflight** — checks the three tools above and prints a green ✓ next to each
2. **Install** — downloads Hermes3D's Python dependencies (one-time, ~2 minutes)
3. **Hooks** — installs a safety check that prevents you from accidentally
   committing to the production branch
4. **Acceptance** — runs the built-in 48-cell test (proves the kit works on
   your machine before you trust it)
5. **UI launch** — opens <http://localhost:7860> in your browser

## Step 4 — Use the control panel

In the browser tab that opened:

| Tab | What it does |
|---|---|
| **Truth Gate Validator** | Drop in an STL file; see if it's printable on each printer in your fleet. |
| **Generate Desk Organizer** | Type in dimensions and slot counts; the kit produces a proof-stamped STL. |
| **Dry-Run Pipeline** | End-to-end demo with no real printer; emits a signed proof envelope. |

The control panel **never** sends your files anywhere. Everything runs locally.

## Step 5 — Stop / restart

- **Stop:** click the terminal where the wizard is running, press `Ctrl+C`.
- **Restart later:** in the same `Hermes3D/` folder, run
  `python -m hermes3d.app.launcher` (the wizard's last step on its own).

---

## When something goes wrong

The wizard prints the location of a JSON capability report on Step 1. Open it,
look for any `"state": "missing"` entries, install those tools, re-run the
wizard. If the missing tool is **optional** (yellow `[opt]`), you can ignore
it — the kit works without it but loses that feature.

If a step fails with a Python traceback, copy the last 20 lines and either:
- File a GitHub issue with that text + your preflight JSON, or
- Run `bash scripts/build-bundle.sh` and attach the produced zip — it contains
  every log the maintainers need to debug.

## What the wizard does NOT do

- It does not push anything to your printers — you must explicitly dispatch a
  print from the UI.
- It does not require you to create any cloud accounts.
- It does not collect telemetry.
- It does not modify your global git or system configuration.

Anything other than those four claims is a bug. File it.
