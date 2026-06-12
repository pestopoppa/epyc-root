# EPYC Handoff — Master Index

**Purpose**: dispatch. Find your domain index or claim a queue row. History lives in `progress/`; completed work in `handoffs/completed/`. Rows are **deleted** on completion (not struck through). Claims cite `MEASUREMENT.md` protocols; historical numbers era-label via `instrument_eras.yaml`. The pre-2026-06-12 chronology header + 66-row queue is preserved at `progress/2026-06/master-index-pre-rewrite-archive-2026-06-12.md`.

## Domain indices
| Routing/autopilot/stack | [routing-and-optimization-index.md](routing-and-optimization-index.md) | | Acceleration | [inference-acceleration-index.md](inference-acceleration-index.md) |
|---|---|---|---|---|
| CPU throughput | [cpu-inference-optimization-index.md](cpu-inference-optimization-index.md) | | Research/eval | [research-evaluation-index.md](research-evaluation-index.md) |
| Hermes/agent UX | [hermes-agent-index.md](hermes-agent-index.md) | | Pipelines | [pipeline-integration-index.md](pipeline-integration-index.md) |

**Standing contracts**: `/workspace/MEASUREMENT.md` (adopted) · `instrument_eras.yaml` (epyc-orchestrator orchestration/) · ATTESTATION (to build, findings-04 §B) · current architecture review: [fable5-findings-00-executive-summary.md](fable5-findings-00-executive-summary.md) — **the Fable 5 one-shot review is COMPLETE (2026-06-12)**; its 7 findings (-01..-07) + appendix are the standing reference, not an open row.

## A. NOW — live damage, zero-inference quick wins, or this-week leverage
| # | Item | A-by | Why now |
|---|---|---|---|
| N1+N4 | **Evidence-plane instrument repair** — W1-W4 live repairs landed 2026-06-12 (baseline ratchet, double `gate.check()`, T0 bypass/namespacing, strategy/distill gates, `expected=''`, pandas, VL/OCR trace, NFKD, Seeder state, dead-row sampler replacement); next is core_v2/audit/item analytics via [evidence-plane-instrument-repair.md](evidence-plane-instrument-repair.md) | op | live damage mostly stopped; fixed core/audit still gate stronger verdicts |
| N2 | **Per-question eval ledger + sequential e-process verdicts** + McNemar replay of 120 trials → [evidence-plane-ledger-and-sequential-verdicts.md](evidence-plane-ledger-and-sequential-verdicts.md) (restart-bundle owner) | op | keystone; gates Queue 3 + CAP-REG |
| N5 | **α(Qwen3-1.7B→frontdoor) on CPU** → [gpu-drafter-mi200-investigation.md](gpu-drafter-mi200-investigation.md) §Gating Measurement | op | hardware-independent; forks the whole GPU program (findings-03 G1) |
| N6 | **Objective policy decision**: task_rate replay/report + doc-truth W4 are done; W3 flip is gated on 1/5 drop vs ≥2/5 proof threshold + raw-rate zero-quality frontier risk → [objective-task-rate-goodput.md](objective-task-rate-goodput.md) | op | review before live dominance change (findings-05) |
| N7 | **Zero-inference campaign analyses** (run today, alongside the live autopilot): J13 BT-hint verdict, J7 DCP-6 offline replay, K-RAG-1 recall sweep (CPU-only) | either | each closes or re-gates a decision at ~0 llama-hours (= campaign Queue 1); DAR-1, J9, and J12 wiring closed 2026-06-12 |
| N9 | **retrain-routing-models unblock**: operator BGE re-embed (NOT lollms); verify the 0-byte `embeddings.faiss` observed 14:54 today | op | live routing-memory anomaly + named blocker |
| N10 | **tri-role shadow-telemetry follow-through** — W7 persistence landed; next use the progress-log fields to close TR-3.3/3.4 instead of adding another shadow path → [routing-truth-restoration.md](routing-truth-restoration.md) | op | coordination surface (this index rewrite applied 2026-06-12) |

