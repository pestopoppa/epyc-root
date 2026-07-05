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

---

## Update (continued 2026-07-05, post-`78428cd2` wrap-up) — MTP CONVERGED to ~neutral at production temp · spec-dec-temp SOTA · stream-K ALREADY-shipped · self-debug loop 4% · CoT research: scaffold dead-end confirmed, verifier/selector = the forward path

The 78428cd2 wrap-up (above) closed the CoT single-shot lane and recorded MTP-on-GPU-MoE as "still-negative (−6.8%)." The campaign continued past that wrap-up (four more commits, `7369b0ec`→`752408bc`) and produced a **cleaner convergence on both fronts plus the major CoT research result.** This continuation supersedes two conclusions above — **the −6.8% MTP verdict** (that was the *temp-0.6 point of a temp curve*, not "production sampling") and **the "recursive loop = only open bet" framing** (the recursive/self-debug loop was tested and is ALSO weak; the real forward path is verifier/selector). Same measurement caveat: every GPU number is an OBSERVATION (single MI210, serial, seed=42, no `P-GPU-1`), usable for direction only.

### 7. MTP-on-GPU-MoE CONVERGED — ~neutral at production temperature (closes the 3-way flip-flop) (commit `7369b0ec`)
Root cause of the flip-flop (−12% → +6.5% → −6.8%): **each reading measured a different, arbitrary output temperature instead of the deployed low-temp config.** Full curve (35B-A3B, seed 42, experimental build), MTP-on vs off:

| output temp | MTP delta | draft acceptance | regime |
|---|---|---|---|
| **0 (greedy)** | **+6.5%** | 0.79 | greedy over-states spec-dec (best-case acceptance) |
| **0.2 (PRODUCTION — registry intent 0.1–0.3 + greedy fallback)** | **−1.6%** | 0.63 | **operative = ~neutral (within single-sample noise)** |
| **0.6** | **−6.8%** | 0.57 | high-temp; the "still-negative" reading above |

- **Verdict: MTP is a WASH on GPU-MoE at production temp** — not worth enabling as a speed lever, but **no longer a reason to avoid it.** `de447119f` (+17.4% single-stream MTP-verify MMQ dispatch) **neutralized the old −12% penalty**; the residual sign at production temp is −1.6% = noise.
- **Do NOT re-quote "−12% / net-negative / no-go" as the current verdict** — that magnitude is now stale; the converged annotation is on findings-05c §Axis-D L8 (line ~95).
- New memory `feedback_production_sampling_seed_not_temp0`: **never A/B spec-dec at temp 0** — greedy inflates draft-acceptance; always measure at the deployed sampling config (temp + seed).

### 8. Spec-dec temperature behaviour is TEXTBOOK SOTA (literature cross-check)
Speculative decoding is **output-distribution-preserving (lossless) at every temperature** — only the *speedup* varies, and acceptance **falls monotonically as temperature rises** (higher temp = flatter target distribution = fewer draft tokens accepted). Our measured curve (accept 0.79 → 0.63 → 0.57 across temp 0 → 0.2 → 0.6) is exactly that shape. **Consequence:** low-temp production (0.1–0.3) is the *favorable* spec-dec regime, so the ~neutral-at-production reading is the expected outcome, not an anomaly — and any spec-dec speed A/B run at temp 0 systematically over-states the win.

### 9. stream-K is ALREADY the LIVE MMQ path on CDNA2 — CLOSED, not an un-tried bet (commit `7cf59c6d`)
Read-only `mmq.cu` assessment (zero build): **`use_stream_k = true` for CDNA2.** The 104-WG grid the campaign already benchmarked **IS stream-K working as designed** — `nsm` persistent blocks, one balanced block/CU — and it PRODUCED the very aggregate baseline the campaign measured. The earlier framing of "stream-K as a bigger separate bet" was a **factual error**; it is the live path, not a lever to try. The **only untested residual** = raise the persistent grid `nsm → k·nsm` (2 WG/CU) + the saved compact-LDS patch (~2-line change, expected **+0–10%**, IQ2/capacity slot only), gated on a **zero-build read of the captured pmc CSVs**. findings-05c §3.3 (line ~133) carries the correction; task #5 resolved.

