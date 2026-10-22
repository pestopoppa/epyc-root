# STACKCHG-GPUPIN-20261022: every thread of a pinned serving launch stays on its placement

**Status: PREPARED (phases 0-5). The operator signs next (phase 6).**
Nothing was applied to a real tree, nothing was pushed or merged, and no process was started, stopped,
reloaded or re-pinned. No production kernel tree or kernel-store file was touched; the change is
launcher-side only.

**Signing token (proposed):** `RATIFY-STACKCHG-GPUPIN-20261022`. There is no ratify script yet. The main
thread should author it from the stack-change template, as `ratify_stackchg_kvpool_20261003.sh` was
authored, pinning the two patch sha256 values listed in section 3. The operator runs it.

## 0. Intent

The operator wants deterministic pinning of GPU-server host threads in PRODUCTION, on every launch path,
for determinism and structure. This is independent of the result of the GPU-to-CPU noise experiment.

```yaml
# intent.yaml
change_id: STACKCHG-GPUPIN-20261022
retire: []
assign: {}
topology: {}          # NO declared placement changes; stack_topology.yaml / registry untouched
launcher:
  pinned_launch_env: {HSA_OVERRIDE_CPU_AFFINITY_DEBUG: "0"}   # every spawn whose prefix is `taskset -c`
  post_health: pin_all_tasks(OUR pid, prefix cpuset); refuse the launch if a task still escapes
  attestation: every task of every live stack pid inside its port's declared placement
```

## 1. The finding (verified 2026-10-22)

A HIP llama-server was started as `taskset -c 184-191 numactl --membind=3 llama-server ... -ngl all --device ROCm0`
(gpu build `kernels/builds/gpu-20261020-dd3d9721c`, ROCm 6.2.0). It had 196 tasks: 195 had
`Cpus_allowed_list: 184-191`, and ONE had `0-191`. That one is tid = pid+7, an early ROCr thread. The
process-level `/proc/<pid>/status` showed `184-191`, the main thread's mask, so a main-thread check could
not see the escape.

- Before the fix: `/mnt/raid0/llm/tmp/gpu-cpu-noise-20261021/diag-affinity-20261022.out`, produced by
  `diag-affinity-20261022.sh`.
- After a one-shot `taskset -a -p -c 184-191 <pid>` at health, 0 of 196 tasks were outside the lane:
  `diag-affinity-pin-20261022.out`.
- The live experiment timeline is `runs/20261022T170902Z/timeline.jsonl` in the same directory. Every
  `server_up` event shows `affinity_before_pin: ["0-191", "<lane>"]`, then `["<lane>"]`.
- The experiment-only fix is research commit `a1e94a002` in `/mnt/raid0/llm/worktrees/gpu-cpu-noise-run-20261021`.
- Live read-only observation (this package, 18:39:23Z): experiment server pid 3866145 was spawned at
  18:37:46Z and pinned once at 18:37:52Z. After it had served the experiment's clients it had **203
  tasks, all 203 on `136-143`**. Either no task was created after the pin, or every task created after
  it inherited the pin. The task count at pin time was not recorded, so the two cases cannot be told
  apart; see probe P1.

(These evidence files were not copied into `evidence/`. A filesystem-containment hook refused a copy
whose target path came from a shell variable, and per the brief the copy was not retried in another
form. The originals are under `/mnt/raid0/llm/tmp/gpu-cpu-noise-20261021/`.)

## 2. Mechanism: what was checked, and the choice

All evidence below is read-only.
- The full disassembly excerpt is in `evidence/rocr-affinity-disassembly.txt`. It sits in the root
  worktree and is **not committed**: the PII pre-commit hook reads objdump's 16-digit addresses as
  account numbers, and the hook was not bypassed.
- To regenerate it:
  `objdump -d --no-show-raw-insn --start-address=0x30131 --stop-address=0x30245 /opt/rocm/lib/libhsa-runtime64.so.1.14.60200`
  (thread creation), and the same command with `--start-address=0x91c3d --stop-address=0x91c9c`
  (knob parse).

