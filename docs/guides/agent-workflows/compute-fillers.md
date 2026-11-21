# Compute Fillers

Inference rows run on the shared host only inside a **grant** the keeper writes. This page is the launcher-side
contract: how a row is published, smoked, granted, run and ended, and the job-side rules bought by incidents.

- **Flow** (publish → smoke → grant → run → file): `backlog-churn-flow.md` → *The row flow* and *The allocator*.
- **Packing** (bins, shapes, priority, the STATUS/ETA report): project skill `.claude/skills/inference-backlog-scheduling/`.
- **Code**: `scripts/coordination/rowflow/` (`publish_row.py`, `rowflow.py allocate`, `filler_run15.sh`, `notify.py`;
  its README has the inference-mailbox watcher) and the successor `scripts/coordination/rowflow2/` (design
  `docs/design/rowflow2-20261105.md`).
- **Live state**: `/mnt/raid0/llm/tmp/compute-flags/` — `ready/<id>.json` (`epyc.row.v3`), `dryrun/<id>/PASS.json |
  FAIL-n.json`, `grants/<id>.grant|.ended|.complete`, `notify/inbox/inference.jsonl`, keeper log
  `ws58-calendar-keeper.log`.
- Plan long measurements with [measurement sufficiency](measurement-sufficiency.md); a grant end is a resource
  boundary, not a scientific completion criterion.

Consolidated 2026-11-07 (keeper-friction review pass 5). The writer-era protocol (FREED flags, grant writers,
`grant_ok.sh`, `ram_admit.sh`, FILLERS 18-cell rows, `filler_run2..8`, owner duties 1-30, the *Queue semantics* and
*Grant validator* sections) was retired by the 2026-11-01 "one allocator" ruling; its text is in this file's git
history before this date and its incidents in the skill's incident ledger
(`.claude/skills/inference-backlog-scheduling/references/incident-ledger.md`). Those tools stay on disk for rows
armed before 2026-11-01 only.

## Deploying rowflow: `deploy_rowflow.sh` is the ONLY sanctioned path (operator 2026-11-05)

