# Proposal: MI210 Kernel R&D as a semi-autonomous loop (planner/critic → hypothesis → verify → authorize)

> **SUPERSEDED AS LOOP OWNER 2026-08-01.** The system-wide, fully autonomous controller,
> tiered evaluation, checkpoint trigger, and automatic-release design now live in
> [`autokernel-research-loop.md`](autokernel-research-loop.md). This file remains the historical
> MI210 scaffold record and should not receive new controller/release architecture. Backend-specific
> MI210 evaluator findings may continue in `agentic-rocm-kernel-authoring.md` and
> `rocm-verify-profile-backend.md`.

**Status**: **APPROVED 2026-07-04 — building. Phase 0 (`kernel_eval.sh`) ✅ BUILT + VALIDATED + committed** (research `48f990f`). **Phase 3 (dashboard page) ✅ BUILT 2026-07-05 by the dashboard-hub session**: the epyc-root hub serves `/kernel` (OBSERVATION-disciplined; Pareto correct-only, best-per-model, run log with MemUnitStalled/Busy mechanism deltas, freshness), reading a self-contained JSON contract produced by the loop-owned `kernel_store.py export` (wired into `kernel_sweep.sh`); seeded + previewing against the real `prefetch-validate` row. **Phases 1–2 remain open** (Phase 1 strategy store: `kernel_store.py` + `export` exist; Phase 2 nightshift loop: not built). Now a buildable handoff (see Build plan). The measure/authorize trust boundary (MEASUREMENT.md, human-amendment-only) is respected by the authorize ceiling below: autonomous only up to experimental-tree commits + OBSERVATIONS; production push is operator-only. **Created**: 2026-07-04 (operator raised: "should sessions like this become another form of autopilot… planner/critic → hypothesis → verify → authorize, like the orchestration-optimization loop?").
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
   Clean autonomy ceiling: the loop can land **experimental-tree commits + OBSERVATIONS autonomously** — `a8afd338` already did (nwarps=4 measured, committed `5dc116130`, reviewed by the main thread). What it **cannot** do autonomously is ratify **P-GPU-1** or promote to production-consolidated-v6 — those are the human-amendment-only trust boundary. So the loop runs autonomously right up to "experimental + observation" and stops at the gate. **(Operator-confirmed 2026-07-04: the loop runs on `llama.cpp-experimental`; ONLY the operator decides when an experimental kernel is production-ready — no autonomous prod-v6 push.)**

## Two non-negotiable design rules (from hard experience)

- **Fitness must be lexicographic, correctness-first — never a weighted sum.** A speed-maximizing loop WILL find a fast, subtly-wrong kernel; numerically-valid-not-bit-exact (flips greedy argmax on near-ties) is the first taste. Gate on `test-backend-ops` pass + PPL-within-ε **first**, then rank by speed. This is the biggest departure from the orchestration autopilot (where a bad point merely loses).
- **Reuse the autopilot machinery; inherit its scars.** A "kernel strategy store" (SQLite) of `(design, params) → verified-result`; a **Pareto checkpoint** over (single-stream, aggregate, correctness-margin) so a win is never lost (cf. [[feedback_checkpoint_pareto_state]]); flag-gate + rewind. Carry the lessons: pause-is-broken-use-SIGTERM ([[feedback_autopilot_pause_broken_use_sigterm]]), rewind-must-purge-the-store ([[feedback_autopilot_rewind_must_purge_strategy_store]]), "noise window" is usually not contention ([[feedback_autopilot_noise_window_not_contention]]). **Dashboard (operator 2026-07-04): reuse + EXPAND the existing orchestration dashboard — add kernel-autopilot page(s) alongside the orchestration pages (ONE dashboard, separate pages), not a parallel stack.**

## Cadence + search efficiency

Single-GPU serialization ⇒ one experiment at a time (unlike the orchestration autopilot fanning across the stack). So (a) the search must be **sample-efficient** (guided by the mechanism profile, not random — which is why the outer planner/critic stays essential even inside the "autopilot"), and (b) it is a **slow-cadence, nightshift-style** run (`scripts/nightshift/`), not a fast loop.

