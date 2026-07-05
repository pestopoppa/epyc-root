# 2026-07-05 — MI210 campaign: big-model residency ladder (2-for-2) + CoT-scaffold rescue-reframe

Self-contained wrap-up for the MI210 "capability/residency + reasoning-economics" phase that landed since the previous full wrap-up (`27af3725`, 2026-07-04). All work was committed inline to the owning handoffs; this entry is the narrative + evidence index. **Every GPU number here is an OBSERVATION** (single MI210, serial, contended host, no `P-GPU-1` protocol per MEASUREMENT.md) — usable for direction, never decision-gating. All items are experimental-HOLD; operator-only authorizes any production push, CPU-correctness-gated first.

## Context

The prior phase declared GPU *speed* structurally exhausted and pivoted the campaign to **capability** (fit a bigger model on the one 64 GB card) + **strategy** (a roadmap for the card). Coming in, the residency bet had one measured data point (122B IQ2 VIABLE) with its eval-parity gate still RUNNING, and the CoT-scaffold reasoning-economics lane had a caveated slice-1 GO. This session closed both gates and added a second residency data point.

## What landed this session

### 1. 122B IQ2 eval-parity gate = PASSED judge-free (commit `679a6f61`)
The architect residency prize is now quality-confirmed. A **212-question deterministic *paired* eval** (same questions, same eval-tower scorer, only the quant differs) gives **IQ2 163/212 = Q4 163/212, Δ0.0pp, McNemar p=1.000** (11/11 disagreements symmetric = quantization noise), + PPL 5.02. On judge-free evidence, **Qwen3.5-122B-A10B UD-IQ2_M is a drop-in GPU-resident architect** (43.7 t/s single / 148.7 agg @B=32, ~17 GB headroom).
- **CORRECTION recorded:** the earlier "93%" architect-quality figure was the **35B coder**, NOT the 122B. The Q4-122B architect quality is **2.57/3 = 85.67%**.
- **Deferred:** the LLM-judge weighted-rubric architect gate (70 Qs) — needs a cross-family judge, not runnable GPU-only.

### 2. 80B-ingest IQ2 GPU-residency = MEASURED VIABLE — the residency pattern GENERALIZES (commit `dc68fffd`)
**Qwen3-Next-80B-A3B i1-IQ2_M** (26.1 GB; qwen3next GDN-hybrid — a *different* GDN family from the qwen3.5 122B/35B) runs coherently on CDNA2 IQ2 MMQ with `-fa on` (feasibility gate PASSED, PPL 5.77 healthy):
- **55.8 t/s single (~2.7–3.9× CPU-Q4) / 265 t/s aggregate @B=32 bf16 (~13–18× CPU-Q4)**.
- VRAM 27.7 GB @`-c 32768` → **~38 GB free, 32K KV fits trivially** (GDN linear-attn keeps KV ~O(1) → the long-context ingest role is comfortably GPU-served, *better* than a dense model would be).
- **bf16-GDN-state generalizes to qwen3next: +13.3% aggregate, coherent** — first confirmation outside the qwen3.5 family.
- **Residency ladder is now 2-for-2 (122B + 80B both VIABLE).**

### 3. 80B IQ2 aggregate ceiling swept (commit `7abe3346`)
B32→B128 sweep: **263 / 301 / 323 / 382 / 405 t/s** aggregate decode; knee at B≈96–128; asymptote ~498. **Compute-bound at the ceiling** (per-step model: 0.059 s BW floor + 0.00201·B compute); **VRAM non-binding** (30 GiB @B128 = 46% of 64 GB). Deployable optimum **B=96 (381 t/s, latency-balanced) / B=128 (405 t/s, max aggregate)**.

