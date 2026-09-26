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

## Evening — Phase 0 applied, HS-4 P0.4 PASS, prior-art intake landed (workspace-8d)

This session is **workspace-8d** — the same session that ran TD-21 earlier, before a `/clear`. Design canvas:
https://claude.ai/artifact/UnjtMaouUFYs9xz5umnwPd

### UFH-12 Phase 0 — embedder placement applied (operator-signed)

- Signed 2026-09-26T17:46Z (receipt `artifacts/operator/receipts/RATIFY-UFH12-PHASE0-EMBEDDER-PLACEMENT-20260926.json`,
  now committed; its pins match the package as landed). Applied ~18:11-18:35Z: orchestrator `5af57377` (merge) and
  `a439070e` (derived regen), research `7640269b`.
- Gates (evidence `epyc-orchestrator/data/embedder_placement/{pre,post,g3b-post}-20260926.json`):
  - **G2 pool scaling:** 0.95× → **4.96×** (45.6 texts/s). PASS.
  - **G0 idle frontdoor decode:** 52.6 → 53.1 tok/s, unchanged. PASS.
  - **G1 saturated ÷ idle frontdoor decode:** `:8070` 0.34 → 0.91 (17.6 → 48.4 tok/s); `:8080` 0.50 → 0.91;
    `:8180` 0.53 → 0.86 — below the 0.95 PASS line on all three, and `:8180` in the pre-registered rollback band.
  - **G3 CPU speech with the pool saturated:** STT RTF ≤ 0.24, TTS first packet ≤ 0.12 s. PASS on the re-run. The
    first run (`g3-post-20260926.json`) read ROLLBACK from one cold first request; the re-run discarded a warm-up
    request, which the pre-registered method did not include, so the warm-up is now pre-registered for later runs.
- Serving proofs P1-P8 pass: affinity tool rc=0, node-local memory 97.8-98.9%, P6 cosine 1.0, P7 402-token input
  accepted, 6/6 healthy, episodic index 0 stale.
- **Operator decision on G1: KEEP** (overriding the rollback band on `:8180`; rolling back would restore 0.53) and add
  a Phase-1 cap — the scheduler caps in-flight embeddings on instances that share a busy frontdoor half's node,
  under the D1 rule "idle instance anywhere → else the requesting model's own hardware → else lexical now, index
  later". Filed as REPL-EMB-1.4 with a G1 re-measure against ≥ 0.95. Belief-kernel source VB-UFH12-PLACEMENT filed
  (row + task).

### HS-4 P0.4 — OpenCode live acceptance PASS

- r3 at ~19:05Z: `verdict.json` pass=true, 10/10 checks, including the new **A5** token parity (session 28819/247
  tokens == tap `server_terminal` over 4 calls; root lane `0ce7e111`). SC86 belief rows written. Durable copy:
  `artifacts/harness/hs4-p04-20260926-r3/`.
- **r1 lesson: never wrap API traffic in an outer region-lock.** r1 failed because the runner held an outer CPU
  region-lock, which starved the orchestrator's own placement (503 `contention_denied`). That was a method error by
  the runner, not a product bug — the API does its own admission.
- **/v1 usage fix.** r2 failed only SC86 capture because `/v1` client tool mode returned no `usage`. Fixed in orch
  `5697828c` (backend-reported prompt/completion/cached counts; `stream_options.include_usage` final chunk) and
  deployed by an API-only reload at 19:01:51Z.
- Next: P0.4b Harness Card republish (HS-7), P0.4c pin freeze at the **tag** `v1.18.31` = `014614d3` (Stage 4 found
  the audit pin `350c726a` is a dev commit), then the P0-split.

### Orchestrator hygiene

- **Stale-code fixes:** orch `cdd05543` — the shapekeyed smoke's default anchor/probe roles named aliases with no NUMA
  instances since `860b0b2d`, so the default seam plan checked nothing; defaults are now derived from the live
  lineup. With `30626243` also in, the unit suite went from 9 failures to 0.
- **Dead-knob removal:** orch `30626243` removes `GGML_NUMA_REPACK_INTERLEAVE` from `stack_env` (operator-approved) —
  not compiled into v10 or the AutoKernel champion (`strings libggml-cpu.so`: 0 hits), so launch behaviour is unchanged.
- **AK-H-NRI-1** — the question whether to re-port the NUMA repack-interleave work — was injected into the AutoKernel
  DS41 inbox as a hypothesis.

### Orchestration prior-art intake (Stages 2b / 3 / 4)

- Stage 2b ingested and dove 7 operator-selected sources (intake-1815..1821); the Stage-3 plan was approved and Stage 4
  applied it (handoffs, index rows, intake dispositions, belief-kernel rows). Landed on root main from
  `intake/orch-prior-art-20260926` @ `0c8e227e`.
- **OD-A:** the KTransformers runtime is DECLINED for now; the MI210 port investigation is OPEN (F7 source-only
  feasibility read; F6 build check follows F7).
- **P-SERVE-SEL-1** (OP-62) ratified by the operator — pending the operator's run of
  `scripts/operator/run_p_serve_sel_1_ratify_20260926.sh --operator <name>` (the protocol text crosses the
  human-only measurement boundary, so no agent writes it).

### Open

- REPL-EMB-1.1 + 1.4 (pooled client with the in-flight cap; G1 re-measure ≥ 0.95).
- HS-4 P0.4b / P0.4c / P0-split.
- The operator's P-SERVE-SEL-1 ratify run.
