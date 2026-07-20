# Research & Evaluation — Coordination Index

**Status**: active
**Updated**: 2026-07-14
**Purpose**: dispatch surface for pre-production research, evaluation, and monitoring work. Production orchestrator changes should route through `routing-and-optimization-index.md`.

> Completed checklist and research-intake chronology was compacted to [`../archived/research-evaluation-index-history-through-2026-06-19.md`](../archived/research-evaluation-index-history-through-2026-06-19.md). Current task truth lives in the owning handoffs and machine artifacts named below.

## Current Queue

| Priority | Work | Owner / source | Gate |
|---|---|---|---|
| HIGH | N2 per-question ledger + sequential verdict readiness | [`evidence-plane-ledger-and-sequential-verdicts.md`](evidence-plane-ledger-and-sequential-verdicts.md) | Trusted-vector and seq-shadow accrual gates are SATISFIED (202/120 trusted vectors, 125/30 seq-shadow, `gaming_alarm=false`). The live gate is W8 keepable-candidate evidence + a deliberate operator cutover — do not enable authority before both. 2026-07-14: seq-fallback unblocked (orchestrator `402e461b`, trial 1346). |
| HIGH | N1+N4 evidence-plane instrument repair tails | [`evidence-plane-instrument-repair.md`](evidence-plane-instrument-repair.md) | W5 ledger-derived core_v2 is artifact/selection clean and guarded; the remaining gate is the operator E4/core era row. T3 semantics are corrected to the expert/hard workflow slice with workflow-shaped rows in the live pool while preserving T3 `core_id` evidence continuity; the latest eval-coverage report (`2439` distinct qids / `24015` scored rows over `52210` stable qids, `<=4.6715%` upper-bound coverage, repeat factor `9.8462x`) is planner pressure, not a blocker. W8 still needs live promotion-eval evidence. |
| HIGH | Eval-tower verification EV-4/5/8/9/10 tails | [`eval-tower-verification.md`](eval-tower-verification.md) | Current EV state (2026-07-14): EV-1/2/3/6 done. EV-7 RLVR export contract LANDED 2026-07-11 observe-only (orchestrator `7ee919d8`/`69445d43` + `export_rlvr_environment.py`; EV-10b consumer `fd709e4a`). EV-4/5/8 are inference-gated. EV-9 implementation is complete (orchestrator `9db36fcb` + `ce6cdf75` + `07720457` + `697ad506`: rubric metric fields, DRACO content axes, saturation screening, Bradley-Terry diagnostics, JSON-only judge prompts, deterministic T1 fallback, default-off `AUTOPILOT_RUBRIC_JUDGE_ROLES` runner) — only judge-role selection + MD-9 A/B evidence remain; production-query sampling stays gated on the F1 real-task corpus. EV-10 gate is wired default-off, awaiting deploy + A/B. Note: index priority HIGH disagrees with the owning-handoff header "Priority: MEDIUM" (header itself stale at Updated 2026-04-15) — keep HIGH here; handoff header flagged for its owner. **2026-07-20 robustness audit** → [eval-tower-loop-robustness-audit-2026-07-20.md](eval-tower-loop-robustness-audit-2026-07-20.md): EV-4 `INFRA_BLOCKED` root-caused (stale contention matrix from the 2026-07-17 vision NUMA rebind, NOT the kernel; also degrades prod cross-role concurrency) + a Phase 0→4 agent-fixable checklist (D1 loop-wedge, D4/D5 v6 pins, B1/B3 runner); EV-11b/ECE is operator-only (confidence proxy `float(correct)` → ECE constant 0.0). |
| MED | Tool-output compression P4e rollout decision | [`tool-output-compression.md`](tool-output-compression.md) | P4c done 2026-06-14, P4d done 2026-06-28 ✅. Remaining: P4e rollout decision — gated on >=100 compressed-call observations (currently 1). |
| MED | Repo-readiness remediation pickup | [`repo-readiness-scorer.md`](repo-readiness-scorer.md) | Passive AutoPilot pickup JSON is generated (`mode=advisory_only`, `authority_gate=false`); dashboard summary is live; future Fable authority launches inject the newest pickup as planner context. It remains non-authority. |
| MED | Real-task eval distribution | [`frontier-f1-real-task-corpus.md`](frontier-f1-real-task-corpus.md) | W2 compact corpus landed in orchestrator `e59577b7`: 372 training-eligible class+outcome rows, prompt text/hash refs omitted. Token telemetry for future rows landed in orchestrator `b8c8ac52`; the 2026-06-21 live token refresh clears the narrow token/class subgate (`213` training-eligible rows, `202` token payload rows, 0 prompt text). Historical conversation importer landed in orchestrator `b4b96580`; sidechain-excluded mixed source-family summary landed in orchestrator `13269679` with 1,246 prompt-free rows represented across `live_progress` and `historical_operator_conversation`. Orchestrator `40a87f3d` adds source-family weighted shares and passes the dominance gate (`historical=0.585007`, `live=0.414993`, max allowed `0.60`). Clean-window W3 EvalTower per-question ledger run COMPLETED 2026-07-07 ✅ (`real_suite_v1_eval_20260707T013009Z`: 35/50, quality 2.10, reliability 0.94); the earlier packaged concurrent-window attempt remains non-acceptance evidence. Next: AP-16 instruction-token-bloat investigation; wire the per-question ledger into promotion/regret views; formal W2 acceptance close. |
| MED | Granite embedder bench Phase B | [`granite-97m-r2-bench-plan.md`](granite-97m-r2-bench-plan.md) | A-fast corpus/harness verified and GGUF artifacts produced for Granite/e5-base/BGE-M3 on 2026-07-03; next prep is embedder-only load/vector smoke, then Phase B. No production model reload required. |
| MED | RoPE long-context matrix K-ROPE-1 | P10 below / clean-window manifest | Continue only in clean model-batched windows; worker path needs Gemma4 MTP serving fix before evidence. 2026-07-14 audit: gate is unverified-stale — re-attest worker Gemma4-MTP serving against the launch recipe before repeating the 2026-06-20 gate claim. |
| LOW | Reasoning compression tails | [`reasoning-compression.md`](reasoning-compression.md), [`memento-block-reasoning-compression.md`](memento-block-reasoning-compression.md) | Enforce path blocked until signal is predictive; Memento S2/S3 remain gated. |
| LOW | Monitoring-only model/research watches | TQ3, Log-Linear GDN, YaRN, Ouro, SLIDERS, Strand, AgentWorld, lossless-weight-compression (ZipNN/DFloat11/ZipServ · intake-815–818 · RIU tq3-quantization-evaluation.md 2026-07-14), Titans-sleep-consolidation (intake-813), sleep-time-compute (intake-819) | Do not consume inference unless the owning handoff's gate is met. Swarm dataset distillation is physically tracked in [`../blocked/swarm-dataset-distillation.md`](../blocked/swarm-dataset-distillation.md) until Strand Phase B clears. |