### 10. CoT self-debug LOOP — also weak (4% rescue, RL-ceiling) + reasoning-effort framing (commit `752408bc`)
The single-shot lane was CLOSED above; the only untouched CoT mechanism was the **recursive reason↔execute loop.** A self-debug instance was run: 35B, bigcodebench 60q, write→execute→feed-error→revise, MAX_ITERS=3, `-fa on`. Result: 1-shot 22% → loop-final 25% (net +2); **RESCUES 2/47 = 4%**; effort curve **FLAT** (both rescues at iter 2, none at 3). **The recursive mechanism is also weak** — matches RL-ceiling (arXiv:2504.13837): self-refinement is bounded by the base's pass@k, so more loops don't cross the ceiling.
- **Caveat (operator):** bigcodebench is library-API-heavy (knowledge gaps, not reasoning) — possibly the wrong distribution → the **GPQA reasoning-diagnostic** (nothink vs ownthink vs scaffold-Qwable, 35B) is IN FLIGHT (see below).
- **Reasoning-effort framing (operator):** loop-depth = a "reasoning effort" knob = the local analog of cloud `reasoning_effort` / thinking-budget. Unifies `{nothink → think-budget → single-shot scaffold → loop-depth → model-escalation}` on ONE effort axis → an operator **FLAG** + an autopilot per-task-class **TUNABLE** (the existing 4D Pareto + per-request-reasoning-budget plumbing). Even the negative loop run yields the calibration data (rescue-vs-effort curve, flat here).

### 11. CoT RESEARCH — scaffold-injection is the PUBLISHED dead-end; VERIFIER/SELECTOR is the working "help another model" mode (commit `5be98734`)
**The major result.** A public-literature survey confirms our negatives ARE the field consensus — scaffold/reasoning-injection is a known dead-end:
- **"Reasoning that Travels" (arXiv:2605.28913):** transplanted reasoning is a capability **AMPLIFIER, not a SUBSTITUTE** — helps capable receivers, "cannot overcome fundamental performance gaps in weaker models"; transfer success tracks the RECEIVER's base capability. = our "transplanted reasoning doesn't transplant capability."
- **Small-planner-degrades-executor (arXiv:2506.11578):** small-model plans drop a LARGER executor BELOW its baseline. = our single-shot 4B→35B derailing.
- **RL-ceiling (arXiv:2504.13837):** self-refinement bounded by base pass@k. = our self-debug loop (4%).
- **Reasoning is ELICITED not INSTALLED** (LIMO 2502.03387, s1 2501.19393, structure>content 2502.07374).
- **Learnability gap (arXiv:2502.12143):** below ~3–7B long-CoT HURTS → our 4B-Fable5 is AT the boundary; Qwable-35B is above it.

**THE ONE WORKING MODE (untested by us): VERIFIER / SELECTOR (best-of-N).** The reasoner does ITS OWN task — grade/rank/verify the beneficiary's candidate answers — and never transplants capability, sidestepping the entire transplant problem:
- **GenRM (arXiv:2408.15240):** best-of-N lifts 5%→45%, 73%→93%.
- **GenPRM (arXiv:2504.00891):** a **1.5B generative PRM BEATS GPT-4o as a judge**; a 7B beats a 72B.
- Fits the GPU-reasoner + CPU-beneficiary topology and **plugs into the existing EV-9 DRACO/MindDR scorer.**

**Reframed GPU-reasoner role** (replaces scaffold-injection): (1) **standalone** — route reasoning-heavy tasks (math/code/STEM) to the GPU reasoner; (2) **verifier/selector (best-of-N)** over CPU-model outputs. Offline, Qwable can still generate CoT to fine-tune CPU models (data-gen). **VERIFIER/SELECTOR is the recommended NEXT GPU-reasoner experiment** (operator, GPU-only): testable **entirely on GPU** by hosting the beneficiary on GPU and artificially **rescaling its t/s** to sweep the CPU-cost tradeoff pivots (no CPU needed); reuses the EV-9 scorer. Run immediately or after the incremental levers land.

