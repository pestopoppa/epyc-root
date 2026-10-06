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

## OP-76..79: Operator decisions applied and completed

### OP-76: STACKCHG-8083BATCH-20261004 signed
- Receipt `RATIFY-STACKCHG-8083BATCH-20261004.json` copied from shared clone to `artifacts/operator/receipts/`.
- Stack change: `:8083` `-b 512 -ub 512` + `--no-cache-idle-slots` (KVU-16f + UFH14-B4j).
- Applies at next :8083 relaunch.

### OP-77 & OP-78: Orchestrator fast-forward
- Orchestrator main fast-forwarded to `aeb3a330` (REGION-SIBLING-1 merged).
- Shared orchestrator checkout updated to `aeb3a330` (includes device-busy fix `6ce26fc9`).
- Both changes deployed and verified.

### OP-79: GPU-window watchdog cron installed
- Cron `/scripts/server/gpu_window_watchdog.cron` installed on HOST at ~04:46Z.
- First tick logged at 04:47:01Z, writing executor-status verdict to `/mnt/raid0/llm/tmp/gpu-window/mi210.json.executor-status.json`.

## STACKCHG-8083BATCH research half pushed
- Research branches: `7c3ff2b4` (A, idle slots) and `f1c6fef5` (B, `-b`/`-ub` 512).
- Evidence citations made durable under `data/stackchg-8083batch-20261004/`.
- Orchestrator reload half still pending (no relaunch until OP-76 applied).

## UFH14-B4g-1: root cause identified
- Issue: no `prompt_save` lines on current `:8083` shape.
- Root cause: lines are TRACE level (4) in v10, default logging is level 3; 489 old lines came from two launches with `LLAMA_ARG_LOG_VERBOSITY=4`.
- Solution: B4g re-run needs `-lv 4` (or `LLAMA_ARG_LOG_VERBOSITY=4`).
- Documentation: `/mnt/raid0/llm/tmp/ufh14-b4-20261005/B4g-1.md`.
- UFH14-B4g updated with recipe reference.

| File | Repo | Change |
|---|---|---|
| `handoffs/active/agentic-serving-harness-fixes.md` | root | UFH14-B4g-1 ✅ 2026-10-05; UFH14-B4g re-run recipe updated |
| `artifacts/operator/receipts/RATIFY-STACKCHG-8083BATCH-20261004.json` | root | Operator signature receipt copied |

## STACKCHG-8083BATCH-20261004: serving proof COMPLETE

**Deployment:** :8083 relaunched 08:02Z with `-b 512 -ub 512 --no-cache-idle-slots`.

**Proof (all §8.3 items PASS):**
- Attestation + promotion gate: OK
- Load VRAM: 48.54 GiB
- Turn-2 cache_n: 2407
- Decode-during-prefill: PASS (gap 0.265× fit; solo decode 28.5/28.2 tok/s)
- Coherence: PASS after review (20/24 byte-identical, 4 EQUIVALENT)
- q38_t7 dflash2: 35.74 vs nodraft 15.7 tok/s

**Evidence:** copied to `artifacts/stackchg-8083batch-20261004/` (bringup_summary.txt, bringup_triage.md, run78_summary.txt, coherence-bringup/REVIEW.md).

**Orchestrator:** fe07865f, plus derived regen (shared checkout 300cf581).

**Research:** 7c3ff2b4 and f1c6fef5.

**Lesson:** gpu_window restore must run AFTER releasing gpu-quiet exclusive (the executor refuses while the device is held); :8083 stayed parked ~15 min.

## UFH14-B4e & UFH14-B4h: deployed at API reload (08:02Z)

**Orch branch:** feat/ufh14-b4-cleanup-ec @ 621791f0 (merged as fe07865f).

**B4e:** `escalation_prewarmer` deleted; OAB-3 witness re-pointed to MemRL q-scoring site.

**B4h:** hot-prefix slot-save warming path deleted; `--slot-save-path` KEPT (KV migration and kv_compress use it); `canonicalize_prompt` KEPT (does not run with pinning off; KPF-23 owns it).

**Tests:** 757 combined pass (lint clean; targeted pytest rc 0). API reloaded at 08:02Z.

**Progress notes from HANDOFF_EDITS.md applied.**

## YaRN native-window finding: FAILS operator rule

**Canonical test:** :8070 recipe, Qwen3.6-35B-A3B CPU, 2026-10-05 12:10Z.

**Results:**
- YaRN ×2 static costs 1.3% at depth 0 and 7.6% at 34k decode
- MTP acceptance drops 53% → 48%
- Greedy outputs byte-identical on only 13/20
- **VERDICT: FAILS operator rule "YaRN must not regress inside the native window"**

**Acceptable approaches:** dynamic/per-request YaRN or DCA (active beyond native length only).

**Evidence:** copied to `artifacts/yarn-native-window-20261005/summary.md`.

**Handoff updates:** YaRN handoff depth check ticked; "make YaRN inert inside the native window" task filed.

**Belief-kernel wiring:** new task in `handoffs/active/vidya-belief-substrate-program.md` for q36 depth-recipe results adapter.

## FIFO region-lock review: APPROVED

**Orchestrator branch:** feat/region-lock-fifo-20261005 (d48b6b79, APPROVED).

**Deterministic FIFO-off control:** precondition for default-on.

**Evidence:** copied to `artifacts/fifo-region-lock-review-20261005/REVIEW.md`.
