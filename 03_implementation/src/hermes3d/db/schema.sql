PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS modules (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    section TEXT NOT NULL,
    priority TEXT NOT NULL,
    license TEXT,
    repo_url TEXT,
    local_path TEXT,
    install_state TEXT NOT NULL DEFAULT 'unavailable',
    install_progress INTEGER DEFAULT 0,
    detected_version TEXT,
    health TEXT,
    launch_kind TEXT,
    bridge_tasks TEXT,
    last_sync_at TEXT,
    lock_hash TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bridge_tasks (
    id TEXT PRIMARY KEY,
    module_id TEXT NOT NULL REFERENCES modules(id),
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    last_run_at TEXT,
    last_result TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS module_runtime_verifiers (
    module_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    runner_kind TEXT NOT NULL,
    tool_key TEXT,
    executable_path TEXT,
    args TEXT NOT NULL DEFAULT '[]',
    capabilities TEXT NOT NULL DEFAULT '[]',
    execute INTEGER NOT NULL DEFAULT 0,
    timeout_s INTEGER NOT NULL DEFAULT 12,
    enabled INTEGER NOT NULL DEFAULT 1,
    proof_gate_version TEXT NOT NULL DEFAULT 'runtime-verifier-v1',
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_module_runtime_verifiers_enabled
    ON module_runtime_verifiers(enabled, module_id);

CREATE TABLE IF NOT EXISTS module_runtime_setup_runs (
    id TEXT PRIMARY KEY,
    module_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    status TEXT NOT NULL,
    runner_kind TEXT,
    command_hash TEXT,
    exit_code INTEGER,
    output_head_sha256 TEXT,
    proof_event_id TEXT,
    started_at TEXT DEFAULT (datetime('now')),
    ended_at TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_module_runtime_setup_runs_module
    ON module_runtime_setup_runs(module_id, started_at DESC);

CREATE TABLE IF NOT EXISTS module_providers (
    id TEXT PRIMARY KEY,
    module_id TEXT NOT NULL REFERENCES modules(id),
    display_name TEXT NOT NULL,
    provider_kind TEXT NOT NULL,
    repo_url TEXT,
    install_command TEXT,
    verify_commands TEXT,
    capabilities TEXT,
    license TEXT,
    state TEXT NOT NULL DEFAULT 'available',
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    printer_id TEXT,
    dry_run INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS job_steps (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id),
    step_number INTEGER NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    started_at TEXT,
    ended_at TEXT,
    duration_s REAL,
    error TEXT
);

CREATE TABLE IF NOT EXISTS job_events (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id),
    event_type TEXT NOT NULL,
    source_agent TEXT,
    message TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    approval_type TEXT NOT NULL,
    job_id TEXT REFERENCES jobs(id),
    model_name TEXT,
    requesting_agent TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    decided_by TEXT,
    decided_at TEXT,
    notes TEXT,
    reason TEXT,
    requested_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    job_id TEXT REFERENCES jobs(id),
    evidence_type TEXT NOT NULL,
    agent TEXT,
    stage TEXT,
    gate TEXT,
    label TEXT,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS plugins (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    state TEXT NOT NULL DEFAULT 'PLANNED',
    config TEXT,
    activated_at TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS voice_assignments (
    agent_id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    voice_name TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'azure',
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS proof_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    source_agent TEXT,
    payload TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS code_history_snapshots (
    id TEXT PRIMARY KEY,
    workspace_root TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    snapshot_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    action_id TEXT,
    agent_id TEXT NOT NULL,
    proof_event_id TEXT,
    reason TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_code_history_snapshots_file
    ON code_history_snapshots(workspace_root, relative_path, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_code_history_snapshots_agent
    ON code_history_snapshots(agent_id, created_at DESC);

CREATE TABLE IF NOT EXISTS roadmap_items (
    id INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'NOT_STARTED',
    link_tab TEXT,
    link_section TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS onboarded_printers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT 'Generic',
    adapter TEXT NOT NULL DEFAULT 'moonraker',
    ip TEXT NOT NULL UNIQUE,
    moonraker_url TEXT NOT NULL UNIQUE,
    camera_url TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    safety_policy TEXT NOT NULL DEFAULT 'read_only',
    source_refs TEXT,
    probe_summary TEXT NOT NULL,
    created_by TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_onboarded_printers_status
    ON onboarded_printers(status);

CREATE TABLE IF NOT EXISTS truth_gate_results (
    id TEXT PRIMARY KEY,
    job_id TEXT REFERENCES jobs(id),
    gate_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    error TEXT,
    duration_s REAL,
    checked_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_conversations (
    id TEXT PRIMARY KEY,
    persona_id TEXT NOT NULL,
    role TEXT NOT NULL,
    message_type TEXT NOT NULL DEFAULT 'TEXT',
    content TEXT NOT NULL,
    action_id TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_autonomous_sessions (
    id TEXT PRIMARY KEY,
    activated_at TEXT NOT NULL,
    deactivated_at TEXT,
    activated_by TEXT NOT NULL DEFAULT 'user',
    deactivated_by TEXT,
    cadence_seconds INTEGER NOT NULL DEFAULT 60,
    actions_taken INTEGER DEFAULT 0,
    escalations INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS agent_autonomous_actions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES agent_autonomous_sessions(id),
    persona_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_payload TEXT NOT NULL,
    safety_agent_status TEXT NOT NULL,
    veto_reason TEXT,
    outcome TEXT NOT NULL,
    error_message TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_autonomous_actions_session
    ON agent_autonomous_actions(session_id);

CREATE TABLE IF NOT EXISTS idle_workbench_candidates (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'research',
    agent_id TEXT NOT NULL DEFAULT 'research-agent',
    status TEXT NOT NULL DEFAULT 'queued',
    risk_level TEXT NOT NULL DEFAULT 'low',
    summary TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'operator',
    source_url TEXT,
    target_tab TEXT,
    target_files TEXT NOT NULL DEFAULT '[]',
    branch_ref TEXT,
    gate_status TEXT NOT NULL DEFAULT '{}',
    proof_event_ids TEXT NOT NULL DEFAULT '[]',
    approval_id TEXT REFERENCES approvals(id),
    blocked_reason TEXT,
    created_by TEXT NOT NULL DEFAULT 'operator',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_idle_workbench_candidates_status
    ON idle_workbench_candidates(status, updated_at DESC);

CREATE TABLE IF NOT EXISTS idle_workbench_events (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES idle_workbench_candidates(id),
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'hermes-agent',
    payload TEXT NOT NULL DEFAULT '{}',
    proof_event_id TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_idle_workbench_events_candidate
    ON idle_workbench_events(candidate_id, created_at DESC);

CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    priority TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    source_agent_id TEXT,
    source_tab TEXT,
    action_url TEXT,
    action_label TEXT,
    read_at TEXT,
    dismissed_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_notifications_created_at
    ON notifications(created_at DESC);

CREATE TABLE IF NOT EXISTS anomaly_reports (
    id TEXT PRIMARY KEY,
    printer_id TEXT NOT NULL,
    confidence INTEGER NOT NULL CHECK(confidence >= 0 AND confidence <= 100),
    description TEXT NOT NULL,
    snapshot_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    reported_by TEXT NOT NULL DEFAULT 'agent',
    created_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS build_plate_clearance (
    printer_id TEXT PRIMARY KEY,
    state TEXT NOT NULL DEFAULT 'unknown',
    last_job_filename TEXT,
    source TEXT NOT NULL DEFAULT 'live_telemetry',
    reason TEXT,
    confirmed_by TEXT,
    confirmed_at TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);
