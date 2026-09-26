# Stack-change package: DAR-LAT-3h — reconcile the `:8074` critic's threads and env with its recipe

**Date**: 2026-09-26 · **Skill**: stack-change phases 0–5 (+ change-topology) · **Status**: READY FOR OPERATOR SIGNATURE
**Handoff**: `handoffs/active/decision-aware-routing.md`, task **DAR-LAT-3h**. It unblocks gate **DAR-LAT-3g**.
**Rollback anchor**: the live configuration, recorded in `live-before-20260926.txt`.

Nothing here has touched a real tree or the live stack. All edits are on lane branches. Live reads were read-only
(`/proc/<pid>/{cmdline,environ,status,task/*/status,numa_maps}`, `ss`, `strings` on the v10 libraries). No process was
started, stopped or signalled, and no inference request was sent.

---

## 0. Intent

```yaml
topology:
  architect_critic:     # :8074, Qwen3.8-Flash-Next UD-IQ4_XS, -np 1. Model, port, cpuset 0-95, interleave=all UNCHANGED.
    threads: decided by gate G1 -> 48 (NUMA_FULL_T48) or 96 (NUMA_FULL)
    env:     decided by gate G1 -> the recipe's GGML knobs, or the canonical env only
text:
  - correct the "-t 48 is the served decode optimum" claim (recipe module + master registry)
bug_fix:
  - launcher: the kernel-store binary-override strip drops every role's declared GGML_* env
```

## 1. What is live, and where each value comes from

Read from `/proc/2030855` (started 2026-09-24 18:47:34Z; `live-before-20260926.txt`):

| Fact | Live | Codified recipe / registry | Source of the live value |
|---|---|---|---|
| `-t` | **96** | **48** (`qwen38_flash_next_recipe.py` THREADS; registry `recipe.threads`, `recipe.cpu_shape: NUMA_FULL_T48`) | `stack_topology.yaml` names `cpu_shape: NUMA_FULL`, which is `("0-95", 96)` in `stack_numa.py`. `orchestrator_stack._resolve_thread_count` reads that tuple. Nothing reads the registry `recipe` block. `stack_templates/default.yaml:155 threads: 96` is **not** read by the launcher (DS-7 template tooling only), but its parity test pins it to the topology. |
| OMP team | 96 threads, each pinned to one CPU of 0-95. The other 194 tasks float on 0-95 | recipe: `taskset -c 0-95 numactl --interleave=all`, spread/cores | canonical OMP env |
| GGML env | `GGML_IQK=1` only | `+ GGML_NOHUGEPAGE_PROCESS=1, GGML_FA_SPLIT_KV=0, GGML_FUSED_DECODE_OFF=1` (module `CHAMPION_GGML_ENV`; the registry `recipe.env` listed two of them) | **Launcher defect (§5.4)**: the binary-override strip removes every declared GGML knob. All three knobs are compiled into v10 (`strings`: 6/3/3 hits). |
| `GGML_NUMA_REPACK_INTERLEAVE` | **absent** | removed from `stack_env` in orch 30626243 | The same strip removed it at launch. **The "stale NUMA_REPACK drift" the dispatch describes does not exist.** The process launched while the block still declared the knob, and the knob never reached it. |
| `-c` | 262144 | recipe measured at 8192 | Already ruled: lineup-change **C4**, "kept, and declared UNVALIDATED". Not reopened here. For 3g, the registered serving value is `serving_shape.n_ctx` 262144. `recipe.measured_at_context` is a measurement fact, not a serving directive. |

## 2. 48 or 96 — the evidence

**No served 48-vs-96 comparison exists for this model on any kernel.** The recipe's "NOT 96: the served decode
optimum" is stronger than its record:

