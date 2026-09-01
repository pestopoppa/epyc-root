# Qwen4exp uniform-IQ4_XS baseline control (requant A/B)

**Status**: MEASURED 2026-08-31 (same-day, ad-hoc audit session) — T1-T5 done; **open: the operator adoption decision** (see Results)
**Created**: 2026-08-31 (spun out of the operator-commissioned INF-67 audit)
**Priority**: MEDIUM — ~1 short session, cheap; but the INF-67 headline inherits this control's honesty
**Categories**: hardware_optimization, benchmarking, quantization
**Workstream**: Inference Acceleration
**Parent index**: [`inference-research-index.md`](inference-research-index.md) (row INF-68)
**Related**:
- [`cpu-fused-decoder-blocks.md`](cpu-fused-decoder-blocks.md) (INF-67) — the consumer of this control
- [`batched-decode-measurement.md`](batched-decode-measurement.md) — the canonical NUMA recipe (interleave + no-mmap)
- `progress/2026-08/2026-08-28.md` @ `165c760d` — all six prior qwen4exp measurement rounds (read via `git show`; the working-tree file may differ)

## Why

INF-67's fused-decode headline will be quoted against the UD-IQ4_XS baseline (tg128 13.46 t/s t48 / 13.95 t64, interleave + no-mmap, ~74 ms/token). But the pre-NUMA record (progress 08-28, entries 4–5) measured a **uniform** IQ4_XS requant at tg 8.89 vs the UD file's 7.28 — **+22%** — because the UD mix's experts are actually IQ3_S ×94 + IQ4_NL ×43 + Q8_0 ×5, a dequant-heavy mix on the IQK decode path, while uniform IQ4_XS (type 14) is the fast path. The uniform artifact (and its FP8 → Q8_0 source chain) was destroyed in the 08-28 `rm -rf` incident and was never re-created after the NUMA-corrected recipe landed. If ~+20% reproduces post-NUMA, the honest top-spec baseline is ~16–17 t/s, and any "13.5 → X" fused headline would overstate the gain (headline policy: compare against the TOP optimized spec, and headlines must be the production-optimal recipe).

## Tasks

- [x] T1 — **Requantize** UD → uniform: `llama-quantize --allow-requantize` from the UD-IQ4_XS shards to uniform IQ4_XS, output `/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/IQ4_XS-uniform/` (~95–100 GB, ~12 min; single-model-root policy — no new root, no symlinks). Label it **SPEED CONTROL**: quant-from-quant (UD source) is valid for the type-mix speed comparison but is NOT quality-representative (the destroyed 08-28 original came from FP8 → Q8_0).
- [x] T2 — **Clean bench binary at the pre-fusion anchor** `7cdd7c97b`: local pinned clone — `git clone --no-checkout /mnt/raid0/llm/llama.cpp-cpu-fusion-20260829 /mnt/raid0/llm/tmp/inf68-baseline-tree && git -C /mnt/raid0/llm/tmp/inf68-baseline-tree checkout --detach 7cdd7c97b` — then CPU-only build with `GGML_IQK=1`; prove linkage with `verify_ggml_linkage.sh` and `[iqk] ACTIVE` in the load log. Do NOT `git worktree add` against the live fusion clone (the INF-67 session owns it) and do NOT reuse its `/tmp/qwen4exp-builds` binaries (the fused path is default-ON there and carries un-gated debug I/O).
- [x] T3 — **A/B bench**, same binary, same session, same box state: llama-bench, `numactl --interleave=all`, `-mmp 0`, the mandatory OMP env stack, t48 AND t64, r5, tg128 + pp512, both files (UD and uniform). Throttle-check the host first; load-gate against the autokernel loop's periodic 96-core builds; hold the CPU region claim on the session bus for the run window. Never `run_benchmark.py`; never pipe llama output.
- [x] T4 — **Correctness pairing** on the uniform file (same binary): greedy "Paris"-style sanity + IQK-engaged confirmation. This ratifies the speed baseline only — not serving quality.
- [x] T5 — **Persist + route**: progress entry with the 2×2 cells (file × threads) carrying the claim tuple per `agents/shared/MEASUREMENT_POLICY.md`; routing amended: the bus outbox is roster-only and this session is ad-hoc, so the route to INF-67 is this repo record (progress + this handoff + index row), which that session syncs at its boundaries; closed out per the outcome contract below.