## Active Evaluation Packages

| Package | Current status | Next action |
|---|---|---|
| K-MEM-1 Tulving episodic | Completed/scored on `ingest_long_context` with `--server-mode --skip-moe-reduction`; research `b6edc64` packages raw run JSON/index/preflight and research `9e63af0` packages corrected scorer JSON/Markdown plus `tulving_failure_modes.md`. Scorer: `456/456` scored, missing ground truth `0`, avg F1 `0.4309`, Simple Recall `0.5530`, Chronological Awareness `0.1593`, avg decode `17.27 t/s`. Research `2eb94f8` adds `scripts/benchmark/build_tulving_followup_manifest.py` and `data/package_k/tulving_followup_20260619_141212_{manifest.jsonl,summary.md}`. | MED clean-window candidate holding the 120-row targeted follow-up manifest (dedup 2026-07-14: the former Current-Queue HIGH row was removed — run completed/scored 2026-06-20 and interpretation written; this row is the single tracking point). Treat as a mixed baseline: lexical entity/time/location recall is usable, event/detail and chronology are weak, and zero-answer hallucination checks fail. The follow-up slice has 120 ID-only rows: 40 zero-answer abstention, 40 event-content/detail recall, and 40 chronology-order cases. K-MEM no longer blocks the next throughput-sensitive lane. |
| G5 short-m@k clean-window | Frontdoor result is committed in research `7e9f67f` at `benchmarks/results/clean_window/short_mk_voting/frontdoor.json`: `status=complete`, `40` questions, `14/40` correct (`0.35` accuracy), GPQA `2/20`, MATH `12/20`, no completion errors. | Schedule remaining G5 roles only in clean model-batched windows; verify affinity/canonical preflight first and avoid blocked exact-boundary K-ROPE or stack mutation in the same window. |
| G11/G10 AA-Omniscience clean-window | Frontdoor run `20260620_035613` first exited after `24:57` with `26 completed`, `0 skipped`, and `1800 errors`; log `/mnt/raid0/llm/tmp/g11_frontdoor_20260620T035601Z.log`; partial `frontdoor_moe4_lookup_*`, `frontdoor_moe6_lookup_*`, and `frontdoor_moe8_lookup_*` files are speed-only telemetry. Triage found the 1800 errors were exactly `baseline`, `moe4`, and `moe6` quality rows falling through to missing subprocess binaries because the generated command omitted `--server-mode`. The corrected server-mode rerun completed under the same run id and is packaged in research `587c6cd`; deterministic-F1 scoring is packaged in research `92a5602` at `data/package_g/omniscience/`. Frontdoor baseline/moe4/moe6 OI is `0.2753` / `0.2725` / `0.2812`. Worker run `20260620_062750` completed with canonical preflight `data/preflight/2026-06-20_062737.json` and is packaged/scored in research `32f2c27`; worker baseline accuracy `0.1433`, avg F1 `0.2280`, hallucination rate `0.6829`, OI `0.2302`, avg decode `52.63 t/s`, labels `86` correct / `351` incorrect / `110` partial / `53` not attempted. Architect G10 run `20260620_081041` completed against resident `architect_general :8083` after canonical preflight `data/preflight/2026-06-20_081041.json`; research `b91d16c` packages/scored `600` baseline rows with accuracy `0.1317`, avg F1 `0.2103`, hallucination rate `0.4971`, OI `0.3173`, avg decode `11.05 t/s`, labels `79` correct / `259` incorrect / `101` partial / `161` not attempted. The combined factual-risk report is `ready_for_tier_update` with all expected roles present and a deterministic AA-Omniscience 4-class scoring policy accepted for role-tier recalibration. | Frontdoor, worker, and architect deterministic scorer evidence are packaged and aggregator-compatible (`3,000` total scored rows). G12 production multipliers are now updated in orchestrator to tier_1 `0.727978`, tier_2 `0.824178`, tier_3 `1.0`; mode/canary/enforce decisions remain separate telemetry gates. |
| K-ROPE-1 | Valid 4K/8K rows for frontdoor/architect/ingest and valid 16K rows for frontdoor/ingest are committed in research; worker rows are not evidence. | Fix/re-attest worker serving before counting worker RoPE cells; continue exact-boundary-safe chat-mode probes. Re-attest worker Gemma4-MTP serving against the launch recipe before repeating the 2026-06-20 gate claim (gate unverified-stale, 2026-07-14 audit). |
| EV-4 / H5 Scoring Verifiers | Adapter loads 6,701 candidate-level verifier items after research `7c11920`. | Run calibration baseline only after evidence substrate sequencing is clear. |
| K-DIV-1 | Diversity metric code exists; semantic baseline requires embedder/model serving. | Keep thresholds gated until N2 ledger vectors and validation rows exist. |
| K-SKILL-1 | Decision logic and default-off accept-path wiring exist. | Run paired skill/no-skill validation before any accept-path authority. |

