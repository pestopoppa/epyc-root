# 2026-09-17 — backlog churn: five low-hanging tasks closed, one defect filed

Operator asked to start implementing handoffs and to **run no inference**. Everything below is
zero-inference: unit tests with fake backends, source reads, and document work. No server was
touched, nothing was started, stopped or reloaded, and no benchmark ran.

Four implementation subagents on disjoint file sets, plus two tasks done in-session.

## Closed

| Task | Handoff | What landed |
|---|---|---|
| **HS-15** | harness-selection-and-integration | The cooperation contract was written against a FIELD NAME. Restated as a capability in `client-surface-audit.md` §1 — *config-declarable arbitrary top-level body keys on the openai-completions path, on the call verb the harness actually uses* — with all three qualifiers explained and the five names it ships under listed. Step 1 now tells the auditor to grep for the capability. |
| **FW-1** | fuzzy-workflow-authoring-gui | Worker-failure routing as the worked two-layer example (taken from PAW-5, not repeated). Pseudocode loop block in the `agent-loop-design.md` shape; GUI vocabulary derived from it — 6 node types, 6 edge types, 11 lint rules. |
| **FW-4** | fuzzy-workflow-authoring-gui | Belief-kernel write side filed at design time: adapters-README source row + task **VB-FW-1**. |
| **UTM-P1a** | unified-trace-memory-service | First pairing-key producer (orchestrator `9a7181f2`). |
| **EVL-42 1c-fix (b)+(d)** | scoring-infra-standardization | Reviewer truncation and the dead `/chat` tool fields (same commit). |

## The three judgement calls worth keeping

**UTM-P1a — which producer is honest, not which is nearest.** UTM-P1 landed the pairing-key schema
in `dd24ed10`, but nothing stamped the keys, so `paired_runs()` returned `{}` on the real store: a
capability dead on arrival. The box named `autopilot_live` and the eval tower as candidates; checked
against code, `autopilot_live` can stamp only `harness` (a `JournalEntry` has no RNG seed, no turn
index, and `trial_id` is autopilot-only) and **the eval tower emits no trace events at all**. The
review plane was wired instead — it already emits live and carries a real cross-harness identity in
`TaskIR.task_id`. **`task_key` is never derived from `subtask_id`**: "S1" recurs across unrelated
tasks, so a fabricated key would silently pair unrelated runs, which is worse than an empty pairing.
Unknown keys stay NULL, which the schema already means as "never captured". Filed **UTM-P1a.2**: one
producer can only pair a harness against itself.

**EVL-42 (d) — deprecate, don't delete.** `ChatRequest.tools`/`tool_choice` are dead, but they are
part of a published `/chat` schema whose model sets `extra="ignore"`, so removal would swallow them
silently: identical runtime, worse visibility. Marked deprecated, description corrected (it falsely
claimed REPL `CALL()` exposure), and `/chat` now logs when a caller sets them — which is what makes
removal safe later.

**FW-1 L2 amended (D-1).** The rule said no confidence branching "until TD-2 lands". TD-2 **has**
landed (27B ECE 0.0625 with one miss at ~0.90; LFM2.5-2.6B 0.267) and TD-5 still forbids enforcement,
so "TD-2 landed" was never the unlock. The lift is now per `(model pin, question catalogue)` on an
operator-ratified calibration record, never global — the 27B number says nothing about LFM, and one
catalogue's ECE says nothing about another's.

## Filed, not fixed

- **NIB2-80** — `nodes.py:235-241` escalates on `EARLY_ABORT` **without calling `_should_escalate`**,
  while its four siblings do. That gate is what enforces `cfg.max_escalations`, so an early-aborting
  run can escalate past its own budget and skip the approval check. Two readings with different
  fixes, and it changes graph control flow on a path evals traverse — so it wants a before/after test
  and the owning session's judgement, not a drive-by patch. Surfaced by the FW-1 loop block, which is
  the point of the convention: it forces every gate and every rejection destination to be named.

## Residual

- The FW-1 acceptance harness run is still owed (needs the FW-2 executor and, for the baseline arm,
  inference — deliberately not run this session).
- `ruff format` flags two pre-existing hunks in `review_service.py`; left alone as unrelated.

## Validation

`index_state.py --check` exit 0 · `cite-check` exit 0 · orchestrator: 136 passed across the combined
trace/review/request slice, 97 across the `openai_compat` slice, 36 in the seam slice; every new test
verified failing against pre-change sources; `ruff check` clean on all touched files.
