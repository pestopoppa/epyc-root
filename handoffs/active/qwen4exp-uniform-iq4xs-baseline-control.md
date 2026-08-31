# Qwen4exp uniform-IQ4_XS baseline control (requant A/B)

**Status**: READY — claimable by any idle session; fully independent of the INF-67 fusion worktree (zero writes there)
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

- [ ] T1 — **Requantize** UD → uniform: `llama-quantize --allow-requantize` from the UD-IQ4_XS shards to uniform IQ4_XS, output `/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/IQ4_XS-uniform/` (~95–100 GB, ~12 min; single-model-root policy — no new root, no symlinks). Label it **SPEED CONTROL**: quant-from-quant (UD source) is valid for the type-mix speed comparison but is NOT quality-representative (the destroyed 08-28 original came from FP8 → Q8_0).
- [ ] T2 — **Clean bench binary at the pre-fusion anchor** `7cdd7c97b`: local pinned clone — `git clone --no-checkout /mnt/raid0/llm/llama.cpp-cpu-fusion-20260829 /mnt/raid0/llm/tmp/inf68-baseline-tree && git -C /mnt/raid0/llm/tmp/inf68-baseline-tree checkout --detach 7cdd7c97b` — then CPU-only build with `GGML_IQK=1`; prove linkage with `verify_ggml_linkage.sh` and `[iqk] ACTIVE` in the load log. Do NOT `git worktree add` against the live fusion clone (the INF-67 session owns it) and do NOT reuse its `/tmp/qwen4exp-builds` binaries (the fused path is default-ON there and carries un-gated debug I/O).
- [ ] T3 — **A/B bench**, same binary, same session, same box state: llama-bench, `numactl --interleave=all`, `-mmp 0`, the mandatory OMP env stack, t48 AND t64, r5, tg128 + pp512, both files (UD and uniform). Throttle-check the host first; load-gate against the autokernel loop's periodic 96-core builds; hold the CPU region claim on the session bus for the run window. Never `run_benchmark.py`; never pipe llama output.
- [ ] T4 — **Correctness pairing** on the uniform file (same binary): greedy "Paris"-style sanity + IQK-engaged confirmation. This ratifies the speed baseline only — not serving quality.
- [ ] T5 — **Persist + route**: progress entry with the 2×2 cells (file × threads) carrying the claim tuple per `agents/shared/MEASUREMENT_POLICY.md`; route the result to the INF-67 session via the session bus using structural `needs_routing_to`/`action_required` fields (never payload prose) so it re-anchors its baseline; then close out per the outcome contract.

## Outcome contract

- **Uniform ≈ UD post-NUMA (≤~3%)**: the 13.5 t/s / 74 ms baseline is honest — record the null result, move this handoff to completed, delete the row.
- **Uniform materially faster**: INF-67's baseline and target arithmetic re-anchor to the uniform numbers. ALSO file (do not act on) a decision-package stub for the operator: "adopt uniform IQ4_XS — or a from-source requant, which requires re-downloading the FP8 original (~250 GB at ~9–16 MB/s, overnight) — as the serving quant for this model?" with options + tradeoffs + recommendation.

## Constraints

- Zero writes to the INF-67 worktree, branch, or `/tmp` build dirs; zero interaction with that session's processes.
- CPU-only (the GPU embargo is irrelevant here), but the bench window still needs the region claim — concurrency is by-design and contention is data, so claim, don't assume a quiet box.
- If the FP8 re-download branch is ever taken: one download at a time on this host (racing resume corrupts `curl -C -`).
