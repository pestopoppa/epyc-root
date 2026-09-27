# DAR-LAT-3h — G1 result and disposition (2026-09-27)

**Outcome: T96.** Recorded only. **Nothing from this package is applied.** `PACKAGE.md` is pinned by sha256 in
`artifacts/operator/receipts/RATIFY-DAR-LAT-3H-CRITIC-THREADS-20260926.json`, so it is left byte-identical and this
file carries the disposition.

## Do NOT merge

None of the v2 outcome lanes is to be merged, in either repo:

- epyc-orchestrator `lane/dar-lat-3h-v2-20260927`, `lane/dar-lat-3h-v2-t48-20260927`
- epyc-inference-research `lane/dar-lat-3h-v2-20260927`, `lane/dar-lat-3h-v2-t48n-20260927`,
  `lane/dar-lat-3h-v2-t96-20260927`, `lane/dar-lat-3h-v2-t96n-20260927`

The v1 lanes (`lane/dar-lat-3h-20260926`, `-t96-`, `-live-`) were already superseded (`PACKAGE.md` header). The
launcher env fix that left this package (orch `5fd6bbdb` + `cfd77e6d`) is on orchestrator main and is unaffected.

## Why nothing is applied

The T96 outcome row (§3) would add only `GGML_FUSED_DECODE_OFF=1` at `-t 96`. That knob is inert under MTP, which G1
itself confirmed (the premise check below). The live critic already runs `-t 96`, which G1 measured as the better
shape. A reload to add an inert knob buys nothing and costs a critic restart, so no contention recertification is
needed either. Decision: the main session's recommendation, operator-aligned with the narrowed plan of 2026-09-27.

## The run

- Driver: epyc-orchestrator `scripts/server/critic_thread_gate.py` @ `8b7e24e3` (the signed gate). Experiment port
  `:18074`; live `:8074` untouched.
- Window: 2026-09-27 ~17:41Z to 18:57Z. 15 launches, 3 per arm, all clean: every request ok, THP mechanism check
  passed, env read back from `/proc`.
- Evidence (untracked, research repo): `/mnt/raid0/llm/epyc-inference-research/data/dar-lat-3h-gate-20260927T1740Z/`.
  Durable copies here: [`g1-result/verdict.json`](g1-result/verdict.json) (byte copy, sha256 `bdca6a84…aec5b`) and
  [`g1-result/summary.json`](g1-result/summary.json) (per-launch stats recomputed from the rows, plus the sha256 of
  every evidence file).
- Workloads: **W1** = the 24-prompt production mix, `max_tokens` 200 (the pre-registered primary). **W2** = the
  critique shape, 4 rotations of ~4k-token prompts, `max_tokens` 400 (reported as `w2_reading`, not decided on).

## Verdict (W1, the signed rule; ratios are candidate ÷ reference, lower = better)

| Comparison | Wall | TTFT | Rule | Reading |
|---|---|---|---|---|
| T96 vs L (premise) | 0.9879× | 0.9499× | non-inferior ≤ 1.03 / 1.10 | **holds**: FUSED_DECODE_OFF is inert |
| T48 vs T96 | 1.0385× | 1.0548× | parity needs wall ≤ 1.03 | **fails** |
| T48N vs T96N | 1.0323× | 1.0680× | parity needs wall ≤ 1.03 | **fails** |
| T96N vs T96 (shim) | 1.0094× | 1.0199× | adopt iff wall ≤ 0.98 | **no gain**, not adopted |
| T48N vs T48 | 1.0033× | 1.0327× | (reported) | — |

Coherence: minimum coherent count 20/24 on every arm (equal across arms; the 4 misses are the same prompts under the
driver's 4-gram check). Threads → 96; shim → no; outcome **T96**.

Mean decode tok/s (token-weighted per launch, mean of 3 launches):

| Arm | W1 | W2 |
|---|---|---|
| L | 43.374 | 32.054 |
| T96 | 44.644 | 32.134 |
| T96N | 44.612 | 31.484 |
| T48 | 43.796 | 33.237 |
| T48N | 43.268 | 32.023 |

The W2 reading reaches the same outcome (T96) with larger deficits for 48 threads: T48 vs T96 wall 1.0532×, TTFT
1.1134×. T48's slightly higher W2 decode does not survive its slower prefill. W2 is 4 requests per launch; it
supports, it does not decide.

**W3 (reported, not gating; one frontdoor `:8070` probe per launch, n = 3 per arm).** A 64-token frontdoor request
run during the arm's decode takes, relative to the same request solo: L 3.39×, T96 3.32×, T96N 3.35×, T48 2.89×, T48N
3.04× the wall (frontdoor decode 0.28-0.34× of solo). Fewer critic threads leave the frontdoor somewhat more room, but
co-running with the critic costs the frontdoor about 3× either way. This is a descriptive reading at n = 3, with no
floor, and it did not enter the rule.

## What this settles

- **`-t 96` is the critic's served optimum on v10 at the served shape** (`-c 262144`, MTP, `-ub 2048`, interleave,
  cpuset 0-95). The 2026-09-22 C3 ruling (`lineup-change-20260922.md` §C3: `NUMA_FULL_T48`, "`THREADS = 48  # NOT
  96: the served decode optimum`") is **superseded by this measurement**. `NUMA_FULL_T48` is not added to
  `stack_numa.py` (O1 is not merged).
- **`GGML_NOHUGEPAGE_PROCESS=1` (the THP shim) gives no gain on v10 at the served shape** (W1 1.009× wall; W2
  1.035×). Settled; do not re-open without a new shape or kernel.
- **`GGML_FUSED_DECODE_OFF=1` is inert under MTP** (premise holds).
- DAR-LAT-3g's "live `-t 96` vs recipe `threads: 48`" blocker is resolved in substance: the live shape is the
  measured-better one. DAR-LAT itself is FROZEN (narrowed plan), so 3g does not resume on this.

## Known residual (recorded, not applied)

The research lane R1, which corrects the recipe text, is not merged either, so `model_registry.yaml`'s
`architect_critic.recipe` (`threads: 48`, `cpu_shape: NUMA_FULL_T48`) and `qwen38_flash_next_recipe.py`'s `THREADS =
48` comment still state the superseded claim. Nothing reads that block (SSU-F11, `model-stack-single-source-update-
pipeline.md`), so it changes no launch. Any claim quoted from it must cite this result instead.

## Belief kernel

No source row exists for the critic thread gate (`scripts/vidya/adapters/README.md` has none; VB-SEL-LOADAB is the
DAR-LAT-3 load sweep's write side and is frozen). The result is recorded in the progress note
`progress/2026-09/2026-09-27-orch-design.md` only.
