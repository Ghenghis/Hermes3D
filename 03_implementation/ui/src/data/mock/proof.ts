/**
 * Proof bundles mock — anchors against the actual Phase 0 + Phase 1 bundles
 * we shipped (so the Dashboard's "Proof & Verification (LATEST)" card shows
 * real-feeling provenance even with mock data).
 */
import type { ProofBundle } from "../../types/proof";

export const MOCK_PROOF_BUNDLES: ProofBundle[] = [
  {
    id: "bundle-phase1-0e561f1",
    sha256: "ce50861d524dedf2fd679027c67833a83dc207b43b16a7cefca8f585f63cd24f",
    branch: "feat/phase-1-foundation",
    commit: "0e561f1ad968bb3a59980f31634e3f3629f3ef6c",
    ts_utc: "2026-05-01T08:14:31Z",
    files_count: 4,
    size_bytes: 12227,
    verdict: "verified",
    gates: [
      { layer: "Layer A — static gates", verdict: "pass", duration_s: 34 },
      { layer: "Layer B — ubuntu × py3.11", verdict: "pass", duration_s: 54 },
      { layer: "Layer B — ubuntu × py3.12", verdict: "pass", duration_s: 62 },
      { layer: "Layer B — windows × py3.11", verdict: "pass", duration_s: 228 },
      { layer: "Layer B — windows × py3.12", verdict: "pass", duration_s: 225 },
      { layer: "Layer C — integration", verdict: "pass", duration_s: 43 },
      { layer: "Layer D — UI E2E", verdict: "pass", duration_s: 91 },
      { layer: "Layer E — release dry-run", verdict: "skip", duration_s: null },
      { layer: "Layer F — honesty gates", verdict: "pass", duration_s: 8 },
      { layer: "Layer T — unified truth gate", verdict: "pass", duration_s: 83 },
      { layer: "Layer W — wizard E2E", verdict: "pass", duration_s: 9 },
    ],
  },
  {
    id: "bundle-phase0-b3efe3d",
    sha256: "36e9e40c6f903d9de74ba6d6dba9ff0a0c9fd9e701e337bafe3ca9bc857a0607",
    branch: "feat/phase-0-foundation-baseline",
    commit: "b3efe3dd9b20a55946ed97a63271a0c99e845588",
    ts_utc: "2026-05-01T00:37:06Z",
    files_count: 4,
    size_bytes: 9896,
    verdict: "verified",
    gates: [
      { layer: "Layer A — static gates", verdict: "pass", duration_s: 36 },
      { layer: "Layer B — all 4 matrix", verdict: "pass", duration_s: 280 },
      { layer: "Layer T — unified truth gate", verdict: "pass", duration_s: 83 },
    ],
  },
  {
    id: "bundle-rc1-6dd9e01",
    sha256: "91bc3c110b907b6da076a005c85d93546697b4efe122028fefe02345521aabfc",
    branch: "release/v5.3.0-rc1",
    commit: "6dd9e01f4e090663c7fdd87bb968f37b512de7ca",
    ts_utc: "2026-04-30T22:20:20Z",
    files_count: 52,
    size_bytes: 107874,
    verdict: "verified",
    gates: [
      { layer: "Layer A", verdict: "pass", duration_s: 35 },
      { layer: "Layer T (full)", verdict: "pass", duration_s: 76 },
    ],
  },
];

export const LATEST_BUNDLE = MOCK_PROOF_BUNDLES[0];
