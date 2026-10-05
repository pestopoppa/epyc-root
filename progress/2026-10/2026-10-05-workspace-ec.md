# 2026-10-05 — workspace-ec

## INF-59 YaRN CPU leg: Qwen3.6-35B-A3B, CN (native) vs CY2 (YaRN ×2)

**What ran:** a dedicated CPU block from 2026-10-04 21:18Z to ~03:15Z on 10-05. Qwen3.6-35B-A3B ran on CPU in two arms:
CN (native, 262,144 ctx) and CY2 (YaRN factor 2, 524,288 ctx, `--yarn-orig-ctx 262144`). The haystack grew by 8K-token
turns on a cached prefix, with needle probes at intervals and a short-context paired set (C1).

**Results:** `artifacts/yarn-e1-20261004/cpu_leg/` (VERDICT.md, verdict.json, block.log, SOURCES.sha256, copied from
`/mnt/raid0/llm/tmp/yarn-e1-20261004/cpu_leg/results/`; the server logs and 6.5 GB of slots stay in scratch).

| Criterion | Result |
|---|---|
| C1 short context, CY2 vs CN | 0 regressions / 84 (52 identical, 13 need review). Gate INCOMPLETE pending those 13 |
| C3 beyond native, CY2 | 5/5 at 323,527 tokens (needles up to 286K back), local check OK: **PASS** |
| Native range | CN 5/5 at 133K / 193K / 253K; CY2 5/5 at 133K / 253K |
| Decode tok/s, 34K / 133K / 253K / 323K | CN 20.4 / 6.4 / 3.7 / –; CY2 19.6 / 6.2 / 3.6 / 2.9 |
| Turn append cost (s per 8K turn) | 19.7 at 0 → 141 at 69K → 253 at 143K → 385 at 211K → 557 at 280K → 603 at 351K (CY2) |

**Contrast with the GPU 27B E1:** there, C1 had 3 regressions. This hybrid MoE showed no short-text regression under
YaRN ×2, and YaRN costs at most ~4% in decode at matched depth.

**Why CY2 stopped at 323K, not 512K:** the per-turn append cost grew to ~600 s per 8K turn at 350K, and the block ended.
The scheduler stopped the server cleanly with the slot saved at turn 42. CPU attention cost at depth is the
bottleneck, not YaRN.

**Process defect:** the first launch of both arms refused, rc=3, for missing proof lines, because `--verbosity 4` was
absent. This is the same defect as GPU E1. It was fixed in `yarn_cpu_leg.py`, and YARN-E1-PROOF now covers moving the
launch and preflight logic into a shared helper.

**Filed:** YARN-CPU-512k (finish CY2 to 512K in a later block) and YARN-CPU-ATTN (CPU attention at depth, handed to the
AK CPU FA route AKX-ALL-21). YARN-CPU is ticked ✅ 2026-10-05.

**Belief kernel:** the INF-59 source row in `scripts/vidya/adapters/README.md` now records that the CPU leg also ran
pre-hook, and VB-YARN-E1 carries a note naming `cpu_leg/verdict.json` as the projection input. The write side is still
unwired (VB-YARN-E1).

| File | Repo | Change |
|---|---|---|
| `handoffs/active/yarn-context-extension-research.md` | root | YARN-CPU ✅ with results; YARN-CPU-512k and YARN-CPU-ATTN filed; YARN-E1-PROOF scope extended |
| `handoffs/active/vidya-belief-substrate-program.md` | root | VB-YARN-E1 note for the CPU leg |
| `scripts/vidya/adapters/README.md` | root | INF-59 adapter row status |
| `artifacts/yarn-e1-20261004/cpu_leg/` | root | durable results copy + SOURCES.sha256 |