## B. ACTIVE — claimable now (HIGH → LOW)
| # | Item | Gate/note |
|---|---|---|
| A1 | **shape-keyed-contention rollout** — analyze Step-1 observation JSONL (free), then the quiesce-window flag bracket | bracket owns the reload (see §C) |
| A2 | **multi-file edit-transaction rollout decision** (5/5 vs loop-failures proven; flag default-off) | operator A/B-then-enable; promotion-cohort candidate |
| A3 | **within-role placement**: J2/J3 live migration probe | quiesce window (single-worker API) |
| A4 | **eval-tower-verification** EV-8/9/10 | re-sequenced AFTER N2/N4 (EV-4 calibration explicitly waits for the redesigned tower) |
| A5 | **bulk-inference-campaign model/role respecification** (G9 references removed architect_coding; G10/G11 name dead models) before spending hours | 3-queue restructure DONE 2026-06-12; respecification is the residual doc work |
| A6 | **Running-state attestation generator** (processes/flags/serving-config/eval-instrument/drift; safety-gate consumer) → [running-state-attestation.md](running-state-attestation.md) | HIGH, ~3-4 days, consolidation of existing checks |
| A7 | **Batched-decode measurement** — E1 CPU14 `-np` sweep + E2 single-instance eval A/B; conditional E3 8x8 GEMM SIMD → [batched-decode-measurement.md](batched-decode-measurement.md) | ACTIVE-HIGH; E1/E2 = quiesce-window Queue-2 item 2 |
| A8 | **Evidence-plane event-sourcing + narrative regeneration** (T2 drift gate already MET) → [evidence-plane-event-sourcing-and-narrative.md](evidence-plane-event-sourcing-and-narrative.md) | HIGH, after N2/EP-2 |
| MED | colbert S5 gate-analysis (read-only script) · DSA D1 smoke (per-run approval; refresh PR snapshot first) · **model-capability descriptors** → [model-capability-descriptors.md](model-capability-descriptors.md) (compiler can start today; swap-CI gate) · reasoning-compression enforce-decision (n≥100 gate) · streaming-llm baseline (nightshift, gates 5 KV items) · unified-trace EXM-1 (coordinate with ledger schema) · engram Track-A Phase-0 (30 min, no compute) · bep-dcp DCP-6 replay · internal-kb-rag K7 · minddr MD-9 (=J15) · repl-turn-efficiency S4 + ColGREP soak check · K-EMB-1 granite bench (embedder servers only; informs the N9 re-embed choice) · meta-harness MH-6/7/9 | per-row gates as written |
| LOW | env-flags-inventory launcher audit · granite Phase-A · integration-test tranches · memento S2 smoke · agent-file-compression Ph3 (HIGH rating stripped) · attention-matching refresh-vs-Qwen3.6 · context-folding tails · multimodal vision validation (servers ARE live; quick win) · searxng CA-1..5 (port-8086 conflict noted) · ernie QA · ODL/LiteParse benches · per-request-budget Fix A/B · root-archetype-linter close-out (one session, then archive) · security-review-skill authoring · x-mas v4 axis · campaign G-tail (respecify models first) / J8 optional / J14 (down-prioritized per findings-02) / K-MEM-1 / K-DIV-1 (measure now, thresholds after N2) / K-ROPE-1 | opportunistic / window-filler |

