# GPU-Drafter Break-Even Model - 2026-07-18

**Status**: zero-inference DR-1 model. This document uses existing Stage-1/Stage-2/K35
artifacts only; it does not make new measurement claims.

## Model

For a speculative round with maximum draft depth `K` and per-position acceptance
probability `a`, the expected number of output tokens advanced is:

```text
E(a, K) = 1 + a + a^2 + ... + a^K
```

Let `B` be target no-spec decode throughput, so one baseline target token costs
`1 / B`. Let `F(K)` be the target verify pass cost in baseline-token units, and
let `H(K)` be all drafter, synchronization, transfer, sampler, and control overhead
in the same units.

```text
spec_speedup = E(a, K) / (F(K) + H(K))
break_even   = F(K) + H(K) < E(a, K)
```

This is intentionally stricter than an alpha-only rule. High `a` helps only if
the external drafter/control path is cheap enough. If `F + H` already exceeds
the maximum possible `E(1, K)`, no acceptance rate can make that lane win without
reducing overhead or increasing useful draft depth.

## Calibration Rows

| Evidence | Baseline | Spec lane | Draft shape | Acceptance | Speedup | Implied `F+H` | Verdict |
|---|---:|---:|---|---:|---:|---:|---|
| Stage-1 CPU target + MI210 external Qwen3.5-0.8B drafter (`stage1_mi210_gpu_drafter_20260717T0518Z_drafttreeunifiedkv`) | `22.19 t/s` | `20.30 t/s` | external, `K=1` | `508/508` | `0.915x` | `2.186` | Fails even at perfect acceptance: `K=1` max `E=2`. |
| Stage-2 MI210 frontdoor no-spec vs co-resident external drafter (`stage2_mi210_gpu_residency_20260717T0510Z`) | `101.64 t/s` | `36.06 t/s` | external, `K=1` | `508/508` | `0.355x` | `5.637` | Structurally dead as tested; even `K=4`, `a=1` maxes at `E=5`. |
| Stage-2 MI210 frontdoor no-spec vs native MTP, short prompt pack | `101.64 t/s` | `96.40 t/s` | native MTP, `K=3` | `683/1002` | `0.948x` | `2.598` | Slight fail on this short shape; needs `a≈0.717` at `K=3` with same overhead. |
| K35 Gate-R 8K MI210 no-spec vs native MTP (`frontdoor_pgpu1_candidate_20260718Tquiet`) | `95.39 t/s` | `119.69 t/s` | native MTP | `3835/3835` | `1.255x` | empirical pass | Long repetitive shape amortizes native MTP and passes. |
| K35 context edges MI210 no-spec vs native MTP (`frontdoor_context_edges_20260718Tcodex`) | `101.52/78.14 t/s` | `123.55/105.17 t/s` | native MTP | `767/767` both | `1.217x/1.346x` | empirical pass | Native MTP wins at 2K and 32K on this task class. |

`F+H` is computed as `E / observed_speedup` when a reliable `K` is known. For
empirical pass rows where the runner reports accepted drafts but not a stable
round-depth model, the observed speedup is the authority.

## Decision Rules

1. Do not revive the measured external-drafter Stage-1/Stage-2 designs as-is.
   They lost despite `a=1.0`, so their blocker is overhead/control cost, not
   acceptance alignment.
2. For any new external lane, require a dry model row before implementation:
   proposed `K`, expected `a`, expected `F+H`, and artifact-derived source for
   each term. If `F+H >= E(a,K)`, do not build.
3. For `K=1`, perfect acceptance only gives `E=2`; therefore any one-token
   external drafter must keep `F+H < 2`. The measured Stage-1 row is `2.186`;
   Stage-2 external is `5.637`.
4. Increasing `K` only helps if the implementation can actually draft useful
   consecutive tokens cheaply. With Stage-2 external's measured `F+H=5.637`,
   break-even requires at least `K=6` with `a≈0.927`, or `K=8` with `a≈0.877`.
   That is not credible without a different control path.
5. Native MTP is different: its head is near-free and already integrated. It can
   lose on short/tiny verifier-like outputs but wins on long repetitive structured
   frontdoor output. Routing should therefore expose a task-class rule rather than
   a global on/off.

## Implications For DR-0

The DR-0 quant-asymmetric same-model self-spec measurement should report more
than alpha:

- `draft_n`, `draft_n_accepted`, and token-weighted `a`
- chosen `K` / acceptance-by-depth curve
- no-spec target throughput `B`
- spec throughput and implied `F+H`
- whether speedup remains positive after cleanup/fresh-server overhead and quality checks

The go/no-go threshold is not `a >= 0.7` by itself. It is:

```text
E(a, K) > F(K) + H(K)
```

Only lanes satisfying that inequality should advance to serving work.
