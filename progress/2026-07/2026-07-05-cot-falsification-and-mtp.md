# 2026-07-05 — MI210 campaign: CoT single-shot scaffold FALSIFIED (both regimes) + MTP-on-GPU-MoE re-checked STILL NEGATIVE

Self-contained wrap-up for the MI210 "reasoning-economics" slice that landed since the previous wrap-up (`1bedcf60`, 2026-07-05, the residency-ladder + CoT-reframe entry `2026-07-05-mi210-residency-and-cot-reframe.md`). This entry continues the CoT-scaffold sidecar story from that reframe to its **experimental close**, records the design-dialogue that settled the lane's objective + architectural end-state, and captures a spec-dec kernel side-result (native-MTP-on-GPU-MoE re-checked — **still net-negative** at production sampling; a temp-0 A/B briefly and spuriously read positive and was corrected the same session). All work was committed inline to the owning handoffs; this is the narrative + evidence index. **Every GPU number here is an OBSERVATION** (single MI210, serial, contended host, single-sample seed=42, no `P-GPU-1` protocol per MEASUREMENT.md) — usable for direction, never decision-gating. All items experimental-HOLD; operator-only authorizes any production push, CPU-correctness-gated first.

## Context

The prior entry (`2026-07-05-mi210-residency-and-cot-reframe.md`) left the CoT-scaffold sidecar lane in a **re-scoped, NOT-closed** state: an operator reframe had corrected the intermediate "marginal / config-fragile" read into a **CONDITIONAL RESCUE lever** (value = rescue rate on tasks nothink FAILS, not token-efficiency vs nothink's average), and a re-scoped **rescue-rate experiment was RUNNING on the MI210**. This session ran that experiment to completion, ran the favorable-regime follow-up, held the design-dialogue that fixed the objective, and closed the single-shot lane. Separately, a spec-dec kernel re-measurement re-checked the native-MTP-on-GPU-MoE verdict — it remains net-negative.

## What landed this session

### 1. Fork-4 RESOLVED — external generators only, in-house-reasoner build PARKED (commit `5cf40378`)
Operator decision (2026-07-05): **no training now.** All CoT-scaffold spec strategies use `Qwable-v1` (IQ4_XS + Q8_0 on disk) or the **fable5-distilled 4B** (`Qwen3-4B-SFT-Fable5-Glint`, q8_0 GGUF); vanilla `Qwen3-4B-Thinking` stays only as the CONTROL bar. The **in-house-reasoner build is PARKED** as a documented future idea: the operator confirms the MI210 *probably could* train (ROCm/PyTorch on gfx90a) but does not wish to explore it now; a revival would also need prompt→thinking pair reconstruction from the session vault (the local CoT corpus is thinking-text-only, 0 Fable-5).

### 2. Formal objective recorded, then CORRECTED to autopilot's EXISTING objective (commits `daf4ae25`, `b859eb9e`, `7c72b601`)
- **`daf4ae25` — formal objective.** The lane's value is NOT "scaffold beats nothink"; it is **minimize BLENDED GPU+CPU wall-clock s.t. quality ≥ quality-parity(ownthink)**. Cost model:
  ```
  T_scaffold = N_gen/r_GPU(gen) + N_gen/r_CPU_prefill(ben) + N_ans/r_CPU_decode(ben)
  T_ownthink = (N_reason + N_ans)/r_CPU_decode(ben)
  ```
  The win comes from the `r_GPU/r_CPU` ratio (fast small GPU model vs slow large CPU model): moving reasoning off CPU-decode pays even at higher token count, as long as the beneficiary's own CPU-decode `N_ans` collapses (interim CONFIRMED it does — scaffold-beneficiary answers ran 5–150 tok vs nothink ~1000). Lever search space: `generator {4B, fable5-4B, Qwable} × depth {setup-only, full} × mode {advisory, prefix} × gen-budget × per-task-class gate`. Interim structural finding: a generator **weaker** than the beneficiary's own reasoning drags quality *below* nothink (imports wrong conclusions) → the generator must ≳ the beneficiary, OR the scaffold must be setup-only/advisory.
- **`b859eb9e` — recursive loop as architectural end-state.** The single-shot scaffold generalizes to an interleaved **GPU-reason ↔ CPU-execute LOOP** (GPU reasoner proposes next step → CPU nothink executes → reasoner grounded by concrete output → recurse). This is a device-split planner-executor = the stack's existing `graph_router` `react`/`repl` mode with the THOUGHT step pinned to the GPU and ACT to the CPU. Key insight: the loop's **execution-feedback self-correction attacks single-shot derailing** — a weak reasoner's error is bounded per-round and corrected by execution feedback instead of compounding, so the loop *may* rescue the weak-generator case single-shot cannot (HYPOTHESIS, untested). Cost = multi-round sum with a growing per-round prefill tax → KV-persistence on the CPU beneficiary + shipping only deltas bounds it.
- **`7c72b601` — CORRECTION: this IS autopilot's existing objective, not a future one.** Verified `safety_gate.objectives() = (quality, speed, -cost, reliability)` is a 4D Pareto (`pareto_archive.py`), and `q_reward.compute_reward` already penalizes wall-clock (`cost_ratio = actual_elapsed/expected_elapsed`, applied ONLY to correct answers = minimize-cost-subject-to-correctness). So autopilot **already** optimizes blended wall-clock at quality-parity. The work is NOT building a cost-aware optimizer — it is **registering the scaffold as a LEVER** (`capability_registry` `prompt`-kind row, beside `per_role_enable_thinking`) that the existing 4D-Pareto + cost-penalized reward + episodic gating evaluate. The recursive loop = one more action in the same optimizer. This corrects the prior "future autopilot objective" framing.

### 3. RESCUE-RATE experiment RESULT — single-shot scaffold on the strong 35B beneficiary FALSIFIED (commit `2ce3271b`)
Suite `mode_advantage_hard` (60q: code/comp/reason/synth ×15; nothink UNSATURATED at 41/60). Beneficiary 35B-A3B-Q8 (GPU). Generators: 4B-Thinking (control), Qwable-v1 IQ4 (distilled). Metric = rescue rate (nothink-fails → scaffold-completes) + 0-regression gate. OBSERVATION (single-sample seed=42).

| arm | ALL | code | comp | reason | synth | vs nothink |
|---|---|---|---|---|---|---|
| nothink | 41/60 | 14 | 9 | 4 | 14 | — |
| scaffold-4B | 32/60 | 10 | 8 | 1 | 13 | **0 rescue / 9 regr / net −9** |
| scaffold-Qwable | 39/60 | 13 | 8 | 3 | 15 | **2 rescue / 4 regr / net −2** |

- **Distillation CONFIRMED:** Qwable fixes 9 of the 4B's derails (4B fixes only 2 of Qwable's); net −2 vs −9. A strong same-class generator derails far less — the distillation thesis holds as a *component*.
- **But single-shot scaffold is NET-NEGATIVE even with Qwable.** comp+reason slice (nothink fails 17/30): 1 rescue, 3 regressions; on reason alone Qwable 3/15 < nothink 4/15.
- **Structural reason:** the 35B beneficiary is ALREADY as strong a reasoner as Qwable (a distilled 35B) → equal-strength injected reasoning adds no capability → nothing to rescue, only derail. A scaffold can rescue ONLY if the generator > the beneficiary's own reasoning.
- **CPU-cost mechanism works** (scaffold-Qwable beneficiary 641 tok/q vs nothink 1071 = −40% CPU decode) **but at a quality loss** → not favorable on this pairing.
- **VERDICT (single-shot, strong beneficiary): FALSIFIED** (net-negative even distilled).

