# 2026-07-05 — MI210 campaign: capability pivot + kernel-R&D loop + strategy

Session wrap-up for the MI210 "capability + kernel-R&D-loop + strategy" phase. This entry is a self-contained index of work that landed incrementally across 2026-07-04/05 (commits already made); the detailed evidence lives in the linked handoffs and the campaign progress file `2026-07-03-mi210-qwen36-27b-speed-campaign.md`. All GPU numbers are **OBSERVATION** (serial single-GPU, contended host) per MEASUREMENT.md — none is decision-gating without P-GPU-1 (G1, still open).

## Context

After the single-stream dense-Q8 lever set was declared exhausted (previous wrap-up `905b9c9d`), the campaign pivoted from *speed* to **capability** (fit a bigger model on the card) + **process** (turn the manual kernel campaign into a semi-autonomous loop) + **strategy** (a roadmap for what to do with one 64 GB card next). Every item below is experimental-HOLD; operator-only authorizes any production push, CPU-correctness-gated first.

## What landed this session

### 1. Kernel-R&D loop Phases 1–2 built (research `133017d`)
`scripts/kernel_rnd/kernel_store.py` (SQLite Pareto strategy store, correctness-first) + `kernel_sweep.sh` (inner sweep loop). Phase 0 harness `kernel_eval.sh` was already validated (research `48f990f`). Phase 3 (dashboard) was specced as a hand-off to the dashboard-hub session (epyc-root `5754b088` spec → hub built it, epyc-root `5a186e87` + research `93c28ed` `kernel_store.py export` contract). Loop is now Phases 0–3 present; **Phase 2 nightshift autopilot wrapper is the only remaining open piece** (see `mi210-kernel-rnd-loop-proposal.md`).

### 2. bf16 GDN recurrent-state = BUILT + GO — the clean deployed-role kernel win (fork `496e2f098`, branch `upstream-mtp-verify`)
Runtime-gated `GGML_CUDA_GDN_STATE_BF16` (default-off, byte-identical when off). Confirmed across **all 3 GDN-hybrid sizes**:
| Role / model | Aggregate @B=32 | Correctness |
|---|---|---|
| Qwen3.5-27B | **+21.5%** (162.8→197.8 t/s) | drift PPL +0.0035%; gemma isolation byte-identical; test-backend-ops 1103/1103 |
| frontdoor 35B-A3B (deployed) | **+17.7%** | byte-identical |
| architect 122B IQ2 (deployed) | **+16.4%** | (inherits the gate) |
Mechanism: bf16 halves the recurrent-state gather+scatter (not just kernel compute) — L2 hit 47.8→59.9%, VALUBusy 15.7→56%. High-batch-only. Occupancy sub-lever (L20) was scoped **NO-GO** (100% theoretical occupancy; the ~42% is pure memory-latency) — the win is the precision lever, not occupancy.

### 3. L15 — 122B IQ2 residency = MEASURED VIABLE (the residency-bet prize) (epyc-root `f6687f34`)
Qwen3.5-122B-A10B **UD-IQ2_M** (40.4 GB download completed + verified) runs **fully GPU-resident**: 47/64 GB used, ~17 GB headroom; **43.7 t/s single / 148.7 t/s aggregate @B=32** (bf16-state on); **IQ2 PPL 5.02** (healthy). Win ≈ 2.2× single / ~8–9× aggregate over the corrected ~20 t/s architect baseline, at a Q4→IQ2 quality trade. **Conditional-GO** — the eval-parity gate (vs architect's 93%) is **RUNNING; do NOT mark complete.**

### 4. CoT-scaffold G1 slice-1 = GO (epyc-root `a7d6508b`)
Context-advisory scaffold beats own-think @0.45× tokens — heavily caveated (suite saturation). Harder-suite slice **RUNNING**. Text-level N5-sidestep; complementary to the drafter axis (`gpu-cot-scaffold-sidecar.md`).

### 5. Strategic roadmap (epyc-root `1c03262f`,`84b21f4d`,`245b19ac`,`1b93d1a8`,`a3a2c58e`)
New dedicated handoff `mi210-big-model-and-acceleration-roadmap.md`: Axis A (quant-ladder IQ2 → expert-offload/REAP → **GLM-5.2 754B GLM-MoE-DSA** endgame) + Axis B (GPU drafter-farm incl. **quant-asymmetric self-spec** — IQ-GPU-drafter → Q8-CPU-verifier, N5-free by construction). Wired into master-index §F + inference-acceleration-index; cross-referenced to glm51-reap (methodology-only; 5.1 superseded by 5.2), gpu-acceleration-path, angelslim.

### 6. Corrected architect baseline (research `2cb1148`)
Production architect (122B UD-Q4_K_M on CPU, v6 native MTP) is **~18–21 t/s single-stream** (best 20.75 MTP; live median ~16), **NOT** the stale lean-registry 4.3. Registry row fixed and era-labeled. GPU wins are now measured against ~20, not 4.3.

## Commits (this session)

| Repo / tree | Branch | Commits |
|---|---|---|
| epyc-root | spec-dec-mtp-refresh-2026-06-22 | `9a27518b` `d7fa4259` `f6687f34` (bf16/122B); `1c03262f` `84b21f4d` `245b19ac` `1b93d1a8` `a3a2c58e` (roadmap); `a7d6508b` (CoT G1); `5754b088` (Phase-3 spec); `5a186e87` (hub, dashboard-hub session) |
| epyc-inference-research | main | `133017d` (kernel_store+sweep); `93c28ed` (export contract, dashboard-hub session); `2cb1148` (architect baseline) |
| llama.cpp fork | upstream-mtp-verify | `5dc116130` (nwarps=4), `7c28056b7` (async-prefetch `GGML_CUDA_Q8_PREFETCH`), `496e2f098` (bf16 GDN-state `GGML_CUDA_GDN_STATE_BF16`) |

Negative patches saved as substrate (not committed): `fused-prefetch-NEGATIVE.patch`, `mmq-compact-lds-NEGATIVE.patch`, branch `campaign/mmq-compact-lds`.

## Verdicts recorded (NO-GO)
- **L3-MoE Q8-MMQ occupancy rewrite** — BUILT + FALSIFIED (grid-limited at B=32, not LDS-limited; compact-LDS lifted residency 1→2 WG/CU but occupancy flat). Settled: **bf16-for-aggregate, Q8-for-capacity.**
- **L20 GDN-occupancy** — SCOPED NO-GO (100% theoretical occupancy).

## Deferred / running (next session picks up)
- **122B IQ2 eval-parity gate** — RUNNING; gates the whole IQ residency program. (Scratch harness `iq2_parity_eval.py` / `iq2_arch_eval.py` in repo root — transient, not committed.)
- **CoT-scaffold harder-suite slice** — RUNNING (`gpu-cot-scaffold-sidecar.md`).
- **Kernel-R&D loop Phase 2** — nightshift autopilot wrapper not built.
- **Roadmap Axis-A/B experiments** (future, gating-experiments-first): expert-routing-skew profile (Axis A offload/REAP), GPU-draft N5 feasibility + quant-asymmetric self-spec α measurement (Axis B).

## Wiki
DEFERRED — the campaign outcome was already added to `wiki/hardware-optimization.md` this session (committed). The source scanner reports 41 new sources, but those span the parallel autopilot/dashboard/evidence-plane sessions; a full compile is out of scope for this focused wrap-up. `.last_compile` NOT touched.