### 4. CoT-scaffold sidecar: gates G2 + G1-ii run, then verdict CORRECTED via operator reframe
- **G1 slice-2 (commit `679a6f61`)** — on a harder unsaturated suite (`mode_advantage` tier-3, N=27, nothink 77.8%) the injection-mode answer FLIPPED from slice-1: SCAFFOLD-**prefix** wins (88.9% vs nothink 77.8%, +11.1pp), SCAFFOLD-context is Pareto-dominated. Slice-1's context-win was a saturation artifact.
- **G2 + G1-ii (commit `0279ad9a`)** — **G2 cross-family**: a literal `<think>`-prefix does NOT transfer 4B→gemma (63% vs gemma-nothink 81.5%, dominated); but **format-native reasoning-slot injection lifts +11.1pp / 0-regressions** → redefine SCAFFOLD-PREFIX = target-native slot injection, not a literal Qwen tag. **G1-ii distillation**: distilled Qwable-prefix > vanilla 4B-control +11.1pp @0.58× tok → **distillation thesis CONFIRMED**; BUT the clean own-think fix forced `-c 10240` and Qwen rope-scaling flipped nothink 77.8%→88.9%, so at clean context NEITHER scaffold beats nothink token-normalized. The intermediate read was "narrow / config-fragile / marginal."
- **VERDICT CORRECTED — operator reframe (commit `13fa4757`).** The "marginal / config-fragile" read was **wrong on 3 counts**:
  1. **Metric** — gating on token-efficiency vs nothink's *average* is the wrong test. When nothink FAILS, token cost is irrelevant; the data already shows the real value: the scaffold **RESCUED 3 (format-native cross-family) / 4 (distilled) tasks nothink failed outright, 0 regressions** = it *enables tasks nothink cannot handle*.
  2. **Distribution** — code puzzles are where reasoning helps *least* (saturate nothink); rescue value lives in hard/realistic multi-step agentic workflows (the `/mnt/raid0/llm/cot-corpus/` distribution, 783 real Claude thinking traces), NOT HumanEval.
  3. **Deployment** — not always-on; a **CONDITIONAL** lever gated by **episodic memory** that learns per-task-class when the accuracy-for-tokens trade is worth paying.
  Both survivors (distilled>vanilla generator; format-native injection) are **orchestration components**. Lane is **re-scoped toward autopilot/orchestration fine-tuning, NOT closed.** New memory file: `feedback_accuracy_token_tradeoff_rescue_metric`.
- **IN FLIGHT (do not re-close):** the re-scoped **rescue-rate experiment** (mode_advantage_hard distribution, nothink vs format-native scaffold, rescue metric with 0-regression gate) is **RUNNING on the MI210 now** — the lane's live open thread.

### 5. Orchestration-infra map for the rescue-rate experiment
The rescue-rate experiment is ~80% pre-built from existing infra: `mode_advantage_hard` distribution + `core_v2_select`; `iq2_arch_eval.py` no-think driver; `think_harder.py` scaffold-boolean; `difficulty_signal.py` band; `episodic.db` `q_value` / `hypothesis_graph` RL memory; `capability_registry.yaml` lever registry. **4 integration forks identified:** static-band vs learned head (head frozen); reward home = `episodic.db` role:mode reuse; proactive vs reactive; distillation external-vs-build (training substrate is an operator-held unknown).

## Commits (this session, epyc-root, branch spec-dec-mtp-refresh-2026-06-22)

| Commit | Summary |
|---|---|
| `679a6f61` | 122B IQ2 eval-parity PASS (judge-free, Δ0.0pp p=1.000) + CoT slice-2 flips injection-mode to PREFIX; "93%"→35B-not-122B correction |
| `0279ad9a` | CoT G2 + G1-ii: scaffold-beats-nothink is CONFIG-FRAGILE; literal `<think>`-prefix does NOT transfer cross-family (format-native does) |
| `dc68fffd` | 80B-ingest IQ2 GPU-residency MEASURED VIABLE — residency pattern generalizes to qwen3next (55.8 single / 265 agg@B32, PPL 5.77) |
| `13fa4757` | CoT verdict CORRECTED (operator reframe): rescue-lever, not marginal — re-scoped toward autopilot/orchestration, not closed |
| `7abe3346` | 80B IQ2 aggregate ceiling: 405 t/s @B128 (asymptote ~498), compute-bound, VRAM non-binding |

Wrap-up doc commit (progress + index/handoff reconciliation + wiki) added separately this session (hash in the wrap-up report).

## Deferred / running (next session picks up)
- **CoT rescue-rate experiment** — RUNNING on the MI210 (mode_advantage_hard, nothink vs format-native scaffold, rescue metric, 0-regression gate). Do not re-close the lane until it reports. (`gpu-cot-scaffold-sidecar.md`)
- **LLM-judge weighted-rubric 122B architect gate** (70 Qs) — deferred, needs a cross-family judge (not GPU-only).
- **Roadmap Axis-A/B gating experiments** (roadmap, gating-experiments-first): expert-routing-skew profile (offload/REAP viability — Zipfian?), GPU-draft N5 feasibility + quant-asymmetric self-spec α measurement, GLM-5.2 endgame (DSA-gated, offload-mandatory).
- **Kernel-R&D loop Phase 2** — nightshift autopilot wrapper still open.
- Scratch experiment drivers (`iq2_parity_eval.py`, `iq2_arch_eval.py`, `iq2_*_results.jsonl`, `iq2_server.*`) remain uncommitted in the repo root — transient, not code artifacts.

## Wiki
The residency-ladder result (2-for-2) was compiled into `wiki/hardware-optimization.md` as a review-flagged 2026-07-05 subsection this session. The source scanner reports 43 new sources, but those span the parallel autopilot / evidence-plane / dashboard sessions; a full cross-session compile is out of scope for this focused wrap-up, so `.last_compile` was **NOT** touched (touching would hide the other sessions' un-compiled sources from the next incremental scan).
