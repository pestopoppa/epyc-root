# Fable 5 findings 03 — Post-bandwidth-wall serving & the MI210 (facet 4)

**Date**: 2026-06-12. **Scope**: brief §4.4 + §5. Citations `file:line` under `/mnt/raid0/llm/epyc-orchestrator` and `/mnt/raid0/llm/llama.cpp`; handoffs under `/workspace/handoffs/active/`.

---

## 1. Verdict on hypothesis #1 (CPU exhaustion) — confirmed at the kernel level, NOT at the serving level

The bandwidth-wall evidence is solid and survived your own adversarial re-measurement: the 2026-04-26 cold-cache canonical matrix collapsed most kernel-level "wins" to noise (EP +17%→+1.6%, mbind +6%→0%, etc.), decode is DRAM-wait-bound across four architecture classes, and the NUMA topology law (quarters 6–7× aggregate ≤65GB; 1×96t for 130–250GB; 192t anti-optimal) is encoded in deployed config (`stack_numa.py:9-15`). **Kernel-level: exhausted. Agreed.**

But "the next gains are architectural" understates how much architecture is *already built and unexploited*:

1. **The frontdoor — your hottest path — runs zero speculative decoding.** No `-md`, no `--spec-type` (`model_registry.yaml:366,374`; confirmed by your own Stage-0 note). The single gating number for the entire GPU-drafter program, α(Qwen3-1.7B → Qwen3.6) on production traffic, is **measurable on CPU today** and is not measured. This is the cheapest high-information experiment in the whole portfolio.
2. **Continuous batching is on by default in the fork and unused** (`common/common.h:530`): heavy roles run `-np 1/2` under a cross-process exclusive lock (`src/runtime/inference_lock.py:1-4`). Meanwhile the actual workload (findings-02 §2.3) is eval/batch-dominated — 400 forced evals/day, autopilot T1 evals at concurrency 3, GEPA 6-worker fan-outs. **The serving layer is latency-shaped for a user who is mostly a batch harness.** For BW-bound CPU decode, batched verification/decode amortizes the weight stream — this is the one regime where the bandwidth wall itself bends.
3. Measured-but-unused operating points: 96t-single-node 49.1 t/s (+26% over deployed worker config), MoE-Spec budget built but inert, ngram-lookup spec types all off.

So the honest framing: you are standing at the bandwidth wall on the *kernel* axis while leaving 1.3–3× of *configuration* on the table on the serving axis. Harvest those before (and as calibration for) the GPU.

## 2. MI210 hypothesis (brief §5) — verdict on hypothesis #4: right device, inverted emphasis

Your stated hypothesis: *(a) dense frontdoor on GPU + (b) fast spec/MTP draft heads on GPU accelerating CPU-resident targets.* The gpu-drafter handoff is more rigorous than the brief implies (α-gate with 3-bin decision rule, staged kill-gates, GT-1030 falsification, Stage-0 already downgrading the MTP-split EV to +10–15%). Critique on top of it:

**2.1 The strongest leg is (a), and it's even stronger than you frame it — but note your frontdoor is an MoE, not dense.** Qwen3.6-35B-A3B Q8 = 37GB fits in 64GB HBM2e with KV headroom; 1.6TB/s vs the ~one-NUMA-node the role sustains today ⇒ **~3× from residency alone** (the handoff's own ~85 t/s solo bound vs 27 t/s deployed) before any spec-dec, and coder_escalation + worker_summarize ride along free (same process today). The handoff buries this as a drafter-co-location detail; it is the headline. (The brief's word "dense" is a slip worth correcting in your own docs: a *dense* ~30B would trade the A3B's CPU-friendliness for GPU-BW-friendliness — that's a real design fork only if you'd also re-pick the frontdoor model; otherwise host the deployed MoE.)

**2.2 The weakest leg is (b) — GPU drafters for CPU-resident targets.** Three structural reasons: (i) your spec-dec history on CPU targets is mostly net-negative, and the confound you correctly identified (drafter steals DRAM BW) is only *one* of the failure modes — verify cost on a BW-bound target is near one full weight pass per round regardless of where the draft came from, so the ceiling is α-bounded and modest at realistic α; (ii) the cross-device loop pays PCIe/xGMI ~64GB/s on every round (your own disagg handoff defaults NOT-PURSUED on exactly this); (iii) Stage-0 showed the MTP path already saturated (76.9% acceptance) where it exists. Keep Stage 1 as designed (≥1.3× kill-gate) but treat it as a falsification probe, not the plan of record.