**Q1. Why does one thread escape?** ROCr widens the thread on purpose.
- In the installed `libhsa-runtime64.so.1.14.60200`, `os::CreateThread` (around `0x30131`) tests a runtime flag byte.
- When the flag is set, it allocates a cpu_set for `get_nprocs_conf()` CPUs, sets every bit
  `0..n-1`, and calls `pthread_attr_setaffinity_np` before `pthread_create`.
- So every thread ROCr creates, at init or later, starts on all 192 CPUs, whatever mask the process
  was pinned with.

**Q2. Is there an env knob?** Yes: `HSA_OVERRIDE_CPU_AFFINITY_DEBUG`.
- Its string is in the library's flag table. Its parse site (`0x91c3d`-`0x91c98`) stores
  `flag = !(len == 1 && value[0] == '0')`, so the default is TRUE.
- With `=0`, ROCr does not set an affinity attribute, and Linux gives the new thread the creating
  thread's mask, i.e. the pin.
- The HIP runtime (`libamdhip64.so.6.2.60200`) has its own affinity code, but it is gated by
  `AMD_CPU_AFFINITY`, which is off in CLR by default. No other library in the server's maps imports
  an affinity setter: the production gpu-store `libggml-*.so` import none.
- **Not yet observed:** a server actually started with `=0`. See probe P1.

**Q3. Does a one-shot `taskset -a -p` after startup stay correct?** Only partly.
- It fixes every task that exists at that moment.
- A thread created later by ordinary `pthread_create` inherits its creator's mask. That covers the
  ggml/OpenMP threads, the HTTP worker threads, and the draft-model context. The live 203/203
  observation is consistent with this.
- A thread that ROCr creates later goes through `os::CreateThread` again and gets 0-191 again: a
  later HSA queue, signal, async-event or PC-sampling thread. This is why the env knob is the primary
  fix and the re-pin is the backstop.
- A thread that calls `sched_setaffinity` on itself can always widen its own mask. Only a cgroup
  cpuset prevents that.

**Q4. Is a cgroup-v2 cpuset available here?** Not determined.
- The server's `/proc/<pid>/cgroup` reads `0::/`, so it uses cgroup v2 and sits at the namespace root.
- The probe that would have shown whether `/sys/fs/cgroup` is writable and has the `cpuset`
  controller was refused by the filesystem-containment hook, because it ran `mount`, which the hook
  treats as privileged and operator-only. Per the brief it was not retried in another form.
- `systemd-run --scope -p AllowedCPUs=` needs a systemd user manager, and this container has none (no
  launcher in the tree uses one). A cpuset is therefore the kernel-enforced FALLBACK the operator can
  choose, not something to deploy now (decision D3).

**Recommendation: ONE mechanism in three layers**, in one shared helper per repo:

| layer | what | why |
|---|---|---|
| 1 cause | `apply_pinned_launch_env(env, prefix)`: a launch whose prefix is `taskset -c` gets `HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0`. It overrides an inherited value. Applied in the orchestrator stack and the serving gate; the AutoKernel loader is excluded (D2). | Fixes the source, including threads ROCr creates later. Inert for CPU binaries, which never load ROCr. |
| 2 backstop | After health, `enforce_launch_affinity(pid, prefix)` runs `pin_all_tasks`: it re-pins every task NOT inside the placement. A task already on a narrower sub-mask (an OpenMP place) is left alone, where `taskset -a` would widen it. It repeats until a pass is clean, then asserts that zero tasks escape. **A remaining escape fails the launch**, and the launcher kills its own pid. It acts only on a pid whose PPid is the launcher (prove OUR pid). | Catches anything layer 1 misses: another library, or a future ROCr that ignores the knob. |
| 3 detection | `affinity_attestation_warnings` runs in `orchestrator_stack.py status` and in `runtime_attestation_warnings`. It reads `/proc/<pid>/task/*/status` for the state-file pid and checks it against the port's declared cpuset (NUMA_CONFIG, the embedder placement, or the aux `cpuset`). `generate_attestation` no longer accepts a row because ONE task, or the main thread, matches: it now reports `task_cpu_escape` and the issue `cpu_affinity_escape:<mask>`. | A thread that later widens itself is REPORTED on every status read, with the remedy `launch_affinity.py --repin <pid> <cpus>`. |

