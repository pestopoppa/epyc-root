# Benchmark Analyst Workflow

## Baseline Procedure

1. Define controls (model, prompt set, threads, NUMA mode).
2. Run benchmark with explicit configuration capture.
3. Repeat runs to reduce noise.
4. Compare against baseline and prior best.
5. Publish decision-grade summary with caveats.

## Required Metrics

- Decode throughput (`TG t/s`)
- Prefill throughput (`PP t/s`)
- Acceptance rate (when speculative decode is enabled)
- Variance across repeated runs

## Reporting Standard

- Separate observations from inferences.
- Flag suspicious anomalies before making recommendations.
- Include exact commands and source result paths.

## Scarce windows (a peer's CPU window, or a peer-paused GPU slot)

- **Stop on anything but `open`.** When a run borrows an AutoKernel CPU window
  (`/mnt/raid0/llm/autokernel/cpu-window.json`), stop at once on any `state` other than `open`, or when
  `loop_holds_claim=true`. `closing` means stop, not finish up.
- **A side server lives as long as its bench run.** Start it just before the run, and stop it on every exit
  path. (origin: INC-20260929-peer-window-closing-overrun)
- **Test every check against real artifacts before spending the window.** A dry-run does not exercise
  live-only checks, such as startup-log regexes, thread placement, directories that must exist, and `set -e`
  interactions. Run each check read-only against real logs or the live production process first, and have
  it print what it saw. (origin: INC-20260929-dry-run-missed-live-checks)
- **No GPU work inside another session's GPU measurement window — subagents included.** A small footprint is
  not "no interference": any kernel launch shares the GPU's compute and memory bandwidth with the measured
  server. GPU tests, micro-benchmarks and smoke runs go only into a coordinated slot. A main that dispatches a
  subagent able to touch the GPU either hands it that slot or tells it not to use the GPU.
  (origin: INC-20261003-subagent-gpu-tests-in-peer-window)

## Your own load, and what counts as noise

