; W18-A7 Print Queue Workflow Proof — minimal valid G-code fixture
; Audit-only artifact reference: must NOT be physically printed.
; This file's path is referenced by the SubmitJobDialog test as the
; artifact source. The backend `POST /api/jobs` does not require the
; file to exist on disk to enqueue (the JobCreate model has no
; artifact_path column), but the fixture is real enough that an
; operator-driven flow could later attach it to the `artifacts` table.
;
; Geometry: 10mm x 10mm x 5mm single-perimeter calibration cube.
; Slicer profile is intentionally generic; this is NOT a printable
; production gcode (no heating, no fan, no retraction). It is a
; structural fixture that proves "any 50-line valid G-code" can be
; referenced.
;
; Generated 2026-05-11 by w18-a7 agent. License: same as Hermes3D.
G21              ; set units to millimeters
G90              ; absolute positioning
M82              ; absolute extruder mode
G92 E0           ; reset extruder to 0
G28              ; home all axes
G1 Z5 F5000      ; lift nozzle 5mm
G1 X0 Y0 F3000   ; move to origin
; ---- Layer 1 (z=0.2mm) ----
G1 Z0.2 F1500
G1 X0 Y0 E0 F1500
G1 X10 Y0 E0.4 F1500
G1 X10 Y10 E0.8 F1500
G1 X0 Y10 E1.2 F1500
G1 X0 Y0 E1.6 F1500
; ---- Layer 2 (z=0.4mm) ----
G1 Z0.4 F1500
G1 X0 Y0 E1.6 F1500
G1 X10 Y0 E2.0 F1500
G1 X10 Y10 E2.4 F1500
G1 X0 Y10 E2.8 F1500
G1 X0 Y0 E3.2 F1500
; ---- Layer 3 (z=0.6mm) ----
G1 Z0.6 F1500
G1 X0 Y0 E3.2 F1500
G1 X10 Y0 E3.6 F1500
G1 X10 Y10 E4.0 F1500
G1 X0 Y10 E4.4 F1500
G1 X0 Y0 E4.8 F1500
; ---- Layer 4 (z=0.8mm) ----
G1 Z0.8 F1500
G1 X0 Y0 E4.8 F1500
G1 X10 Y0 E5.2 F1500
G1 X10 Y10 E5.6 F1500
G1 X0 Y10 E6.0 F1500
G1 X0 Y0 E6.4 F1500
; ---- Layer 5 (z=1.0mm) ----
G1 Z1.0 F1500
G1 X0 Y0 E6.4 F1500
G1 X10 Y0 E6.8 F1500
G1 X10 Y10 E7.2 F1500
G1 X0 Y10 E7.6 F1500
G1 X0 Y0 E8.0 F1500
; ---- Layer 6 (z=1.2mm) ----
G1 Z1.2 F1500
G1 X0 Y0 E8.0 F1500
G1 X10 Y0 E8.4 F1500
G1 X10 Y10 E8.8 F1500
G1 X0 Y10 E9.2 F1500
G1 X0 Y0 E9.6 F1500
G92 E0           ; reset extruder
G1 Z10 F5000     ; lift nozzle
G1 X0 Y0 F3000   ; park
M84              ; disable steppers
; End of fixture file — total perimeter ~ 60mm * 6 layers
