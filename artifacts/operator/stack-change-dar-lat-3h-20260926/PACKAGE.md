# Stack-change package: DAR-LAT-3h — reconcile the `:8074` critic's threads and env with its recipe (v2)

**Date**: 2026-09-27 (v2; v1 2026-09-26) · **Skill**: stack-change phases 0–5 (+ change-topology) · **Status**: READY FOR OPERATOR SIGNATURE
**Handoff**: `handoffs/active/decision-aware-routing.md`, task **DAR-LAT-3h**. It unblocks gate **DAR-LAT-3g**.
The split-off follow-up is **DAR-LAT-3i** (`GGML_FA_SPLIT_KV`).
**Rollback anchor**: the live configuration, recorded in `live-before-20260926.txt`.

**v2 (operator decision 2026-09-26, after the GGML_* env audit): the package is SPLIT.**
- The launcher env fix is **no longer in this package**. It lands on orchestrator main on its own as a quiet correction, with the
  recurrence guard (§5.4). The commit is `7c426412` on `lane/strip-preserve-v2-20260927`, a fast-forward of main
  `f58db8be`. **The main push was refused by a permission check (2026-09-27); main is NOT yet at 7c426412.**
  The v2 orchestrator lanes are built on 7c426412, so they carry it either way. P0 requires it on main before apply.
- `GGML_FA_SPLIT_KV=0` is **dropped** and becomes task DAR-LAT-3i.
- `GGML_FUSED_DECODE_OFF=1` rides along. It is inert under MTP, and G1 checks that premise.
- `GGML_NOHUGEPAGE_PROCESS=1` (the THP shim) is now **its own G1 factor**, judged independently of threads.
- Serving proof reads `THP_enabled` from `/proc/<pid>/status`.
- The v1 lanes (`lane/dar-lat-3h-20260926`, `-t96-`, `-live-`) are **superseded**. Do not merge them.

Nothing here has touched a real tree or the live stack. The separately approved env-fix landing reached its lane
only (see above). Live
reads were read-only: `/proc/<pid>/{cmdline,environ,status,task/*/status,numa_maps}`, `ss`, and `strings` on the v10
libraries. No process was started, stopped or signalled, and no inference request was sent.

---

## 0. Intent

```yaml
topology:
  architect_critic:     # :8074, Qwen3.8-Flash-Next UD-IQ4_XS, -np 1. Model, port, cpuset 0-95, interleave=all UNCHANGED.
    threads: decided by G1 -> 48 (NUMA_FULL_T48) or 96 (NUMA_FULL)
    env:
      GGML_FUSED_DECODE_OFF: "1"                        # every applying outcome; inert under MTP
      GGML_NOHUGEPAGE_PROCESS: decided by G1 (own factor)
      GGML_FA_SPLIT_KV: NOT SET                         # DAR-LAT-3i
text:
  - correct the "-t 48 is the served decode optimum" claim (recipe module + master registry)
```

## 1. What is live, and where each value comes from

Read from `/proc/2030855` (started 2026-09-24 18:47:34Z; `live-before-20260926.txt`):

| Fact | Live | Codified recipe / registry | Source of the live value |
|---|---|---|---|
| `-t` | **96** | **48** (`qwen38_flash_next_recipe.py` THREADS; registry `recipe.threads`, `recipe.cpu_shape: NUMA_FULL_T48`) | `stack_topology.yaml` names `cpu_shape: NUMA_FULL` = `("0-95", 96)`. `_resolve_thread_count` reads that tuple, and nothing reads the registry `recipe` block. The 2026-09-22 C3 ruling added the shape to the registry only; the orchestrator half never landed. |
| OMP team | 96 threads, each pinned to one CPU of 0-95; 194 other tasks float on 0-95 | `taskset -c 0-95 numactl --interleave=all`, spread/cores | canonical OMP env |
| GGML env | `GGML_IQK=1` only | the module's `CHAMPION_GGML_ENV` adds FUSED_DECODE_OFF, FA_SPLIT_KV, NOHUGEPAGE_PROCESS | Declared env blocks were dropped at launch from b060dd56 (2026-07-31) until the env-fix landing (§5.4). On main, no role declares any GGML knob beyond IQK. |
| `GGML_NUMA_REPACK_INTERLEAVE` | **absent** | removed in orch 30626243 | The same strip removed it at launch. **There was never a live drift to clear.** |
| `THP_enabled` (`/proc/<pid>/status`) | **1** | shim ON would read 0 | no shim |
| `-c` | 262144 | recipe measured at 8192 | Already ruled in lineup-change **C4** ("kept, and declared UNVALIDATED"). Not reopened. |