## B2. Frontier programs (strategic spine — spec: [fable5-findings-07-strategic-frontiers.md](fable5-findings-07-strategic-frontiers.md))
| # | Prio | Item | Handoff |
|---|---|---|---|
| F4 | HIGH (this month) | Backup the irreplaceable <2GB evidence base off the raid0 (manifest, restic job, restore proof, ATTESTATION checks) | [frontier-f4-continuity-backup.md](frontier-f4-continuity-backup.md) |
| F5 | HIGH (this month) | Harden research-intake against instruction injection (quarantine policy, renderer, validator, canary) — prereq for F2 intake jobs | [frontier-f5-intake-injection-hardening.md](frontier-f5-intake-injection-hardening.md) |
| F1 | MED | Real-task corpus as eval distribution — passive task_record capture, real-suite v1, wire into promotion/routing decisions | [frontier-f1-real-task-corpus.md](frontier-f1-real-task-corpus.md) |
| F2 | HIGH, gated: N1+N4, N2, F5 | Self-running lab — lab_jobs.yaml inventory, contract-validated runner with review queue, shadow→reviewed→autonomous ladder | [frontier-f2-self-running-lab.md](frontier-f2-self-running-lab.md) |
| F3 | MED (W3 HW-GATED: MI210) | Data flywheel — planner-archive/triage capture hygiene + dataset builders now; planner-distill/drafter/judge fine-tunes after GPU | [frontier-f3-data-flywheel.md](frontier-f3-data-flywheel.md) |
| F6 | MED | Upstream/publication yield-capture: D2 DSA PR spearhead, canonical-bench methodology post, protocol-tagged results page | [frontier-f6-upstream-publication.md](frontier-f6-upstream-publication.md) |
| F7 | LOW-MED | Economic ledger over existing logs: weekly cloud-spend/inference-hours/operator-latency + digest section + decision rules | [frontier-f7-economic-ledger.md](frontier-f7-economic-ledger.md) |

## C. The bulk-inference campaign, restructured
Full structure + per-task detail in [bulk-inference-campaign.md](bulk-inference-campaign.md) (restructured into 3 queues 2026-06-12).
- **Queue 1 — offline-now** (≈0 llama-hours): remaining N7 analyses (J13/J7/K-RAG) + G12 tier calibration when G10/G11 data exists + campaign-doc hygiene. DAR-1, J9, and J12 wiring are closed.
- **Queue 2 — ONE consolidated quiesce window** (at t1000 or operator SIGTERM; ~28–31h; ONE attested reload serves all): (1) reload with **declared production env** (fixes test-defaults; sets every flag this window needs — the only route around the 1-of-6 POST /config bug) + per-worker attestation; (2) **E2 then E1 batched-decode measurements first** (findings-06 — E2 makes every later eval cheaper); (3) shape-keyed flag-on bracket; (4) J2/J3 single-worker probe; (5) J12 probe + THINK-ABL-1 (best leverage/hour, +33pp class effect); (6) J15 MD-9; (7) J7 DCP-6 inference half; (8) J10 URE shadow env-flag rides the reload free; J16 only if N2+N4 landed and its leak premise re-verified.
- **Queue 3 — restart bundle** (next autopilot restart, flag-isolated): per-question ledger + sequential verdicts (findings-01c) + J11/BSV-2 + K-SKILL-1; then H5/EV-4 calibration baselines the **redesigned** tower (K-EVAL-1 folded into H5 — single owner).
- **Standalone model-batched windows** (~27h): group K-MEM-1 × K-ROPE-1 × G11 × G5 **by model** so each GGUF loads once; K-EMB-1 embedder-only; H7 transformers-CPU serial.
- **Frozen after DAR-1 replay**: Package I (SPO+/bilinear/ThinkPRM) stays frozen because the 2026-06-12 replay measured 0.00% identifiable mean regret (<5% gate).
- Stale premises corrected in the campaign doc's §Staleness corrections: J6 superseded (continuous run IS the soak), G9 targets the removed architect_coding role, G10/G11 name pre-swap models, J12 wiring was verified against LlamaServerBackend `/v1/chat/completions` (not openai.py), flag A/Bs set flags via launch env + per-worker attestation, speed-metric paragraph changes when the task_rate objective lands.

