# Release Rules

## rc1 rule
Do not cut rc1 unless all required gates are green and the QA record is green.

## UI-Final rule
UI-Final is post-rc1 unless explicitly chosen otherwise. It must pass screenshot gates before merging.

## External tool rule
External repos may be cloned and inspected, but production uses pinned versions and adapter gates.

## Printer safety rule
No live print or movement command in release tests unless user explicitly enables hardware-in-the-loop mode.