| # | Evidence | Numbers | Grade |
|---|---|---|---|
| E1 | D4/C5 sweep, the one the recipe relies on (`handoffs/active/cpu-decode-roofline-program.md:141,384-389`; raw `/mnt/raid0/llm/tmp/inf70/results-c5v2-20260902T103808Z/bench-c5-omp-on.log`) | llama-bench, build 10196, uniform IQ4_XS, pre-BIOS. tg128: t48 **10.09** / t64 9.69 / t96 **9.67**. pp512: t48 **172.6** / t96 **147.2** | one window, no ABA, bare bench, no MTP |
| E2 | `progress/2026-08/2026-08-28.md:259`, UD-IQ4_XS | tg: t48 13.46 / **t64 13.95** / t96 12.84 | t64 won there. Never chased |
| E3 | Post-BIOS bench, 2026-09-21 (`results-c5postbios-20260921T100850Z`) | tg: t48 16.82 vs t64 15.96. pp: t48 203.3 vs **t64 216.1**. No t96 arm | INF-68 build |
| E4 | Mechanism (`progress/2026-09/2026-09-21.md`) | barrier 1.9 µs at 48T vs 3.2 µs at 96T. Post-BIOS read bandwidth 410.4 vs **446.8 GB/s** | microbench |
| E5 | Only served -t 96 on v10 (`docs/reference/speech/cpu-speech-contention-20260924.md:77-79`) | :8074 solo **31.1–31.3 tok/s**. `-t 56` on 40-95 gave 23.0/24.5 | no served t48 arm beside it |
| E6 | Champion served headline at -t 48 (`qwen38_flash_next_recipe.py:829`) | 43.281 MTP / 27.893 plain tok/s | pre-BIOS, different binary. Not comparable to E5 |

R23-64 (`handoffs/active/autokernel-rebuild-program.md:2254`) states the same thing: the floor has moved 2.76× since
D4, the one term that scales with threads is a larger share of each token, and "Do not assume 48 still wins." The
BIOS change it waited on has happened. Post-BIOS, bandwidth favours 96 slightly (E4) and prefill favours 64 over 48
(E3), so the direction is open.

**Verdict: the evidence is insufficient.** The package therefore carries a measurement gate, G1, and a pre-registered
rule instead of a choice.

### What 48 vs 96 means for frontdoor and for the principle

- The critic's cpuset is 0-95 at either thread count, so it holds **all four CPU region locks** while any request runs.
  No CPU role (frontdoor full or halves) is placed while it decodes. 48 threads free no cores for a locked role.
  **Frontdoor's cost of a consult is the critic's request wall time**, so G1's primary metric is wall time.
- Unlocked co-tenants do share cores with it: speech on 0-39, the GPU host lane 184-191 (the siblings of 88-95), and
  the embedder pool on siblings. The matrix's measured `architect_critic × worker_vision` ratio at -t 96 is **0.08
  (block)**. G1's W3 probe measures frontdoor decode while the critic decodes, as the bypass case, and G3 re-benches
  the pairs.
- **The operator's principle** (the strongest model is a consultant; smaller models do the grunt work): a consult
  should hold the machine as briefly as possible and spin as few threads as possible over the cores others use.
  At equal wall time, 48 wins on the second count. Hence the rule: **R48 is adopted at parity** (within 3% wall time).
  It is also the value the operator already ruled in C3 ("Add the needed cpu shape... should use it properly"), so a
  parity result completes signed work rather than reopening it.

## 3. The three candidate states

| Outcome | `-t` | GGML env | Orchestrator lane merged through | Research branch merged | Reload |
|---|---|---|---|---|---|
| **R48** (recommended if G1 allows) | 48 (`NUMA_FULL_T48`) | recipe | `20c7d902` | `lane/dar-lat-3h-20260926` `cf2476b0` | architect_critic |
| **R96** | 96 (`NUMA_FULL`) | recipe | `071d8ff9` | `lane/dar-lat-3h-t96-20260926` `2a4613f7` | architect_critic |
| **L** | 96 | canonical only | `27008a15` (O1–O3: inert + the bug fix, which changes no live env) | `lane/dar-lat-3h-live-20260926` `cc8dd98e` | **none** (no launch change) |
| INCONCLUSIVE | — | — | nothing | nothing | none; re-run G1 in another window |

The orchestrator lane is linear, so each outcome merges a prefix. The research fallbacks branch from `cf2476b0`.

## 4. Gates

### Measurement gates (pre-registered; the thresholds are signed with the package)

