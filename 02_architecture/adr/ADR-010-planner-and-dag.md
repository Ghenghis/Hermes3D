# ADR-010: Planner and DAG Contract — Deterministic Template, Simulated Gen3D Boundary, Capability Extensions

## Status
Accepted for CP3.2-A design. No implementation code is introduced by this ADR.

## Context
Phase 3.1 established the read-only orchestration foundation in
[`ADR-009-orchestration-skeleton.md`](ADR-009-orchestration-skeleton.md):
a supervisor, capability tokens, an append-only ledger, and a localhost-only
bridge. Phase 3.2 extends that foundation with a Planner agent and a simulated
3D Generation read-only slice while preserving the same safety boundary:
no write adapters, no printer movement, no slicer or Blender execution, no
external provider calls, and no native window or process launch.

The execution plan for this phase is
[`00_overview/PHASE3_2_PLAN.md`](../../00_overview/PHASE3_2_PLAN.md). This ADR
summarizes that plan as the contract for CP3.2 work.

## Decision

### 1. DAG Schema
Phase 3.2 introduces a typed task DAG as data only. The first implementation
checkpoint that writes code must keep the DAG package free of I/O, adapters,
network, subprocesses, slicers, Blender, printer access, and UI logic.

The schema is:

| Field | Type | Rule |
|---|---|---|
| `dag_id` | string | Content-addressed or deterministic identifier for the plan. |
| `run_id` | string | Supervisor run identifier used for ledger correlation. |
| `nodes` | `TaskNode[]` | Non-empty ordered collection of typed task nodes. |
| `edges` | `TaskEdge[]` | Directed dependencies between node ids. |
| `max_depth` | integer | Hard cap of 12, matching the DTE 12-stage template. |
| `max_fanout` | integer | Hard cap on outgoing edges per node. |
| `metadata` | object | Deterministic planner metadata; no secrets or external handles. |

Each `TaskNode` contains:

| Field | Type | Rule |
|---|---|---|
| `node_id` | string | Unique within the DAG. |
| `tool` | string | Must be registered before dispatch. |
| `kind` | string | Planner-defined typed node category. |
| `inputs` | object | Canonical-JSON-serializable request payload. |
| `retry_budget` | integer | Finite bounded retry count. |
| `gate_set` | string[] | Named safety gates that must pass before dispatch. |
| `depends_on` | string[] | Parent node ids; must match `edges`. |

Each `TaskEdge` contains:

| Field | Type | Rule |
|---|---|---|
| `from_node` | string | Existing source node id. |
| `to_node` | string | Existing target node id. |
| `condition` | string | Deterministic condition name, defaulting to success. |

Validation rules:
- Cycles are refused.
- Depth greater than 12 is refused.
- Fanout is capped by the CP3.2-B unit-test contract.
- Edges may not reference missing nodes.
- A node may not name an unregistered tool.
- Retry budgets must be finite and bounded.

### 2. Planner Deterministic-Template Contract
The Planner agent in Phase 3.2 is deterministic-template-only. It accepts a
typed `PlanRequest` and returns a `PlanResult` containing a `TaskDAG`.

Rules:
- The Planner uses fixture templates only.
- The same prompt fixture must produce the same DAG sha across runs.
- The Planner must not import or call OpenAI, Anthropic, local LLM gateways, or
any external provider.
- The Planner must not call adapters directly.
- The Planner must not emit write-class tools such as printer movement, slicer
execution, Blender execution, or native launch operations.
- The Planner may emit placeholder Mesh QA or Slicer QA nodes only as
non-dispatched DAG data when the registered-tool check allows them in a later
phase. In Phase 3.2, unregistered placeholders are refused by R6.

### 3. Simulated Gen3D Boundary
Phase 3.2 includes a simulated 3D executor, not a real 3D-generation provider.

The only allowed simulated execution tool is:

```text
gen3d.generate
```

The simulated executor produces a deterministic `SimulatedModelArtifact` whose
sha is derived from the request fields, such as prompt and seed. The artifact is
written only under:

```text
var/orchestration/artifacts/
```

Rules:
- No TRELLIS, Hunyuan3D, TripoSR, MiniMax, or other provider call.
- No Blender MCP call.
- No slicer call.
- No printer call.
- No subprocess or shell call.
- No network dependency.
- No path escape outside `var/orchestration/artifacts/`.

UI execution remains locked in CP3.2-D: the 3D Generation tab may preview a
plan, but the "Generate" action remains a `LockedAction`.

### 4. Capability-Token Tool Extensions
ADR-009's token shape is unchanged. Phase 3.2 extends only the tool vocabulary.

New Phase 3 tool values:

| Tool | Purpose | Phase | Dangerous |
|---|---|---:|---|
| `planner.plan` | Convert a prompt fixture into a typed DAG. | 3 | false |
| `gen3d.generate` | Produce a deterministic simulated model artifact. | 3 | false |

Capability-token rules from ADR-009 still apply:
- R1: no token is refused.
- R2: unknown token is refused.
- R3: unauthorized tool is refused.
- R4: expired token is refused.
- R5: phase violation is refused.

Tokens scoped to `planner.plan` cannot invoke `gen3d.generate`, and tokens
scoped to `gen3d.generate` cannot invoke `planner.plan`.

### 5. Refusal Rule R6
Phase 3.2 adds one refusal rule:

| # | Trigger | Outcome |
|---|---|---|
| R6 | Planner emits a DAG node whose `tool` is not in the supervisor's registered tool set. | `Err::Forbidden("tool_unregistered")`; no node is dispatched. |

R6 applies before dispatch. If any node names an unregistered tool, the plan is
refused as a plan and no downstream executor runs. This prevents the Planner
from becoming an indirect route to tools that the supervisor has not admitted.

### 6. Bridge and UI Scope
CP3.2-A writes documentation only. Later CP3.2 checkpoints may add:

- `POST /api/plan/preview`, returning the DAG only and never executing it.
- `GET /api/runs/<run_id>`, returning a ledger-derived read-only summary.
- `planPreview(prompt)` on the existing UI AdapterAPI.
- A 3D Generation tab affordance that renders the returned DAG through existing
UI primitives while keeping "Generate" locked.

No new HTTP surface is implemented in CP3.2-A. Any future route remains
localhost-bound and read-only.

## Consequences
- Phase 3.2 grows the orchestration vocabulary without changing ADR-009's token
shape.
- All real provider, slicer, Blender, and printer integration remains deferred.
- Planner behavior is testable because it is fixture-driven and deterministic.
- The simulated Gen3D executor proves the Planner-DAG-Executor seam without
creating write capability.
- R6 makes registered tools the supervisor-owned boundary; a prompt cannot
smuggle an unregistered operation into the DAG.

## Cross-links
- [`00_overview/PHASE3_2_PLAN.md`](../../00_overview/PHASE3_2_PLAN.md)
- [`ADR-008-adapter-lifecycle-and-dock-undock.md`](ADR-008-adapter-lifecycle-and-dock-undock.md)
- [`ADR-009-orchestration-skeleton.md`](ADR-009-orchestration-skeleton.md)