> **FROZEN: `filler_run15.sh` only.** The 2026-11-05 freeze ("Freeze current + build rowflow2") covered `rowflow.py`,
> `publish_row.py` and `filler_run15.sh`; on **2026-11-10 the operator lifted it on `rowflow.py` and `publish_row.py`**
> ("Lift freeze on 2, keep engine (Recommended)", pipeline audit finding #14). Those two now deploy through the unit +
> replay gates with a `D9-ack:` line on the commit and no per-change `--emergency`. `deploy_rowflow.sh` still refuses
> (exit 77) a deploy that changes `filler_run15.sh` (the engine running pollers re-read) unless `--emergency "<reason>"`
> is given; the reason is recorded in `DEPLOYED.json`. rowflow2 keeps running in read-only SHADOW beside the live keeper.

Nothing may copy files into `compute-flags/` by hand: every installed file is a line of
`scripts/coordination/INSTALL.manifest`, and `deploy_rowflow.sh --parity` reports drift (SAME/DIFF/MISSING). `scripts/coordination/rowflow/deploy_rowflow.sh
[--ref origin/main] [--check-only] [--emergency "<reason>"]` stages a detached worktree of `<ref>`, runs the unit tests
and the replay gate (`scripts/coordination/tests/replay/`), refuses on any failure, refuses to swap `filler_run15.sh`
under open grants, backs up each changed file, installs via `<f>.part` + `mv -f`, writes `DEPLOYED.json`, and requires a
keeper `SNAPSHOT` with no traceback within 300 s, rolling back otherwise. Run `--check-only` before asking for a deploy.
A new incident class = a new scenario in `tests/replay/scenarios.py`, never a new `if`.

## The grant contract (what a launcher must do)

1. **No grant, no run.** The launcher (`filler_run15.sh --id <id> --class cpu|gpu|cpu+gpu --cmd ... --min-window S
   --stop <abs STOP>`) polls `grants/<id>.grant` (`regions=<...> start=<UTC> end=<UTC hard>`), shell `sleep` only, and
   runs only inside the window, under exactly the granted regions (`FILLER_CPUS`, `FILLER_THREADS`, `FILLER_END_ISO`
   in the job env). The keeper is the only grant writer; peers never write grants.
2. **One row = one STOP file, absolute, never shared with a sibling row** (one withdraw killed every sibling,
   2026-11-06). STOP is honoured before start, between items and mid-job.
3. **At `end` or STOP:** stop new items, SIGTERM then SIGKILL by the pid / process group the launcher itself created
   (never a name pattern), verify dead, stop + remove the docker containers the row started (`epyc.filler.row=<id>`
   label, via the `docker` shim), release the claim, delete the grant, write `grants/<id>.ended` (`rc=<n> time=<UTC>
   reason=<...>`). `rc=75` = window/deadline, `124` = hard end, `5` = `--precond-cmd` build missing, `2` = unusable
   grant for the class, `4` = port/lock refused, `78` = fenced GPU test that never touched the GPU.
4. **All work done:** write `grants/<id>.complete`; the launcher exits for good. Only a *grant* may complete a row; a
   smoke's outputs never count.
5. **Resumable** where the work allows it (resume-skip on already-written units); a run over 1.5x its estimate is a
   failure to explain; a row whose predecessor ended `rc=75 deadline` republishes with a larger `estimate_s`.
6. **Watch your own rows.** Every row alert lands in the inference mailbox; arm the zero-token watcher in
   `scripts/coordination/rowflow/README.md` right after `publish_row.py`, read with `rowflow.py alerts --unacked`, ack
   with `--ack <key>`. On any `.ended rc!=0`: read the log, name the cause, fix, republish (`-rN`, `supersedes`), never
   re-grant a failure blind.

## Publishing discipline (2026-11-09, AutoKernel row failures)

- **Publish a row the moment it is ready.** The keeper ranks and serializes rows; never hold one back to protect another row's window.
- **One publish per id at a time, in the foreground.** A republish during that id's smoke unpublishes the row.
- **Before a row's first keeper launch** read the entrypoint's docstring, `--help` and refusal paths, and run one manual `--dry-run`. After merging into code a prepared row uses, redo its gates before publishing.
- **A job dir's `launch.sh` ignores `--dry-run` and starts a REAL launcher.** Dry-run a row with its `precond.sh` plus the runner's own `--dry-run`, never `launch.sh --dry-run` (2026-11-11, AGG-1.5 prep).
- **A quarter booked on purpose and kept idle is declared, not hidden (pipeline-mgmt 2026-11-21).** A timing row that books extra quarters as a pre-registered contention guard (it benches on q1 and a /proc/stat sampler on q0+q2 rejects any cell where they are busy) adds the optional spec field `"quiet_guard_regions": ["q0", "q2"]`: a non-empty list of quarters that must be a subset of the row's booked `regions` (publish refuses otherwise) and is carried into the `ready/<id>.json` manifest. The keeper's UNDERUSED check and its per-region IDLE-HELD log and IDLE-HELD-WARN skip those regions (no UNDERUSED, UNDERUSED-SHRINK, IDLE-HELD or warning for them) and logs `QUIET-GUARD <id> regions=...` once; `queue_status.py` prints `GUARD q0,q2` instead of `IDLE-HELD` for them. Regions NOT listed are judged as before, and the build-idle auto-release still touches only `build-*` grants.
- **Smokes hold GPU residency about 45 s**, the keeper's minimum is 40 s; a longer idle load blocks every other row's quiet check.
- **Non-inference work never waits behind inference, but during a quiet-host measurement builds and tests may use only the partial q3 cores that do not interfere with the GPU management threads (72-87 and siblings 168-183), and only if those are free.** Never 88-95 or 184-191. If the measurement holds them too, as a CPU row on 0-95 does, builds and tests wait for its `.ended`; edits, commits and dispatch continue (operator 2026-11-09).
- **A job must propagate its real exit code**, and a smoke's output must not satisfy the live `--complete-cmd`.
- **A row is queued only if its manifest is in `ready/` or it holds a grant.** A row whose dry run failed sits in `dryrun/<id>/` (`FAIL-1.json`, `SMOKE-EXITED.json`) and runs nothing. After every `publish_row.py`, check `ls ready/<id>.json` (or `dryrun/<id>/PASS.json`); the exit of the publish command is not that check. 2026-11-09: three AutoKernel rows failed their dry run and went unnoticed for hours, including (`ak-iq3s-prof-c9-20261109` 20:45Z, `inf75-w2-gpu-census-c9-20261109` 21:10Z), and a row in `dryrun/` reads as "published" in a prose status.
- **A job whose smoke writes its output somewhere other than the live `result_path` needs a `smoke_predicate`** that tests the smoke output (newer than `FILLER_SMOKE_T0`, expected verdict), else the keeper cannot see the smoke's output. Write it before the first publish and test it against a real smoke output; the two failed rows above both ended with their `smoke_predicate` never exiting 0 (their `FAIL-1.json` says so).
- **A build job exits non-zero on `BUILD_FAIL`.** On 2026-11-09 a mutant build wrote `BUILD_FAIL`, exited 0, counted complete and starved the GPU row behind it.
- **Big-model smokes test plumbing only** (latency pre-check plus one answered request), not the full workload; a CPU smoke gets 4 cores, so widen it with the spec key `smoke_cpus` (4..24, never above the row's own width; 24 may take a whole free q0-q2 quarter, never drain-reserved cores or q3 88-95 while a GPU row is queued) only when even plumbing cannot finish on 4 cores (D9 2026-11-18).
- **A smoke proves the paths it touched, at that moment.** c2-producer-replay passed its smoke, then crashed on import because its source worktree was removed before the grant. Pin every worktree a row imports from until the row is filed.
- **A smoke in a separate process from the main run defeats in-memory caches.** AGG-1.5 r3 (2026-11-11) tripped `no_rebuild_per_request` because the smoke process and the resumed main run each built the JPMORGAN index (5 builds vs the expected 4). A "no rebuild" gate must count per process, or the index must persist to disk; persisting it (orchestrator `4299454597bb`) is the fix.
- **After publishing, check smoke status inside the first slot; do not wait only for the grant's end marker.** A failed smoke never writes `grants/<id>.ended`, so an end-only watcher waits forever. Watch `dryrun/<id>/FAIL-*` (and `SMOKE-EXITED.json`) as well as `grants/<id>.ended`. 2026-11-11: `agg13-reingest-cpu-20261111` and `agg14-backfill-cpu-20261111` failed smoke at 21:33Z on a duplicate `reused` keyword in `seed_units` (research `40010bcfb`) and were found only by looking at `dryrun/`.
- **Keep rows ready ahead of the current ones.** There is no timer to refill the queue: on 2026-11-09 the day's rows ended about 19:30Z with none behind them and the host sat idle. Publish the next rows while the last are running.
- A row that builds from the C9 configure argv (`-DLLAMA_LLGUIDANCE=ON`) needs `cargo`: put the pinned toolchain from the build identity's INPUTS.json (`rust-*/bin`) first on PATH with an empty CARGO_HOME, or `llama-bench`/`common` fail with `cargo: not found` (hit twice on 2026-11-09).

## Job-side rules (each bought by an incident; dates in the skill's incident ledger)

- fold-build rows must write VERSION.txt + SHA256SUMS + PROVENANCE.md into each store (re-anchor find_store_build requires them)
- **Derive CPUs and thread counts from the granted affinity**, never hardcode a CPU list, and set the CPU-backend
  thread count explicitly (`-t`, `GGML_N_THREADS`, `OMP_NUM_THREADS`): under `taskset` ggml still defaults to 192
  threads (H8b correctness took 16 min per pass, 2026-11-06). `job_fence.py` sets the thread env from
  `sched_getaffinity` when unset.
- **GPU rows prove residency by their own PID**: hold own-PID VRAM for >= 40 s (the 1 s sampler), re-pin every task
  after start (`HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0` or `taskset -a -p`; one ROCr thread is born with full-host
  affinity), and never run a CPU-wide preflight or bench inside a GPU-only grant. Containers carry `--cpuset-cpus
  "$FILLER_CPUS"`; the docker client's `taskset` does not confine them.
- **GPU row serving argv = the orchestrator pinned-launch contract** (GPS-PIN-1, 2026-11-18): `numactl --membind=3 -- taskset -c 184-191
  <llama-server> ... -t 8 -tb 8` with `HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0` in the env (`scripts/server/launch_affinity.py
  apply_pinned_launch_env`). The c14/c15 fold rows launched `taskset` only: no membind, no knob, so one ROCr thread per server ran on all
  CPUs. Whether that matters for visit scatter is measured by `gps-pin-1-scatter-gpu-20261118` (pinned vs unpinned, KEEP iff pinned CV <= 0.5x).
- **Harness servers guard the HIP-graph VRAM leak** (GPU-LEAK-1): correctness jobs run `GGML_CUDA_DISABLE_GRAPHS=1`,
  timing jobs keep graphs on with a fresh server per session, both with an own-PID VRAM guard that ends cleanly
  (`.ended`, not OOM). Prove the knob is in the binary first (`strings <lib> | grep GGML_CUDA_DISABLE_GRAPHS`).
- **Never use `run_direct` for GPU work while the keeper runs**: it counts as a foreign KFD user and stalls the
  keeper's GPU queue. Route GPU jobs through grants. More generally (operator, 2026-11-07): **do not
  `run_direct` anything while a row is grantable** — publish it as a row and let the keeper grant it;
  `run_direct` is for the case where no keeper/grant path exists. And re-arm your completion watcher after
  EVERY event (11-07: a watcher not re-armed after 01:22 let two failures sit ~6 GPU-h unnoticed).
- **A job must not re-claim a device its launcher already holds** (`--no-device-claim` inside the job; a self-claim
  waits on itself and dies `rc=75`).
- **A quality or correctness job runs the role's registered serving env** from `model_registry.yaml`, never the bare
  binary (Q38FN without `GGML_FUSED_DECODE_OFF=1` aborted on a fused-decode repack bug). Qwen3.x servers: `.
  jobs/qwen_thinking_lib.sh`, `$(qwen_reasoning_args "$MODEL")` in the argv, `qwen_first_reply_preflight $PORT`
  before the workload; chat-path requests send `enable_thinking:false` unless thinking is pre-registered.
- **Linkage gates compare real paths** (`kernels/production/{cpu,gpu}` are symlinks into `kernels/builds/`); resolve
  with `realpath`. Never `strings <bin> | grep -q` under `pipefail` (SIGPIPE false FAIL); capture first.
- **Use an explicit interpreter** (`/usr/bin/python3` or the venv path); a bare `python3` under region-lock resolves
  to the orchestrator `.venv`.
- **Never edit a running launcher or job script**; version it (`job2.sh`) and re-arm.
- **Pinned-worktree jobs refuse a dirty tree**, and a shared lib must not reassign a job's pinned tree variable.
- **A model-free correctness row needs an exec tripwire** that fails on `llama-*`/`.gguf` execs, proven on a control.
- **Verify every fast "complete" against its per-gate lines**, not the summary verdict (`fail=1` set inside a `$(...)`
  subshell never reached a `GATE gpu PASS` summary).
- **Subagent briefs**: any model execution (ASR and TTS included) needs a row and a grant; never touch another
  session's scratchpad; worktrees are removed with `git worktree remove <path>`, never `prune`; the Bash containment
  hook refuses variable-expanded write targets, so launch commands use literal paths.
- `WINDOW_CONFIRMED=1` may be exported only inside a live grant naming the job's regions (OP-KPF64-ARM, 2026-10-22).

## Shared job templates: import, never copy (operator 2026-11-06)

Two vendored lane templates caused most lost compute in Pass 4 of
`docs/reports/coordination/keeper-friction-review-20261105.md`: the gitnexus-impact `job.py` (~40 copies, 40 rc!=0
runs after a good 29-min analyze, ~9 host-h) and the yarn `write_fence.py` / `smoke_admission.py` /
`smoke_root_exec.py` trio. **New rows import the shared modules from
`/mnt/raid0/llm/tmp/compute-flags/bin/job_templates/`** (source and tests: `scripts/coordination/job_templates/`;
redeploy with a plain copy after the tests pass). Existing rows are not rewritten.

- `gitnexus_impact.py --config job.json --phase analyze|scan|all`: analyze writes `out/ANALYZED.json` and is skipped
  while the graph is fresh; a scan never re-analyzes. Unresolved / partial / vacuous scan = rc 0 with
  `out/INCONCLUSIVE`; HIGH/CRITICAL = rc 3; failed analyze or parser defect = rc 1.
- `job_fence.py fence [--gpu] <dirs> -- /abs/exe ...` / `smoke [--gpu] <root> -- ...` / `admit --cpus .. --granted ..`:
  `--gpu` allows `/dev/kfd` and `/dev/dri/*` and gives HIP a writable `TMPDIR` inside the fence; admission is affinity
  **subset of the grant**; `repin_threads()` pulls the ROCr thread into the grant; `tree_usage()` skips `comgr-*` /
  `.hip-tmp` entries; declared output dirs allow mkdir/rmdir/unlink; `max_file_mib` (spec or `MAX_FILE_MIB`, default
  128, cap 8192) sets RLIMIT_FSIZE, with a one-line EACCES / SIGXFSZ diagnostic.
- Publish lint (warn only): `template_lint.py <launcher>` warns on a vendored `write_fence.py` /
  `smoke_admission.py` / `smoke_root_exec.py` that does not import `job_fence`, and on a one-process gitnexus job.
  `rowflow2.publish` runs it; the frozen `publish_row.py` does not, so run it by hand until cutover.

## Codex NI client contract (2026-10-24/25)

Codex has no compute authority and is not reachable by `SendMessage`; IPC is files under
`/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/` (the IPC contract and the rule text Codex passes into every worker
brief live there). Harness sizing: `agents/shared/OPERATING_CONSTRAINTS.md` → *Codex Delegation & Long-Horizon
Throughput*.

- **Assign, don't offer.** Every non-inference blocker of a row is ASSIGNED to Codex with a spec, acceptance tests and
  a deadline tied to the window it unblocks. A standalone coding task goes to Codex by default.
- **Codex executes nothing outside a grant.** Any interpreter or toolchain run (`python`, `pytest`, `py_compile`,
  `cmake`, compilers, `gitnexus analyze`) is compute; while any `compute-flags/HOLD_*` exists nothing of Codex's runs.
- **Codex writes only its own files and refs**: `codex/*` with an explicit refspec, never a kernel `experimental` /
  `ak` / `main` branch, a shared clone, the frozen production tree or the kernel store. On a failed run it diagnoses and
  republishes the same id with a reviewed fix; no blind retries.
- **Since 2026-11-01** the day-to-day form is the churn flow (`backlog-churn-flow.md`): each worker reads
  `compute-flags/BACKLOG-<worker>.md`, clears the non-inference tasks under its blocked rows, prepares the launcher,
  lets the keeper qualify it and moves on. `[unblocks: <ready-id>]` on a task line links it to the row it frees.

## Lessons from 2026-11-10 (AutoKernel)

- **Harness units must stay in the row's process group.** `c11-skinny-det-gpu-20261110-r2` used `skdetjob.py` killpg isolation; at hard-end a GPU child escaped the row's group and held 36.9 GiB from 15:05 to 16:40Z. The keeper saw the VRAM as foreign, dropped the floor's reservation, and the floor r3 drain slipped from a predicted 19:07Z to about 18:35Z. Do not setsid/killpg-isolate a child out of the row's group; the engine's cgroup leaf reaping (deployed by Pipeline) is the backstop, not a licence.
- **A replay that replays the model's own reply verbatim never enters checkpoint search.** The INF-86 v1 smoke had `attempt_lines=0` because a verbatim reply replay extends the cached prefix exactly. To exercise the hybrid-checkpoint path the harness needs a trimmed-reply divergence (the next request diverges inside the prior reply). Check `attempt_lines > 0` in the smoke before burning a window (`inf86-reprefill-rate-20261110`).
- **Placement:** CPU rows prefer q0-q2 over q3 (operator, 2026-11-10); gpu-q3 timing rows block while another row holds q3.
- **A fail-closed foreign-load guard needs a threshold matched to the window's width, plus two-sample persistence.** Floor r3 died on a janitor `du` scan at 57% and r4 on a single 8.7% `git log` sample; either transient killed a whole-host drain. r5 uses a 25% threshold with two-sample persistence.
- **When copying a row dir to a new attempt, drop one-shot marks** such as ONE-WINDOW, or the new attempt inherits a spent window.
- **In the shared clone, commit from a temp worktree and never `update-ref` local main.** An `update-ref` on main left /workspace stale (2026-11-10) and a restore had to put 5 docs/publication files back to HEAD. Use `git worktree add -b <tmp> <path> origin/main` and `serialized_push.py --push`.

## Lessons from 2026-11-11 (AutoKernel)

- **Never run network pulls inside a grant.** `vllm-aiter-gfx90a-gpu-20261111` r1 pulled a ~35 GB image under the GPU grant and was killed at rc=143 three minutes in. Pre-stage large downloads outside the grant (prep step, before publishing) and make the row fail fast when the artifact is absent.
- **Read `queue_status.py` output WITH its section headers.** Grepping lines without the headers misattributed GRANTABLE/QUEUED rows as RUNNING. Always `grep -n -A` from the header.
- **Check the `.ended` reason before reporting a withdrawal or stop as a bug.** `reason=job-rc-143:exited` (session kill) and `partial-native-incomplete` (smoke rc75) are normal stop paths; only `reason=complete` is a run result, and smoke-stage ends live in `dryrun/<id>/ended`, not `grants/`.
- **An analysis harness that fakes the phenomenon overstates real-world gains.** The INF-86 replay's wasted-token metric counted the unavoidable SSM suffix as waste, and the replay does not look like real orchestrator traffic. Probe on real logged traffic (e.g. `inf86-cms512-live-probe`) before a stack change; hold the reload until it reads RELOAD_OK.
- **A GPU-row smoke must make real GPU contact (VRAM residency).** A smoke that never touches the MI210 fails the residency check and publish refuses (H13 `ak-asm-h13-hctail-gpu-20261111` r1 smoke, no GPU contact). Make the smoke load or run one tiny GPU op and let the residency probe see it.
- **Never `cp -a` a row dir into a successor.** Hidden markers (`.exported`) and build caches carry over and break the new job. Copy only the sealed sources (job script, spec, pinned inputs) into a fresh dir.
- **Validate a harness fix offline against every suite's stored logs before spending GPU on a rerun.** race-eqv r7 and r8 each burned ~40 min of MI210 on an instrument failure that a replay of stored baseline logs per suite would have caught (the r9 fix `4d441c131` ships an offline baseline replay test for this reason).
- **Correctness-only GPU rows use shape `gpu`, not `gpu-q3`.** They need no q3 host threads, so as `gpu` they can backfill while q3 is busy (race-eqv, b3-gdn r3). Keep gpu-q3 for timing rows.
- **Verify a row is published before reporting it queued.** Check `ready/<id>.json` exists (and the keeper lists it under GRANTABLE/QUEUED). race-eqv r9 was reported queued with no `ready/` entry.

## Lessons from 2026-11-15/16 (AutoKernel, upstream b12421 rows)

- **Parse `test-backend-ops` from the `Failing tests:` block after an ANSI strip, and fail closed.** Per-op `[OP] ... test failed FAIL` lines did not match the old `FAIL_RE`, giving vacuous `n_fail=0`; r2+ rows use `tbo_fail_names()`. rc!=0 with no parsed failures is a failure.
- **Decode A/Bs must set `ignore_eos`.** Without it generations end early and the step-cost windows differ; the first GPU A/Bs were invalidated by it.
- **GPU MTP A/Bs need an acceptance-normalized metric.** GPU greedy output is nondeterministic, so draft acceptance varies per visit (bisect `up-bundle1-gpu-bisect-20261116`: 25-197 of ~280). Gate on ms per verify step = predicted_ms/(n - draft_n_accepted), never tok/s.
- **Run `refresh_hub_view.sh` before `publish_row`**, or the row is published against a stale hub view.
- **Launch containers via `docker` on PATH**, not by an absolute path or wrapper that may be absent in the grant shell.

## Lessons from 2026-11-17 (AutoKernel, C12/C13 rows)

- **`llama-server` builds from a `git archive` need an offline UI dist.** Rows have no network, so `llama-ui-assets` fails (farows r13, c12-cpu-validate r4, q38p1, c13-farows-sidechannel, greedy-aa-bisect). Seed `<src>/tools/ui/dist` from a local dist AND configure `-DLLAMA_USE_PREBUILT_UI=OFF`.
- **Never depend on another row's build dir.** It is reclaimed when that row is filed (c12-cpu-validate r4 adopting r2's build, q38p1). Build in-row, or hardlink the artifact and verify its sha before use.
- **Watchers must scan for ended-but-unfiled rows and smoke FAILs, not first-match a fixed list.** Compare `grants/*.ended` against `filing-done/*.FILED` (queue_status prints `UNFILED-ENDED`) and read the smoke-stage ends too.
- **The keeper burns a row id once `.ended` exists, and nothing auto-requeues a STOPped row.** A `"resumable": true` row its owner STOPs (job checkpoints, exits `rc=75 reason=stopped`) or releases early (`reason=released-early`) is requeued in place by its owner: `rowflow.py resume <id> --by <owner> --reason R`. It refuses unless the last end was one of those two, the spec is resumable, no job runs and the PASS still matches the launcher. It archives the `.ended` to `grants/.resume/`, removes the STOP file, archives any FILED receipt to `filing-done/.resumed/` (the next end files again), puts the manifest back in `ready/` (no new smoke), keeps `out/` and the job's resume ledger, and logs `ROW-RESUMED <id>`. `rowflow.py status` prints `next: resume (rowflow.py resume <id>)` for such rows. Only a non-resumable row, or one whose launcher/spec changed, needs an `-rN` successor. (Hard-end at the keeper's own drain cap is the separate, automatic capcut requeue.)
- **GPU rows booking `gpu-q3` wait on q3.** Correctness-only GPU rows should book shape `gpu` (`mi210_0,184-191`) without `--role bench` so they backfill while q3 is busy.
- **A packet with an internal source-pin manifest must be re-pinned whenever its sources are edited,** or the sealed check fails at arm time.
- **Parse `test-backend-ops` failure lines that start with `[OP] ERR` or print NaN.** The old matcher missed them and gave vacuous passes; fail closed on rc != 0 with no parsed failure.
- **A controller running inside a GPU grant deadlocked on the runner's own flock** until `e8d969919` (fixed by Pipeline); a controller-in-grant design must take no lock the runner already holds.
- **Ratify scripts must be apply-tested through the real commit hooks** (the `Operator-Ratified` trailer path), not only dry-run, and ship as one single-line command for the operator.