## Literature Expansion Reference Rows (2026-07-08)

From 14-paper literature sweep (intake-784 through intake-797), compiled into `research/recommendations.yaml`. These rows cross-reference the recommendations to their owning handoffs.

| Rec | Priority | Topic | Target Handoff | Action |
|---|---|---|---|---|
| rec-001 | HIGH | Meta-Harness: automated benchmark design | [`meta-harness-optimization.md`](meta-harness-optimization.md) / [completed ledger](../completed/meta-harness-optimization.md) | ✅ Closed 2026-07-11: MH-10 harness-search scoping, MH-11 HTIR, and MH-12 SEAGym views landed or were scoped observe-only. Remaining validation lives in EV-10 / Package K, not Meta-Harness. |
| rec-002 | HIGH | DGM: dynamic task generation | [`frontier-f1-real-task-corpus.md`](frontier-f1-real-task-corpus.md) | Evaluate DGM methodology for corpus expansion |
| rec-003 | MED | MCE/AFlow: multi-agent consensus judging | [`eval-tower-verification.md`](eval-tower-verification.md) | Assess consensus patterns for critic pipeline |
| rec-004 | MED | SIA/ShinkaEvolve: self-improvement architectures | [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) | Review integration points; SkillsBench v3 caution applies |
| rec-005 | MED | RE-Bench: reasoning evaluation | [`reasoning-compression.md`](reasoning-compression.md) | Cross-reference for open-weight model compatibility |
| rec-006 | LOW | PaperBench: source-fidelity validation | [`minddr-deep-research-mode.md`](minddr-deep-research-mode.md) | Monitor for source-fidelity validation needs |
| rec-007 | HIGH | KernelBench: kernel-level benchmarking | [`mi210-speed-campaign-summary.md`](mi210-speed-campaign-summary.md), [`agentic-rocm-kernel-authoring.md`](agentic-rocm-kernel-authoring.md), [`v6-iqk-promotion.md`](../completed/v6-iqk-promotion.md) | Integrate into experimental kernel validation pipeline |
| rec-008 | MED | EvoScientist: autonomous research orchestration | [`tri-role-coordinator-architecture.md`](tri-role-coordinator-architecture.md) | Cross-reference memory module patterns |
| rec-009 | MED | J-space interpretability for routing | [`routing-intelligence.md`](routing-intelligence.md) | Review integration points for learned-head routing |
| rec-010 | MED | fast-rlm: RLM harness patterns | [`hermes-agent-index.md`](hermes-agent-index.md) | Harvest ACP/MCP/session management patterns |