## Sequencing (recommended)

1. **Do not stop to build it now** — a live lever (async-prefetch) is in flight, and finishing it tells us what the harness must capture. **This interactive session is the spec for the autopilot.**
2. **Harvest the codified recipe** from the runs `a8afd338` and the async-prefetch agent are exercising right now (env, foreground-only rule, alternated-A/B, rocprofv2 flags + `pmc:` prefix + `libpciaccess` path, the correctness checks).
3. **Stand up `kernel_eval.sh`** (the verify layer) — highest-leverage, riskiest-if-wrong, most-repeated step. That alone removes most of the fragility.
4. **Wrap the inner loop** (sweep params → `kernel_eval.sh` → Pareto store) as a nightshift; keep hypothesis planner/critic-interactive; keep authorize human.

## Operator decisions (confirmed 2026-07-04)
- **BUILD APPROVED** — proceed in parallel with the (b) L3-MoE/L15 research bet, until the loop is ready to test/run.
- **Authorize ceiling** — loop runs on `llama.cpp-experimental`; autonomous up to experimental commits + OBSERVATIONS; **operator-only** decides production-readiness / prod-v6 push.
- **Lexicographic correctness-first** fitness — confirmed (correctness gate first, then speed; never a weighted sum).
- **Reuse + EXPAND the existing dashboard** — kernel-autopilot page(s) alongside orchestration pages, one dashboard.
- **`kernel_eval.sh` first** — confirmed as the do-first artifact.

