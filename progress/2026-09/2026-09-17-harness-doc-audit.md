# 2026-09-17 — HS-4 document audit: decision-record refresh, fuzzy-workflow hardening

Operator-initiated review ("is there anything that could be refined?") over the harness-selection
document set and the two new agent-loop handoffs. Zero inference, zero process management, no API
reload, no host config touched.

## Shared clone fast-forwarded

`/workspace` was **623 commits behind `origin/main`** with 63 tracked files dirty and 145 untracked
entries — the condition the session-start lane notice reports. The dirty files were **older states
already superseded upstream** (checked file by file: e.g. the working copy of
`unified-trace-memory-service.md` predated the UTM-P1 tick, and `scripts/vidya/adapters/README.md`
lacked the VB-WIRE-1 ingest section). The one local commit, `d347f47f`, was already upstream by
content (`git cherry` reports it applied; the added file is byte-identical to origin/main).

Procedure: full backup of every tracked diff (patch vs local HEAD and vs origin/main) plus verbatim
copies of all 63 files, then `reset --hard origin/main`, then **restore the six live runtime/state
files** (`.research-session.json`, the two session-bus state files, `.devc/overrides.json`,
`.devcontainer/devcontainer.json`, `data/benchmark_artifact_inventory.json`) so no daemon lost its
state. Sixty-five untracked paths that shadow files now tracked upstream were moved aside, not
deleted. Backup: `/workspace/tmp/hs4-audit-20260917/preexisting-worktree-backup/`.

## What the audit found (four read-only agents; reports in `/workspace/tmp/hs4-audit-20260917/`)

- **The HS-4 decision was recorded but the surrounding prose still read as undecided**: the
  candidates table said "selection is OPEN" with OpenCode "TBD (no eval yet)", the Status line said
  Phase 0 "not started" although P0.1/P0.2/P0.3/P0.5 had landed, and the dependency graph still
  terminated at "HS-4 selection decision".
- **Duplicate IDs**: `HS-5` and `HS-6` each named two different tasks.
- **Pin drift**: the design docs quote OpenCode `4bffbb655`; P0.3 re-pinned `350c726a` (v1.18.31).
- **One wrong finding**: the P0.3 shard says FastMCP silently drops an undeclared `session_id`. At
  our pin (`fastmcp>=3,<4`) it **refuses** the call.
- **Two fixed defects still described as live**: the `/v1` `recall()` failure (fixed by orch
  `83c7ed2f`) and the inert `mempalace` config block (commented out, root `91d56181`).
- **The fuzzy-workflow handoff named the deterministic/fuzzy boundary without defining it** — no
  fuzzy-node contract, no gates, no rejection destinations, none of the four things
  `agent-loop-design.md` requires; and its FW-2 re-opened a placement question that HS-4 §2 plus the
  dashboard plane rule already answer.
- **The improvement loop left its mutation object unbounded**, including policy documents that HS-7
  and HS-5b forbid a model to edit.

## Applied

Decision-record refresh in `harness-selection-and-integration.md` (post-decision candidates table,
Status, Objective, graph, Reporting; per-step P0.1–P0.5 evidence lines; `HS-5c`/`HS-15` renames;
mechanism pointers for P1–P5 without double ownership). Outcome banner and superseded-pin notes in
both HS-4 design docs. Corrections appended (never rewritten) to the three 2026-09-16 shards.
Link/finding fixes in the harness-candidate references. SC86 producer row updated in the adapters
README. FW-1/FW-2/FW-4 and HIL-1/HIL-4/HIL-5 hardened per the audit; UFH-01/08/09 rows refreshed.

**No checkbox was ticked** — the Phase-0 work belongs to other sessions; evidence went into box text
instead, and the P0.4 live gate is still theirs to flip.

## Residuals

- `src/api/models/openai.py` still describes `x_max_escalation` as capping escalation while `/v1`
  only records it — filed as `HS-4 P4-pre` (epyc-orchestrator, one line, for the owning session).
- Unknown `x_*` keys are still silently ignored (`extra="ignore"`), and `/v1` B2 compression still
  fails open to the unfolded history. Both recorded, neither fixed here.
- The archive/promotion proposal for this handoff (≈340 history lines → `archived/`, Harness Cards →
  `docs/reference/`) was **not** applied; it needs an operator call.

## Validation

`python3 scripts/handoffs/index_state.py --check` exit 0 · `vidya cite-check` clean (106 citations,
0 problems; the `unknown` rows are pre-existing unanchored claims).