**Key synthesis**: 3 HIGH-priority actions (rec-001/002/007), 6 MED, 1 LOW. SkillsBench v3 caution (self-generated skills net-negative -1.3pp) applies to all self-improvement/self-generation recommendations.

## Additional Active References

These handoffs are still active but currently sit behind specific evidence, model-availability, or policy gates. Keep them indexed; do not spend inference unless the owning gate is met.

| Handoff | Current role | Next action |
|---|---|---|
| [agent-file-prose-compression.md](agent-file-prose-compression.md) | Static agent-file compression pilot; Phase 1-4 are landed for the local production stack, with registry operating points applied. | Decide Phase 5 rollout scope or run the optional n=30 expansion before broad compressed-artifact rollout. |
| [integration-test-coverage.md](integration-test-coverage.md) | Active test-gap backlog after Phases 1-4 compaction. | Add narrow integration tests only when a current failing surface or coverage tranche justifies it. |
| [mathsmith-hc-formalizer-eval.md](mathsmith-hc-formalizer-eval.md) | Formalizer evaluation gate. | Check model artifacts, then run the S4 mini-protocol. |
| [per-request-reasoning-budget.md](per-request-reasoning-budget.md) | Hybrid SSM/MoE reasoning-budget investigation. | Steps 3-4 need a running server; keep code changes gated by reproduction. |
| [rao-redel-substrate-spike.md](rao-redel-substrate-spike.md) | RAO/ReDel substrate spike; Steps 1-2 executed 2026-05-19 (parity-leaning-positive, ambiguous). No activity since 2026-05-19 — 2026-07-14 audit reprioritization: **fund-or-close**. | Real open gate: naturally-delegating workload A/B (~10-60 min) + operator taxonomy-branch push decision. Note: the handoff's "DGX Spark not yet acquired" training gate is dead — MI210 gfx90a installed 2026-07-02. |
| [gpu-cot-scaffold-sidecar.md](../completed/gpu-cot-scaffold-sidecar.md) | Preliminary **pure-GPU** lane: can a small MI210-resident reasoner's injected CoT scaffold lift a CPU code worker? Control (Qwen3-4B-Thinking) vs treatment (Qwable-v1) generators; beneficiaries = code roles (coder_escalation, worker_general). | Study COMPLETE 2026-07-06 ✅; handoff archived to `../completed/gpu-cot-scaffold-sidecar.md`. Qwable standalone control is no longer pending: the 2026-07-05/06 control plus the 2026-07-17 admission work make standalone Qwable the preferred route when it can answer directly; scaffold remains fallback when the beneficiary must answer. Successor tracked in the next row. See reasoning-economics cluster below. |
| [scaffold-autopilot-cost-lever-deployment.md](scaffold-autopilot-cost-lever-deployment.md) | Successor to gpu-cot-scaffold-sidecar: DESIGN stage (created 2026-07-06), unassigned. | Gated on operator approval + live-autopilot-agent availability; do not start work without both. |
| [sliders-local-validation.md](sliders-local-validation.md) | Parked speculative SLIDERS validation. | Do not integrate before KB-RAG/default-retrieval gates justify it. |
| [strand-rust-coder-rustevo2-verification.md](strand-rust-coder-rustevo2-verification.md) | Standalone RustEvo2 verification gate. | Launch only after approval; result gates blocked swarm dataset work in [`../blocked/swarm-dataset-distillation.md`](../blocked/swarm-dataset-distillation.md). |
| [eval-benchmark-cost-reduction.md](eval-benchmark-cost-reduction.md) | Mid-range difficulty filter (intake-727) for TB Core external evals — NOT autopilot (wrong objective: ranking ≠ regression detection; stable core has only 3/50 mid-range qids). Actionable for TB Core v0.1.1 re-evaluations only: 44–70% task reduction at ρ ≥ 0.87 rank fidelity after cold-start. | Gate behind TB Core adapter build (~1d: wrap `/v1/chat/completions` in Terminus-compatible Harbor adapter) + one baseline TB Core run. Separately: use autopilot per-qid pass-rate data for question pool *curation* — rotate permanently saturated/floor qids from `simpleqa`, `coder`, `general` stable core. Carve-out (2026-07-14 audit): the Wilson/McNemar stdlib paired-significance port is an **independent non-inference operator-review item** — it is NOT gated on this Harbor/TB-Core adapter (consolidation owner: loops-and-dashboards; consumer: this handoff). |

