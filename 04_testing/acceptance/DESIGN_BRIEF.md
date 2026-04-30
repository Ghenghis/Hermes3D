# Desk Organizer — Design Brief

> The product. What we're modelling, and why.

---

## 1. The product

A **rectangular tray with adjustable internal compartments**, intended
to sit on a desktop and hold pens, USB drives, fastener-bag bits, or
similar small objects. The tray has:

- A flat base
- Four perimeter walls
- Internal divider walls (count parameterised)
- A 2 mm chamfer at every top edge for printability and hand-feel

The product is functional, visually plain, and printable in any of
the kit's supported materials. It is deliberately not "art" — the
point is that the kit handles a real, useful thing.

---

## 2. Parameter space

```python
@dataclass(frozen=True)
class DeskOrganizerParams:
    width_mm: float           # X — outside dimension
    depth_mm: float           # Y — outside dimension
    height_mm: float          # Z — outside dimension
    compartment_count: int    # number of compartments along X
    wall_thickness_mm: float  # perimeter + divider walls
    chamfer_mm: float = 2.0
```

Constraints (validated by the design generator):

- `width_mm`, `depth_mm`, `height_mm` ∈ [40, 400] mm
- `compartment_count` ∈ [1, 16]
- `wall_thickness_mm` ∈ [1.2, 4.0] mm
- `compartment_count × wall_thickness_mm < width_mm` — divider walls
  cannot occupy the entire interior

Out-of-range parameters raise `ValueError` with a clear message
(`tests/unit/test_desk_organizer.py` covers each bound).

---

## 3. The four canonical variants

The acceptance runner uses a fixed set of four variants. Every CI run
exercises all four:

### `compact` — 80 × 80 × 30 mm, 4 compartments
- Wall: 1.6 mm
- Tests: smallest sane size; should fit on every printer

### `standard` — 200 × 150 × 50 mm, 6 compartments
- Wall: 2.0 mm
- Tests: most common case; should fit on most printers

### `wide` — 350 × 280 × 60 mm, 8 compartments
- Wall: 2.4 mm
- Tests: excludes Prusa MK3S+ (250 × 210 bed) and most deltas;
  should fit CR-6 Max comfortably and CR-10S marginally

### `tall` — 120 × 120 × 320 mm, 4 compartments
- Wall: 2.0 mm
- Tests: exercises the Z-height check; should fit deltas and CR-10S
  but excludes Prusa MK3S+

---

## 4. Why parametric

A non-parametric STL is a single shape. We can dispatch it once and
prove the dispatch was correct.

A parametric model is a **family** of shapes. The acceptance runner
generates a different STL for each variant and dispatches all four —
proving that the kit handles dimensional variation without
short-circuiting on cached results.

The parameter space is small (5 numbers, 1 integer) but the geometric
diversity is large. A 350-mm-wide variant is a fundamentally
different dispatch problem than an 80-mm-wide one — most of the fleet
becomes ineligible.

---

## 5. STL generation

The generator (`core.design.desk_organizer.generate_organiser_stl`):

1. Builds the outer hollow box as a single mesh (4 walls + base).
2. Adds `compartment_count − 1` internal divider walls evenly spaced.
3. Applies the chamfer to every top edge.
4. Outputs a binary STL.

The generator uses only the standard library + `numpy` (always
available in the kit's runtime). It does **not** depend on Blender,
trimesh's CAD ops, or any other third-party CAD tool. This keeps the
acceptance suite fast and CI-portable.

---

## 6. Validation against `mesh_analyzer`

Every generated STL is required to pass these `mesh_analyzer` checks:

| Check | Required | Reason |
|-------|----------|--------|
| `is_watertight` | True | Slicer needs a closed mesh |
| `is_volume` | True | Trimesh recognises it as a solid |
| `triangle_count` | >0, <50_000 | Bounded — no runaway tessellation |
| `overhang_pct` | <5% at 50° threshold | The chamfered tops are gentle slopes |
| `risk_flags` | does not contain `non_watertight` or `nan_vertex` | Hard fail signals |

If any of these fail, the test crashes — the design generator has a
bug.

---

## 7. Out of scope (deliberately)

- **Lid.** A snap-fit lid would add geometric complexity without
  exercising new code paths.
- **Curves.** The walls are vertical and the floor is flat. A curved
  wall variant is a v6 stretch goal.
- **Multi-material.** The acceptance runner uses a single material
  per cell. Multi-material handling is a separate test in
  `tests/unit/test_dispatcher.py::test_dispatcher_multi_material`.

---

## 8. Provenance

The desk organizer was chosen because:

- Dave actually prints these. There's a row of them next to his
  workstation holding the things he's used to lose.
- Honey Bunny knocked the previous batch off the desk. The kit's
  mission is, in a sense, to make the next batch easier to replace.
- It's the simplest thing that exercises every relevant decision in
  the kit. The acceptance runner is short, fast, and meaningful.
