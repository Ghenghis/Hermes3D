"""Unit tests for the second-wave agentic enhancements."""

from __future__ import annotations

import time

import pytest

# ---------------------------------------------------------------------------
# LLM provider abstraction
# ---------------------------------------------------------------------------


def test_llm_provider_config_from_env_defaults(monkeypatch):
    from hermes3d.core.llm.providers import LLMProvider, ProviderConfig

    for k in (
        "HERMES3D_LLM_PROVIDER",
        "HERMES3D_LLM_BASE_URL",
        "HERMES3D_LLM_MODEL",
        "HERMES3D_LLM_API_KEY",
    ):
        monkeypatch.delenv(k, raising=False)
    cfg = ProviderConfig.from_env()
    # ADR-015: LM Studio is the canonical local default; Ollama is the
    # documented fallback (callers select_provider_with_fallback if needed).
    assert cfg.provider == LLMProvider.LMSTUDIO
    assert cfg.base_url.startswith("http://127.0.0.1:1234")
    assert cfg.api_key is None


def test_llm_provider_config_from_env_ollama_fallback(monkeypatch):
    from hermes3d.core.llm.providers import LLMProvider, ProviderConfig

    monkeypatch.setenv("HERMES3D_LLM_PROVIDER", "ollama")
    for k in ("HERMES3D_LLM_BASE_URL", "HERMES3D_LLM_MODEL", "HERMES3D_LLM_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    cfg = ProviderConfig.from_env()
    assert cfg.provider == LLMProvider.OLLAMA
    assert cfg.base_url.startswith("http://127.0.0.1:11434")


def test_llm_provider_config_from_env_lmstudio(monkeypatch):
    from hermes3d.core.llm.providers import LLMProvider, ProviderConfig

    monkeypatch.setenv("HERMES3D_LLM_PROVIDER", "lmstudio")
    monkeypatch.setenv("HERMES3D_LLM_MODEL", "qwen2.5-7b-instruct")
    cfg = ProviderConfig.from_env()
    assert cfg.provider == LLMProvider.LMSTUDIO
    assert cfg.model == "qwen2.5-7b-instruct"


def test_llm_select_provider_returns_correct_class():
    from hermes3d.core.llm.providers import (
        LLMProvider,
        LMStudioProvider,
        OllamaProvider,
        ProviderConfig,
        VLLMProvider,
        select_provider,
    )

    p = select_provider(
        ProviderConfig(LLMProvider.OLLAMA, "http://127.0.0.1:11434", "qwen2.5-coder")
    )
    assert isinstance(p, OllamaProvider)
    p = select_provider(ProviderConfig(LLMProvider.LMSTUDIO, "http://127.0.0.1:1234/v1", "x"))
    assert isinstance(p, LMStudioProvider)
    p = select_provider(ProviderConfig(LLMProvider.VLLM, "http://127.0.0.1:8000/v1", "x"))
    assert isinstance(p, VLLMProvider)


def test_llm_openrouter_requires_api_key():
    from hermes3d.core.llm.providers import (
        LLMProvider,
        ProviderConfig,
        ProviderUnavailable,
        select_provider,
    )

    cfg = ProviderConfig(
        LLMProvider.OPENROUTER, "https://openrouter.ai/api/v1", "qwen", api_key=None
    )
    with pytest.raises(ProviderUnavailable):
        select_provider(cfg)


def test_llm_extract_json_handles_fences_and_preamble():
    from hermes3d.core.llm.providers import extract_json

    raw = """Sure, here is the result:
```json
{"verdict": "approve", "confidence": 0.83}
```
"""
    parsed = extract_json(raw)
    assert parsed["verdict"] == "approve"
    assert parsed["confidence"] == 0.83


def test_llm_extract_json_handles_raw_object():
    from hermes3d.core.llm.providers import extract_json

    raw = '{"a": 1, "b": [1,2,3]}'
    parsed = extract_json(raw)
    assert parsed == {"a": 1, "b": [1, 2, 3]}


def test_llm_extract_json_finds_object_in_prose():
    from hermes3d.core.llm.providers import extract_json

    raw = 'yeah I think the answer is {"verdict":"reject"} based on this stuff'
    assert extract_json(raw) == {"verdict": "reject"}


def test_llm_extract_json_raises_when_no_json():
    from hermes3d.core.llm.providers import extract_json

    with pytest.raises(ValueError):
        extract_json("totally not json at all, just words")


def test_llm_provider_unavailable_when_unreachable():
    from hermes3d.core.llm.providers import (
        LLMProvider,
        OllamaProvider,
        ProviderConfig,
        ProviderUnavailable,
    )

    cfg = ProviderConfig(LLMProvider.OLLAMA, "http://127.0.0.1:1", "missing", timeout_seconds=0.5)
    p = OllamaProvider(cfg)
    assert p.available() is False
    with pytest.raises(ProviderUnavailable):
        p.generate("hello")


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------


def test_tool_registry_register_and_call():
    from hermes3d.core.agents.tool_registry import ToolRegistry, register_tool

    reg = ToolRegistry()

    @register_tool(
        name="echo",
        description="Echo input",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
        registry=reg,
    )
    def echo(text: str) -> str:
        return text

    assert "echo" in reg
    assert reg.call("echo", text="hello") == "hello"
    spec = reg.get("echo")
    assert spec.description == "Echo input"
    schema = spec.to_json_schema()
    assert schema["name"] == "echo"
    assert schema["parameters"]["required"] == ["text"]


def test_tool_registry_rejects_duplicate_names():
    from hermes3d.core.agents.tool_registry import ToolRegistry, register_tool

    reg = ToolRegistry()

    @register_tool(name="t", description="d", parameters={"type": "object"}, registry=reg)
    def t1() -> int:
        return 1

    with pytest.raises(ValueError):

        @register_tool(name="t", description="d", parameters={"type": "object"}, registry=reg)
        def t2() -> int:
            return 2


def test_tool_registry_rejects_invalid_names():
    from hermes3d.core.agents.tool_registry import ToolRegistry, ToolSpec

    reg = ToolRegistry()
    bad = ToolSpec(
        name="bad name with spaces",
        description="x",
        parameters={"type": "object"},
        handler=lambda: None,
    )
    with pytest.raises(ValueError):
        reg.register(bad)


def test_tool_registry_filters_by_category_and_tag():
    from hermes3d.core.agents.tool_registry import ToolRegistry, register_tool

    reg = ToolRegistry()

    @register_tool(
        name="slice_one",
        description="x",
        parameters={"type": "object"},
        category="slicer",
        tags=("io", "blocking"),
        registry=reg,
    )
    def s() -> str:
        return "ok"

    @register_tool(
        name="dispatch_one",
        description="y",
        parameters={"type": "object"},
        category="dispatch",
        tags=("planning",),
        registry=reg,
    )
    def d() -> str:
        return "ok"

    assert {t.name for t in reg.by_category("slicer")} == {"slice_one"}
    assert {t.name for t in reg.by_tag("planning")} == {"dispatch_one"}
    assert set(reg.categories()) == {"slicer", "dispatch"}


def test_tool_registry_call_filters_unknown_kwargs():
    from hermes3d.core.agents.tool_registry import ToolRegistry, register_tool

    reg = ToolRegistry()

    @register_tool(name="add", description="add", parameters={"type": "object"}, registry=reg)
    def add(x: int, y: int) -> int:
        return x + y

    assert reg.call("add", x=2, y=3, ignore_me="zzz") == 5


def test_tool_registry_manifest_shape():
    from hermes3d.core.agents.tool_registry import ToolRegistry, register_tool

    reg = ToolRegistry()

    @register_tool(name="ping", description="ping", parameters={"type": "object"}, registry=reg)
    def p() -> str:
        return "pong"

    m = reg.manifest()
    assert m["tool_count"] == 1
    assert m["tools"][0]["name"] == "ping"


# ---------------------------------------------------------------------------
# Quality scorer
# ---------------------------------------------------------------------------


def test_quality_score_perfect_success_no_feedback():
    from hermes3d.core.agents.quality_scorer import (
        PrintOutcome,
        ScoringInput,
        score_print,
    )

    inp = ScoringInput(
        outcome=PrintOutcome.SUCCESS,
        predicted_duration_seconds=3600,
        actual_duration_seconds=3650,
    )
    report = score_print(inp)
    # No user feedback caps overall around 0.85; that's intentional headroom.
    assert 0.78 <= report.overall_score <= 0.90
    assert report.outcome == PrintOutcome.SUCCESS


def test_quality_score_perfect_success_with_5_star():
    from hermes3d.core.agents.quality_scorer import (
        PrintOutcome,
        ScoringInput,
        score_print,
    )

    inp = ScoringInput(
        outcome=PrintOutcome.SUCCESS,
        predicted_duration_seconds=3600,
        actual_duration_seconds=3600,
        user_rating_1_to_5=5,
    )
    report = score_print(inp)
    assert report.overall_score >= 0.95


def test_quality_score_failure_low():
    from hermes3d.core.agents.quality_scorer import (
        PrintOutcome,
        ScoringInput,
        score_print,
    )

    inp = ScoringInput(
        outcome=PrintOutcome.FAILED,
        spaghetti_detected=True,
        gcode_risk_flags=["aggressive_z_lift", "no_brim"],
        pause_count=2,
        user_rating_1_to_5=1,
        layer_shift_detected=True,
    )
    report = score_print(inp)
    # FAILED outcome + user rating 1/5 + layer shift + spaghetti = clearly bad
    assert report.overall_score < 0.30


def test_quality_score_partial_with_obico_pauses():
    from hermes3d.core.agents.quality_scorer import (
        PrintOutcome,
        ScoringInput,
        score_print,
    )

    inp = ScoringInput(
        outcome=PrintOutcome.PARTIAL,
        obico_pause_count=1,
        layer_shift_detected=True,
        user_rating_1_to_5=2,
    )
    report = score_print(inp)
    assert 0.20 <= report.overall_score <= 0.55


def test_quality_score_explainability():
    from hermes3d.core.agents.quality_scorer import (
        PrintOutcome,
        ScoringInput,
        score_print,
    )

    report = score_print(ScoringInput(outcome=PrintOutcome.SUCCESS))
    assert any(
        d.name == "outcome" and "without manual intervention" in " ".join(d.reasons)
        for d in report.dimensions
    )
    d = report.to_dict()
    assert "dimensions" in d
    assert isinstance(d["overall_score"], float)


# ---------------------------------------------------------------------------
# Self-improvement loop
# ---------------------------------------------------------------------------


def _make_obs(printer="prusa_mk3s", material="PLA", outcome="success", params=None):
    from hermes3d.core.agents.quality_scorer import (
        PrintOutcome,
        ScoringInput,
        score_print,
    )
    from hermes3d.core.intelligence.self_improvement import PrintObservation

    outcome_enum = {
        "success": PrintOutcome.SUCCESS,
        "failed": PrintOutcome.FAILED,
        "partial": PrintOutcome.PARTIAL,
    }[outcome]
    quality = score_print(
        ScoringInput(
            outcome=outcome_enum,
            predicted_duration_seconds=3600,
            actual_duration_seconds=3600 if outcome == "success" else 1800,
            user_rating_1_to_5=5 if outcome == "success" else 1,
        )
    )
    return PrintObservation(
        printer_id=printer,
        material=material,
        parameters=params or {},
        quality=quality,
    )


def test_self_improvement_reinforces_existing_skill(tmp_path):
    from hermes3d.core.intelligence.self_improvement import run_once
    from hermes3d.core.memory.skill_store import SkillKind, SkillScope, SkillStore

    store = SkillStore(tmp_path / "skills.json")
    skill = store.add(
        skill_kind=SkillKind.PARAMETER_OVERRIDE,
        name="pla_mk3s_first_layer_speed=20",
        scope=SkillScope(printer_id="prusa_mk3s", material="PLA"),
        body={"parameter": "first_layer_speed", "value": 20},
        confidence=0.5,
    )
    initial_conf = skill.confidence

    obs = [_make_obs(outcome="success") for _ in range(3)]
    report = run_once(store, obs)
    updated = store.get(skill.skill_id)
    assert updated.confidence > initial_conf
    assert any(u.skill_id == skill.skill_id for u in report.reinforcements)


def test_self_improvement_weakens_on_failures(tmp_path):
    from hermes3d.core.intelligence.self_improvement import run_once
    from hermes3d.core.memory.skill_store import SkillKind, SkillScope, SkillStore

    store = SkillStore(tmp_path / "skills.json")
    skill = store.add(
        skill_kind=SkillKind.PARAMETER_OVERRIDE,
        name="asa_t1_chamber=55",
        scope=SkillScope(printer_id="flsun_t1_a", material="ASA"),
        body={"parameter": "chamber_temp", "value": 55},
        confidence=0.7,
    )

    obs = [_make_obs(printer="flsun_t1_a", material="ASA", outcome="failed") for _ in range(3)]
    report = run_once(store, obs)
    updated = store.get(skill.skill_id)
    assert updated.confidence < 0.7
    assert any(u.skill_id == skill.skill_id for u in report.weakenings)


def test_self_improvement_proposes_new_skills(tmp_path):
    from hermes3d.core.intelligence.self_improvement import run_once
    from hermes3d.core.memory.skill_store import SkillStore

    store = SkillStore(tmp_path / "skills.json")
    obs = [
        _make_obs(
            printer="creality_cr10s", material="PETG", params={"bed_temp": 80}, outcome="success"
        )
        for _ in range(4)
    ]
    report = run_once(store, obs)
    assert len(report.new_skills) >= 1
    created = report.new_skills[0]
    assert "PETG_on_creality_cr10s" in created.skill_name


def test_self_improvement_retirement_floor(tmp_path):
    from hermes3d.core.intelligence.self_improvement import (
        RETIREMENT_FLOOR,
        run_once,
    )
    from hermes3d.core.memory.skill_store import SkillKind, SkillScope, SkillStore

    store = SkillStore(tmp_path / "skills.json")
    skill = store.add(
        skill_kind=SkillKind.PARAMETER_OVERRIDE,
        name="bad_skill",
        scope=SkillScope(printer_id="prusa_mk3s", material="PLA"),
        body={"parameter": "x", "value": 1},
        confidence=RETIREMENT_FLOOR - 0.01,
    )
    skill.evidence_count = 6
    store.save()

    report = run_once(store, [])
    assert any(u.skill_id == skill.skill_id for u in report.retirements)


# ---------------------------------------------------------------------------
# Vector memory
# ---------------------------------------------------------------------------


def test_vector_memory_tfidf_finds_relevant_skill(tmp_path):
    from hermes3d.core.memory.skill_store import SkillKind, SkillScope, SkillStore
    from hermes3d.core.memory.vector_memory import VectorMemory

    store = SkillStore(tmp_path / "skills.json")
    store.add(
        skill_kind=SkillKind.MATERIAL_QUIRK,
        name="asa_chamber_boost",
        scope=SkillScope(material="ASA"),
        body={"chamber_temp": 55},
        notes="ASA layer adhesion improves dramatically with enclosed chamber heating",
    )
    store.add(
        skill_kind=SkillKind.PRINTER_QUIRK,
        name="mk3s_pa_value",
        scope=SkillScope(printer_id="prusa_mk3s"),
        body={"pressure_advance": 0.045},
        notes="Prusa MK3S optimal pressure advance value for PLA",
    )

    vm = VectorMemory(store, backend="tfidf")
    hits = vm.search("ASA layers delaminating", top_k=2)
    assert hits
    # ASA-related skill should rank first.
    assert hits[0].skill.name == "asa_chamber_boost"


def test_vector_memory_dynamic_add(tmp_path):
    from hermes3d.core.memory.skill_store import SkillKind, SkillScope, SkillStore
    from hermes3d.core.memory.vector_memory import VectorMemory

    store = SkillStore(tmp_path / "skills.json")
    vm = VectorMemory(store, backend="tfidf")
    assert len(vm) == 0

    skill = store.add(
        skill_kind=SkillKind.SCHEDULING_PREF,
        name="tronxy_x5sa_quiet_at_night",
        scope=SkillScope(printer_id="tronxy_x5sa_pro"),
        body={"max_speed_after_2200": 80},
        notes="Tronxy X5SA Pro is loud at night — limit speed after 22:00",
    )
    vm.add(skill)
    hits = vm.search("loud printer at night", top_k=1)
    assert hits and hits[0].skill.skill_id == skill.skill_id


def test_vector_memory_handles_empty_store(tmp_path):
    from hermes3d.core.memory.skill_store import SkillStore
    from hermes3d.core.memory.vector_memory import VectorMemory

    vm = VectorMemory(SkillStore(tmp_path / "skills.json"), backend="tfidf")
    assert vm.search("anything", top_k=5) == []


# ---------------------------------------------------------------------------
# Incident detector
# ---------------------------------------------------------------------------


def test_incident_detector_network_loss():
    from hermes3d.core.agents.incident_detector import (
        IncidentDetector,
        IncidentType,
        PrinterPing,
    )

    det = IncidentDetector(network_loss_pings=3)
    events: list = []
    for i in range(3):
        events += det.ingest_ping(
            PrinterPing(printer_id="flsun_t1_a", timestamp=time.time() + i, reachable=False)
        )
    types = {e.incident_type for e in events}
    assert IncidentType.NETWORK_LOSS in types


def test_incident_detector_no_false_alarm_on_single_blip():
    from hermes3d.core.agents.incident_detector import (
        IncidentDetector,
        IncidentType,
        PrinterPing,
    )

    det = IncidentDetector(network_loss_pings=3)
    events = det.ingest_ping(PrinterPing(printer_id="prusa_mk3s", timestamp=1.0, reachable=False))
    types = {e.incident_type for e in events}
    assert IncidentType.NETWORK_LOSS not in types


def test_incident_detector_runaway_temp_critical():
    from hermes3d.core.agents.incident_detector import (
        IncidentDetector,
        IncidentSeverity,
        IncidentType,
        PrinterPing,
    )

    det = IncidentDetector()
    events = det.ingest_ping(
        PrinterPing(
            printer_id="creality_cr10s",
            timestamp=1.0,
            reachable=True,
            klippy_state="ready",
            print_state="printing",
            hotend_temp_c=260.0,
            hotend_target_c=215.0,
        )
    )
    runaway = [e for e in events if e.incident_type == IncidentType.RUNAWAY_TEMP]
    assert runaway and runaway[0].severity == IncidentSeverity.CRITICAL


def test_incident_detector_obico_signal():
    from hermes3d.core.agents.incident_detector import (
        IncidentDetector,
        IncidentType,
        PrinterPing,
    )

    det = IncidentDetector()
    events = det.ingest_ping(
        PrinterPing(
            printer_id="flsun_s1",
            timestamp=1.0,
            reachable=True,
            klippy_state="ready",
            print_state="printing",
            obico_failure_score=0.55,
        )
    )
    types = {e.incident_type for e in events}
    assert IncidentType.OBICO_FAILURE_SIGNAL in types


def test_incident_detector_filament_runout():
    from hermes3d.core.agents.incident_detector import (
        IncidentDetector,
        IncidentType,
        PrinterPing,
    )

    det = IncidentDetector()
    events = det.ingest_ping(
        PrinterPing(
            printer_id="prusa_mk3s",
            timestamp=1.0,
            reachable=True,
            print_state="printing",
            filament_present=False,
        )
    )
    types = {e.incident_type for e in events}
    assert IncidentType.FILAMENT_RUNOUT in types


def test_incident_detector_print_stalled():
    from hermes3d.core.agents.incident_detector import (
        IncidentDetector,
        IncidentType,
        PrinterPing,
    )

    det = IncidentDetector(stall_seconds=600, ping_window=20)
    base = 1000.0
    # Send 5 pings with progress unchanged spanning >600s.
    events: list = []
    for i in range(5):
        events += det.ingest_ping(
            PrinterPing(
                printer_id="flsun_v400",
                timestamp=base + i * 200,
                reachable=True,
                klippy_state="ready",
                print_state="printing",
                progress=0.42,
            )
        )
    types = {e.incident_type for e in events}
    assert IncidentType.PRINT_STALLED in types


def test_incident_detector_power_loss_suspected():
    from hermes3d.core.agents.incident_detector import (
        IncidentDetector,
        IncidentType,
        PrinterPing,
    )

    det = IncidentDetector()
    det.ingest_ping(
        PrinterPing(
            printer_id="tronxy_d01_pro",
            timestamp=1.0,
            reachable=True,
            klippy_state="ready",
            print_state="printing",
            progress=0.5,
        )
    )
    events = det.ingest_ping(
        PrinterPing(
            printer_id="tronxy_d01_pro",
            timestamp=2.0,
            reachable=True,
            klippy_state="shutdown",
            print_state="standby",
        )
    )
    types = {e.incident_type for e in events}
    assert IncidentType.POWER_LOSS_SUSPECTED in types


# ---------------------------------------------------------------------------
# Remote control bridge
# ---------------------------------------------------------------------------


def test_remote_control_help_command():
    from hermes3d.core.agents.tool_registry import ToolRegistry
    from hermes3d.core.integrations.remote_control import (
        RemoteControlBridge,
        RemoteControlConfig,
    )

    bridge = RemoteControlBridge(
        config=RemoteControlConfig(),
        registry=ToolRegistry(),
    )
    resp = bridge.handle_text(chat_id="123", user="dave", text="help")
    assert "tools" in resp.text.lower()


def test_remote_control_list_tools():
    from hermes3d.core.agents.tool_registry import ToolRegistry, register_tool
    from hermes3d.core.integrations.remote_control import (
        RemoteControlBridge,
        RemoteControlConfig,
    )

    reg = ToolRegistry()

    @register_tool(
        name="ping_fleet", description="ping the fleet", parameters={"type": "object"}, registry=reg
    )
    def _ping() -> str:
        return "pong"

    bridge = RemoteControlBridge(config=RemoteControlConfig(), registry=reg)
    resp = bridge.handle_text(chat_id="123", user="dave", text="tools")
    assert "ping_fleet" in resp.text


def test_remote_control_invokes_tool():
    from hermes3d.core.agents.tool_registry import ToolRegistry, register_tool
    from hermes3d.core.integrations.remote_control import (
        RemoteControlBridge,
        RemoteControlConfig,
    )

    reg = ToolRegistry()

    @register_tool(
        name="add", description="add two numbers", parameters={"type": "object"}, registry=reg
    )
    def add(a: int, b: int) -> int:
        return a + b

    bridge = RemoteControlBridge(
        config=RemoteControlConfig(rate_limit_seconds=0.0),
        registry=reg,
    )
    resp = bridge.handle_text(chat_id="123", user="dave", text="add a=2 b=3")
    assert "5" in resp.text


def test_remote_control_unknown_tool():
    from hermes3d.core.agents.tool_registry import ToolRegistry
    from hermes3d.core.integrations.remote_control import (
        RemoteControlBridge,
        RemoteControlConfig,
    )

    bridge = RemoteControlBridge(config=RemoteControlConfig(), registry=ToolRegistry())
    resp = bridge.handle_text(chat_id="123", user="dave", text="/nope x=1")
    assert "Unknown tool" in resp.text


def test_remote_control_rate_limit():
    from hermes3d.core.agents.tool_registry import ToolRegistry, register_tool
    from hermes3d.core.integrations.remote_control import (
        RemoteControlBridge,
        RemoteControlConfig,
    )

    reg = ToolRegistry()

    @register_tool(name="x", description="x", parameters={"type": "object"}, registry=reg)
    def x() -> str:
        return "ok"

    bridge = RemoteControlBridge(
        config=RemoteControlConfig(rate_limit_seconds=10.0),
        registry=reg,
    )
    a = bridge.handle_text(chat_id="9", user="dave", text="x")
    b = bridge.handle_text(chat_id="9", user="dave", text="x")
    assert "ok" in a.text or "✅" in a.text
    assert "rate limited" in b.text


# ---------------------------------------------------------------------------
# Farm discovery
# ---------------------------------------------------------------------------


def test_farm_discovery_expand_targets_cidr():
    from hermes3d.core.integrations.farm_discovery import expand_targets

    result = expand_targets(["192.168.1.10", "10.0.0.0/30"])
    assert "192.168.1.10" in result
    # /30 has 2 host bits → 2 usable hosts
    assert "10.0.0.1" in result
    assert "10.0.0.2" in result


def test_farm_discovery_expand_targets_ignores_garbage():
    from hermes3d.core.integrations.farm_discovery import expand_targets

    # Empty/whitespace are dropped; CIDR-shaped garbage that fails to parse is also dropped.
    # Bare hostnames pass through (we don't try to be DNS).
    assert expand_targets(["", "  ", "not-a-cidr/xxx"]) == []
    assert expand_targets(["printer-01.local", "  ", "10.0.0.5"]) == [
        "printer-01.local",
        "10.0.0.5",
    ]


# ---------------------------------------------------------------------------
# LangGraph adapter
# ---------------------------------------------------------------------------


def test_langgraph_adapter_renders_source(tmp_path):
    from hermes3d.core.orchestration.langgraph_adapter import (
        export_to_file,
        to_langgraph_source,
    )
    from hermes3d.core.orchestration.print_workflow import build_print_workflow

    graph = build_print_workflow()
    source = to_langgraph_source(graph)
    assert "from langgraph.graph import StateGraph" in source
    assert "def build_pipeline()" in source
    # Every hermes3d node should appear as a wrapper.
    for name in graph.node_names:
        assert f"node_{name.replace('-', '_').lower()}" in source

    out = tmp_path / "exported.py"
    export_to_file(graph, str(out))
    assert out.exists() and out.stat().st_size > 0


def test_langgraph_adapter_rejects_empty_graph():
    from hermes3d.core.orchestration.agent_graph import WorkflowGraph
    from hermes3d.core.orchestration.langgraph_adapter import to_langgraph_source

    g = WorkflowGraph(name="empty")
    with pytest.raises(ValueError):
        to_langgraph_source(g)
