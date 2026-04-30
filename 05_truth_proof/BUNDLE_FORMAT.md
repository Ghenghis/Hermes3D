# Hermes3D Proof Bundle Format (A.6)

Schema version: `bundle-1.0.0`

A **proof bundle** is a single signed zip aggregating every piece of
evidence produced by one Hermes3D build. It is the artifact a release
auditor inspects to verify that a tagged build is what the kit claims
it is.

## Zip layout

```
<git-sha-12>-<utc>.zip
├── manifest.json          # signed; schema = bundle-1.0.0
├── manifest.sig           # HMAC-SHA256 over canonical(manifest.json)
├── evidence_ledger.md     # claim → proof-file table (auto-generated)
├── tests/
│   ├── pytest-report.xml
│   └── pytest-report.html (optional; only if pytest-html installed)
├── logs/
│   ├── pytest.log
│   └── forbidden_scan.log
├── proof/
│   └── envelopes/         # copied from var/acceptance-results, var/dispatch
│       └── *.json         # existing per-dispatch HMAC envelopes
└── screenshots/           # populated when Playwright is wired in (A.3)
```

## `manifest.json` schema

```jsonc
{
  "schema_version": "bundle-1.0.0",
  "git":   { "sha": "...", "branch": "...", "dirty": false },
  "build": { "utc_iso": "2026-04-29T12:34:56+00:00",
             "run_id":  "abcdef012345-20260429T123456Z",
             "duration_seconds": 42.0 },
  "env":   { "python": "3.11.9", "python_impl": "CPython",
             "os": "Windows-11-...", "machine": "AMD64",
             "deps": { "pytest": "8.x", "trimesh": "...", "...": "..." } },
  "signer": { "identity": "<env HERMES3D_SIGNER_IDENTITY or 'unknown'>",
              "key_env_var": "HERMES3D_PROOF_KEY" },
  "files":  [ { "path": "tests/pytest-report.xml",
                "size": 12345,
                "sha256": "..." }, ... ]
}
```

`files[].path` is bundle-relative, forward-slash. `files[].sha256` is
SHA-256 over the on-disk bytes.

## Signature algorithm

- **Algorithm:** HMAC-SHA256 (RFC 2104).
- **Key:** `HERMES3D_PROOF_KEY` env var (UTF-8 bytes); a documented
  development default is used if unset, with a warning. The default
  key is **not** secret — production releases must set
  `HERMES3D_PROOF_KEY`.
- **Payload:** the canonical JSON of `manifest.json` with the
  `signature` field removed (it is not present at sign time anyway).
- **Canonicalisation:** identical to
  `hermes3d.core.proof.proof_envelope.canonical_payload` —
  `json.dumps(doc, sort_keys=True, separators=(",", ":"))`,
  UTF-8 encoded. This matches the format already used for per-dispatch
  proof envelopes so the same key handling and same digest-size apply.
- **Output:** `manifest.sig` contains `{"algorithm": "HMAC-SHA256",
  "value": "<hex digest>"}`.

## Verification

```bash
python 03-PROOF-SYSTEM/conformance_runner.py --bundle <bundle.zip>
```

Exits **0** when **all** of the following hold:

1. The zip opens and `ZipFile.testzip()` returns clean.
2. `manifest.json` parses and contains every required schema field;
   `schema_version` equals `bundle-1.0.0`.
3. `manifest.sig.algorithm == "HMAC-SHA256"` and the digest matches
   `HMAC(canonical(manifest), HERMES3D_PROOF_KEY)`.
4. Every entry in `manifest.files` exists in the zip with a matching
   sha256.
5. `evidence_ledger.md` exists and every `proof_envelope` row points
   at a file that is in the bundle.

Non-zero exit codes:

| code | meaning                                    |
|------|--------------------------------------------|
| 1    | one or more verification checks failed     |
| 2    | bundle missing/corrupt or schema unparseable |

JSON output: pass `--json` to receive a structured `{path, ok,
errors[], manifest}` document on stdout.

## Building a bundle

```bash
# bash
HERMES3D_PROOF_KEY=mykey bash scripts/build-bundle.sh

# PowerShell
$env:HERMES3D_PROOF_KEY = "mykey"
scripts\build-bundle.ps1
```

Optional flags (both wrappers): `--output <dir>` (default
`05_truth_proof/bundles/`) and `--key-env-var <NAME>` (default
`HERMES3D_PROOF_KEY`).

The script prints the absolute path, byte size, and sha256 digest of
the produced zip, then exits 0.

## References

- RFC 2104 — HMAC: Keyed-Hashing for Message Authentication.
- `02-SCAFFOLDING/src/hermes3d/core/proof/proof_envelope.py` —
  per-dispatch envelope signing (same key, same canonicalisation).
- `00-CONTRACT/HONESTY_LEDGER.md` — source for the `evidence_ledger.md`
  claim rows.