| Gate | When | What | PASS / decision | ROLLBACK |
|---|---|---|---|---|
| **G1 thread × env ABA** | after signature, **before** apply | `scripts/server/critic_thread_gate.py run`: arms L / R96 / R48, each a fresh launch of the **live :8074 argv** on port 18074 (only `-t`/`--port` changed, `--slot-save-path` dropped), same `numactl --interleave=all -- taskset -c 0-95` prefix. 12 launches in balanced blocks (4 per arm, unit = LAUNCH). W1 = the 24-prompt production mix (`gate/prompts-24mix.json`, the champion harness shape, max_tokens 200, greedy, no prompt cache). W2 = critique shape, ~4k-token prompt, max_tokens 400. W3 = frontdoor :8070 probe solo and while the arm decodes (reported, not gating). A launch with any lineup port busy is discarded and re-queued | `decide()`: **R48** if its mean per-launch median W1 wall time ≤ **1.03×** both R96 and L, TTFT ≤ **1.10×**, and coherent count ≥ ref − 1. Else **R96** if the same holds vs L. Else **L**. Fewer than 3 clean launches per arm → INCONCLUSIVE. W2 is reported under the same rule as a second reading | — |
| **G2 serving proof** | after reload | §6 P4–P5 | all hold | any fails → §7 |
| **G3 contention recert** (R48 only) | same window, right after G2 | `scripts/server/contention_matrix.py run`. `-t` is in `topology_fingerprint`, so the hash moves 4893e37e → **50f30ccc**. Until recert, `ContentionGate` **fails closed fleet-wide** (background QUEUE, foreground DEGRADED_ALLOW) | `check_contention_matrix_fresh.py` OK; `test_real_matrix_against_live_numa_config` passes | recert fails → §7 (the rollback restores hash 4893e37e, and the old matrix is fresh again) |

### The three stack gates (memory `feedback_stack_change_three_gates`)

| Stack gate | Status in scratch (per outcome) | After apply |
|---|---|---|
| 1. `stack_change_pipeline.py update` / `check` | **R48, R96, L all compile.** lean ok, descriptors/priors/enums/summary updated, guard / guard_strict / stack_manifest_registry / q_scorer_priors **ok** (`pipeline-update-{R48,R96,L}.txt`). Baseline `origin/main` already has stale descriptors (`pipeline-check-baseline.txt`). `runtime_attestation` fails in scratch only because a lane has no `orchestrator_state.json` (every live port reads as unmanaged; same as UFH-12) | re-run `update` then `check` in the real tree |
| 2. start-time `validate_or_raise` | **ok** for all three lean registries | runs at reload |
| 3. `runtime_attestation` vs live | expected drift until the reload | `check` after the reload must show `runtime_attestation: ok` for :8074 |

Tests: the full orchestrator unit suite on the R48 candidate after `update` gives **15,347 passed, 1 failed**
(`unit-R48-summary.txt`). Baseline `origin/main` gives 15,327 passed, 0 failed (`unit-base-summary.txt`). The one
failure is `test_real_matrix_against_live_numa_config` (the matrix hash 4893e37e vs the candidate's 50f30ccc), which is
exactly G3. The new parity, strip and gate tests pass on each outcome's head. `topology_check.py`: PASS (5 roles,
7 instances, 9 shapes).

## 5. Patch set (committed on lane branches, pushed, not applied)

