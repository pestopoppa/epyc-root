# PROPOSAL v2 — master-handoff-index.md rewritten (full-portfolio review, 2026-06-12)

> **v2 supersedes v1** (same day). v1 was seeded from the old queue's live rows; **v2 is grounded in a full review of all 96 active handoffs + blocked/ + a deep audit of bulk-inference-campaign.md** (5 reviewer agents, 108 classified rows; raw verdicts in `fable5-findings-appendix-evidence-reports.md`). Apply by replacing the master index body; per-handoff header refreshes and archive moves listed in §D. **All MI210-dependent work stays HW-GATED per operator instruction** — the only GPU-adjacent active items are hardware-independent de-risking measurements.

---

# EPYC Handoff — Master Index

**Purpose**: dispatch. Find your domain index or claim a queue row. History lives in `progress/`; completed work in `handoffs/completed/`. Rows are **deleted** on completion. Claims cite `MEASUREMENT.md` protocols; historical numbers era-label via `instrument_eras.yaml`.

## Domain indices
| Routing/autopilot/stack | routing-and-optimization-index.md | | Acceleration | inference-acceleration-index.md |
|---|---|---|---|---|
| CPU throughput | cpu-inference-optimization-index.md | | Research/eval | research-evaluation-index.md |
| Hermes/agent UX | hermes-agent-index.md | | Pipelines | pipeline-integration-index.md |

**Standing contracts**: `/workspace/MEASUREMENT.md` (adopted) · `instrument_eras.yaml` (epyc-orchestrator orchestration/) · ATTESTATION (to build, findings-04 §B) · current architecture review: `fable5-findings-00-executive-summary.md`.

## A. NOW — live damage, zero-inference quick wins, or this-week leverage
| # | Item | A-by | Why now |
|---|---|---|---|
| N1 | **Baseline ratchet fix** (t775 noise-max baseline; −5% gate failing ~half of honest trials) + double `gate.check()` + dead throughput floor + T0 `[:10]` + strategy/distill exclusion gates | op | live damage (findings-01 §3) |
| N2 | **Per-question eval ledger** + McNemar replay of 120 trials | op | keystone; gates the restart bundle (findings-01-impl Ph1) |
| N3 | **Prod flag declaration + shared flag substrate + per-worker attestation endpoint** | op | every flag A/B invalid until fixed (findings-02 §2) |
| N4 | **Instrument repair**: `expected=''` gate, pandas, trace one vl request, NFKD diacritics, persist Seeder per-question results | op | 8 dead questions of 43 (findings-01-impl §2.0) |
| N5 | **α(Qwen3-1.7B→frontdoor) on CPU** | op | hardware-independent; forks the whole GPU program (findings-03 G1) |
| N6 | **Objective replay**: task_rate axis over journal history; bloat-artifact report | op | zero inference (findings-05) |
| N7 | **Zero-inference campaign cleanup**: K-RAG formal K7 prep/sweep + DCP-6a content-depth/freshness repair before J7 inference | either | J7 offline replay closed 2026-06-12 but found one-line slices + missing content hashes; K-RAG diagnostic is non-certifying until runtime/index/harness are fixed |
| N8 | **autopilot-continuous-optimization**: hunk-stage the 4 uncommitted autopilot.py groups; `git add` tool-use-eval-contract.md + fable5 files (untracked coordination state) | op | uncommitted live-deployed code in a shared clone |
| N9 | **retrain-routing-models unblock**: operator BGE re-embed (NOT lollms); verify the 0-byte `embeddings.faiss` observed 14:54 today | op | live routing-memory anomaly + named blocker |
| N10 | Apply this index rewrite + §D hygiene batch; tri-role shadow-telemetry keep-or-kill decision | op | coordination surface for everything above |