## D. Hygiene executed 2026-06-12 (Fable 5 portfolio pass)
A full review of all active + blocked handoffs (108 classified rows; raw verdicts in [fable5-findings-appendix-evidence-reports.md](fable5-findings-appendix-evidence-reports.md)) drove a one-session cleanup: **15 handoffs archived** (extract-then-move to `../completed/`, no unchecked items / no live reopen gate), **5 merged** (qkernel→cpu-shape-specialized-gemv-decode · autowiki→internal-kb-rag · handoff-backlog-hygiene-audit→this rewrite · cpu-benchmark-rigor (CPU20)→`MEASUREMENT.md` · campaign K-EVAL-1→H5), and header refreshes on the stale live files (deepseek-v4, tool-use-eval-contract, retrain-routing-models, learned-routing-controller, decision-aware-routing, bulk-inference-campaign, moe-spec). Per-handoff disposition (which residuals moved where, reopen triggers) is in `progress/2026-06/2026-06-12.md`. Do not re-add archived/merged handoffs as active rows.

## E. GATED — do not start; named conditions (representative clusters)
| Cluster | Gate |
|---|---|
| Routing expansion (LRC Ph1.5+, Trinity TR-4/5, outer-coordinator, DAR-3/SPO+, Package I, J14-beyond-kill-gate) | **Frozen**: DAR-1 replay on 2026-06-12 measured 0.00% identifiable mean regret (<5%). Re-open only after a future quarterly/current-traffic DAR-1 replay reaches ≥5% AND per-question vectors (N2) exist. |
| Accept-path changes (J11/BSV-2, K-SKILL-1, H5/EV-4, K-DIV-1 thresholds, any future J9 promotion) | restart bundle WITH findings-01 ledger/verdicts — owner: [evidence-plane-ledger-and-sequential-verdicts.md](evidence-plane-ledger-and-sequential-verdicts.md). Current J9 proxy metrics closed diagnostic-only on 2026-06-12. |
| Capability registry + safe role-restart applicator + monthly promotion pass → [capability-registry-and-promotion.md](capability-registry-and-promotion.md) (W0 workload model ungated, 1 day) | EP-2 ledger landed (instrument must certify effects before the optimizer gets bigger levers) |
| Batched-kernel work: 8x8 GEMM SIMD body (E3), CPU17 chunked-prefill re-promotion, CPU18 MegaBlocks → owner [batched-decode-measurement.md](batched-decode-measurement.md) | E1/E2 results (Queue 2) |
| TiDAR one-pass Variant B ggml work (~1.3–2× from idle FLOPS; 5–10 days) → [tidar-one-pass-variant-b.md](tidar-one-pass-variant-b.md) (W1 static mask analysis ungated) | Q4_K_M-quantizable TiDAR-class checkpoint exists |
| Upstream-PR monitors: STQ1_0 #22836 (then bench the on-disk 1.8B artifact), TQ3 #21089, DSA #21149 maturation, log-linear-GDN / multiscreen / summary-token checkpoint watches | external releases |
| Operator-decision-only: deepseek-v4 D1/D2/D3, launcher --numa-mode default, halo-engine install, δ-mem Phase-2 go, glm51 Phase-0 disposition, qwen36-27b curiosity probe, sliders Phase-0 (K7-triggered), swarm-distillation (Strand Phase-B bands), agent-world AW-6/7/8 | named per row |
| sarathi-serve | workload-shift gate — **flag to the E1/E2 executor: the batched-eval regime IS this gate's trigger; expect it to fire** |
| internal-interaction-lifecycle P1→J17 | contention bake clean + P1 refactor + ledger |

## F. HW-GATED — MI210 (~July 2026; **all gated per operator instruction**)
gpu-drafter-mi200 (G1 α moved to N5 — CPU-testable; all GPU stages gated) · gpu-acceleration-path (internal order per findings-03: residency → eval-engine → embedder host → prefill → drafter farm) · agentic-rocm + rocm-verify-profile (pre-hardware prep only: pin commits, license check, env recipe, write P-GPU-1 protocol BEFORE the card) · delta-mem magnitude gates · 08-doc-to-lora Phase-B (archived; reopen tag).

## Reporting
On completing a row: delete it here, update the owning handoff + domain index, append to `progress/YYYY-MM/`; numbers use the claim grammar. Weekly freshness check must pass (>14d untouched without a `gated:` tag = violation).
