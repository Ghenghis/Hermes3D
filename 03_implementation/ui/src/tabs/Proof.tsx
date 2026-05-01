/**
 * Proof & Reports tab — Phase 2 mock-only per TAB_SPECS.md §11.
 *
 * Proof bundles · gate matrix · screenshots/artifacts · commit/branch
 * metadata · artifact download (locked).
 */
import { useState } from "react";
import { Panel } from "../components/layout/Panel";
import { ProofChip } from "../components/badges/ProofChip";
import { StatusBadge, type StatusTone } from "../components/badges/StatusBadge";
import { LockedAction } from "../components/badges/LockedAction";
import { MOCK_PROOF_BUNDLES } from "../data/mock/proof";
import type { GateVerdict } from "../types/proof";

const GATE_TONE: Record<GateVerdict, StatusTone> = {
  pass: "green",
  fail: "red",
  skip: "muted",
  pending: "amber",
};

const SCREENSHOTS = [
  { id: "ss-001", name: "dashboard_checkpoint4_1920x1080_v2.png", size_kb: 287 },
  { id: "ss-002", name: "dashboard_checkpoint4_1920x1080.png", size_kb: 247 },
  { id: "ss-003", name: "Hermes3D.png (visual contract)", size_kb: 51 },
];

export function ProofTab() {
  const [selectedId, setSelectedId] = useState(MOCK_PROOF_BUNDLES[0].id);
  const selected = MOCK_PROOF_BUNDLES.find((b) => b.id === selectedId) ?? MOCK_PROOF_BUNDLES[0];

  return (
    <div className="grid grid-cols-12 gap-2.5 auto-rows-min" data-testid="proof-root">
      <div className="col-span-12 lg:col-span-4">
        <Panel
          id="proof.bundles"
          title="PROOF BUNDLES"
          dense
          status={{ tone: "green", label: `${MOCK_PROOF_BUNDLES.length} verified` }}
          className="h-[440px]"
        >
          <ul className="flex flex-col gap-1.5 h-full overflow-auto text-xs">
            {MOCK_PROOF_BUNDLES.map((b) => (
              <li key={b.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(b.id)}
                  className={[
                    "w-full flex flex-col gap-0.5 px-2 py-1.5 rounded border text-left",
                    b.id === selectedId
                      ? "bg-surface2 border-accent-cyan/40"
                      : "bg-surface2/30 border-border hover:border-accent-cyan/20",
                  ].join(" ")}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-fg font-medium truncate text-[11px]">{b.id}</span>
                    <ProofChip status={b.verdict === "verified" ? "verified" : "pending"} />
                  </div>
                  <div className="text-muted text-[10px] font-mono truncate">{b.branch}</div>
                  <div className="text-muted text-[10px] font-mono">
                    {b.files_count} files · {(b.size_bytes / 1024).toFixed(1)} KB · {b.gates.filter((g) => g.verdict === "pass").length}/{b.gates.length} gates pass
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
      <div className="col-span-12 lg:col-span-8">
        <Panel
          id="proof.detail"
          title={`BUNDLE · ${selected.id}`}
          dense
          status={{ tone: "green", label: selected.verdict }}
          headerExtra={<ProofChip status={selected.verdict === "verified" ? "verified" : "pending"} />}
          className="h-[440px]"
        >
          <div className="grid grid-cols-2 gap-3 h-full text-xs">
            <div className="flex flex-col gap-2">
              <div className="text-muted text-[10px] uppercase tracking-wide">Metadata</div>
              <KV k="Bundle ID" v={<span className="font-mono">{selected.id}</span>} />
              <KV k="Branch" v={<span className="font-mono">{selected.branch}</span>} />
              <KV k="Commit" v={<span className="font-mono">{selected.commit}</span>} />
              <KV
                k="SHA-256"
                v={<span className="font-mono text-[10px] truncate block">{selected.sha256}</span>}
              />
              <KV k="Files" v={String(selected.files_count)} />
              <KV k="Size" v={`${(selected.size_bytes / 1024).toFixed(1)} KB`} />
              <KV k="Built" v={<span className="font-mono">{selected.ts_utc}</span>} />
              <div className="mt-auto flex flex-wrap gap-1.5 pt-2 border-t border-border">
                <LockedAction label="Download bundle" hint="locked · adapter phase" />
                <LockedAction label="Verify SHA-256" />
                <LockedAction label="Open evidence ledger" />
              </div>
            </div>
            <div className="flex flex-col gap-1.5 overflow-auto">
              <div className="text-muted text-[10px] uppercase tracking-wide">
                Gate Matrix · {selected.gates.filter((g) => g.verdict === "pass").length}/{selected.gates.length} pass
              </div>
              <ul className="flex flex-col gap-0.5">
                {selected.gates.map((g) => (
                  <li key={g.layer} className="flex items-center gap-2 text-[11px]">
                    <StatusBadge tone={GATE_TONE[g.verdict]} label={g.verdict} />
                    <span className="text-fg flex-1 truncate">{g.layer}</span>
                    <span className="text-muted font-mono shrink-0">
                      {g.duration_s != null ? `${g.duration_s}s` : "—"}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Panel>
      </div>
      <div className="col-span-12">
        <Panel
          id="proof.screenshots"
          title="SCREENSHOTS / ARTIFACTS"
          dense
          status={{ tone: "muted", label: `${SCREENSHOTS.length} files` }}
          className="h-[180px]"
        >
          <ul className="grid grid-cols-1 md:grid-cols-3 gap-2 h-full overflow-auto text-xs">
            {SCREENSHOTS.map((s) => (
              <li
                key={s.id}
                className="flex items-center gap-2 px-2 py-1.5 rounded bg-surface2/40 border border-border"
              >
                <div className="h-9 w-9 rounded bg-bg border border-border flex items-center justify-center text-muted font-mono text-[10px] shrink-0">
                  png
                </div>
                <div className="flex-1 min-w-0 leading-tight">
                  <div className="text-fg font-mono truncate text-[11px]">{s.name}</div>
                  <div className="text-muted text-[10px] font-mono">{s.size_kb} KB</div>
                </div>
                <LockedAction label="Open" hint="locked · file open is a Phase 6 capability" />
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}

function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex flex-col min-w-0 leading-tight">
      <span className="text-muted text-[10px] uppercase tracking-wide">{k}</span>
      <span className="text-fg text-[12px] truncate">{v}</span>
    </div>
  );
}
