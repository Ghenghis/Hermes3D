import { useCallback, useEffect, useState } from "react";
import { adapters } from "../api/adapters";
import { ArtifactList } from "../components/artifacts/ArtifactList";
import { PANEL_POLL_MS, usePollingEffect } from "../hooks/_useQuery";
import type { Agent } from "../types/agent";
import type { Artifact, ArtifactGate, ArtifactStage, ArtifactType, EvidenceForm } from "../types/artifact";
import type { Job } from "../types/job";

// ---- Proof bundle types (Lane 15 — H3D-CLAUDE-ARTIFACTS-PROOF) ----
interface ProofFile {
  filename: string;
  size_bytes: number;
  modified_utc: string;
  type: string;
}

interface ProofManifest {
  proof_dir: string;
  file_count: number;
  total_size_bytes: number;
  files: ProofFile[];
}

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT = (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_BASE_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}`;

const EVIDENCE_TYPES: ArtifactType[] = ["photo", "screenshot", "mesh", "g-code", "log", "agent_attachment", "other"];

export function ArtifactsTab() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [proofManifest, setProofManifest] = useState<ProofManifest | null>(null);
  const [proofError, setProofError] = useState<string | null>(null);
  const [form, setForm] = useState<EvidenceForm>({
    jobId: "",
    evidenceType: "screenshot",
    agent: "",
    stage: "MODELING",
    gate: "MODEL_APPROVAL",
    label: "",
    file: null,
    notes: "",
  });
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const ready = form.jobId !== "" && form.agent !== "" && form.label !== "" && form.file != null;

  // One-shot mount: pull jobs + agents (used to seed the upload form's
  // default jobId / agent). These rarely change during a session and
  // re-fetching them would clobber the operator's current form selection.
  useEffect(() => {
    void adapters.getJobs().then((next) => {
      setJobs(next);
      setForm((current) => ({ ...current, jobId: next[0]?.id ?? "" }));
    });
    void adapters.getAgents().then((next) => {
      setAgents(next);
      setForm((current) => ({ ...current, agent: next[0]?.role ?? "" }));
    });
  }, []);

  // W21-MVP-5: poll the artifact-list and proof-manifest panels on
  // PANEL_POLL_MS so newly-produced artifacts (mesh, proof, thumbnail)
  // surface without a manual reload. Re-uses the existing fetch
  // functions; ``usePollingEffect`` cancels overlap + cleans up on
  // unmount.
  const refresh = useCallback(async () => {
    const [arts, proofResult] = await Promise.all([
      loadArtifacts(),
      loadProofManifest(LIVE_BASE_URL),
    ]);
    setArtifacts(arts);
    if (proofResult.ok) {
      setProofManifest(proofResult.manifest);
      setProofError(null);
    } else {
      setProofError(proofResult.error);
    }
  }, []);
  usePollingEffect(refresh, PANEL_POLL_MS, [refresh]);

  const attach = async () => {
    const file = form.file;
    if (!ready || file == null) {
      return;
    }
    const body = await file.arrayBuffer();
    const params = new URLSearchParams({
      job_id: String(form.jobId),
      evidence_type: form.evidenceType,
      stage: form.stage,
      gate: form.gate,
      agent: form.agent,
      label: form.label,
      notes: form.notes,
    });
    try {
      const response = await fetch(`${LIVE_BASE_URL}/api/artifacts?${params.toString()}`, {
        method: "POST",
        headers: { Accept: "application/json" },
        body,
        cache: "no-store",
      });
      const payload: unknown = await response.json().catch(() => null);
      const artifact = normalizeArtifact(payload);
      if (!response.ok || !artifact) {
        setActionMessage(`Blocked: ${artifactSummary(payload, response.statusText)}`);
        return;
      }
      setArtifacts((current) => [artifact, ...current]);
      setForm((current) => ({ ...current, label: "", notes: "", file: null }));
      setActionMessage(`Attached ${artifact.name} from the live artifacts API.`);
      await adapters.emitProofEvent("artifacts.evidence.attached", { job_id: form.jobId, label: form.label, uploaded: true, artifact_id: artifact.id });
    } catch (error) {
      setActionMessage(`Blocked: ${errorMessage(error)}`);
    }
  };

  return (
    <div data-testid="artifacts-root" className="flex min-h-[calc(100vh-6.5rem)] flex-col gap-3">
      <div className="grid gap-3 lg:grid-cols-12">
      <section id="artifacts.attach" className="rounded border border-border bg-surface p-4 lg:col-span-5">
        <h2 className="text-base font-semibold text-fg">ATTACH VISUAL EVIDENCE</h2>
        <div className="mt-4 grid gap-2 text-sm">
          <select className="rounded border border-border bg-bg px-2 py-1 text-fg" value={String(form.jobId)} onChange={(event) => setForm({ ...form, jobId: event.target.value })}>{jobs.map((job) => <option key={job.id} value={job.id}>{job.name}</option>)}</select>
          <select className="rounded border border-border bg-bg px-2 py-1 text-fg" value={form.evidenceType} onChange={(event) => setForm({ ...form, evidenceType: event.target.value as ArtifactType })}>{EVIDENCE_TYPES.map((type) => <option key={type}>{type}</option>)}</select>
          <select className="rounded border border-border bg-bg px-2 py-1 text-fg" value={form.agent} onChange={(event) => setForm({ ...form, agent: event.target.value })}>{agents.map((agent) => <option key={agent.id}>{agent.role}</option>)}</select>
          <input className="rounded border border-border bg-bg px-2 py-1 text-fg" aria-label="Stage" value={form.stage} onChange={(event) => setForm({ ...form, stage: event.target.value as ArtifactStage })} />
          <input className="rounded border border-border bg-bg px-2 py-1 text-fg" aria-label="Gate" value={form.gate} onChange={(event) => setForm({ ...form, gate: event.target.value as ArtifactGate })} />
          <input className="rounded border border-border bg-bg px-2 py-1 text-fg" aria-label="Label" value={form.label} onChange={(event) => setForm({ ...form, label: event.target.value })} />
          <input className="text-sm text-muted" type="file" accept=".png,.jpg,.stl,.3mf,.gcode,.txt,.log,.md" onChange={(event) => setForm({ ...form, file: event.target.files?.[0] ?? null })} />
          <textarea className="rounded border border-border bg-bg px-2 py-1 text-fg" aria-label="Notes" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
          <button type="button" disabled={!ready} onClick={() => void attach()} className="rounded bg-accent-blue px-3 py-2 font-semibold text-bg disabled:opacity-50">Attach Evidence</button>
        </div>
        {actionMessage && <div className="mt-3 rounded border border-border bg-bg/40 p-2 text-xs text-muted">{actionMessage}</div>}
      </section>
      <section id="artifacts.list" className="flex min-h-0 flex-col rounded border border-border bg-surface p-4 lg:col-span-7">
        <h2 className="text-base font-semibold text-fg">Artifacts List</h2>
        <p className="text-sm text-muted">Models, evidence, G-code, and logs</p>
        <div className="mt-4 grid min-h-0 flex-1 content-start gap-3 overflow-auto">
          <ArtifactList artifacts={artifacts} onView={(artifact) => void viewArtifact(artifact, setActionMessage)} />
        </div>
      </section>
      </div>
      <section id="artifacts.proof" data-testid="proof-bundles" className="rounded border border-border bg-surface p-4">
        <h2 className="text-base font-semibold text-fg">Proof Bundles</h2>
        <p className="text-sm text-muted">Auditable proof files from 03_implementation/proof/ — scanned live from the server.</p>
        {proofError && <div className="mt-2 rounded border border-border bg-bg/40 p-2 text-xs text-muted">{proofError}</div>}
        {proofManifest && (
          <div className="mt-3">
            <div className="mb-2 text-xs text-muted">{proofManifest.file_count} files · {(proofManifest.total_size_bytes / 1024).toFixed(1)} KB total · scanned from {proofManifest.proof_dir}</div>
            <div className="grid gap-1">
              {proofManifest.files.map((f) => (
                <div key={f.filename} className="grid grid-cols-[auto_1fr_auto_auto] items-center gap-2 rounded border border-border bg-bg/40 px-3 py-2 text-sm">
                  <span className="rounded bg-surface2 px-2 py-0.5 text-xs text-muted">{f.type}</span>
                  <span className="min-w-0 truncate text-fg">{f.filename}</span>
                  <span className="text-xs text-muted">{(f.size_bytes / 1024).toFixed(1)} KB</span>
                  <a
                    href={`${LIVE_BASE_URL}/api/artifacts/proof/${encodeURIComponent(f.filename)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded border border-border px-2 py-1 text-xs text-fg hover:bg-surface2"
                  >
                    View
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}
        {!proofManifest && !proofError && <div className="mt-2 text-sm text-muted">Loading proof bundles…</div>}
      </section>
    </div>
  );
}