## Outcome contract

- **Uniform ≈ UD post-NUMA (≤~3%)**: the 13.5 t/s / 74 ms baseline is honest — record the null result, move this handoff to completed, delete the row.
- **Uniform materially faster**: INF-67's baseline and target arithmetic re-anchor to the uniform numbers. ALSO file (do not act on) a decision-package stub for the operator: "adopt uniform IQ4_XS — or a from-source requant, which requires re-downloading the FP8 original (~250 GB at ~9–16 MB/s, overnight) — as the serving quant for this model?" with options + tradeoffs + recommendation.

## Constraints

- Zero writes to the INF-67 worktree, branch, or `/tmp` build dirs; zero interaction with that session's processes.
- CPU-only (the GPU embargo is irrelevant here), but the bench window still needs the region claim — concurrency is by-design and contention is data, so claim, don't assume a quiet box.
- If the FP8 re-download branch is ever taken: one download at a time on this host (racing resume corrupts `curl -C -`).

## Results (2026-08-31) — measured; decision open

Evidence: `epyc-inference-research/data/inf68-uniform-iq4xs-ab-20260831/` (SHA256SUMS) @ `0dbc9992`.
Full record: `progress/2026-08/2026-08-31-inf68-baseline-control.md`. Clean, verified windows
(per-arm load-gates + in-window contamination samplers), build 10151 @ `7cdd7c97b`, canonical recipe:

| file | t48 tg128 | t64 tg128 | t48 pp512 | t64 pp512 |
|---|---|---|---|---|
| UD-IQ4_XS | 9.13 ±0.04 | 8.86 ±0.08 | 130.7 ±9.0 | 128.4 ±1.2 |
| uniform IQ4_XS | **10.52 ±0.05** | 9.79 ±0.08 | 161.2 ±0.5 | 169.4 ±1.5 |

1. **The outcome contract's "materially faster" branch fired**: uniform +15.2%/+10.5% decode,
   +23-32% prefill. Greedy Paris PASS on the uniform file. INF-67's baseline and any
   "UD → X t/s" headline must re-anchor to the uniform numbers (headline policy).
2. **Bonus finding**: the documented UD 13.46 t/s record does not reproduce on the current box
   state (9.13-9.18 clean; `-fa 1` refuted as the cause). INF-67 should re-anchor on its own
   build at its own boundary; its same-window fused-vs-graph ratios are unaffected.
3. Numbers are **observations** per `MEASUREMENT_POLICY` — a codified `bench_canonical`
   attestation run is the ratification gate for adoption.

### Operator decision — adopt uniform IQ4_XS for qwen4exp CPU work?

*(Master-index row **OP-32**; minted as OP-30 and renumbered at the 2026-09-01 reconciliation, where the autokernel lane had concurrently minted OP-30/31.)*

- [ ] **Option A**: adopt as the serving + bench reference. +15% decode / +23-32% pp for
  +4.4 GB file size. Requires: codified attestation run + a quality gate (this artifact is
  quant-from-quant off the imatrix-tuned UD — quality unverified beyond greedy sanity).
- [ ] **Option B (recommended)**: keep UD canonical for serving (imatrix pedigree); the uniform
  file becomes the REQUIRED comparison baseline for INF-67 headlines and CPU-kernel work.
  Zero quality risk, honest headlines, decision reversible to A after a quality run.
- [ ] **Option C**: from-source uniform requant (FP8 re-download ~250 GB) — **blocked on disk**
  (90 G free) until the reclaim sweep lands; strictly dominates A on quality if taken later.

Recommendation: **B now**, revisit A/C after the quality suite and the disk reclaim.
