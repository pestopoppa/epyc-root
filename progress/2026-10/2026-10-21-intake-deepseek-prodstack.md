# 2026-10-21 — research intake: DeepSeek V4.1-Flash deployment commentary (gap analysis vs the DeepInfer intake)

Lane `intake/deepseek-prodstack-20261021` (worktree `/mnt/raid0/llm/worktrees/intake-deepseek-prodstack-20261021`, base `1aee2b958`), run by a subagent for main session workspace-f8. Stages 1–3 complete; **Stage 4 NOT applied** (operator review pending). Zero compute.

## What was processed

- Operator-pasted commentary on susun's X note of 2026-10-20 (status id in intake-2214's url) about DeepSeek's Zhihu deployment post. The Zhihu URL collides with `intake-2136` (dived 2026-10-20) and was recorded there as a **re-encounter** (re-fetched via r.jina.ai, identical text); not re-minted. The X note became `intake-2214` (FxTwitter JSON + three attached note images transcribed; read FULL; dive-verified).
- Every claim in the commentary was classified against intake-2116..2142 and the 2026-10-20 plan: all DeepSeek-system claims **ALREADY COVERED**; the practitioner's own notes are **REFINES** (WP-15, HSF-4) or **NEW monitors**; the PP-vs-EP position is the X author's, misattributed to the article by the relay; the TTL sentence in the note is inverted vs the article (citation hygiene recorded).
- Stage-2b: three waves on every recommended dive-surfaced source, each with an independent second reader — wave 1: `intake-2215` (vLLM-Ascend ShortRequestFirst), `intake-2216` (Dual-Pool Token-Budget Routing 2604.08075; 2604.09613 is its withdrawn duplicate); wave 2: `2217` EWSJF, `2218` Medha v5, `2219` fairness-aware chunked prefill, `2220` GreenLLM, `2221` FlowPrefill; wave 3: `2222` LAPS (MLSys 2026 oral), `2223` SLOWeave. Wave 4: nothing recommended. Reader corrections (NBSP/thin-space anchors, a Table-4 baseline-column slip in 2220, wording in 2219) persisted.

## The finding that matters

Verified by main in the frozen v10 tree (`ffc1bac82`): `tools/server/server-context.cpp` fills the pending-prompt batch in fixed slot-index order (`iterate()` :2793; `return` for every later slot once `batch.size() >= n_batch`, :3205-3230, :3614), and the KVU-16g prefill budget (`98c0ce12a`, experimental only, not an ancestor of v10) returns 0 when no slot is generating. A short request landing in a higher-index slot than an in-flight 64K prefill waits for the whole remaining prefill (PB-QCOST-1 fit: ~75 s vs ~4 s by slot index). Nothing filed on 2026-10-20 measures this; the v11 enable (KVU-16g-2) does not cover it.

## Stage-3 plan (draft)

`/mnt/raid0/llm/tmp/intake-deepseek-prodstack-stage3/PLAN.md` (+ `payload.json`, v2; `validate_intake.sh --plan-file --session-file` exit 0). 71 ledger rows, 19 scan rows, 10 entry updates. Packets: **P1** refine WP-15 (five selection arms, re-prefill fraction, load-regime stratification, long-request delta, chars-per-token fit); **P2** refine HSF-4 (per-role uncached-length histogram, alpha(B) at 1K..64K, alpha(1-1/rho) ceiling); **P3** new `PB-HOL-1` collision probe + refined `PB-QCOST-1` (per-n re-validation, P99 residual) in gpu-serving-tie-in-program, DI-126 monitor rewritten with the slot-order mechanism and per-component remedies, KVU-16g-2 decode-gating/margin rider; K1-K5 knowledge; M1-M4 monitors (NUMA page-cache locality of KV handover; fleet-wide prefix index gated on WP-15 arm (d) + KVU-12; budget fragmentation guard; ordering fix on PB-HOL-1 / ggml suspend-resume / TPOT classes). No new handoff, no new index row. Six operator questions with recommended answers in section 12.

## Lane state

Commits on the lane: index (intake-2214..2223 + re-encounter on 2136) and session file only; handoffs untouched. Scratch kept as cited evidence under `/mnt/raid0/llm/tmp/intake-deepseek-prodstack-20261021/` (xpost, zhihu, dive-* dirs); generator scratch removed.
