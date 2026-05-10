import type { ProofBundle } from "../../types/proof";

export function CompilerProofSection({ proofs }: { proofs: ProofBundle[] }) {
  const latest = proofs[0] ?? null;

  return (
    <section className="rounded border border-border bg-surface2/30 p-3">
      <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted">
        Compiler Proof
      </h3>
      {latest ? (
        <div className="grid grid-cols-2 gap-2 text-xs">
          <Field label="Bundle" value={latest.id} />
          <Field label="Timestamp" value={latest.ts_utc} />
          <Field label="Result" value={latest.verdict.toUpperCase()} tone={latest.verdict === "verified" ? "text-accent-green" : "text-accent-red"} />
          <Field label="Evidence Hash" value={latest.sha256.slice(0, 12)} mono />
        </div>
      ) : (
        <div className="py-4 text-center text-xs text-muted">No proof bundle yet</div>
      )}
    </section>
  );
}

function Field({
  label,
  value,
  tone = "text-fg",
  mono = false,
}: {
  label: string;
  value: string;
  tone?: string;
  mono?: boolean;
}) {
  return (
    <div className="min-w-0">
      <div className="text-[10px] uppercase tracking-wide text-muted">{label}</div>
      <div className={`truncate ${tone} ${mono ? "font-mono" : ""}`}>{value}</div>
    </div>
  );
}
