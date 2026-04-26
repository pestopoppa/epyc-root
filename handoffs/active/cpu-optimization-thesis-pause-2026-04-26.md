# CPU Optimization Pause & Reorganization — 2026-04-26

**Purpose**: stop, take stock, separate what we KNOW from what we ASSUMED, and rebuild the priority queue from honest premises.

---

## What changed in the past 36 hours

We went from "EP is the headline win" to a much more nuanced picture, and the corrections matter:

| Date | Claim | Status |
|------|-------|--------|
| 2026-04-25 | "EP +100% on Qwen3.6-35B-A3B, bit-identical PPL" | **Half right** — PPL is bit-exact, but +100% was vs `--numa distribute` baseline; vs honest `-t 96` baseline it's +17% — **AND on the proper cold canonical (`--mmap 0 + --interleave=all`) it's +1.6% (noise) — see compounding matrix 2026-04-26 evening** |
| 2026-04-25 | "REAP-246B EP regresses because bandwidth-saturated" | **Wrong** — 145 GB/s used at baseline = 32% of 460 GB/s, not saturated |
| 2026-04-25 | "EP wins for <50B class, fails for >150B" | **Partially wrong** — Qwen3-Coder-30B-A3B (worker_explore) regresses -10%, contradicting the size heuristic |
| 2026-04-26 | "+25% on Qwen3-Coder-30B-A3B" | **Wrong baseline** — vs honest baseline, EP is -10% |
| 2026-04-26 | "+64% on Qwen3-Next-80B" | **Wrong baseline** — vs honest baseline, EP is at parity |

**Confirmed wins that survive scrutiny:**
- **PPL bit-identical** on EP+drone+shard (32-chunk WikiText-2 on Qwen3.6) — the implementation is *correct*, just rarely *useful*
- ~~**Qwen3.6-35B-A3B at +17%** with honest baseline — the only meaningful production EP win~~ — **DOWNGRADED 2026-04-26 evening**: the +17% was vs the warmed mmap=1 baseline. On the proper cold canonical (`--mmap 0 + --interleave=all`) EP delivers +1.6% (noise). The biggest practical gain on Q8_0 is the canonical config itself (+44% vs warmed mmap=1, no code).
- **REAP-246B / M2.7 regress** — direction was right, framing (bandwidth) was wrong