Fallback, if P1 shows the knob does not hold on this ROCr: layers 2 and 3 alone still give a correct
placement at health plus detection afterwards. The kernel-enforced next step is a cgroup-v2 cpuset
(decision D3).

## 3. Patch set (unpushed branches; the main thread lands them)

| repo | branch | worktree | commit |
|---|---|---|---|
| epyc-orchestrator | `ws58/gpu-host-thread-pinning-20261022` | `/mnt/raid0/llm/worktrees/ws58-gpu-pin-orch-20261022` | `370ebd1c55fef53a532f3c983386082b76d73caf` (base origin/main `d0e0e477`) |
| epyc-inference-research | `ws58/gpu-host-thread-pinning-20261022` | `/mnt/raid0/llm/worktrees/ws58-gpu-pin-research-20261022` | `33268e5b43fc49b0ffa82acd4448ac3420112844` (base origin/main `ea3c98434`) |
| epyc-root (this package and the progress file only) | `ws58/gpu-host-thread-pinning-20261022` | `/mnt/raid0/llm/worktrees/ws58-gpu-pin-root-20261022` | this commit |

The patches are in `patches/*.patch` (`git format-patch` of each branch against origin/main) and their
sha256 values are in `patches/SHA256SUMS`.

**Orchestrator** (5 files plus 1 test):
- `scripts/server/launch_affinity.py` (new): parse/format, `prefix_cpuset`, `apply_pinned_launch_env`,
  `read_task_affinities`, `affinity_escapes`, `pin_all_tasks`, `parent_pid`, `enforce_launch_affinity`,
  `declared_cpuset_for_port`, `affinity_attestation_warnings`. The CLI has `--check` (read-only) and
  `--repin`.
- `scripts/server/orchestrator_stack.py`: the layer-1 env is applied before the launch banner in all six
  `start_server` llama-server branches (eval-batch, GPU shadow lane, vision, embedding, worker pool,
  registry-backed; the registry-backed branch is the one that launches `architect_critic` :8083) and in
  `start_aux_service`. `_post_health_affinity_gate` runs in all seven branches. The banner therefore
  records the knob in the launch env.
- `scripts/server/stack_commands.py`: `_affinity_attestation_warnings` runs in `cmd_status` and in
  `runtime_attestation_warnings`.