## Backlog ROI Audit Additions (2026-07-14)

New research-eval rows from the backlog ROI audit ([`backlog-roi-audit-2026-07-14.md`](backlog-roi-audit-2026-07-14.md) §A):

- [ ] RE-1 Math-Verify scoring re-baseline (EV-11, S) — scorer flip landed 2026-07-17; EV-11a boxed-Latex parser companion fix landed 2026-07-20; fresh re-baseline waits on EV-11b ECE-binning operator decision.
- [ ] RE-2 intake-757 execution-free patch verifier (EV-12, M) — pre-gate SIGNAL module built (`src/verification/patch_pre_gate.py` `902fd303`: verdict/should_escalate policy, 11 tests); live-dispatch gate wiring DEFERRED (serving-path, freeze)
- [ ] RE-3 review-finding-F1 suite from intake-658 (EV-13, M)
- [x] RE-4 LongCoT-Mini calibration run, intake-386 (owner: `bulk-inference-campaign.md`, M) — frontdoor/worker command path, manifest/source lock, and scored-artifact scaffolding are now concretely prepared from `run_benchmark.py` (`--suite longcot_mini` on both live stack roles); score commands pass `bash -n` and artifacts are recorded under `research` as per `581940a3` and `563930a3`. ✅ 2026-07-20 (compute not launched: `OP-quiet-window` still busy)
- [ ] RE-5 Simula double-critic fold into F1-DGM scoping, intake-410 (owner: `frontier-f1-real-task-corpus.md`, S)
- [x] Wilson/McNemar stdlib paired-significance port — independent non-inference operator-review item; NOT gated on the Harbor/TB-Core adapter it currently sits behind (consolidation owner: loops-and-dashboards; consumer: [`eval-benchmark-cost-reduction.md`](eval-benchmark-cost-reduction.md)) ✅ 2026-07-17 (`eval_tower.screen_paired_arms` — exact McNemar p + per-arm Wilson CIs on discordant pairs, provenance-gated; `e93c6263`. chapter-06 doc-note residual tracked in eval-benchmark-cost-reduction L77)

