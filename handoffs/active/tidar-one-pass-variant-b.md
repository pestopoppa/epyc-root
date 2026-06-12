# TiDAR-Pattern One-Pass Draft+Verify (Variant B)

**Status**: SPEC'D, not started (from the Fable 5 architecture review)
**Created**: 2026-06-12
**Priority**: GATED — on a Q4_K_M-quantizable TiDAR-class checkpoint existing (quality risk under Q4 is unmeasured); rank 4 in the findings-06 table: highest-ceiling, highest-variance kernel work remaining
**Spec**: [fable5-findings-06-kernel-and-concurrency.md](fable5-findings-06-kernel-and-concurrency.md) §1.1 + [nemotron-labs-diffusion-tri-mode.md](../../research/deep-dives/nemotron-labs-diffusion-tri-mode.md) §10.3 (Variant B) / §10.5 (decision sequence) / §10.6 (roofline promotion + caveats) — read before claiming any waypoint
**Related**: roofline findings at `data/cpu_optimization/2026-05-28-decode-roofline/findings.md` in epyc-inference-research (plain-text path); [cpu-inference-optimization-index.md](cpu-inference-optimization-index.md)

## Why

The roofline audit measured decode at 0.03–0.35% of theoretical FLOPS while
per-thread BW is saturated — no kernel that streams the same bytes faster can
win, but idle compute is free budget. TiDAR-pattern one-pass draft+verify
(single forward, unified causal+bidirectional mask) drafts and verifies in
one weight scan, ~halving per-cycle weight traffic; estimated 1.3–2×
algorithmic (findings-06 §1.1). The roofline audit itself promoted Variant B
from deep-dive §10.6 — this handoff surfaces it from that appendix into the
priority queue. ggml-op effort: 5–10 days (FlexAttention-equivalent mask).

## Waypoints

- [ ] **W1 — static mask-complexity analysis** (~1 day, no inference, ungated): TiDAR-pattern vs Linear-SS mask ggml-op complexity per deep-dive §10.4.2/§10.5 step 1 — read the antirez fork + intake-635 minimal reimpl for the mask trick, Nemotron paper §4.2 for the Linear-SS shape. Acceptance: written comparison; if comparable, Variant B is strictly cheaper than Variant A long-term on CPU.
- [ ] **W2 — checkpoint gate + Q4 quality validation** (bench-only when gate fires): watch for a Q4_K_M-quantizable TiDAR-class checkpoint (none exists today — deep-dive §10.4.3 calls this question dormant until then); on release, quantize and measure the quality delta (TiDAR-8B showed 6–9% HumanEval/MBPP loss at BF16; the gap may widen under Q4). Acceptance: go/no-go quality verdict recorded with eval protocol.
- [ ] **W3 — ggml-op implementation** (5–10 days, gated on W2 go): unified causal+bidirectional mask single-forward draft+verify path in the experimental fork (per `feedback_experimental_repo`). Acceptance: correctness vs reference AR output; acceptance-rate instrumentation in place.
- [ ] **W4 — canonical bench + decision memo** (~1 day): end-to-end decode vs AR baseline per the canonical protocol; synthesize into the Variant A vs B memo per deep-dive §10.5 step 4. Acceptance: claim filed per MEASUREMENT.md grammar; promote/park decision recorded.

## Gates & pitfalls

- The win is an algorithmic acceptance multiplier, NOT bandwidth recovery — the "2–4× BW headroom" framing was falsified 3× (deep-dive §10.6 caveat 4); do not re-derive expected gains from the 460 GB/s gap.
- W3 must not start before the W2 checkpoint gate fires; W1 is the only ungated work today.
- Estimated 1.3–2× is an estimate from the roofline audit, not a measurement — never quote it without that provenance.
- The §10.6 roofline run was on a degraded host (13.29→45.80 t/s recovered post-rewarm); the qualitative compute-idle verdict stands, but absolute BW numbers from that session are not claim-grade.
- All experimental kernel work in llama.cpp-experimental, never the production fork; defer C1/C2 hybrids until a single-arch variant works (deep-dive §10.5).

## Reporting

Tick waypoints here + one-line progress entry per session; on full completion delete the master-index row and move this file to `completed/`; every number follows the [MEASUREMENT.md](../../MEASUREMENT.md) claim grammar.