| # | Patch | Repo · branch · commit | Content | Outcomes |
|---|---|---|---|---|
| O1 | `patches/orchestrator/0001-*` | epyc-orchestrator · `lane/dar-lat-3h-20260926` · `c43d10fb` | `stack_numa.py`: `NUMA_FULL_T48 = ("0-95", 48)` in `_CPU_SHAPES` + `_SHAPE_CLASSES` (class `full`); `_UNDERSUBSCRIBED_SHAPES`; the invariant split (`>` fatal for every shape, `<` fatal unless registered). Tests incl. both negatives. **Inert** | all |
| O2 | `0002-*` | same · `aa2c2c2a` | `scripts/server/critic_thread_gate.py` (G1 driver) + 11 tests. **Inert** | all |
| O3 | `0003-*` | same · `27008a15` | **Bug fix, §5.4**: the binary-override strip keeps the role's declared knobs. It changes no live env on its own | all |
| O4 | `0004-*` | same · `071d8ff9` | `stack_env._ROLE_ENV_BLOCKS["architect_critic"]` = the three recipe knobs; a recipe-env parity test that composes the env as `start_server` does | R96, R48 |
| O5 | `0005-*` | same · `20c7d902` | `stack_topology.yaml` critic → `NUMA_FULL_T48`; `default.yaml` `numa FULL_T48, threads 48, ram_gb 69→90` (69 was the 122B), stale 122B header text; shape↔recipe parity test | R48 |
| R1 | `patches/research/0001-*` | epyc-inference-research · `lane/dar-lat-3h-20260926` · `cf2476b0` | recipe module + registry: correct the "served optimum" claim; `recipe.env += GGML_FUSED_DECODE_OFF` (module parity) | R48 (and the base of both fallbacks) |
| R2 | `patches/research-fallback-R96/0002-*` | `lane/dar-lat-3h-t96-20260926` · `2a4613f7` | `recipe.threads 96`, `cpu_shape NUMA_FULL` | R96 |
| R3 | `patches/research-fallback-L/0002-*` | `lane/dar-lat-3h-live-20260926` · `cc8dd98e` | as R2, and `recipe.env` → `champion_measurement_env` (not a serving env) | L |

### 5.4 The launcher defect (found while tracing the env; fixed in O4)

`orchestrator_stack._apply_runtime_requirements_env` strips every `GGML_*` key except `GGML_IQK` whenever a binary
override is set. Since v10 every role's compiled prior carries `binary_dir` (the kernel store), so
`_stack_prior_runtime_overrides` always returns an override. The compiler labels these roles `env_policy: canonical`,
which the launcher never reads. Result: **every declared per-role GGML knob is silently dropped**. The live :8074
environ proves it. Without O3, O4 would have shipped inert. O3 preserves the role's own declared keys and still strips
ambient `GGML_*`. Only architect_critic has knobs beyond `GGML_IQK`, so no other role's env changes (tested).

### Surfaces (DERIVATION.md source list)
| Surface | Touched | Why |
|---|---|---|
| research `model_registry.yaml` (master) | yes (R1/R2/R3) | recipe block text, env parity, fallback values |
| `stack_topology.yaml` | O5 | the one value that sets `-t` |
| `stack_numa.py` | O1 | the new shape must exist in `_CPU_SHAPES`, `_SHAPE_CLASSES` and the invariant together |
| `launch_manifest.yaml` | no | port, tier and `role_launch_meta` unchanged |
| `src/config/models.py`, `src/roles.py` | no | no role or alias change |
| `stack_templates/default.yaml` | O5 | restates the topology; `test_default_template_topology_parity` fails otherwise |
| `stack_env.py`, `orchestrator_stack.py` | O4, O3 | env is not in scratch.sh's source list, which is the same gap UFH-12 found for launcher features |
| kernel store symlink | no | `production/cpu → builds/cpu-20260921-ffc1bac82/bin` |
| derived artifacts | **never hand-edited** | `PREVIEW-derived-after-update-R48.diff`: only hashes, `repo_commit`, `compiled_at` and one lean line (`GGML_FUSED_DECODE_OFF`). Do not apply it; phase 7 regenerates it |
| human-only paths | **none** | no `MEASUREMENT.md`, protocol annex, era row or AutoPilot baseline is touched, so no §5 receipt is required. The ratify script writes only its own receipt, and `check_ratification_receipts.py` stays at exit 0 |

## 6. Bring-up (phases 7–8), by the session that owns the inference, after the receipt exists

