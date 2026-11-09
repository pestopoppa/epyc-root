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

> **FROZEN (operator 2026-11-05, "Freeze current + build rowflow2").** `rowflow.py`, `publish_row.py` and
> `filler_run15.sh` are frozen (`bin/rowflow/DEPLOYED.json`). `deploy_rowflow.sh` refuses (exit 77) any deploy that
> would change one of them unless `--emergency "<reason>"` is given; the reason is recorded in `DEPLOYED.json` and the
> unit + replay gates still run. No new rules, no per-incident `if` in `plan()`/`contract_of`: a scheduling fix lands in
> **rowflow2**, which runs in read-only SHADOW beside the live keeper. **Exit criterion:** rowflow2 passes its shadow
> week (criteria in the design doc) and is cut over; until then the freeze holds. Other `bin/rowflow/` files
> (`notify.py`, `hostutil.py`, …) deploy as before.

Nothing may copy files into `compute-flags/bin/rowflow/` by hand. `scripts/coordination/rowflow/deploy_rowflow.sh
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
- **Smokes hold GPU residency about 45 s**, the keeper's minimum is 40 s; a longer idle load blocks every other row's quiet check.
- **Non-inference work never waits behind inference, but during a quiet-host measurement builds and tests may use only the partial q3 cores that do not interfere with the GPU management threads (72-87 and siblings 168-183), and only if those are free.** Never 88-95 or 184-191. If the measurement holds them too, as a CPU row on 0-95 does, builds and tests wait for its `.ended`; edits, commits and dispatch continue (operator 2026-11-09).
- **A job must propagate its real exit code**, and a smoke's output must not satisfy the live `--complete-cmd`.
- **A row is queued only if its manifest is in `ready/` or it holds a grant.** A row whose dry run failed sits in `dryrun/<id>/` (`FAIL-1.json`, `SMOKE-EXITED.json`) and runs nothing. After every `publish_row.py`, check `ls ready/<id>.json` (or `dryrun/<id>/PASS.json`); the exit of the publish command is not that check. 2026-11-09: three AutoKernel rows failed their dry run and went unnoticed for hours, including (`ak-iq3s-prof-c9-20261109` 20:45Z, `inf75-w2-gpu-census-c9-20261109` 21:10Z), and a row in `dryrun/` reads as "published" in a prose status.
- **A job whose smoke writes its output somewhere other than the live `result_path` needs a `smoke_predicate`** that tests the smoke output (newer than `FILLER_SMOKE_T0`, expected verdict), else the keeper cannot see the smoke's output. Write it before the first publish and test it against a real smoke output; the two failed rows above both ended with their `smoke_predicate` never exiting 0 (their `FAIL-1.json` says so).
- **A build job exits non-zero on `BUILD_FAIL`.** On 2026-11-09 a mutant build wrote `BUILD_FAIL`, exited 0, counted complete and starved the GPU row behind it.
- **A smoke proves the paths it touched, at that moment.** c2-producer-replay passed its smoke, then crashed on import because its source worktree was removed before the grant. Pin every worktree a row imports from until the row is filed.
- **Keep rows ready ahead of the current ones.** There is no timer to refill the queue: on 2026-11-09 the day's rows ended about 19:30Z with none behind them and the host sat idle. Publish the next rows while the last are running.
- A row that builds from the C9 configure argv (`-DLLAMA_LLGUIDANCE=ON`) needs `cargo`: put the pinned toolchain from the build identity's INPUTS.json (`rust-*/bin`) first on PATH with an empty CARGO_HOME, or `llama-bench`/`common` fail with `cargo: not found` (hit twice on 2026-11-09).

## Job-side rules (each bought by an incident; dates in the skill's incident ledger)

- **Derive CPUs and thread counts from the granted affinity**, never hardcode a CPU list, and set the CPU-backend
  thread count explicitly (`-t`, `GGML_N_THREADS`, `OMP_NUM_THREADS`): under `taskset` ggml still defaults to 192
  threads (H8b correctness took 16 min per pass, 2026-11-06). `job_fence.py` sets the thread env from
  `sched_getaffinity` when unset.
- **GPU rows prove residency by their own PID**: hold own-PID VRAM for >= 40 s (the 1 s sampler), re-pin every task
  after start (`HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0` or `taskset -a -p`; one ROCr thread is born with full-host
  affinity), and never run a CPU-wide preflight or bench inside a GPU-only grant. Containers carry `--cpuset-cpus
  "$FILLER_CPUS"`; the docker client's `taskset` does not confine them.
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
