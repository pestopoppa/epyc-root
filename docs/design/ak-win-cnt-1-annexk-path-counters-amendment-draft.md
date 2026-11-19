# AK-WIN-CNT-1 — Annex K amendment DRAFT: in-window path counters (human-amendment-only)

Status: DRAFT for the operator. Nothing here amends `measurement/protocols/kernel-research.md`; that file is a measurement trust boundary
and changes only by human amendment. Source: intake-2562#record (Resin keeps `graph_counts` / `overlap_counts` that exclude warmup).
Box: `handoffs/active/autokernel-loop.md` AK-WIN-CNT-1. Evidence for the controls: row `ak-win-cnt-1-20261119-r1` (published, not yet run).

## Problem

Annex K "Record grammar" proves WHAT was measured (anchor, recipe, scope, raw samples) but not HOW the timed window executed. T0 checks a dispatch
trace; T1 and T2 do not re-prove the path. A window that silently ran eager launches instead of hipGraph replay (graphs disabled by an env var, a
graph-incompatible node, a shape change after warmup) is a different measurement with a plausible number.

## Proposed counter set (diagnostic sidecar, v1)

Captured in-process by the HIP/CUDA backend, reset directly before the first timed repetition (after every warmup), read directly after the last:

| counter | meaning |
|---|---|
| `calls` | graph_compute calls in the window |
| `replay` | calls executed by `cudaGraphLaunch` of an existing executable |
| `capture` | calls that captured/instantiated (or updated) a graph and launched it |
| `eager` | calls executed node by node |
| `graph_resets` | post-warmup property changes (a new shape; the next launch may first-use kernels) |

Implementation: `patches/path-counters.patch` of row `ak-win-cnt-1-20261119-r1` (C10 `7f1bd044b`, `ggml-cuda.cu` + `llama-bench`; default off,
`GGML_CUDA_PATH_COUNTERS=1`; llama-bench prints `autokernel_path_counters: {json}` on stderr). Not covered in v1: code-object load / JIT events (HIP lazy
loading is not observable in-process; `graph_resets` and `capture` after warmup are the proxy; a rocprofv3 `hipModuleLoad` trace is the follow-on source).

## Proposed text (to add to "Record grammar")

> A T1 or T2 search record carries a **path sidecar**: the in-window counters above, written next to the raw samples, referenced from the record as
> `path=<sidecar_ref>` and covered by the record's raw-sample hash. The recipe constructor declares the intended `path_class` (`graphed` or `eager`).
> The sidecar is evaluated against it: for `graphed`, a window is **path-valid** iff `replay/calls >= 0.90`, `eager/calls <= 0.05` and
> `(capture + graph_resets)/calls <= 0.05`; for `eager`, iff `replay == 0`. The thresholds are declared constants of the evaluator bundle, not per-run knobs.

## Proposed text (to add to "What voids a run")

> ... a window whose path sidecar is missing, unreadable, not covered by the raw-sample hash, or not path-valid for the recipe's declared `path_class`
> (a **path mismatch**) ...

A path-mismatch window is journaled `INVALID` with its reason like any voided run; it never ranks, banks or composes.

## Controls (from the row; the sidecar ships only if all hold)

1. Degraded negative: `GGML_CUDA_DISABLE_GRAPHS=1` window must be FLAGGED with `replay == 0` and `eager == calls`.
2. A/A: two default windows of the same recipe are both path-valid and their `replay` counts differ by <= 5 percent.
3. Frozen anchor and one candidate each carry a sidecar; the raw counters of every window are kept.

## Open points for the operator

- Whether the counters live in the evaluator bundle (preferred: one bundle hash covers the thresholds) or in the recipe.
- Whether a path-mismatch is VOID (proposed) or only a caveat on T1; the box proposes VOID because a different path is a different measurement.
- Code-object / JIT events: ship v1 without them, or hold the amendment for a rocprofv3-based source.