- **P0 preconditions**, checked from region holders and captured PIDs, never name patterns:
  - The receipt exists.
  - A bus-granted whole-host quiet window (INVARIANTS #8; MEAS-6 forbids a concurrent GPU chain). AutoPilot is
    quiesced by its owner. No llama-bench, AutoKernel CPU arm or GPU loop is running.
  - `:8074 /slots` shows `is_processing: false`, and the admission ledger shows `in_flight == 0` for architect_critic.
    Nothing is routed to the critic mid-decode. The `reasoning` chain is `explicit_request` only, so hold consult
    callers for the window.
- **P1 G1**: `scripts/region-lock run --cpu-list 0-191 -- .venv/bin/python scripts/server/critic_thread_gate.py run
  --live-pid <:8074 pid> --prompts <this dir>/gate/prompts-24mix.json --out
  /mnt/raid0/llm/epyc-inference-research/data/dar-lat-3h-gate-<UTC>`, then `summarize`. About 90 min. Run it from an
  orchestrator lane worktree at `aa2c2c2a` or later. `verdict.json` names the outcome.
- **P2 apply the outcome's prefix (§3)**:
  1. Merge in a detach worktree on `origin/main`.
  2. Push with the push lock.
  3. `git pull --ff-only` in both shared clones. The launcher runs from `/mnt/raid0/llm/epyc-orchestrator`.
  4. `stack_change_pipeline.py update --numa-mode both`.
  5. `check`, which is expected to show only :8074 runtime drift.
- **P3 reload architect_critic ONLY**: `orchestrator_stack.py reload architect_critic`. Never the stack. Do not stop
  AutoPilot. Outcome L: no reload.
- **P4 serving proof, from `/proc`, not config**:
  - argv[0] resolves into `kernels/builds/cpu-20260921-ffc1bac82`, and argv has `-t 48` (R48) or `-t 96`.
  - environ holds the three knobs (R48/R96).
  - Per-task `Cpus_allowed_list` shows exactly 48 (or 96) single-CPU tasks, on distinct CPUs, all inside 0-95. Every
    other task is on 0-95.
  - `numa_maps` pages are spread roughly evenly over N0–N3.
  - `/health` ok, and `stack_change_pipeline.py check` → `runtime_attestation: ok`.
- **P5 coherence at production prompt length**: one completion on :8074 with the W2 critique prompt (~4k tokens),
  `max_tokens` 1024, thinking off. The content must be non-empty and coherent, and `timings.draft_n_accepted > 0`,
  which shows MTP is live.
- **P6 G3** (R48): `contention_matrix.py run` in the same window, then `check_contention_matrix_fresh.py` → OK.
- **P7**: re-check DAR-LAT-3g's "live argv/env = registered recipe", then close 3h. The DAR-LAT-3a prior table
  freezes the NEW `topology_hash`.

## 7. Rollback (to the live configuration L)

1. On orchestrator main, `git revert` whichever of `20c7d902 071d8ff9` were merged, newest first. O1–O3 stay: they
   are inert or a bug fix. On research main, merge `lane/dar-lat-3h-live-20260926`; after R96, revert `2a4613f7`
   first.
2. `update`, then `reload architect_critic`.
3. The topology hash returns to 4893e37e, and the 2026-09-24 matrix is fresh again, with no re-bench.
4. Verify with P4 (`-t 96`, canonical env).

Rollback triggers: P4 or P5 fails; G3 cannot certify in the window; or `runtime_attestation` stays red after reload.

## 8. Needs-operator

- **N-1** Sign the G1 rule and thresholds (§4: 3% wall, 10% TTFT, coherence −1, ≥3 clean launches per arm). A
  changed threshold means re-preparation, because the driver pins them.
- **N-2** Grant the window: G1 (~90 min) + reload + G3 in one whole-host quiet window.
- Not decided here: `n_ctx` (C4 stands), and the speech co-tenancy (operator chose no change on 2026-09-24).

## 9. Findings outside the diff

- The contention pre-commit hook (`.git/hooks/pre-commit.extras` in the orchestrator clone) scopes on
  `stack_numa|stack_manifest|contention*|model_registry`, **not `orchestration/stack_topology.yaml`**, the main
  invalidator since 2026-08-01. It also runs the shared clone's copy of the checker, not the committing worktree's.
  O5 changed the topology hash and committed green. The hook file is untracked in the orchestrator repo, so the fix
  belongs to whoever owns the hook installer (epyc-root `scripts/hooks/install_git_hooks.sh`).
- The served-quality record at master registry ~L3289 was taken at `-t 96` with the canonical env. After R48/R96 the
  served configuration differs (threads, and numerics via `GGML_FA_SPLIT_KV`/`FUSED_DECODE_OFF`). DAR-LAT-3's
  quality non-inferiority arm covers it. It is not re-derived here.