## B. ACTIVE — claimable now (HIGH → LOW)
| # | Item | Gate/note |
|---|---|---|
| A1 | **shape-keyed-contention rollout** — analyze Step-1 observation JSONL (free), then the quiesce-window flag bracket | bracket owns the reload (see §C) |
| A2 | **multi-file edit-transaction rollout decision** (5/5 vs loop-failures proven; flag default-off) | operator A/B-then-enable; promotion-cohort candidate |
| A3 | **within-role placement**: J2/J3 live migration probe | quiesce window (single-worker API) |
| A4 | **eval-tower-verification** EV-8/9/10 | re-sequenced AFTER N2/N4 (EV-4 calibration explicitly waits for the redesigned tower) |
| A5 | **bulk-inference-campaign restructure** into 3 queues (§C) + header/package respecification (G9 references removed architect_coding; G10/G11 name dead models) | doc work, today |
| MED | colbert S5 gate-analysis (read-only script) · DSA D1 smoke (per-run approval; refresh PR snapshot first) · reasoning-compression enforce-decision (n≥100 gate) · streaming-llm baseline (nightshift, gates 5 KV items) · unified-trace EXM-1 (coordinate with ledger schema) · engram Track-A Phase-0 (30 min, no compute) · bep-dcp DCP-6a repair + replay rerun · internal-kb-rag K7 runtime/index/harness prep · minddr MD-9 (=J15) · repl-turn-efficiency S4 + ColGREP soak check · K-EMB-1 granite bench (embedder servers only; informs the N9 re-embed choice) · meta-harness MH-6/7/9 | per-row gates as written |
| LOW | env-flags-inventory launcher audit · granite Phase-A · integration-test tranches · memento S2 smoke · agent-file-compression Ph3 (HIGH rating stripped) · attention-matching refresh-vs-Qwen3.6 · context-folding tails · multimodal vision validation (servers ARE live; quick win) · searxng CA-1..5 (port-8086 conflict noted) · ernie QA · ODL/LiteParse benches · per-request-budget Fix A/B · root-archetype-linter close-out (one session, then archive) · security-review-skill authoring · x-mas v4 axis · campaign G-tail (respecify models first) / J8 optional / J14 (down-prioritized per findings-02) / K-MEM-1 / K-DIV-1 (measure now, thresholds after N2) / K-ROPE-1 | opportunistic / window-filler |

## C. The bulk-inference campaign, restructured (replaces its flat Current-State table)
**Queue 1 — offline-now** (≈0 llama-hours): K-RAG formal K7 prep/sweep + DCP-6a repair/replay rerun + G12 tier calibration + campaign-doc hygiene; J7 offline replay, DAR-1, J9, J13, and J12 wiring are closed in the canonical index.
**Queue 2 — ONE consolidated quiesce window** (at t1000 or operator SIGTERM; ~28–31h; ONE attested reload serves all): (1) reload with **declared production env** (fixes test-defaults; sets all flags this window needs — the only route around the 1-of-6 POST /config bug) + per-worker attestation; (2) **E2 then E1 batched-decode measurements first** (findings-06 — E2 makes every later eval cheaper); (3) shape-keyed flag-on bracket; (4) J2/J3 single-worker probe; (5) J12 probe + THINK-ABL-1 (best leverage/hour, +33pp class effect); (6) J15 MD-9; (7) J7 DCP-6 inference half; (8) J10 URE shadow env-flag rides the reload free; J16 only if N2+N4 landed and its leak premise re-verified.
**Queue 3 — restart bundle** (next autopilot restart, flag-isolated): per-question ledger + sequential verdicts (findings-01c) + J11/BSV-2 + K-SKILL-1; then H5/K-EVAL-1 calibration baselines the **redesigned** tower (fold K-EVAL-1 into H5 — duplicate row).
**Standalone model-batched windows** (~27h): group K-MEM-1 × K-ROPE-1 × G11 × G5 **by model** so each GGUF loads once; H7 transformers-CPU serial.
**Frozen pending DAR-1 replay** (~24–28h): Package I (SPO+/bilinear/ThinkPRM) — prediction: regret <5% ⇒ stays frozen.
Stale premises to fix in the campaign doc: J6 superseded (the continuous run IS the soak — close by analysis); G9 targets a removed role; G10/G11 name pre-swap models; J12 verification must target LlamaServerBackend (not openai.py); speed-metric policy paragraph awaits the task_rate axis.

