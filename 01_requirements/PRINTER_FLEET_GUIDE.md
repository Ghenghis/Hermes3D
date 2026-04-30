# PRINTER FLEET GUIDE — Hermes3D-OS Lite

> Operator's guide to the 12 printers Hermes3D-OS is built around.
> What each printer is good for, what it isn't, and how the dispatcher
> reasons about them.

---

## The fleet (12 printers, 3 kinematics)

| ID | Manufacturer / Model | Kinematics | Bed | Z height | Sweet spot |
|----|----------------------|-----------|-----|----------|------------|
| `flsun_qqs_pro` | FLSUN Q5 / QQ-S Pro | Delta | Ø260 mm | 360 mm | Tall thin parts; PLA/PETG |
| `flsun_t1_a` | FLSUN T1 (unit A) | Delta | Ø260 mm | 330 mm | High speed PLA, ABS in enclosure |
| `flsun_t1_b` | FLSUN T1 (unit B) | Delta | Ø260 mm | 330 mm | Same as T1A — second unit for parallel jobs |
| `flsun_super_racer` | FLSUN Super Racer | Delta | Ø260 mm | 330 mm | Speed runs, PLA showpieces |
| `flsun_s1` | FLSUN S1 | Delta | Ø320 mm | 430 mm | The biggest delta in the fleet — vases, lampshades |
| `flsun_v400` | FLSUN V400 | Delta | Ø300 mm | 410 mm | Direct-drive delta — TPU, PETG |
| `creality_cr10s` | Creality CR-10S | Cartesian | 300 × 300 mm | 400 mm | Wide flat parts; budget workhorse |
| `creality_cr6_max` | Creality CR-6 Max | Cartesian | 400 × 400 mm | 400 mm | Big flat parts; the largest cartesian bed |
| `prusa_mk3s` | Prusa i3 MK3S+ | Cartesian | 250 × 210 mm | 210 mm | Reliability king — use when failure is expensive |
| `sovol_sv01` | Sovol SV01 | Cartesian | 280 × 240 mm | 300 mm | Solid mid-size cartesian |
| `tronxy_d01_pro` | Tronxy D01 Pro | CoreXY | 330 × 330 mm | 400 mm | Fast, but Z-wobble above 180 mm — see skill pack |
| `tronxy_x5sa_pro` | Tronxy X5SA Pro | CoreXY | 330 × 330 mm | 400 mm | Larger CoreXY, enclosure-friendly |

The canonical source of truth is `config/printers.toml`. Any change to
the fleet should go there first; the Python profiles
(`core.printers.printer_profiles.FLEET`) are loaded from that file.

---

## Bed shape geometry

Two bed shapes are modelled:

- **Rectangular** — `BedShape(kind="rectangular", x_mm, y_mm)`.
- **Circular (delta)** — `BedShape(kind="circular", diameter_mm)`.

`fits_bed(printer, bbox_xy)`:

- Rectangular: bbox X ≤ x_mm and bbox Y ≤ y_mm.
- Circular: the part's enclosing circle radius ≤ printer's radius
  (i.e., `hypot(bbox_x, bbox_y) / 2 ≤ diameter / 2`).

The dispatcher uses the same `fits_bed` check; you can never get a
"fits" decision that wouldn't actually fit.

---

## Material capability matrix

Material support per printer is encoded in
`core.agents.materials.MATERIAL_CAPABILITY` and validated by the
material truth gate.

| Material | Requires direct drive | Requires enclosure | Requires hardened nozzle |
|----------|------------------------|---------------------|---------------------------|
| PLA | no | no | no |
| PETG | no | no | no |
| ABS | no | yes | no |
| ASA | no | yes | no |
| PC | no | yes | no |
| TPU | yes | no | no |
| Nylon (PA) | no | yes | no |
| PA-CF | no | yes | yes |
| PETG-CF | no | no | yes |
| PLA-CF | no | no | yes |