## Reasoning-economics cluster — "is added reasoning worth its cost?"

These handoffs are **not independent tails** (they are also referenced individually in the queues above); they are **one question at different weights**: *does adding structured reasoning to a request beat the cheaper baseline, net of token cost?* Ordered from **removing** reasoning to **adding** it:

| Handoff | Position on the spectrum | Shared gate / status |
|---|---|---|
| [`reasoning-compression.md`](reasoning-compression.md) + [`memento-block-reasoning-compression.md`](memento-block-reasoning-compression.md) | Reasoning can be **net-negative** → compress/remove it (OPSDC: Qwen3-14B 70.0→86.1% on MATH-500 from conciseness alone). | **The cluster's binding counter-evidence.** Enforce path blocked until the signal is predictive. |
| [`per-request-reasoning-budget.md`](per-request-reasoning-budget.md) | How **much** reasoning to spend per request (hybrid SSM+MoE). | Steps 3-4 need a running server. |
| [`gpu-cot-scaffold-sidecar.md`](../completed/gpu-cot-scaffold-sidecar.md) | Can a small GPU reasoner's **injected** scaffold lift a CPU **code** worker? | Study COMPLETE 2026-07-06 ✅ (handoff archived to `../completed/`); Qwable standalone control is closed, with standalone direct-answer preferred when feasible and scaffold retained as fallback. Successor: [`scaffold-autopilot-cost-lever-deployment.md`](scaffold-autopilot-cost-lever-deployment.md) (DESIGN, operator + live-autopilot-agent gated). |
| [`minddr-deep-research-mode.md`](minddr-deep-research-mode.md) (owned by `routing-and-optimization-index.md`) | Does a **full multi-step** deep-research pipeline beat direct-answer? | **MD-9 (=J15) is the same gate as scaffold G1, one weight up.** 2026-07-14: the owning handoff's "DGX Spark" Phase-2 training gate is dead (MI210 gfx90a installed 2026-07-02) — that gate must be re-evaluated against gfx90a training viability. |
| [`rao-redel-substrate-spike.md`](rao-redel-substrate-spike.md) | Recursive-agent delegation — the heaviest long-horizon end. | Steps 1-2 executed 2026-05-19 (parity-leaning-positive, ambiguous); open gate = naturally-delegating workload A/B (~10-60 min) + operator taxonomy-branch push decision. 2026-07-14 audit: fund-or-close. |

**Shared measurement contract:** every arm compares **token-normalized** against a cheaper baseline (direct-answer / own-think / no-think) and must clear it *net of cost*. The whole cluster is bounded by the same counter-evidence — OPSDC (reasoning can harm), epiphenomenal-CoT (arXiv:2606.13603), and our `enable_thinking=false` +33 pp on Qwen3.6/122B. The **EV-9 CPU-portable DRACO/MindDR scoring contract** (Current Queue, HIGH row) is the scoring substrate for MD-9 and should also score scaffold G1 — do not build a parallel scorer.

## Dependency Graph

```text
Reasoning-economics cluster: one gate at increasing weight
  reasoning-compression (remove) -> per-request-budget (meter)
  -> gpu-cot-scaffold-sidecar (COMPLETE 2026-07-06; Qwable-standalone GPQA control pending;
     successor: scaffold-autopilot-cost-lever-deployment, DESIGN)
  -> minddr MD-9 (full pipeline) -> rao-redel (recursive)
  all vs cheaper baseline, token-normalized, via EV-9 DRACO/MindDR scoring

N1/N4 instrument repair + N2 ledger readiness
  -> EV-4/H5 calibration authority
  -> K-DIV/K-SKILL thresholds and accept-path changes

Completed K-MEM baseline
  -> interpret low Tulving score / compare follow-up cells
  -> schedule next clean-window model-batched package

Weighted real-task corpus summary + token completeness
  -> real-suite v1 curation
  -> promotion eval real-task slice
```