### 4. Favorable-regime follow-up ALSO falsified → single-shot lane CLOSED (commit `6b8d39b2`)
The only remaining single-shot hope was the favorable regime **generator > beneficiary**. Ran Qwable → **gemma-4-26B** (`-fa on`, format-native injection):
- gemma-nothink 39/60 vs +Qwable-scaffold 36/60 = **net −3; 1 rescue of 21 available nothink-failures (5%), 4 regressions**; clean injection (no channel leak); **no CPU savings** (gemma 917 vs 920 tok/q).
- Combined with the 35B result, **single-shot CoT-scaffold injection is FALSIFIED as a rescue lever in BOTH regimes** (gen≈beneficiary AND gen>beneficiary).
- **Mechanism:** *transplanted reasoning does not transplant capability* — handing a model a pre-made reasoning trace neither unlocks tasks it fails (20/21 gemma-failures unrescued) nor is cost-free (occasional derail). Independent of generator/beneficiary strength ordering.
- **LANE STATUS: single-shot CLOSED (clean negative, both regimes).** The only untouched mechanism = the **recursive reason↔execute LOOP** — a fundamentally different and bigger build, prior LOWERED by these negatives, treated as a **separate OPERATOR-GATED investment** (not autonomously spun up). The distillation-adds-value + format-native-injection findings **stand as components** IF the loop is ever built. Speed levers (residency / kernel) are the clearer path to the overarching goal.

