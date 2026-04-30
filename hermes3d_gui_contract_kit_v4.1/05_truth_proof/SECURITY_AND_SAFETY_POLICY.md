# Security and Safety Policy

VPS cannot execute raw shell on Windows worker. Worker exposes only typed job endpoints. Job payloads validate against schema. Commands are allowlisted templates. Artifacts write to staging folders. Secrets never appear in proof bundles.

Printer write actions require printer allowlist, operator confirmation or explicit automation policy, emergency stop visible in UI, and audit log entry.

Blender MCP arbitrary Python must use a safe executor wrapper, restricted output paths, blocked network/file deletion/shell subprocess usage, timeboxes, and command hash capture.

No release if secrets are found, raw shell passthrough exists, direct main push occurred, printer write lacks audit log, or worker command lacks allowlist mapping.
