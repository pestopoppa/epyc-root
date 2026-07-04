# Proposal: MI210 Kernel R&D as a semi-autonomous loop (planner/critic → hypothesis → verify → authorize)

**Status**: PROPOSAL — **build only on explicit operator go.** Standing up a new autopilot-class mode touches the measure/authorize trust boundary (MEASUREMENT.md is human-amendment-only), so this is a design to react to, not a task to execute. **Created**: 2026-07-04 (operator raised: "should sessions like this become another form of autopilot… planner/critic → hypothesis → verify → authorize, like the orchestration-optimization loop?").
**Context**: this GPU speed campaign (findings-05b, findings-05c, the three mi210 kernel handoffs) is the manual instance of exactly this loop — we're running it by hand right now.

## The core claim

It is **not** autopilot *vs* interactive. Kernel R&D is a **two-layer loop**, and only the inner layer should be autopilot; the outer stays planner/critic-interactive and the gate stays human.

The orchestration autopilot works because it optimizes a **tunable surface** (scalar/discrete knobs, cheap+parallel+reversible eval, well-defined fitness). Kernel R&D breaks three of those assumptions, and that difference is the whole design:

| | Orchestration autopilot | GPU kernel R&D |
|---|---|---|
| Unit of work | a **point** in knob-space | a **creative artifact** (a kernel design) |
| Evaluation | cheap, parallel across the stack | **expensive, serial, one MI210** (~minutes/iter) |
| Correctness | bad config just scores low | bad kernel **silently corrupts** (garbage / numerically-valid-not-bit-exact) |
| Authorize | flag-gate, reversible | touches the **human MEASUREMENT trust boundary** |

## The three steps and their owners

1. **Hypothesis (outer loop) — planner/critic + interactive. NOT autopilot.**
   "Async-prefetch via `raw.buffer.load.lds`, not the gfx940-gated builtin" came from reading fork source + CK headers + LLVM threads + the Fleet paper. That is not a point in a space you can search — it is a design read out of source and literature. The single-GPU serialization *forces* smart proposals (you cannot afford brute search on one card), so the planner must use the mechanism data ("rocprofv2 says MemUnitStalled high → prefetch") to pick the next point. This is where the human / high-effort model adds the most value, and it is what a **focused interactive workflow** (or a planner→critic agent pair) is for.

2. **Verify (inner loop) — CODIFY FIRST; this is the autopilot-shaped part.**
   Given a chosen design, the tuning IS a surface: the nwarps sweep (2/4/8→4) we did by hand, plus prefetch-distance, SLC on/off, tile size. And the rigor harness around each variant is mechanical, repeated every time, and the thing most easily gotten wrong under time pressure (we have already hit stalls, rocprof-v1-aborts, the `libpciaccess` path, the `-fa 1`/KV-quant gotcha). **First concrete artifact — `kernel_eval.sh`, the exact analog of `bench_canonical.sh`:** given a built binary + a variant label, it runs `build → test-backend-ops → alternated-A/B llama-bench → rocprofv2 mechanism-confirm → emit a verified (single-t/s, aggregate-t/s, correctness-margin, mechanism, OBSERVATION) record`. Once it exists, the inner loop is a thin wrapper over it.

3. **Authorize — stays human, and that is MEASUREMENT.md, not timidity.**
   Clean autonomy ceiling: the loop can land **experimental-tree commits + OBSERVATIONS autonomously** — `a8afd338` already did (nwarps=4 measured, committed `5dc116130`, reviewed by the main thread). What it **cannot** do autonomously is ratify **P-GPU-1** or promote to production-consolidated-v6 — those are the human-amendment-only trust boundary. So the loop runs autonomously right up to "experimental + observation" and stops at the gate.

## Two non-negotiable design rules (from hard experience)

- **Fitness must be lexicographic, correctness-first — never a weighted sum.** A speed-maximizing loop WILL find a fast, subtly-wrong kernel; numerically-valid-not-bit-exact (flips greedy argmax on near-ties) is the first taste. Gate on `test-backend-ops` pass + PPL-within-ε **first**, then rank by speed. This is the biggest departure from the orchestration autopilot (where a bad point merely loses).
- **Reuse the autopilot machinery; inherit its scars.** A "kernel strategy store" (SQLite) of `(design, params) → verified-result`; a **Pareto checkpoint** over (single-stream, aggregate, correctness-margin) so a win is never lost (cf. [[feedback_checkpoint_pareto_state]]); flag-gate + rewind. Carry the lessons: pause-is-broken-use-SIGTERM ([[feedback_autopilot_pause_broken_use_sigterm]]), rewind-must-purge-the-store ([[feedback_autopilot_rewind_must_purge_strategy_store]]), "noise window" is usually not contention ([[feedback_autopilot_noise_window_not_contention]]).

## Cadence + search efficiency

Single-GPU serialization ⇒ one experiment at a time (unlike the orchestration autopilot fanning across the stack). So (a) the search must be **sample-efficient** (guided by the mechanism profile, not random — which is why the outer planner/critic stays essential even inside the "autopilot"), and (b) it is a **slow-cadence, nightshift-style** run (`scripts/nightshift/`), not a fast loop.

## Sequencing (recommended)

1. **Do not stop to build it now** — a live lever (async-prefetch) is in flight, and finishing it tells us what the harness must capture. **This interactive session is the spec for the autopilot.**
2. **Harvest the codified recipe** from the runs `a8afd338` and the async-prefetch agent are exercising right now (env, foreground-only rule, alternated-A/B, rocprofv2 flags + `pmc:` prefix + `libpciaccess` path, the correctness checks).
3. **Stand up `kernel_eval.sh`** (the verify layer) — highest-leverage, riskiest-if-wrong, most-repeated step. That alone removes most of the fragility.
4. **Wrap the inner loop** (sweep params → `kernel_eval.sh` → Pareto store) as a nightshift; keep hypothesis planner/critic-interactive; keep authorize human.

## Open questions for the operator

- Is `kernel_eval.sh` (step 3) worth building as a standalone even if we never wrap the autopilot? (My view: yes — it pays for itself in fragility-removal on the next 3 levers regardless.)
- Autonomy ceiling confirmation: is "autonomous experimental-tree commits + OBSERVATIONS, human-gated at P-GPU-1 + prod promotion" the right line?
- Does this belong under the existing autopilot infra (strategy store / nightshift) or as a sibling? (Reuse recommended.)
