# Bulk Inference Campaign — active backlog (Packages G–K)

**Status**: active - live backlog is Queue 2 consolidated quiesce-window measurements, Queue 3 restart-bundle evidence accrual, standalone model-batched windows, and Package I frozen after the DAR-1 replay failed its reopen gate. J7/DCP remains default-off after the first live A/B worsened latency; K-MEM-1 completed its first Tulving baseline and no longer blocks the next throughput-sensitive lane; frontdoor G11 run `20260620_035613`, worker G11 run `20260620_062750`, and architect G10 run `20260620_081041` are packaged as raw-response/throughput evidence and deterministic-F1 scored. G12 tier calibration is complete: deterministic AA-Omniscience 4-class scoring was accepted for role-tier recalibration only, and orchestrator `d0e082a7` updated production factual-risk tier multipliers to `0.727978/0.824178/1.0`; factual-risk mode/canary/enforce decisions remain separate telemetry gates. The v6 contention-matrix age blocker was cleared on 2026-06-27 by refreshing the full/primary pair layer in orchestrator `526ba3a2`; Queue 3 baseline mutation should now fail or pass on clean evidence, not stale topology metadata.
**Created**: 2026-04-06
**Updated**: 2026-06-20 - K-MEM-1 run `20260619_141212` completed and was packaged in `epyc-inference-research` `b6edc64`; research `9e63af0` fixed Tulving ground-truth parsing and rescored it. The production/default-expert run scored 456/456 Tulving questions with avg F1 `0.4309`, Simple Recall `0.5530`, Chronological Awareness `0.1593`, and avg decode `17.27 t/s`; the runner log ended `448 completed, 8 skipped, 0 errors` because the first 8 rows were reused from the corrected resume. This is a mixed baseline with usable lexical entity/time/location recall, weak event/detail and chronology, and zero-answer hallucination failure; it is not a memory-routing promotion signal. Research `2eb94f8` adds a targeted 120-row follow-up manifest for zero-answer abstention, event-content/detail recall, and chronology-order repair. Frontdoor G5 short-m@k clean-window evidence is packaged in research `7e9f67f`. Frontdoor G11 clean-window run `20260620_035613` first exited after `24:57` with `26 completed`, `0 skipped`, and `1800 errors`; triage found the quality rows used the subprocess path without built `completion`/`lookup` binaries, while the successful `moe4_lookup`/`moe6_lookup`/`moe8_lookup` files were speed-only telemetry. Research `7d27597` makes generated AA/clean-window suite commands add `--server-mode --skip-speed-tests`; the corrected rerun completed and is packaged in research `587c6cd` with `600/600` non-blank rows for baseline, moe4, and moe6. Research `92a5602` adds deterministic-F1 AA labels and the factual-risk report view: baseline accuracy `0.1117`, hallucination rate `0.5610`, OI `0.2753`; moe4 accuracy `0.1117`, hallucination rate `0.5666`, OI `0.2725`; moe6 accuracy `0.1233`, hallucination rate `0.5608`, OI `0.2812`. Worker G11 run `20260620_062750` completed with canonical preflight `data/preflight/2026-06-20_062737.json` and is packaged/scored in research `32f2c27`: baseline accuracy `0.1433`, avg F1 `0.2280`, hallucination rate `0.6829`, OI `0.2302`, avg decode `52.63 t/s`, and label counts `86` correct / `351` incorrect / `110` partial / `53` not attempted. Architect G10 run `20260620_081041` completed against resident `architect_general :8083` and is packaged/scored in research `b91d16c`; the combined factual-risk report is `ready_for_tier_update`, and orchestrator `d0e082a7` applied the measured tier multipliers. Research `7d05d03` adds X-MAS constrained-policy A/B to the clean-window manifest after the earlier DS-E1 entry; research `7d2dade` adds Queue-2 E2 plan generation and E1 batched-decode sweep entries. Current generated manifest state is 27 entries, 21 ready, and 6 blocked under observed live ports/contexts. K-ROPE clean-window evidence has valid 4K/8K cells plus valid 16K frontdoor/ingest cells; exact-boundary rows and the current `worker_general` MTP serving path remain blocked. J7/DCP launch-code provenance is satisfied, but the first live A/B does not support enablement.
**Categories**: evaluation, inference, coordination
**Priority**: HIGH
**Depends on**: Package A results (complete)
**Related**: [`routing-and-optimization-index.md`](routing-and-optimization-index.md), [`research-evaluation-index.md`](research-evaluation-index.md), [`pipeline-integration-index.md`](pipeline-integration-index.md), [`hermes-agent-index.md`](hermes-agent-index.md), [`inference-acceleration-index.md`](inference-acceleration-index.md), [`cross-role-nway-contention-matrix.md`](../completed/cross-role-nway-contention-matrix.md)

---

## Problem

14 inference-dependent tasks are scattered across 5 domain indices. Running them independently requires 14 separate stack launches with 5-15 minutes of NUMA warmup each — over 3 hours of dead time before any evaluation begins. Many tasks share the same stack configuration and can collect cross-task telemetry simultaneously via feature flags.

**Consolidation**: 14 tasks → 4 optimized runs. Each run maximizes the number of tasks resolved per inference session by piggybacking telemetry collection, A/B comparisons, and eval passes on shared model instances.

---

## Current State (2026-06-12) — Three-Queue Structure

The 2026-04 campaign (Packages A–F) is complete/overtaken and archived (see *Completed* below). The cross-role N-way matrix + within-role placement SM (J1/J4a-J4c/J4/J5) are CLOSED (see the compaction note in Package J). The remaining inference-gated backlog is organized into three queues plus standalone windows and a frozen block, per the Fable 5 portfolio pass. Per-task detail is preserved in the Package G/H/I/J/K sections below — this is the dispatch view.

### Immediate first-idle-window bundle (2026-07-06)

Use this when AutoPilot is deliberately stopped. The items below are ordered to
drain current Fable blockers without rediscovering command syntax. Do not run
DS-E1 concurrently with any other live-stack workload; it is the only row here
that needs a full CPU-stack quiet window rather than just AutoPilot stopped.

| Order | Item | Command(s) | Quiet requirement | Expected artifacts |
|---:|---|---|---|---|
| 1 | A9 contrast-replan collection | `cd /mnt/raid0/llm/epyc-orchestrator && A9_COLLECTION_TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ) uv run python scripts/analysis/collect_offline_reward_pairwise_audit_target_live.py --manifest orchestration/reports/offline_reward_oracle_token_coverage_final_labels_20260621/offline_reward_pairwise_audit_target_live_20260705T185704Z_contrast_replan_20260705T202257Z_collection_manifest.json` | AutoPilot stopped only | Four `seeding_a9_*_<UTC>.json` batches under `epyc-inference-research/benchmarks/results/eval/`, feeding the existing `...contrast_replan_20260705T202257Z` manifest bundle. |
| 2 | DS-E1 KV measurement | `cd /mnt/raid0/llm/epyc-inference-research && scripts/benchmark/ds_e1_kv_measurements.sh --execute`; then `cd /mnt/raid0/llm/epyc-orchestrator && uv run python scripts/server/dynamic_stack_evidence_packet.py --output orchestration/reports/ds_e1_evidence_packet_<UTC>.md --strict` | Full CPU-stack quiet: AutoPilot stopped and live `llama-server` processes coordinated down | New `data/dynamic_stack/ds_e1_kv_measurements_<UTC>/kv_measurements.csv` plus refreshed DS-E1 evidence packet. |
| 3 | RI-10 scored canary | Dispatch: `cd /mnt/raid0/llm/epyc-orchestrator && uv run python scripts/analysis/ri10_canary_dispatch_requests.py --payloads-jsonl orchestration/reports/ri10_canary_scored_request_plan_20260705T151725Z.payloads.jsonl --responses-jsonl orchestration/reports/ri10_canary_scored_request_plan_20260705T151725Z.responses.jsonl --failures-jsonl orchestration/reports/ri10_canary_scored_request_plan_20260705T151725Z.failures.jsonl --summary-json orchestration/reports/ri10_canary_scored_request_plan_20260705T151725Z_dispatch_summary.json --host-quiet-confirmed`; then score with `uv run python scripts/analysis/ri10_canary_score_responses.py --answer-key orchestration/reports/ri10_canary_scored_request_plan_20260705T151725Z.answer_key.jsonl --responses-jsonl orchestration/reports/ri10_canary_scored_request_plan_20260705T151725Z.responses.jsonl --scored-jsonl orchestration/reports/ri10_canary_scored_request_plan_20260705T151725Z.scored.jsonl --summary-json orchestration/reports/ri10_canary_scored_request_plan_20260705T151725Z_score_summary.json --summary-md orchestration/reports/ri10_canary_scored_request_plan_20260705T151725Z_score_summary.md` | AutoPilot stopped only | `responses.jsonl`, `failures.jsonl`, dispatch summary, `scored.jsonl`, and score summaries next to the existing `20260705T151725Z` packet. |
| 4 | J12 think-loop probe | `cd /mnt/raid0/llm/epyc-orchestrator && uv run python scripts/benchmark/j12_think_loop_probe.py --roles frontdoor architect_general --confirm-clean-window` | AutoPilot stopped only | `/mnt/raid0/llm/tmp/j12_architect_think_loop_probe_<UTC>.jsonl` and `_summary.json`; if clean, THINK-ABL-1 is the follow-on. |
| 5 | W8/Fable readiness refresh | `cd /mnt/raid0/llm/epyc-orchestrator && uv run python scripts/autopilot/w8_promotion_trajectory_report.py --journal orchestration`; then `uv run python scripts/autopilot/fable5_gate_report.py --json --strict` | AutoPilot stopped only; report-only | Refreshed W8 trajectory and Fable strict gate snapshots under `orchestration/reports/`. |

### Queue 1 — offline-now (≈0 llama-hours; run today alongside the live autopilot)
- ✅ **J7 DCP-6 offline replay + DCP-6a repair CLOSED/PREPARED; first live A/B does not support enablement** — launch-code provenance is satisfied and orchestrator `56a72f6` packages the first 3-off/3-on live run. Result: 6/6 HTTP 200, zero errors, all delegated, fewer generated tokens with DCP ON, but worse p50 latency (32.628s vs 20.219s). Keep `dcp_pre_assembly` off; rerun only for a larger quality-scored falsification after operational attestation cleanup.
- ✅ **DAR-1 regret replay CLOSED 2026-06-12** — current-traffic replay over 2026-06-05..2026-06-12 analyzed 12,057 routing decisions, matched 11,249 outcomes, found 8,145 regret-identifiable decisions, and measured 0.00% identifiable mean regret versus the >=5% reopen gate. Package I and broader learned-routing expansion remain frozen. Report: `epyc-orchestrator/orchestration/reports/dar1_regret_replay_2026-06-12.md`; code/telemetry landed in `epyc-orchestrator` `1dfbc22`.
- ✅ **K-RAG-1 formal K7 sweep CLOSED 2026-06-13** — final 70-case pool over the fresh K7 index produced 420 rows with `ok=true` and no missing evidence files. Safety/default candidate is `recency_w0.3_s90` (recall@10 0.6167, 0 missed-all-evidence cases); aggregate winner `recency_w0.1_s90_rerank_w0.3` reached recall@10 0.6298 but missed 3 all-evidence cases, and the 1.31pp gap is below the declared 2pp noise floor. Temporal recency is validated; cross-encoder rerank stays opt-in for first-rank/recall@3-biased consumers.
- ✅ **J13 P17.BT-3 analysis CLOSED 2026-06-12; cleanup landed 2026-06-13** — 341 rich/stagnation-fired trials and 75 logged BT-disagreement events satisfy the sample-size gate, but the journal does not persist the BT top trial ID, the hypervolume-top trial ID, or whether the planner followed either seed. Available proxy outcomes do not justify P17.BT-4 (`current frontier`: 2/75 BT-disagreement events vs 9/266 no-disagreement rich events; cluster-start next-10 frontier: 1/7 vs 8/34 thinned no-disagreement). Verdict: do not queue peer-judged BT. The cosmetic `bt_tiebreak_hint` rich-prompt block was removed while AutoPilot was paused in orchestrator `b8c0611`; the offline/shared BT helper remains.
- ✅ **J9 HLE-4 analysis CLOSED 2026-06-12** — 580 metric-bearing trials from immutable snapshot `/mnt/raid0/llm/tmp/autopilot_journal_snapshot_1781290411.jsonl`. Verdict: no Pareto co-objective promotion from the current rule metrics. `execution_fidelity` and `planning_stability` separate keep/revert but mostly mirror existing quality/reliability/safety verdicts; keep them diagnostic/advisory. `feedback_interpretation`, `memory_coherence`, and `recovery_rate` stay dashboard-only because of low variance, constant score, or 99.3% missingness. Any future J9 promotion waits for N2 per-question ledgers/sequential verdicts and redesigned evidence.
- ✅ **J12 wiring half CLOSED 2026-06-12** — registry-driven auto-population of `chat_template_kwargs` exists and the production `LlamaServerBackend` `/v1/chat/completions` path honors the kwarg (`tests/unit/test_registry_chat_template_kwargs.py`, `tests/unit/test_llama_server.py::...chat_template_kwargs`, `tests/unit/test_chat_completions_roles.py` -> 6 passed). The empirical J12 probe + THINK-ABL-1 remains Queue 2.
- ✅ **G12 factual-risk tier calibration CLOSED 2026-06-20** — deterministic AA-Omniscience 4-class scoring was accepted for role-tier recalibration only; orchestrator `d0e082a7` updated `_DEFAULT_ROLE_TIERS`, default config, and live `classifier_config.yaml` to measured multipliers. Do not reopen G12 for LLM-judge scoring; mode/canary/enforce decisions remain separate telemetry gates.