## 2. 48 or 96 — the evidence

**No served 48-vs-96 comparison exists for this model on any kernel.**

| # | Evidence | Numbers | Grade |
|---|---|---|---|
| E1 | D4/C5 (`handoffs/active/cpu-decode-roofline-program.md:141,384-389`), the one the recipe relies on | llama-bench, build 10196, pre-BIOS. tg128: t48 10.09 / t64 9.69 / t96 9.67. pp512: t48 172.6 / t96 147.2 | one window, no ABA, bare bench, no MTP |
| E2 | `progress/2026-08/2026-08-28.md:259` (UD-IQ4_XS) | tg: t48 13.46 / **t64 13.95** / t96 12.84 | t64 won there; never chased |
| E3 | post-BIOS 2026-09-21 (`results-c5postbios-20260921T100850Z`) | tg: t48 16.82 vs t64 15.96. pp: t48 203.3 vs **t64 216.1**. No t96 arm | INF-68 build |
| E4 | mechanism (`progress/2026-09/2026-09-21.md`) | barrier 1.9 µs (48T) vs 3.2 µs (96T). Post-BIOS bandwidth 410.4 vs **446.8 GB/s** | microbench |
| E5 | only served -t 96 on v10 (`docs/reference/speech/cpu-speech-contention-20260924.md:77-79`) | :8074 solo 31.1–31.3 tok/s | no served t48 arm beside it |
| E6 | champion served headline at -t 48 (`qwen38_flash_next_recipe.py:829`) | 43.281 MTP / 27.893 plain | pre-BIOS, different binary |

R23-64 (`handoffs/active/autokernel-rebuild-program.md:2254`) records the floor as having moved 2.76× since D4, and
says: "Do not assume 48 still wins". **The evidence is insufficient**, so a pre-registered gate decides.

**Shim evidence conflicts** (the env audit):
- For: CHAMP-2 measured the shim at +5.23% with lower launch sd.
- Against: v10's `common.cpp:78-88` records CHAMPION-3 at +1.48% with the shim OFF.
- Neither was measured on v10 at the served shape. G1 therefore judges the shim as its own factor, and adopts it
  only on a real gain.

**Frontdoor and the principle**:
- The critic's cpuset is 0-95 at either `-t`, so it holds all four CPU region locks while a request runs, and no
  locked CPU role is placed meanwhile. Frontdoor's cost of a consult is therefore the critic's **request wall time**,
  which is G1's primary metric.
- Unlocked co-tenants do share cores with the critic: speech, the GPU host lane (siblings of 88-95) and the embedder
  siblings. The matrix records `architect_critic × worker_vision` = 0.08 (block) at -t 96. G1's W3 probe reports the
  frontdoor cost under overlap, and G3 re-benches.
- The operator's principle (the strongest model is a consultant): at equal wall time, fewer threads spinning over
  shared cores wins. So **48 is adopted at parity**, which also completes the operator's own C3 ruling.

## 3. Outcomes

| G1 outcome | `-t` | critic GGML env | Orchestrator merge | Research merge | Reload |
|---|---|---|---|---|---|
| **T48** | 48 | FUSED_DECODE_OFF | `lane/dar-lat-3h-v2-t48-20260927` @ `379dca64` | `lane/dar-lat-3h-v2-20260927` @ `cbaeee2d` | architect_critic |
| **T48N** | 48 | FUSED + NOHUGEPAGE | `lane/dar-lat-3h-v2-20260927` @ `2e5e5544` | `lane/dar-lat-3h-v2-t48n-20260927` @ `af4f5675` | architect_critic |
| **T96** | 96 | FUSED_DECODE_OFF | `lane/dar-lat-3h-v2-20260927` through `ee21ed4e` | `lane/dar-lat-3h-v2-t96-20260927` @ `a969d2f9` | architect_critic |
| **T96N** | 96 | FUSED + NOHUGEPAGE | `lane/dar-lat-3h-v2-20260927` through `4a4bbd8f` | `lane/dar-lat-3h-v2-t96n-20260927` @ `48f7ebf6` | architect_critic |
| INVALID-PREMISE | — | — | nothing | nothing | none. FUSED_DECODE_OFF was not inert; report it |
| INCONCLUSIVE | — | — | nothing | nothing | none. Re-run G1 in another window |