**2.3 Alternatives under-weighted in your §5 hypothesis (rank by EV):**
1. **Frontdoor residency** (§2.1) — deterministic ~3×, hottest path, zero algorithmic risk. Decision: solo bench on arrival.
2. **Eval/batch acceleration** — host the T1/T2 eval fan-out, GEPA workers, and bulk-inference campaigns on the GPU. This is the cross-facet compounding play: **eval throughput IS statistical power** (findings-01 §1). A GPU that runs promotion evals at 150–200q in the wall-time of today's 43q directly buys the measurement resolution the whole self-optimization program is starved of. No other MI210 use compounds like this.
3. **Embedder/classifier/reranker host** — 6×BGE processes, ColBERT NextPLAID, the routing classifier + verifier retrains (currently BLOCKED partly on embedding infra), KB-RAG. Batch-friendly, compute-bound, frees CPU cores, and unblocks the routing-retrain pipeline (findings-02 §2.3).
4. **Prefill/long-context offload** — compute-bound, the GPU's natural win (`gpu-acceleration-path.md:195-204`); gate on measuring the per-role prefill/decode wall-time split, which nobody has profiled.
5. **Drafter farm** (your (b)) — last; only past the Stage-1 kill-gate.

**2.4 The ROCm kernel program** (`agentic-rocm-kernel-authoring.md`) is correctly scoped as enablement, not placement. One warning from your own history: the CPU program's biggest measurement lesson (canonical-baseline rigor, CPU20) must transfer to the GPU on day one — vendor-reported numbers, warm-cache flatters, single-run benches will reproduce the closure-inflation cycle on new silicon. Write the GPU canonical protocol *before* the card arrives.

## 3. Serving-layer assumptions to retire (the §8.5 "dangerous assumptions" for this facet)

| Assumption (encoded where) | Why it's now wrong | Replacement |
|---|---|---|
| Single-user, latency-first (exclusive locks, `-np 1/2`, SERIAL_ROLES) | The dominant traffic is the eval/optimization harness + batch campaigns | Two explicit serving classes: interactive (current path) and **batch/eval class** using continuous batching + larger `-np` on dedicated instances; the contention gate already gives you the admission layer |
| One context per process / static role→port | Same-GGUF consolidation already broke role↔process 1:1; GPU adds a device axis | A small **placement manifest**: role → (device, instance-set, serving-class), compiled like the lean registry; this is the hardware-abstraction boundary the North Star needs for "CPU now + GPU soon" |
| Spec-dec is per-model tuning lore | frontdoor has none; decisions encoded as launcher special-cases (`_NO_SPEC_DECODE`, ik-binary override) | Put draft/MTP/lookup config in the model-capability descriptor (findings-02 §3) so acceleration travels with the model, not the launch script |
| The fork is one binary | worker_general already runs a *separate* ik_llama.cpp build with env-stripping shims | Either upstream MTP into the fork or make multi-binary a first-class manifest field — the shim is load-bearing and invisible |

## 4. Decision gates & smallest decisive observations

| # | Observation (cost) | Decides |
|---|---|---|
| G1 | **α(1.7B→frontdoor) on CPU, production traffic** (one launcher flag + log read) | the entire drafter program's 3-bin fork — *run this week, no GPU needed* |
| G2 | Per-role prefill/decode wall-time split (log analysis) | prefill-offload EV vs decode-residency EV |
| G3 | Frontdoor-on-GPU solo bench (day-1 after arrival) | residency as plan-of-record (predict ~2.5–3×) |
| G4 | Eval-batch on GPU: T1 wall-time at n=200 vs CPU n=43 (day-2) | whether the GPU becomes the measurement engine (findings-01) |
| G5 | Stage-1 GPU-draft/CPU-target ≥1.3× kill-gate (as designed) | drafter-farm life or death |
| G6 | One week of batch-class serving (continuous batching on a quarter set) vs status quo on eval traffic (CPU-only, now) | whether the batch serving class pays before the GPU lands |

**Irreversible vs reversible**: buying/placing the MI210 PCIe lanes under NPS4, and the chassis power budget, are the only hard-to-reverse items (verify before install — your own open question). Everything else above is config-reversible. **Compounding bets**: G1/G4/G6 compound with findings-01 (measurement power) and findings-02 (descriptor schema); make them now. **Optional until evidence**: custom drafter training (FastDraft), cross-tokenizer spec-dec, MTP-split engineering — all correctly gated in your own handoff; keep them gated.