### In flight (do NOT wait) + mid-precision probe
- **GPQA reasoning-diagnostic** (nothink vs ownthink vs scaffold-Qwable, 35B) — decides whether the CoT scaffold closes **bench-independently**, or whether **ownthink helps but the transplant does not** (the bigcodebench-distribution caveat). Running; next session reads the result.
- **gemma-4-26B IQ4_XS downloaded** — mid-precision probe queued (between the deployed Q4_K_M and the Q8 clean-quality arm).

### Commits (this continuation, epyc-root, branch spec-dec-mtp-refresh-2026-06-22)

| Commit | Summary |
|---|---|
| `7369b0ec` | findings-05c L8: MTP-on-GPU-MoE **CONVERGED** — ~neutral at production temp (curve: temp0 +6.5% / temp0.2 −1.6% / temp0.6 −6.8%); `de447119f` neutralized the −12%; closes the 3-way flip-flop (root cause = measured arbitrary temps not the deployed config) |
| `7cf59c6d` | findings-05c: **stream-K is ALREADY the LIVE MMQ path on CDNA2** (`use_stream_k=true`; 104-WG grid = stream-K working as designed) — "bigger separate bet" was a factual error; residual = `nsm→k·nsm` + compact-LDS (~2-line, +0–10%, pmc-CSV-gated); task #5 resolved |
| `5be98734` | **CoT research:** scaffold-injection = literature dead-end (2605.28913 / 2506.11578 / 2504.13837 / LIMO-s1); the ONE working mode = **VERIFIER/SELECTOR best-of-N** (GenRM 2408.15240; GenPRM 2504.00891 — 1.5B PRM beats GPT-4o judge); GPU-reasoner role reframed |
| `752408bc` | CoT handoff current: **self-debug loop 4%** (RL-ceiling), effort curve flat; reasoning-effort framing (loop-depth = local `reasoning_effort`); **verifier/selector = recommended next GPU-only experiment** (beneficiary-t/s rescale, reuses EV-9 scorer) |

Wrap-up doc commit (this continuation + handoff Status header + index/wiki reconciliation) added separately this session (hash in the wrap-up report).

### Deferred / open (this continuation)
- **VERIFIER/SELECTOR best-of-N = the forward GPU-reasoner experiment** (operator-approved, GPU-only via beneficiary-t/s rescale, reuses EV-9 scorer). This is now the primary open CoT bet, ahead of the loop.
- **Recursive reason↔execute loop** = operator-gated bigger build, prior **further lowered** by the self-debug 4% result (RL-ceiling). Distillation-adds-value + format-native-injection stand as components IF it is ever built.
- **findings-05c residual −12% cells** — the converged verdict (~neutral) is applied to the primary Axis-D L8 cell (§Axis-D) and §3.3 stream-K note, but the older **−12% / "N" / "Do NOT enable MTP"** magnitude still appears in the §1.1 compact-grid L8 row, §3.3 item 6, §3.4 item 7, and the §5 headline. The verdict shifted negative→~neutral, so those summary cells now read *more* conservative-but-inconsistent than at the prior wrap-up. Per the established flag-not-overwrite precedent for measurement-adjacent category verdicts (operator-reviewed cadence), they are **FLAGGED, not swept**, this wrap-up.
- **GPQA reasoning-diagnostic** in flight (do not wait); **gemma-4-26B IQ4_XS** mid-precision probe queued.

### Memory
New memory `feedback_production_sampling_seed_not_temp0` — never A/B spec-dec at temp 0 (greedy inflates draft-acceptance = best-case); measure at the deployed sampling config (temp + seed). This is the discipline lesson that resolved the 3-way MTP flip-flop.