A printer is "material capable" iff it satisfies every requirement for
the material. The dispatcher won't even score a printer that can't run
the material.

---

## Dispatcher strategies

When you call dispatch with a part bbox + material, you can hint a
strategy. AUTO is the default and blends multiple criteria.

| Strategy | Optimises for |
|----------|---------------|
| `auto` | Weighted blend (quality + least busy + smallest fit) |
| `fastest` | Highest `max_print_speed_mm_s` profile field |
| `quality` | Lowest accel + direct drive (less ringing) |
| `largest_bed` | Biggest bed that fits |
| `smallest_fit` | Smallest bed that fits — efficient farm use |
| `least_busy` | Idle preferred over printing |
| `delta_prefer` | Tall / cylindrical parts → delta |
| `cartesian_prefer` | Wide / flat parts → cartesian |

The result is a `DispatchDecision` with:

- `selected_printer_id` — the chosen one (None if nothing fits)
- `candidates` — every printer scored, with `fits`, `eligible`,
  `reasons`, and `blockers`
- `rationale` — a human-readable explanation
- `strategy_used` — echoed back for clarity

---

## Per-printer skill packs

Three printer-specific skill packs ship with v5:

- `flsun_t1_essentials.json` — pressure advance + input shaper +
  flow ratio for both T1 units
- `tronxy_d01_quirks.json` — Z-wobble warning above 180 mm; bed mesh
  refresh interval
- `asa_general_tips.json` — material-level pack, applies to every
  enclosure-capable printer

Load them via the Gradio Skill Pack Manager tab, or:

```bash
python -m hermes3d.cli skill import config/skill_packs/flsun_t1_essentials.json
```

---

## Adding a new printer

1. Edit `config/printers.toml`. Add a `[printers.<your_id>]` block
   with `manufacturer`, `model`, `kinematics`, `bed_shape`, `z_height_mm`,
   `max_print_speed_mm_s`, `direct_drive`, `enclosed`, `hardened_nozzle`,
   `moonraker_url`.
2. Add the corresponding Klipper config under
   `config/klipper/<your_id>.printer.cfg`. The kit ships with templates
   you can copy from.
3. Run the doctor: `pwsh scripts/doctor.ps1`.
4. Run the tests: `pwsh scripts/test.ps1`. The fleet count test will
   pick up the new printer automatically.
5. (Optional) Build a printer-specific skill pack and put it under
   `config/skill_packs/`.
6. Update `00_overview/contract/HONESTY_LEDGER.md` if the new printer changes
   any tier annotation.

---

## Removing a printer

1. Comment out (don't delete — keep history) the `[printers.<id>]`
   block in `printers.toml`, with a date and reason.
2. Run the tests; the fleet count test will tell you what to update.
3. Migrate any pending jobs targeting that printer to a different one
   via the Gradio Job Queue tab.

---

## Day-to-day operations

- **Check fleet status:** Gradio "Print Farm Dashboard" tab, or
  `python -m hermes3d.cli fleet --json | jq .`.
- **Add a job:** drop the STL into the Gradio Dispatch tab, or
  `hermes3d queue add <stl> --material PETG --quality normal`.
- **Inspect why a printer wasn't picked:** Gradio Dispatch tab shows
  every candidate's `blockers`. CLI:
  `hermes3d dispatch <stl> --material PETG --explain`.
- **Calibrate a printer:** Gradio Calibration tab. The macro is
  shown read-only; firing it requires confirmation.
- **Browse skill memory:** Gradio Skill Memory Browser tab, or
  `hermes3d skill list --kind printer_quirk`.

---

## Hardware references

The kit assumes Klipper firmware on every printer (Marlin printers are
not actively supported in v5 — OctoPrint is the bridge for them, see
`core.integrations.octoprint_client`).

- Klipper docs: https://www.klipper3d.org/
- Moonraker docs: https://moonraker.readthedocs.io/
- Mainsail / Fluidd / Obico are independent web UIs — Hermes3D
  coexists with them; nothing in this kit conflicts.
