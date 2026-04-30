# `agents/` — Role Manifests

This directory contains machine-readable manifests describing each automated
role in the Hermes3D contract kit. The goal: any orchestrator — Claude Code
multi-agent mode, n8n, GitHub Actions, a hand-rolled Python loop — can load
these YAMLs and dispatch the kit without guessing names, model tiers, gate
thresholds, or escalation paths.

## Files

- `_schema.json` — JSON Schema (draft 2020-12) every manifest must validate
  against.
- `<role>.yaml` — one file per role. Filename stem matches the `role` field.
- See `../scripts/validate-agents.py` for the validator.

## Convention

Each manifest is a flat YAML with these top-level keys (all required):

| key              | meaning                                                              |
|------------------|----------------------------------------------------------------------|
| `role`           | machine name, lowercase, matches filename stem                       |
| `description`    | one-sentence prose summary                                           |
| `model`          | LLM tier hint: `opus` \| `sonnet` \| `haiku`                          |
| `inputs`         | typed input contract (name, type, required, description)             |
| `action_sequence`| ordered list of steps; each is `run:` (shell), `tool:` (named tool), or `prompt:` |
| `outputs`        | files (`path:`) or named artifacts (`artifact:`) the role produces   |
| `gates`          | pass/fail checks; each has a runnable `command` and a `blocking` flag |
| `retry_policy`   | `{max_retries, backoff_strategy: linear\|exponential, initial_delay_seconds}` |
| `escalate_to`    | role name to hand off to when retries exhausted, or `human`          |

The vocabulary mirrors `hermes3d.core.agents.multi_agent` (Critic / Optimizer /
Executor) — verdicts, retries, escalation — so a Python orchestrator can wrap
each YAML in an agent dataclass with minimal glue.

## Adding a new role

1. Copy the closest existing manifest as a template.
2. Set `role` to the new lowercase name; rename the file to match.
3. Fill in real script paths and gate commands. **No placeholders.** If a
   sibling task is creating a script that does not yet exist, reference its
   final path — but it must be the path that script will actually have.
4. Run the validator:

   ```bash
   python scripts/validate-agents.py
   ```

   You should see one `[OK] <role>` line per manifest and exit code 0.

## How an orchestrator consumes them

Pseudo-code (works the same in Python, n8n, or GH Actions):

```
for manifest in glob("agents/*.yaml"):
    spec = yaml.safe_load(manifest)
    validate(spec, schema=load("agents/_schema.json"))

    # collect inputs from upstream context
    inputs = bind(spec["inputs"], context)

    # execute the action sequence
    for step in spec["action_sequence"]:
        run_step(step, inputs)

    # enforce gates
    for gate in spec["gates"]:
        rc = shell(gate["command"])
        if rc != 0 and gate["blocking"]:
            for attempt in range(spec["retry_policy"]["max_retries"]):
                sleep(backoff(spec["retry_policy"], attempt))
                if shell(gate["command"]) == 0:
                    break
            else:
                handoff(spec["escalate_to"], context)
```

## Roles in this kit

| role          | purpose                                                                  |
|---------------|--------------------------------------------------------------------------|
| `architect`   | designs implementation plans, emits ADRs                                  |
| `implementer` | TDD code writer; consumes a task spec, emits a PR diff plus tests         |
| `qa`          | runs pytest + Playwright; gates on 100% pass                              |
| `repair`      | diagnoses failures, tries skill_store fix then LLM patch then escalates   |
| `reviewer`    | code review against the contract; emits comment list and a verdict        |
| `releaser`    | tags release, builds wheel, signs proof bundle                            |
| `auditor`     | runs `forbidden_pattern_scan` and `honesty_diff`; gates on zero violations |
| `preflight`   | runs `scripts/preflight.sh`; gates on required tools present              |
| `branchguard` | pre-push hook checks; gates on branch != main/master and tests green      |
| `bundlesigner`| produces signed proof bundle zip; gates on signature verification         |