- **Your own subagents are load too, and the easiest to forget.** Before any gate, bench or calibration you
  start or depend on:
  1. Send "pause tests" to every running subagent.
  2. A pause message lands only at the agent's next tool round, so a suite already running keeps going. Find
     pytest/xdist, build and `test-backend-ops` processes whose cwd is one of your worktrees, and wait for
     them to exit.
  3. Confirm the host is quiet with a live `top -bn2 -d 3`. `ps %CPU` is a lifetime average and does not
     show current load.
  4. Measure, then tell the subagents to resume.

  (origin: 2026-09-26, UFH-12 Phase 0 pre-gates started 4 minutes into a fix agent's `pytest -n 8`)
- **An AutoKernel loop's own floor calibration and A/B phases are measurement windows.** While
  `loop-status.json` shows `serving_floor_provenance: absent`, or anchor llama-servers run back to back, the
  loop is calibrating: run no tests, dry-runs or `find /`, pinned or not. On 2026-09-30 pytest runs (some
  pinned to SMT siblings 184-191 of DS41's cores 0-95) during a 48-launch DS41 serving-floor calibration
  inflated the verified floor to **4.533% instead of about 1.9%**. The operator kept that floor, so candidates
  must beat 4.5% until the next promotion. One unpaused afternoon of tests cost a whole promotion cycle's
  sensitivity.
- **Loop test fixtures take the real GPU device lock.** The loop's full-CPU pytest fixtures acquire
  `/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock` (`claim.DEVICE_LOCK`). Run them through a private-lock runner
  (for example `/mnt/raid0/llm/tmp/c78-dry/runtests.py`, which redirects `DEVICE_LOCK` to a private file).
  Otherwise they hang behind the live loop and can block it.
- **Light background load is metadata, not poisoning** (operator, 2026-10-04: "Cloud hosted agent traffic
  can't possibly be considered poisoning… Let's be a bit more pragmatic"). A measurement preflight refuses
  only on genuinely heavy local CPU work: builds, benchmarks, other local inference, `test-backend-ops`,
  pytest suites. It records the rest (agent harness processes at 100-200% CPU, idle servers, a paused loop)
  as metadata on the run and proceeds. ABA ordering plus repetition already absorbs light noise. Refusing on
  it cost whole measurement windows. The hazard that sinks windows is local compute, usually our own
  subagents' (above, and the GPU rule under *Scarce windows*).

## Running more than one AutoKernel lane

Ratified 2026-10-04 into `agents/shared/OPERATING_CONSTRAINTS.md` (root `35fe43d2`, RATIFY-AK-LANES-20261004); the
bullets below are the working detail.

- **A second lane starts at once, in parallel; it is never gated on a CPU window** (operator, 2026-10-04). An
  AutoKernel lane spends most of its wall time in hosted planning and authoring, which uses no local compute, so
  that phase overlaps the other lane's measurements freely. Only the local steps (builds, ak-check compiles and
  op-tests, calibration, A/B) contend, and those already queue on region claims. Waiting for "a free CPU window"
  before launching the lane idles the planner for nothing.
- **In a multi-loop deployment, check that every local step of an actor phase waits on the OTHER loop's region
  claim.** A loop releases its own claim during the actor phase, so its compile, op-test and build steps must treat
  any live claim as a peer, including one held under the same role name by a different loop. Pinning those steps to
  "spare" cores is not isolation: the affinity tail 184-191 is the SMT sibling set of 88-95, inside q0-q3. (origin:
  research `aef2da6c`, 2026-10-04 — ak-check skipped role `autokernel-cpu` as "its own claim", so with two loops one
  loop's author would compile inside the other loop's measurement; DS41-C122 in
  `handoffs/active/deepseek-v41-flash-evaluation.md`)
- **A pinned research worktree runs only with `PYTHONPATH` starting at the worktree root.** The shared research venv
  (`/mnt/raid0/llm/epyc-inference-research/.venv`) has an editable install of the main clone, so `import
  scripts.lib...` resolves to the main clone's code, not the pinned worktree's, unless the worktree root comes first:
  run from inside the worktree with `PYTHONPATH=.:scripts/kernel_rnd:...`. Prove it before launch:
  `python -c 'import scripts.lib.canonical_recipe as m; print(m.__file__)'` must print a path inside the worktree.
  (origin: 2026-10-04 Q38FN lane launch, DS41-C111 — the editable install shadowed the pinned
  `scripts.lib.canonical_recipe`)

## Gating and folding AutoKernel keeps

- **One launch per arm in a fixed order is not a comparison.** Before acting on a microbench delta (filing a
  regression, starting a bisect), re-run it in interleaved rounds (ABAB…, at least 5–6 rounds) and judge the median
  effect against the between-round spread. (origin: 2026-10-04 — c2 read anchor-gen-022 slower on Q4_K MUL_MAT_ID from
  one fixed-order launch per arm; c5's 6 interleaved rounds put every delta inside the noise, D vs v10 −5.10%
  [−19.44, +1.46], so the planned bisect was skipped. DS41-C124 in `handoffs/active/deepseek-v41-flash-evaluation.md`)
- **Per-keep wins need a bundle gate before they fold.** A chain of keeps that each won a 5-pair keep-grade A/B is not
  evidence that the chain wins: run the serving gate on the whole bundle against its base, and fold only on a
  decisive bundle result. (origin: the 14 DS41 keeps after COR failed two bundle gates — `dca32b0e3` +0.10% vs a
  4.533% floor, then Z vs X −2.51% on 2026-10-04 — and were held off the champion; DS41-C125)
- **Run a correctness gate on the anchor first.** A gate refusal counts against a patch only if the anchor passes the
  identical gate (same flags, seed and suite). Otherwise it is "oracle unavailable", not a patch failure. (origin:
  2026-10-04 AK GPU run 1 — Q8_0-guarded patches refused 5× on q4_K MUL_MAT cases they cannot reach; the anchor had
  only passed the plain invocation, never the seeded `--autokernel-properties` gate. Fix research `e747d45e`;
  INF-81 AKX-ALL-15c)
- **An unpaired single-arm effect beyond the metric's paired noise floor is unverified, not a gain.** Quote it as
  unverified and confirm with a paired run before it reaches a headline. (origin: 2026-10-04 champion-only receipt
  read pp +18.2% unpaired against the stored v10 baseline, beyond the 9.91% paired floor, while the same code's paired
  run 3 h earlier gave −0.12%; host drift. Research `9b57f555` labels such effects `unpaired_unverified`)
- **`region-lock run` changes directory before it runs your command.** The orchestrator shim
  (`epyc-orchestrator/scripts/region-lock`) does `cd "$REPO_ROOT"` so its Python module resolves, so the child runs
  with the orchestrator repo as cwd. Give runner scripts, output dirs and model paths as absolute paths, or `cd` inside
  the child. (origin: 2026-10-04 backlog runners)
- **Dry-run cleanup removes only the exact paths it created, never a glob.** See INC-20261004-glob-rm-deleted-receipt-evidence
  in `docs/reference/agent-config/INCIDENT_LOG.md` (a `rm -rf receipt-ab/paired-*` deleted a real, ingested run dir).
  Copy any ledger-cited run dir under root `artifacts/` before cleanup runs in its scratch tree.
- **Never present a measurement from model A as model B's cost curve because they are "siblings."** Check
  architecture first — Qwen3.6-35B-A3B (dense attention) and Qwen3.8-Flash-Next (QSA sparse indexer attention) are
  both `qwen4exp`-family but have different attention mechanisms with different cost-at-depth behavior; a decode
  falloff curve measured on one does not transfer to the other. (origin: 2026-10-05 — an AK inbox note attributed
  workspace-ec's Qwen3.6-35B-A3B YaRN CPU-leg decode curve to Q38FN; corrected in `store-b0ba1d427/inbox/64-*.md`)
- **A status claim that something was handed off must be backed by the actual send.** "Relayed to X" or "handed to
  the coordinator" is a claim about an event, not a description of intent — verify the message, file or bus entry
  that constitutes the handoff actually exists before writing the claim down. (origin: 2026-10-05 wrap-up review)
- **To make room on a shared host, PAUSE an AutoKernel serial loop (takes effect at the batch boundary); never DRAIN it.** Drain is terminal for that serial state generation and forces a re-anchor. (origin: 2026-10-05 Q38FN incident, DS41-C126)
- **Never wrap a child script in a timeout shorter than its own internal wait.** A subprocess timeout in an outer wrapper that is shorter than the child's own liveness check (both 120 s in this case) will kill a healthy child. (origin: 2026-10-05 Q38FN relaunch attempt 1)
- **Liveness must read the store's loop-status.json, not the per-launch state dir's.** The per-launch state dir holds a snapshot; reads from it miss progress that happened after launch. (origin: 2026-10-05 monitoring defect, `lane_change_watch.py`)
- **Never hand-write build provenance/identity receipts; derive them from the build's own records.** A hand-written provenance attempt was rejected in review. Use evidence-derived provenance (kernel store image metadata, commit identity from the build system). (origin: 2026-10-05 Q38FN re-anchor, DS41-C126)
- **Brief external reviewers with the threat model; adversarial hunting without one inflates friction.** (origin: 2026-10-06, low-bit-scope consensus — 14 review rounds between Opus fixer and Codex independent reviewer were costly; each threat model clarification ('are we hunting for all possible flaws or only load-bearing ones?') shortened rounds)
- **Verify test corpora are derived from the SERVED model's GGUF, not a drafter or sibling.** (origin: 2026-10-06 — served-shape test cases were built from the DSpark block drafter and a dense 27B instead of DS41 and Q38FN's own served GGUFs; the mismatch was structural: DS41 384 experts, 6 used; Q38FN 512 experts, 10 used)
- **zsh doesn't word-split $var; use explicit per-item commands in process-control scripts.** (origin: 2026-10-06 — a `for p in $pids; do kill $p; done` hung in zsh on a variable whose items were space-separated because zsh preserves the string literal)
- **recal_serving_floor writes the legacy serving floor, not the matched-process floor.** (origin: 2026-10-06 — tool name was misleading; the matched floor — the peer floor under the loop's matched instrument — is in the loop's own `loop-status.json` result)
- **A killed parent's child `sleep` can hold a watchdog flock; wait for it before restarting.** (origin: 2026-10-06 — a parent loop was killed, leaving a grandchild `sleep` holding a gpu-quiet flock; the watchdog restart hung on the same lock)

## Research Intake Application and Routing

- **When applying a research intake entry, route its actionable techniques in the same step.** Kernel ideas → inbox notes in the owning AK lanes (hypotheses, cite intake-NNN#record); serving or speculation ideas → a handoff to the stack owner; report the routing with the intake. The sparkglm (intake-1923#record) and TensorFold (intake-1924#record) techniques sat unrouted for hours after application, caught by the operator at wrap-up; immediate routing is part of completing the intake application task. (origin: 2026-10-06, DS41 intake-routing lapse)

## Window discipline (2026-10-06)

- **Smoke the EXACT argv before any window.** Gate-A attempts failed at preflight on script bugs (`--help` wrote to stderr; `strings | grep -q` under pipefail) and burned scheduled time.
- **Never edit a running script**, and **never use `| grep -q` under `set -o pipefail`** (grep exits at the first match, the upstream gets SIGPIPE, the pipeline reports failure).
- **A waiter whose EXIT trap touches DONE also fires when it is stopped.** Make the trap distinguish normal completion from a stop, or the next stage starts on a dead run.
- **Schedule correctness and timing separately.** Correctness runs take build-role quarter claims; timing runs take windows. Single-quarter claims starve full-host waiters while FIFO is off.
- **"All recommended" means the full list**, not the first few.
- **No `pgrep`/`pkill` by name, read-only or not** (CLAUDE.md, Process Management); two subagents did it. Track PIDs you captured.