async function loadProofManifest(baseUrl: string): Promise<{ ok: true; manifest: ProofManifest } | { ok: false; error: string }> {
  try {
    const response = await fetch(`${baseUrl}/api/artifacts/list`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) {
      return { ok: false, error: `Proof API returned ${response.status} ${response.statusText}` };
    }
    const payload: unknown = await response.json();
    if (!isRecord(payload) || !Array.isArray(payload.files)) {
      return { ok: false, error: "Proof API returned unexpected shape" };
    }
    return {
      ok: true,
      manifest: {
        proof_dir: stringValue(payload.proof_dir),
        file_count: numberValue(payload.file_count),
        total_size_bytes: numberValue(payload.total_size_bytes),
        files: (payload.files as unknown[]).map((f) => {
          const r = isRecord(f) ? f : {};
          return {
            filename: stringValue(r.filename),
            size_bytes: numberValue(r.size_bytes),
            modified_utc: stringValue(r.modified_utc),
            type: stringValue(r.type) || "file",
          };
        }),
      },
    };
  } catch (error) {
    return { ok: false, error: `Proof API unreachable: ${errorMessage(error)}` };
  }
}

async function loadArtifacts(): Promise<Artifact[]> {
  try {
    const response = await fetch(`${LIVE_BASE_URL}/api/artifacts`, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) {
      return [];
    }
    const payload: unknown = await response.json();
    return Array.isArray(payload) ? payload.map(normalizeArtifact).filter((artifact): artifact is Artifact => artifact != null) : [];
  } catch {
    return [];
  }
}