## Lessons from 2026-11-17/18 (AutoKernel, C13 rows)

- **Row servers run inside a Landlock write fence (`out/servers`).** A profiler or env output path (for example a `--eval-file`, trace or stats path) that sits outside the fence is denied at run time: q38p1-c13 r3 collected valid data and was still rejected because the eval file went to `out/prof`. Keep every profiler and env output path inside the fence, and add a fail-fast write probe to each such path before the long unit starts.
- **Residency samplers must poll fast for processes that live about 1 s.** A sampler at a multi-second period misses a short-lived server or test binary, so a "no VRAM / no KFD process" reading can be a sampling miss (see Observation Windows). Poll at 100-200 ms for short processes, and record the sample count next to the residency claim.
- **A futility verdict must name its offenders.** FUTILITY_NEAR_UNPARSED ended with an EMPTY offender list on q81 r3: a classifier bug masked as a finding, and the answer was only recoverable by reading the raw data. A futility class must print the cases, gate or unit that triggered it; an empty list is a classifier defect, not a verdict.
- **GPU greedy identity gates need an A-vs-A calibration.** Identical GPU runs diverge (C10-GPU-GREEDY-AA-DIVERGENCE, NOT_LOCALIZED), so a bitwise token-ID gate with no calibration reads nondeterminism as NOT_EXACT: inf48-favec-tail returned NOT_EXACT while its knob-OFF build, a no-op, also failed to reproduce C13. Run an A-vs-A arm first and make the gate "candidate divergence within the A-vs-A band", or use only the correctness and speed gates on GPU.
- 2026-11-18 (autokernel, C11-GPUPROOF-ANSI-PARSE): parse tbo output with rowlib tbo_parse (`epyc-inference-research/scripts/kernel_rnd/rowlib/tbo_parse.py`), never `endswith('OK')`. Note: no box by that name exists in kernel-champion-and-promotion.md and the c11 `gpuproof.py` has no tbo parser, so nothing was ticked.
- 2026-11-18 (autokernel, GPU-MTP-ACCEPTANCE-METRIC + KEEP-TAIL-1): GPU MTP decode A/B row templates import `epyc-inference-research/scripts/kernel_rnd/rowlib/decode_metrics.py` (`step_ms` = predicted_ms/(predicted_n-draft_n_accepted), `cells_from_visits`, mean/median/pair-geomean ratios) and `rowlib/keep_tail.py` (`p95_inflation`, `widened_floor` = max(2%, sqrt2*P), `apply_rule` returns legacy and widened verdicts), never a per-row copy of `step_ms`. Report P and F beside every GPU A/B; the legacy rule still gates until the champion owner agrees to enforce F (research d166ca005).

