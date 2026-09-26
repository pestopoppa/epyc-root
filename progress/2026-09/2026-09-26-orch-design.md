# 2026-09-26 — orch-design session (REPL/embedding design, routing audit, typed-decision tidy)

This session ran **without its own lane worktree** and made no edits in the shared root clone. Its
wrap-up was run by a subagent in `/mnt/raid0/llm/worktrees/wrapup-orch-design-20260926` on
`lane/wrapup-orch-design-20260926`.

## Vidya v10 KV-quant reader (VB-KVQ-V10), handed off

- The root-side adapter, ingest name and `kvq_planner_context.py` were already on `main` as `876af60b`
  (2026-09-25). The copies left uncommitted in the shared clone are an earlier subset of it: the hunks are
  byte-identical for `cli.py`, `ingest_sources.py` and `test_ingest_sources.py`, and the landed README row
  and handoff text are supersets. Nothing needed porting. Checks: `tests/vidya` 1546 passed / 81 skipped;
  `cli.py ingest kv-quant-27b-v10-measurement --dry-run` matched 0 units (no post-hook sweep exists yet,
  VB-KVQ-V10-INGEST).
- The research-side planner consumption was handed to AutoKernel session workspace-76. Research
  `lane/vidya-kvq-planner-20260925` @ `254b5c05` is kept as review input and was **not** merged.
- The shared research clone's stale planner edits were removed by reverse-applying this session's own
  byte-identical patch.

## REPL / embedding design — decisions

Canvas: https://claude.ai/artifact/UnjtMaouUFYs9xz5umnwPd. Filed as **UFH-12**
[`repl-embedding-retrieval.md`](../../handoffs/active/repl-embedding-retrieval.md).

| Decision | Outcome |
|---|---|
| D1 placement | Agreed: embedders beside each serving model; idle instance → same-hardware instance → lexical now. Granite-97M-R2 leads. |
| D2 REPL tool gate | `repl-turn-efficiency.md` S4 gate waived for retrieval, conditional on the Phase-2 kill criterion. |
| Baseline | Baseline 1 = benchmark quality of Qwen3.8-Flash-Next, the stack's public-benchmark leader. Speed baseline (large MoE hybrid across CPU+RAM+both MI210s) deferred. |
| Typed routing | Used as ADVICE (hint vs no-hint A/B on frontdoor), not as an enforcer (TD-10 was ~1pp worse). |

## Audit findings (code + live process, 2026-09-26)

- The CPU frontdoor is the default REPL role, so the synchronous 512-token spill summary costs about 12 s.
- All six BGE embedders pin to the same four cores inside frontdoor's 0-95, so they deliver one server's
  compute. Their per-slot context is 256 tokens.
- Episodic memory is used for routing only. It is queried about 3-4 times per request, none of which is
  timed, and it has never been A/B-tested.
- Typed decisions are off in production. The native single-token path needs v11 (the SW-9 probs fix).

## Work landed

- **Typed-decision doc tidy.** Root `lane/td-tidy-20260926` @ `e5dea736` was merged. Orchestrator
  `lane/td-tidy-orch-20260926` @ `744cf697` was fast-forwarded to orchestrator main; its typed_decisions
  tests pass (327).
- **UFH-12 filed**, with its index row. `repl-turn-efficiency.md` records the D2 waiver.
- **TODOs filed:**
  - RI-16..RI-21. RI-16 (per-stage routing latency) is the priority, and the RTG-30 row now points at it.
  - M-12k and M-20..M-22.
  - LRC-1 and LRC-2.
  - TD-28.
  - An NIB2-78c note.
  - REPL-EMB-B.1 and REPL-EMB-B.2.
- **Doc corrections**, verified against orchestrator `744cf697`:
  - `wiki/routing-intelligence.md`: 92% → 81.0% STAGED; memory is not write-only; the prompt section
    appears only on streaming turn 0; the verifier gate defaults off.
  - `learned-routing-controller.md`: "8k rows" → 64,396 live routing rows.
  - `episodic-memory-integrity.md`: `memrl.py:481` → `:645`.
  - `tool-output-compression.md`: `_spill_output` → `:716-800`.
  - `harness-selection-and-integration.md`: HS-4 P0.1/P0.2/MCP are deployed in the running API; P0.4
    waits only on a quiet CPU window.
- **Belief-kernel wiring.** Source rows and tasks were added for VB-ROUTE-LAT, VB-UFH12-RETR and
  VB-TD-ADVICE.
- **Orchestrator bug fixes** (the `ParallelEmbedderClient` Python-3.11 `asyncio.coroutine` bug and
  related fixes) are owned by a sibling agent. No branch had been pushed when this wrap-up ran.

## Open

- **REPL-EMB-0.1:** prepare the embedder-placement stack-change package. Once prepared, it needs the
  operator's signature.
