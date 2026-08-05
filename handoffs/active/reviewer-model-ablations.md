# Reviewer Control Plane — Registry-Driven Model-Role Ablation Tournament (H5)

**Status**: active — M3 "compared" milestone; GATED on H4 instrument (P-REV-1) + H6 arms + operator bench windows
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: benchmark_methodology, agent_architecture, routing_intelligence
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related**: [`reviewer-calibration-accounting.md`](reviewer-calibration-accounting.md) (the instrument), [`glm52-reviewer-capability-gates.md`](glm52-reviewer-capability-gates.md) (A4 arm gates), [`autopilot-control-plane-integration.md`](autopilot-control-plane-integration.md) (screening-tier driver), [`mi210-big-model-and-acceleration-roadmap.md`](mi210-big-model-and-acceleration-roadmap.md) (GPU arms), [`architect-model-selection-bench.md`](architect-model-selection-bench.md) (sibling — the architect-role model-selection bench, same objective-scored-only discipline)
**Repo**: `epyc-orchestrator` + `epyc-inference-research`

## Objective

Answer the model-role question empirically — which (architect, reviewer, grading-model) assignment maximizes calibrated review value per token — via a **registry-driven staged tournament** over the ~240-model registry, not a fixed condition table (operator 2026-07-16: the report's 7-row matrix is an example only).

## Thesis

Three stages: (1) **pool generation** — architect × reviewer × grader pools drawn from `model_registry.yaml` by capability/speed tier with pruning rules (RAM/VRAM fit, t/s floor, quality floor from existing benches, cross-family preference; staged candidates include Hy3-295B-IQ1M, MiniMax-M2.7, DeepSeek-V4-Flash, Qwen3-Next-80B, gemma-4-31B, and Qwen3.6-27B; Bonsai tier-C is opt-in/reopen-only and excluded from default staging until a named quality/protocol fix clears the strict-output blocker); (2) **screening** — cheap small-n sweeps over many pairings, autopilot-driven (H8) on a corpus-v1 subset via eval-tower T0/T1; (3) **confirmation** — full paired N≥100 P-REV-1 runs only for Pareto-promising pairs. Family-preference/collusion is **measured as a covariate, not assumed** (direct measurements found it weak, −0.9..+3.5pp — intake-837; the stronger prior lives in Panickssery 2404.13076, unverified locally).

## Prioritized Task List

**2026-07-19 operator priority — fast-track anchor comparison on the now-decision-grade C-CRAB corpus.** The mechanical accept-oracle relabel (`GC-shadow-repair4b.2c`, [`glm52-reviewer-capability-gates.md`](glm52-reviewer-capability-gates.md)) made the C-CRAB P-REV-1 slice decision-grade, and **GLM-5.2-IQ2 (arm A4) FAILED admission on it** — `FA 41.7%`, `FR 25.0%`, **AUC 0.509 (≈ random)**, 2026-07-19. Before the full tournament, run the cheap high-value anchor cut on that SAME corpus. **Hard requirement (operator): every reviewer arm below runs MI210-hosted (GPU: `-ngl 99 -dev ROCm0`), NOT CPU — grammar/schema on.** The whole point is a *fast* slate we can iterate; GLM ran CPU-IQ2 at ~2.5 t/s, these run at 40–100 t/s on the card. Three distinct arms:

- [x] **RM-2.fast — Qwen3.6-27B reviewer arm on the decision-grade C-CRAB P-REV-1 corpus** (operator-requested 2026-07-19): ran Qwen3.6-27B dense Q8 on MI210 through the same P-REV-1 runner/prompt/schema family and identical `48`-row slice. Result: `FA 54.2%`, `FR 16.7%`, `AUC 0.503`, `ECE 0.316`, parse `0.0%`, median row wall `6.2s`; artifact `epyc-inference-research/data/reviewer_model_ablations/rm2-fast-qwen36-27b-q8-ccrab-p-rev1-20260719T162109Z`; summary `epyc-inference-research/docs/data/reviewer_model_ablations_rm2_fast_ccrab_p_rev1_20260719.md`. Verdict: faster, but not better than GLM; over-approves and remains random by AUC, so this does **not** decouple v7. ✅ 2026-07-19

- [x] **RM-2.fast-b — Harnessed-small-model reviewer arms vs the big quantized model** (operator-requested 2026-07-19): the strategic question is *large quantized model (GLM-5.2-IQ2, FAILED) vs efficiently-harnessed small models*. On the SAME decision-grade C-CRAB slice + runner, added these reviewer arms alongside RM-2.fast's plain 27B and reported matched `FA/FR/AUC/ECE` vs GLM's `41.7/25.0/0.509`: ✅ 2026-07-19
  - **(a) Qwable standalone** (35B-A3B IQ4_XS, ~90–100 t/s MI210 — the strongest cheap local reasoner). **This is the primary harnessed-small candidate:** it historically **dominated** the Qwable→beneficiary scaffold on GPQA (77% vs 73%, 2026-07-05, [`../completed/gpu-cot-scaffold-sidecar.md`](../completed/gpu-cot-scaffold-sidecar.md)).
  - **(b) Qwen3.6-27B + Qwable CoT scaffold** (the explicit coupling the operator asked about). **Caveat from past evidence:** the Qwable→gemma-26B scaffold was FALSIFIED (net −3, quality loss) because the beneficiary was already as strong a reasoner as Qwable → expect **Qwable-standalone ≥ 27B+scaffold** unless patch-review behaves differently from GPQA. Test it to confirm on this task, not assume.
  - **Outcome:** Qwable standalone was fast but failed (`FA 54.2%`, `FR 45.8%`, `AUC 0.438`, `ECE 0.441`, median `2.1s`; artifact `data/reviewer_model_ablations/rm2-fast-b-qwable-iq4xs-ccrab-p-rev1-20260719T162712Z`). Qwen+Qwable scaffold improved the FA/AUC shape (`FA 33.3%`, `FR 41.7%`, `AUC 0.659`, `ECE 0.315`, median `6.5s`; artifact `data/reviewer_model_ablations/rm2-fast-b-qwen36-27b-q8-plus-qwable-iq4xs-scaffold-ccrab-p-rev1-20260719T162958Z`) but is still not role-ready because FR and raw errors exceed GLM. Decision-grade conclusion: no tested small/fast arm cleanly beats GLM; keep reviewer choice open and pursue A3/external/SWE or a scaffold repair, not blind v7 decoupling.

**2026-07-19 GLM disposition consumed.** H6/GC-external-1e now routes production
patch-review selection away from GLM on the current policy: GLM failed C-CRAB hard negatives,
external JudgeBench/SWE evidence is positive but partial, and RM-2.fast did not find a clean
small replacement. The next H5 progress is therefore not another unchanged GLM/Qwable/Qwen
rerun; it is the remaining anchor/floor set and the screening protocol.

- [x] **RM-1 — Pool-generation script** ✅ 2026-07-17 (`scripts/analysis/reviewer_pool_gen.py`; live run: 157 roles → pools 68/77/65 → 5,236 pairings; anchors A0/A1/A3/A4 forced-present, A4 cross-family-flagged; deterministic w/ registry+config sha256 provenance; 19 tests) with pruning rules + provenance (registry rev, pruning config hash); emit the candidate pairing list.
- [x] **RM-1a — Bonsai Q1 default-staging stop**: `epyc-orchestrator` commit `d30593a2` removes Bonsai Q1_0 from `reviewer_pool_gen` `DEFAULT_STAGED_KEYS`; Bonsai remains opt-in/reopen-only until a named quality/protocol fix clears the strict-output blocker. ✅ 2026-07-19
- [ ] **RM-2 — Anchor arms (guaranteed confirmation-tier)**: A0 gates-only (objective-verifier floor); A1 self-review (status quo alias); A3 same-family GPU heavyweight (122B-IQ2 resident, 43.7 t/s, grammar mandatory); A4 cross-family GLM-5.2-IQ2 CPU (target); A4g +hot-expert offload (skew-profile-gated); Ref external judge-of-judge (approved bounded: pinned model-id+date, ~100 sampled decisions, budget-capped).
  - [x] **RM-2.next — Complete non-GLM anchors after GC-external-1e**: A0/A1 floor extraction and A3 same-family GPU heavyweight are complete on the decision-grade C-CRAB slice. A4 is recorded failed on the current policy; A4g still requires an expert-routing-skew profile plus a concrete GLM repair hypothesis before spending MI210/CPU time. ✅ 2026-07-19
    - [x] **A0 objective-verifier floor materialized on the matched C-CRAB P-REV-1 slice**: no-inference oracle ledger over the same `48` row ids (24 hard accepts + 24 hard negatives) scored `FA 0.0%`, `FR 0.0%`, `ECE 0.000`, `Brier 0.000`, parse `0.0%`; AUC is undefined because all decisions are correct. Artifact: `epyc-inference-research/data/reviewer_model_ablations/rm2-next-a0-objective-floor-ccrab-p-rev1-20260719T205208Z`; report: `epyc-inference-research/docs/data/reviewer_model_ablations_rm2_next_ccrab_p_rev1_20260719.md`. ✅ 2026-07-19
    - [x] **A3 same-family GPU heavyweight ran on MI210**: Qwen3.5-122B-A10B `UD-IQ2_M`, `-ngl 99 -dev ROCm0`, same P-REV-1 runner/prompt/schema and matched C-CRAB slice. Result: `FA 12.5%` (`3/24`), `FR 58.3%` (`14/24`), `AUC 0.513`, `ECE 0.302`, `Brier 0.319`, parse `0.0%`, median row wall `5.5s`, server decode `43.89 t/s`. This materially reduces false accepts versus GLM but rejects too many good patches, so it is not a production reviewer replacement. Artifact: `epyc-inference-research/data/reviewer_model_ablations/rm2-next-a3-qwen35-122b-iq2-ccrab-p-rev1-20260719T204845Z`. ✅ 2026-07-19
    - [x] **A1 status-quo self-review live run**: Qwen3.5-122B `UD-Q4_K_M` CPU self-review ran through the same P-REV-1 runner/prompt/schema and matched C-CRAB slice. Result: `FA 45.8%` (`11/24`), `FR 41.7%` (`10/24`), `AUC 0.463`, `ECE 0.385`, `Brier 0.397`, parse `0.0%`, median row wall `41.4s`, total wall `2164.234s`. Verdict: parse-clean but worse than GLM and not a production reviewer replacement. Artifact `epyc-inference-research/data/reviewer_model_ablations/rm2-next-a1-architect-statusquo-ccrab-p-rev1-20260719T210513Z`. ✅ 2026-07-19
- [ ] **RM-3 — Screening-tier protocol**: small-n, per-pairing FA/FR/CR estimates with wide CIs; promotion rule to confirmation tier (Pareto on quality-vs-cost); driven by the H8 autopilot action, respecting no-concurrent-inference + placement-queue-not-/chat discipline.
  - [x] **RM-3a — Matched C-CRAB P-REV-1 row-id-bound dry-run queue ✅ 2026-07-19**: `epyc-orchestrator` runner now accepts `--row-ids`, records row-id filter provenance in dry-run queues, filters live execution to that exact allowlist, and applies CLI `--max-pairings` after priority ordering. Focused runner tests passed (`32`). Artifact: `epyc-orchestrator/orchestration/reports/rm3_ccrab_p_rev1_screening_dryrun_20260719T215914Z/` with `64` priority-resolved jobs from `6525` pairings, `per_pairing_n=12`, `row_id_filter_n=48`, placement-queue transport, and no inference.
  - [x] **RM-3b — Live screening bridge**: `epyc-orchestrator` now routes `screening_tier_driver` live execution (only with `dry_run=false` + `AUTOPILOT_SCREENING_TIER_INFERENCE=1`) through `screening_tier_runner.run_screening_tier`; the runner's default live probe reuses the P-REV-1 direct corpus prompt, binary ReviewDecision JSON schema, parser, forced-direct `/chat` path, and placement-queue priority/workload stamps instead of the old free-text approve/reject prompt. Focused validation passed (`190` tests + ruff + py_compile). ✅ 2026-07-19
  - [x] **RM-3c — First live screening batch ✅ 2026-07-19**: ran the first routable live-stack subset from the `64` priority-resolved jobs using the RM-3 live bridge, same matched C-CRAB P-REV-1 row-id allowlist (`48` rows), `n=12` per pairing, forced direct `/chat` with background/eval-batch stamps, and the binary ReviewDecision schema. Scoped stack: API `8000` + frontdoor full server `8070` serving `frontdoor` and `coder_escalation` (`Qwen3.6-35B-A3B-MTP-Q8_0`, CPU-only stack launch, `draft-mtp`); AutoPilot was not restarted. Result leaderboard: `frontdoor` FA `16.7%`, FR `50.0%`, consistency `66.7%`, mean row latency `26.8s`; `coder_escalation` FA `25.0%`, FR `75.0%`, consistency `58.3%`, mean row latency `24.1s`. Artifact: `epyc-orchestrator/orchestration/reports/rm3_ccrab_p_rev1_screening_live_frontdoor_slice_20260719T221931Z/`. Verdict: live forced-direct P-REV screening works mechanically, but this does **not** prove the stricter placement-queue-not-/chat discipline, and neither frontdoor-served role is a confirmation-tier candidate from this observation-grade slice.
  - [x] **RM-3d — Transport metadata repair ✅ 2026-07-19**: `screening_tier_runner.py` now keeps dry-run/planned jobs as `placement_queue` while live execution rows explicitly record `transport=forced_direct_chat`, `planned_transport=placement_queue`, `force_mode=direct`, and `uses_chat_endpoint=true`. This prevents RM-3c-style forced-direct observations from being misread as true placement-queue evidence. Focused validation: `uv run pytest -q tests/test_screening_tier_runner.py` (`33 passed`) plus `python3 -m py_compile scripts/autopilot/screening_tier_runner.py`. True placement-queue execution remains a stronger future transport gate, but metadata can no longer overclaim it.
- [ ] **RM-4 — Confirmation-tier protocol**: fully paired (same tasks/prompts/grammar/stop/verifier budget), N≥100/arm, paired flips via `sequential_verdict.quality_trial_statistic`, Holm across metric families; per-domain reporting.
- [ ] **RM-5 — Bias-robustness probe set**: the 6 content-bias injections (authority, self-declared correctness, renaming, reverse-authority, misleading-task, illusory complexity) as a held-out probe → per-reviewer **robustness rate** as a selection axis (small judges more fragile); blinding/randomization controls baked into the harness (sanitized packages, no reference-comparison mode without swap-augmentation).
- [ ] **RM-6 — RA-8 field-order A/B** (evidence-first vs verdict-first GBNF) on the leading arm — opposing hypotheses on record (intake-836 vs intake-837).
- [ ] **RM-7 — With-vs-without verifier-request access** ablation on the winning pair (isolates contextual verification vs second-opinion effect).
- [ ] **RM-8 — Report + registry annotation**: winners' calibration profiles into model registry `measured:` fields; publish claims in P-REV-1 grammar only.
- [ ] **RM-9 — (deferred, LOW) A5 reviewer-as-architect** (GLM-5.2 solo) — only after A4 results justify it.
- [ ] **RM-10 — Run a mindfulness-only metacognitive prompt ablation, not a superalignment test.** Add three
  matched prompt arms to the confirmation protocol on the same leading reviewer configuration: the current
  framing-neutral prompt, a matched-length neutral reflection/self-check prompt, and a mindfulness-only
  present-attention/self-monitoring prompt. Hold candidate rows, grammar, field order, token budget, sampling,
  verifier access, and seeds fixed; score with objective/dual-gold outcomes plus a blinded cross-family or
  human-owned sample, reporting FA, FR, calibration, consistency, latency, and style/rubric leakage. Exclude
  emptiness, non-duality, moral-goal substitution, constitutional relaxation, and any instruction that can
  weaken MEASUREMENT.md, operator authority, safety rules, or frozen-kernel constraints. Ignore the source's
  current effect sizes and do not describe any result as superalignment evidence.

## Dependency Graph

```text
H4 P-REV-1 + corpus v1 → RM-1 → RM-3a dry-run queue ✅ → RM-3b live screening bridge ✅ → RM-3c first live batch ✅ → RM-3d metadata repair ✅ → RM-4 confirmation → RM-7 → RM-8
RM-2 anchors: A0/A1/A3/A4 are closed evidence; A4g requires a concrete GLM repair/skew rationale before reopening; Ref needs an operator budget/window.
RM-5, RM-6 fold into RM-4 protocol. Operator bench windows gate all inference-heavy runs.
```

## Cross-Cutting Concerns

1. **Single-card contention** — A3/A4g arms use the MI210; sequence behind the parallel session's admission smokes + the operator's GPU bets 1→4 ordering.
2. **Latency accounting** — parallel-reviewer wall-clock models as SUM not MAX on this host; per-arm cost reported alongside quality (keeps "stronger" arms honest).
3. **Saturated-suite hazard** — screening on journal-derived items must include near-miss/ambiguous rows, or arms will tie at ceiling (the corpus exists precisely to avoid this).

## Key Files / Surfaces

- `epyc-inference-research/orchestration/model_registry.yaml` (pool source; `measured:` target)
- H4 ledger + `reviewer_calibration_report.py`; `src/autopilot_core/sequential_verdict.py`
- eval tower T0/T1 (screening); H8 autopilot action (driver); `scripts/autopilot/screening_tier_runner.py`

## Reporting Instructions

Flip checkboxes `✅ YYYY-MM-DD`; screening leaderboards + confirmation results recorded here; winners update H0 + registry; NO claim leaves this handoff without P-REV-1 citation; bench windows requested via OP bundle.

## Evidence Base (intake)

intake-837/838 bias probes + family-preference-as-covariate · intake-836 big-model FR priors + IQ2 quant caveat · intake-834 grading-model insensitivity (2.4pp) · intake-846 fidelity-over-fan-out · audit doc 2026-07-16 · IQ2==Q4 parity (n=212, Δ0.0pp; workspace-root iq2_parity_results.jsonl).