### 5. Driver-optimization saga (recorded inline in the rescue-rate result)
The initial rescue-rate run was misconfigured `-fa off` → ~12 t/s, which made Qwable look "too slow to be practical." Corrected to `-fa on` → ~92 t/s on both models; **Qwable IQ4 decodes ~96 t/s = as fast as the beneficiary**. The "Qwable too slow" read was a `-fa` misconfig, NOT the model. A parallel worry ("we're missing native MTP on the GPU-MoE beneficiary, so speed is understated") was investigated and is addressed by finding 6 below — MTP-on-GPU-MoE is **net-negative** for this beneficiary, so its absence was not the bottleneck.

### 6. findings-05c L8 — MTP-on-GPU-MoE re-checked: STILL net-negative (−6.8% at production sampling) (commits `93353884` → `ec2bda8e`)
A temp-0 A/B of the 35B-A3B experimental build first read **MTP-on 91.2 vs off 85.6 t/s = +6.5%** and was recorded as a sign-flip (commit `93353884`). **That reading was a methodology artifact and was corrected the same session (commit `ec2bda8e`):** greedy (temp-0) decoding spuriously inflates MTP draft-acceptance. Re-measured at **production sampling (temp 0.6, seed 42, per `f4a8a3ca` in the experimental build): MTP-on-GPU-MoE is −6.8%** (87.9 vs 94.3 t/s, draft acceptance 0.57, mean-accept-len 3.3) — **STILL NEGATIVE.** `de447119f` (+17.4% single-stream MTP-verify MMQ dispatch) **NARROWED the penalty (−12% → −6.8%) but did NOT flip it.** MTP remains a **net-negative** lever for GPU-resident qwen35moe. Do NOT write "+6.5%" or "flipped positive" — the corrected annotation is on findings-05c §5 (L8 "FLIPS SIGN") line. Lesson (new memory `feedback_production_sampling_seed_not_temp0`): never A/B spec-dec at temp 0 — greedy inflates acceptance; measure at production sampling (temp 0.6 + seed).

## Design-dialogue outcomes (summary)

| Question | Resolution |
|---|---|
| What is the lane's objective? | Minimize **blended GPU+CPU wall-clock at quality-parity** — NOT "scaffold beats nothink." |
| Is that a new optimizer to build? | **No** — it IS autopilot's existing 4D Pareto (`quality, speed, −cost, reliability`) + `q_reward` cost penalty. The scaffold is a **LEVER** (`capability_registry` prompt-kind), not a new objective. |
| Does single-shot injection work? | **No — FALSIFIED in both regimes.** Transplanted reasoning ≠ transplanted capability. |
| What is the untouched bet? | The **recursive reason↔execute loop** (execution-feedback self-correction) — **operator-gated**, prior lowered by the single-shot negatives. |
| In-house reasoner? | **Parked** (Fork-4); external generators only for now. |
| What stands regardless? | Distillation-adds-value (Qwable > vanilla 4B) + format-native reasoning-slot injection (+11pp / 0-regressions) — components IF the loop is built. |

## Commits (this session, epyc-root, branch spec-dec-mtp-refresh-2026-06-22)