## 4. Gates

### Measurement gates (pre-registered; thresholds signed with the package)

**G1 — threads × THP-shim launch ABA, before apply.** The driver is `scripts/server/critic_thread_gate.py`
(orch `565a7c15`).
- Arms: each is a fresh launch of the **live :8074 argv** on port 18074. Only `-t` and `--port` change, and
  `--slot-save-path` is dropped. The prefix is the same `numactl --interleave=all -- taskset -c 0-95`.

| Arm | `-t` | env beyond live |
|---|---|---|
| L | 96 | none (the incumbent, exactly) |
| T96 | 96 | FUSED_DECODE_OFF |
| T96N | 96 | FUSED_DECODE_OFF + NOHUGEPAGE_PROCESS |
| T48 | 48 | FUSED_DECODE_OFF |
| T48N | 48 | FUSED_DECODE_OFF + NOHUGEPAGE_PROCESS |

- **15 launches**, 3 per arm, in three blocks that each hold every arm once (unit = LAUNCH, about 2 h).
- Workloads:
  - W1: the 24-prompt production mix (`gate/prompts-24mix.json`: champion-harness shape, max_tokens 200, greedy,
    no prompt cache).
  - W2: a ~4k-token critique shape (max_tokens 400), reported as a second reading.
  - W3: a frontdoor :8070 probe, solo and during arm decode (reported, not gating).
- **Mechanism check**: `THP_enabled` from `/proc/<pid>/status` must be 0 on every N launch and 1 on every other. A
  mismatch makes the launch unclean, and it is re-queued. Any lineup port busy also makes the launch unclean and
  re-queued.
- **Rule (`decide`)**, where non-inferior means wall ≤ **1.03×**, TTFT ≤ **1.10×** and coherent ≥ ref − 1:
  1. **Premise**: T96 must be non-inferior to L, else **INVALID-PREMISE**.
  2. **Threads**: 48 iff T48 is non-inferior to T96 **and** T48N to T96N (parity at both shim levels); otherwise 96.
  3. **Shim**: adopted iff, at the chosen `-t`, TtN wall ≤ **0.98×** Tt (a real gain is required) and TtN is
     non-inferior to Tt on TTFT and coherence.
  4. Fewer than **3** clean launches in any arm gives **INCONCLUSIVE**.

**G2 — serving proof**, after reload (§6 P4–P5).

**G3 — contention recert**, T48/T48N only, in the same window. `-t` enters `topology_fingerprint`, which moves
4893e37e → 50f30ccc. Until the recert, `ContentionGate` **fails closed fleet-wide**. Pass: `contention_matrix.py run`,
then `check_contention_matrix_fresh.py` OK. If G3 fails, roll back (§7); the old hash returns and the old matrix is
fresh again.

### The three stack gates (memory `feedback_stack_change_three_gates`)
1. **`stack_change_pipeline` update/check**:
   - Each orchestrator outcome head carries derived artifacts regenerated against its paired research branch
     (`pipeline-update-v2-{O3,T96N,T48N}.txt`): lean, guard / guard_strict / stack_manifest_registry / q_scorer_priors ok.
   - `runtime_attestation` fails in a lane only, because a lane has no state file. The new
     `declared_env_attestation` step reads COULD-NOT-CHECK in a lane, and ok on the live stack.
   - Phase 7 re-runs `update` against merged research main.
2. **Start-time `validate_or_raise`**: runs at reload.
3. **`runtime_attestation` + `declared_env_attestation` vs live, after reload**: both must be ok. The second now proves
   the declared GGML env actually reached `/proc/<pid>/environ`, which is the check that was missing for eight
   weeks.

Tests (pinned `taskset -c 72-79 nice -n 10`):
- Targeted stack/env/launch/numa/topology/critic/template/pipeline suites: T96 and T96N heads 1,846 passed; T48
  and T48N heads 1,846 passed, 1 failed.
- The landing commit's full `tests/unit`: 15,468 passed, 0 failed.
- The one failure is `test_real_matrix_against_live_numa_config`, which is exactly G3.

## 5. Patch set (lane branches, pushed, not applied)

