# 2026-08-14 — AutoKernel inaugural-session wrap-up

## Scope

This delegated wrap-up records the completed AutoKernel portfolio-v2 product, its expanded historical
memory, and the first live launch attempt. It ran from isolated root branch
`codex/autokernel-inaugural-wrap-up-20260814`; it did not touch frozen production or the shared
`llama.cpp-experimental` checkout.

## Product completed

| Surface | Immutable research commit | Durable result |
|---|---|---|
| Critic boundary | `4d2e69f8` | Claude Fable 5/high is the sealed pre-build critic/veto actor. |
| Portfolio/source authority | `2153ccac` | Evidence-bound portfolio v2, reviewed source visibility, controller-owned dispatch, and balanced S1/S2 measurement authority landed. |
| Legacy hypothesis memory | `c6a98db8` | L1-MoE `mmid`, L6 Q8_0 SoA repack, and L21 Q4_K MMQ dequant-GEMV were preserved with regime-specific lifecycle state. |

The final bundle contains 18 hypotheses, 17 scoped do-not-repeat records, and four hypotheses eligible
for the exact Qwen2.5-Coder-0.5B frame. The hardware-free product suite passed 235/235, the dedicated
legacy-memory gate passed 4/4, and public validation remained config-only with
`inference_executed=false`. Canonical deployment:
`/mnt/raid0/llm/autokernel/deployments/gpu-discovery-portfolio-v2-memory-final-v1`; graph SHA-256
`508ad0216b89e81f27a7492d350c5ef084b64176ebd93e1d164cb69902e6895d`.

Root documentation commits `0d05908d`, `ae030298`, and `52dce491` recorded the portfolio, the three
legacy levers, SC32's prospective Vidya write-side obligation, and the original launch guard. This
wrap-up merges those records onto current `origin/main` history. The earlier statement that the dirty
shared experimental checkout blocked launch is superseded: launch preflight resolved exact sealed
instrument ref `81bf32f11b4a421880e8f25faec3e4ba872363f0` in its dedicated clean worktree and left the
unrelated shared checkout untouched.

## Inaugural launch attempt — failed safe before compute

The first public launch began at `2026-08-14 16:23 UTC` from product commit `c6a98db8` and the bundle
above. Sol selected `akh-v2-q5-type-specific-dequant` and authored its source patch/plan. The
controller then exited `rc=1` at `discovery_controller.py:816` with
`DiscoveryControllerError: planner bounded dispatch schema mismatch`.

The refusal occurred before Fable critic review, build, profiling, or GPU execution. Device samples
overlapping the attempt saw no KFD process and no VRAM residency. Therefore:

- the attempt is a controller launch-path failure, not a Q5 hypothesis result;
- it produced no performance measurement, candidate ranking, bank, champion, or promotion authority;
- its empty event/hypothesis journals must not be reconstructed or treated as evidence; and
- SC32 remains prospective: wire producer-authored Vidya rows before the first successful source
  screen and never back-fill this pre-hook refusal.

The live next action is to repair the bounded-dispatch producer/validator contract, preserve the
actor-invented-dispatch refusals, reseal a fresh graph/bundle, and relaunch from a new immutable
identity. The owning launch session is actively doing that work; this failed attempt is preserved
rather than resumed.

## Wrap-up verification and authority boundary

- README freshness check: clean, with no warnings.
- GitNexus: the isolated root worktree was indexed successfully (43,583 nodes, 58,760 edges, 481
  clusters, 300 flows); no code symbol changed, so no symbol-impact result applies.
- Root/research promotion merge preflights showed no textual conflict at the sampled tips.
- Index regeneration, wiki compilation, and promotion were not run: the wrap-up lease requires a
  truthful roster ID, while this delegated subagent has only canonical task identity
  `/root/session_wrap_up`. Neither borrowing another main's ID nor fabricating one is authorized.
