# Inference backlog schedule — 2026-10-04 (shared: ak-ds41-main + workspace-ec)

Operator direction (05:45Z): park the AutoKernel lanes and drain the inference backlog together.
Each session edits ONLY its own rows (Owner column). Times are estimates; update the Status column as you go.

**Rules:**
- GPU benches and CPU *measurements* never overlap. On this host, sustained GPU host threads raise the CPU A/A floor about 9×.
- Builds and compiles overlap anything, under `region-lock run --cpu-list 0-95 --role build`.
- Every CPU job, builds included, takes the region lock.
- The GPU is never idle while a validated runner is waiting.

**AutoKernel lanes:**
- **Q38FN:** stopped 05:50Z (verified dead).
- **DS41:** stopping at its next planning step via `stop_at_planning_20261004.sh` (WATCHDOG3_HOLD set). Parked 06:03:08Z (TERM at planning step 05:52, KILL after 10 min ignore; tree verified dead).

| # | Device | Item | Owner | Est | Status |
|---|---|---|---|---|---|
| 0 | GPU | gpu-slot-ak: KVU-16b replay skip OFF/ON × -b 2048/512 (+P3 v2 remainder) | ak-ds41-main | done 06:20Z | DONE (4 replay arms; P3 v2 skipped for budget) — `gpu-slot-ak-20261004/results/20261004T050808Z` |
| 1 | CPU-meas | c1 EXL3 CPU microbench (~10 min) + c2 MXFP4 vs Q4_K DS41 expert shapes (C114, ~8 min) | ak-ds41-main | ~15 min | scripts ready (`/mnt/raid0/llm/tmp/cpu-backlog-20261004/c1,c2`), moved AFTER KVU-16h (GPU handed over 06:24Z; avoids idling the GPU) |
| 2 | GPU | KVU-16h VRAM attribution (+ forced arm B `-b 512 -ub 512`) | workspace-ec | ≤60 min | runner validated |
| 2a | GPU | ~~ALT: :8083 restore after KVU-16h~~ | workspace-ec | — | not chosen |
| 3 | CPU-meas | c3 IQ4_K/IQ4_KS on Q38FN via ik_llama instrument | ak-ds41-main | — | BLOCKED: ik_llama has no qwen4exp arch; no IQ4_K/KS Q38FN GGUF; no Q8_0/BF16 source on disk |
| 3b | CPU-meas | ~~YaRN CPU attention micro-bench here~~ MOVED to the step-6 CPU window (after c4), so the GPU block starts right after c1/c2: command `/workspace/repos/epyc-orchestrator/scripts/region-lock run --cpu-list 0-95 --role bench --tag yarn -- bash /mnt/raid0/llm/tmp/yarn-e1-20261004/cpu_leg/fa_depth.sh bench-locked` | workspace-ec | ~15-35 min | moved to step 6 |
| 4 | GPU | KVU-19 fold slot (19a + 19b commit 1), gpu_slot_fold.sh | workspace-ec | ≤20 min | candidate 1bceceb05 READY (G0 PASS, CPU harness 86+141 bit-identical, tbo CPU 5178/5178); gpu_slot_fold.sh ~19 min |
| 4a | GPU | champion-vs-production standing: operator 08:5xZ chose ONE paired v10-vs-champion run on the current :8083 DFlash2 protocol (ab_probe serving, >=14 launches each); future champions single-arm vs it. Needs workspace-89 writer protocol kind (serving probe) | workspace-ec | ~26-30 min | runner being built; after 4c |
| 4b | GPU | rocprof breakdown of a long-context concurrent decode step (4x80k decode, 1x80k, 4x4k control) on the fold-candidate image validated in row 4 (else c7f5ac9ad); `/mnt/raid0/llm/tmp/rocprof-longctx-20261004/` | ak-ds41-main | <=25 min | READY: `rocprof_longctx.py --execute` (dry-run 0 problems; build gpu-20261004-1bceceb05 = fold image; runs only after row 4 validates it) |
| 4c | GPU | KVU-16h follow-up with fix arm: A (prod v10, graphs on) -> C (private-arena fix gpu-20261004-656c9a66b) -> B (GGML_CUDA_DISABLE_GRAPHS=1), byte-faithful T7#1 phase-A n_max:0 replay. `gpu_slot_kvu16h_followup_c.sh --execute --arm-c-bin /mnt/raid0/llm/kernels/builds/gpu-20261004-656c9a66b/bin` | workspace-ec | ~32 min | READY |
| 5 | GPU | v11fa: ROCWMMA OFF/ON + cherry-pick arm + upstream-master arm; DF2-9 first on every arm | workspace-ec | ≤75 min | ran 11:37-11:48Z (opnan/det/perf/tbo-D); gaps rerun as 5h |
| 5a | GPU | 19b commit-2 rework v2, gpu_slot3.sh (`/mnt/raid0/llm/tmp/fa-maskskip-batched-20261004/`; store build gpu-20261004-54df2c030; exactness 8 arms, perf 4x80k rows 8/9, p3batch, tbo hint cases under region-lock) | workspace-ec | ~15-18 min | READY |
| 5c | GPU | KVU-16g prefill-budget A/B on fold-based build gpu-20261004-65d48a7a0: `ARMS="off pb512 b512 t1000" /mnt/raid0/llm/tmp/prefill-budget-20261004/gpu_slot.sh` (DEPTH=20000, NEIGHBOUR=80000, MAX_MIN=45; headline neighbour TTFT vs decode-under-prefill) | workspace-ec | <=45 min | READY |
| 5d | GPU | FA-INT64-OFFSET (#27090) GPU validation: `/mnt/raid0/llm/tmp/dca-yarn-kernel-20261004/fa-int64/gpu_slot_fa_int64.sh slot` | workspace-ec | ~15 min | READY (duration tbc) |
| 5e | GPU | DCA v1 GPU validation (tests on ROCm0 + 64K PPL vs CPU): `/mnt/raid0/llm/tmp/dca-yarn-kernel-20261004/gpu_slot_dca.sh slot` | workspace-ec | ~15 min | READY (duration tbc) |
| 5h | GPU | v11fa selective rerun: model-level DF2-9 (probe + server) + tbo on arms A/B/E(B+#27870 only)/C: `STEPS=... ARMS="A B E C" gpu_slot_v11fa.sh` | workspace-ec | ~25-30 min | E arm building |
| 5f | GPU | champion-allkeeps candidate X gates: 27B paired ab_probe receipt vs v10 (paired_receipt.sh pointed at X), GPU test-backend-ops, KVU-16b replay on X | workspace-ec + ak-ds41-main | 45-60 min | after X built + CPU-verified |
| 5g | CPU-meas | X CPU gates: DS41 serving gate (5 pairs) + Q38FN paired serving & output check (allowlist token-45 divergence 10-03); --gpu-quiet shared | ak-ds41-main | 60-75 min | after 5f |
| 6b | GPU | AutoKernel GPU lane, first job: multi-row dequant-GEMV for draft-verify (operator priority, ahead of long-context work). Interim terms: scheduled slot, mi210_0 device claim (+gpu-quiet exclusive once landed, NO region claims), 62 GiB in-run abort, AK never writes mi210.json, hard stop at slot end. Anchor: champion-allkeeps candidate if built, else 1bceceb05 | ak-ds41-main | 2-3 h | agreed 10:5xZ (G1 automation NACKed) |
| 5b | GPU | ~~:8083 restore after v11fa~~ | workspace-ec | — | superseded: operator 06:40Z "AFTER E1" |
| 6 | CPU-meas | c5 Q4_K expert regression confirm (~7 min) + bisect (~30-50 min, only if confirmed; incl. C112 proxy) -> then c4 only confirms c5 first-bad with llama-bench (else full c4) (receipt moved to row 4a: it is a GPU A/B) | ak-ds41-main / workspace-ec | ~50 min (worst 75) + receipt | c4 ready (`cpu-backlog-20261004/c4`); receipt after step 4 |
| 7 | GPU | YaRN E1 (stays in this parked block; or v11fa/rework in its place if the runner is not validated yet) | workspace-ec | ~3 h | runner in validation |
| 8 | GPU | **:8083 production restore + serving proof, AFTER E1** (operator, confirmed to workspace-ec) | workspace-ec | ~15 min | scheduled, end of block |
| 9 | CPU-meas | YaRN CPU leg: Qwen3.6-35B-A3B hybrid at native / YaRN x2 to 512k / x4 to ~1.03M, 8k-turn incremental build, decode-at-depth + needles + short-suite regression + 1 cold-prefill point (`/mnt/raid0/llm/tmp/yarn-e1-20261004/cpu_leg/`, RUNBOOK §9). Needs ONE dedicated ~6 h CPU block; does not fit AK windows (1.8-5.3 min). Proposed: after row 8, before the AK lanes relaunch, as part of draining the backlog. Inputs build + CPU attention micro-bench (~35 min) can go earlier in any CPU window. | workspace-ec | ~6 h | AGREED by ak-ds41-main 06:5xZ |

**Builds that overlap anything (under the build lock):** KPF-P1 (prefix fork), the V11-FA arms incl. upstream master, the fold store builds, the 19b rework, prefill-budget dev tests, EXL3-6 perf tuning.

**After the backlog:** relaunch DS41 (remove WATCHDOG3_HOLD, relaunch at a batch boundary on lane0 args) and the Q38FN lane (`/mnt/raid0/llm/tmp/q38fn-lane-run1-20261004/relaunch.sh`). At that restart, opt both into champion folding (lane-targets `champion` + `working_branch`, research ≥ be23ac25), pinned to the then-current champion tip including the KVU-19 fold.

## Re-ordered 12:00Z (workspace-ec): candidate X first
GPU/CPU order from ~12:05Z: slot3 (running) -> **5f** X gates (ec: paired receipt on X cf23279ae/10325 ~29 min + tbo FA ~8 min; then ak-ds41-main KVU-16b/P3 replay on X) -> **5g** ak-ds41-main CPU window ~2 h (a+b+c incl. Z bundle gate, one --gpu-quiet shared claim) -> 5c prefill budget -> 5d FA-INT64 -> 5e DCA -> 5h v11fa selective rerun (A B E C) -> 6b AK GEMV (anchor X if gated, else 1bceceb05) -> 7 YaRN E1 -> 8 :8083 restore (+ signed batch package, if signed).

---

## Completion state, ak-ds41-main rows (durable copy, 2026-10-04 ~21:20Z)

Copied from `/mnt/raid0/llm/tmp/backlog-schedule-20261004.md` (48 lines, verbatim above this rule). workspace-ec's
rows are not restated here; their status is in their own records.

| # | Item | State | Evidence |
|---|---|---|---|
| 0 | gpu-slot-ak KVU-16b replay | DONE 06:20Z | `artifacts/gpu-slot-ak-20261004/` |
| 1 | c1 EXL3 CPU microbench + c2 MXFP4 vs Q4_K | DONE 07:13–07:33Z | `/mnt/raid0/llm/tmp/cpu-backlog-20261004/c1,c2/runs/`; INF-80 EXL3-6c6, INF-77 DS41-C114a |
| 3 | c3 IQ4_K/KS on Q38FN | BLOCKED (unchanged) | INF-26 NEW-8 steps 0–1 |
| 4b | rocprof long-context concurrent decode | DONE 08:10–08:28Z | `/mnt/raid0/llm/tmp/rocprof-longctx-20261004/results/20261004T081019Z/report.md` |
| 5f | X GPU gates (with workspace-ec) | DONE | ledger `handoffs/active/autokernel-champion-aggregate.md` → *all-keeps fold* |
| 5g | X/Y/Z CPU gates (a+b+c incl. Z bundle gate) | DONE 12:56Z | `/mnt/raid0/llm/tmp/fold-allkeeps-20261004/runs/20261004T125648Z/` |
| 6 | c5 confirm (+ c4 bisect) | DONE 10:34–11:15Z | c5 NOT REAL (DS41-C124); c4 first bad `9b148baab` (DS41-C112) |
| 6b | AK GPU lane, first job (multi-row GEMV) | RUN 1 DONE, 0 measured | INF-81 AKX-ALL-15c-1; fixes pending review (AKX-ALL-15c-2) |

Folds that came out of the block (all ledgered in `autokernel-champion-aggregate.md`): KVU-19 `90c12df42` →
`1bceceb05`; all-keeps `1bceceb05` → `61bdb185c`; CPU FA overflow `61bdb185c` → `9a3f1392a`; W `9a3f1392a` →
`b0ba1d427`.

**Remaining before "after the backlog":** row 9 (workspace-ec's ~6 h YaRN CPU leg). The DS41 relaunch on
`b0ba1d427` with folding enabled follows it (~03:00Z 2026-10-05; INF-77 DS41-C121). :8083 package
RATIFY-STACKCHG-8083BATCH-20261004 is still unsigned (OP-76).