### Queue 2 — ONE consolidated quiesce window (t1000 or operator SIGTERM; ~28–31h; one attested reload serves all)
Ordered manifest (one reload, then everything rides it):
1. **Reload with declared production env** (fixes test-defaults; sets EVERY flag this window needs in launch env) **+ per-worker attestation** — orchestrator `4bbf1163` adds the concrete runbook and local `attest_orchestrator_workers.py` process-env proof, paired with `attest_flags.py`; live read-only default-poll checks saw all six API workers with no feature/env diffs. This is the only route around the 1-of-6 `POST /config` propagation bug. Rerun both attesters after the Queue-2 reload before trusting any flag.
2. **E2 then E1 batched-decode measurements FIRST** (findings-06 — E2 makes every later eval cheaper; they also fire the sarathi-serve workload-shift gate).
3. **Shape-keyed flag-on bracket** (`CROSS_ROLE_DISJOINT_PLACEMENT=1` live → verify env → multi-role fan-out probe → `SHAPE_AWARE_CONTENTION=1` smoke → revert or `mark_epoch`).
4. **J2/J3** single-worker live migration probe (`--workers 1`).
5. **J12 probe + THINK-ABL-1** (best leverage/hour, +33pp class effect; real ablation needs a non-no-op suppressor at fixed non-truncating `max_tokens`, same tasks both arms). **2026-06-26: `architect_general` is now LIVE on the `/v1/chat/completions`+jinja path with `enable_thinking=false` (N14 / [prompt-construction-determinism.md](prompt-construction-determinism.md) change #4).** The probe is therefore now a **REVERT-GATE on a deployed prod change**, not just wiring validation: confirm `enable_thinking=false` actually suppresses the Qwen3.5-122B `<think>`-loop the 2026-04-15 `0879ed56` exclusion guarded; if it loops, revert the architect jinja flip. Frontdoor (same family) is the working reference arm. 2026-06-27 opportunistic live-load probe (AutoPilot T2 running, not Queue-2 quiesce) found no immediate revert trigger: frontdoor 15/15, architect 12/15 by coarse scorer, 0 `<think>` leaks, 0 known wait-reference loops, 0 repetition-loop flags; architect had 2/15 HTTP 504s. 2026-06-28 orchestrator `16876006` packaged the clean-window runner as `scripts/benchmark/j12_think_loop_probe.py`; rerun/close with `--confirm-clean-window` in the declared quiesce window before treating J12 as promotion-grade.
6. **J15** MD-9 deep_research sentinel A/B.
7. **J7** DCP-6 inference half follow-up. First live run is packaged in `epyc-orchestrator` `56a72f6` and does not justify enablement; keep `dcp_pre_assembly` off. Use `scripts/benchmark/dcp_j7_ab.py` only for larger/quality-scored falsification or reruns after broad operational attestation cleanup.
8. **J10** URE shadow env-flag rides the reload free (passive).
9. **J16** RI-ITG-1 ingest-triviality A/B — **only if** N2 per-question ledger landed AND its leak premise re-verified against the live routing path.

### Queue 3 — restart bundle (live code; collect clean vector history)
- **Per-question eval ledger + sequential verdicts** (findings-01c) — the keystone; everything below gates on it. Ledger W1/W2 are live in the current orchestrator lineage (`22a3874a`, `9f6fc8e`); W3 pure sequential-verdict math is live at `7e6ac9c`; W4 default-off safety-gate/update-baseline wiring and W7 game-layer hardening are landed. Authority remains disabled until readiness passes. The 2026-06-28 strict fold after the E5/v6 restart reports archive authority aligned, baseline fold ready, and sequential cutover ready, but W6 audit cutover is now era-fenced by `pareto_exclude_before_ts`: `100` pre-v6 audited rows are fenced out, current-era W6 has `9/30` trusted audited rows, and the current-era gaming alarm is still triggered. The first post-pool restart missed the W4/W6 env and was stopped at trial `1004`; continue current-era W6 collection under the corrected live `--max-trials 2000` AutoPilot run with `AUTOPILOT_SEQ_VERDICT=1` and W6 audit shadow flags; do not enable sequential verdict/baseline authority until strict readiness passes with `--require-seq-cutover --require-w6-audit`.
- **J11/BSV-2** behavior-signature accept gate — observe-only diagnostics are live (`fd84655e` + `d89b4a9`), same-qid paired reporting now accepts both journal rows and standalone EvalResult-like artifacts (`0943e7c0` + `5b29eead`), and final accept gate remains flag-isolated behind `AUTOPILOT_BSV2_ACCEPT_GATE`.
- **K-SKILL-1** skill-efficacy gate (flag `AUTOPILOT_SKILL_EFFICACY_GATE`) — default-off accept-path wiring landed on the live branch at `924ca50`; keep it flag-isolated from J11 for attribution until N2 W4 cutover.
- **Current runtime evidence**: operator-conservative quarantine covers pre-clean-epoch artifacts `#786-#797`; `#798` is killed-startup audit. Clean vector collection has advanced through the patched trial-888 denominator repair, but readiness is still sample-size blocked. Do not use raw paired-stats counts without filtering quarantined/killed rows. **2026-06-27 v6 matrix unblock:** trial 972 exposed baseline-update refusal on `matrix_status=stale`; topology hash still matched (`df373c79cc4af06f`), but the matrix age exceeded the 30-day certification window after the v6+iqk stack cutover. Orchestrator `526ba3a2` refreshed the measured full/primary pair layer against the live v6 stack, preserved curated same-role/N-way policy, removed the two stale unknown pairs, and passed `check_contention_matrix_fresh.py`. AutoPilot was paused, the long trial 973 worker was terminated during the refresh window, and the post-refresh restart recovered it as `AUTOPILOT_KILLED` before resuming at trial 974 with `--max-trials 2000`.
- Then **H5/EV-4** calibration baseline against the **redesigned** tower (K-EVAL-1 folded into H5 — single owner; see the Package K note).

### Standalone model-batched windows (~27h; group by model so each GGUF loads once)
- ✅ **K-MEM-1 Tulving on `ingest_long_context` completed/scored 2026-06-20** — run `20260619_141212` used `--server-mode --skip-moe-reduction` so evidence reflects production/default GGUF expert settings. Raw artifacts were packaged in research `b6edc64`; corrected score artifacts and `tulving_failure_modes.md` landed in research `9e63af0` after fixing Tulving ground-truth parsing for NumPy-array/list-repr answers. Scorer result: `456/456` scored, missing ground truth `0`, avg F1 `0.4309`, Simple Recall `0.5530`, Chronological Awareness `0.1593`, avg decode `17.27 t/s`. The benchmark log ended `448 completed, 8 skipped, 0 errors`; the eight skipped rows are the reused corrected-resume rows. Research `2eb94f8` adds `data/package_k/tulving_followup_20260619_141212_manifest.jsonl` and `summary.md`: 120 ID-only rows split evenly across zero-answer abstention, event-content/detail recall, and chronology-order cases. Treat this as a mixed baseline and targeted repair slice, not a memory-routing promotion.
- **Current standalone lane** — K-MEM no longer blocks scheduling. Frontdoor G5 short-m@k clean-window evidence is now packaged in `epyc-inference-research` `7e9f67f` at `benchmarks/results/clean_window/short_mk_voting/frontdoor.json`: `status=complete`, `40` questions, `14/40` correct (`0.35` accuracy), GPQA `2/20`, MATH `12/20`, and no completion errors. Frontdoor G11 AA-Omniscience run `20260620_035613` was launched with canonical preflight pass records (`data/preflight/2026-06-20_035546.json`, `data/preflight/2026-06-20_035613.json`) and full-affinity caveat limited to absent old parallel replicas; target `frontdoor :8070` was healthy/idle before launch. It first exited after `24:57` with `26 completed`, `0 skipped`, and `1800 errors`; `/mnt/raid0/llm/tmp/g11_frontdoor_20260620T035601Z.log` shows a completed speed sweep but no claim-grade quality aggregate. Triage root cause: the generated G11 command omitted `--server-mode`, so baseline/moe4/moe6 quality rows fell through to missing subprocess binaries (`completion`, `lookup`) and failed `600` rows each; the successful lookup sweep artifacts are speed-only telemetry. Corrected repair completed under the same run id with `--server-mode --skip-speed-tests --force --baseline-run 20260620_035613`; preflight `data/preflight/2026-06-20_043836.json` passed all gates with an uptime warning. Research `587c6cd` packages `frontdoor_baseline.json`, `frontdoor_moe4.json`, `frontdoor_moe6.json`, lookup telemetry, three preflights, and `summary.md`: all three quality configs have `600/600` non-blank responses and avg TPS `24.8823`, `25.9453`, and `25.7758`. Research `92a5602` adds `data/package_g/omniscience/frontdoor_20260620_035613_aa_omniscience.jsonl` (`1,800` rows), deterministic-F1 summary, and factual-risk aggregation report. Worker G11 then completed as run `20260620_062750` after canonical preflight `data/preflight/2026-06-20_062737.json`; research `32f2c27` packages `worker_general_baseline.json`, the scored JSONL/summary, and factual-risk aggregation report. Worker baseline scored `600` rows with accuracy `0.1433`, avg F1 `0.2280`, hallucination rate `0.6829`, OI `0.2302`, and avg TPS `52.63`. Research `1d80fca` added the guarded resident-server runner path needed to avoid double-loading the 122B model; architect G10 then completed run `20260620_081041` against resident `architect_general :8083` after canonical preflight `data/preflight/2026-06-20_081041.json`, and research `b91d16c` packages/scored it: baseline accuracy `0.1317`, avg F1 `0.2103`, hallucination rate `0.4971`, OI `0.3173`, avg TPS `11.05`, label counts `79` correct / `259` incorrect / `101` partial / `161` not attempted. The combined factual-risk report is `ready_for_tier_update`, and orchestrator `d0e082a7` applied the measured G12 multipliers; do not reopen G12 for scoring-policy work.
- **Clean-window manifest state** — `docs/data/clean_window_measurement_manifest.json` and commands group G10/G11, K-MEM-1, K-ROPE-1, G5, Queue-2 E2/E1, DS-E1 dynamic-stack KV measurement, and the now-run X-MAS constrained-policy A/B by model/window. Current readiness is 21 ready / 6 blocked across 27 entries under observed live ports/contexts after research `7d2dade`. Generated `run_benchmark_suite` commands now include `--server-mode --skip-speed-tests` so clean-window quality runs use the server path and do not re-run speed-only MoE/spec/lookup sweeps. E2 is staged as an attested run-plan generator, E1 as the direct P-BENCH-3 `-np 1,2,4,8,16` sweep; both still require a clean host-health/reboot window for decision-grade claims. Queue-2 and DS-E1 remain clean-window gated and must not run while AutoPilot or live llama-server processes occupy the quiet window; X-MAS is no longer a missing-run blocker after the 2026-06-21 `hold` result.
- **K-ROPE progress** — valid 4K and 8K clean-window cells exist for `frontdoor`, `architect_general`, and `ingest_long_context`; valid 16K cells exist for `frontdoor` and `ingest_long_context`. Exact-boundary rows are now blocked, and `worker_general` is blocked by the Gemma4 MTP 8072 serving/slot-state issue until reloaded/re-attested.
- **K-EMB-1** embedder-only (standalone granite/BGE servers; informs the N9/retrain-routing re-embed choice).
- **H7** Ouro-2.6B transformers-CPU, serial (feeds H5).

### Frozen after DAR-1 replay (~24–28h avoided)
**Package I** (I1 SPO+ / I2 bilinear / I3 ThinkPRM EV-5) — frozen by findings-02's routing reframe and the 2026-06-12 current-traffic DAR-1 replay. The measured regret was 0.00% (<5% reopen gate), so do NOT spend the 24–28 inference-hours unless a future replay after enough new `action_topk` telemetry reaches the gate.

## Staleness corrections (2026-06-12 audit; refreshed 2026-06-19)
- ✅ **J6 CLOSED/SUPERSEDED 2026-06-19** — the continuous autopilot run already satisfied the 24h soak, and orchestrator `2eb4437` closed the code half by making `_eval_concurrency()` matrix-aware: explicit `AUTOPILOT_EVAL_CONCURRENCY` still wins, otherwise the default is capped by topology safe-N and requires a certified-fresh same-role contention-matrix `ALLOW` verdict for background/eval traffic. Missing/stale/invalid matrix evidence fails closed to serial. Do not re-run J6 as a fresh inference task.
- ✅ **G9 respecified 2026-06-12** — the removed `architect_coding` target is gone. G9 now asks only whether MiniMax M2.7 can replace or complement the live `architect_general` role; code-generation replacement is out of scope unless a separate coder-eval owner claims it.
- ✅ **G10/G11 respecified 2026-06-12** — model targets now name the live stack: `architect_general` = Qwen3.5-122B-A10B, `frontdoor` = Qwen3.6-35B-A3B Q8, `worker_general` = gemma4-26B-A4B-it-Q4_K_M.
- ✅ **J12 wiring verification closed 2026-06-12** against production `LlamaServerBackend` `/v1/chat/completions` (NOT `src/backends/openai.py`). Remaining J12 work is the quiesce-window empirical probe + THINK-ABL-1.
- **ALL flag-flip A/Bs must set flags via launch env + per-worker attestation** — `POST /config` reaches only 1 of 6 workers, so any A/B that flips a flag at runtime is invalid. Flags go in the reload env; attest each worker before measuring.
- **The speed-metric policy paragraph below changes when the `task_rate` objective lands** (fable5-findings-05) — the current aggregate-batch-t/s convention is provisional until the objective layer is redesigned.

J6's 24h autopilot soak ran on certified topology `df373c79cc4af06f` (now superseded — see above). The cross-role **N-way contention matrix is closed + certified** (all-allow on certified affinity; defensive runtime policy in `src/scheduling/contention_gate.py` + `orchestration/contention_matrix.yaml`) — handoff archived to [`../completed/cross-role-nway-contention-matrix.md`](../completed/cross-role-nway-contention-matrix.md).

> Binding hard rules (baseline-mutation / live-affinity / concurrent-metric) are in **Remaining Execution Order** below; canonical sequencing is the three-queue structure above. Chronological history → `progress/2026-05/` and `progress/2026-06/`.

## Completed — 2026-04 Campaign (Packages A–F)

Complete or overtaken by the Package J reprioritization. Full runbook detail (commands, expected outputs, results, telemetry plan) archived to **[`../completed/bulk-inference-2026-04-packages.md`](../completed/bulk-inference-2026-04-packages.md)**.

| Pkg | Outcome | Owning handoff |
|-----|---------|----------------|
| **A** | Routing thresholds recalibrated (635 decisions, 2026-04-06) | [`routing-and-optimization-index.md`](routing-and-optimization-index.md) |
| **B** | Instrumented seeding eval v2 — tool-compression +4pp, WS-3 fix validated (2026-04-10) | [`routing-intelligence.md`](routing-intelligence.md) |
| **C** | Context-folding eval batch — 30B summarizer, L3 sweet spot, TALE deferred (2026-04-11) | [`context-folding-progressive.md`](context-folding-progressive.md) |
| **D** | AR-3 relaunch + RI-10 canary (ran autonomously; canary live since 2026-04-06) | [`routing-and-optimization-index.md`](routing-and-optimization-index.md) · [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) |
| **E** | Vision + Hermes multimodal validation — Hermes PASS, vision fixed 2026-04-08 | [`pipeline-integration-index.md`](pipeline-integration-index.md) · [`hermes-agent-index.md`](hermes-agent-index.md) |
| **F** | llama.cpp v3 smoke tests + production binary swap (coder +101%, REAP +50%, 2026-04-10) | [`inference-acceleration-index.md`](inference-acceleration-index.md) |

---
## Remaining Execution Order

> **SUPERSEDED FOR SEQUENCING (2026-06-12)**: the canonical run order is now the three-queue structure at the top (Queue 1 offline-now → Queue 2 one consolidated quiesce window → Queue 3 restart bundle → standalone model-batched windows → frozen Package I). The flat J1→J11 table below is retained as detailed-ordering provenance; the closed placement/matrix gates (J1/J4a-J4c/J4/J5) are compacted in the Package J note. **The hard-rule paragraphs that follow the table (baseline-mutation / live-affinity / concurrent-run metric policy / frontdoor Half0/Half1 / autopilot dispatch defaults) remain binding for any concurrent or bench run.**

| Order | Work | Duration | Why this order / concurrency policy |
|-------|------|----------|--------------------------------------|
| 0 | **Parallel-dispatch integrity + live-affinity preflight** | ~30 min | Before any large run: confirm epyc-orchestrator main is `15350fe` or later plus the concurrency-metric patch if present, run the placement/migration unit subset, verify `AUTOPILOT_EVAL_CONCURRENCY` defaults to topology-safe `max_safe_concurrency(frontdoor)=3`, and confirm 4-way frontdoor traffic queues rather than placing on overlapping q0/q1. Also verify live llama-server process affinity against `NUMA_CONFIG` for every matrix role before trusting any matrix result. Abort the bulk train if this fails. |
| 1 | **J1** WP-2 placement state-machine gate | ~1h | First required inference gate. Proves safe fan-out (full + disjoint quarters + queued overlap) before any downstream task relies on parallel dispatch. |
| 2 | **J2** WP-3 forward-migration verification | ~2h | Verifies shipped session-handover migration semantics and sticky quarter affinity. This is not proactive mid-decode eviction; do not require an impossible in-flight full decode preemption. |
| 3 | **J3** WP-4 reverse-migration verification | ~30 min + analysis | Verifies solo-after-burst recovery before persistent parallel flags stay on. |
| 4 | **J4a/J4b** N-way contention-matrix closure | ~4-12h, runs alone | Required before using cross-role parallelism to accelerate the backlog. Enumerate every non-trivial all-lower-order-allowed active set up to the scheduler's maximum cross-role concurrency, bench it, write N-way verdicts, and fail closed until every candidate is either measured or explicitly pruned/excluded for this topology. |
| 5 | **J5** WP-6 within-role instance-pair matrix re-bench | overnight, runs alone | Completes the within-role side of the matrix. Must run alone because it launches controlled instance-pair benches. |
| 6 | **J10** URE-1 shadow logger | passive | Flip after the matrix gates are safe; it shapes no workload and can accumulate through all later traffic. |
| 7 | **J12** chat_template_kwargs wiring verification | CLOSED 2026-06-12 | Non-inference wiring verified; remaining work is the Queue-2 empirical probe + THINK-ABL-1 under declared production env. |
| 8 | **J4** WP-5 ratification observation + **J9/J11** observe-only/paired gates where wired | 6-12h | Uses the newly verified parallel-dispatch path and completed matrix. J9 is observe-only; J11 runs per accepted mutation. Keep paired-eval attribution sequential unless explicit concurrent approval exists. |
| 9 | **J6** WP-7 24h rollout | 24h passive | Requires J4a/J4b/J5. J7/J8/J9/J10/J11 can co-run only when their own flags are observe/advisory, the N-way matrix allows the specific active set, and run metadata records concurrency. |
| 10 | **J7** DCP inference gate + optional **J8** legacy BEP A/B | 3-4h each | J7's DCP-4 hook is already default-off/advisory, the offline replay is closed, `29b9ba3` adds the off/on A/B runner, and `56a72f6` packages the first live A/B. Initial result: zero errors/all delegated, fewer generated tokens with DCP ON, but worse p50 latency; no enablement. J8 is not a remediation gate; run it only if its answer would change whether the legacy `batch_edit_mode` path is kept, retired, or exposed as a narrow task-class knob. |
| 11 | **Package H/I/G residuals and D-tail** | variable | H7 before H5; I1 before I2; I3 independent. Standalone G benches can fill downtime, but do not co-run with J4a/J4b/J5 or any standalone throughput bench. |

**Completed historical ordering**: E/B/F/C and the completed G/AM/SEAL items remain documented below for provenance only. Do not use their April ordering as the current run order.

**Concurrent-run metric policy**: When `AUTOPILOT_EVAL_CONCURRENCY>1`, fan-out is allowed only inside a single trial's eval batch; do not run separate trials concurrently in one autopilot process. Individual request tokens/sec normally drops while aggregate batch throughput can improve. Every concurrent eval must record `speed_metric_mode`, `eval_concurrency`, median per-request t/s, aggregate batch t/s, and eval wall time. For concurrent eval batches, the SafetyGate/Pareto `speed` objective is aggregate batch t/s; the raw median request t/s is retained as audit metadata. This prevents the planner from treating safe same-trial fan-out as a regression while still exposing the per-instance slowdown for diagnostics. Cross-role bulk parallelism is stricter: pairwise-allowed is necessary but not sufficient; before J4b completion, unmeasured N-way active sets fail closed. After J4b completion for the current topology, there should be no unclassified N-way active set: each is measured `allow`, measured `block`, or explicitly pruned/excluded by a lower-order failure. This closed-world guarantee is scoped to the exact `topology_hash` / stack state measured by J4b; any future orchestration-stack, role, model, CPU binding, or server-launch topology change invalidates the matrix and requires re-derivation before using cross-role parallelism again.

**Baseline mutation hard rule**: Do not update production baselines, Pareto archives, regression thresholds, learned scheduling priors, routing speed priors, or trial-scheduling evidence from any run unless `speed_metric_mode`, `topology_hash`, and `matrix_status` are recorded and valid. Cross-role concurrent runs must also record the exact N-way active-set verdict or a same-trial within-role fan-out marker. Missing, stale, or inconsistent metadata means diagnostic-only quarantine.

**Live-affinity hard rule (2026-05-26 stack audit)**: `topology_hash` is necessary but not sufficient. It fingerprints the intended `NUMA_CONFIG`, not proof that the currently running llama-server processes were launched with the intended `taskset`/`numactl` prefix. Before J4/J5/J6 or any downstream concurrent run, compare each live port's `/proc/<pid>/task/*/status` `Cpus_allowed_list` union against the exact `NUMA_CONFIG[role].instances[idx]` CPU list. If any process has CPUs outside the expected set or misses expected CPUs, mark matrix status `diagnostic_only`, reload that role through `scripts/server/orchestrator_stack.py`, rerun the affinity check, and rerun all matrix rows involving the affected role/shape before baseline mutation or bulk parallelism.

**Frontdoor Half0/Half1 interpretation**: The dashboard's `Half0` cell for frontdoor is the current idx0 solo/full-speed anchor shape (`0-47,96-143`), not evidence that a validated second `Half1` frontdoor instance exists. Current certified frontdoor concurrency is via the existing q0-q3 quarter instances. Adding a dedicated frontdoor `Half1` replica is a new topology experiment, not a matrix-repair assumption: it requires a new server/port, explicit placement policy, fresh topology hash, isolated benchmarks comparing Half0+Half1 against the current Half0-plus-quarters policy, and a new matrix derivation before it can accelerate the bulk backlog.

**Autopilot dispatch-latency defaults (2026-05-26 hardening)**: before starting the long bulk train, run on an orchestrator containing `scripts/autopilot/phase_status.py`, the dashboard `autopilot_phase` panel, async auxiliary plot/digest scheduling, and contention-aware seed-role waves. Recommended environment:

```bash
AUTOPILOT_ASYNC_AUX=1
AUTOPILOT_ASYNC_WORKERS=2
AUTOPILOT_SEED_ROLE_CONCURRENCY=auto
AUTOPILOT_PAUSE_POLL_S=1
AUTOPILOT_HEALTH_BACKOFF_S=10
```

Use the dashboard phase panel to classify idle gaps before changing scheduling policy: stopped/down, paused, health backoff, planner prompt build, planner invoke, dispatch, journaling, checkpointing, or async artifact scheduling. Seeder fan-out is allowed only for background contention-matrix-safe role waves; missing/stale/unknown matrix evidence should collapse toward serial behavior. Request-level `trial_id`/`batch_id` propagation through benchmark HTTP callers is still deferred because those callers have high/critical GitNexus blast radius; the current phase heartbeat gives loop-level attribution without changing those contracts.

---

## Package G: Deferred Inference-Dependent Research Tasks

**Duration**: Variable (opportunistic — run during Package D downtime or after D completes)
**Stack required**: Individual model servers (like Package C)
**Depends on**: Nothing — independent research evaluation
**Status**: NOT STARTED — indexed here 2026-04-11 during handoff audit

These tasks are scattered across active handoffs and require inference compute but are not time-critical. Consolidated here so they can be scheduled opportunistically.

| # | Task | Source Handoff | Description | Models Needed | Effort |
|---|------|---------------|-------------|--------------|--------|
| G1 | Memento S2 feasibility | [memento-block-reasoning-compression.md](memento-block-reasoning-compression.md) | Benchmark KV masking overhead on llama.cpp. Test if KV states from masked blocks preserve accuracy. | Any 8B+ model | ~4h |
| G2 | Expected Attention S8 profile sweep | [triattention-kv-selection.md](triattention-kv-selection.md) | Sweep `keep_ratio` and `layer_weights` per production role; record Pareto profile with quality, speed, cost, and reliability axes. Historical S1 deployment evidence moved to completed ledger. | coder_escalation + one long-context role | ~4h |
| G3 | Expected Attention stacking/high-compression check | [triattention-kv-selection.md](triattention-kv-selection.md) | Reopen selection + quantization stacking only if S8 shows production need for higher compression; otherwise compare Attention Matching before adding kernel complexity. | coder_escalation | ~4h |
| G4 | FlowSteer activation steering | [reasoning-compression.md](reasoning-compression.md) Tier 2 | Test nonlinear activation steering for concise reasoning on 30B-A3B worker. | worker_general | ~6h |
| G5 | short-m@k voting baseline | [reasoning-compression.md](reasoning-compression.md) Tier 1 | Run k=3 parallel generations, majority vote. Measure accuracy vs single-shot on GPQA/math. | Any reasoning model | ~4h |
| G6 | v3 clean NUMA throughput | [llama-cpp-v3-upstream-rebuild.md](../completed/llama-cpp-v3-upstream-rebuild.md) | Isolated NUMA test (requires stopping production stack). Compare v3 vs v2 48t quarter throughput. | frontdoor or worker | ~1h |
| G7 | MiniMax M2.7 download + launch | Research intake (intake-328/329) | ✅ DOWNLOADING: Q8_0 (243GB) + UD-Q4_K_XL (141GB) from unsloth/MiniMax-M2.7-GGUF → `/mnt/raid0/llm/models/MiniMax-M2.7-GGUF/`. MoE 230B-A10B, 256 experts, 200K ctx. Launch with `--spec-type ngram-simple --draft-max 64`, `numactl --interleave=all`. No spec-dec (200K vocab, no compatible draft). Expected: Q4_K_XL ~12-16 tps w/ ngram, Q8_0 ~9-13 tps w/ ngram. | Standalone | ~2h |
| G7a | MiniMax M2.7 NUMA sweep | — | Sweep NUMA parallelization: 1×192t interleave vs 2×96t per-node vs 4×48t quarters. Model fits single node (~141-243GB vs ~560GB/node). 256-expert scatter pattern may favor interleave. | Standalone | ~3h |
| G8 | MiniMax M2.7 tool-calling | Research intake (intake-328/329) | Evaluate tool-calling reliability vs Qwen3 stack. Test orchestrator function-calling pipeline. | Standalone | ~4h |
| G9 | MiniMax M2.7 architect_general replacement eval | Research intake (intake-328/329) | **Goal: test whether MiniMax M2.7 can replace or complement the live `architect_general` role only.** The removed `architect_coding` role is no longer a target. Compare M2.7 against current `architect_general` (Qwen3.5-122B-A10B) on architecture/general-reasoning tasks plus any existing MiniMax G8 tool-calling evidence. Do not treat this as a coder replacement or RAM-consolidation decision unless a separate coder-eval owner reopens that scope. | Standalone | ~4-6h |

### Progress (updated 2026-04-13)

- **G1 (Memento S1)**: ✅ Feasibility CONFIRMED (2026-04-13). `llama_memory_seq_rm()` supports mid-sequence block eviction. Runtime validation passed (slot erase + continued generation). OpenMementos-228K downloading (`microsoft/OpenMementos`). S2 (LoRA) is next.
- **G2 (EA S1)**: ✅ Scaffold ready + proxy evaluation done (2026-04-13). KV compression at 50% removal: cosine=1.000 on NIAH tasks. Full KVPress integration needs compatible transformers version.
- **G3 (stacking)**: PENDING — depends on G2 full evaluation
- **AM P2**: ✅ Validated on Qwen2.5-7B (2026-04-13). 2x=1.000, 5x=0.906, 10x=0.807. Layer-adaptive strategy identified.
- **AM L1-L3b**: ✅ COMPLETE (2026-04-13). Beta bias kernel in llama.cpp-experimental, public `llama_memory_set_beta()` API, server `POST /slots/{id}?action=set-beta` endpoint, E2E test on Coder-32B f16. Full pipeline: Python compaction → HTTP beta injection → server decode. Next: quality comparison test.
- **SEAL cvector**: ✅ Pipeline validated (2026-04-13). Trained 28-layer concise reasoning vector on 7B. A/B: +1.8% tokens (minimal at 7B, real experiment targets 30B+). Fixed v3 GGML_OP_GLU build issue (stale libggml-cpu.so).

### New tasks for AR-3 fold-in assessment

The following medium-term tasks could piggyback on AR-3 stack sessions:

| Task | Can fold into AR-3? | Notes |
|------|---------------------|-------|
| **PPL sweep** (v3 baseline) | YES — run during AR-3 warmup/cooldown | `llama-perplexity` on wikitext2 for coder, frontdoor, worker, REAP. Independent of stack. ~1h total. |
| **AM P3** (AM vs EA head-to-head) | PARTIAL — needs model loaded, not full stack | Compare AM HighestAttnKeys-fast vs Expected Attention at 5x/10x/20x on same model. Python-only, ~4h. Can run during Package D downtime. |
| **RI-10 canary** | YES — this IS Package D | Extended to 2026-04-27, n=16/50 high-risk samples. AR-3 generates these samples. |
| **SEAL on 30B** | NO — needs dedicated server with cvector | Train + eval concise reasoning vector on Qwen3-Coder-30B-A3B. Separate from orchestrator stack. |
| **AM P2 on 32B** | ✅ DONE — E2E beta injection tested on 32B f16 | L1-L3b complete. Beta injection via server endpoint works on Coder-32B. Full compaction quality test next. |
| **ColBERT reranker S1 data** | YES — passive (already instrumented) | S1 relevance logging in `_web_research_impl()` fires on every web_research call. AR-3's 50-question `web_research` sentinel suite generates the data. After AR-3, grep logs for `web_research relevance summary` to measure irrelevant page rate. If >20%, proceed to S3 (model download). See [colbert-reranker-web-research.md](colbert-reranker-web-research.md). |
| **SearXNG backend validation (SX-5/SX-6)** | YES — activate via feature flag | SX-1/2/3/4 implemented (Docker service, `_search_searxng()`, settings.yml, telemetry). Activate `ORCHESTRATOR_SEARXNG_DEFAULT=1` during AR-3 warmup trial. The web_research sentinel suite (50q) validates SearXNG search quality under real query patterns. Telemetry: `searxng unresponsive_engines` logs engine failures; S1 relevance instrumentation measures page quality. If no regression on first warmup trial, lock in SX-6 swap. If regression, disable flag and iterate on SX-3 engine tuning. Post-AR-3: analyze engine failure rates + result quality delta vs DDG baseline. See [`searxng-search-backend.md`](searxng-search-backend.md) P12. |

### Prioritization (updated 2026-04-13)

- **G1 + G5 together**: Memento S1 DONE. G5 runner/manifest wiring is READY in research `cbf00e1`; run the clean-window G5 GPQA/math commands with the standalone model-batched window, not during active AutoPilot evidence collection.
- **G2 + G3 sequentially**: G2 proxy DONE (gate passed). Full KVPress evaluation + G3 stacking test pending. **AM compaction is now the primary path** — P2 results show structured attention compresses near-losslessly at 2-5x with layer-adaptive strategy.
- **G4**: Defer — FlowSteer library maturity unconfirmed.
- **G6**: Low priority — v3 smoke tests showed no regression.
- **G7**: ✅ COMPLETE (2026-04-17). All models downloaded and benchmarked. Q4_K_XL deleted (Q8 preferred for quality). M2.7 Q8 = 11.1 tps. Also swept: Qwen3.6 Q8 (27.4 tps), SG4-26b Q4 (42 tps), SG4-31b Q4 (9.0 tps), SG4-26b-MM Q8 (21.1 tps), Gemma4 E2B/E4B (deleted — no value).
- **G7a**: ✅ COMPLETE (2026-04-17). Full NUMA characterization with concurrent requests. Key findings: (1) --mlock + --membind required for multi-instance, (2) Q8 > Q4 for dense models < 40GB, Q4 > Q8 for large MoE, (3) concurrent benchmarks show ~40% less aggregate than serial sum. New deterministic `numa_sweep.py` with early stopping + scaling gates.
- **G8 + G9**: IN PROGRESS (2026-04-19). Quality benchmarks run with Claude-as-Judge scoring. Multiple iterations to fix model-specific serving issues (chat templates, reasoning mode, KV cache, repeat_penalty). Partial results: SG4-26b-MM 65.4%, SG4-31b 60.5%, M2.7 55.7%. Qwen3.6 still iterating (thinking model config). SG4-26b Q4KM deprecated (irrecoverable degeneration at Q4). Final run with `--reasoning off` in progress for all 4 remaining models.
- **G10 + G11 + G12**: AA-Omniscience hallucination calibration — can run per-model sequentially, ~6h total.

### G10-G12: AA-Omniscience Factual-Risk Calibration (2026-04-15 research intake)

**Source**: intake-381/intake-383 ([arxiv:2511.13029](https://arxiv.org/abs/2511.13029)), [routing-intelligence.md](routing-intelligence.md) Phase 4 calibration gap
**Dataset**: `ArtificialAnalysis/AA-Omniscience-Public` (600 Qs, Apache 2.0, already in HuggingFace cache)
**Goal**: Replace heuristic capability tiers in `factual_risk.py` (`_DEFAULT_ROLE_TIERS`: tier_1=0.6, tier_2=0.8, tier_3=1.0) with measured per-model hallucination rates. **Done 2026-06-20**: deterministic AA-Omniscience 4-class scoring was accepted for this role-tier recalibration, and orchestrator now uses measured tier_1 `0.727978`, tier_2 `0.824178`, tier_3 `1.0`.

Scoring methodology (from paper): Omniscience Index = 50% accuracy + 50% (1 - hallucination_rate), where hallucination_rate = incorrect / (incorrect + partial + not_attempted). Answers graded as CORRECT/INCORRECT/PARTIAL_ANSWER/NOT_ATTEMPTED. Models prompted to say "I don't know" rather than guess.

| # | Task | Description | Models Needed | Effort |
|---|------|-------------|--------------|--------|
| G10 | AA-Omniscience: architect_general | Run 600 Qs through the live `architect_general` target, Qwen3.5-122B-A10B. Record per-domain accuracy + hallucination rate. Expect above-zero Omniscience Index. | architect_general (solo) | ~2h |
| G11 | AA-Omniscience: frontdoor + worker | ✅ Raw-response + deterministic-F1 evidence packaged for live `frontdoor` (research `587c6cd` + `92a5602`) and live `worker_general` (research `32f2c27`). | frontdoor, worker_general (sequential) | complete |
| G12 | Calibrate capability tiers | ✅ Deterministic AA-Omniscience 4-class scoring accepted for role-tier recalibration; `_DEFAULT_ROLE_TIERS`, default config, and live `classifier_config.yaml` updated to measured multipliers. Future SimpleQA augmentation is optional evidence expansion, not a blocker for this tier update. | No inference — analysis only | complete |

**2026-06-19 G12 offline prep:** Orchestrator `7d729e3` repaired
`scripts/build_factual_risk_calibration_v2.py` so HuggingFace `datasets` is not shadowed by the local
`scripts/datasets` package when run by path, hardened JSONL writing to ASCII-escape Unicode line separators,
and regenerated the v2 calibration artifacts:
`orchestration/factual_risk_calibration_v2.jsonl` plus `_train`, `_val`, `_test`. Completed artifact has
2,600 rows (`v1_regex` 2,000 + `aa_omniscience` 600), risk features populated for all rows, and split counts
1,806 / 375 / 419. This is dataset prep only; G10/G11 live per-model AA-Omniscience runs and the downstream
`src/classifiers/factual_risk.py` tier update remain open and should stay on the main thread when touched.

**2026-06-19 measurement/report prep:** Research `cf3cd3a` added
`scripts/benchmark/aa_omniscience_manifest.py` plus generated
`docs/data/aa_omniscience_measurement_manifest.json` and
`docs/data/aa_omniscience_measurement_commands.sh`. The adapter preflight sees all 600 AA-Omniscience
questions, 56 candidate roles, 43 ready roles, and 13 blocked roles with missing local model paths. The
generated command file leaves canonical preflight enabled and comments blocked roles instead of executing
them. Research `7d27597` refreshed this generator after the failed frontdoor G11 run so every AA quality command
uses `--server-mode --skip-speed-tests`; do not resurrect the older subprocess/speed-sweep command shape for
G10/G11 evidence. Orchestrator `8546b3e` added `scripts/analysis/factual_risk_calibration_report.py`, which summarizes
the v2 corpus/splits and can aggregate future G10/G11 result JSONL by role/model/outcome. Orchestrator
`61e670d` extends that report with AA outcome rates and a fail-closed `tier_calibration_readiness`
block. After research `b91d16c`, the deterministic report observes all expected roles and reports
`ready_for_tier_update`: architect multiplier preview `0.727978`, frontdoor `0.824178`, and
worker_general `1.0` relative to the current worst observed hallucination rate. Orchestrator then accepted deterministic
AA-Omniscience 4-class scoring for this role-tier recalibration only and updated `src/classifiers/factual_risk.py`,
`src/classifiers/config_loader.py`, and `orchestration/classifier_config.yaml` to those measured values. Factual-risk
mode/canary/enforce decisions remain on their separate telemetry gates.

**Implementation notes**:
- Prompt template from paper: `"You are answering questions about {domain}, and in particular {topic}. You will be given a question, answer with JUST the answer (no explanation). If you do not know the answer, or you need more context or tools to answer the question, be clear about this - it is better that you say this than get the wrong answer."`
- Grading: LLM-as-judge with 4-class output, or regex for exact-match answers (many are short factual: dates, names, section numbers)
- Results persist to `data/package_g/omniscience/` per model — incremental (one row per question)
- Key output: `{model}_{domain}_hallucination_rate.json` → feeds tier recalibration
- SimpleQA augmentation: grep seeding logs for `simpleqa` suite with `passed=False`, extract prompt+answer pairs, cross-reference with AA-Omniscience domains for combined calibration

**Exit criteria**:
- [x] Per-model hallucination rate per domain computed
- [x] Empirical tier multipliers differ from heuristic by >5% (otherwise heuristic was adequate)
- [x] `factual_risk.py` `_DEFAULT_ROLE_TIERS` updated with measured values
- [x] routing-intelligence.md Phase 4 calibration gap closed for role-tier calibration

## Package H: Research-Driven Inference Tasks (2026-04-12 research intake)

**Duration**: Variable (~12-16h total if sequential)
**Stack required**: Standard orchestrator stack (frontdoor + coder) for most; Ouro needs transformers separately
**Depends on**: Non-inference Tasks 10-11 (DSPy/GEPA install + dspy.RLM setup)
**Status**: NOT STARTED — indexed 2026-04-12 from research intake deep-dives

These tasks evaluate research-intake findings that require live inference. Ordered by dependency chain.

| # | Task | Source Handoff | Description | Models Needed | Effort |
|---|------|---------------|-------------|--------------|--------|
| ~~H1~~ | ~~GEPA frontdoor optimization (AP-19)~~ | ~~[autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) P10~~ | → **Folded into Package D** (2026-04-12). GEPA integrated as PromptForge mutation type. AR-3 runs GEPA trials at 30% of PromptForge budget. | — | — |
| ~~H2~~ | ~~GEPA Full Program Adapter eval (AP-20)~~ | ~~[autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) P10~~ | → **Folded into Package D**. Resolved by comparing GEPA vs LLM mutation acceptance rates in AR-3 journal. | — | — |
| ~~H3~~ | ~~PromptForge GEPA integration test (AP-21)~~ | ~~[autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) P10~~ | → **Folded into Package D**. Decision from AR-3 data: if GEPA dominates Pareto frontier after 50+ trials → increase ratio to 100%. | — | — |
| H4 | dspy.RLM integration testing (AP-26) | [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) P11 | Test dspy.RLM for benchmark analysis via REPL exploration. Coder as main LM, frontdoor as sub_lm. **Post-AR-3** — controller change too risky mid-run. | coder + frontdoor | ~2h |
| H5 | RLVR eval tower validation (AP-27) + calibration baseline (EV-4) | [eval-tower-verification.md](eval-tower-verification.md) EV-4 + [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) P11 | Run eval tower on Scoring Verifiers HE-R+ to establish ECE/AUC baseline (EV-4), then validate T0/T1/T2 as RLVR verification functions. **Depends on**: EV-1+EV-2+EV-3 (non-inference prep, now complete after research `7c11920` fixed candidate-level Scoring-Verifiers labels) + P7 Ouro results. **Post-AR-3** — modifies eval trust boundary. | full stack | ~4h |
| ~~H6~~ | ~~GEPA search algorithm eval (MH-4)~~ | ~~[meta-harness-optimization.md](meta-harness-optimization.md) Tier 2b~~ | → **Folded into Package D**. Pareto frontier contributions by mutation source analyzed from AR-3 journal. | — | — |
| H7 | Ouro-2.6B-Thinking benchmark (P7) | [research-evaluation-index.md](research-evaluation-index.md) P7 | Run MATH-500 + reasoning suite via transformers on CPU. NOT llama.cpp. Standalone. No stack conflict if needed, but not urgent — feeds H5 which is post-AR-3. | Ouro-2.6B (transformers, CPU-only) | ~4h |

### Prioritization (updated 2026-04-12)

- ~~**H1/H2/H3/H6**~~: **Folded into Package D** (2026-04-12). GEPA integrated into PromptForge as mutation type. AR-3 generates comparison data organically. See `scripts/autopilot/species/gepa_optimizer.py`.
- **H4 post-AR-3**: dspy.RLM testing. Controller architecture change — defer to AR-4.
- **H5 post-AR-3**: RLVR formalization + EV-4 calibration baseline. Non-inference prep (EV-1/2/3/6) now complete — ready for inference run. Defer to AR-4. Depends on H7.
- **H7 post-AR-3**: Ouro benchmark. Standalone (transformers CPU, no stack conflict). Feeds H5. Not urgent.

---

## Package I: Decision-Aware Routing Validation (post-AR-3)

**Duration**: ~2 days (DAR-3 exploration needs sustained traffic for counterfactual data)
**Stack required**: Full orchestrator stack
**Depends on**: Future DAR-1 replay reaching the >=5% regret reopen gate + N2 per-question eval vectors. The current-traffic replay on 2026-06-12 did **not** reach the gate (0.00% identifiable mean regret), so Package I remains frozen. Historical DAR-1 analysis also found uniform Q (April: 96%; current replay: 99.1%).
**Status**: NOT STARTED — indexed 2026-04-15 from research deep-dive

These tasks modify routing behavior and need isolated measurement. Running exploration routing during Package H's research eval would contaminate both.

| # | Task | Source Handoff | Description | Models Needed | Effort |
|---|------|---------------|-------------|--------------|--------|
| I1 | DAR-3 SPO+ exploration | [decision-aware-routing.md](decision-aware-routing.md) DAR-3 | 10% epsilon-greedy exploration routing for counterfactual data collection. Convex SPO+ loss replaces TD update. | full stack | ~3-4 sessions |
| I2 | DAR-4 bilinear scorer A/B | [decision-aware-routing.md](decision-aware-routing.md) DAR-4 | Model-feature-conditioned Q vs current per-action Q-tables. Zero cold-start for new models. | full stack | ~2 sessions |
| I3 | EV-5 ThinkPRM-1.5B T2 | [eval-tower-verification.md](eval-tower-verification.md) EV-5 | Deploy ThinkPRM-1.5B-Q4KM for T2 process verification on uncertain questions. Cross-family constraint enforced. | ThinkPRM + eval stack | ~4h |

### Prioritization

- **I1 (DAR-3)**: Highest priority — generates counterfactual data needed for decision-aware training. Must run with sustained traffic.
- **I2 (DAR-4)**: Can run after I1 data collection. A/B comparison: bilinear scorer vs current Q-scorer on same traffic.
- **I3 (EV-5)**: Independent of I1/I2. Deploy ThinkPRM-1.5B, run T2 verification pass. Validate cross-family constraint (EV-6, already in code).

### DAR-1 Preliminary Results (2026-04-15)

Initial regret analysis on 7,211 routing decisions (Apr 10-14):
- 96% uniform Q-values — Q-scorer has barely learned preferences
- Selection score spread is non-trivial (median 0.107) — comes from cost/similarity, not Q-values
- 25% trivial spread (<0.01)
- Implication: DAR-2 contrastive training needs more routing memories. Consider seeding-driven memory accumulation before Package I.

---

## Package J: Within-Role Placement + Audit-Batch Inference Gates (2026-05-26)

> **▶ STATUS UPDATE (2026-05-27) — supersedes the "Status" line below.** The 2026-05-26 status is stale. Current truth (reconciled against `orchestration/contention_matrix.yaml` + `data/bulk_inference_2026_05_26/execution_manifest.jsonl`):
> - **Contention matrix: CLOSED + certified, ALL-ALLOW.** The famous `{frontdoor,ingest,vision}=0.847` "block" was a **bad-affinity artifact** (launcher `_numa_prefix` bug mis-pinned quarters); re-benched on certified disjoint quarters (`live_affinity_verified=true`) it is **1.731 allow**, and every measured N-way set allows (`4363dae`). **No measured N-way block remains.** New hard gate: `live_affinity_verified` + `affinity_preflight.py` artifact (topology_hash alone is insufficient).
> - **J4b/J5: SUPERSEDED** by the certified re-bench (their verdicts were bad-affinity). **J4c: LIVE but now DEFENSIVE** (`nway_policy` wired; nothing currently queues). **J4: RATIFIED** (placement SM live; per-role policy decided). **J6: relaunched repeatedly** (soak runs on `df373c79`, production API; the live daemon pid changes on every relaunch — discover it at runtime via `pgrep -af "autopilot.py start"`, do not trust any pid written here).
> - **J1 core PASS; J2/J3 NOT live-closed** — migrations never naturally triggered in the ratification autopilot; a dedicated live migration probe is still pending.
> - **BEP-2 status changed after the 2026-05-27 edit-transaction work**: the read-loop is no longer the active remediation blocker. Qwen3.6 passed the direct one-shot ablation 5/5, and the default-off `force_mode="edit"` transaction path is built + hardened. **J8 is now optional for a narrower decision**: whether to keep, retire, or task-scope the legacy structured patchset/batch-edit path. **DCP-6 is no longer gated on BEP's read-loop**, and DCP-4 advisory attach is already wired/default-off; only its offline replay + eval remain.
> - **N-way runtime policy** is fail-OPEN for unmeasured foreground / closed-world for background-bulk (matches the code + cross-role-bw handoff); the older "closed-world serialize" wording is superseded.

**Duration**: ~1-3 days if sequenced; J5 (matrix re-bench) can run overnight
**Stack required**: Standard orchestrator stack; J1-J3 require `ORCHESTRATOR_PLACEMENT_STATE_MACHINE=1`; J3 additionally requires `ORCHESTRATOR_REVERSE_MIGRATION=1` set in the API env
**Depends on**: epyc-orchestrator main @ `15350fe` or later — both feature branches MERGED 2026-05-26 (`fe6805c` placement WP-0..WP-4 + WP-5 scaffold; `15350fe` intake-607 harness DCP/BEP/BSV/URE). 347 unit tests on main; all new code additive + flags default-OFF. No further branch merging needed before any J task.
**Status**: IN PROGRESS (claude 2026-05-26). Preflight PASS (67 tests). **J4a DONE** (`data/contention_matrix/bulk-2026-05-26-j4a/`). **J1 core PASS** — placement SM scales concurrent frontdoor 1.68×–1.91× across disjoint instances, no overlap; the `topology_overlap` queue is NOT observable via `/chat` (HTTP rate limiter 60rpm/10burst + a persistent dashboard client cap concurrent arrivals) → **J1 queue + J2/J3 migration verification re-vehicled to the autopilot eval-concurrency fan-out path** (the original WP-0 motivation). **J4b**: first full-instance pass exposed an operator-flagged methodology error → corrected to a **quarter-level disjoint-cpuset feasibility model** (`enumerate --feasibility`: 25 feasible / 32 `topology_infeasible`); quarter-level re-bench (`--safe-sampling`) IN PROGRESS (`data/contention_matrix/bulk-2026-05-26-j4b-feasible/`). **gemma4 worker_general full-instance crash FIXED** (uncaught PEG-parser throw → raw-content fallback; ik_llama.cpp `d84755dc`, rebuilt+redeployed+verified). Findings F1–F4 in [within-role-placement-state-machine.md](within-role-placement-state-machine.md); correction detail in [cross-role-nway-contention-matrix.md](../completed/cross-role-nway-contention-matrix.md). Remaining: finalize quarter-level matrix → J4c policy wiring → J5/J4/J6 → J7–J12.

**2026-05-27 Codex audit checkpoint**: this runbook is structurally correct, but several execution-state surfaces
need a consistency sweep before launching another nonstop bulk agent. Later certified-affinity results supersede
older manifest/handoff rows that still cite the `{frontdoor,ingest,vision}` `0.847` block as live proof; current
matrix/progress says that row was a bad-affinity artifact and remeasured `allow`. Runtime safety also needs two
code-level hardening items before baseline-eligible cross-role bulk parallelism: `ContentionGate.matrix_health()`
should check the live topology hash, and `SafetyGate.update_baseline()` should enforce the documented
`speed_metric_mode`/`topology_hash`/`matrix_status` baseline mutation rule. J2/J3 live migration verification
remains open; do not call J1-J3 complete until the dedicated probe produces evidence. See the 2026-05-27 progress
entry "Codex bulk-campaign audit + wrap-up skill checkpoint" for the full findings list.

Inference-gated verifications and observability runs for the within-role-placement-state-machine handoff. Also bundles the two sibling inference gates from the 2026-05-25 audit batch (DCP-6, BEP-2) because they share the same "needs autopilot-style eval workload" profile and benefit from one operator sitting + one cleared stack window. Add other-agent inference-gated items under this Package (or a successor) for shared sequencing.

### Priority-zero sequencing (RUN FIRST)

> **J1 → J2 → J3 → J4a/J4b/J5 must run BEFORE any downstream inference Package that relies on parallelism** (D-tail, G/H/I, J4/J6-J9, or other-agent items appended at the end). Reason: J1-J3 enable the within-role WP-2/3/4 parallelization flags, while J4a/J4b/J5 finish the cross-role and within-role matrix evidence needed to decide which concurrent active sets are actually throughput-positive. Once verified and left on, every subsequent autopilot/eval/bench task benefits from safe concurrency without corrupting throughput metrics or scheduling priors.
>
> Equivalent ordering rule for the global Execution Order table: insert **`J1, J2, J3, J4a, J4b, J5`** ahead of any not-yet-started inference Package that could use shared-stack concurrency. Don't backfill `Package E/B/F/C` ordering — those already completed.
>
> If the operator wants to mix flag-enablement validation with downstream work in the same sitting, the safe interleave is: J1 (~1h) → J2 (~2h) → J3 (~30-min profile) → J4a dry-run enumeration → J4b/J5 matrix benches in isolated slots → enable flags persistently → proceed with anything else.

### Parallel-dispatch integrity preflight (abort-on-fail)

Before starting the bulk train, run this preflight on the orchestrator checkout:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
python3 -m py_compile src/backends/concurrency_aware.py src/scheduling/placement.py scripts/autopilot/eval_tower.py scripts/autopilot/safety_gate.py scripts/autopilot/autopilot.py
pytest -q tests/unit/test_eval_tower_concurrency_metrics.py \
  tests/unit/test_topology_concurrency.py \
  tests/unit/test_dispatch_placement_state_machine.py \
  tests/unit/test_per_region_locks_migration.py \
  tests/unit/test_load_transition_migration.py \
  tests/unit/test_reverse_migration.py \
  tests/unit/test_migration_transaction.py
```

Gate expectations:
- `AUTOPILOT_EVAL_CONCURRENCY` unset resolves to `max_safe_concurrency(frontdoor)=3`; any explicit override above 3 is a deliberate stress test, not a production default.
- Four concurrent frontdoor requests show exactly 3 active safe placements and one queued/denied for `topology_overlap`; no q0/q1 overlap with full is allowed.
- Concurrent eval results include `speed_metric_mode`, separate median request t/s, and aggregate batch t/s metadata. If a run predates that telemetry, compute the two metrics manually from logs and mark the trial analysis as concurrency-audited before using it for scheduling decisions.
- Live process affinity matches `NUMA_CONFIG` for all roles used by J4/J5/J6. Minimum check: enumerate live llama-server ports, map port->role/index from `NUMA_CONFIG`, union all thread `Cpus_allowed_list` values for each PID, and assert exact equality with the expected CPU set. Record the result in the execution manifest as `live_affinity_verified: true` plus `affinity_artifact`.
- Specific 2026-05-26 audit hazard: frontdoor and ingest affinities were observed correct, but `worker_general` and `vision_escalation` quarter ports were observed with wrong live affinity when their special launcher paths used `_numa_prefix(role)` instead of `_numa_prefix(role, numa_instance)`. After applying/reloading the launcher fix, rerun the affinity check and treat pre-fix worker/vision matrix rows as diagnostic until re-measured.
- If any of these fail, stop. Do not run D-tail/G/H/I/J4+ on top of a suspect dispatcher, stale live affinity, or unlabelled concurrent speed metric.

> **CLOSED placement + matrix gates (J1, J4a, J4b, J4c, J4, J5, J6) — runbook should migrate to `handoffs/completed/`.** Per the 2026-05-27 status update above plus the 2026-06-19 J6 closure: J1 core PASS; J4b/J5 SUPERSEDED by the certified disjoint-quarter re-bench (`4363dae`, all-allow, `live_affinity_verified=true`); J4c LIVE-but-defensive (`nway_policy` wired, nothing queues); J4 RATIFIED (placement SM live, per-role policy decided); J6's soak is superseded by the continuous run and its EvalTower default is now matrix-aware (`2eb4437`). Their detailed commands/gates/manifest are reference-only and should move to the completed placement runbook (`within-role-placement-state-machine.md` + `../completed/cross-role-nway-contention-matrix.md` own the canonical copies). The only OPEN item from the placement block is **J2/J3** (live migration probe — never naturally triggered), scheduled in Queue 2. The table below retains J2/J3 + J7-J9 rows; J6 is closed/superseded.

| # | Task | Source Handoff | Description | Models Needed | Effort |
|---|------|---------------|-------------|--------------|--------|
| J2 | WP-3 forward-migration verification | [within-role-placement-state-machine.md](within-role-placement-state-machine.md) § Phase 3 | Forward migration is shipped on the existing session-handover trigger (transactional, policy-gated), not as proactive mid-decode eviction. Verify: under sustained 2+ concurrent traffic with session handover on full, MigrationTransaction completes (state_history shows planned→saving→restoring→verified→source_erased→committed within budget), old session's NEXT request lands on the assigned quarter (sticky affinity preserved), and aggregate t/s under continuous fan-out approaches the matrix's 4-quarters baseline once all requests are placed on disjoint cpusets. | frontdoor (Qwen3.6-35B-A3B Q8 ×5) | ~2h |
| J3 | WP-4 reverse-migration verification | [within-role-placement-state-machine.md](within-role-placement-state-machine.md) § Phase 4 | Enable `ORCHESTRATOR_REVERSE_MIGRATION=1`, run a 30-min mixed traffic profile (alternating bursts of 4 concurrent and solo turns) on frontdoor. Verify reverse-migration log/stat evidence increments, per-session migration counts respect the cap (default 5), and solo-after-burst per-request latency regresses ≤+10% vs solo-only baseline. The Prometheus counter named in the original Phase 4 plan is not wired as of this audit; do not block on it unless a metrics patch lands first. | frontdoor (Qwen3.6-35B-A3B Q8 ×5) | ~30-min profile + analysis |
| J6 | WP-7 production rollout + 24h gate | [within-role-placement-state-machine.md](within-role-placement-state-machine.md) § Phase 7 | **CLOSED/SUPERSEDED 2026-06-19.** Continuous AutoPilot satisfied the soak, and `_eval_concurrency()` now uses a matrix-aware default (`2eb4437`): topology safe-N is only used when the same-role contention matrix is certified fresh and allows background/eval fan-out; env override remains the documented operator escape hatch. | full production stack | closed |
| J7 | DCP-6 delegation context pre-assembly eval | [delegation-context-preassembly.md](delegation-context-preassembly.md) DCP-6 | DCP-4 advisory attach is wired/default-off (`features().dcp_pre_assembly`) and validated by `tests/unit/test_dcp4_wiring.py`. 2026-06-12 offline replay passed scratch-root/file-selection/budget correctness over 5 historical BEP tasks, then DCP-6a branch `fix/dcp6a-context-depth-current` (`530128b7`) fixed shallow slices + missing hashes and replayed clean: 100% file coverage, 100% line coverage, 0 missing hashes at budgets 500/1000/2000. Code landed on the live branch at `2e2e0d3`; 2026-06-19 launch-code provenance check found current `server_launch_git_sha=eeb8cce` already contains `2e2e0d3` and `756c96b`. Orchestrator `29b9ba3` adds `scripts/benchmark/dcp_j7_ab.py`, which validates its artifact schema in `--stub`, refuses real inference without `--host-quiet-confirmed`, refuses while AutoPilot is running, and records per-prompt latency/token/delegation telemetry in off/on arms. Next is a clean running-state attestation after clearing deleted llama-server binary paths, flag intent diffs, and missing API-parent tool-sentinel env, then inference gate measuring prefill tokens, latency, top-ups, bundle-build latency, quality, hallucinated-file references, and context-contamination failures vs reactive-discovery baseline. Default-off flag stays off until results justify. | frontdoor + worker_coder (delegation-heavy roles) | ~3-4h after clean DCP-6a running-state attestation |
| J8 | BEP-2 batched edit CPU-latency A/B | [batched-edit-parallel-apply.md](batched-edit-parallel-apply.md) BEP-2 | **Optional decision experiment for the legacy batch-edit path.** The production-relevant remediation is the shipped edit transaction, which bypasses both the interleaved Root LM loop and the old patchset proposal. Run J8 if the answer would change whether `ORCHESTRATOR_BATCH_EDIT_MODE` is kept, retired, or exposed as a narrow task-class knob, especially for large-repo patch economy or structured-patch provenance. Do not run it merely to validate the already-built edit-transaction remediation. | worker_coder + frontdoor | ~3h |
| J9 | HLE-4 harness metrics observe-only run | [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) HLE-4 + [meta-harness-optimization.md](meta-harness-optimization.md) HLE-1/2/3 | **CLOSED 2026-06-12** from existing trial journal snapshot. `EvalResult` + journal JSONL carry `harness_metrics`, `oracle_adequacy`, `metric_schema_version` and retain concurrency telemetry fields. `execution_fidelity` and `planning_stability` separate keep/revert but are not independent enough to promote; `feedback_interpretation`, `memory_coherence`, and `recovery_rate` fail signal/missingness gates. No Pareto co-objective promotion before N2 ledger/sequential verdict redesign. | full autopilot stack | closed |

### Sequencing notes

- **Preflight → J1 → J2 → J3 → J4a/J4b/J5 → J4** is the new parallelization block. J1-J3 prove dispatcher safety; J4a/J4b close cross-role N-way contention; J5 closes within-role instance-pair contention; J4 observes policy choices on the now-characterized stack.
- **J4b and J5 matrix benches** must run ALONE on the host and honor `feedback_no_concurrent_inference`. They are the highest stack-conflict risk in this Package and are required before using cross-role concurrency to speed up the remaining inference backlog.
- **Affinity repair outranks matrix reuse**: if live affinity differs from `NUMA_CONFIG`, the matrix is stale even when `topology_hash` matches. Reload/fix the affected role first, then rerun all matrix evidence involving that role/shape before J4/J6 or downstream parallel bulk work.
- **Optional frontdoor Half1 exploration is out-of-band**: do not add or assume a second half frontdoor inside the repair path. If pursued, create a separate topology experiment after current matrix repair: add Half1 port/config, validate affinity, measure Half0+Half1 and Half0/Half1+quarters against current q0-q3 policy, update `topology_hash` and rederive the matrix before use.
- **J6 (production rollout)** is 24-hour passive once flipped; can start as soon as J4a/J4b/J5 are done and any J4c policy wiring needed for bulk scheduling is in place.
- **J7 and J9** are independent of the WP implementation work but should run after J1-J3 so they inherit safe fan-out. J7 is an autopilot-style eval against the production stack; its DCP-4 hook is already built, and DCP-6a code is landed but must be server-reloaded/attested at a clean deploy boundary before inference. J9 is closed diagnostic-only as of 2026-06-12. **J8 is optional** because edit-transaction mode solved the practical BEP-2 blocker; keep it out of the critical run order unless its result would change the legacy batch-edit path's keep/retire/task-scope decision.

### Execution manifest template

Before launching the nonstop bulk train, create a run manifest with one row per task/gate. A JSONL file is preferred for machine checking; this table defines the required fields.

| Field | Required | Notes |
|-------|----------|-------|
| `run_id` | yes | Stable id shared by logs, artifacts, and progress notes. |
| `task_id` | yes | Package task id such as `J1`, `J4b`, `H7`, `I1`. |
| `allowed_concurrency_mode` | yes | `serial`, `same_trial_eval_fanout`, `cross_role_matrix_allow`, `observe_only`, or `isolated_bench`. |
| `required_topology_hash` | yes for concurrent/bench tasks | Must match runtime before launch. |
| `live_affinity_verified` | yes for concurrent/bench tasks | Boolean. True only after every live llama-server PID in scope has thread affinity exactly matching `NUMA_CONFIG` for its role/index. |
| `affinity_artifact` | yes for concurrent/bench tasks | Path to captured port->pid->expected-cpus->observed-cpus evidence. |
| `matrix_status` | yes | `not_required`, `preclosure`, `closed_world`, `stale`, or `diagnostic_only`. |
| `flags` | yes | Feature flags and env vars used for the task. |
| `command` | yes | Exact command or script invocation. |
| `output_path` | yes | Primary artifact directory/file. |
| `journal_quarantine_rule` | yes | When results must be kept out of baselines/Pareto/scheduling priors. |
| `pass_fail_gate` | yes | Concrete metric threshold or artifact condition. |
| `next_action` | yes | Continue, rerun, serialize downstream, stop, or open follow-up. |

Minimum manifest example:

```json
{"run_id":"bulk-2026-05-26-j4b","task_id":"J4b","allowed_concurrency_mode":"isolated_bench","required_topology_hash":"<hash>","live_affinity_verified":true,"affinity_artifact":"data/contention_matrix/<run_id>/live_affinity.json","matrix_status":"preclosure","flags":{"feedback_no_concurrent_inference":true},"command":"python scripts/server/contention_matrix.py ...","output_path":"data/contention_matrix/<run_id>/","journal_quarantine_rule":"diagnostic_only_until_closed_world","pass_fail_gate":"all candidate_sets measured or excluded; CV <= 0.05; live affinity exact-match","next_action":"J5 if pass; stop if topology drift, affinity drift, or unmeasured bucket remains"}
```

### Baseline mutation rule

Baseline mutation is opt-in, never implicit. A run is baseline-eligible only if:

- `speed_metric_mode` is present and matches the evaluation shape.
- `topology_hash` matches the manifest and matrix artifact.
- `live_affinity_verified=true` for any run that depends on the contention matrix.
- `matrix_status` is `closed_world` for cross-role parallel runs, or `not_required` for serial/same-trial-only runs.
- Same-trial EvalTower fan-out records `eval_concurrency`, median per-request t/s, aggregate batch t/s, and eval wall time.
- Cross-role concurrent runs record the exact active-set verdict id and launch only `allow` sets.

Everything else is diagnostic-only. Diagnostic-only data can be summarized in progress reports, but it must not update production baselines, Pareto archives, regression thresholds, learned scheduling priors, routing speed priors, or future trial scheduling evidence.

### Resume protocol

If the long-running session is interrupted:

1. Read the latest `progress/YYYY-MM/*.md` entry and the run manifest.
2. Verify the current orchestrator git sha, stack state, and topology hash before relaunching anything.
3. Inspect the last produced artifact, not just the final log line or process exit status.
4. Rerun only idempotent preflight steps automatically: py_compile, unit subset, health checks, topology hash capture, and J4a dry-run enumeration.
5. Continue from the first incomplete gate in the manifest.
6. Keep partially completed throughput benches quarantined unless every sample, CV, ratio, verdict, topology hash, and artifact path is present.
7. If topology hash, live affinity, or matrix status changed, stop cross-role parallelism and return to J4a/J4b before downstream bulk work.

### Other agents' inference-gated work — add here

This Package is designed to absorb additional inference-gated items from parallel agents so one operator-sitting window clears multiple. Append rows below (or open a Package K for a separate window). Suggested format: same table columns; surface dependencies in this sequencing section if any.

| # | Task | Source Handoff | Description | Models Needed | Effort |
|---|------|---------------|-------------|--------------|--------|
| J10 | URE-1 routing-uncertainty calibration | [decision-aware-routing.md](decision-aware-routing.md) URE-1 | Enable `ORCHESTRATOR_URE_UNCERTAINTY_SHADOW_LOG=1`; passively collect shadow routing-uncertainty records over normal traffic; compute ECE/AUC for "would escalation help?", abstention precision/recall, per-suite calibration drift. Pre-enforcement gate: ECE ≤ eval-tower P8 target + abstention precision > baseline escalation precision + ≤10% latency regression. **Shadow-only** — needs no dedicated window. Prereq: URE-1 shadow logger wired (approval_record schema done in `src/trace/harness_schema.py`). | none extra (shadow on existing frontdoor/escalation traffic) | passive collection + ~1h analysis |
| J11 | BSV-2 behavior-signature differential testing | [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) BSV-2 | Before promoting a mutation, run new-vs-old paired on the same sentinels (sequential under identical model snapshot preferred; parallel only if explicitly approved per `feedback_no_concurrent_inference`); compare behavior_signature diff severity (benign/watch/blocking) + scalar score; gate accept on both. Catches silent Pareto-win regressions a scalar misses. Prereq: BSV-1 partial archive-member observe wiring is now on main (`9a175eac`, default-off, `trial:<id>` archive IDs + compact signature index), now prefers per-question `question_results` sentinel outcomes before falling back to per-suite proxies (`31e7e008`), has a read-only same-question BSV paired report scaffold (`0943e7c0`), and can feed standalone paired-run EvalResult-like JSON artifacts into the same report via `eval-result-pair` (`5b29eead`). Remaining prerequisite is the paired inference runner plus full-enough trace/answer/tool evidence before accept-loop enforcement. | autopilot eval stack | paired eval per candidate mutation |
| J12 | chat_template_kwargs empirical probe + THINK-ABL-1 | epyc-orchestrator `cac4148` (chat_template_kwargs passthrough merge), later registry/production-backend wiring tests, and [x-mas-text-routing.md](x-mas-text-routing.md) | **Non-inference wiring is CLOSED 2026-06-12**: registry-driven `chat_template_kwargs` auto-populates per-role defaults, production `LlamaServerBackend` forwards them on `/v1/chat/completions`, and chat-completions role selection shares one source of truth. Focused verification: `uv run pytest tests/unit/test_registry_chat_template_kwargs.py tests/unit/test_llama_server.py::TestLlamaServerBackend::test_chat_completions_stream_forwards_registry_chat_template_kwargs tests/unit/test_chat_completions_roles.py -q` -> 6 passed. 2026-06-27 live-load 15-task frontdoor+architect probe produced `/mnt/raid0/llm/tmp/j12_architect_think_loop_probe_20260627T090826Z_summary.json`: no `<think>` leaks or known loops, no immediate architect revert, but 2 architect HTTP 504s under concurrent load. 2026-06-28 orchestrator `16876006` packaged `scripts/benchmark/j12_think_loop_probe.py`, including stack-prior port discovery, `enable_thinking=false`, JSONL/summary output, leak/loop classifiers, dry-run support, and a fail-closed active-AutoPilot guard. Remaining empirical work: repeat/close the cheap-kill probe in the declared quiesce window with `uv run python scripts/benchmark/j12_think_loop_probe.py --roles frontdoor architect_general --confirm-clean-window`, then run THINK-ABL-1 with a non-no-op suppressor for ingest (`/no_think` or empty-`<think></think>`) at fixed non-truncating `max_tokens`, same tasks both arms. Gate: frontdoor +30pp or better, architect +15pp or better; ingest result decides only the THINK-ABL-1 policy. | frontdoor + architect_general + ingest_long_context | ~2h probe + ~1h ablation |
| J13 | P17.BT-3 axis-vote BT tiebreak falsification | [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) § P17 BT-3 (epyc-orchestrator commits `2e51c86` + `60ed552` + `45df95c` + `56ee9fc` range-normalization fix; prompt cleanup `b8c0611`) | **CLOSED 2026-06-12** from existing journal data; **cleanup landed 2026-06-13**. Sample size passed (341 rich/stagnation-fired trials, 75 logged disagreements), but the exact seed-outcome gate is not measurable because journal/log artifacts do not persist BT top ID, hypervolume-top ID, or planner-followed seed. Proxy outcomes do not clear the positive-signal threshold. Do not queue P17.BT-4; the cosmetic rich-prompt `bt_tiebreak_hint` has been removed. | autopilot eval stack (no new models) | closed |
| J14 | DAR-6.5 swarm-fanout adversarial-robustness A/B | [decision-aware-routing.md](decision-aware-routing.md) § DAR-6.5 | 2-arm A/B on a chosen injection suite (Garak / HouYi / PromptInject — pick one with active maintenance + Apache/MIT licence). Arm A: existing single-model escalation. Arm B: N≥2 heterogeneous concurrent serves via `dispatch_swarm_fanout` in `src/swarm_fanout.py`, aggregated via the shared BT module (`src/bradley_terry.py`). Replicates intake-615's published 0.12% vs 6.20% prompt-injection-degradation claim on our own suite. Pre-enforcement gate: ≥3pp absolute reduction in injection-success rate AND ≤30% per-stream throughput regression at the swarm-fanout setting. **Prereq status (2026-05-28)**: (1) P26.1 BT module ✅ (`src/bradley_terry.py`); (2) DAR-6.1 feature flag ✅ (`features().swarm_fanout`, default-off), DAR-6.3 dispatch ✅ (`dispatch_swarm_fanout`), DAR-6.4 BT-aggregator ✅ (`bradley_terry_aggregate`) — all in epyc-orchestrator commit pending; (3) injection-risk classifier is now explicitly tracked as [routing-intelligence.md](routing-intelligence.md) RI-13, but should **not** be built before the cheap-first unconditional J14 A/B clears its gate. | 2-3 heterogeneous concurrent serves (e.g., gemma4-26B-A4B + qwen3.6-35B + qwen3-coder, depending on injection-suite topic) + injection eval harness + a pairwise judge model OR the included `length_proxy_aggregator` baseline (the latter is documented as a deliberate weak baseline — see `src/swarm_fanout.py:length_proxy_aggregator`) | 1-2 days A/B harness assembly + one eval run (DAR-6.1/6.3/6.4 are no longer in this estimate — already ✅) |
| J15 | MD-9 deep_research_mode sentinel A/B | [minddr-deep-research-mode.md](minddr-deep-research-mode.md) MD-9 | Phase 1 MindDR readiness gate. Sentinel suite at `orchestration/deep_research_sentinel.yaml` (20 curated queries: 7 BrowseComp + 7 WideSearch + 6 mixed); each query is pre-tagged `is_research_like=True`. Run the suite with `ORCHESTRATOR_DEEP_RESEARCH_MODE=0` (control) then `=1` (treatment), score on the four NaN-safe rubric fields already wired into `EvalResult` (`rubric_reasoning_trajectory`, `rubric_tool_calls`, `rubric_outline`, `rubric_content_stage`). Promote to production default iff uplift ≥+5pp on the aggregate rubric AND no regression on the existing eval-tower sentinels. **All prereqs already landed 2026-04-22** (MD-1 flag, MD-2 classifier, MD-3/4/5 prompts, MD-6 pydantic_graph subpackage, MD-7 EvalResult rubric stubs, MD-8 sentinel suite). The LLM-as-judge scoring functions themselves are tracked separately as EV-9 in [`eval-tower-verification.md`](eval-tower-verification.md) (also inference-gated; if EV-9 hasn't landed at J15 run-time, fall back to structural-only scoring against the `expected_contains` hints baked into the sentinel YAML). | frontdoor + worker_coder + web-research backend (per the three-agent pydantic_graph pipeline) | ~1 day inference + ~2h analysis |
| J16 | RI-ITG-1 ingest-triviality guard A/B | epyc-orchestrator `9203c00` (flag `INGEST_TRIVIALITY_GUARD`, default OFF, depends on `specialist_routing`) + [x-mas-text-routing.md](x-mas-text-routing.md) § "Follow-up validation" | The learned MemRL router leaks ~8.5% of ingest_long_context traffic as trivial short prompts (153/1803 math in the 2026-05-30 tap analysis) — a ~19× latency tax (80B @ ~6.4 t/s) for work a cheap role answers identically. `apply_ingest_triviality_guard` demotes ingest→`worker_general` ONLY for positively-trivial requests (difficulty band ≠ medium/hard AND short AND no long-context). 2-arm enforce A/B vs flag-off baseline on the eval-concurrency fan-out; also enable `difficulty_signal` shadow/enforce so the easy-band path is live. **Gate**: ingest short-prompt leakage materially reduced AND **zero accuracy regression** vs baseline; long-context + short-but-hard reasoning routes unchanged. Then consider default-on. | frontdoor + ingest_long_context + worker_general (existing stack; no new models) | ~1-2h enforce A/B + ~1h analysis |
| J17 | Internal-interaction-lifecycle P2 consult A/B (`review_before_commit` at the edit-transaction seam) | [internal-interaction-lifecycle.md](internal-interaction-lifecycle.md) P2 + P2-0 design note (2026-05-31) | 2-arm A/B at `epyc-orchestrator/src/edit_transaction.py:199` `run_edit_transaction()`, between the one-shot draft `llm_call()` at `:209` and `apply_edit_transaction()` at `:211` (chosen attach point per P2-0). Arm A = baseline (`features().consult_skills_enabled.review_before_commit=false`); Arm B = `=true` with `consult(consultant_role="architect_general", requester_role="coder_escalation", skill="review_before_commit", ...)` between draft and apply, integrating advisory with one re-run cap when `blocking_issues` non-empty AND `confidence ≥ 0.6`. ≥50 code-edit turns on a fixed eval slice. **Gate to P3**: tokens saved ≥30% on advisory leg; code-edit eval ≤1pp quality drop; `coder_escalation` decode p50 within ±5%; advice cache hit ≥10% on repeated identical-shape edits within 1h; all six handoff invariants (I1–I6) hold under P2 traffic. **Prereqs (HARD, SEQUENTIAL — do NOT trigger before both clear)**: (1) Cross-Role Contention + Placement TRACKING section's autopilot/contention bake clean (this handoff's tail); (2) P1 lifecycle refactor landed + regression gate passed (pytest suite green, `delegation_diagnostics` byte-equal on identical inputs, no wire change to `delegation_events`, no affinity drift, ≥48h autopilot bake). | `coder_escalation` (Qwen3.6-35B-A3B Q8 @ :8071, shared mmap with frontdoor) + `architect_general` (Qwen3.5-122B Q8) + code-edit eval slice harness | ~1d eval slice + ~2h A/B analysis |

**Sequencing of the appended items (intake-607 residual gates + 2026-05-27 P17/DAR-6 additions):**
- **J16 (RI-ITG-1)** is an **active routing change** (enforce-mode demotion), so it **cannot co-run with the passive J6 24h soak** (would contaminate the baseline) — run it as a dedicated cheap eval in a host-quiet window after the matrix gates, like J11/K-EVAL-1. *Partial-fold option*: a shadow/observe mode (log would-demote without demoting) would be observe/advisory and could ride J6 to passively quantify leakage; that mode is **not yet built**, and the accuracy A/B needs enforce mode regardless. THINK-ABL-1 (real thinking ablation for ingest) is **not** a J16 item — it folds into **J12** (same chat_template_kwargs subsystem); see the corrected J12 row above.
- **J10 (URE-1) is shadow-only** — flip the flag and let it accumulate during ANY of J1–J9 or Package I traffic; it shapes no workload and needs no dedicated slot. Analyze once enough decisions accrue.
- **J11 (BSV-2)** runs per-mutation inside the autopilot accept loop; co-runs naturally with J9's autopilot observation window.
- **J13 (P17.BT-3) is CLOSED 2026-06-12** — offline analysis reached a negative/non-certifying verdict; do not queue P17.BT-4. The rich-prompt hint removal landed at `b8c0611` on 2026-06-13 while AutoPilot was paused.
- **J14 (DAR-6.5)** had a real prereq backlog until 2026-05-27 when DAR-6.1/6.3/6.4 scaffolding landed. Remaining prereq is the conditional-routing trigger (DAR-6.2 injection-risk classifier in [`routing-intelligence.md`](routing-intelligence.md)); cheap-first variant runs unconditional A/B without it, decoupling J14 from the classifier work.
- **J15 (MD-9)** has zero outstanding prereqs as of 2026-04-22 (all of MD-1..MD-8 done). Sentinel YAML + EvalResult rubric fields + pydantic_graph subpackage all present. Can run any time inference window opens; results compare to existing sentinel baselines.
- J10/J11 are gated on their wiring landing (URE-1 shadow logger; BSV-1 partial archive-member observe wiring now on main via `9a175eac`, per-question sentinel preference via `31e7e008`, read-only paired report scaffold via `0943e7c0`, and standalone EvalResult artifact input via `5b29eead`; BSV-2 paired inference runner / accept-loop flag integration still open). J13's P17.BT-2 hint wiring was removed from the live planner prompt after P17.BT-3 closed negative/non-certifying on 2026-06-12; the shared BT algorithm remains available. Schemas + pure algorithms on `15350fe` and orchestrator `2e51c86`+`60ed552`+`45df95c`; prompt cleanup at `b8c0611`. DCP-6/BEP-2/HLE-4 are already covered above as J7/J8/J9 — no duplication.
- **J17 (internal-interaction-lifecycle P2)** has TWO hard sequential prereqs and must NOT be triggered before both clear: (a) the Cross-Role Contention + Placement bake (tracked at the tail of this handoff) — autopilot/contention rollout has to complete so the bake measurement establishes a clean baseline that the P2 invariant checks (I1 region-lock visibility, I6 one-shot only) can compare against; (b) the P1 lifecycle refactor regression gate (zero-behavior-change refactor of `_architect_delegated_answer`, must show byte-equal `delegation_diagnostics` on identical inputs and ≥48h autopilot bake with no `delegation_cache_hits` miss-rate rise). Counter emission for that bake is now live via orchestrator `02a01617` (deployed `2026-07-03T15:40:30Z`): delegated completions persist cache lookup/hit/miss/rate counters and `ContentionDenied` 503s emit `kind="contention_denied"` progress events. Then-and-only-then is the J17 A/B safe to run after the ≥48h counter window is clean. Triggering owner: whichever inference-window operator next has a quiet code-edit eval slice after both prereqs clear — see the Internal Interaction Lifecycle TRACKING section at the tail of this handoff for the live status of (a) and (b).

### Per-gate conditional workflows + mitigation policies (intake-607 gates J7–J11 — READ BEFORE RUNNING)

Each gate is a **decision point**, not just a measurement: run → branch on the result → apply the mitigation. Deep specs are in the owning handoffs (linked); this is the operator decision tree so the run can proceed in one sitting without round-trips.

**Pre-run wiring status** (none is in production until wired AND its gate passes; all flags default-OFF):
- **J10 / URE-1**: shadow logger **WIRED** (`ORCHESTRATOR_URE_UNCERTAINTY_SHADOW_LOG`) on main (merged 2026-05-26) — runnable now.
- **J7 / DCP-6**: **DCP-1 + DCP-2 discovery + DCP-3 ast-codemap DONE** on main (merged 2026-05-26) and **DCP-4 advisory attach DONE** in the live specialist delegation path (`chat_delegation._maybe_dcp_seed_context`, flag `dcp_pre_assembly`, default-off; validated by `tests/unit/test_dcp4_wiring.py`). 2026-06-12 offline replay closed task-root/file-selection/budget validation; DCP-6a branch `530128b7` then fixed content-depth/freshness and replayed clean on the current live lineage; equivalent code landed at `2e2e0d3`. 2026-06-19 launch-code provenance check is satisfied (`server_launch_git_sha=eeb8cce`, current API `git_sha=27e09a1`), but operational attestation remains caveated. `29b9ba3` adds the real A/B runner. Remaining work is clean running-state attestation, then inference A/B.
- **J8 / BEP-2**: optional legacy path. `_execute_turn` batch divergence + sandboxed patchset path are wired behind `ORCHESTRATOR_BATCH_EDIT_MODE`, but the active remediation path is already the `force_mode="edit"` transaction, not this batch-vs-interleaved A/B.
- **J9 / HLE-4**: `EvalResult`/journal extension is DONE (`931e43c`), rule-based HLE-1 metric computation + HLE-2 oracle-adequacy registration are DONE (`9222a19`), and the 2026-06-12 metric-validity analysis is DONE. Shared trace schema is done. Current verdict: dashboard/advisory only; no Pareto promotion from the current proxies.
- **J11 / BSV-2**: BSV-1 partial archive-member observe wiring is on main (`9a175eac`, default-off), now prefers per-question `question_results` sentinel outcomes before falling back to suite proxies (`31e7e008`), has a read-only paired behavior report over same-qid journal vectors (`0943e7c0`), and can compare standalone paired-run EvalResult-like JSON artifacts through `eval-result-pair` (`5b29eead`). It still needs the paired inference runner and full-enough trace/answer/tool evidence before it can gate accepts. Compute (`compute_behavior_signature`, `diff_signatures`) done.

**J8 — BEP-2 batched-edit A/B (optional decision experiment; NOT on the critical remediation path):**
- **What it decides**: whether the legacy structured patchset/batch-edit mode is worth keeping as a task-class knob, retiring, or preserving only for provenance/large-repo patch-economy cases.
- **What it does not decide**: whether Qwen3.6 can complete multi-file coding tasks, and whether the edit-transaction remediation works. Those were already answered by the direct one-shot ablation and the edit-mode unit/module/server validations.
- **Run J8 if** the answer would change `batch_edit_mode` ownership: keep/retire decision, large-repo/full-file-cost concern, need for structured-patch provenance, or evidence for BEP-3 task-class routing.
- **Defer J8 if** the immediate goal is routine coding completion reliability, because `force_mode="edit"` is the higher-leverage shipped path and J7/J11/J15 are more directly actionable in scarce inference windows. J9 and J13 analyses are already closed.
- ✅ batch cuts end-to-end latency ≥15% AND quality within −1pp AND parse-failure ≤5% AND apply-failure ≤2% (whole-repo verify) → keep the legacy batch flag available for narrow task-class experiments; do **not** displace edit-transaction mode without a separate rollout decision.
- ⚠️ latency win but quality −1..−3pp OR parse/apply failures 5–15% → do NOT promote; keep the legacy flag off and treat the result as parser/prompt hardening evidence only.
- ❌ no latency win OR quality < −3pp OR failures >15% → retire the legacy batch-vs-interleaved path; record NEGATIVE in the handoff + intake-605. This does **not** invalidate the shipped edit-transaction remediation.
- **Mitigation**: flag-off = instant rollback; **every apply is in a sandbox/worktree (BEP-5), never production files, until whole-repo verify passes AND accept**; stale-base rejection; parse=None/invalid → fall back to the normal REPL loop (zero behavior change).

**J7 — DCP-6 delegation pre-assembly eval (run advisory-first: bundle attached, reactive discovery still on):**
- Prereq before inference: clean running-state attestation with launch marker containing `2e2e0d3` or later; the isolated replay already showed full-small-file/padded ranges, per-file `content_sha256`, 100% line coverage, and 0 missing hashes. The 2026-06-19 attestation satisfied launch-code provenance but did not satisfy the clean-running-state gate.
- ✅ prefill+latency down AND quality ≥ baseline AND top-up rate ≤20% → keep advisory; consider seed-bundle-primary mode after a second confirm.
- ⚠️ quality flat but top-up rate >20% → packer under-selecting; tune discovery depth / ColGREP top-k / budget; re-run.
- ❌ quality drop OR no latency improvement → keep reactive discovery; shelve pre-assembly; flag off.
- **Mitigation**: flag-off; advisory mode never removes reactive discovery; top-ups always allowed (no hard firewall); bundle freshness (repo_sha/content_sha256) re-checked per delegation.

**J9 — HLE-4 harness-metrics observe-only (no Pareto promotion during the run):**
- **2026-06-12 result**: the observation window already happened. 580 metric-bearing trials showed `execution_fidelity` cleanly separates keep/revert (`r=0.52`, keep mean `0.851` vs revert `0.731`) but strongly mirrors quality/reliability (`r=0.83`/`0.89`). `planning_stability` separates keep/revert even more (`r=0.84`, keep mean `0.988` vs revert `0.623`) but is derived from the same safety verdicts, so it is useful as a sanity dashboard/advisory signal, not an independent objective. `feedback_interpretation` is low-confidence/low-variance; `memory_coherence` is constant; `recovery_rate` is missing on 99.3% of rows.
- Decision: keep all current HLE metrics diagnostic/advisory only. Do **not** promote any J9 metric to Pareto selection or hard guardrail until N2 per-question ledgers/sequential verdicts land and a redesigned metric demonstrates independent predictive signal.
- **Mitigation**: observe-only first; low-signal/low-confidence metrics never gate; oracle-adequacy flags shortcut-prone suites so they can't drive promotion.

**J10 — URE-1 calibration (shadow → enforce; J10 itself only collects + analyzes):**
- ✅ ECE ≤ eval-tower P8 target AND abstention precision > baseline escalation precision AND ≤10% shadow latency regression → enable uncertainty-routed escalation (separate enforce flag) + optionally URE-3 (uncertainty as a frozen-label routing feature).
- ❌ any gate fails → stay shadow-only; recalibrate (re-weight components / threshold) on a frozen shadow set; do NOT enforce.
- **Mitigation**: calibration-precedes-enforcement; shadow→enforce is a separate flag flip; frozen shadow-calibration set; re-run calibration after any DAR-3/DAR-4 change to avoid a feedback loop.

**J11 — BSV-2 differential testing (mutation accept gate; per candidate mutation):**
- `benign` → auto-accept; `watch` (route/tool changed, outcomes equal) → accept + log; `blocking` (prior-pass sentinel regressed, forbidden shortcut appeared, or cost guardrail crossed) → **REJECT, do not promote**; if it touches a shared subsystem → BSV-3 conflict-ledger review.
- **Mitigation**: gate accept on BOTH scalar regression AND signature severity; partial-confidence signatures cannot certify `benign`; git-committed revert remains the backstop.

**J13 — P17.BT-3 axis-vote BT tiebreak falsification (offline post-run analysis):**
- **2026-06-12 result**: sample requirement passed (341 rich/stagnation-fired trials, 75 logged disagreement events), but the exact BT-picked-seed vs hypervolume-top-seed comparison is not measurable from current artifacts. The journal stores only `"BT-tiebreak disagrees with hypervolume top"`; logs/planner archive do not retain the `BT picks trial #... (rank-by-hv would pick #...)` line or whether the planner followed either seed.
- Proxy outcomes are not enough to keep investing: current-trial frontier rate was 2/75 (2.7%) for BT-disagreement events vs 9/266 (3.4%) for rich no-disagreement events; cluster-start next-10 frontier rate was 1/7 (14.3%) vs 8/34 (23.5%) for thinned no-disagreement rich prompts. Overlapping raw windows showed 23/75 next-10 frontier hits, but those are dominated by long repeated disagreement clusters and cannot certify the seed-level gate.
- Decision: treat P17.BT-3 as negative/non-certifying. The `bt_tiebreak_hint` block was removed from the rich-prompt template at `b8c0611`; do **not** queue P17.BT-4 unless a future explicitly-instrumented run persists BT top ID, hypervolume-top ID, chosen seed/action lineage, and then shows positive signal.
- **Mitigation completed**: the live planner prompt no longer carries the cosmetic hint. Failure mode is closed for future restarts; the shared BT helper remains for offline diagnostics and non-AutoPilot consumers.

**J14 — DAR-6.5 swarm-fanout adversarial-robustness A/B (publishability falsification):**
- ✅ ≥3pp absolute reduction in injection-success rate AND ≤30% per-stream throughput regression at the chosen N=2 or N=3 swarm-fanout setting → enable the routing mode (separate enforce flag); also queue work on the conditional injection-risk classifier in [routing-intelligence.md](routing-intelligence.md) so swarm-fanout is reserved for high-risk prompts rather than always-on.
- ⚠️ Reduction in injection-success rate present but <3pp OR throughput regression 30–50% → keep DAR-6 code path but stay shadow-only; revisit if (a) lighter peer models (8B specialists) emerge from swarm-dataset-distillation or (b) hardware changes.
- ❌ No measurable reduction OR throughput regression >50% → **kill DAR-6 swarm-fanout mode**; document the kill in DAR § DAR-6 with the exact A/B numbers; the BT module remains available for the autopilot P17 and distillation P3 consumers.
- **Mitigation**: cheap-first variant runs the A/B unconditionally on a fixed injection-prompt set BEFORE building the conditional-routing trigger; this isolates "does swarm-fanout reduce injection success at all?" from "is our routing classifier good enough to gate it?"

**J15 — MD-9 deep_research_mode sentinel A/B (Phase 1 promotion gate):**
- ✅ Aggregate rubric uplift ≥+5pp on `deep_research_sentinel.yaml` AND no regression on existing eval-tower sentinels → set `deep_research_mode` production-default ON for queries matching `is_research_like()`; queue MD-7 LLM-as-judge wiring (EV-9 in [`eval-tower-verification.md`](eval-tower-verification.md)) if it wasn't already landed.
- ⚠️ Uplift 0–5pp OR regression on a sub-rubric (e.g., `tool_calls` worse but `outline` better) → keep `deep_research_mode` flag available but stay default-off; the rubric breakdown is the trigger for MD-3/4/5 prompt iteration before re-running.
- ❌ Uplift ≤0pp OR meaningful regression on existing sentinels → leave flag default-off; record the kill in [`minddr-deep-research-mode.md`](minddr-deep-research-mode.md) with rubric-level numbers; Phase 2 (RL) becomes unmotivated.
- **Mitigation**: flag-off is the default state; routing classifier `is_research_like()` shadow-logs without altering routing today (per MD-2); the pydantic_graph subpackage at `src/graph/minddr/` is decoupled from production `src/graph/` so a kill is just "stop calling the new entry point" — no rollback of routing infra needed.

---

## Package K: Audit-Batch Code-Ready Inference Gates (2026-05-27)

**Origin**: the 2026-05-27 `/research-intake` of agent-oss (intake-610–613) prompted an audit of `research-evaluation-index.md` + `pipeline-integration-index.md` for work that is *not* inference-gated. All code scaffolding was implemented that session (see `progress/2026-05/2026-05-27.md` + `research/deep-dives/2026-05-27-agent-memory-cluster.md`). The RUNS below are now unblocked — code has landed, models/datasets are downloaded or have a one-line fetch noted. **Independent of Package J** — pick up in any stack window; none block J.

**Stack required**: varies per row (most need only individual model servers, not the full orchestrator).

| Task | Code prereq (DONE this session) | Inference run / gate |
|------|----------------------------------|----------------------|
| **K-RAG-1** — KB-RAG hybrid-signal eval (K7 + K9/K10) | `kb_rag.query()` recency+rerank params (`src/retrieval/kb_rag.py`); `src/retrieval/cross_encoder.py`; cross-encoder ONNX on disk at `/mnt/raid0/llm/models/ms-marco-minilm-l6-v2-onnx`; 21 unit tests pass. 2026-06-12 diagnostic used `/mnt/raid0/llm/pace-env` because orchestrator `.venv` is missing `onnxruntime`; stale index had 137 files / 4,634 chunks, max mtime 2026-05-30. | Formal K7 is not yet runnable/decision-grade: add/locate the HotpotQA/LoCoMo-style query set + harness, restore `onnxruntime` in orchestrator `.venv` or bless `pace-env`, refresh the KB index, then sweep `KB_RAG_RECENCY_WEIGHT` / `KB_RAG_RECENCY_SIGMA_DAYS` / `KB_RAG_RERANK=1` / `KB_RAG_RERANK_WEIGHT`. Gate: any config beats the MaxSim-only baseline on doc-recall@{3,5,10} by >2pp (Flywheel ~1pp noise floor). Do not promote default weights from the tiny diagnostic. |
| **K-EMB-1** (P9) | A-fast fallback corpus + dry-run harness are verified (`100` docs, `30` queries, no missing refs); HF sources and conversion env are staged; warm/default-off embedder server recipes for Granite, multilingual-e5-base, and BGE-M3 landed in orchestrator `e2922d7` — see `granite-97m-r2-bench-plan.md` | Next prep is GGUF conversion/quantization, then Phase B: throughput + nDCG@10/recall@10/50 + 32K probe + end-to-end-with-reranker. Gate: dense first-stage retriever decision (granite vs BGE-M3 vs defer). |
| ~~**K-EVAL-1**~~ → **FOLDED INTO H5 (2026-06-12)** | EV-3 `scoring_verifiers` adapter DONE (`scripts/benchmark/scoring_verifiers_adapter.py`, registered in `dataset_adapters.py`+`suites.py`); 2026-06-19 validation confirms the local snapshot loads 6,701 candidate-level verifier items with 3,395 correct / 3,306 incorrect labels after research `7c11920`. | **Single owner: H5 / [eval-tower-verification.md](eval-tower-verification.md) EV-4.** This row was a duplicate of H5's ECE/AUC calibration baseline on Scoring-Verifiers — do NOT schedule it separately (struck to avoid double-scheduling). Runs in Queue 3 after the per-question ledger lands. |
| ✅ **K-MEM-1** (P3b) | `tulving_episodic` suite adapter + deterministic F1 scorer landed (`scripts/benchmark/tulving_episodic_adapter.py`); 77 unit tests. 2026-06-18 prep: Figshare data extracted at `/mnt/raid0/llm/data/eval/tulving_episodic/`, adapter selection hardened to the documented Claude 20ch/456-QA slice, benchmark extras now include parquet deps, `suites.load_suite("tulving_episodic")` bridges adapter suites into `run_benchmark.py`, and prompts are self-contained with the selected book narrative prepended. 2026-06-19 post-run scorer `scripts/benchmark/score_tulving_run.py` landed in research `8249be9` for Simple Recall / Chronological Awareness report generation from raw run JSON. | **Completed/scored 2026-06-20**: raw run packaged in research `b6edc64`; corrected score and failure report in research `9e63af0` after parser repair. Run `20260619_141212`, `ingest_long_context`, production/default experts via `--skip-moe-reduction`; `456/456` scored, avg F1 `0.4309`, Simple Recall `0.5530`, Chronological Awareness `0.1593`, avg decode `17.27 t/s`, preflight all passed. Result is mixed: usable lexical recall, weak event/detail and chronology, and zero-answer hallucination failure. Research `2eb94f8` adds the targeted 120-row follow-up manifest; next action is to run that repair slice in a clean window, not route/memory promotion. |
| **K-DIV-1** (EV-8) | `diversity_metrics` + 5 `EvalResult` fields wired (`scripts/autopilot/diversity_metrics.py` + `safety_gate.py`; `src/` side pre-existing); 50 tests | Baseline diversity pass on 4 production roles; populate the SafetyGate two-tier WARN/REJECT thresholds (semantic-embedding-agreement needs an embedder pass). |
| **K-ROPE-1** (P10.2) | `scripts/benchmark/rope_position_probe.py` (`--dry-run` verified) | 5 models × 4 context lengths (4K/8K/16K/32K), 100 samples/cell ≈ 100 min. LOW priority, **bulk-pickup eligible**. Record collapse-point per model into the RoPE deep-dive appendix. |
| **K-SKILL-1** (EV-10a/b) — skill-efficacy gate validation | **Default-off live-branch wiring landed 2026-06-13** in epyc-orchestrator `924ca50`: `scripts/autopilot/actions.py` runs the no-artifact pre-mutation eval arm when `AUTOPILOT_SKILL_EFFICACY_GATE` is enabled, compares post-mutation per-suite deltas through `evaluate_skill_efficacy`, attaches `eval_result.details["skill_efficacy"]`, and reverts prompt/GEPA/code mutations before epoch acceptance if the gate rejects. Decision logic remains in `scripts/autopilot/skill_efficacy.py` (`evaluate_skill_efficacy`/`_split` negative-delta guard + dev/test discipline; surrogate `proxy_reward`/`feedback`/`require_cross_family`). Validation: 43 focused tests passed; ruff check/diff-check passed on changed files. | Remaining **restart/validation** work: deploy/restart with the flag default-off unless deliberately measuring it, then run a paired A/B over PromptForge mutations with `AUTOPILOT_SKILL_EFFICACY_GATE` isolated from `AUTOPILOT_BSV2_ACCEPT_GATE`. **Gate**: the negative-delta guard flags ≥1 real per-suite regression that aggregate-only acceptance would have admitted (the SkillsBench 16/84 pattern), AND accepted edits show no held-out-split regression beyond threshold. EV-10b surrogate scoring still needs verifier-LLM assertion authoring (cross-family, inference). The N2/J11 restart bundle is rebased onto live W7 tip `9e5d861` at `c63816b`; keep that lineage for deployment. Source: [eval-tower-verification.md](eval-tower-verification.md) EV-10 + [meta-harness-optimization.md](meta-harness-optimization.md) § 2026-05-27. |

**Run-command note**: each adapter is registered as a named suite, so existing seeding/eval harnesses pick them up by suite name (`scoring_verifiers`, `tulving_episodic`). K-RAG-1 + K-ROPE-1 are standalone scripts (env-var-swept / `--context-length` per cell). **K-SKILL-1 is the exception** — it is not a suite run; its default-off accept-path wiring exists, but validation is a flag-isolated paired-mutation A/B after the restart bundle, so it cannot be picked up turnkey like the others. Per `feedback_speed_verify_via_llama_bench` + `feedback_no_concurrent_inference`: the user/campaign runs these manually with per-run approval — code is prepared, not executed.

**K-RAG-1 seed sweep update (2026-06-19)**: the CPU-only K7 seed sweep ran during
the active AutoPilot window without touching llama servers:
`uv run python scripts/kb_rag/cli.py eval --output-dir
data/kb_rag/eval/k7_seed_20260619T0411Z` in `epyc-orchestrator`. The ignored
derived artifact contains 20 cases, 6 configs, no missing evidence files, index
stats 142 files / 4,958 chunks, and `onnxruntime 1.26.0` working in the
orchestrator venv. Best recall@10 was `0.300` for `rerank_w0.3`,
`rerank_w0.6`, and `recency_w0.1_s90_rerank_w0.3` vs MaxSim baseline `0.275`
(+2.5pp on the seed suite). Treat this as a seed-suite positive for rerank, not
a final default-weight promotion; the case file itself says it is not the final
50+20 certification pool.

---

## Reporting

After each Package completes:
1. Update the task checkboxes in this file
2. Update the relevant domain index (routing, research, pipeline, hermes)
3. Update [`master-handoff-index.md`](master-handoff-index.md) priority queue
4. Add session to `progress/YYYY-MM/YYYY-MM-DD.md`

When all Packages complete:
- Move this handoff to `handoffs/completed/`
- Extract reusable findings to docs/research
- Update `CHANGELOG.md` with key results

---

## Cross-Role Contention + Placement (shape-keyed-contention-gating) — TRACKING [added 2026-05-30]

Sibling to **Package J** (within-role placement). Where Package J makes *one role* fan out across disjoint quarters, this work (`handoffs/active/shape-keyed-contention-gating.md`) makes *different roles* co-reside on disjoint shapes — closing the seeder's non-work-conserving gap (heavy node-half runs while q2/q3 sit idle).

**State:** Part A + A-1 CODE-COMPLETE, and Step 1 is staged in `orchestrator_stack.py` to default `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1` on the next API reload. Part B is now end-to-end code-complete/default-off: dispatch passes real `candidate_topology_idx` values to the authoritative shape-aware gate when both flags are armed, with 146 affected tests green. Live traffic is unchanged because `ORCHESTRATOR_SHAPE_AWARE_CONTENTION` is off and the API was not reloaded. C remains prep only (`select_backfill_candidate`); heavy veto/barrier/pressure-skip are untouched.

**⏳ ACTION ON J6 END (do immediately):** the live-observation gate must run *while the stack is quiesced*, in a flag-on bracket, then either revert or deliberately mark an epoch before resuming. Sequence: autopilot clears → reload orchestrator so the staged `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1` default is live → verify `/proc/<api_pid>/environ` → run the multi-role fan-out helper from orchestrator `937e6446` (`.venv/bin/python scripts/benchmark/placement_fanout_probe.py --roles frontdoor,ingest_long_context --n 4 --mode concurrent --out /tmp/step2_cross_role_fanout.json`) → confirm region-lock dashboard shows heavy+light on disjoint shapes + queue-on-overlap → bracket `ORCHESTRATOR_SHAPE_AWARE_CONTENTION=1` smoke for Step 2 (disjoint quarters admit; true q-overlaps queue). Adopting flag-on for production traffic is a SEPARATE decision requiring a `mark_epoch`/archive reset, not a silent resume.

**Cross-ref:** Package J (`within-role-placement-state-machine.md`) J7 is the within-role analogue (`ORCHESTRATOR_PLACEMENT_STATE_MACHINE=1` rollout); this is the cross-role layer above it.

---

## Internal Interaction Lifecycle (consult sibling) — TRACKING

Sibling tracker for [`internal-interaction-lifecycle.md`](internal-interaction-lifecycle.md); the inference-gated A/B it lands here is **J17** (above). J17 is double-hard-gated and must NOT trigger before BOTH clear: (a) the Cross-Role Contention + Placement bake (the shape-keyed TRACKING section above) shows green, and (b) the P1 lifecycle refactor has landed on `epyc-orchestrator/main` with the regression gate signed off (pytest green, byte-equal `delegation_diagnostics`, ≥48h autopilot bake). P1 code landed 2026-06-28 in orchestrator `18956892`; the byte-equal `delegation_diagnostics` regression gate is now pinned, but the live affinity preflight and >=48h bake remain open, so J17 stays locked.
Attach point chosen (P2-0): `edit_transaction.py:199` `run_edit_transaction()` between draft parse `:210` and apply `:211`; requester `coder_escalation` / consultant `architect_general` / skill `review_before_commit`. When both prereqs clear, trigger J17, then report back here + the lifecycle handoff's P2 Gate-to-P3 checklist (P3 shadow-gate / P4 reward-eval surface as J18+ once J17 clears).
