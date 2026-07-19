# 2026-07-18/19 — Handoff dashboard priority/lifecycle signal + stale-open backlog audit

Session driven by an operator question: *"if the inference-batch-loop consolidation is only 11 checkboxes, what are the remaining ~660 open tasks about?"* That exposed the board's headline open-task count (678 active+blocked) as over-counting stale work. Two deliverables + follow-through.

## 1. Handoff dashboard — priority grouping + parked/superseded signal (`:8100`)

Frontend + parser changes (`dashboard/handoff_parser.py`, `dashboard/static/handoffs.html`):
- **Priority sections** inside the Active & Blocked columns — cards (already priority-sorted) grouped under counted headers (`P0 · N handoffs · M open / K done`), mirroring the backlog table. Plus a priority-colored left edge on every card.
- **Lifecycle (shelved-work) signal** — `parse_lifecycle()` emits `parked`/`superseded` from a high-precision Status/Priority scan; an explicit `**Lifecycle**:` metadata field overrides it (authoritative). Shelved cards get a dashed chip + 50% dimming; group headers show `· N parked/superseded (M open)`. Deliberately conservative (5 cards flagged, never dims a live handoff). 51/51 parser tests green.

## 2. Stale-open backlog audit — `handoffs/active/stale-open-audit-2026-07-18.md`

3 parallel read-only agents audited the 22 handoffs whose Status/Priority carried a park/landed keyword.
- **Result: 134 of 173 open tasks in the flagged handoffs (77%) are stale-open** (landed / superseded / deprioritized / frozen behind an unfired gate). **Corrected live backlog ≈544, not 678** (upper bound — only the flagged 22 were audited).
- Biggest stale masses: GEMV microkernel (36/38 — kernel landed 2026-04-24, SIMD deprioritized), decision-aware-routing (23) + learned-routing-controller (15) frozen behind an unfired routing-expansion gate (DAR-1 replay 0.00%).
- **Fragmentation exemplar (operator-caught):** `qwen36-27b-cpu-feasibility` reads parked/dead, but the *same model* was characterized extensively on the MI210 (29.5→40.4 t/s, the banked "dense-Q8 +37%" v7 win) under handoffs it never cross-linked. Cross-link added.
- **5-handoff duplicate cluster** on the stack-update pipeline → authoritative pair = `model-stack-single-source-update-pipeline` + `stack-change-governance-pipeline`.

## 3. Follow-through applied (safe, reversible)

- **2 doc-hygiene fixes**: `Lifecycle: live` override on `llama-cpp-dsa-contribution` (board was over-flagging it superseded; committed by a parallel session); MI210-GPU-campaign cross-link into `qwen36-27b-cpu-feasibility`.
- **4 fired reopen-triggers surfaced** (dated 🔔 note + reactivate task each): gpu-drafter (MI210 gate opened), minddr (DGX→MI210), sarathi (batched-decode E1/E2 landed), sliders (KB-RAG K7 certified).
- **Stack-cluster soft-consolidation — corrected on verification** (the "retire 3" verdict was too coarse): `standardized-stack-update-pipeline-finalization` → superseded (W4 co-tracked); `model-stack-update-pipeline-audit` → kept LIVE (2 orphan-live boxes: `ctx_model_max`, tap/policy-hint); `model-stack-change-standardization-audit` → flagged as a repeatable runbook.
- **Operator-gated remainder**: the hard-archive (git-mv to `completed/` + orphan-box migration into the SSoT + repointing ~10 inbound index links).

Audit doc at 5/11 recommendations done. Dashboard live on `:8100`; all changes committed with explicit paths (parallel-session work in the shared tree deliberately excluded).