## Build plan (phases — (c), in parallel with the (b) research bet)
- **Phase 0 — `kernel_eval.sh` (the verify layer, DO-FIRST) — ✅ BUILT + VALIDATED 2026-07-04** (research `48f990f`, `scripts/kernel_rnd/kernel_eval.sh`, 230 lines). Codifies the campaign's proven recipe into one script: given a built binary + variant label → `GPU-idle gate → test-backend-ops (correctness gate, LEXICOGRAPHIC-first — a FAIL never speed-ranks) → coherence check → alternated-A/B llama-bench tg128 -fa 1 -r 3 → rocprofv2 mechanism-confirm (pmc: MemUnitStalled/Busy/occupancy) → emit {single-t/s, aggregate-t/s, correctness-margin, mechanism, OBSERVATION} JSONL`. Reference = the exact harness the campaign agents exercised (env incl. the `/usr/lib/x86_64-linux-gnu` libpciaccess path; foreground-only; rocprofv2-not-v1; the alternated-A/B protocol). **Validated** against the async-prefetch kernel (`GGML_CUDA_Q8_PREFETCH` 0/1, 27B-Q8): reproduced +2.11% tg128, MemUnitStalled −55%, `test-backend-ops` 1103/1103, byte-identical; correctness-first gate additionally proven with a broken stub. Standalone value even if the full loop never ships.
- **Phase 1 — kernel strategy store (SQLite).** `(design, params) → verified-result`; Pareto frontier over (single-stream, aggregate, correctness-margin) so a win is never lost. Reuse the orchestration autopilot store; carry the scars (SIGTERM-not-pause, rewind-purges-store, noise-window≠contention).
- **Phase 2 — the loop.** Outer hypothesis = planner/critic-interactive (creative kernel designs, not autopilot-searchable); inner tuning loop (sweep params → `kernel_eval.sh` → Pareto store) as a **nightshift** (single-GPU serial ⇒ overnight cadence). Authorize gate per the ceiling above.
- **Phase 3 — dashboard page — ✅ BUILT 2026-07-05 (dashboard-hub session).** Delivered as a page on the **epyc-root dashboard hub** (`:8100/kernel`), not the orchestration dashboard — the hub is the epyc-root-owned home for project-wide/artifact-backed pages (autopilot stays on :8000). The loop-owned contract producer is `epyc-inference-research/scripts/kernel_rnd/kernel_store.py export` (reuses `_pareto`/`correct==1`; wired into `kernel_sweep.sh`; default artifact `/mnt/raid0/llm/tmp/mi210-build/campaign/kernel_dashboard.json`, env `$KERNEL_DASHBOARD_JSON`); the hub reads it read-only with the freshness contract and the OBSERVATION banner. Seeded with the real `prefetch-validate` row (`samples/prefetch-validate.jsonl`) for preview. Original spec below, satisfied — self-contained data contract, no kernel context in the hub:
  - **Data source (read-only; append-only, so safe to poll):** SQLite `kernel_strategy_store.sqlite` (default `/mnt/raid0/llm/tmp/mi210-build/campaign/kernel_strategy_store.sqlite`, override `$KERNEL_STORE_DB`), table `runs` — columns `label, ts, git_sha, model, status, tbo, coherence, single_tps_baseline, single_tps_variant, delta_pct, aggregate_tps_variant, correct(1/0), mechanism(JSON), raw`. Schema + a `pareto`/`best`/`list` query CLI live in `epyc-inference-research/scripts/kernel_rnd/kernel_store.py`; the store is written by `kernel_sweep.sh` after each sweep, and each `raw` field is one `kernel_eval.sh` JSONL record (with the rocprofv2 mechanism deltas).
  - **Page content** (a kernel-autopilot page beside the orchestration pages): the **Pareto frontier over CORRECT runs only** — a fast-but-wrong variant must NEVER render as a win (lexicographic; mirror `kernel_store.py`'s `correct=1` filter) — plus current-best-per-model, the run log (label / git_sha / Δ% / correctness / mechanism), a correctness-margin column, and the per-run MemUnitStalled/Busy mechanism deltas.
  - **Discipline:** every number is an **OBSERVATION** (no P-GPU-1) — the page must NOT present them as decision-gating; carry the OBSERVATION tag + the "operator-only authorizes prod push" note, and apply the same freshness contract as the other dashboard pages ([[project_dashboard_freshness_contract]]).
  - **Dependency:** most valuable once the loop has run a live sweep (real rows in the store); a single validation row (`prefetch-validate`, +2.11%, MemUnitStalled −55%) exists now to build/preview against.
- **First real workload once Phase 0–2 land: the (b) L3-MoE/L15 MMQ-family bet** — its param sweep (tile size / VGPR budget / occupancy / quant type) IS the inner loop's job. (b) hand-runs it now; the loop automates it later.

## Open questions (now answered 2026-07-04 — see Operator decisions above)

- Is `kernel_eval.sh` (step 3) worth building as a standalone even if we never wrap the autopilot? (My view: yes — it pays for itself in fragility-removal on the next 3 levers regardless.)
- Autonomy ceiling confirmation: is "autonomous experimental-tree commits + OBSERVATIONS, human-gated at P-GPU-1 + prod promotion" the right line?
- Does this belong under the existing autopilot infra (strategy store / nightshift) or as a sibling? (Reuse recommended.)

## Progress checklist

- [x] Phase 0 kernel_eval.sh verify layer (BUILT + VALIDATED, research 48f990f) ✅
- [x] Phase 3 dashboard page :8100/kernel (BUILT 2026-07-05) ✅
- [x] Phase 1 kernel strategy store SQLite + Pareto/purge/rewind wiring (research `133017de`,
  `a1f38cd7`) ✅ 2026-07-17
- [ ] Phase 2 the nightshift loop (outer planner/critic + inner sweep->kernel_eval.sh->Pareto)
- [ ] First real workload: L3-MoE/L15 MMQ-family param sweep through the loop


## Auto-kernel revival — research-intake integration 2026-07-22 (Phase 2 from OpenHyra harness)
_Via /research-intake Stage-2 (intake-885 OpenHyra)._
- [ ] Build Phase 2 (autonomous inner verify loop) on OpenHyra's harness pattern: all-outcomes Experience Bank (`eb.py` append-only + fsync) as the Phase-1 strategy store; evidence-gated stop (the LLM may only REQUEST stop; deterministic guards on evaluator records dispose; `stopping.py:238-263`). Autonomy ceiling unchanged — experimental-tree commits + OBSERVATIONS only; P-GPU-1 / production push stays operator-gated