## Key Files

| Resource | Path |
|---|---|
| Benchmark runners | `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/` |
| Tulving results | `/mnt/raid0/llm/epyc-inference-research/benchmarks/results/runs/20260619_141212/` |
| Tulving targeted follow-up | `/mnt/raid0/llm/epyc-inference-research/data/package_k/tulving_followup_20260619_141212_manifest.jsonl` |
| F1 compact real-task corpus | `/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/real_task_corpus_20260620/real_tasks.training_eligible.compact.jsonl` |
| F1 mixed corpus summary | `/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/real_task_corpus_mixed_20260620/summary.md` |
| F1 historical conversation sources | `/mnt/raid0/llm/cloud-llm-vault/epyc/claude/`, `/mnt/raid0/llm/cloud-llm-vault/claude/`, `/mnt/raid0/llm/claude-backups/` |
| F1 historical importer smoke | `/mnt/raid0/llm/tmp/f1-historical-smoke-20260620/manifest.json` |
| Repo-readiness passive AutoPilot pickup (2026-07-06: three repos Autonomous/L5, epyc-llama L3) | `/mnt/raid0/llm/epyc-root/data/repo_readiness/repo_readiness_autopilot_pickup_2026-07-06.json` |
| Packaged G11 frontdoor raw-response run | `/mnt/raid0/llm/epyc-inference-research/benchmarks/results/runs/20260620_035613/` |
| Scored G11 frontdoor AA labels | `/mnt/raid0/llm/epyc-inference-research/data/package_g/omniscience/frontdoor_20260620_035613_aa_omniscience.jsonl` |
| Packaged G11 worker raw-response run | `/mnt/raid0/llm/epyc-inference-research/benchmarks/results/runs/20260620_062750/` |
| Scored G11 worker AA labels | `/mnt/raid0/llm/epyc-inference-research/data/package_g/omniscience/worker_general_20260620_062750_aa_omniscience.jsonl` |
| Clean-window manifest | `/mnt/raid0/llm/epyc-inference-research/docs/data/clean_window_measurement_manifest.json` |
| AA-Omniscience manifest | `/mnt/raid0/llm/epyc-inference-research/docs/data/aa_omniscience_measurement_manifest.json` |
| Eval-tower code | `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/eval_tower.py` |
| Sequential verdict code | `/mnt/raid0/llm/epyc-orchestrator/src/autopilot_core/sequential_verdict.py` |

## Reporting

After completing a row, update the owning handoff, this index, `master-handoff-index.md` if priority changed, and `progress/YYYY-MM/YYYY-MM-DD.md`. Put measured artifacts in the owning repo and cite exact run directories or report filenames.

## Progress checklist

- [ ] HIGH N2 per-question ledger + sequential verdict readiness — accrual gates satisfied (202/120, 125/30, gaming_alarm=false); live gate = W8 keepable-candidate evidence + deliberate operator cutover (seq-fallback unblocked 2026-07-14)
- [ ] HIGH N1+N4 evidence-plane instrument repair tails; W8 needs live promotion-eval evidence
- [ ] HIGH Eval-tower tails: EV-4/5/8 inference-gated; EV-9 judge-role selection + MD-9 A/B; EV-10 deploy + A/B (EV-1/2/3/6 done; EV-7 landed 2026-07-11 observe-only)
- [ ] MED Tool-output compression P4e rollout decision (>=100 compressed-call observations, currently 1); repo-readiness remediation pickup
- [x] MED Real-task eval distribution W3 EvalTower per-question ledger run ✅ 2026-07-14 (completed 2026-07-07: `real_suite_v1_eval_20260707T013009Z`, 35/50, quality 2.10, reliability 0.94)
- [ ] MED F1 next: AP-16 instruction-token-bloat investigation + wire per-question ledger into promotion/regret views + formal W2 acceptance close
- [ ] MED Granite embedder bench Phase B; RoPE K-ROPE-1 matrix (needs Gemma4 MTP serving fix; re-attest vs launch recipe before repeating 2026-06-20 gate claim)
- [ ] LOW Reasoning-compression tails; monitoring-only watches (TQ3, YaRN, swarm/Strand, etc.)
