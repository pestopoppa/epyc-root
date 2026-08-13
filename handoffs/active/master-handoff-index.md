# EPYC Handoff — Master Index

**Purpose**: **routing only.** Find your domain index, then your row. This file owns no backlog rows —
it is the cheapest hop, so it stays short. Work lives in the domain indices; history lives in `progress/`
and `handoffs/completed|archived/`.

> **Live campaign state** (autopilot posture, freeze status, active lanes):
> [`CURRENT-CAMPAIGN.md`](CURRENT-CAMPAIGN.md) — read it before starting anything that touches the
> production stack.

## Domain indices

| Domain | Index | Scope |
|--------|-------|-------|
| Inference research | [inference-research-index.md](inference-research-index.md) | Kernels, quantization, serving performance, models (CPU **and** GPU) |
| Routing / autopilot / stack | [routing-and-optimization-index.md](routing-and-optimization-index.md) | Orchestrator, registry, stack lifecycle, autopilot, fleet coordination |
| Research & evaluation | [research-evaluation-index.md](research-evaluation-index.md) | Benchmarks, scorers, audits, research programs |
| User-facing harness | [user-facing-harness-index.md](user-facing-harness-index.md) | REPL/UX, prompting, memory, output compression (surface, not an implementation commitment) |
| Pipelines & integration | [pipeline-integration-index.md](pipeline-integration-index.md) | Ingestion, document/RAG pipelines, knowledge base |
| Reviewer control plane | [reviewer-control-plane-index.md](reviewer-control-plane-index.md) | Reviewer roles, capability gates, control-plane policy |

**Exactly one index owns each handoff.** A handoff listed twice is a defect — `index_state.py --check`
fails on it. Cross-domain relevance is a `Deps` edge, never a second row.

## Operator decision queue

Decisions only the operator can make. **This is the one hand-maintained list in this file** — it exists
because a form-screen cannot detect "needs a human choice", and a decision buried in a handoff body gets
missed (measured: G9-disk sat unnoticed for two weeks and governed 227 GB).

| ID | Decision | Owner | Open since |
|----|----------|-------|-----------|
| OP-1 | P0.1–P0.3 sign-off bundle | [orchestration-robustness-audit-2026-07-11.md](orchestration-robustness-audit-2026-07-11.md) | 2026-07-11 |
| OP-3 | Zero-inference decision batch — residual `dispatch_swarm_fanout` items | [routing-and-optimization-index.md](routing-and-optimization-index.md) | 2026-07-14 |
| OP-5 | Reviewer control-plane decision bundle (P-REV-1 amendment) | [reviewer-control-plane-index.md](reviewer-control-plane-index.md) | 2026-07-16 |
| OP-6 | Consolidated quiet window — reviewer-plane baselines on the v8 reference lineup | [reviewer-control-plane-index.md](reviewer-control-plane-index.md) | 2026-07-17 |
| OP-7 | `HF_TOKEN` provisioning — downloads run unauthenticated at ~9 MB/s (~5.5 h per 170 GB) | [deepseek-v4-flash-0731-dspark.md](deepseek-v4-flash-0731-dspark.md) | 2026-08-09 |
| OP-8 | GLM-5.2 GO/WAIT/KILL verdict — also governs **222 GB** of disk | [glm51-reap-cpu-evaluation.md](glm51-reap-cpu-evaluation.md) | 2026-08-10 |
| OP-9 | Nothing restarts `hub_supervisor.sh` if it dies — cron `once` form vs leave as-is (host-level) | [handoff-index-and-backlog-graph.md](handoff-index-and-backlog-graph.md) | 2026-08-10 |
| OP-10 | P-GPU-1 `duty_cycle` amendment — field 4's "fresh server per rep" measures the **bursty** regime, not sustained serving; label it or author a sustained variant. Human-amendment-only (measurement trust boundary) | [autokernel-research-loop.md](autokernel-research-loop.md) §21 AK-OP-1 | 2026-08-10 |
| OP-12 | Approve or decline one experimental commit for the one-file IQ2_XXS one-row VPOPCNT dispatch; screening A/B is +5.733% at n=1 and parity at n=512 | [mi210-q8-dequant-gemv-roofline.md](mi210-q8-dequant-gemv-roofline.md) INF-37 | 2026-08-11 |
| OP-13 | Ratify a P2-5j placement amendment or require a full P-BENCH-PLACEMENT-1 composite; the old four-arm design is observation-only | [gpu-serving-tie-in-program.md](gpu-serving-tie-in-program.md) P2-5j | 2026-08-11 |
| OP-15 | Approve or decline one experimental commit for the Q4_K branchless scale/min decoder before a clean governed replay | [mi210-q8-dequant-gemv-roofline.md](mi210-q8-dequant-gemv-roofline.md) INF-37 | 2026-08-11 |
| OP-17 | Amend frozen-v9 attestation with llama ggml `0.16.0`, or retain an intentionally unverified complete-kernel-set fold | [autokernel-research-loop.md](autokernel-research-loop.md) AK6 dashboard residual | 2026-08-12 |
| OP-19 | Rule the E8 chain retired (or not): B9/B10 are BLOCKED-AND-LIKELY-MOOT — their source evidence was destroyed and the era advanced to E9 on 2026-08-11, so both boxes wait on this ruling alone | [autopilot-decision-plane-audit-2026-07-22.md](autopilot-decision-plane-audit-2026-07-22.md) | 2026-08-12 |
| OP-20 | One ruling on `task_failed` scoring applied to BOTH producers (`eval_tower:1339` excludes it; the seeding path scores it WRONG) — until it lands, quality numbers are not comparable across producers. Auditor recommends: non-infra → WRONG in both, infra → EXCLUDED in both | [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) | 2026-08-12 |
| OP-24 | Adopt the trained `[Q]`/`[D]` ColBERT prefixes in KB-RAG — which requires **re-embedding the whole KB corpus** — or accept the current off-distribution retrieval. Measured: omitting the prefix perturbs MaxSim **25× more than INT8 quantization** (1.63e-01 vs 6.60e-03) and changes top-1 on **37.5%** of queries. Index and query paths are mutually consistent today, so a one-sided fix is strictly worse; that is what makes it a migration, not a patch. Also gates whether published BEIR deltas forecast production | [colbert-reranker-web-research.md](colbert-reranker-web-research.md) PREFIX-1 | 2026-08-12 |  **ANSWERED 2026-08-12: operator said go. Migration in flight — new index-qd-v1 store built alongside the live one, ~40% at the reboot, resuming with 176-core fan-out.**
| OP-22 | Rebuild the devcontainer to deploy `136894e8` (2026-07-31, drops CPU-only llama dirs from the global `LD_LIBRARY_PATH`). Committed but NOT live: container PID 1 started 2026-07-29, so every shell inherits the pre-fix `containerEnv` and hand-run speech binaries silently load mixed ggml generations. Production serving is unaffected; host/container lifecycle is operator-only | [ggml-linkage-and-speech-kernels](../../scripts/session/verify_speech_kernels.sh) | 2026-08-12 |