**Unexplained findings that need investigation:**
- Qwen3-Coder-30B-A3B at 44.71 t/s today vs 49.34 t/s logged 2026-04-24 = **~10% regression** somewhere in the experimental kernel commits
- Why `--numa distribute` HURTS these MoE models (it's supposed to spread bandwidth — should be neutral or positive)
- What IS the actual bottleneck on REAP-246B at 6.89 t/s when we have 315 GB/s of unused aggregate bandwidth

---

## Outstanding hypotheses (separating from claims)

### H1: There's a real ~10% regression on Qwen3-Coder-30B-A3B
- **Evidence**: 49.34 t/s logged 2026-04-24, 44.71 t/s measured today, same model+config protocol
- **Confidence**: high; reproduced with 5-iteration std ± 0.22 today
- **Test**: `git bisect` between 2026-04-24 reference commit and `feature/cpu-ep-inter-process` HEAD on Qwen3-Coder-30B-A3B baseline. Find the regressing commit.
- **Priority**: **must-fix** before any v5 push; this is exactly what the user's track 2 audit catches.

### H2: The real decode bottleneck on >100B MoE is not bandwidth
- **Evidence**: master-handoff-index.md line 59: "Qwen3.6-27B Q8_0 ceiling is NOT BW-bound — only 26% of 460 GB/s"; REAP-246B uses 32% of 460 GB/s at baseline
- **Confidence**: high; cited from prior measurements
- **Candidate causes** (per CPU2 handoff): cross-CCD coordination overhead, per-thread compute throughput, cache-miss patterns, cross-NUMA latency (not aggregate BW)
- **Test**: `GGML_PERF=1` profile on REAP-246B at 96t baseline. Per-op time breakdown. Identify the op consuming most time + whether it's wall-clock or DRAM-wait.
- **Priority**: **high** — diagnoses whether ANY further optimization (EP, L3aaN, kernel work) can plausibly help this class

### H3: `--numa distribute` actively hurts MoE decode
- **Evidence**: Qwen3.6-35B-A3B 9.93 (with) → 14.69 (without) = +48%; Qwen3-Coder-30B-A3B similar pattern
- **Confidence**: medium; observed across 3 models but not investigated mechanistically
- **Test**: re-bench with `numactl --interleave=all` vs default, both with and without GGML_NUMA_WEIGHTS=1, on a representative MoE
- **Priority**: medium — explains why our "EP wins" looked larger than they are; corrects production guidance

### H4: EP's value is genuine but narrow
- **Evidence (DOWNGRADED 2026-04-26 evening)**: Qwen3.6-35B-A3B EP shows +17% only against the warmed mmap=1 baseline. On the proper cold canonical it's +1.6% (noise). PPL bit-exact preserved (the code is correct, the throughput claim was the artifact).
- **Confidence**: high (after honest baseline correction)
- **Implication**: production deployment of EP is for ONE model class, not the full MoE lineup
- **Decision**: still worth shipping, but production wiring scope is narrower than originally thought

### H5: Qwen3.5-family has a kernel-level slowdown vs Qwen3.6
- **Evidence**: Qwen3.6-35B-A3B Q8_0 baseline 14.69 t/s; Qwen3-Next-80B-A3B Q4_K_M baseline 23.34 t/s — the 80B model is *faster* than the 35B model. Likely Qwen3.5 architecture (DeltaNet + attention hybrid) has worse single-instance perf than newer Qwen3 designs
- **Confidence**: low; speculative
- **Test**: profile both models at baseline, compare per-op breakdown
- **Priority**: low — interesting but not blocking deployment

---

## Priority queue — track 1 (finish CPU optimization handoffs)

In order of "must-do before v5 push":

1. **H1 regression** (Qwen3-Coder-30B-A3B 49.34 → 44.71): bisect, identify, fix or revert. Cannot ship a regression to production.
2. **H2 bottleneck profile** (`GGML_PERF=1` on REAP-246B): diagnose what's actually limiting decode. Result determines whether L3aaN reboot or any future kernel work is even worth pursuing for this class.
3. **H3 `--numa distribute` investigation**: minor — affects production guidance phrasing but not deployment correctness.

H4 production routing is a *consequence* of (1)-(3), not a separate work item.
H5 is research-grade, defer.

## Priority queue — track 2 (audit experimental kernel)

After tracks 1 ✓:

1. List ALL env-gated flags introduced across CPU1-CPU15 work
2. For each: production-ready, deprecated, or experimental?
3. PPL gate every "production-ready" flag combination
4. Document the recommended config for each model class
5. Run the benchmark suite at the recommended config — final sign-off numbers

## Priority queue — track 3 (push to production-consolidated-v5)

After track 2 ✓:

1. New branch off current `main` of upstream llama.cpp
2. Cherry-pick the audited-clean commits
3. Build, smoke test
4. Update production llama-server symlink
5. Re-bench production lineup at v5 — confirm no regressions vs current production

## Priority queue — track 4 (rewire orchestration)

After track 3 ✓:

1. `model_registry.yaml` `deployment.mode` schema
2. `orchestrator_stack.py` env-injection for EP-mode roles
3. Auto-selector by model class
4. Per-role validated config

---

## What I'm asking the user to confirm

1. **Is this the right priority order?** The four tracks above (1: finish optimization, 2: audit, 3: v5 push, 4: orchestration) match your earlier guidance. Within track 1, is H1 (regression bisect) the right first move, or should H2 (bottleneck profile) come first?

2. **What does "SG4" / "MoE sg4 models" refer to?** I don't recognize this name. Production lineup includes Qwen3.6-35B-A3B, Qwen3-Coder-30B-A3B, Qwen3-Next-80B, REAP-246B. Test models include gemma-4-26B-A4B-it (already tested), MiniMax-M2.7. If you meant gemma-4 specifically, only the A4B variant is MoE. If you meant GPT-OSS or another architecture, please confirm so I can locate or download.

3. **No more inference until plan confirmed.** I shouldn't run more measurements until the methodology question is settled — last few iterations had baseline-config errors that polluted the conclusions. What's the right baseline for production-relevant comparisons? Recommend: `taskset -c 0-95 -t 96 -fa 1` (matches 2026-04-24 protocol) without `--numa distribute`, no GGML_NUMA_WEIGHTS unless explicitly testing it.

---

## Useful artifacts already on disk

- **Honest measurements 2026-04-26**: `progress/2026-04/2026-04-26.md` Round 2 table
- **Bandwidth ceiling reference**: `master-handoff-index.md` line 59 ("26% of 460 GB/s" cite)
- **CPU2 ceiling explanation**: `cpu-shape-specialized-gemv-decode.md` lines 88-138 (perf profile run, ceiling explained — relevant prior art for H2)
- **NPS reboot runbook**: `nps-reboot-runbook.md` (L3aaN gating; updated yesterday with shard-based memory budget)

## Acknowledged debt

- I labeled "+100%" win without checking that the baseline was the production-relevant config. Won't repeat.
- I framed REAP-246B as bandwidth-saturated without checking actual GB/s utilization. The 460 GB/s aggregate vs 145 GB/s used = obvious gap, missed.
- I should have run a baseline-determination pass first (proper `-t 96` measurement on production-relevant configs) BEFORE running EP comparisons.

The corrections are now in `progress/2026-04/2026-04-26.md` and the related handoffs. Going forward, every benchmarking session starts with a baseline-determination pass and a `pgrep -af "llama"` zombie check.