- `scripts/attest/generate_attestation.py`: the per-task containment check described in layer 3.
- `scripts/benchmark/serving_gate.py` (the deploy gate's own server): it applies the layer-1 env, runs
  the post-health `enforce_launch_affinity` (and fails on an escape), and re-checks after warm-up when it
  stops. The re-check is recorded per arm as `affinity_escapes_at_stop`.
- `tests/unit/test_launch_affinity.py`: 34 tests. They cover the /proc fixture with the exact finding,
  sub-mask preservation, a thread born mid-walk, ESRCH vs EPERM, the PPid guard, the CLI, the
  attestation row, all six branches with a pinned prefix, the failed-gate kill, the unpinned path left
  untouched, and the aux source order.

**Research** (the AutoKernel serving loader is the one code path that turns `artifacts/serving-recipes/*.json` into argv):
- `scripts/kernel_rnd/autokernel/loop/launch_affinity.py` (new): a trimmed twin of the orchestrator
  helper (the repos do not import each other), plus `pin_own_child`.
- `serving._measure_once`, **layer 2 only**:
  - after health and before any request, a pinned recipe runs `pin_own_child`, and a remaining escape
    raises `ServerDied`;
  - the result is recorded as `residency.affinity`;
  - `affinity.escapes_end` re-reads the masks after the measurement round (read-only).
- **Layer 1 (the env knob) is NOT in the AutoKernel loader.**
  - A first version added it as a loader-owned key in `Recipe.server_env` and broke about 173 AK tests.
    The loader env is identity-bearing: `resolved_recipe` (two allowlists), `unified_planner`,
    `production_enrollment`, `runtime_identity` and `legacy_targets` compare launch env minus
    `LD_LIBRARY_PATH` for equality.
  - That version was reverted inside this branch. Adding the knob there is an AK identity change; see D2.
- `test_launch_affinity.py`: 11 tests. They cover the finding fixture, the PPid guard, EPERM, a
  vanished pid, parsing, the unchanged loader env with the re-pin wired before the first request, and
  "every canonical GPU serving recipe pins".

**Tests.** All runs were file-scoped, in the foreground, at nice 19, using the repo venvs.
- Orchestrator: `test_launch_affinity.py`, `test_launch_env_every_branch.py`, `test_generate_attestation.py`,
  `test_stack_log_banner.py`, `test_embedding_placement.py`, `test_aux_service_env.py`,
  `test_diag_env_override.py`, `test_build_server_command_helpers.py`, `test_ufh12_arms.py` and
  `test_stack_numa_evict.py`: **316 passed**.
- Orchestrator files that reference `cmd_status` / `runtime_attestation_warnings`: **298 passed, 2
  failed**. Both failures are in `test_stack_change_pipeline.py`, they come from promotion-gate command
  code this change does not touch (`uv run pytest` shape vs `REPO_ROOT / target`), and both pre-exist.
- Research:
  - the 16 AK files the first version broke, plus `test_launch_affinity`, `hip_launch_proof`,
    `gpu_serving_profile`, `cpu_serving_recipe` and `legacy_cpu_serving`: **312 passed, 2 failed**;
  - the 2 failures are `test_serial_roster.py::test_shared_author_sandbox_*`, which fail identically on
    origin/main (a detached baseline worktree gave 2 failed / 271 passed on the same files);
  - earlier: `recipe_env`, `cpu_serving`, `legacy_cpu`, `hip_proof` and `gpu_serving_profile`: 96 passed.

## 4. Classification: stack-change, yes, ONE signature

- **Topology and lineup are unchanged**: no `stack_topology.yaml`, registry, manifest or derived file is
  edited. Phase 2 (transform) therefore has no DERIVATION surface, and phase 3 preflight
  (`stack_change_pipeline.py check`) has nothing to compile differently. Run it anyway at phase 7.
- It IS a serving change, which is why it needs the signature:
  1. it changes the launch env of every pinned production process (:8083 GPU, the CPU roles, the
     embedders, whisper and tts);
  2. it adds a new launch REFUSAL: a pinned launch whose tasks cannot be held inside the placement does
     not come up;
  3. it changes attestation semantics. A currently running server with an escaped thread will start
     reporting `cpu_affinity_escape` the moment the code lands, before any reload;
  4. it changes the AutoKernel GPU serving loader's launch condition.
- **Effect needs a relaunch.** The env applies only at spawn, so the change takes effect on the next
  reload of each pinned role. Until then, `status` reports the escape on any live GPU server.
  `launch_affinity.py --repin <pid> <cpus>` is the no-restart interim remedy.

### Operator decisions (each blocks only its own item)

- **D1. Launch-time refusal vs warn.** Recommend **refuse**: a declared placement that does not hold is
  not a served placement, and layers 1 and 2 make a residual escape a real defect. The alternative is a
  `[WARN]` line plus a status warning, with the launch kept up.
- **D2. AutoKernel loader env (layer 1 for AK).** As shipped, the AK loader gets layer 2 only.
  - This is correct at health: the re-pin happens before the first request.
  - `escapes_end` REPORTS any thread created later. It does not prevent one.
  - Every existing GPU floor was calibrated with one ROCr thread free on 0-191. After this change the
    re-pin moves that thread onto `cpu_list` before measuring, so this IS a measured-condition change
    for GPU serving floors.
  - **Recommend: (a) the AK owner re-checks one GPU A/A at the next GPU window. Then (b) adds the knob
    as a loader-owned key, threading it through the five identity sites listed above as one AK change.**
  - The alternative is to mark every GPU floor stale now and re-calibrate.
  - The thread is the ROCr async/event thread and is mostly idle, so no material shift is expected.
    That is a hypothesis, not a measurement.
- **D3. cgroup-v2 cpuset.** Adopt only if P1 fails or a self-widening thread is ever reported. It needs
  the cpuset-controller probe that was refused here.

## 5. Bring-up and verification plan (phases 7-8, after signature)

1. Land both branches (`ff-only`). Run `stack_change_pipeline.py check --run-promotion-gate`.
2. Reload the pinned roles through `orchestrator_stack.py reload <role>`, by the session that owns the
   inference, at its own boundary. Start with `architect_critic` (:8083), the GPU host lane.
3. For every pinned pid in the state file:
   - **every task** inside its declared cpuset:
     `scripts/server/launch_affinity.py --check <pid> <cpus>` exits 0;
   - **environ**: `HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0` is in `/proc/<pid>/environ`;
   - the launch log shows `[affinity] ... N tasks inside <cpus>`. `re-pinned 0` is the expected value
     if layer 1 works; a non-zero count means the knob did not cover something, so record it.
4. Serving proof per role, as in phase 8: argv[0] resolves into the kernel store, `/proc/<pid>/maps`
   shows `libggml-hip`, VRAM is non-zero during the run, there is a real completion with a real token
   budget, and `serving_gate.py` passes. The gate now records `affinity` and
   `affinity_escapes_at_stop`, and both must be clean.
5. **Post-warm-up re-check:** after the first real completion, AND after a request that exercises the
   DFlash2 draft, run `orchestrator_stack.py status`. It must show no `cpu_affinity_escape` line.
   `generate_attestation` must show `issue_count` with no `cpu_affinity_escape`.

## 6. Rollback

- `git revert` the orchestrator commit and the research commit. No data or derived file changes, and no
  symlink changes.
- Reload the same roles. Servers launched under the change keep their pinned threads until restarted,
  which is harmless.
- Interim, without a revert: re-pinning a live pid restores the placement in one step (`--repin`).

## 7. What could not be determined without starting a server: the one-minute probes

**P1 (does the knob hold, and do later threads inherit?).** About 60 s, a 0.5B model, inside a gpu-quiet
grant. This is `diag-affinity-20261022.sh` with two changes:

```bash
HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0 LD_LIBRARY_PATH=$B taskset -c 184-191 numactl --membind=3 \
  $B/llama-server -m $M --host 127.0.0.1 --port 18977 -t 8 -ngl all --device ROCm0 --no-webui -c 4096 &
P=$!; # wait for /health, then:
dump() { for t in /proc/$P/task/*; do echo "$(cat $t/comm) $(grep Cpus_allowed_list $t/status|cut -f2)"; done | sort | uniq -c; ls /proc/$P/task | wc -l; }
dump                                   # (a) at health: expect 0 tasks outside 184-191
curl -s localhost:18977/completion -d '{"prompt":"hi","n_predict":32}' >/dev/null
dump                                   # (b) after the first request: count may grow; still 0 outside
# then kill $P (own pid), verify dead
```

- Pass: (a) and (b) both show no `0-191` WITHOUT any `taskset -a`.
- If (a) fails: the knob does not hold on this ROCr. Layers 2 and 3 still apply; decide D3.
- If (b) shows new tasks that are all inside the lane: later threads inherit, which settles Q3 for this
  workload.

**P2 (speech services).** whisper and tts are HIP builds run with `HIP_VISIBLE_DEVICES=-1`. Read the
per-task masks of the live whisper/tts pids. Layer 3 does this on every `status`, so P2 needs no
launch: it is answered by the first `status` after landing.

## 8. Launch-path coverage

See section "Launch paths" in the progress entry for the full list of 27 paths.
- **Covered:** every production launch path, the serving gate, and the AutoKernel recipe loader.
- **Not changed** (one-off research and bench drivers): `gpu_serving_profile.py` (it inherits the env
  through `server_env` only when it launches through `Recipe`), `ab_server_pair.py` (its GPU arm is
  unpinned), `inf61_q38_np_depth_grid.py` (it already runs `taskset -apc`), `gpu_cpu_noise_driver.py`
  (it already re-pins with `a1e94a002`), the kpf/df2/occ1 drivers, and root `fillers/v11/v11_driver.py`.
- New research drivers should import the loop helper. Folding the rest is follow-up GPS-PIN-2.