Full text for OP-1..OP-6 (including the closed OP-2 and the superseded narration) is preserved in
[`../archived/master-handoff-index-history-through-2026-08-10.md`](../archived/master-handoff-index-history-through-2026-08-10.md).

## Standing contracts

`/workspace/MEASUREMENT.md` (adopted) · `instrument_eras.yaml` (epyc-orchestrator `orchestration/`) ·
current architecture review: [fable5-findings-00-executive-summary.md](../completed/fable5-findings-00-executive-summary.md)
(COMPLETE 2026-06-12 — standing reference, not an open row) ·
cross-domain governance: [stale-open-audit-2026-07-18.md](stale-open-audit-2026-07-18.md).

## Backlog state (generated)

Regenerate with `python3 scripts/handoffs/index_state.py`. Per-handoff detail — open/closed counts,
`last_advanced`, blocked/guarded — lives in `handoffs/active/.index-state.json`.

**`last_advanced` is the date a checkbox last changed**, not the file mtime and not the last commit:
prose edits and typo fixes are not progress. A domain whose oldest advance is months back has handoffs
nobody is moving.

<!-- BEGIN GENERATED index_state -->
| Domain | Handoffs | Open | Blocked | Oldest advance |
|--------|----------|------|---------|----------------|
| inference-research | 53 | 367 | 12 | 2026-07-29 |
| pipeline-integration | 5 | 55 | 1 | 2026-07-29 |
| research-evaluation | 46 | 313 | 9 | 2026-07-29 |
| reviewer-control-plane | 9 | 30 | 11 | 2026-07-29 |
| routing-and-optimization | 50 | 379 | 18 | 2026-07-29 |
| user-facing-harness | 7 | 38 | 3 | 2026-07-29 |
<!-- END GENERATED index_state -->

## Reporting

On completing a row: flip the checkbox in the owning **handoff**, update the row's `Next action` in its
domain index, append to `progress/YYYY-MM/`. Then run `python3 scripts/handoffs/index_state.py` to
refresh generated state and `--check` before committing. Numbers use the claim grammar in
[`MEASUREMENT_POLICY.md`](../../agents/shared/MEASUREMENT_POLICY.md).

Row contract (what may and may not go in a row):
[`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).