## Lessons from 2026-11-18 (AutoKernel, C14/C15 rows)

- **rowflow derives threads only from launcher literals, never from spec `declared_threads`.** Write `-t N` or `OMP_NUM_THREADS=N` literally in the launcher or the row is booked with the wrong thread count.
- **"draining for …" in queue_status is not proof a region is reserved (corrected 2026-11-18).** IDLE-WHY prefixed EVERY idle region with the drain line whenever any drain existed; the pm-drain-gpu-20261118 trace (FINDINGS.md) showed the drain never reserved the MI210 or q3 (a CPU multi-quarter target's options exclude q3). The GPU was actually held by an exclusive codemode GPU grant (11:50-~15:03Z, util swinging 0-100%), then the smoke batch. Before blaming a drain, check the real grants (`compute-flags/grants/*.grant`) and rocm-smi over a window. Operator D9 (2026-11-18): the label now prints only on actually-reserved regions, and drains have a 2 h reserve horizon. The rank 35->110 republish of 13a/a3b48 was harmless but did not change placement.
- **`queue_status` "measured gpu-quiet=0% IDLE-HELD" is not GPU utilisation.** It reads the reservation, not the device; check `rocm-smi` before concluding the GPU is busy or idle.
- **`test-backend-ops` MUL_MAT with n>128 q8_0 on CDNA goes to hipBLAS, not MMQ.** Capture, trace and replay rows must use n<=128 or they profile the wrong kernel.
- **rocprofv3 is at `/opt/rocm/bin/rocprofv3`** (not on PATH).
- **The commit hook misreads `git commit -qF <file>` as a pathspec.** Use separate flags: `git commit -q -F <file>`.
- **CPU speed rows on this host need a quiet booking of q0-q2, not the whole host (2026-11-18, amended).** Co-tenants keep foreign busy at 25-50%; the 25% foreign filter voided every c15-fold-cpu-r2 visit. Book regions 0-71 (q0-q2), pin the servers to q1+q2 (24-71) with a literal `--threads 48`, and keep the foreign-load sampler informational (see c15-cpu-fa-splitkv-speed-20261118-r2, KEEP). **Never book a whole-host quiet window (0-95) for CPU timing**: it takes q3 and idles the MI210 for the whole row (c15-fold-cpu r3 was stopped for this).
- **A gpu-q3 grant is 16 CPUs (88-95,184-191).** A row whose precondition demands exactly 8 CPUs refuses every grant (rka-a3b-mmvf8-e2e r1, no data). Check `>=` the threads you use, never `==`.
- **Do not carry `estimate_s` over from a predecessor row.** A copied estimate turned a 3 h approval into a 10 h grant; re-derive it from this row's own visits x cell time.
- **Q38FN GPU noise floor: A/A KLD ~0.025 (0.0248-0.0267), A/A PPL spread ~1.4%, greedy A/A agreement 0.33-0.78.** Q38FN routing amplifies rounding ~45x versus the dense 27B (~0.0006). Any Q38FN GPU quality clause must be A/A-calibrated; on the GPU the 27B clause decides (operator, 2026-11-18).
- **Build pocket: a long q0-q2 row must leave short builds a pocket (2026-11-20).** filler-ak-q38fn-draftfa-window-cpu-20261119 (multi-quarter(3), 28000 s) held q0-q2 for ~7.8 h while a build claim waited >45 min (q3 is the MI210's host threads). Rule (`build_pocket_policy.json`, overridable via `allocator.json` `build_pocket`): a CPU row booking all of q0-q2 with hold > `long_hold_s` (7200 s) and no `"whole_host_need": true` (a) is not granted while a build claim waits (`BUILD-POCKET-HELD`; waiter = live region-lock FIFO ticket on q0-q2, or a `build-wait/<owner>.json` left by a refused `rowflow.py claim --build`), and (b) if `"resumable": true`, is granted with a hard end at `max_hold_s` (capcut-requeued), so the pocket reopens at each cut. A non-resumable long row is never cut. Wire a long row's declaration instead of relying on the carve-out: resumable if it checkpoints, `whole_host_need` if it truly needs q0-q2 for hours.

## Releasing an idle grant early (2026-11-20, AutoKernel)

A grant whose job is idle or finished (a leftover q2 slot, a build lane booked to 22:16Z) is released by its OWNER, not left to run to `end=`:

```
python3 scripts/coordination/rowflow/rowflow.py release <row-or-build-id> --by <owner> --reason "<why>" [--regions q2[,q1]]
```

- **Owner-only**: `--by` (default: `EPYC_AGENT_ID`/`WRAPUP_AGENT_ID`/`SESSION_BUS_AGENT`) must equal the row manifest `owner`, or the `build.json` owner for `build-*` grants.
- **Refused while the job runs**: a live engine/poller/dry-run pid (a zombie is dead) refuses. It never kills; preemption stays drain-only.
- **Whole release** writes `grants/<id>.ended rc=75 reason=released-early`, renames `.grant` to `.grant.released-early` and logs `GRANT-RELEASED`; the cores free on the keeper's next tick. **`--regions`** (quarters the grant holds, not all of them) shrinks the grant to the rest.
- `open_grants` treats any grant with a `.ended` receipt as released, so a hand-release that leaves `.grant` or `.build.json` behind holds nothing. Hand-editing `grants/` is no longer needed.
