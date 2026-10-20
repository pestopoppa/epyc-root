# AutoKernel on every device and every dimension: long-context surfaces, attention routes, GPU serving, profilers as planner inputs

**Status**: ACTIVE. Operator-ruled requirement (2026-10-04), not a decision package. Three implementation subagents
started at filing on research branches: `feat/ak-longctx-surface` (C1 + C4), `feat/ak-cpu-fa-route`
(C2 `cpu_fa_schedule` + C3) and `feat/ak-gpu-surface` (G2 + G5 + G6 + the quiet-window default). G1 needs
workspace-ec (the stack owner). G3, `cpu_fa_numerics` and the DS41 attention-graph route follow those.
**Created**: 2026-10-04 (drafted for ak-ds41-main from the long-context audit)
**Priority**: HIGH. AutoKernel measures every target at a KV depth of about 300 tokens, while production decode runs
at long context: on `:8074` (Q38FN, CPU) 67% of decode wall is above 32k tokens and the rate falls from 41 tok/s
under 8k to 13–18 tok/s; on `:8083` (27B, MI210) 88% of decode wall is above 32k. AutoKernel cannot see that regime,
and no route lets it act on attention at any depth.
**Categories**: autonomous_research, hardware_optimization, kernel_development, benchmark_methodology
**Parent index**: [inference-research-index.md](inference-research-index.md) (row INF-81, applied by the owning
session)
**Scratch**: `/mnt/raid0/llm/tmp/ak-alldims-handoff-20261004/` (this draft and its prepared rows) ·
audit `/mnt/raid0/llm/tmp/ak-longctx-audit-20261004/` · research worktrees
`/mnt/raid0/llm/worktrees/research-ak-{longctx-surface,cpu-fa-route,gpu-surface}` · GPU trace prototype
`/mnt/raid0/llm/tmp/rocprof-longctx-20261004/` · lb1 roofline `/mnt/raid0/llm/tmp/lb1-profile-20261003/`
**Owners**: **ak-ds41-main** keeps this handoff and its index row, and runs the CPU and GPU subagents.
**workspace-ec** owns `:8083` and executes its side of G1 (drain, unload, reload). The INF-73 loop owner reviews
every merge into research main.
**Depends on**: INF-73 [`autokernel-unified-surface-program.md`](autokernel-unified-surface-program.md) (the
loop, serial router and target model), INF-75 [`autokernel-cross-workload-keep-gate.md`](autokernel-cross-workload-keep-gate.md)
(the keep gate G5 extends), RTG-57 [`kv-unified-stack-rollout.md`](kv-unified-stack-rollout.md) (`:8083` argv and
its windows), INF-62 [`dflash2-block-drafter-experimental-build.md`](dflash2-block-drafter-experimental-build.md)
(DF2-9, the rocWMMA FA pin and its NaN reproducer)
**Related**: INF-77 [`deepseek-v41-flash-evaluation.md`](deepseek-v41-flash-evaluation.md) (DS41 lane; finding 1,
DS41-C9, DS41-T2, DS41-B14), RTG-58 [`kv-prefix-fork-and-paged-attention.md`](kv-prefix-fork-and-paged-attention.md)
(np=4 × ~80k is its regime too; KPF gates share G4's slot restore), INF-74
[`autokernel-concurrent-target-coordination.md`](autokernel-concurrent-target-coordination.md) (stage claims),
INF-31 [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md) (dense-mask vs sparse gather), INF-70
[`cpu-decode-roofline-program.md`](cpu-decode-roofline-program.md) (the 0.80% → 7.22% GPU-overlap floor and
be2-fa row-exactness), [`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md) (VB-AK-LONGCTX)

## Why this exists

**Operator ruling, 2026-10-04 (verbatim):** "autokernel needs to be able to work on whatever kernel we launch it on,
whether CPU or gpu! It needs to be able to perform optimizations across the board to maximize performance across all
the dimensions we track". Profilers "should be available to the autokernel planner also". The long-context gap
"needs fixing".

The audit [`/mnt/raid0/llm/tmp/ak-longctx-audit-20261004/REPORT.md`](/mnt/raid0/llm/tmp/ak-longctx-audit-20261004/REPORT.md)
(read-only, loop code at research `origin/main` `be23ac25f`) found:

| Gap | Where (audit §) | Fixed by |
|---|---|---|
| Every instrument runs at KV depth ≤ ~360 tokens; `bench.py` has no `-d`; held-out prompts must keep the same token count | §0.1, §1 | AKX-ALL-4..7 (C1, C4) |
| No CPU route admits `flash_attn_ext*`, `llama-kv-cache*`, `llama-graph.cpp` or `deepseek41.cpp` (refusal `gates.py:1494`) | §0.2, §2 | AKX-ALL-9, -11, -12 (C2, DS41) |
| `flash-attention` is 1–5% at ~300 tokens, so the "highest share first" planner never picks it | §2 | AKX-ALL-7 (C4), AKX-ALL-16 (G2) |
| Runtime arms cover threads/cpu_list/numa/load_threads/env only; `-ub`, `-ctk/-ctv`, FA knobs are not dimensions | §2 | AKX-ALL-13 |
| The AK Q38FN recipe pins `GGML_FA_SPLIT_KV=0`, `GGML_FUSED_DECODE_OFF=1`, 48 threads, `-ub 512`; production `:8074` runs 96 threads, `-ub 8192`, neither env | §2 | AKX-ALL-8 |
| GPU serving targets print "selected GPU serving profile unavailable" (`run.py:3706`); rocprofv3 runs on `llama-bench` only | §1, §4.1 | AKX-ALL-16 (G2) |
| No GPU FA or `convert.cu` route; `test-backend-ops` passed on the DF2-9-broken binary | §4.1, §4.2 | AKX-ALL-19 (G3) |
| No exclusive MI210 window: `:8083` holds 51–59 GiB of 64 | §4.2 | AKX-ALL-15 (G1) |
| The keep gate does not cover long decode, prefill at depth, concurrency or capacity | §4.2 | AKX-ALL-17 (G5) |
| `--cpu-measurement-gpu-quiet` defaults to `off`, contradicting "GPU and CPU measurements never overlap" | §4.3 | AKX-ALL-2, -3 |
| DS41 final attention is a dense −inf mask plus a full `ggml_concat` of the compressed plane every layer, every step | §5 | AKX-ALL-12, AKX-ALL-20 |

**The tracked dimensions** (what "across all dimensions" means here, and what G5 gates): short decode, long decode
(decode at depth), prefill at depth, concurrent aggregate (np>1), capacity (peak VRAM on GPU, RSS on CPU, at the
recipe's context and slot count), and correctness (bit-identity or tolerance gate per route, greedy identity at
depth). Every surface below records all of them it can reach; no keep may regress one it does not measure without
saying so.

## Start here

**2026-10-04 ~21:20Z state (ak-ds41-main wrap-up 4).** The first wave is on research main: integration merge
`4e2471bd` (`eff6c41f` integrates `dc1828a0` long-context surface + `91a09158` `cpu_fa_schedule` + `9313ad32` GPU surface:
G2 profile, G5 `keep_dimensions`, G6 recipe, GPU-POOL-1 static rule, per-launch HIP proof), then gpu-quiet `f1d1d9eb`
(on orchestrator `c5dc4ae5`), production `serving_probe` `46256fa3`, unpaired-verdict gate `9b57f555`, KeyError fix
`1b307ddf`. First AK GPU run done (AKX-ALL-15c-1: 0 measured); its two fixes wait for review (AKX-ALL-15c-2). Code
landing alone closes no box below whose done-test needs a live run; those carry a note instead.

1. **The three in-flight branches** (subagents started at filing, all forked from research `be23ac25`):
   - `feat/ak-longctx-surface` → AKX-ALL-4 (C1) and AKX-ALL-7 (C4).
   - `feat/ak-cpu-fa-route` → AKX-ALL-9 (`cpu_fa_schedule`) and AKX-ALL-10 (C3).
   - `feat/ak-gpu-surface` → AKX-ALL-2 (quiet default), AKX-ALL-14 (G6), AKX-ALL-16 (G2), AKX-ALL-17 (G5).
   Each lands on research main through the INF-73 loop owner's review, not by direct push from the subagent.
2. **AKX-ALL-1**: the belief-kernel wiring (VB-AK-LONGCTX) is prepared at filing; the owning session applies it
   before the first long-surface record exists.
3. **AKX-ALL-15 (G1)**: open the MI210 window protocol with workspace-ec on the bus. Every GPU measurement task
   (G3, G4, the GPU half of G5) waits on it.
4. **After the first wave merges**: AKX-ALL-11 (`cpu_fa_numerics`), AKX-ALL-12 (DS41 attention-graph route),
   AKX-ALL-19 (G3), then the end-to-end proofs AKX-ALL-21/22.

## Standing rules for every task

- **Kernel workflow** (CLAUDE.md *Experimental Kernel Workflow*): `/mnt/raid0/llm/llama.cpp` @ `ffc1bac82`
  (production-consolidated-v10) is READ-ONLY reference. AutoKernel builds only from the current champion tip,
  resolved live, in its own worktrees. Production arrives only via the kernel-promotion skill.
- **ONE champion, one binary.** A route's candidate dispatches inside the one champion binary; the A/B control is
  argv or batch shape, never an env-only gate (env vars are diagnostic kill switches only).
- **Loop code** lives in epyc-inference-research `scripts/kernel_rnd/autokernel/`. Subagents work only in their
  own `research-ak-*` worktree and never switch the shared clone's branch.
- **Measurement** (MEASUREMENT.md, `agents/shared/MEASUREMENT_POLICY.md`): pair every speed number with a
  correctness check at the production prompt length; matched instrument; alternating ABA; noise floors carry their
  unit (process); two-sample persistence before acting on a delta. **A measurement at ~300 tokens is not evidence
  about attention at 64k.**
- **CPU/GPU never overlap** (audit §4.3; INF-70 measured 0.80% → 7.22% CPU A/A floor under a pinned GPU bench):
  CPU measurements hold the q3 quiet window, GPU measurements hold the q3 CPU-region claim plus `mi210_0`
  (AKX-ALL-2/3). Never run during another session's GPU window (INC-20261003-subagent-gpu-tests-in-peer-window).
- **HIP residency is proven, not asserted**: `verify_ggml_linkage.sh`, KFD process count, VRAM sampled DURING the
  run. `ldd` proves nothing (llama.cpp dlopens `libggml-hip.so`).
- **Process discipline**: signal only PIDs the loop started; a profiled server gets SIGTERM with a long grace so its
  trace flushes; no `pkill`/`pgrep` patterns.
- **Reload ownership**: `:8083` is drained, unloaded and reloaded by workspace-ec, never by AutoKernel (AKX-ALL-15).
- **Belief kernel**: every surface below writes its native record under VB-AK-LONGCTX (AKX-ALL-1) from its first run.
- **GitNexus before editing** loop symbols (`gitnexus impact <sym> --direction upstream`); stop and warn on HIGH or
  CRITICAL. Re-index only via `scripts/gitnexus-analyze.sh`.

## AK harness autonomy hardening (operator, 2026-10-06: the loop must run autonomously without hand-holding)

**Scope note:** these are harness/loop-infrastructure changes made by us; AutoKernel itself only edits kernels for performance and never changes its own loop, routes or gates.

**Rationale:** every 2026-10-05/06 failure was found by a human or audit, not by the loop.

- [x] AKX-AUTO-1 Roofline-gap route coverage: per-node roofline in the planner context; startup/stagnation check flags gap share in nodes with no admitted route (uncovered_gap, scope_gap.json). Detect only, never auto-widen. (research 0e9e0b4a)
- [x] AKX-AUTO-2 Planner sees its own history: structured abstentions, abstentions trip the diminishing-returns escape, always-shown epoch keeps/families, generated ALREADY-IMPLEMENTED block (research ecdded0d)
- [x] AKX-AUTO-3 Campaign-level numerics contract (operator: wikitext2 |Δppl| ≤ 0.5% + NMSE + coherence) instead of per-route constants (research f17bb5a3). ppl_contract acceptance is layered (NMSE on served shapes + Δppl ≤ 0.5% + coherence/token agreement on production-length prompts + a ≥1k-token canary), fails closed, and never folds on bench evidence alone (operator: 'utmost care to not introduce garbage').
  - [ ] cross-lane quality gate so low-bit (ppl_contract) keeps can reach the global champion
- [ ] AKX-AUTO-4 Calibration self-check: reject a contiguous degraded block, or auto-recalibrate when spread is anomalous vs the prior floor (2026-10-05 Q38FN floor 6.528% from a 5.5-min degraded block)
  - 2026-10-07: the generic matched-floor outlier guard landed (Astra R21-R24, research `e3bcf010`): a suspect
    floor never carries forward, an unguarded floor >3x the previous floor is refused, atomic
    `REMEASURE_REQUEST.json` written under `<store>/runtime-source-floors/<recipe_hash>/`. This is evidence-based
    refusal of a *future* bad floor, not a fix to the Q38FN 6.528% floor itself — a `REMEASURE_REQUEST` was filed
    for recipe `cff9ad900700…` and is still open. Leave this box open until that remeasure lands.
- [ ] AKX-AUTO-5 Launch preflight cross-checks lane binding ↔ inputs ↔ anchor ↔ store (2026-10-06: lane1 bound to inputs-b0ba1d427 while running inputs-802bf9ac6)
- [ ] AKX-AUTO-6 Auto re-anchor/relaunch on champion advance (uses the --new-anchor-epoch path, research 5da038ad)
- [ ] AKX-AUTO-7 Supported resume of a drained lane, or make drain impossible to issue by mistake (DS41-C126(e))
- [ ] AKX-AUTO-8 Every lane has a watchdog by construction (Q38FN had none until 2026-10-05 23:03Z)
- [ ] AKX-AUTO-9 Routes generated by default: every compiled CPU kernel file gets a route automatically, with an oracle class by file family (quant GEMM/dequant → scalar reference + NMSE; graph/scheduling → model identity). Refuse only files with no possible oracle (CMakeLists.txt, code shared by both arms). Replaces hand-listed per-function routes, so a new hot file is in scope without a human (2026-10-06: Q38FN's IQ3_S/IQ4_NL kernels had no route).
- [ ] AKX-AUTO-10 Profiler refinement: separate prefill and decode phases; per-node bytes accounting; MMID overlap bracketing; per-verify-width breakdown; an isolated op microbench to pin ambiguous rooflines (DS41 Q4_K MMID gate estimate 206–411 GB/s vs a ~394–470 ceiling is unresolved).

## Tasks

### P0: setup and coordination

- [ ] **AKX-ALL-1: belief-kernel wiring, VB-AK-LONGCTX.** Prepared at filing in
  `/mnt/raid0/llm/tmp/ak-alldims-handoff-20261004/PREPARED_ROWS.md`: (a) a source row for
  `scripts/vidya/adapters/README.md` covering the production context-bucket analysis and the C1/G4 long-context
  surfaces; (b) the task section VB-AK-LONGCTX for `vidya-belief-substrate-program.md`. The owning session applies
  both. Done when both are on main and AKX-ALL-4's runner writes `belief_measurements.jsonl` rows.
- [x] **AKX-ALL-2: flip the CPU/GPU quiet-window default to on (`--cpu-measurement-gpu-quiet q3`).** ✅ 2026-10-04 Branch
  `feat/ak-gpu-surface`. Change the CLI default in `loop/run.py` (`_q3_cpu_gpu_quiet_window`), invert
  `loop/test_q3_measurement_window.py::test_cli_declares_gpu_quiet_policy_default_off` to assert `(default: q3)`,
  keep `off` as an explicit, logged opt-out. Find where the 2026-09-25 "run GPU work concurrently" policy is written
  (the code comment and any doc it cites) and supersede it there, citing the 2026-10-04 ruling. Done when the merged
  loop's `--help` shows `default: q3` and a CPU measurement under a held GPU claim waits instead of measuring.
  ✅ Done in a different shape: `9313ad32` flipped the default to q3, then research `f1d1d9eb` (design agreed with
  workspace-ec) moved both sides onto the orchestrator's host-wide gpu-quiet flock (`c5dc4ae5`,
  `src/runtime/gpu_quiet_lock.py`). `--cpu-measurement-gpu-quiet {off,lock}` defaults to `lock` (`q3` is a
  deprecated spelling of it); CPU measurements hold it SHARED, GPU measurements EXCLUSIVE, so a CPU measurement waits
  behind a GPU bench. Proven by `loop/test_gpu_quiet_measurement_window.py`; not yet observed live.
- [ ] **AKX-ALL-3: GPU measurements take the q3 CPU-region claim.** The GPU host threads 184-191 are the SMT
  siblings of q3 (cores 88-95). Every GPU measurement (serving A/B, profile, microbench) acquires the q3 region claim
  in addition to `mi210_0`, through the existing claim API, and releases both in a `finally`. Done when a GPU batch's
  resource receipt lists both claims and a concurrent CPU measurement in another loop is shown waiting on it.
  - 2026-10-04: **mechanism superseded** by `f1d1d9eb`: a GPU measurement takes gpu-quiet EXCLUSIVE and NO q3 region
    claim (the region claim 503'd every serving role placed on q3). Read "both claims" as `mi210_0` + gpu-quiet.
    Run 1 of `ak-27b-gpu-verify-20261004` refused at batch 1 because a GPU-only bundle had no CPU component; fix
    `4375b5aa` (research `ak/gpu-run1-20261004`, unpushed, pending review) makes the receipt carry the device flock
    plus the observed gpu-quiet EXCLUSIVE hold. Still open: that fix merged and a live receipt listing both.

### P1: CPU — long context and attention

- [ ] **AKX-ALL-4 (C1): long-context surface with prefill-once.** Branch `feat/ak-longctx-surface`.
  - One frozen long prompt per target, ~64k tokens of real text (a 128k manifest later); `cache_prompt true`, same
    greedy controls. Recipe `-c` ≥ depth + 4k + 256, plus `--slot-save-path` (already admitted,
    `resolved_recipe.py:513`).
  - The anchor prefills once and saves the slot; the slot file is keyed by model, recipe execution digest and prompt
    digest, and regenerated on every anchor change.
  - Per launch: restore the slot; request A = prefix + fixed 4k tail → `prompt_per_second` (prefill at depth);
    request B = prefix again + 256 decode → `predicted_per_second` (decode at depth).
  - Refuse the run if request B's `prompt_n` exceeds a small bound (Q38FN's hybrid layers need a recurrent
    checkpoint near the prompt end) or if the restore fails. Refusals are typed records, never silent passes.
  - Runs as the primary metric for attention candidates and as a no-regression gate on every keep (like the peer
    floor). Write the VB-AK-LONGCTX record from the first run.
  - Done when the surface runs end to end on Q38FN against the current anchor, both metrics recorded, refusals
    tested.
  - 2026-10-04: code on research main (`dc1828a0`, integrated in `eff6c41f`; opt-in `--longctx-surface <spec>`),
    refusals unit-tested. Not yet run end to end on Q38FN, so open.
  - 2026-10-20: the 10-08 Q38FN r10 attention candidates refused `oracle_unavailable` / `process_environ_witness_missing`. Cause: `_oracle_arm` (32a72fefc) rebuilt the oracle template without environment variables, so all 8 recipe keys checked at `/proc/<pid>/environ` went `unknown`. Fixed on research main (1aa0b0441 + b27636385; the latter fixes the same env-less template in `production_enrollment.resolve_exported_recipes`, the runtime-anchor path) with regression tests (92 pass). The refusal happened before serving, so no stale `identity-*.json` receipts. Also 2026-10-20: a manual served sweep measured Q38FN at depth 512-128k (research `data/q38fn-threads-depth-20261020/`, commit 23119ea4e): decode 33-37 -> 16-17 t/s and 4k-tail prefill 160-210 -> 72 t/s at 128k, insensitive to 48 vs 96 threads - use it as the pre-AK baseline for the long-context surface; `-t 48 -tb 96` is the runtime-arm candidate.
- [ ] **AKX-ALL-5 (C1): DS41 restore-identity gate.** `state_write/read` exist for the dsv4 caches and engram, but
  DS41-B14 warns those caches mutate destructively. One-time gate: a restored slot and a fresh prefill give
  identical greedy continuations at depth. If it fails, DS41's long surface falls back to fresh prefill (~27 min) and
  the defect is filed under INF-77. Done when the gate verdict is recorded for the current DS41 anchor.
- [ ] **AKX-ALL-6 (C1): noise floor at depth, per target.** 24 process-unit pairs per target (~2 h machine time for
  Q38FN), unit = process, p95, the same procedure as the DS41 3.469% floor. Nothing is calibrated at depth today.
  Done when each long-surface target carries a floor with its unit, n and interval.
- [ ] **AKX-ALL-7 (C4): planner inputs at depth.** Branch `feat/ak-longctx-surface`. Repeat the node profile and
  the CPU perf capture on the long manifest with the slot restored; put the target depth on the target card; feed
  the production context histogram (regenerated from `llama-server-*.log`, by context bucket, decode wall share and
  rate) to the planner as the workload weighting. Done when the planner prompt for a Q38FN round shows the at-depth
  family table and the histogram, and `FLASH_ATTN_EXT`'s at-depth share is visible.
  - 2026-10-04: code on research main (`dc1828a0`); no Q38FN round has run with it yet.
- [ ] **AKX-ALL-8: a production-shaped attention recipe for the Q38FN target.** The AK target pins
  `GGML_FA_SPLIT_KV=0`, `GGML_FUSED_DECODE_OFF=1`, 48 threads, `-ub 512`; production `:8074` runs 96 threads,
  `-ub 8192` and neither env. The long surface runs at the production shape, or the target card states which pin is
  kept and why (`GGML_FA_SPLIT_KV=0` exists for spec-decode row-exactness, INF-70 be2-fa). Done when the long
  surface's recipe digest matches the `:8074` argv apart from documented, justified deltas.
- [ ] **AKX-ALL-9 (C2): `cpu_fa_schedule` route (bit-exact).** Branch `feat/ak-cpu-fa-route`.
  - Scope: the FA dispatch body, `ggml_compute_forward_flash_attn_ext_f16_one_chunk`, `reduce_partials`, new static
    helpers (`ops.cpp:9241-9982` at `dd6c9cdbd`).
  - Allowed: work split and traversal only, each output row's reduction order unchanged — e.g. process the GQA query
    heads of one KV head in a single KV pass (Q38FN: 12 query heads per KV head re-read it separately today); split
    KV across threads with a fixed-order merge.
  - Gate: bit-identity with the anchor via `test-backend-ops` on the AKX-ALL-10 case set, repeated to catch races,
    plus model identity on the short and long manifests.
  - Done when the route is admitted (no fallback refusal at `gates.py:1494`) and one planner-authored candidate
    passes or fails it with a typed verdict.
  - 2026-10-04: route admitted on research main (`91a09158`, hardened in `eff6c41f`: no added `_Pragma`/omp/macro
    lines, const-only file-scope helpers). No planner-authored candidate yet.
- [ ] **AKX-ALL-10 (C3): flash-attention microbench case set.** Branch `feat/ak-cpu-fa-route`. A
  `test-backend-ops` case set behind the existing selector (precedent
  `AUTOKERNEL_CORRECTNESS_CASE_SET=odd_gqa7_d64_q1_v1`). Q38FN: head dim 256, 2 KV heads, 12 query heads per KV head,
  kv 8k/64k/128k, nb 1 and 5, f16. DS41: head dim 512, 1 KV head, 64 query heads, attention sinks, kv ~n/2..n, nb 1
  and 3. Perf mode on the CPU backend, anchor and candidate paired, as the screen before serving A/B; the same cases
  are the correctness corpus. The stock mask does not model DS41's top-k mask, so DS41 relies on C1. Done when the
  set runs in both modes from the loop and its timings land in the candidate record.
  - 2026-10-04: `cpu_fa_longctx_v1` is defined (`91a09158`), but the case set and perf screen record SKIP until the
    llama tree carries `tmp/ak-cpu-fa-route-20261004/test-backend-ops-cpu-fa-longctx-v1.patch` (a champion fold).
- [ ] **AKX-ALL-11 (C2): `cpu_fa_numerics` route (tolerance).** After AKX-ALL-9/10 merge. Scope: the same bodies plus
  `_tiled`; arithmetic may change. Gate: a new float64 FA reference probe (pattern of `cpu_norm_reference`), 2^-10
  relative; repetitions bit-identical; row-exactness across N (row i at N=k equals the same row at N=1, which
  speculative decoding needs); a coherence smoke at depth (`coherence_gate`). Done when the route is admitted and its
  reference probe is in the correctness corpus.
  - 2026-10-07: **pending, not landed** — branch `fix/ak-longctx-identity-oracle-20261007` @ `6f116e55`
    (research, Codex Astra round 1, "full-observation divergence receipts + DS41 real-mask N>1
    coverage"), worktree `/mnt/raid0/llm/worktrees/research-ak-longctx-oracle-20261007` (**KEEP**).
    The long-context identity oracle now strips MTP (the anchor's own repeats differed
    under speculative decoding), plus full divergence receipts, the FA case set widened to N=1..5,
    and a fail-closed DS41 real-mask probe. Astra R22 change requests are addressed in the branch
    but it had not yet been re-reviewed at the first checkpoint. Follow-up: Astra's original review
    returned FAIL; corrected Python commit `5da222c4` received static PASS, then Astra's C++ review
    passed for research commit `f6b24d54` and kernel patch commit `8393305bc`. Bounded tests/build remain
    pending; the branch is not landed, and no live real-mask capture exists.
    - [ ] C++ follow-up: a probe `--mask-file` mode.
    - [ ] C++ follow-up: a llama.cpp DS41 top-k mask dump hook.
    - [ ] C++ follow-up: regenerate `test-backend-ops-cpu-fa-longctx-v1.patch`.
    - [ ] Complete bounded test validation and land after the corrected review; do so before the
      AKX-ALL-21 round, not alongside it.
    - OP80 settled 2026-10-07: wire `check_cpu_fa_real_mask_identity` into `run.py`; fail-closed
      `oracle_unavailable` blocking until the C++ producer lands is accepted. Producer capture and
      reader wiring are prepared under VB-AK-REALMASK; no real-mask capture exists yet.
    - 2026-10-07 build boundary: ROOT accepted `OP80_CPU_BUILD_ACCEPTED.json` (SHA-256
      `08304fcd564d4316ba3f733c928f242b3571d6cba60c898c6789bf43793aa2dd`) for canonical CPU source
      `8393305bcc68395ee531bd19ad911b980298efc9`, tracked-clean, with the original native build RC 0.
      The accepted binaries match their proof hashes and report version `10345 (8393305bc)`; this
      establishes CPU build/capture-knob/own-tree-linkage only. No HIP residency, model validation,
      real-mask capture or promotion is established. Python OP80 candidate `896…` still has no
      accepted runtime result.
- [ ] **AKX-ALL-12: DS41 attention-graph route.** After AKX-ALL-4/5. A multi-file route with
  `identity_arch=deepseek41` admitting `src/models/deepseek41.cpp` `build_attention_v41` and the mask helpers
  (`build_top_k_mask`), and the host-side mask/plan rebuild (DS41-C9). The lever is the graph/mask/host path, not the
  FA kernel (AKX-ALL-20). Lane 0 already owns the file in `exclusive_paths`; this makes it authorable. Gate: greedy
  identity on short and long manifests plus AKX-ALL-5's restore identity. Done when the route is admitted and the C1
  surface measures a candidate on it.
- [ ] **AKX-ALL-13: runtime arms at depth.** Admit `-ub`, `-ctk/-ctv` and the FA knobs as runtime-arm dimensions
  measured on the long surface (today only threads, cpu_list, numa_policy, load_threads and env are). `-ctk/-ctv` change
  numerics: they carry the coherence gate at depth and the KV-quant evidence from VB-KVQ-V10, never a speed-only keep.
  Done when the runtime-arm schema accepts the three and one arm runs through the keep-grade A/B on the long surface.

### P2: GPU — window, profile, routes, surfaces, gate

- [ ] **AKX-ALL-14 (G6): HIP build recipe.** Branch `feat/ak-gpu-surface`. HIP gfx90a, ROCm 6.2, rocWMMA FA on as in
  v10 (DF2-9 pin `GGML_HIP_ROCWMMA_FATTN=ON`); carry rocWMMA as an in-binary arm per the v11 FA audit
  (`artifacts/v11-fa-path-audit-20261004/`). Every GPU launch proves residency: `verify_ggml_linkage.sh`, KFD process
  count, non-zero VRAM during the run. Done when a loop-built GPU candidate carries the build recipe digest and a
  residency proof in its receipt.
  - 2026-10-04: recipe `GFX90A_ROCM62_V10_RECIPE` and `hip_launch_proof.py` on research main (`9313ad32`). Run 1
    built candidates, but none reached a measured launch (AKX-ALL-15c-1), so no receipt carries a residency proof yet.
- [ ] **AKX-ALL-15 (G1): MI210 window and handover with the stack owner.** Needs workspace-ec. `:8083` holds
  51–59 GiB of 64, so AutoKernel needs an exclusive window:
  1. AutoKernel sends a bus window request to workspace-ec (duration, batches, reason).
  2. workspace-ec drains and unloads `:8083` itself (reload ownership).
  3. AutoKernel takes `mi210_0` (+ q3, AKX-ALL-3), runs its GPU batches, releases the claims.
  4. workspace-ec reloads `:8083` and confirms serving.
  The router schedules GPU batches only inside a granted window and runs CPU batches otherwise. Done when the bus
  message schema is agreed with workspace-ec, the router honours it, and one real window completes the full cycle
  with receipts.
  - *(2026-10-04, workspace-ec.)* **G1 round-2 review** (Fable, `/mnt/raid0/llm/tmp/g1-review-20261004/REVIEW-ROUND2.md`):
    - (a) Windows the stack owner invokes manually: **ACK-with-fixes**.
    - (b) AK-requested windows: **NACK**. F4: the AK flock is per `run.py` child, so it drops between serial batches,
      and there is a TOCTOU. F5: the handshake is still a refusing stub, with no compute-request sender and
      `--gpu-window` defaulting off. F6: expiry cannot be enforced against a live holder.
    - Manual-window fixes landed: orch `4b871cc5` is in the shared checkout (operator-approved). Device-busy
      `6ce26fc9` is not; updating the checkout needs operator approval.
    - The gpu-quiet lock is live (orch `c5dc4ae5`).
    - Operator, 2026-10-04: the AK GPU lane's first job is multi-row dequant-GEMV (AKX-ALL-15c).
  - *(2026-10-04 ~21:20Z, ak-ds41-main.)* G1 executor state: orchestrator `4b871cc5` (F1/F3) and `6ce26fc9`
    (device-busy refusal: KFD processes, gpu-quiet EXCLUSIVE, AK flock) are both on orchestrator origin/main; the
    shared checkout moves to `6ce26fc9` only on OP-78. The host cron (AKX-ALL-15a) waits on OP-78's fast-forward and
    the host install (OP-79). AK-requested windows are still **NACK**: the AK half of round 2 (F4/F5/F6) is research
    `d6b1a5ac` (not on research main), pending re-review (AKX-ALL-15b).
  - [ ] **AKX-ALL-15a — arm the GPU-window watchdog (review F2) after today's :8083 restore.** (filed 2026-10-04,
    workspace-ec) Install `scripts/server/gpu_window_watchdog.cron` in the host crontab (`* * * * *` +
    `@reboot sleep 90`). Done when a tick is seen writing `mi210.json.executor-status.json` after the restore and
    the hub probe is green.
  - [ ] **AKX-ALL-15b — close review F3/F4/F5/F6 so that AK-requested windows can be ACKed.** (filed 2026-10-04,
    workspace-ec; needs a coordinator grant path)
    - F4: a window-scoped flock held in `serial_run`'s parent across batches.
    - F5: a real compute-request sender and handshake.
    - F6: the AK honours `expected_end` mid-measurement.
    - F3: `--compute-grant` verified against the coordinator-daemon grant file.
    - Done when a third review ACKs (b).
  - [ ] **AKX-ALL-15c — the first AK GPU-lane job is multi-row dequant-GEMV.** (filed 2026-10-04, operator decision)
    It runs in the first window granted after AKX-ALL-15's manual cycle completes. Done when its batch receipts are
    recorded here.
    - [x] **AKX-ALL-15c-1 — run 1, campaign `ak-27b-gpu-verify-20261004`.** ✅ 2026-10-04 (17:46–18:21Z; backlog row
      6b interim terms: scheduled slot, `mi210_0` + gpu-quiet EXCLUSIVE, no region claims, 62 GiB abort). Anchor
      `9a3f1392a`; GPU serving floor calibrated **0.807%** (verified, unit process). 6 iterations, **0 measured**: the
      two stream-k Q8_0 MMQ hypotheses (`akm-gfx90a-q8-tiny-streamk-cap`, `akm-q8-j16-single-tile-streamk-five-cta`)
      were refused 5× with "MUL_MAT failed on ROCm0" on q4_K cases their Q8_0-guarded patches cannot reach, then
      retired at 3/3 attempts. Likely cause: the anchor itself fails the SEEDED gate (`--suite-seed 71
      --autokernel-properties`, fp64-ratio property); the earlier 1139/1139 pass was the plain invocation. The run
      then stopped on `SerialSchedulingRefused: held intervals lack one original CPU context` (GPU-only bundle).
      Store: `/mnt/raid0/llm/autokernel/campaigns/ak-27b-gpu-verify-20261004/store/experiments.md`.
    - [ ] **AKX-ALL-15c-2 — review and merge the run-1 fixes, then resume.** Research branch `ak/gpu-run1-20261004`
      (unpushed): `4375b5aa` (GPU-only held intervals settle on the device claim + observed gpu-quiet EXCLUSIVE) and
      `e747d45e` (anchor-relative GPU correctness: a seeded-gate refusal counts against a patch only if the anchor
      passes, else `oracle_unavailable`; the detail keeps the stderr FAIL lines). Both change
      `gate_rules_fingerprint`, so run 1's `gate_refused` candidates resume and re-gate. The campaign brief now makes
      H1 (`akg-ri-multirow-q8-gemv`, row-invariant multi-row Q8_0 GEMV) mandatory, drops H11, and sets planner effort
      high. Fable seeds: `/mnt/raid0/llm/tmp/ak-gpu-seeds-20261004/inbox-gpu-multirow-gemv.md` (in the store inbox as
      `10-fable-gpu-multirow-gemv-20261004.md`). Done when both fixes are on research main and run 2 records at least
      one measured candidate, or a typed refusal that is not an anchor-gate failure.
- [ ] **AKX-ALL-16 (G2): GPU serving profile as a planner input.** Branch `feat/ak-gpu-surface`. Fold the
  `rocprof_longctx.py` pattern (server under rocprofv3 for its whole life; windows cut by timestamp markers; holds
  `mi210_0`; 184-191 lane, `membind=3`) into `hotspots`. One anchor profile per anchor change, cached by anchor and
  request digest. Windows: short decode, long decode, concurrent decode, prefill. Per-kernel tables with registers,
  spills and occupancy (lb1 columns). Replaces "selected GPU serving profile unavailable". Done when a GPU serving
  target's planner prompt shows the per-window kernel table.
  - 2026-10-04: run 1 captured an anchor profile
    (`/mnt/raid0/llm/autokernel/campaigns/ak-27b-gpu-verify-20261004/store/gpu-serving-profiles/4bca25e9…/profile.json`).
    That the planner prompt rendered the table is not yet verified; check it in run 2's planner export, then tick.
- [ ] **AKX-ALL-17 (G5): keep gate across all tracked dimensions, both devices.** Branch `feat/ak-gpu-surface`.
  Extend INF-75's cross-workload keep gate (do not build a second one): a keep must not regress short decode, long
  decode, prefill at depth, concurrent aggregate, or capacity — peak VRAM (GPU) or RSS (CPU) must still fit at the
  recipe's context and slot count, measured by the residency sampler. A dimension that was not measured is reported
  as `not_measured`, never as a pass. Done when a keep record carries one verdict per dimension and a synthetic
  capacity regression is refused in a test.
  - 2026-10-04: `keep_dimensions` on research main (`9313ad32` + `eff6c41f`); the synthetic capacity refusal is
    tested. No keep has been recorded under it yet, so open.
- [ ] **AKX-ALL-18 (G4): GPU long-context and concurrent surfaces.** After AKX-ALL-4 and AKX-ALL-15. The C1
  instrument at np=4: four distinct restored slots at ~80k each (the operator's 36.8 tok/s regime, also RTG-58's and
  KVU-16b's). Controls: 1 slot at 80k, 4 slots at 4k. Floor calibration as AKX-ALL-6. Done when all three arms run
  inside a granted window with residency proofs and floors.
- [ ] **AKX-ALL-19 (G3): GPU attention and K/V-conversion routes with the DF2-9 gate.** After AKX-ALL-14/15/16.
  Routes: the FA dispatch in `fattn.cu`; the `fattn-vec`, `-tile`, `-wmma-f16`, `-mma-f16` bodies; the q8_0→f16 K/V
  conversion in `convert.cu`. Gates: `test-backend-ops -b ROCm0 -o FLASH_ATTN_EXT` against the CPU backend (head dim
  256, GQA 6, q8_0, KV padded and unpadded); the DF2-9 reproducer — all-NaN draft-model input features on 60–340-token
  prompts (`test-backend-ops` passed on that broken binary, so this gate is required); greedy output identity. Done
  when the routes are admitted and the DF2-9 reproducer refuses the known-bad build in a test.
- [ ] **AKX-ALL-26 — Width-invariance op probe: the first failing verify width per op, type and backend, on CPU and gfx90a HIP (intake-2021/2037/2038/2039/2046; filed 2026-10-20).** Experimental branch from the current champion tip (resolved live; the production kernel set is untouched), as a research-repo case family beside the AKX-ALL-10 selector. Each case is ONE graph holding a batched op over k columns/queries and k serial single-column ops on the same operands; compare bytes with memcmp, tolerance 0, repeated 3x so run-to-run nondeterminism is separated from width variance. Cases: MUL_MAT and MUL_MAT_ID over Q8_0, Q4_K, Q3_K, Q6_K, IQ2_XXS, IQ2_XS, IQ3_XXS, IQ3_S, IQ4_XS at the served models' real shapes; FLASH_ATTN_EXT over F16/Q8_0/Q4_0 KV with n_kv in {2048, 7168, 16384} plus one long-context point, counting the KV split (`parallel_blocks`) as part of the contract; GATED_DELTA_NET at the champion's head_count/head_size and gate form with the state threaded serially and the final state compared; k = 1..9 (8 = DFlash2 n-max 7 verify rows). Backends: CPU and ROCm0 (gfx90a; residency proven by `verify_ggml_linkage.sh` plus VRAM sampled during the run), and Vulkan on the MI210 as an extra column when a same-tip Vulkan build exists (a column, never a gate). Freeze a predicted-fail list from source reading BEFORE the first run (champion `mmvq.cu` CDNA2 route thresholds and `calc_nwarps`; the intake-2037 gfx90a reading is inference, not a source result). Output: one JSONL record per cell (both digests, first differing element) and a first-fail-k table per op/type/backend/route; UNSUPPORTED and ERR cells are rows, never omissions. Correctness work: build-role claim plus the device claim for the HIP half, no quiet host. Done when the table exists for CPU and HIP, the A/A repeat is clean, a deliberately width-dependent positive control FAILS, and every predicted cell is marked confirmed or falsified.
  - 2026-10-20 CPU half measured (HIP half NOT in this note; checkbox stays open until it is recorded). Probe `scripts/kernel_rnd/autokernel/loop/width_invariance_probe.cpp` + driver `width_invariance.py` (research repo `f1bf316a7`), evidence `artifacts/akx_all_26_cpu_20261020/` there (`cells.jsonl.gz` 4,761 cell records with both digests per rep and first differing element; `first_fail_tables.md`; `summary.json`; config echo `group_headers.jsonl`). Instrument: ggml CPU build of champion tip `e33229348` (`ak/champion/llama-cpp-ffc1bac82eec`, unmodified; worktree `/mnt/raid0/llm/worktrees/akx-all-26-cpu-20261020`, branch `experimental/akx-all-26-cpu-width-probe-20261020`), CPU-only ggml targets, `verify_ggml_linkage.sh` PASS, 24 threads on region q0 (nth=1 as an extra column). Predictions: the HIP-half agent's frozen list (47 `cpu`, 18 `cpu-native`, 1 `cpu[IQK_Q8_0]` rows, hashes in `/mnt/raid0/llm/tmp/gpu-queue-20261020/FROZEN_BEFORE_PROBES.sha256`) reused unchanged, plus a CPU addendum frozen 2026-10-20T16:47:27Z before the first run (a 6-command smoke ran after the freeze and is excluded). Cells: 4,113 with 3 reps, 0 A/A-unclean, 0 ERR, 0 missing groups; remaining 648 are UNSUPPORTED rows (ne00=640 for K/IQ types). Controls: width-dependent positive control PFFFFFFFF (FAILS at k>=2), width-independent negative PPPPPPPPP, injected bit flip FAILS at every k at the injected element.
  - First-fail k (route `cpu` = GGML_IQK=1, 24 threads; PASS = bit-equal k=1..9; identical across every shape a type can be built at): MUL_MAT Q8_0, IQ2_XXS, IQ2_XS, IQ3_XXS, IQ3_S F@2; Q4_K, Q3_K, Q6_K, IQ4_XS PASS. `cpu-native` (GGML_IQK unset): only Q8_0 F@2, everything else PASS. `GGML_IQK_Q8_0=1`: Q8_0 PASS. `GGML_ROWEXACT_N=9`: all nine types PASS. MUL_MAT_ID: Q8_0, Q4_K, Q3_K, Q6_K, IQ4_XS PASS in every ids mode; IQ3_XXS F@2 in every ids mode; IQ2_XXS, IQ2_XS, IQ3_S depend on routing: `shared` experts F@2, `disjoint` PASS, `rand` (seed 1) F@5. FLASH_ATTN_EXT: F16 KV F@2 at n_kv 2048/7168/16384/65536 at 24 threads and PASS at 1 thread; Q8_0 and Q4_0 KV PASS at both. GATED_DELTA_NET (H_v 48 and 32 scalar gate, 48 KDA gate; state threaded serially, final state compared): PASS at 24 and 1 threads.
  - Scoring of the frozen CPU rows: 63 confirmed, 3 falsified, 0 void; 40 of 40 addendum predictions confirmed. The 3 falsified rows are `CPU-MMID-IQ2_XXS/IQ2_XS/IQ3_S-ALL`, which predicted F@3 (low confidence, routing-dependent): with seed 1 the first routing collision is at k=5 and the first fail is k=5. Over seeds 1-6 x 3 shapes (54 cells) the first-fail k equals the first k at which any expert receives two (token, slot) rows in all 54 cells (seed 1..6 on M2048/IQ2_XXS: F@5,2,2,2,3,5), so the mechanism is confirmed and only the median-k guess missed. The frozen note that the tip differs from `4348de400` only in non-numeric `ggml-cpu.c` edits was not contradicted by any row.
  - Remaining for the box: the HIP/ROCm0 half (table, A/A, residency proof) from the MI210 agent; then the combined note and the tick.
  - **2026-10-20 HIP/ROCm0 half measured (gpu-queue lane; record only, no tick; evidence [`artifacts/gpu-queue-20261020/akx-all-26/`](../../artifacts/gpu-queue-20261020/akx-all-26/)).** Harness: `scripts/benchmark/akx_width_invariance/{width_probe.cpp,run_width_probe.py}` (research lane branch `lane/gpu-queue-20261020`, commit `93bdbce3e`, out-of-tree against the ggml API; the CPU half above used a different probe, so the two halves do not share a cell definition: HIP cell = one graph holding the batched op and k serial single-column ops on identical operands, memcmp tolerance 0, 3 repeats, k = 1..9, synthetic N(0,0.05) weights quantized per type, seeded routers, flash-attn mask rows = k with `GGML_PREC_F32`). Build: champion HIP build `/mnt/raid0/llm/kernels/builds/gpu-20261006-4348de400` (src `4348de400`, GPU-resident code identical to the tip `e33229348`, which differs only in `ggml-cpu.c`), `LD_LIBRARY_PATH=<build>/bin:/opt/rocm/lib`, `verify_ggml_linkage.sh` PASS on the probe binary, every cell record carries `backend_bound=ROCm0`, `device_description=AMD Instinct MI210` (1,016 of 1,016 cells), 8 host threads. Predictions: the frozen list (`FROZEN_BEFORE_PROBES.sha256`, 96 `rocm0` rows) used unchanged; a harness dev run on the CPU backend and a 4-id smoke on ROCm0 preceded the official run and are excluded.
    - **Result (`first_fail_table.md`, `scorecard.json`, `cells.jsonl`):** 96 predicted ROCm0 rows scored 66 confirmed, 30 partially (same FAIL verdict, earlier first-fail k), 0 falsified, 0 void, 0 ERR; 26 cells UNSUPPORTED (ne00 = 640 for K/IQ types, as predicted). A/A: 900 k-records, 0 unstable. Positive control PC-1 FAILS (by construction already at k=1: split-K summation order; it is the only k=1 identity violation). Residency: the probe ran as KFD process (one PID), VRAM 0.01 to 1.38 GB, gpu_busy up to 99 % in 16 samples; the kernels are millisecond-scale so VRAM use stays small, and the device is proven by the per-cell device field rather than by VRAM size.
    - **First-fail k (smallest k whose batched output differs from k serial columns; `-` none in 1..9), ROCm0 on the 27B dense shapes (ne00 5120/6144/17408):** MUL_MAT Q8_0 F@2; Q4_K F@2; Q3_K F@4; Q6_K F@5; IQ2_XXS, IQ2_XS, IQ3_XXS, IQ3_S, IQ4_XS F@5. On the small MoE-expert shapes (ne00 512/2048): Q8_0 F@2; Q4_K F@2; Q3_K F@4; Q6_K F@5 (M2048) and F@6 (M512); IQ2_XXS/XS, IQ3_XXS, IQ3_S, IQ4_XS F@9; on the F2560 shape the IQ types fail at F@5 and Q3_K at F@4. MUL_MAT_ID: Q8_0 and Q4_K F@2 on every shape; Q3_K and Q6_K F@2 (M2048, F2560) and F@9 (M512); IQ2_XXS, IQ2_XS, IQ3_XXS F@6 (M2048, M512) and F@2 (F2560); IQ3_S F@5 and F@2; IQ4_XS F@9 and F@2. FLASH_ATTN_EXT (D=256, GQA 6; F16, Q8_0, Q4_0 KV at n_kv 2048, 7168, 16384, 65536): FAIL at k=2 in all 12 cells (predicted k=3; inference, not tested: the ncols=1 and ncols=2 VEC kernels differ in `parallel_blocks`/reduction); the mixed K/V row is UNSUPPORTED as predicted. GATED_DELTA_NET: F32 state PASSES, BF16 state FAILS at k=2, both as predicted. The 30 partial rows are the dense K/IQ types at the 1|2 boundary, the F2560 shapes and all 12 FA cells.
    - **Cross-checks:** the Q8_0 first failure at k=2 matches DF2-18, where the first differing node at every width is the layer-0 Q8_0 `MUL_MAT`; the k=2 failure of Q4_K/IQ types on the dense shapes means the 1|2 geometry flip is not Q8_0-specific on gfx90a, which the frozen list had predicted only for Q8_0. Caveats: synthetic operands, one thread count (8 host threads), the harness's CPU-side validation is a dev subset only, and `GRAPH-GDN-builder` is graph-level and `not_probed`.
  - Remaining for the box: the combined CPU+HIP note and the tick (main).
- [ ] **AKX-ALL-27 — Width invariance as an observe-only keep dimension, with the reporting recipe (intake-2039/2044/2046; filed 2026-10-20).** After AKX-ALL-26 and DF2-18 deliver their tables. Extends the AKX-ALL-17 `keep_dimensions` record (no second gate). A keep whose footprint touches mmvq, mmq, fattn or GDN sources records its AKX-ALL-26 table against the ANCHOR's own table (the champion keeps knowingly width-variant routes, so the comparison is relative, never absolute zero): new failing cells, lower first-fail k, or unchanged; a keep for which the probe did not run records `not_measured`, never a pass. The model-level companion is the DF2-18 `rowexact` runner on the keep's build at widths 2, 4, 5, 8, reporting per width the reference-arm near-tie counts (pre-softmax top1-top2 gap < 1.0 and < 0.25), top-1 flips, row-mean-centred max delta and max dP, over a near-tie-dense corpus of real code rather than repetitive text; a zero-flip result on a confident prompt is recorded as uninformative and fixed-width perplexity is not accepted as evidence. Refuses nothing (refuse mode is monitor M7). Done when one historical mmvq-touching keep is replayed against its parent through the dimension with a non-trivial verdict and the record schema carries the recipe fields.

### P3: the DS41 dense-mask finding

- [x] **AKX-ALL-20: file the DS41 dense-mask finding in INF-77 and cross-reference INF-31.** ✅ 2026-10-04 Audit §5, code
  reading at `dd6c9cdbd` (`deepseek41.cpp:1095-1100`): final attention is a dense −inf mask over all compressed rows
  (`build_top_k_mask`), not a sparse gather, and `ggml_concat(raw_k, comp_k)` copies the full compressed plane every
  layer every step (~29 KiB per context token per step: ~0.9 GiB at 32k, ~3.6 GiB at 128k, vs ~8.7 GB/token of
  weights). The CPU FA kernel skips −inf cells one by one (`ops.cpp:9367`), so FA dot products stay ~640 rows per
  head; what grows with context is the concat, the mask fill/set_rows/add, the lightning indexer + `top_k` on 8
  index-source layers, and the host mask rebuild (DS41-C9). Arithmetic, not measured. The DS41-C123 text and the
  finding-1 / DS41-T2 notes are prepared in `PREPARED_ROWS.md` §D for the owning session. Done when DS41-C123 is in
  the DS41 handoff and AKX-ALL-12's route targets this path.
  ✅ DS41-C123 is in `deepseek-v41-flash-evaluation.md` (with the finding-1 / DS41-T2 notes), and AKX-ALL-12's scope
  names `build_attention_v41`, `build_top_k_mask` and the host mask rebuild (DS41-C9) as its targets.

### P4: end-to-end proofs

- [ ] **AKX-ALL-21: first CPU attention campaign round at depth.** After AKX-ALL-4/6/7/9/10/17. A Q38FN lane round
  where the planner sees the at-depth profile, authors a `cpu_fa_schedule` candidate, and the C1 surface plus the G5
  gate decide it. Done when one keep-or-refuse verdict at depth is recorded with all dimensions.
  - 2026-10-07 harness checkpoint: private candidate `20870bf42e9dbd487cf50bf7e303122af323ee9f` (v3 physical-owner lifetime repair `824320ac`) has independent SOURCE PASS for the exact 62-file composition. The committed manifest is `consolidated-harness/roster-import-composition-final/COMMITTED_RUNTIME_MANIFEST.json` (SHA-256 `6e78bb27847980bff6b9cf490f8c3ce57425f5e662ed30b462f1c3368deb129b`); final source-review report SHA-256 is `90f2aeac4600876e73938f2f4e6723b40a493fea2c006fae34d9ef861ce99b5c`. The prior `eedaf468` source approval was revoked after survivor-lifetime review. The corrected runtime driver has its own SOURCE PASS and explicit runtime-only ROOT approval, and one q2 CPUs 50–57, 10,800-second build-claim job (`consolidated-20261007T084059Z-r1`) is queued for lifecycle control, 13 focused modules, then the complete loop suite. No worker/pytest entry exists yet; this is not runtime validation, integration, landing, activation, or a performance result.
  - Environment-roster regression status: original import-root test run was 5 failed/3 passed; the next actual run was 3 failed/5 passed, exposing duplicate CPU-screen fixture kwargs and a wide generated-child mask. Test-only corrections are private research commit `4efeccb187ee5a44561f7d167048b83de66e5522`; the original `50c4a829` worktree is clean. One r2 test retry is queued under CPUs 48–49 build claim (launcher 2444478, region-lock 2444481); pytest has not started and no result is accepted. The r2 queue and complete-suite queue are separate claims and have no inferred ordering or pass state.
  - [ ] **AKX-ALL-23 — Q38FN's QSA top-k may not bound decode cost; structural lever if it doesn't.** (filed
    2026-10-05, ak-ds41-main) Q38FN (GGUF arch `qwen4exp`: 48 layers, full attention every 4th layer = 12 attn
    layers, 24 Q heads, 2 KV heads, head_dim 256) has QSA sparse attention with indexer `top_k=2048` (indexer 4
    heads, key_length 128, compressed blocks) — a **different attention family from DS41's dense mask-and-concat**
    (AKX-ALL-12/20); do not reuse that finding's arithmetic here. In llama.cpp `src/models/qwen4exp.cpp`
    (`build_qsa_top_k` / `build_attn_qsa`, ~L675-880) the top-k is realized by `ggml_set_rows` unmasking cells in a
    FULL `n_kv` KQ mask, then dense FA over all `n_kv` cells — so decode cost may still be **O(n_kv)** despite
    `top_k=2048`, i.e. the sparsity may be masked, not computed sparse. **Q38FN decode-vs-context is UNMEASURED**
    (code reading only, not benched). Structural lever if the at-depth profile shows it is not flat: gather the
    top-k K/V rows into a compact O(2048) buffer before FA instead of masking a dense `n_kv`-wide pass. Feeds the
    AKX-ALL-21 at-depth profile and `cpu_fa_schedule` candidate authoring directly — confirm or refute the O(n_kv)
    read before the planner commits to a candidate shape. Done when the at-depth profile shows flat (QSA bounds
    cost, drop this lever) or growing (structural gather lever is real; scope a candidate) decode cost.
  - [ ] **AKX-ALL-24 — candidate CPU kernel target: dense attention decode may parallelize only over Q heads.**
    (filed 2026-10-05, ak-ds41-main; **hypothesis, not measured**) workspace-ec's INF-59 YaRN CPU leg
    (`yarn-context-extension-research.md` → YARN-CPU-ATTN) measured Qwen3.6-35B-A3B (dense attention, not QSA)
    decode falling ~5x from 34K to 253K context (20.4 → 3.7 tok/s) while per-8K-turn append cost rose ~30x over
    the same range — a falloff that reads far off the DRAM-bandwidth roofline for a model whose weight-read cost
    per token is constant with depth. Candidate explanation, unconfirmed: CPU FA decode parallelizes only over the
    model's Q heads (16 for this model), so the achievable thread count at the attention-at-depth stage is capped
    well below the host's 96 threads regardless of context length. Label this a hypothesis until a thread-occupancy
    profile at depth either confirms or refutes it; it is a candidate explanation for YARN-CPU-ATTN's curve, not an
    independent claim.
- [ ] **AKX-ALL-22: first GPU campaign batch in a granted window.** After AKX-ALL-14..18. One GPU serving target,
  planner fed by the G2 profile, one candidate decided by G4 surfaces and the G5 gate, inside an AKX-ALL-15 window.
  Done when the batch's receipts show both claims, the residency proof, the window cycle and per-dimension verdicts.
- [ ] **AKX-ALL-25: inject the cafe-llama seeds AK-A, AK-B, AK-C, AK-G (CPU) and AK-D (GPU, low priority).** One inbox note per lane with knob, kernel, expected effect, measurement (text in the Stage-3 plan of the cafe-llama intake). AK-E and AK-F are conditional and are NOT injected until their triggers fire (CAFE-7, KLD gap). Done when the planner has the seeds in its inbox and the CPU ones are scheduled in a window. (intake-1925) — Owner: workspace-ec (2026-10-06).

### P5: tooling probes (research intake 2026-10-20)

- [ ] **AKX-ALL-28: TileLang gfx90a viability probe on the MI210 (decides whether TileLang becomes an AK GPU kernel-authoring surface).** In an isolated venv on a research scratch path (never the production tree or `/mnt/raid0/llm/llama.cpp`), install upstream `tilelang` (its `docs/get_started/Installation.md` at `876a59e` states the Linux PyPI wheel carries the ROCm backend) with a ROCm-6.2 torch build, one download at a time; confirm the target resolves to `{"kind": "hip", "mcpu": "gfx90a"}`; compile and run the plain f16 MFMA GEMM example at 3 tile configs; compare each against a torch fp32 reference (pass = compiles and NMSE <= 1e-4, fixed seed and shapes, wheel and torch versions recorded) and record `hipcc` compile seconds per config. Hold the MI210 inside an AKX-ALL-15 granted window plus the q3 CPU-region claim (CPU and GPU never overlap) and sample VRAM during the run to prove residency. Also read `tilelang/rocm/op/gemm/gemm_mfma.py`, `examples/amd` and `examples/dequantize_gemm` and record whether an IQ2/IQ3 grid-lookup dequant-GEMM is expressible on gfx9 (the tree at `876a59e` shows only a gfx950-gated MXFP4 example and nibble-unpack examples, no grid-decode example). Done when a note here records pass or fail per config with hipcc seconds, set beside the rebuilt loop's measured per-attempt build seconds from AK-HR-1(d) if that has landed, or the install or compile failure verbatim; no ggml integration is attempted and a pass only keeps TileLang a candidate.
  - **2026-10-20 RESULT (gpu-queue lane; record only, no tick; evidence [`artifacts/gpu-queue-20261020/akx-all-28/`](../../artifacts/gpu-queue-20261020/akx-all-28/)).** Isolated venv `/mnt/raid0/llm/tmp/gpu-queue-20261020/akx-all-28/venv` (Python 3.12.14 via uv; the host's 3.13 has no ROCm-6.2 torch wheel), installed one download at a time: `torch==2.5.1+rocm6.2` (hip 6.2.41133), `tilelang==0.1.15` PyPI wheel (`cp39-abi3-manylinux_2_28_x86_64`; tree `876a59e` is also version 0.1.15), `apache-tvm-ffi 0.1.12`; full freeze in `freeze.txt`. Target: `determine_target("auto")` returns `{"kind":"hip","mcpu":"gfx90a"}` (thread_warp_size 64); torch sees `gfx90a:sramecc+:xnack-`. Probe `probe.py`: the plain f16 `T.gemm` example (`examples/gemm/example_gemm.py` form, `num_stages=2`, 128 threads), M=N=K=1024 for the three tile configs 64x64x32, 128x128x32, 128x64x64, seed 20261020, NMSE against the torch fp32 reference, hipcc seconds from the hipcc child process, plus a second shape (2048x1024x512, reported only).
    - **Predeclared result: FAIL, all three configs, at compile time, verbatim.** `RuntimeError` from the hipcc step (`clang++ --offload-arch=gfx90a ...`, 20 errors) in `tilelang/src/tl_templates/hip/hip_fp8.h`: `unknown type name '__hip_fp8x4_e4m3'`, `'__hip_fp8_e5m2'`, `'__hip_fp8x2_e5m2'`, `'__hip_fp8x4_e5m2'`, `use of undeclared identifier '__HIP_E4M3'`. Cause: the header takes the OCP fp8 path for every arch except gfx940/941/942, and the host ROCm 6.2.0 `amd_hip_fp8.h` only provides the FNUZ types. Full error text in `results/probe_result.json` (config entries). hipcc seconds to the failure: 1.41, 1.33, 1.35.
    - **Diagnostics with local patches to the venv's installed headers, labelled as such and not counted as a pass:** variant B (force the FNUZ fp8 variants) moves the failure to `__builtin_amdgcn_wavefrontsize` (absent from ROCm 6.2 clang) in `scan.h`; variant C (replace it by 64 in `scan.h`) fails the same way in `reduce.h`; **variant D (both shims everywhere in `tl_templates/hip`) compiles and runs all three configs on the MI210: NMSE 4.32e-08 (primary) and 4.28e-08 (second shape) for every tile config, repeat bitwise identical, kernel source contains `mfma`, hipcc 1.41 / 1.45 / 1.55 s per config (compile wall 1.8-2.0 s), configs ordered as above.** So TileLang's gfx90a MFMA f16 GEMM works on ROCm 6.2 once two ROCm-7-era header assumptions are shimmed; unpatched wheel + this host does not compile. Per the task, a pass only keeps TileLang a candidate and no ggml integration was attempted; the comparison to the rebuilt loop's per-attempt build seconds (AK-HR-1(d)) was not made because that item has not landed.
    - **Residency caveat:** VRAM sampled during the run peaked at 1.06 GB with one KFD process and the torch device is gfx90a; the 1024^3 GEMMs are millisecond-scale so the 0.25 s gpu_busy sampler recorded no busy sample in the variant D run (earlier variants recorded 23 percent in 2 samples). Residency rests on VRAM, the KFD PID, the device arch string and the NMSE of GPU-resident results.
    - **Read of `gemm_mfma.py`, `examples/amd`, `examples/dequantize_gemm` (`tilelang_read_note.md`, tree facts tagged with file:line):** an IQ2/IQ3 grid-lookup dequant-GEMM is **expressible with workaround, not shown**: no literal-table primitive (the 256/512-entry grids and sign table need an extra global tensor, shared staging or raw HIP via `import_source`/`call_extern`; the only computed-index LUT is a 16-entry fp4 table in the gfx950-gated `quantize/mxfp.py:141-153`), the emitter forces int8/fp8 to `k_dim=32` (`mfma_macro_generator.py:141-143,190-191`, an instruction that is gfx940+), so on gfx90a the route is dequantize to f16/bf16 then MFMA or `T.dp4a` (`hip/common.h:128-143`, lowers to `__builtin_amdgcn_sdot4`, untested upstream), `num_stages` is stripped on every ROCm target except gfx950 (`pipeline_planning.cc:1155`), CI is gfx942 only, and IQ block sizes of 66/74/98/110 bytes are not 4-byte aligned. The `3rdparty/tvm` directory is empty in the checkout, so base-TVM lowering could not be read.
- [x] **AKX-ALL-29: Port map of Magnitude's Vulkan-backend mechanisms to gfx90a HIP / EPYC CPU (read-only)** Done when every Magnitude Vulkan-floor feature and tuning mechanism is classed native / port-candidate / not-portable with the HIP equivalent and consumer named. (re-scoped 2026-10-20 by operator: eligibility was already falsified 2026-07-02; the question is portability) ✅ 2026-10-20
  - **Result note (2026-10-20, host `Beelzebub`, kernel 6.14.0-37-generic, origin/main `4c83f813b`):** ELIGIBILITY ANSWER: `no Vulkan tuning evidence obtainable on the MI210 without a driver-stack install`. Evidence (read-only): `which vulkaninfo` → not found; `ldconfig -p | grep -i vulkan` → empty; no `libvulkan*` in `/usr/lib/x86_64-linux-gnu/`; no `*vulkan*` file under `/opt/rocm`, `/usr/lib` or `/usr/share` except the CMake module `FindVulkan.cmake`; no ICD manifests in `/usr/share/vulkan/icd.d/` or `/etc/vulkan/icd.d/`. Installed GPU-stack packages (`dpkg -l | grep -iE 'rocm|hip|amdgpu|mesa|vulkan'`): only `libdrm-amdgpu1:amd64 2.4.125-1ubuntu0.1`. `/opt/rocm` exists (ROCm, not Vulkan). `/dev/dri` has card1-3 and renderD128-129. Floor items (Vulkan 1.3, bufferDeviceAddress, vulkanMemoryModel, subgroup size 32/64, 8/16-bit storage, workgroup_memory_explicit_layout, RTE fp32): none could be checked because no device enumeration is possible, so none is recorded as passed; all are unverified. Floor source: `/mnt/raid0/llm/tmp/dive-1979/repo` at commit `940e51b`, `facts.rs` L714-L745 (read only). No install, no build, no Seismic run. The MI210 was not queried, since vulkaninfo is absent. Checkbox left open for main review and not ticked.
  - **Prior finding (pointer, 2026-10-20):** the eligibility question was already settled — Vulkan on gfx90a was falsified on this hardware on 2026-07-02 (no ICD for CDNA2; `design-backlog-triage-2026-07-23.md:229`, `fable5-window2-findings-03-portfolio-and-master-queue.md:45`); the note above only re-confirms it. The port map below answers the re-scoped question.
  - **Port map (2026-10-20, documentation-only; zero compute, no install, nothing built or run; checkbox left open for main review).** Sources, read as untrusted data: Magnitude `inference/seismic/` @ `940e51b` (`backends/vulkan/src/{facts,device,formation,seal,probe,memory,direct}.rs`, `runtime/src/native/vulkan_prelude.glsl`, `lang/native-library/vulkan/{element,slab,packets}.glsl`, `runtime/src/native/{tune,search,plan,replay,admission,observation}.rs`, `measure/src/{clock,session}.rs`, `native-tests/fixtures/vulkan/`). Ours, read-only: production tree `/mnt/raid0/llm/llama.cpp` HEAD `ffc1bac82` (`ggml/src/ggml-cuda/`), epyc-inference-research `18c72a1c1` (AutoKernel GPU lane). Excluded and cross-referenced instead: `packets.glsl` IQ2_XS/IQ2_XXS/IQ3_XXS decode layout and `grids.glsl` (see INF37-IQ-4's 2026-10-20 note in `mi210-q8-dequant-gemv-roofline.md`). Scope: every item of the floor at `facts.rs` L714-L745 plus each kernel-library, tuning and measurement mechanism; CPU is out of scope for the Vulkan floor (the Vulkan backend has no EPYC analogue), so the CPU half of the title applies to no row. Magnitude's goal in these mechanisms is bit-reproducible cross-backend semantics (prelude L1-L26), ours is NMSE/greedy-identity/throughput gates, which is the main reason several rows classify as "no value". Class key: **N** = already native in HIP: nothing to port; **P** = port candidate → AK seed (seed id in the sub-list); **X** = not portable / no value (reason given; X rows are classifications for the operator to confirm, not dismissals of the source).

    | ID | Magnitude mechanism (locator) | What it buys Magnitude | gfx90a HIP equivalent (native status) | Ours already has (evidence) | Effort | Consumer | Class |
    |---|---|---|---|---|---|---|---|
    | V1 | Vulkan 1.3, synchronization2, maintenance4, timelineSemaphore (`facts.rs` L712, L721-L723; `direct.rs` L377-L460) | One submission-numbering timeline the host can gate/wait on; modern barriers | hipStream + hipEvent + graphs; native | `ggml-cuda.cu` streams/events; HIP graphs (`ggml-cuda.cu` L2566 `use_cuda_graph`) | - | none | N |
    | V2 | Compute-only queue with timestamps; calibrated timestamps; per-launch timestamp batch (`facts.rs` L713, `device.rs` timestamps, `direct.rs` L476-L540, L717-L760) | Per-launch device intervals on the host clock without replay | hipEventRecord per launch, rocprofv3 kernel trace; native | AKX-ALL-16 rocprofv3 per-window kernel table (open); `gfx90a_isa_audit.py` | - | AK GPU profile | N |
    | V3 | bufferDeviceAddress, shaderInt64, scalarBlockLayout; every tensor a 64-bit pointer; launch args in one block addressed by the only push constant (`facts.rs` L714-L715, L720; prelude L55-L64; `element.glsl` L52-L71; `direct.rs` L6-L8) | Pointer-style kernels, no descriptor sets, one fixed ABI | raw device pointers and by-value kernel args; native | all of `ggml-cuda/`; production q8pf kernel even builds a bounded buffer resource (`mmvq.cu` L1033) | - | none | N |
    | V4 | shaderInt8/Int16, storageBuffer8/16BitAccess, shaderSubgroupExtendedTypes (`facts.rs` L716-L719, L727) | Sub-word loads/stores of int8/fp16/bf16 codes | `int8_t`, `__half`, `uint16_t` global loads; native | `ggml-cuda/` quant blocks (`block_q8_0` etc.); `common.cuh` L374 16-byte copy width | - | none | N |
    | V5 | subgroupSizeControl, computeFullSubgroups, required subgroup 32, logical 32-lane subgroup over a 64-lane wave via clustered ops (`facts.rs` L729-L731; `formation.rs` L218-L231; prelude L18-L45) | Same kernel source on 32- and 64-lane GPUs | gfx90a has no size control; fixed wave64; native by construction | `common.cuh` L365-L371 `ggml_cuda_get_physical_warp_size()` = 64; `warp_reduce_sum<width>` templated | - | none | N |
    | V6 | Subgroup ops (vote, ballot, shuffle, clustered, quad); fixed-order butterfly reduction instead of `subgroupAdd` for floats (`facts.rs` L732-L733; prelude L342-L360) | Bitwise-identical float reductions on every lane and run | `__shfl_xor`, `__ballot`; native; same xor order | `common.cuh` L433-L441 `warp_reduce_sum` xor butterfly from `width/2` down to 1; width-invariance of cross-warp LDS sums is owned by AKX-ALL-26/27 | - | AKX-ALL-26/27 | N |
    | V7 | VK_KHR_workgroup_memory_explicit_layout (base, 8-bit, 16-bit, scalar) (`facts.rs` L734-L735) | One shared block aliased as differently typed views | `extern __shared__` with casts; native (LDS 64 KiB per workgroup on gfx90a, above the 32 KiB floor) | `mmq.cuh` L833 `extern __shared__ int data_mul_mat_q[]`; `mmvq.cu` L1038 double-buffered `lds_w` | - | MMQ seeds | N |
    | V8 | vulkanMemoryModel + device scope (`facts.rs` L725-L726) | Defined cross-workgroup visibility for atomics/flags | `__threadfence`, `__hip_atomic_*` scopes; native | `fattn-vec.cuh` L534 completion-counter `atomicAdd` pattern | - | none | N |
    | V9 | shaderIntegerDotProduct (`dotPacked4x8EXT`, prelude L382-L388; `facts.rs` L728) | dp4a-class int8 dot without saturation | `v_dot4_i32_i8` via `__builtin_amdgcn_sdot4`; native | `common.cuh` L694-L697 `ggml_cuda_dp4a` (CDNA branch) | - | MMQ seeds | N |
    | V10 | RTE fp32 + SignedZeroInfNanPreserve + `NoContraction` on every float op, sealed into the SPIR-V (`facts.rs` L737-L738; `seal.rs` L1-L9; prelude L1-L16) | CPU/CUDA/Metal/Vulkan bit-parity for a reference semantics | gfx90a default is round-to-nearest-even fp32; contraction is a compiler flag (`-ffp-contract`), not sealed; no per-op seal | production uses default contraction (no `fp-contract` in `ggml/src/ggml-hip/CMakeLists.txt`); gates are NMSE/greedy-identity, not bit-parity | M (build arm + per-op audit) | AK build recipe (AKX-ALL-14) | X: sealing every op NoContraction removes the fma/mad contraction MMQ and FA throughput relies on, to buy bit-parity our gates do not require; revisit only if a bit-exact GPU route is ever filed (AKX-ALL-9 is CPU-only) |
    | V11 | Correctly rounded fp32 div/sqrt in integer code, `OpFmaKHR` binding, open-time rounding/fma probes (`prelude` L232-L296; `probe.rs` L1-L15; `formation.rs` L180-L188) | Works around Vulkan compilers that trap on `RoundingModeRTE` fp32 divide or split `fma` (RADV, NVIDIA 580) | hipcc lowers `/`, `sqrtf`, `fmaf` to IEEE-correct sequences / `v_fma_f32` natively | nothing needed | - | none | X: the mechanism is a workaround for Vulkan driver defects that do not exist in the HIP toolchain |
    | V12 | f32 atomic add, shared int64 atomics as gated facts (`facts.rs` L34-L35, L291-L292) | Atomic split-K/accumulation paths where the device has them | `atomicAdd(float)` (HW fadd needs `-munsafe-fp-atomics` on gfx90a); native | integer `atomicAdd` only (`count-equal.cu` L25, `fattn-vec.cuh` L534); float atomics deliberately unused (order-dependent sums conflict with width invariance, AKX-ALL-26/27) | - | none | N |
    | V13 | Cooperative-matrix / wide-accumulator / mixed-dot facts select kernel paths (`facts.rs` L636-L650) | Per-device path choice from probed facts, incl. disabling a slower path on one driver | MFMA via compile-time arch macros | `common.cuh` L265 `AMD_MFMA_AVAILABLE`; `mmvq.cu` L483-L523 per-arch parameter table; rocWMMA FA arm (AKX-ALL-14) | - | MMQ seeds | N |
    | V14 | VK_EXT_memory_budget; `measured()` counts driver memory (pipeline creation, command memory) beyond allocations; block allocator 64 MiB-1 GiB, empty blocks freed; upload/staging placement (`facts.rs` L736, L744-L753; `device.rs` L800-L860; `memory.rs` L1-L19) | Honest headroom accounting; no hidden driver memory | `hipMemGetInfo`, VMM pool, pinned host memory; native | `ggml-cuda.cu` L535-L683 VMM pool (on for HIP, `common.cuh` L254), L4557 `cudaMemGetInfo`, L1282 pinned host buffers; AKX-ALL-17 peak-VRAM residency sampler covers driver/scratch memory in its total | - | INF37 residency, AKX-ALL-17 | N |
    | V15 | Limits floor: 32 KiB shared, 1024 invocations, 65535 groups, 128 B push constants (`facts.rs` L739-L743) | A portable lower bound | gfx90a exceeds all of them | - | - | none | N |
    | V16a | Pipeline cache keyed by `pipeline_cache_uuid` (`formation.rs` L218-L248; `facts.rs` L461-L470) | Avoids recompiling SPIR-V per driver | none: ggml-hip kernels are ahead-of-time code objects in the fatbin, no JIT | - | - | none | X: nothing is compiled at run time on our stack, so there is nothing to cache |
    | V16b | Tuning identity = vendor, device, name, driver id and version, so a driver update invalidates stored tuning (`facts.rs` L521-L531) | Tuning results are never replayed across a driver change | device id + HIP runtime/kernel-driver/firmware version as key | AK build recipe pins ROCm 6.2.0 only (`controller/build_recipe.py` L203-L244 `check_rocm_version`); amdgpu kernel-driver and firmware versions are not part of it (this read found no such field; the vidya `autokernel_rocm_diagnostic.py` adapter was not read) | S | AK GPU receipts / keep gate | P (S1) |
    | M1 | Specialization-constant geometry (workgroup size, group-memory views) + declared-domain plan search: domain never materialised, one step at a time, parameters grouped by co-runnable launches (`formation.rs` L205-L215; `plan.rs` L1-L25) | Searches launch geometry without enumerating the product | C++ template params + `__launch_bounds__`, edited per build; native, but geometry tables are hand-set per type | `mmvq.cu` L786-L850 `calc_nwarps` / L916 `calc_rows_per_block`: GCN table tuned only for Q4_K/Q6_K (fixed 1536) and Q8_0 (nwarps 4/8, AK-made); every other type, IQ2/IQ3 included, takes the generic GCN row | M | AK GPU search dims; INF37 IQ roles; MMQ seeds | P (S2) |
    | M2 | Objective = invocation-demand-weighted elapsed service relative to the default, not a single-shape time (`search.rs` L1-L25, `Cost::relative` L53) | A kernel that wins one shape but loses the shapes that dominate service is not chosen | none needed: scoring is search policy | AK scores on serving throughput; AKX-ALL-16 per-window kernel tables give launches per token but the planner does not weight candidate shapes by them (this read of AKX-ALL-16/17 only) | S | AK GPU search dims | P (S3) |
    | M3 | `LaunchKey`: configurations that run the same device work at a point share one measurement (`search.rs` L33; `direct.rs` L32-L47 `LaunchKind`) | Saves timing of edits that compile to identical work | compare gfx90a code-object kernel bytes | `gfx90a_isa_audit.py` `diff` already extracts per-kernel ISA and registers as an accept gate, but is not used to skip timing identical kernels | S | AK GPU search dims | P (S4) |
    | M4 | Paired sign test with mixture martingale; budget rule; replay of recorded surveys (`measure/statistics.rs` L123; `tune.rs` L2118-L2130; `replay.rs` L1-L30) | Resolves leads with a Ville-type guarantee; ends a comparison at first non-ahead round | policy, not a device feature | `evaluator/statistics.py` sign test-martingale; budget rule and replay filed as AK-RI-ARMSEARCH-1 (dormant trigger) | - | AK GPU search dims | N |
    | M5 | Untimed lead pass per sample, repetitions calibrated to a minimum device time, shuffled order, sustained-clock raise before a session (`measure/session.rs` L1-L40; `clock.rs` L1-L45) | Reads at the clock serving sees; removes first-after-idle bias | MI210 SCLK ramps 800 -> 1700 MHz | `evaluator/devices.py` L76-L161 models gfx90a clock ramp (first nominal SCLK at 0.25 s) in ranked-duration admission; `loop/bench.py` L100 `WARMUP_PAIRS = 1` discarded | - | AK GPU measurement | N |
    | M6 | Numerical admission in rounding steps of the governing type: `sqrt(error_power/step_power) <= alpha`; integers/packed/NaN pattern bit-exact (`admission.rs` L1-L25) | One type-relative tolerance for fp32/fp16/bf16 outputs | policy, not a device feature | AK keep uses NMSE thresholds + `test-backend-ops` + DF2-9 NaN reproducer (AKX-ALL-19) | S | AK GPU keep gate; MMQ seeds | P (S5) |
    | M7 | Written-region audit: every output element outside the declared written rows must equal the default's bits; fixture `stray_write.comp` plants a stray write (`observation.rs` L18-L40; `native-tests/fixtures/vulkan/stray_write.comp`) | Catches out-of-extent writes that an output-only compare misses | poison-fill guard bands around dst/KV views | `test-backend-ops` compares dst only (DF2-9 passed it on a broken binary, per AKX-ALL-19) | S | AK GPU keep gate | P (S6) |
    | M8 | Graph = secondary command buffers recorded once with fixed argument blocks, replayed in segments (`direct.rs` L174-L345, L614-L660) | Cuts per-launch CPU cost | HIP graphs | `ggml-cuda.cu` L2566-L2654 graph path with `cudaGraphExecUpdate`; megakernel/persistent decode bounded at +5.9% (`design-backlog-triage-2026-07-23.md`) | - | none | N |
    | M9 | `rows16` planar resident layout for q4k/q5k/q6k/q8 and dense: separate code, scale and super planes, 16-byte aligned packet loads (`packets.glsl` L1-L30, L86-L120, Q8 at L291, L353; IQ grid kinds excluded) | Aligned 16-byte loads; no 34-byte block straddling | needs a load-time repack and new GEMV kernels | production reads `block_q8_0` (34 B, not DWORD-aligned) and works around the straddle with a rounded-up buffer resource (`mmvq.cu` L1027-L1033); SoA-repack already on file as a conditional lever (`mi210-q8-dequant-gemv-roofline.md` L179: only if coalescing measured poor, currently deemed healthy) | L | MMQ seeds; INF37 (non-IQ part) | P (S7) |
    | M10 | Factored dot `scale*dot(code,x) + bias*sum(x)` with per-16 activation sums computed once per staged activation (`packets.glsl` L17-L20) | Removes per-weight-row min/bias work | `block_q8_1` carries the activation sum | `ggml-common.h` L268 `block_q8_1` (`ds` = d, s); `vecdotq.cuh` L116-L133 uses `ds8.y` | - | none | N |
    | M11 | Scale-format decode by arithmetic (E8M0, UE4M3), even/odd nibble split into two vec4s, 16-byte vector loads (`packets.glsl` L141-L183; `element.glsl` L52-L71, L151-L171) | No tables, exact small integers, wide loads | `ldexpf`, `int4`/`uint4` loads; native | `common.cuh` L834-L852 e4m3 decode via `ldexpf` under HIP; L374 16-byte copies | - | none | N |
    | M12 | Slab address table: a tensor's rows live in separately allocated slabs reached through a table of 64-bit addresses (`slab.glsl` L1-L26) | Grows KV storage incrementally without moving it | pointer table in a kernel; native | llama.cpp KV is one preallocated contiguous buffer on the VMM pool | M | RTG-58 / KVU-16b | X: capacity here is bounded by fixed ctx x slots, so incremental growth buys nothing, and the table adds a dependent load per row; flag for operator review if slot save/restore ever needs non-contiguous KV |
    | M13 | Precision-gated hardware approximations (`ex2`, `lg2`, `rcp`, `rsqrt`, `tanh`) admitted only where an entry's precision gate allows them (prelude L294-L330) | Cheap transcendental where the numerics gate permits | `__expf`/`exp2f` -> `v_exp_f32`; native | online-softmax uses exact `expf` (`fattn-common.cuh` L790-L791, L894-L895, L963) | S | AKX-ALL-19 FA route | P (S8) |
    | M14 | Compile pipeline: glslang -> seal -> spirv-val -> dead-code-only cleanup; "the driver compiler does all optimization" (`formation.rs` L20-L130) | Validated, reproducible modules; no float-rewriting passes | hipcc/LLVM + offline ISA audit | `gfx90a_isa_audit.py` is the standing static gate | - | none | N |
    | M15 | Element kinds as compile-time constants; bf16 RNE and fp16 conversions in integer code (`element.glsl` L1-L50; prelude L67-L119) | Template-free kernels with exact conversions | C++ templates; `__float2bfloat16` | `ggml-cuda/` templated kernels, `convert.cu` | - | none | N |

    Counts: 32 rows, N = 20, P = 8, X = 4 (V10, V11, V16a, M12).
  - **Seed hypotheses (sub-list; each is a hypothesis with a falsifier; no seed file written and no AutoKernel config touched; filing them into the AK inbox is a separate step).**
    - S1 (V16b, tuning identity): a GPU keep or baseline receipt is only comparable if the amdgpu kernel-driver version, firmware and HIP runtime version match; falsifier: the existing receipts already record those fields, or two receipts of one unchanged kernel taken across a driver/firmware change differ by less than the AK noise floor unit.
    - S2 (M1, geometry sweep): on gfx90a the generic GCN `calc_nwarps`/`calc_rows_per_block` row is not optimal for IQ2_XS/IQ3_XXS/IQ4 batch-1 GEMV, as Q8_0 was not (+4.6% from nwarps alone); falsifier: a declared-domain sweep of nwarps x rows_per_cuda_block per type finds no cell beating the table by more than the noise floor unit under greedy-identical output.
    - S3 (M2, demand-weighted objective): ranking candidates by sum over shapes of (launches per token x time at shape), relative to the incumbent, picks a different keep than tg128 alone for some recorded candidate; falsifier: on the recorded GPU candidates both objectives give the identical ordering.
    - S4 (M3, identical-work dedupe): some AK GPU edits compile to a byte-identical gfx90a kernel body and so need no timing; falsifier: none of the recorded candidates has a kernel body identical to the incumbent's under `gfx90a_isa_audit.py diff`.
    - S5 (M6, type-relative tolerance): a rounding-step bound (`sqrt(error_power/step_power) <= alpha`) separates accept from reject differently from the NMSE gate for fp16/bf16 outputs; falsifier: both gates give the same verdict on every recorded candidate.
    - S6 (M7, written-region audit): GPU kernel edits can write outside their declared extent without failing `test-backend-ops`; falsifier: poison guard bands around dst and KV views stay intact across all recorded candidate runs, which would show the check adds no catch.
    - S7 (M9, planar Q8_0 layout): a rows16-style Q8_0 layout (aligned 16-byte code loads, separate scale plane) lifts batch-1 Q8_0 GEMV achieved bandwidth over the current q8pf path; falsifier: an isolated-op bench shows no gain above the noise floor unit, or coalescing is already healthy as the roofline handoff records (the reason this stays conditional).
    - S8 (M13, approximate exp arm): `exp2`-based `v_exp_f32` in the FA online softmax passes the FA op-test NMSE gate and gains decode throughput; falsifier: the op-test NMSE exceeds the gate, or the gain is inside the noise floor unit.
  - **Routing (2026-10-20, main-approved; rule: we fix the harness, AutoKernel only edits kernels).** Kernel seeds filed as epyc-inference-research `scripts/kernel_rnd/autokernel/loop/seeds/hypotheses/`: S2 -> `04-iq-mmvq-geometry-sweep.md` (AK-H-IQG-1), S7 -> `05-q8-planar-rows16-layout.md` (AK-H-Q8P-1), S8 -> `06-fa-softmax-approx-exp.md` (AK-H-FAE-1); no campaign started. Harness and objective items S1, S3, S4, S5, S6 are the tasks below. Duplicate check before filing: S1 is PARTIAL (host identity already records BIOS, kernel release and GPU VBIOS in `loop/production.py` host facts, and `c5_rocm_oracle.py` records rocm/driver versions for the oracle; missing is amdgpu module version and HIP runtime version in GPU receipts); S5 is PARTIAL (`evaluator/correctness.py` L1406 already has `exact_bitwise | ulp_bounded | metric_bounded` modes; open is whether the GPU keep gate uses a type-relative bound for fp16/bf16); S3, S4, S6 found no equivalent.
  - [ ] **AKX-ALL-29.1 (S1, partial duplicate): add the amdgpu kernel-module version and HIP runtime version to the GPU host-identity facts carried by receipts.** Falsifier: GPU receipts already carry both (then close as done), or two receipts of one unchanged kernel across a driver/runtime change differ by less than the noise-floor unit.
    - 2026-10-20 note (akx-all-29-harness, research 6b8fb5615): falsifier checked - receipts carried BIOS/kernel/VBIOS only (`read_host_facts`), no amdgpu or HIP version, so not already done. `read_host_facts` now adds `amdgpu_module_version` (/sys/module/amdgpu/version; None on this host, in-tree module, `kernel_release` is its version), `amdgpu_srcversion`, `rocm_version` (/opt/rocm/.info/version) and `hip_runtime_version` (libamdhip64.so.X.Y.Z); additive and nullable, old records never read as changed. Test: `test_gpu_stack_versions_are_read_and_nullable`. Not ticked.
  - [ ] **AKX-ALL-29.2 (S3; objective change; operator decision before adoption): score GPU candidates by sum over shapes of (launches per token x time at shape) relative to the incumbent, using the AKX-ALL-16 per-window kernel table.** Changes what AutoKernel optimises. Falsifier: on the recorded GPU candidates the demand-weighted ranking equals the tg128 ranking.
    - 2026-10-20 evidence note (read-only; no run, no claim; checkbox not ticked; the objective change stays the operator's decision). **Falsifier: NOT DECIDABLE on disk.** Recorded GPU history is `campaigns/ak-27b-gpu-verify-20261004` (`store/experiments.db`: 13 rows, 5 `gate_refused`, none kept or timed: mechanisms `akm-gfx90a-q8-tiny-streamk-cap` x3 and `akm-q8-j16-single-tile-streamk-five-cta` x2, every one `MUL_MAT failed on ROCm0`, `effect_fraction` null) and the 2026-08-12 `hip-silu-decision-grade-r4..r6` / `hip-arm-silu-roundtrip-r2..r4` receipts (a standalone fp32 SiLU HIP file timed in isolation against Torch-ROCm, 20 paired blocks, ~1.077x in r6; no tg128, no per-shape table). The other stores (`ak-ds41-cpu-decode`, `ak-q38fn-cpu-decode`) are CPU. So no GPU candidate has a tg128 (`aggregate_tok_s`) result and none has candidate-side time at any shape: there are zero candidates to rank by either objective, and a one-candidate ordering is trivially identical. What IS on disk for the incumbent: the AKX-ALL-16 anchor profile `store/gpu-serving-profiles/4bca25e9.../run/trace/` with `serving_kernel_stats.csv` (58 rows: Calls, TotalDurationNs per kernel; e.g. `mul_mat_q<Q8_0,16>` 18407 calls, 55.61% of device time) and `serving_kernel_trace.csv` (171,588 timestamped dispatches with grid size) plus `profile.json` spans for `prefill` and `short_decode` (windows `concurrent_decode`, `long_decode`, `prefill_at_depth` skipped). Launches per token for the incumbent are derivable from trace x span x the decoded-token count in `run/server.log`; this note did not derive them, because the candidate half is missing and a one-sided table decides nothing. Missing, precisely: (a) any GPU candidate that passed the correctness gate and reached timing; (b) per-kernel dispatch counts and durations captured for the candidate build over the same windows. Cheapest way to record: when a GPU candidate reaches the timing stage, rerun the AKX-ALL-16 profile for it on the same windows and store `serving_kernel_stats.csv` next to its experiment row (the profile harness exists; the gap is that no candidate has reached it). Also note AKX-ALL-16's planner-prompt rendering of the table is still unverified.
  - [ ] **AKX-ALL-29.3 (S4): skip timing of a candidate whose gfx90a kernel bodies are byte-identical to the incumbent's, using `gfx90a_isa_audit.py diff`.** Falsifier: no recorded candidate has a kernel body identical to the incumbent's, so there is nothing to skip.
    - 2026-10-20 note (akx-all-29-harness, research 6b8fb5615): `loop/noop_build.py` hashes .text/.rodata/.data of every gfx90a code object (reuses `gfx90a_isa_audit` ELF/bundle reader; `gfx90a_isa_audit.py diff` itself is a register gate, not a byte compare, so it is not the comparator). `run.py` measure raises `loop.NoOpBuild` before `measured_bench_compare` for HIP recipes; `iterate` records status `no_op_build` with both body hashes, never a keep; `serial_scheduling` classes it invalid. Unreadable hash on either side returns None and falls through to normal timing. Real production lib hashes (135 code objects, 0.1 s). Falsifier (any recorded candidate identical to its incumbent) NOT evaluated: needs recorded candidate build dirs, which the harness change does not read. Note R23-40: -j64 HIP builds are not bit-reproducible, so hits are expected mainly for serial builds. Tests: `test_noop_build.py` (9, synthetic code objects), `test_loop.py` no-op case. Not ticked.
  - [ ] **AKX-ALL-29.4 (S5; gate change; verify against the MEASUREMENT trust boundary first): evaluate a type-relative rounding-step bound (`sqrt(error_power/step_power) <= alpha`) as an additional fp16/bf16 output check next to the existing `ulp_bounded` / NMSE modes.** Falsifier: the bound gives the same verdict as the current gate on every recorded candidate. The trust boundary is human-amendment-only, so this task may only prepare the comparison, not change the gate.
    - 2026-10-20 evidence note (read-only; no new run; checkbox not ticked). **Gate mode in use:** `execution/t0_provider.py` L2988-L3004 projects every `test-backend-ops` case into `ReferenceComparison(mode="metric_bounded", metric_id=test_backend_ops_error/v1 (AK_REF_V1 observed/tolerance))`; `evaluator/correctness.py` L2934-L2949 (`check_exact_reference_comparison`) then fails a case when `max_error_observed > tolerance_error`. `ulp_bounded` (L2934) and `exact_bitwise` (L2931) exist in the evaluator but the provider constructs neither; the GPU keep gate is therefore the NMSE-style metric_bounded mode, with no per-output-dtype branch. **Falsifier: NOT DECIDABLE on recorded results.** The only recorded GPU correctness outcomes are the 5 `gate_refused` rows of `ak-27b-gpu-verify-20261004` (5 distinct candidate diffs; `MUL_MAT failed on ROCm0`); their stored detail is a 2000-character tail of the failing case list (all shown cases are `type_a=q4_K`, `type_b=f32`, a type the Q8_0 patches do not name) and carries no observed-error number, no tolerance, and no output dtype, so a rounding-step bound cannot be computed for any of them. No fp16/bf16 output candidate exists on record. The one other recorded GPU error set, `hip-silu-decision-grade-r4..r6`, is fp32 with an absolute-error gate (atol 3e-06, max recorded 1.23e-06 over 24 cases, oracle `independent_host_double_stable_silu/v1`); it is accepted by that gate, and the receipts do not record output magnitudes, so the step-relative bound is not computable from them either. Candidates affected on the evidence: none can be listed. What would decide it: persist `AK_REF_V1` observed, tolerance and per-op output dtype (and output RMS) for every gated case, not a truncated stdout tail; this is a record-keeping gap on the write side. **Trust boundary:** the correctness gate is a MEASUREMENT trust-boundary item (human-amendment-only); this task prepares the comparison only, and any change to the gate is the operator's decision.
    - 2026-10-20 WRITE SIDE NOW EXISTS (lane `ak-gate-detail`; research repo `ed059b186`; checkbox not ticked; no gate behaviour change). The evidence note's gap is closed prospectively: `loop/gates.py` `op_correctness` (the gate that produces the stored `gate_refused` detail) now also attaches `Verdict.case_records`, written under the key `case_records` in `Verdict.to_dict()` (so on the experiment row's `gates[]` entries), one compact record per gated `test-backend-ops` case: `op`, `params` (<=256 chars), `types` (the `type*=` entries of the case params, e.g. `{type_a: q4_K, type_b: f32}`), `status`, `passed`, and from the `AK_REF_V1` receipt `metric_id`, `observed`, `tolerance`, `fraction_of_tolerance`, `oracle_id` (null when the case carried no receipt, e.g. the GPU run without `--autokernel-properties`, or a failing case). `output_dtype` and `output_rms` are always null: the instrument prints neither and no computation was added. Failing cases sort first then worst fraction-of-tolerance; capped at 256 per verdict; sharded runs merge their shards' records. Key is omitted when None, so old rows and verdicts without records are byte-identical; pass/fail logic, tolerances and modes untouched (`evaluator/correctness.py` not edited). This still cannot decide the falsifier alone: it needs output dtype and RMS, which are an instrument-side (`test-backend-ops` receipt) change, not made here. Rows written before this commit carry nothing.
  - [ ] **AKX-ALL-29.5 (S6): add poisoned guard bands around dst and KV views to the GPU candidate check, to catch writes outside the declared extent that `test-backend-ops` misses.** Falsifier: guard bands stay intact across all recorded candidate runs, so the check adds no catch.
    - 2026-10-20 note (akx-all-29-harness, research 6b8fb5615): `loop/guard_bands.py` = harness side only: `GuardedArena` (position-dependent poison head/tail bands per view, alignment pad guarded), `check()` names view, band, offset, and `verdict_from_receipt` (opt-in, not in the default gate chain; missing/incomplete receipt fails that call). Tested on CPU buffers (`test_guard_bands.py`, 9). NOT yet producing evidence on a GPU candidate: `test-backend-ops` allocates dst/KV in llama.cpp `tests/test-backend-ops.cpp`, so the producer is a llama.cpp-experimental change (allocate guarded views, read back, emit the receipt). Falsifier not evaluated. Not ticked.

- **AK-RI-ARMSEARCH-1 (durable trigger, no checkbox; intake-1979):** activate when AKX-ALL-13 widens the runtime-arm dimensions and at least 20 runtime-arm attempts with per-block samples exist (the three `runtime-arms-attempts.json` files hold 10 attempts of 5 pairs, all keep-grade matched-floor comparisons, which cannot support a search-order replay). Design comparison on record: AK's selection test is the sign test-martingale of `evaluator/statistics.py` (`sign_martingale_predictable_lambda/v1`, threshold 1/alpha, minimum blocks from A/A calibration); Magnitude's promotion test (`statistics.rs`, `Tally::verdict`) is a uniform-mixture sign test of the same family (sign null P(ahead) <= 1/2, Ville guarantee), so the statistic is not swapped and the dive's simulation (agent-computed, not source text) found comparable power. The one transferable item is a BUDGET rule: Magnitude admits a comparison session only the fewest rounds that could cross and ends it at the first non-ahead round (`tune.rs` L2123-L2128), dropping a challenger formally only when its behind-mixture crosses, and later sessions stay valid. Then replay recorded blocks with replacement (the method the ledger attributes to Magnitude's `replay.rs`, which is not among the dive's anchored claims) to compare arm ordering and an end-at-first-behind policy on evals-to-best and false-keep rate for the widened arm set. Dormant, not blocked.

## Dependencies and sequencing

| Task | Hard dependencies | Interacts with |
|---|---|---|
| AKX-ALL-1 | none | VB-AK-BELIEF (planner reader), VB-KVU-16B, VB-YARN-E1 |
| AKX-ALL-2/3 | none | INF-74 stage claims, RATIFY-AK-LANES-20261004 (peer claims) |
| AKX-ALL-4, -7 | none (in flight) | RTG-58 slot save/restore paths |
| AKX-ALL-5, -6 | AKX-ALL-4 | DS41-B14 |
| AKX-ALL-8 | AKX-ALL-4 | INF-70 be2-fa |
| AKX-ALL-9, -10 | none (in flight) | — |
| AKX-ALL-11 | AKX-ALL-9, -10 | `coherence_gate` (VB-COHGATE-1) |
| AKX-ALL-12 | AKX-ALL-4, -5, -20 | DS41-C9, INF-31 |
| AKX-ALL-13 | AKX-ALL-4, -6 | VB-KVQ-V10 |
| AKX-ALL-14, -16, -17 | none (in flight) | INF-75, v11 FA audit |
| AKX-ALL-15 | workspace-ec agreement | RTG-57 windows, INF-80/INF-59 window queue |
| AKX-ALL-18 | AKX-ALL-4, -15 | RTG-58, KVU-16b |
| AKX-ALL-19 | AKX-ALL-14, -15, -16 | INF-62 DF2-9 |
| AKX-ALL-21 | AKX-ALL-4, -6, -7, -9, -10, -17 | — |
| AKX-ALL-22 | AKX-ALL-14..18 | — |

## Effort summary (audit estimates, not measurements)

| Block | Estimate |
|---|---|
| CPU minimum (C1 + `cpu_fa_schedule` + C4) | ~4–5 agent-days |
| Full CPU (+ numerics, microbench, DS41 route) | ~9 agent-days |
| GPU (G1–G6) | ~8–10 agent-days |
| Loop time per Q38FN attention candidate or keep check | +20–30 min (≈10 launches at load + 1–2 min each) |
| One-off per target | ~2 h floor calibration; one prefill per anchor change (~10 min Q38FN, ~30 min DS41) |

## Key files

- **Loop** (epyc-inference-research `scripts/kernel_rnd/autokernel/`; line refs at `be23ac25f`, snapshot in
  `/mnt/raid0/llm/tmp/ak-longctx-audit-20261004/src/`): `loop/serving.py` (metric, `:1138-1157`),
  `heldout_serving.py:24-33`, `bench.py:93` (`SURFACES`), `census.py:58`, `cpu_profile.py:313,638`,
  `hotspots.py:144` (rocprofv3), `run.py:3706` (GPU profile unavailable) and `_q3_cpu_gpu_quiet_window`,
  `gates.py:1494` (fallback refusal), `actor_context.py:106-136`, `resolved_recipe.py:513`,
  `resource/device_claim.py`, `loop/claim.py`, `loop/test_q3_measurement_window.py`.
- **llama.cpp** (reference at the DS41 tree `/mnt/raid0/llm/llama.cpp-experimental-fastload-ds41-20260925` @
  `dd6c9cdbd`; edit only in AK worktrees): `ggml/src/ggml-cpu/ops.cpp:9241-9982` (FA), `src/llama-kv-cache*.cpp`,
  `src/llama-graph.cpp` `build_attn*`, `src/models/deepseek41.cpp:1095-1100`; GPU `ggml/src/ggml-cuda/fattn*.cu{,h}`,
  `convert.cu`.
- **Evidence**: the audit REPORT; Q38FN census `/mnt/raid0/llm/tmp/cpu-window2-20261004/step0_struct_falsifiers/REPORT.txt`;
  DS41 node profiles `/mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/store/node-profiles/`; production
  logs `/mnt/raid0/llm/epyc-orchestrator/logs/llama-server-{8074,8083,8070}.log`; v11 FA audit
  `artifacts/v11-fa-path-audit-20261004/`.

## Not filed here (explicit)

- **Upstream sparse-gather DSA kernels**: INF-31 owns the generic sparse-attention gates. This handoff only makes
  DS41's graph path authorable by AutoKernel.
- **Server-side prefix fork, cache-aware dispatch, `kv_rows`, cascade attention**: RTG-58. G4 reuses its slot
  regime but does not build its features.
- **`:8083` argv changes**: RTG-57 and the stack-change skill. AutoKernel measures candidates inside granted windows;
  it never changes the production stack.

## Reporting

Flip boxes here. The owning session (ak-ds41-main) updates INF-81's `Next action`; subagents report branch
boundaries to it, and workspace-ec reports G1 window grants on the bus. Append to `progress/YYYY-MM/`. On
completion, compile the long-context lesson ("a surface at 300 tokens is blind to the regime production spends
67–88% of decode wall in") into the wiki and the AutoKernel README, move this file to `completed/` and delete the row.