async function viewArtifact(artifact: Artifact, setMessage: (message: string) => void) {
  const target = artifact.downloadUrl || `${LIVE_BASE_URL}/api/artifacts/${encodeURIComponent(artifact.id)}/download`;
  try {
    const response = await fetch(target, { method: "GET", cache: "no-store" });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    window.open(target, "_blank", "noopener,noreferrer");
    setMessage(`Opened artifact ${artifact.name}.`);
    await adapters.emitProofEvent("artifacts.artifact.viewed", { artifact_id: artifact.id, accepted: true });
  } catch (error) {
    setMessage(`Blocked: artifact view failed: ${errorMessage(error)}`);
  }
}

function normalizeArtifact(value: unknown): Artifact | null {
  if (!isRecord(value)) {
    return null;
  }
  const id = stringValue(value.id);
  if (!id) {
    return null;
  }
  const jobId = stringValue(value.jobId ?? value.job_id) || "unassigned";
  const path = stringValue(value.path ?? value.file_path);
  const sizeBytes = numberValue(value.sizeBytes ?? value.file_size);
  return {
    id,
    jobId,
    jobTitle: stringValue(value.jobTitle) || String(jobId),
    type: artifactTypeValue(value.type ?? value.evidence_type),
    name: stringValue(value.name ?? value.label) || path.split(/[\\/]/).pop() || id,
    path,
    stage: artifactStageValue(value.stage),
    gate: artifactGateValue(value.gate),
    agent: nullableString(value.agent),
    label: nullableString(value.label),
    notes: nullableString(value.notes),
    sizeBytes,
    createdAt: stringValue(value.createdAt ?? value.created_at),
    downloadUrl: stringValue(value.downloadUrl) || `${LIVE_BASE_URL}/api/artifacts/${encodeURIComponent(id)}/download`,
  };
}

function artifactSummary(value: unknown, fallback: string): string {
  if (!isRecord(value)) {
    return fallback || "Artifact upload failed with no JSON response.";
  }
  if (typeof value.detail === "string") {
    return value.detail;
  }
  if (isRecord(value.detail)) {
    return String(value.detail.reason ?? value.detail.error ?? JSON.stringify(value.detail));
  }
  return String(value.reason ?? value.error ?? fallback);
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Artifacts API is unreachable.";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function nullableString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function numberValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function artifactTypeValue(value: unknown): ArtifactType {
  return EVIDENCE_TYPES.includes(value as ArtifactType) ? value as ArtifactType : "other";
}

function artifactStageValue(value: unknown): ArtifactStage {
  const stages: ArtifactStage[] = ["INTAKE", "MODELING", "SLICING", "AGENT_CHAT", "PRINT_APPROVAL", "PRINT_RUN", "COMPLETE"];
  return stages.includes(value as ArtifactStage) ? value as ArtifactStage : "INTAKE";
}

function artifactGateValue(value: unknown): ArtifactGate | null {
  return typeof value === "string" && value.length > 0 ? value as ArtifactGate : null;
}
