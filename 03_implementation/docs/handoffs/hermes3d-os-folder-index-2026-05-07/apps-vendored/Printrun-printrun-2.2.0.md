# Printrun-printrun-2.2.0

## Purpose

Printrun is a suite of Python hosts for 3D printers (and other CNC machines): `printcore` (library), `pronsole` (interactive CLI host), and `pronterface` (wxPython GUI host). It also includes `plater`/`gcodeplater` plate-layout tools. In Hermes3D OS it is the printer-host module — the final stage that streams G-code over serial/USB to the physical printer and exposes an RPC server for remote control.

The vendored snapshot also has prebuilt Windows binaries adjacent to it (`Pronsole.exe`, `Pronterface.exe`, `printrun-2.2.0_windows_x64_py3.10.zip`), so Hermes3D can either run from source or shell out to the bundled exe.

## Tech stack

- Language: Python 3
- GUI: wxPython (pronterface, plater)
- Packaging: setuptools (`setup.py`), `requirements.txt`, `pyproject.toml`, `MANIFEST.in`
- Distribution: PyPI (`Printrun`), GitHub binary releases
- License: GPL (per `COPYING`)

## Status

Vendored snapshot, not a git repo.
- Last write time of folder: 2024-10-20 12:57:24
- Version: `__version__ = "2.2.0"` (from `printrun/printcore.py`)
- Folder name encodes the upstream tag (`printrun-2.2.0`).

## Top-level layout

- `printrun/` — Python package (printcore, host code)
- `images/`, `screenshots/`, `locale/`
- `testfiles/`, `tests/`, `testtools/`
- `pronterface.py`, `pronsole.py`, `printcore.py`, `plater.py`, `gcodeplater.py`, `calibrateextruder.py` — top-level entry scripts
- `setup.py`, `pyproject.toml`, `requirements.txt`, `MANIFEST.in`
- Linux desktop integration: `pronterface.desktop` + `.appdata.xml`, `pronsole.desktop` + `.appdata.xml`, `plater.desktop` + `.appdata.xml`
- Icons / launcher images: `pronterface.ico`, `pronterface.png`, `pronsole.ico`, `pronsole.png`, `plater.ico`, `plater.png`, `P-face.icns`
- `release_windows.bat`, `auth.config`, `custombtn.txt`, `dot.pronsolerc.example`
- `README.md`, `README.cleanup`, `README.i18n`, `NEWS.md`, `CONTRIBUTORS.md`, `COPYING`, `TODO`
- `.gitignore`, `.gitmodules`

## Hermes3D integration (INFERRED)

INFERRED: registered as the printer-driver module:
- `kind: cli` (pronsole) + `gui` (pronterface)
- `binary: pronsole.py | Pronsole.exe` for headless H3D dispatch
- `verifier: pronsole --help` exit 0 + version match `2.2.0`
- `capabilities: ["printer.connect.serial", "gcode.stream", "rpc.server"]`
- The README documents an RPC server, which Source OS most likely probes via HTTP/socket as a runtime liveness check.
- Locale overlays from the sibling `apps\locale` folder feed `pronterface`.

## Disk size

3.66 MB

## SVG diagram

<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200">
  <rect x="0" y="0" width="400" height="200" fill="#fafafa" stroke="#ddd"/>
  <rect x="10" y="80" width="90" height="50" fill="#dcdcdc" stroke="#222"/>
  <text x="55" y="100" text-anchor="middle" font-family="sans-serif" font-size="12">G-code</text>
  <text x="55" y="118" text-anchor="middle" font-family="sans-serif" font-size="10">from slicer</text>
  <rect x="130" y="40" width="130" height="120" fill="#10b981" stroke="#222"/>
  <text x="195" y="65" text-anchor="middle" font-family="sans-serif" font-size="13" fill="#fff">Printrun 2.2.0</text>
  <text x="195" y="85" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#fff">printcore lib</text>
  <text x="195" y="100" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#fff">pronsole CLI</text>
  <text x="195" y="115" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#fff">pronterface GUI</text>
  <text x="195" y="130" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#fff">RPC server</text>
  <text x="195" y="148" text-anchor="middle" font-family="sans-serif" font-size="9" fill="#fff">plater / gcodeplater</text>
  <rect x="290" y="80" width="100" height="50" fill="#dc2626" stroke="#222"/>
  <text x="340" y="100" text-anchor="middle" font-family="sans-serif" font-size="13" fill="#fff">3D printer</text>
  <text x="340" y="118" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#fff">serial / USB</text>
  <line x1="100" y1="105" x2="130" y2="105" stroke="#222" stroke-width="2" marker-end="url(#a6)"/>
  <line x1="260" y1="105" x2="290" y2="105" stroke="#222" stroke-width="2" marker-end="url(#a6)"/>
  <defs>
    <marker id="a6" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#222"/>
    </marker>
  </defs>
  <text x="200" y="25" text-anchor="middle" font-family="sans-serif" font-size="14" font-weight="bold">Printrun host stage</text>
  <text x="200" y="180" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#666">Streams G-code over serial; exposes RPC for H3D</text>
</svg>
