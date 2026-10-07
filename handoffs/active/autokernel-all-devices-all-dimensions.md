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
