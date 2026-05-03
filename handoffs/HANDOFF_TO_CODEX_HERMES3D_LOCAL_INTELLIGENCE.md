# HANDOFF_TO_CODEX — LOCAL-INTELLIGENCE (SUPERSEDED — see splits below)

> **Status:** SUPERSEDED. The original mega-brief was split per the audit's M2 recommendation after the LOCAL-INTELLIGENCE audit returned VERDICT: FAIL on six critical issues (paths wrong, Settings tab nonexistent, mnemosyne PyPI name wrong, port-monitor not a library, llm_policy rewrite destructive).
>
> **Replaced by three independently-completable briefs:**
>
> 1. `HANDOFF_TO_CODEX_HERMES3D_LOCAL_LM_STUDIO.md` — Task 4a (LM Studio default + Ollama fallback + Hipfire optional)
> 2. `HANDOFF_TO_CODEX_HERMES3D_MNEMOSYNE_RECALL.md` — Task 4b (Mnemosyne recall layer)
> 3. `HANDOFF_TO_CODEX_HERMES3D_SERVICE_HEALTH.md` — Task 4c (in-house port probe + new top-level /health route)
>
> Each split is scope-tighter, has an audit-clean lock list, and can ship independently. If the Mnemosyne PyPI install hits a quirk, the LM Studio and Service Health work still ships.
>
> **Do NOT pick up this file.** Pick up the splits in order: 4a → 4b → 4c.
