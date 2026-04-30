# TROUBLESHOOTING — Hermes3D-OS Lite

> Symptoms, causes, and concrete fixes. If the symptom isn't listed
> here, run `scripts/doctor.{ps1,sh}` first; it covers most.

---

## Install / setup

### `[FAIL] Python 3.11+ required`

You're on an older Python. The kit needs ≥3.11 for `tomllib` and
modern type-hint syntax.

**Fix:** install Python 3.11 or 3.12.

```powershell
winget install Python.Python.3.11
```

```bash
sudo apt install python3.11 python3.11-venv python3.11-dev
```

### `pip install -e .` complains about read-only filesystem

You're on Linux/WSL with system Python. Add `--break-system-packages`
or, better, use a venv.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### `ModuleNotFoundError: No module named 'hermes3d'` after install

The editable install didn't run. From `03_implementation/`:

```bash
pip install -e .
```

Or set `PYTHONPATH` manually:

```bash
export PYTHONPATH="$PWD/src:$PYTHONPATH"
```

```powershell
$env:PYTHONPATH = "$PWD\src;$env:PYTHONPATH"
```

### `verify_install.py` reports `[WARN] HERMES3D_PROOF_KEY not set`

This is a warning, not a failure. The kit uses the dev default key
(`hermes3d-default-proof-key-not-secret`). For production, set a strong random
value in `.env`:

```bash
HERMES3D_PROOF_KEY=$(openssl rand -hex 32)
```

---

## Runtime

### Gradio launcher fails to start with `address already in use`

Port 7860 is taken. Either close whatever's using it, or set:

```powershell
$env:GRADIO_SERVER_PORT = '7861'
pwsh scripts/run-dev.ps1
```

### REST API returns 500 on `/v1/fleet`

Likely cause: `printers.toml` was edited and now has a typo. Run:

```bash
python -c "import tomllib; tomllib.load(open('config/printers.toml','rb'))"
```

Any traceback identifies the line.

### Moonraker probes time out for every printer

Likely causes:

- The printer's Pi is offline.
- The Moonraker URL in `config/printers.toml` is wrong.
- A firewall is blocking outbound TCP from this host.

Test directly:

```bash
curl http://<printer-ip>:7125/printer/info
```

If that works, restart the supervisor daemon (it caches probes):

```bash
pkill -f hermes3d.core.supervisor.daemon
bash scripts/run-dev.sh
```

### Slicer never finishes / runs forever

The slicer has a 600-second timeout. If you're seeing 600 + warning
messages, the slicer is genuinely hung on the input.

Check `mesh_analyze` first:

```bash
python -m hermes3d.cli mesh analyse path/to/your.stl
```

If it reports `is_watertight: false` or a long list of `risk_flags`,
the mesh is the problem.

### Acceptance runner reports proof envelope verification failure

Either `HERMES3D_PROOF_KEY` was changed between the run that produced
the envelopes and the run that's verifying them, or the envelope file
was edited.

**Fix:** delete `var/acceptance-results/` and re-run:

```bash
rm -rf var/acceptance-results
python ../04_testing/acceptance/run_acceptance.py
```

---

## Tests

### `pytest` says `264 passed` locally but CI fails

Typical causes:

1. **Path separators.** A test hard-coded `/` in a path; CI on Windows
   trips on it. Use `pathlib.Path`.
2. **Locale.** A test compares against a localised string that's
   different on the CI runner. Force the locale or use a
   locale-independent assertion.
3. **Time zone.** A test compares timestamps; CI is UTC. Use UTC
   throughout, or freeze time with `freezegun`.

Reproduce CI locally:

```bash
docker run --rm -v "$PWD:/work" -w /work python:3.11 \
    bash -c "pip install -r 03_implementation/requirements.txt -r 03_implementation/requirements-dev.txt && cd 03_implementation && pytest"
```

### A single test flakes

By contract, flakes are bugs. Identify the cause:

```bash
pytest tests/unit/test_xxx.py::test_yyy -v --count=20  # needs pytest-repeat
```

The most common causes:

- **Implicit ordering** in a `dict` or `set` — sort outputs before
  asserting.
- **Time-dependent waits** — replace `sleep()` with deterministic
  state checks.
- **Shared filesystem state** — use `tmp_path` and `monkeypatch`.

If you genuinely cannot stabilise the test, file an issue with `flake`
in the title and add a `@pytest.mark.skip` with the issue reference.

---

## CI

### `forbidden-pattern scan` fails

You introduced a TODO/FIXME/STUB or a bare `except: pass`. Either:

- Implement the thing — preferred.
- Remove it from runtime code (move to a doc).
- If it's a legitimately spec-only `raise NotImplementedError` with a
  detailed remediation message, append `# noqa: forbidden_pattern_scan`
  on the same line and explain why in `HONESTY_LEDGER.md`.

### `honesty-diff` reports drift

The `KIT_MANIFEST.json` and the `HONESTY_LEDGER.md` disagree about a
file's tier. Either:

- Promote the file to runnable in the manifest by adding tests, or
- Demote the file to scaffold in the ledger honestly.

Regenerate the manifest after edits:

```bash
python 00_overview/contract/_generate_manifest.py
```

---

## Hardware

### Xolo dog Honey Bunny is sleeping on the printer

Move dog. Resume print. (Genuinely listed because it's the second
most common cause of false-failure incidents on Dave's farm.)

### A delta printer thinks it's homed but isn't

This is a Klippy state issue, not a Hermes3D issue. Run
`FIRMWARE_RESTART` from Mainsail/Fluidd, then re-home. Hermes3D will
pick up the new state on its next probe.

---

## Asking for help

If the troubleshooting steps above don't cover your symptom:

1. Run `scripts/doctor.{ps1,sh}` and paste the output.
2. Run `scripts/test.{ps1,sh}` and paste the failure trace.
3. Include the relevant section of `var/proof-report.json` if it's a
   correctness question.
4. Open a GitHub issue with all three.

The kit's contract (`00_overview/contract/MASTER_CONTRACT.md`) means that any
genuine bug here is a contract violation — we want to hear about it.