| # | Patch | Repo · branch · commit | Content | Outcomes |
|---|---|---|---|---|
| O1 | `patches/orchestrator/0001-*` | epyc-orchestrator · `lane/dar-lat-3h-v2-20260927` · `f98d210b` | `NUMA_FULL_T48` shape + split thread invariant. **Inert** | all applying |
| O2 | `0002-*` | same · `565a7c15` | G1 driver v2 (5 arms, rule, THP readback) + 14 tests. **Inert** | all applying |
| O3 | `0003-*` | same · `ee21ed4e` | critic `stack_env` = FUSED_DECODE_OFF; recipe-env parity test, both directions (`env_not_serving` must not leak); critic in `DELIBERATE_GGML_BLOCKS`; derived regenerated | all applying |
| O4 | `0004-*` | same · `4a4bbd8f` | + NOHUGEPAGE_PROCESS; derived regenerated vs T96N | T96N, T48N |
| O5 | `0005-*` | same · `2e5e5544` | topology `NUMA_FULL_T48`, template, shape↔recipe parity test; derived regenerated vs T48N | T48N |
| O5′ | `patches/orchestrator-t48/0004-*` | `lane/dar-lat-3h-v2-t48-20260927` · `379dca64` | O5 on top of O3 (no shim) | T48 |
| R1 | `patches/research/0001-*` | epyc-inference-research · `lane/dar-lat-3h-v2-20260927` · `cbaeee2d` | corrects the claim; `recipe.env` = FUSED; `recipe.env_not_serving` = {NOHUGEPAGE (G1), FA_SPLIT_KV (3i)} | T48 as-is; base of the rest |
| R2 | `patches/research-t48n/*` | `…-v2-t48n-20260927` · `af4f5675` | + NOHUGEPAGE in `env` | T48N |
| R3 | `patches/research-t96/*` | `…-v2-t96-20260927` · `a969d2f9` | threads 96, `NUMA_FULL` | T96 |
| R4 | `patches/research-t96n/*` | `…-v2-t96n-20260927` · `48f7ebf6` | both | T96N |

### 5.4 Landing separately (NOT in this package): the launcher env fix + recurrence guard, `7c426412` (pending main fast-forward)

- **Root cause.** b060dd56 (2026-07-31) gave every role a `binary_dir`. The compiler labels a backend-derived
  `binary_dir` `env_policy: canonical` precisely so that it does not change env policy. The launcher, however, keyed
  its GGML strip on `binary_dir` presence, so it stripped every role's declared block on every launch.
- **Fix.** One strip rule (`stack_env.strip_ambient_ggml`) now applies to every branch:
  - Declared keys are kept; ambient `GGML_*` is dropped.
  - The strip no longer keys on the override.
  - `preserve` is passed on the registry-backed, vision, gpu_shadow_lane and worker_pool branches.
  - The embedding, eval-batch and aux-service branches now strip too.
- **Behaviour-neutral on main.** No role declares a GGML knob beyond IQK, and no live process carries ambient GGML.
- **Guard.**
  - `test_launch_env_every_branch.py` drives every branch through `start_server` / `_build_aux_env` and reads the env
    handed to Popen. All 11 cases fail on the pre-fix tree.
  - `declared_env_attestation` in `stack_change_pipeline` compares live `/proc/<pid>/environ` with the declared env.
    Live run: **ok, 17 compared, 0 errors** (`env-attestation-live.txt`). Its negative control, re-declaring
    NUMA_REPACK in memory, FAILS on :8074 (`env-attestation-live-negctl.txt`).

### Surfaces (DERIVATION.md)
| Surface | Touched | Why |
|---|---|---|
| research master registry | R1–R4 | recipe block text, serving env, fallback values |
| `stack_topology.yaml` | O5/O5′ | the one value that sets `-t` |
| `stack_numa.py` | O1 | the shape must exist in `_CPU_SHAPES`, `_SHAPE_CLASSES` and the invariant together |
| `stack_env.py` | O3/O4 | the critic's declared env |
| `stack_templates/default.yaml` | O5/O5′ | restates the topology (parity test) |
| `launch_manifest.yaml`, `src/config/models.py`, `src/roles.py`, kernel store | no | port, tier, roles and binary unchanged |
| derived artifacts | regenerated by `update`, never hand-edited | a lane head is self-consistent; phase 7 regenerates against research main |
| human-only paths | **none** | no §5 receipt required; `check_ratification_receipts.py` exits 0 |

## 6. Bring-up (phases 7–8), by the session that owns the inference, after the receipt exists