| Commit | Summary |
|---|---|
| `5cf40378` | CoT Fork-4 RESOLVED: external generators only (Qwable + fable5-4B); in-house build PARKED (operator: MI210 probably can train but not exploring now) |
| `daf4ae25` | CoT formal objective recorded — minimize blended GPU+CPU wall-clock at quality-parity + lever search space + weak-generator-derails structural finding |
| `b859eb9e` | CoT recursive GPU-reason↔CPU-execute loop recorded as architectural end-state (execution-feedback self-correction hypothesis) |
| `7c72b601` | CORRECTION: blended cost IS autopilot's EXISTING 4D-Pareto objective; scaffold = a LEVER in it, not a new optimizer |
| `2ce3271b` | RESCUE-RATE RESULT: single-shot scaffold on strong 35B beneficiary FALSIFIED (net-negative even distilled); distillation confirmed; `-fa` speed misconfig corrected |
| `6b8d39b2` | Single-shot lane CLOSED: Qwable→gemma-26B (generator>beneficiary) ALSO falsified (net −3, 1/21 rescue); transplanted reasoning ≠ capability; recursive loop = only open bet |
| `93353884` | findings-05c L8: temp-0 A/B read MTP-on-GPU-MoE as +6.5% (91.2 vs 85.6 t/s) — **SUPERSEDED by `ec2bda8e`** |
| `ec2bda8e` | CORRECT: MTP-on-GPU-MoE STILL NEGATIVE at production sampling (−6.8%, 87.9 vs 94.3 t/s, accept 0.57); the temp-0 +6.5% was a greedy-inflated-acceptance artifact; `de447119f` narrowed −12%→−6.8% but did NOT flip. New memory `feedback_production_sampling_seed_not_temp0` |

Wrap-up doc commit (this progress entry + index/handoff/wiki reconciliation) added separately this session (hash in the wrap-up report).

## Deferred / open (next session picks up)
- **Recursive reason↔execute loop** — the ONLY untouched CoT mechanism; **operator-gated** (bigger build, prior lowered by the single-shot negatives). Do not autonomously spin up. Distillation + format-native-injection stand as its components. (`gpu-cot-scaffold-sidecar.md`)
- **MTP-on-GPU-MoE stays a no-go** — re-checked net-negative (−6.8% at production sampling); the earlier temp-0 +6.5% was a greedy-inflated-acceptance artifact (`ec2bda8e`). findings-05c §5 (L8) now carries the corrected −6.8% annotation, but the older **−12%** figure still appears in the §3.3 category-matrix cell (L8 row), the §5 "do-first" list, and the §evidence-plane summary. The sign is unchanged (still negative), so no verdict flip is needed; the operator may want to refresh those −12% magnitudes to −6.8% for consistency — flagged, not overwritten this wrap-up (measurement-adjacent category verdict).
- **Roadmap Axis-A/B gating experiments** (unchanged from prior entry): expert-routing-skew profile (offload/REAP viability), GPU-draft N5 feasibility + quant-asymmetric self-spec α, GLM-5.2 endgame (DSA-gated, offload-mandatory).
- Scratch experiment drivers (`iq2_parity_eval.py`, `iq2_arch_eval.py`, `iq2_*_results.jsonl`, `iq2_server.*`) remain uncommitted in the repo root — transient, not code artifacts.

## Memory
New memory file `feedback_accuracy_token_tradeoff_rescue_metric` (recorded in the prior entry's reframe, already indexed in MEMORY.md) is the load-bearing measurement-discipline takeaway: an accuracy-vs-token feature is gated by **rescue rate on tasks the cheap path fails**, not token-efficiency vs the cheap path's average. The single-shot falsification is the empirical closure of that thesis for the injection-based mechanism (the rescue rate itself was too low to pay).

## Wiki
This session's slice (CoT single-shot falsification + MTP-on-GPU-MoE re-check-still-negative) was compiled into `wiki/hardware-optimization.md` as an extension of the existing review-flagged 2026-07-05 subsection. The source scanner reports **47 new sources** (up from 43), spanning parallel autopilot / evidence-plane / dashboard sessions; a full cross-session compile is out of scope for this focused wrap-up, so `.last_compile` was **NOT** touched (advancing it would hide the other sessions' un-compiled sources from the next incremental scan — same precedent as prior wrap-ups).