## D. Hygiene batch (one session): ARCHIVE 15 / MERGE 5 / header refreshes
- **Archive** (extract-then-move; no unchecked items, no live reopen gate): earlyoom (verified live), nps-reboot-runbook, reboot-validation-resume-2026-05-19, cpu-optimization-thesis-pause, llama-cpp-kernel-push-rebase (keep #22836 watch in tq3 row), peer-verifier (NO-GO + triggers), gemma4-mtp-drafter-eval (deployed 5wk ago; extract 3 residuals to acceleration index), 08-doc-to-lora (extract findings), qwen-scope-sae (fold §4 into eval-tower), single-instance-system-tuning (reference), cpu-decode-flops-roofline (results live in findings-06; backfill note), autopilot-dispatch-latency (core done), blocked/09-ouroboros (references deprecated stack), campaign Packages A–F + J1/J4x/J5 prose (runbook → completed).
- **Merge**: qkernel-q5q6 → cpu-shape-specialized-gemv-decode · autowiki → internal-kb-rag · handoff-backlog-hygiene-audit → this rewrite (carry its method-corrections as policy) · **cpu-benchmark-rigor (CPU20) → MEASUREMENT.md** (single protocol source; keep the handoff as the historical record) · campaign K-EVAL-1 → H5.
- **Header refreshes** (stale current-state on live files): deepseek-v4 (still says "download 5%"; reality = Strategy-B FAIL + 3 operator decisions), tool-use-eval-contract ("resume pending" vs live t777), retrain-routing-models (wrong blocker named), learned-routing-controller (must state the fast-path is dead — weights missing), decision-aware-routing + bulk-inference-campaign "Updated" lines, moe-spec (consumer gone; reopen chained to N5/α).

## E. GATED — do not start; named conditions (36 rows; representative set)
| Cluster | Gate |
|---|---|
| Routing expansion (LRC Ph1.5+, Trinity TR-4/5, outer-coordinator, DAR-3/SPO+, Package I, J14-beyond-kill-gate) | **DAR-1 regret replay ≥5% AND per-question vectors (N2)** — else stays frozen |
| Accept-path changes (J11/BSV-2, K-SKILL-1, H5/EV-4, K-DIV-1 thresholds, J9 promotion) | restart bundle WITH findings-01 ledger/verdicts |
| Batched-kernel work: 8x8 GEMM SIMD body (E3), CPU17 chunked-prefill re-promotion, CPU18 MegaBlocks | E1/E2 results (Queue 2) |
| Upstream-PR monitors: STQ1_0 #22836 (then bench the on-disk 1.8B artifact), TQ3 #21089, DSA #21149 maturation, log-linear-GDN / multiscreen / summary-token checkpoint watches | external releases |
| Operator-decision-only: deepseek-v4 D1/D2/D3, launcher --numa-mode default, halo-engine install, δ-mem Phase-2 go, glm51 Phase-0 disposition, qwen36-27b curiosity probe, sliders Phase-0 (K7-triggered), swarm-distillation (Strand Phase-B bands), agent-world AW-6/7/8 | named per row |
| sarathi-serve | workload-shift gate — **flag to the E1/E2 executor: the batched-eval regime IS this gate's trigger; expect it to fire** |
| internal-interaction-lifecycle P1→J17 | contention bake clean + P1 refactor + ledger |

## F. HW-GATED — MI210 (~July 2026; **all gated per operator instruction**)
gpu-drafter-mi200 (G1 α moved to N5 — CPU-testable; all GPU stages gated) · gpu-acceleration-path (internal order per findings-03: residency → eval-engine → embedder host → prefill → drafter farm) · agentic-rocm + rocm-verify-profile (pre-hardware prep only: pin commits, license check, env recipe, write P-GPU-1 protocol BEFORE the card) · delta-mem magnitude gates · 08-doc-to-lora Phase-B (archived; reopen tag).

## Reporting
On completing a row: delete it here, update the owning handoff + domain index, append to `progress/YYYY-MM/`; numbers use the claim grammar. Weekly freshness check must pass (>14d untouched without a `gated:` tag = violation).