- **P0 preconditions**, checked from region holders and captured PIDs, never name patterns:
  - The receipt exists.
  - Orchestrator main contains `7c426412`, the env fix and recurrence guard (`git merge-base --is-ancestor`).
  - A bus-granted whole-host quiet window (INVARIANTS #8; MEAS-6 forbids a concurrent GPU chain). AutoPilot is
    quiesced by its owner. No bench, AutoKernel CPU arm or GPU loop is running.
  - `:8074 /slots` shows `is_processing: false`, and admission shows `in_flight == 0` for architect_critic. Nothing
    is routed to the critic mid-decode; hold consult callers for the window (the `reasoning` chain is
    `explicit_request` only).
- **P1 G1**: `scripts/region-lock run --cpu-list 0-191 -- .venv/bin/python scripts/server/critic_thread_gate.py run
  --live-pid <:8074 pid> --prompts <this dir>/gate/prompts-24mix.json --out
  /mnt/raid0/llm/epyc-inference-research/data/dar-lat-3h-gate-<UTC>`, then `summarize`. Run it from an orchestrator
  worktree at `565a7c15` or later. `verdict.json` names the outcome.
- **P2 apply the outcome's pair (§3)**:
  1. Merge in a detach worktree on `origin/main` and push with the push lock.
  2. `git pull --ff-only` both shared clones.
  3. `stack_change_pipeline.py update --numa-mode both`, then `check`.
- **P3**: `orchestrator_stack.py reload architect_critic`, and **only** that. Do not stop AutoPilot.
- **P4 serving proof, from `/proc`, not config**:
  - argv[0] is in `kernels/builds/cpu-20260921-ffc1bac82`, and argv has `-t 48` or `-t 96` per the outcome.
  - environ has `GGML_FUSED_DECODE_OFF=1`, and `GGML_NOHUGEPAGE_PROCESS=1` iff the outcome ends in N. It has **no**
    `GGML_FA_SPLIT_KV`.
  - **`THP_enabled` in `/proc/<pid>/status` is 0 iff N, else 1.**
  - Per-task `Cpus_allowed_list` shows exactly 48 (or 96) single-CPU tasks on distinct CPUs inside 0-95; every other
    task is on 0-95.
  - `numa_maps` pages are spread roughly evenly over N0–N3.
  - `/health` ok, and `check` shows `runtime_attestation: ok` **and** `declared_env_attestation: ok`.
- **P5 coherence at production prompt length**: one :8074 completion with the W2 critique prompt (~4k tokens),
  `max_tokens` 1024, thinking off. The content must be non-empty and coherent, with `timings.draft_n_accepted > 0`.
- **P6 G3** (T48/T48N): `contention_matrix.py run`, then `check_contention_matrix_fresh.py` OK.
- **P7**: re-check the 3g "live argv/env = registered recipe" item, then close 3h. The 3a prior table freezes the
  new `topology_hash`.

## 7. Rollback

1. On orchestrator main, `git revert` the merged O5/O5′, O4 and O3, newest first. O1 and O2 are inert and may stay.
   The env fix `7c426412` stays; it is independent and neutral.
2. On research main, revert the merged outcome commit, then R1 if the operator wants the recipe wording back.
3. `update`, then `reload architect_critic`.
4. Verify with P4 (`-t 96`, `GGML_IQK` only, `THP_enabled` 1). The hash returns to 4893e37e, so the old matrix is
   fresh again.

Triggers: P4 or P5 fails; G3 cannot certify in the window; either attestation stays red after the reload.

## 8. Needs-operator

- **N-1** Sign the G1 rule and thresholds: 1.03 wall, 1.10 TTFT, 0.98 shim gain, coherence −1, ≥ 3 clean launches
  per arm.
- **N-2** Grant the window: G1 (~2 h), the reload and G3.
- Not decided here:
  - `GGML_FA_SPLIT_KV` → DAR-LAT-3i.
  - `n_ctx` → C4 stands.
  - Speech co-tenancy → the operator's 2026-09-24 "no change" stands.

## 9. Findings outside the diff

- The orchestrator pre-commit contention hook scopes on `stack_numa|stack_manifest|contention*|model_registry`, not
  `orchestration/stack_topology.yaml`. It also runs the shared clone's checker, so O5 committed green while moving the
  topology hash. The fix belongs to the owner of epyc-root `scripts/hooks/install_git_hooks.sh`.
- The served-quality record (master registry ~L3289) was taken at -t 96 with the canonical env. DAR-LAT-3's quality
  arm covers any change.
