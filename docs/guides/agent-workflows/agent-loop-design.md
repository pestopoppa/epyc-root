# Designing an autonomous agent loop

**Convention, ratified 2026-08-28.** Agent-loop work **opens with a pseudocode
expression of the loop** — actors, what each reads, what gates it, where every
rejection goes, and which single step is expensive — and gets alignment on that block
*before* any plan is written around it.

The block is the alignment artifact. The plan is downstream of it.

**Why.** On the AutoKernel rebuild, one review round on the loop block surfaced three
design corrections that prose had hidden across several turns: the critic needed
**two** passes rather than one, every rejection needed an explicit **loopback** to the
actor that could act on it, and hypotheses needed to be **generated against a live
profile** rather than selected from a frozen list. None of those were visible in
paragraphs describing the same system.

---

## The four things a loop block must show

1. **Every actor, and what it reads.** An actor whose inputs are not listed is an
   actor you cannot reason about. AutoKernel's planner was a pure function of a
   context bundle that turned out to be empty — no refusal reasons, no memory, no
   profile — and that was invisible until the inputs were written down.
2. **Every gate, and what it rejects on.** A gate stated as "the critic reviews it"
   is not a gate; state the rejection grounds.
3. **Where every rejection GOES.** *A rejection with no visible destination is a
   bug.* In AutoKernel, `prior_authoring_refusals` filtered on a status the
   controller never wrote, so 22 of 23 authoring failures returned no reason and the
   planner re-derived rejected work blind. The arrow was missing from the design, so
   the defect was invisible in the code.
4. **Which single step costs real resources.** Every gate should sit before it. If a
   gate sits after the expensive step, say why.

## Budgets

Name each budget and keep them **independent**. AutoKernel charged `critic_revise` to
the same 3-strike counter as a real authoring failure, so a hypothesis could be
retired *for the critic doing its job* — in v33, three turns retired
`akh-v2-q5-type-specific-dequant` without ever testing it.

If two failures have different causes, they need different counters.

## Retirement

Distinguish retiring an **attempt** from retiring a **hypothesis**. A bad patch is
not evidence against the idea it was trying to implement. And a hypothesis that
exhausts its budget should re-enter the pool carrying its rejection history, not
disappear: the profile moves, and what was unsupported last week may be the hotspot
this week.

---

## The reference block

This is the AutoKernel discovery loop, and it is **normative**: if an implementation
and this block disagree, the block wins until it is deliberately amended in
[`handoffs/active/autokernel-rebuild-program.md`](../../../handoffs/active/autokernel-rebuild-program.md).

```
when the champion changes (at most weekly otherwise):
    rocprofv3 the champion → ranked hotspots

each iteration, planner works in a worktree with the full toolbox:
    reads   champion · experiments.md · hotspots · hypotheses/inbox/
    probes  FREELY — llama-bench, rocprofv3, test-backend-ops -o OP --perf,
            llvm-objdump for VGPR/occupancy, env-flag sweeps. Nothing gated.
    forms   hypothesis H, backed by evidence it gathered itself

HYPOTHESIS REVIEW LOOP · budget 3 rounds
    CRITIC PASS 1 reviews H — no patch exists yet.
      rejects on: already measured · mechanism unsupported by the profile ·
        no falsifier · wrong surface · already present in v9
      REJECT → reason returned VERBATIM to the planner, which refines or
        regenerates H and re-enters. It still has the toolbox and may go
        probe to answer the objection.
      BUDGET SPENT → record refused_at_formation with every reason and pick a
        DIFFERENT hypothesis. H is NOT retired; it re-enters the pool carrying
        its rejection history and may be revisited once the profile moves.
      cost of a rejection: one planner call. No patch, no build, no GPU.

    planner writes patch P implementing the accepted H

PATCH REVIEW LOOP · budget 2 rounds
    CRITIC PASS 2 reviews the committed diff P.
      rejects on: P does not implement the accepted mechanism · scope creep ·
        correctness risk · edits a file that must stay byte-identical to production
      REJECT → reason returned VERBATIM; planner rewrites P. H is untouched —
        a bad patch is not evidence against the idea.
      BUDGET SPENT → record refused_at_authoring and hand control BACK to the
        hypothesis loop, so H can be refined knowing it could not be implemented
        cleanly.
      cost of a rejection: one authoring call. No build, no GPU.

    build (ccache, -j64)   → fails? reason returns to the planner, rewrite P
    test-backend-ops       → fails? reason returns to the planner, rewrite P
    A/B alternating, n≥5   ← the only GPU spend in the whole iteration

    keep → commit onto the champion branch
    else → negative, with mechanism and sample vector, into experiments.md
```

**Three separate budgets, none feeding another.** **Every rejection returns its reason
to the actor that can act on it**, and nothing is retired without the planner having
seen why. Compile and correctness failures loop back the same way; they need no
critic, because the toolchain's own message is the reason.

Pass 2 sits **before** the build, since the build is the most expensive step. The
tradeoff — it judges the diff without knowing it compiles — is acceptable, because a
compile failure is cheap and returns automatically.

`n≥5` is not a preference. The instrument's own A/A noise floor, measured 2026-08-28
at n=20 alternating pairs, is p95 **2.175%** on prefill and **3.452%** on decode for a
single pair; 4 of 20 pure-noise decode pairs already exceeded the loop's 3%
nomination bar. Five pairs bring those to 0.75% and 1.85%. See
`artifacts/autokernel-aa-noise-floor/` in epyc-inference-research.

---

## What makes this shape work

**The champion tree is the only durable state.** No intermediate artifact needs to be
trusted, because there is none. The champion is a git commit: anyone can check it out
and re-measure it. "Did we improve?" is answered by rebuilding and benching, not by
reading a receipt about a run that happened last Tuesday.

That is the general principle: **prefer verification by reproduction to verification
by proof.** Proof requires every intermediate step to be sealed and refuse-on-doubt,
so its cost grows with the number of steps and has no natural stopping point.
Reproduction requires only that you kept the recipe — cost is one re-run, and it is
bounded. AutoKernel chose proof where reproduction was available: a `llama-bench`
re-run costs 90 seconds, while proving a run was honest cost 3,869 lines in
`gpu_source_evidence.py` to deliver a single float.

**The only durable output is a row saying faster-or-not.** This is the anti-regrowth
property, and it is a design requirement rather than an aesthetic one. If the loop's
sole product is an entry in the store's experiments ledger and a commit on the champion branch, no
agent can spend a week on receipts and call it progress.

**Hypotheses are generated, not selected from a frozen list.** A static portfolio goes
stale exactly when the loop starts working, because every accepted patch moves the
hotspot distribution. Generating against a live profile also dissolves the
do-not-repeat ledger: a planner that reads its own history sees what was tried. Dedup
is a property of having memory, not a mechanism you install.

---

## Operating the existing loop across targets

On the first visit to an explicit CPU/GPU serving target, an absent exact recipe/request
floor is prepared automatically under the existing claim before source research.
Fresh unified CPU targets without an existing applicable floor select
`matched_process_v2`: 24 independent A/A pairs (48 server launches) calibrate the
existing ratio-of-arm-medians estimator at the declared comparison pair count.
Both calibration and comparisons use randomized, balanced AB/BA process pairs.
The descriptive floor interval is not a replacement acceptance threshold.

The serial owner persists the instrument choice before its first child starts.
Existing serial continuations and applicable legacy floors retain `legacy_v1`;
direct CLI and GPU defaults also remain legacy, with `max(2, --serving-pairs)`
calibration launches. `--cpu-calibrate-serving` / `--gpu-calibrate-serving` override
the count; for matched CPU calibration the count means independent pairs and must
be at least24. An explicit smaller legacy count is refused, not silently multiplied.
Matched floors have separate filenames and bind instrument, pair count, workload
and placement. Source-only changes may reuse that frame; runtime recipe changes may
not. Existing exact floors are reused, not recalibrated, and malformed/mismatched
records refuse rather than being overwritten. Dry-run reports preparation but
launches nothing and does not persist an instrument selection.

CPU/GPU runtime treatments use the same executable and existing loop. Prospective `ak-`
campaigns retain admitted recipes; serial batches carry their references automatically.
Historical `aku-*` source campaigns remain source-only. `--calibrate-runtime` is optional:
ordinary source proposals do not require runtime preparation. Default first-treatment
setup declares 800 calibration server launches plus controls. The invocation budget
stops new setup launches and retains completed evidence. Typed runtime interruptions can
resume the original pending pair after serial verifies original child termination and
held-resource accounting. Completed evidence is reused; a fresh holder uses a separate
window for incomplete work. Unknown child cleanup aborts before any fallback measurement.
Other failed targets are not automatically retried. The existing dashboard reports runtime
phase/counts and selected recipe with an observation age independent of heartbeat.

GPU runtime experiments use the existing CPU-host and ROCm0 claims together. Numeric
device observations must cover the measured requests, including interior sampling gaps;
the existing device and duration rules still decide validity. Missing GPU control
suppliers are reported before calibration collection starts, including an explicit
`--calibrate-runtime` request. Source research remains available. This backend wiring
does not itself supply qualified GPU positive/historical controls or authorize a keep.

A runtime keep requires a new recipe-bound source floor, not a rebuild. Existing pruning
protects its original measured build, not every generation. Operational rebinding to a
new source build does not transfer the old gain claim. Changed producer code can refuse
an old strict frame explicitly; never relabel or delete that original evidence.

The research repository's `scripts.kernel_rnd.autokernel.loop.serial_run` CLI
(published source `718f4108`, 2026-09-10) launches finite batches of the existing
`loop.run` as owned children. It does not replace its pool, actors, resource claims,
measurements, grading or keep/null history. Ordinary single-target `loop.run`
arguments remain supported.

For a resolved campaign, research `8f67076c` / main `d5705634` adds automatic roster
assembly from ready enrolled production/candidate targets plus **one** concise
owned-target map. It derives the facts already present in enrollment; original
editable source, branch, anchor and frozen requests remain explicit. The
[research roster contract and owner-map example](https://github.com/pestopoppa/epyc-inference-research/blob/main/docs/autokernel-serial-roster.md)
documents the exact fields and optional shared actor settings. No per-target argv
files are required in this mode:

```bash
EPYC_ROOT_REPO=/mnt/raid0/llm/worktrees/mains/autokernel-unified-20260908 \
PYTHONPATH=.:/mnt/raid0/llm/worktrees/mains/autokernel-unified-orchestrator-20260908 \
python3 -m scripts.kernel_rnd.autokernel.loop.serial_run \
  --resolved-campaign /absolute/inputs/original-resolved-campaign.json \
  --owned-targets /absolute/inputs/owned-targets.json \
  --batch-iterations 1 --rounds 1 \
  --state-dir /absolute/dedicated-serial-state --dry-run
```

Owned-roster mode now derives resource-time scheduling automatically and requires
one iteration per selected stage. It preserves original CPU/GPU held intervals for
accounting and selects new stage identities on subsequent passes. Failed targets
are removed from selection. `--scheduler-manifest` is an optional policy override,
not required setup. The printed default whole-stage bound is build timeout plus
four stage timeouts; overruns remain charged and fence successors. `--rounds 0`
continues until STOP, the derived 1000-attempt cap, or the corresponding charged-time
budget. Explicit target-argv mode retains its previous round-robin behavior unless
a scheduler manifest is supplied. A hand-built GPU anchor can explicitly opt into
the existing `allow_unverified_anchor` owner-map flag; CPU identity rules are unchanged.

Run from the research checkout. This dry-run invokes the existing owner's startup
and workload checks without providers/builds/claims; it still reads original
startup/workload metadata, so respect the live owner's boundary. Remove `--dry-run`
only at that owner's authorized start boundary. Unavailable/unowned targets are
reported explicitly, not treated as complete coverage. The real GLM owner dry-run
passed on 2026-09-10 (1 ready seed, 17 unavailable), verifying original startup,
model census and the retained request floor; it was not a live mixed-target rotation
or a new performance measurement. `EPYC_ROOT_REPO` selects the installed feedback
reader without requiring an optional common-args file. To retain the current GLM
trial's **medium** actor effort on its next start, use optional `--common-args`
with `["--planner-effort", "medium", "--critic-effort", "medium"]`; the generated
default planner effort is high. This does not change the already-running controller.

From the research repository, the command syntax is:

```bash
python3 -m scripts.kernel_rnd.autokernel.loop.serial_run \
  --target-args /absolute/inputs/glm-cpu.args.json \
  --target-args /absolute/inputs/canonical-gpu.args.json \
  --batch-iterations 1 --rounds 0 \
  --state-dir /absolute/dedicated-serial-state
```

Each input is a JSON array of existing `loop.run` arguments, not a new enrollment
format. These examples are **templates, not installed launch authority**: replace
`/absolute/...` paths and target IDs with the original owned inputs. Do not launch
against a worktree/store whose existing owner is still running.

`glm-cpu.args.json` (historical example: GLM-5.3-Flash and its `llama.cpp-experimental-glm53-*`
worktrees were deleted 2026-09-22, so these paths no longer resolve; substitute the current CPU
target's inputs):

```json
[
  "--resolved-campaign", "/absolute/inputs/original-resolved-campaign.json",
  "--target-id", "ORIGINAL_CPU_TARGET_ID",
  "--worktree", "/mnt/raid0/llm/llama.cpp-experimental-glm53-champion-20260909",
  "--experimental-branch", "ak/champion-glm53-candidate-20260909",
  "--anchor-build", "/mnt/raid0/llm/tmp/glm53-validation-20260908/champion-candidate-c463f601b",
  "--cpu-serving-launch", "/mnt/raid0/llm/tmp/aku12a-glm53-five-loop-inputs/glm53-c463f601b-cpu-mtp-depth3-b2048-ub512-corrected.recipe.json",
  "--frozen-prompts", "/mnt/raid0/llm/tmp/aku12a-glm53-five-loop-inputs/glm53-fixed2029-depth3.prompt-manifest.json",
  "--store", "/absolute/original-cpu-store",
  "--belief-root-repo", "/mnt/raid0/llm/worktrees/mains/autokernel-unified-20260908",
  "--worker-root", "/absolute/cpu-worker-worktrees",
  "--worker-build-root", "/absolute/cpu-worker-builds",
  "--pairs", "5", "--workers", "1",
  "--planner-model", "gpt-5.6-sol", "--planner-effort", "medium",
  "--critic-model", "gpt-5.6-sol", "--critic-effort", "medium"
]
```

`canonical-gpu.args.json`:

```json
[
  "--resolved-campaign", "/absolute/inputs/original-resolved-campaign.json",
  "--target-id", "ORIGINAL_GPU_TARGET_ID",
  "--worktree", "/mnt/raid0/llm/tmp/champ2",
  "--champion-branch", "ak/champion/llama-cpp-ffc1bac82eec",
  "--anchor-build", "/absolute/original-verified-current-gpu-build",
  "--cor-build", "/absolute/original-verified-champion-of-record-build",
  "--store", "/mnt/raid0/llm/autokernel/loop-memory",
  "--worker-root", "/absolute/gpu-worker-worktrees",
  "--worker-build-root", "/absolute/gpu-worker-builds",
  "--surface", "tg128", "--pairs", "5", "--workers", "1",
  "--serving-recipe", "/absolute/inputs/original-gpu-serving-recipe.json",
  "--serving-pairs", "5",
  "--planner-model", "gpt-5.6-sol", "--planner-effort", "medium",
  "--critic-model", "gpt-5.6-sol", "--critic-effort", "medium"
]
```

The selected model comes from original enrollment. CPU launch and frozen requests
must match it. The GPU example above remains explicitly `legacy_gpu_screen`;
selection alone does not turn that screen into exact enrolled serving execution.
For explicit GPU serving, use `--gpu-serving-launch` with the original canonical
resolved GPU launch and `--frozen-prompts`; `--gpu-calibrate-serving N` is the
optional request-bound first-batch calibration. The roster mode derives that
explicit serving route. An experimental GPU branch is a candidate, not the
canonical champion; declared host CPUs/build jobs and the supported GPU route are
checked and used by the existing owners. In particular,
the retained `build-fold-ef81196d5` directory without original provenance is not
made ready by this example. Never fabricate provenance or add an anchor waiver.

For a **future** direct CPU start or its serial target argument file, explicitly pass
`--belief-root-repo /mnt/raid0/llm/worktrees/mains/autokernel-unified-20260908` to load
the installed serving-observation reader. `EPYC_ROOT_REPO` is the environment fallback;
the final `/workspace` fallback may be stale on this host and is not proof the reader
is installed. Wrong/missing reader code is reported as unavailable, not silently connected.
The loop incrementally ingests exact new receipts into its own store's
`serving-beliefs/feedback-ledger.jsonl` and joins original source facts to the existing
fold/query status. Model/recipe/request/epoch/current-anchor scope is mandatory for
numeric context; an unresolved legacy GPU subject does not acquire that scope by name.
Historical experiment recall remains available independently, including nulls and
pre-hook records. Observation status is not a qualified gain or permission to keep.
Owned-target rosters automatically add canonical and sibling stores as read-only
historical suggestions. Standalone runs may repeat `--shared-history-root PATH`.
Each context reads at most eight stores and five suggestions per store, rotates
across serial batches, and reports omitted/unavailable sources. Useful keeps and
measured outcomes have reserved selection slots, so planner transients cannot bury
them. Original model/quant/recipe/surface and caveats remain visible; structured
cross-scope magnitudes are redacted, and these suggestions do not enter the local
characterised-mechanism pool or establish transfer. Existing records are not rewritten.
This option does not reload an existing PID: the current trial has not been restarted
to load these hooks, and real post-hook hardware/live-ingest proof is still outstanding.

Use distinct target worktree/store/worker roots and a separate routing state
directory. The wrapper owns `--iterations`, `--out` and `--resume-run`; do not
put them in target files. Positive `--rounds N` runs N roster passes; 0 keeps
rotating but exits if every target fails. Failed targets are not repeatedly relaunched.
Each batch keeps its own full result and logs; canonical history stays in the
original GPU store. Router status names the active target and its original store.

When targets share an experimental worktree, a retained source keep can schedule an
explicit validation stage against another target's original baseline. It uses the
existing scheduler and resource accounting; pending validation permits ordinary
research before retrying. The original serving/FOLD-2 non-regression rule applies.
An exact original keep observation can be reused; a different assembled source or
build is remeasured. Validation records and original belief receipts are retained.
This path does not yet combine distinct CPU/GPU worktrees or promote a final unified
canonical champion. Those are separate completion requirements, not inferred passes.

After completed matching measured-search batches, the serial owner forecasts stage
duration from the original held intervals (empirical p75 of at most8 observations).
The estimate is scoped to the target, inputs, source, runtime recipe, CPU geometry
and accounting epoch; absent or incompatible history retains the configured estimate.
Failed or interrupted attempts still cost budget but do not train a shorter successful
estimate. This is cost learning, not scientific reward weighting. Existing coverage,
seed opportunities, accounting and maximum stage bounds remain authoritative.

For a new CPU workload with no matching floor, the existing optional
`--cpu-calibrate-serving N` may be supplied for its first batch. Omit it when
reusing an original matching floor. On later visits the wrapper reopens that floor
and the actual retained current/COR builds; switching alone does not trigger an
anchor rebuild or recalibration. Normal hypothesis builds still occur. Original
recipe/request bytes and the existing provenance checks remain required.

To stop, create `STOP` in the routing state directory, or signal the captured
wrapper PID with SIGTERM/SIGINT. It signals only its captured child and waits for
the existing owner to drain. STOP persists across wrapper restarts. **STOP is not a between-batches drain:** the
wrapper forwards SIGTERM to the running child at once, so a forming lane (e.g. an in-flight planner call) is
abandoned (measured 2026-09-25, DS41-C28). To stop between batches, use the control plane's `pause` (below) or a
bounded `--rounds N`. What a stop does to an actor call already in
flight changed at research `21ca61b0`; see *Launching and stopping a DS41-style serial run* below. Exit 0 without
the same-target, same-input terminal continuation is not a successful batch.
An unreconciled active batch refuses automatic relaunch rather than overlapping
an unknown child. No broad process-name kills are part of this CLI.

Optional authenticated controls use `--control-listen 127.0.0.1:PORT` and
`--control-origin http://HOST:8100`, with `AUTOKERNEL_CONTROL_TOKEN` supplied through
the environment. The existing `/snapshot` and `/commands` HTTP routes are reused.
Command schema `epyc.autokernel.serial_command.v1` carries `config_digest`, `owner_id`,
`request_id`, `operation` (pause/resume/drain), `expected_revision`, `expected_batch`,
and `expected_target`, taken from the current snapshot. Retry an uncertain request
with the same ID and payload. Tokens are never written to status. No listener starts
unless configured. The existing loop dashboard's serial-routing card exposes the
buttons when a fresh original owner publishes this listener. Use HTTPS or a localhost
tunnel, enter the reachable control endpoint and token, and configure the listener's
exact trusted origin accordingly. Tokens stay only in tab memory. A malformed control
block disables controls without hiding valid measurements. After an owner restart,
an old uncertain command is reported but never replayed to the new owner.

Pause completes the current batch and its resource accounting before waiting without
a child or claims. Resume permits the next selection; drain uses the original stop
path above. An accepted command is not necessarily completed: inspect its outcome.
Failed cleanup cannot report a completed drain. A persisted pause is not cleared by
restart; configure the listener/token again to resume, or use STOP to finish without
resuming. Ordinary invocations without controls retain their existing behavior.

A direct single-target restart may pass
`--resume-run /absolute/prior-batch/loop-continuation.json` with the same original
inputs; the loop loads and verifies the actual retained current/COR builds. Without
that file, a restored COR differing from the current anchor requires its original
`--cor-build`: the current build cannot be relabelled as the old COR.

The published connector has hermetic rotation/keep/resume/STOP coverage, not a live
CPU/GPU serial-hardware acceptance result. Production promotion and scientific
qualification remain with the existing owners.

### Launching and stopping a DS41-style serial run (measured 2026-09-24)

These lessons come from DS41 runs 7 and 8 (`handoffs/active/deepseek-v41-flash-evaluation.md` DS41-C10, C20,
C22). The code is research main `21ca61b0`.

- **Launch from the research root with `PYTHONPATH=.:scripts/kernel_rnd:<orchestrator checkout>`.** The loop's
  modules import the `autokernel` package directly (e.g. `census.py`: `from autokernel.controller import
  workload_contract`), so without `scripts/kernel_rnd` on the path the launch fails at import. Run 8's exact
  command is recorded under DS41-C10.
- **`EPYC_ROOT_REPO` must name a root checkout that carries the VB-AK-SEAT contract**
  (`scripts/vidya/adapters/autokernel_actor_seat_capture.py`). Every actor call's `actor-calls.jsonl` line is
  built by that module. Without it, the line keeps the pre-hook shape plus a `v1_refused: <why>` field and
  projects no claim. A lane worktree used this way is frozen for the life of the run (DS41-C24).
- **Do not trust the dry-run floor banner.** Before run 8, `serial_run --dry-run` printed `request-bound floor
  None [absent]`, yet the live run loaded the store's cached floor (5.097) and did not recalibrate. Check the
  store for the cached floor instead of relying on the banner.
- **Never fast-forward the shared research clone while a serial run is live.** Each new batch's `run.py`
  imports from that clone, so a mid-run fast-forward mixes code versions across batches (the DS41-C19
  mechanism). Land new loop code between runs.
- **Stop semantics.**
  - **Before `21ca61b0`:** SIGTERM/STOP is a graceful drain. A planner or critic call IS a forming stage, so the
    drain waited out the whole actor call. An actor that was TERM'd (rc −15) was retried as a transient, so
    `run.py` launched a new one. Stopping run 7 took TERM on the actor, then KILL on `run.py` and `serial_run`.
  - **From `21ca61b0` (DS41-C22):** a stop TERMs the in-flight actor's whole process group, then KILLs it after
    15 s. It raises `ActorStopped`, recorded as `stopped_mid_formation`, and is never retried or backed off.
  - **rc < 0 with no stop asked is still retried, by design.** Killing one hung actor must not end the run.
  - Only forming stages make actor calls, so a lane holding the serialized tail still finishes its A/B.
- **Actor seat.** `--actor-seat plain` (bare `opencode run`) is the default, per the DS41-C20 A/B: plain 31.9
  min vs bounded 44.3 min on one proposal, both schema-valid. `--actor-seat bounded` (per-run opencode config,
  output-capped MCP tools, step cap) is opt-in; its deficit was attributed to perf-tool time, which is now
  doubted (the cache measures 1.3 s per uncached call; DS41-C20d). The pitfalls of
  driving `opencode run` headless are listed in
  [`docs/reference/harness-candidates/opencode-p03-audit-20260916.md`](../../reference/harness-candidates/opencode-p03-audit-20260916.md) →
  *Addendum 2026-09-24*.

**Added from run 9 (2026-09-24/25, research `6afc7eed` then `30631761`, anchor `5a60152ae`):**

- **Loop order after an anchor change.** The pre-launch plan assumed both floors calibrate back to back
  (~8.5 h), and that was wrong. The real order is:
  1. The half-screen floor (cores 0-47, `-t 48`, 48 `matched_process_v2` launches, ~4.7 min each, ~4 h).
  2. **Batch 0's half-screen PROPOSAL and its measurement.** This includes a planner call, which ran 61 min in
     run 9.
  3. **Batch 1's full-target calibration** (cores 0-95, ~4 h, every CPU region lock).

  So an off-hours launch at ~20:00Z puts the full-target calibration, and its frontdoor (:8070) impact, well into
  the next morning. Plan the window around step 3, not around "calibration". Floors persist per anchor in
  `store/runtime-source-floors/`, so a relaunch on the same anchor goes straight to the planner (DS41-C28).
- **A store whose champion of record (COR) is not the anchor refuses the launch**, and the dry run does not
  check it. Run 9's first attempt was refused because the store's COR was the old port anchor `ebb68dc55`, with 0
  keeps and 1 experiment row. The route the operator approved follows the DS41-C13 precedent:
  - archive the store (`store-run8-cor-ebb68dc55/ARCHIVED.txt`);
  - start a fresh store, carrying over `inbox/`;
  - keep the refused state dir (`state-run9-refused-cor`).

  Until the dry run checks COR against the anchor (DS41-C27), compare them by hand before an off-hours launch.
- **`EPYC_ROOT_REPO`: point it at a detached checkout of root `origin/main`, not a lane**
  (run 9b: `/mnt/raid0/llm/worktrees/root-main-epyc-root-repo`). Refresh that checkout between runs, never
  during one.
- **The DS41-C22 stop path works on a live actor call.** Run 9 was stopped 61 min into a planner call. TERM on
  `run.py` and `serial_run` ended everything, including opencode, and freed the CPU locks with no KILL. The first
  `actor-calls.jsonl` line was an `actor_call.v1` with rc −15. A stop *during calibration* still needs DS41-C26.

### Operating lessons from runs 9c-10 (2026-09-25)

From DS41 runs 9b-10 (`handoffs/active/deepseek-v41-flash-evaluation.md` DS41-C28 to C33). Research code:
`c7215eb5`, `1ef55655`, `71c46655`, `67cac838`.

- **Never idle the compute.** Nothing else on this host uses the CPU besides AutoKernel (operator, 2026-09-25).
  - Never hold or stop a campaign for "off-hours". DS41-C28's daytime premise cost 04:26Z → 07:15Z of idle CPU.
  - Run GPU-only experiments (A/Bs on :8083) concurrently with the loop, and alternate arms so both see the noise.
  - Pausing IS allowed for planner/orchestrator A/Bs: pause cleanly, run the A/B, relaunch right after.
  - Before relaying an approved sequence that idles compute, say what it idles and for how long.
- **Stop between batches with the control plane, not `STOP`.** `STOP` forwards SIGTERM at once (above). Launch
  every serial run with `--control-listen 127.0.0.1:PORT --control-origin http://HOST:8100` and
  `AUTOKERNEL_CONTROL_TOKEN` from a mode-0600 file, as runs 9d and 10 do (`127.0.0.1:8471`, token
  `/mnt/raid0/llm/tmp/ak-ds41-control-token-run<N>`). Then pause by posting an
  `epyc.autokernel.serial_command.v1` built from the current `/snapshot`.
  - **A pause lands only when the current batch ends.** A full-target calibration batch runs for hours: run 9d's
    pause, requested at 12:27Z, was still `pausing` when the run was killed at ~14:40Z. For a prompt stop, TERM at
    a forming stage (the DS41-C22 path); never mid-measurement.
- **Run a campaign from a dedicated research worktree, never the shared clone.** `serial_run` spawns a fresh
  `run.py` per batch from its code root, so the code root must not move for the life of the run. The shared clone
  moves: it is fast-forwarded between runs, and on 2026-09-25 a peer's uncommitted `actors.py` edits blocked its
  fast-forward altogether. Run 10 runs from `/mnt/raid0/llm/worktrees/research-ds41-run10`, a detached checkout
  of research `origin/main` (`67cac838`). New loop code lands by relaunching on a fresh worktree, and the old one
  is removed only after its run is dead. This retires the "never fast-forward the shared clone mid-run" hazard
  above instead of managing it.
- **A stop no longer loses the candidate.** `--resume` is on by default (`1ef55655`): a relaunch re-queues
  critic-accepted-unbuilt patches to build and interrupted authors to author, re-validated and at most once. A
  harness fault releases the claim with a retry count (`71c46655`), and `resume reopen <row>#<n> --apply` re-opens
  a consumed claim. A resume needs the same store; a fresh store (a re-anchor) starts empty, so carry retained
  patches into `store/inbox/` by hand.
- **Read the disposition log when a gate refuses.** `gates.op_scope` keyed on markers that exist in one tree only
  and dropped every Q4/Q5 dot-kernel candidate on the DS41 anchor: 0 of ~15 builds across runs 3-9c (DS41-C29).
  Since `c7215eb5` every abandoned candidate is recorded with its retained patch.
- **Model load can dominate a calibration launch.** On the 519 GB DS41 model each launch spent ~3.5 min in a
  single-threaded load, and the host looked ~85% idle during calibration. The fast loader (champion `90c12df42`,
  INC-20260925) cut the launch to 163-170 s from ~282 s. Check the loader's thread count before costing a
  calibration.
- **Thinking is on even when `tokens.reasoning` reads 0.** That field is an accounting artifact: the exports carry
  `reasoning` parts. `--planner-effort high` (opencode `--variant high`) is inert on this server. The planner's
  cost is decode (87%), dominated by long reasoning turns (INF-78 OAB-20 to OAB-23).

## Context as files, per-call metrics, tool-output caching (seat-side, 2026-09-24)

The operator directed these three techniques to be built on the opencode seat as a reduced-scope precursor to the
orchestrator wiring below. They were built on research lanes `ce5800cb`, `0bf2d7c2` and `f4a5d240`, merged to
research main `30631761` (2026-09-25), and the context placement was A/B'd (INF-78 OAB-9, below). The full
write-up and its mapping to OAB-7/OAB-4/R4/S4-T1 are in
`handoffs/active/autokernel-orchestrator-actor-backend.md` → *Techniques learned in the opencode seat*.

**A/B result: context as files LOST on the 27B plain seat** (2 pairs, research `605e8301`,
`artifacts/autokernel_ctx_ab_20260925/`):

| | wall (min) | steps | tool calls | decoded | peak context |
|---|---|---|---|---|---|
| inline | 37.6 / 28.7 | 23 / 24 | 25 / 26 | 52.9k / 43.8k | 104k / 92k |
| variable | 54.4 / 33.6 | 49 / 29 | 54 / 35 | 68.9k / 47.7k | 163k / 118k |

Every call had 0 compactions and a schema-valid reply. The variable arm's first-step context was half the inline
arm's (19.1k vs 40.6k).

What the result teaches:
- **A thin prompt made the model explore MORE, not less.** It read all six file-only sections back, which is
  everything inline carried, then explored lane source further. Moving context out of the prompt does not by
  itself reduce work.
- **The RLM-style benefit presupposes a model or scaffold that pulls precisely.** A 27B left to pull freely does
  not pull precisely.
- **On a 196k slot, compaction is no longer the binding cost.** Inline no longer compacted, so the main predicted
  benefit had nothing to fix. Re-test on a small slot before generalising.
- **The next levers are elsewhere:**
  - fixed overhead (INF-78 OAB-10);
  - the planner reading its own lane and never building (OAB-11);
  - orchestrator-side scouts that pull on the model's behalf (OAB-8).

  Hiding context is not one of them.
- **n = 2 with a fixed inline-first order**, so the magnitudes are soft; the direction held on every cost metric.

**Context as files.** Every byte of an inlined bundle stays in every step of an append-only conversation until
compaction. That motivated this technique, but **the A/B above shows that moving the bytes to files does not
remove them on a model that reads everything back.** Use files when compaction binds (small slot) or when the
reader pulls precisely (a scaffold with pull caps, OAB-12); otherwise inline wins. The mechanics, if you use it:
- **Write the bundle to a per-call directory beside the working tree**, never inside it: a file there rides into
  the authored diff. The layout is sections, per-key JSON, `INDEX.md` with sizes, and a manifest bound to the
  prompt's sha256.
- **Send an index plus a small inline set.** Choose the inline set from evidence — what past replies actually
  cited — and include the this-turn directives.
- **Measured on the DS41 planner prompt:** 26,293 → 5,510 tokens (−79%).
- **Tokenize with the real vocab.** chars/3.5 undercounted by ~30%, because hex digests run at 2.46 chars/token.
- **Keep it lossless and reversible:** the files concatenate back to the inline text, and a failed bundle falls
  back to inline.
- **Know your tool surface first.** The plain opencode seat has no MCP server, only native `read`/`grep`/`glob`/
  `bash`. Reads outside its `--dir` work only under `--auto`, which a read-only critic does not get.
- **Budget the fixed overhead** separately: about 13.2k tokens of system prompt, tool schemas and the working
  tree's `AGENTS.md`.
- **Do not show provenance digests to a planner.**

**Per-call metrics.** Record one efficiency row per actor call as the call happens. Do not recompute it from
exports afterwards.
- **Schema:** `epyc.autokernel.actor_call_metrics.v1`, written as a sibling line to the closed, self-hashed
  `actor_call.v1` record. Do not widen the closed record.
- **Columns:** steps, tool calls by name, compactions, prompt/decoded/cache tokens, first/max context.
- **Define "decoded" once:** output tokens including reasoning.
- **Metrics failure is recorded as `metrics_error`** and never fails the call.
- **opencode export has no per-tool latency, no per-step wall time, and no compaction step.** Say "unknown"
  rather than zero.
- **Scouts are the sessions new since the call began.** Session listings carry no parent/child link.

**Tool-output caching.** Cache a deterministic tool's output keyed by its exact argv plus its input's identity:
path, size, `mtime_ns`, a content hash, the tool version, and a build-id for inputs rewritten in place. A hit is then
the literal bytes of a prior run. Keep client-side knobs such as `limit` out of the key. Keep the cache outside any
integrity-checked directory. Measured: 1.283 s → 0.0012 s, byte-identical.

**Before building a speed fix, check it against the loss it claims to fix.** At 1.3 s per call, the cache cannot
explain the ~12-minute loss it was built for. Measure first.

**Traps (each looked like a model failure):**
- `opencode export` truncates through a pipe (98,304 bytes), so export to a file.
- A compaction summary quotes the reply template.
- `rc=1` can come with a complete reply.
- Gate real-CLI hooks on the resolved binary, not a kind string, or test doubles shell out.
- A planner told "never build" still compiled `.o` files into `/tmp`, and read the anchor build tree instead of its
  lane.

More opencode pitfalls:
[`docs/reference/harness-candidates/opencode-p03-audit-20260916.md`](../../reference/harness-candidates/opencode-p03-audit-20260916.md) →
*Addendum 2026-09-24*.

## Who owns fan-out and context: the orchestrator (operator ruling, 2026-09-24)

**Parallel scouts (fan-out) and REPL-held context are the orchestrator's job. They are not the harness's job and
not the AutoKernel loop's.** Anyone designing an actor, a harness integration or a new loop must not build
either one into the harness or the loop.

Why:
- **Delegation.** Given an allowed `task` tool plus fan-out guidance, the 27B planner never delegated (0 scouts
  in 69 steps).
- **Context.** Every seat arm compacted exactly once however tool output was capped, because an opencode
  conversation is append-only.

What to build instead:
- **Fan-out:** the orchestrator decides the split. For example, one read-only scout per top profile hotspot,
  run concurrently through `repl_environment/parallel_dispatch.py`. The loop sends one request and never
  implements fan-out itself (INF-78 OAB-8).
- **Context:** the context bundle becomes a REPL variable that the model inspects instead of an inlined prompt
  (the RLM pattern). Tool output lands in variables instead of the conversation (INF-78 OAB-7). Its seat-side
  precursor lost the 2026-09-25 A/B on the 27B plain seat, so the orchestrator version must add what the seat
  lacked: exact pull accounting with a byte cap (OAB-12) and scouts that pull for the model (OAB-8).

Long term, the loop calls the orchestrator as a single `Backend`, and the orchestrator owns model choice
(`handoffs/active/autokernel-orchestrator-actor-backend.md`, INF-78).

## Bringing up a new actor model or backend

**Run this checklist before a new actor model, backend kind, harness or seat config takes a live call.**
That covers a local model replacing a cloud one, a new CLI, or a critic moved to another provider.

The DS41 local-planner bring-up took **57.5 h from launch to the first measurement**, and 10 of its 11 runs
scored nothing. Most of the ~26 incidents were harness semantics or latent loop bugs, not the model. A fake
server or a stub finds each of them in seconds; live inference found them one multi-hour run at a time.
Full record: the
[AutoKernel local-actor bring-up retrospective](../../design/autokernel-local-actor-bringup-retro-20260926.md)
(`INC-20260926-local-actor-bringup`).

1. **Wire-test the exact invocation against a fake model first.** Script an OpenAI-compatible stub server and
   drive the **exact** actor command line through it: same CLI, flags, config, env and prompt transport. Assert
   each of these:
   - the full reply survives to a file at full length. A pipe truncated opencode replies at 64-96 KiB, and argv
     prompts hit the 128 KiB limit;
   - both exit-code paths are handled. opencode exits 1 after a *recovered* tool error, with good stdout;
   - a compaction or template echo does not parse as an answer;
   - the timeout covers a deliberately slow reply;
   - a config key does what you think. `prompt:` **replaced** opencode's system prompt, and `instructions`
     appends;
   - requested limits reach the wire. opencode silently clamps `max_tokens` to 32000, and drops
     `chat_template_kwargs` for providers it does not flag as reasoning-capable;
   - **permission semantics hold.** Without `--auto`, an `ask`-class permission is auto-rejected **and ends the
     whole session with no final text**, while a configured `deny` fails only that one call. A read-only seat
     must never be able to reach an `ask` (`b8d6a046`).
2. **Run one end-to-end dry iteration against a fast stub** before a real campaign. Stub the actors, build and
   bench, and exercise:
   - a kill mid-formation;
   - a kill mid-calibration;
   - `touch STOP`;
   - a resume after a mid-build kill;
   - a refused resume, which must yield to the next queued checkpoint;
   - **a keep followed by the next batch.** An experimental campaign that cannot continue past its first keep
     (DS41-C45) is invisible until something is kept.
3. **Never silently discard produced work.** Every accepted hypothesis, authored patch or completed reply that
   is dropped writes a disposition record: what, why, and where the retained artifact is. Enforce this with a
   test that walks every non-fatal failure path, not by convention. Before `c7215eb5`, op_scope silently
   dropped ~15 candidates across seven runs, and none of them ever built.
4. **Key comparability on the measurement identity, not the actor roster.** Resume, planner history and
   do-not-repeat must survive an actor swap (`P-AK-SEARCH-1-A3.1`). Swapping who proposes never invalidates what
   was measured.
5. **Give free compute an explicit budget.** Every backend and every role needs a per-call decoded-token cap and
   a wall budget that end the call as a recorded abstention, not a transient retry. With a cloud actor the API
   bill was the budget; a local model has none. One planner call ran for 61 min without replying.
6. **Check seeded numeric evidence for freshness.** Any hard numeric ceiling in the campaign inbox carries its
   measurement date and host config. Re-measure it after a BIOS or config change, before it can drive
   autonomous abstention. A stale "~220 GB/s" (the real figure was 399-449) cost 13 batches.
7. **Run the harness's own reference probes in the candidate's env, and test that they work there.** The
   independent CPU quant/GDN oracles were compiled under the candidate's allowlisted launch env, which had no
   PATH, so they reported `oracle_unavailable` ("cannot execute cc1plus"; `7037165f`).
8. **Resolve routes from what the actor actually writes.** A route lookup that needs exact symbols refuses a
   planner-written `Class<...>::method (template body...)` as `unresolved` (`77f8bf58`). Test the lookup with
   real planner output.
9. **Size the per-keep costs you inherited.** Keep anchor builds run at `-j1`, a fix for HIP non-reproducibility
   (R23-40). On a CPU/gcc campaign that costs ~1 h per keep with 95 cores idle, and whether gcc is reproducible
   at `-j64` was never checked (DS41-C46).
10. **Pick the verification scope for the change type.** An actor-only change never needs
    `campaign_cli --verify-artifacts`, which re-hashes the 519 GB model and takes ~2.7 h.

The standing tasks that turn items 1-3 and 5 into gates are INF-78 OAB-29..OAB-32.

## Scratch disk is the flow's job: one registry (operator directive, 2026-09-26)

**All AutoKernel scratch goes through `ScratchRegistry` (`scripts/kernel_rnd/autokernel/loop/scratch.py`).**
This covers temp dirs, per-call configs, context bundles, detached worktrees, non-evidence build dirs and actor
TMPDIRs. No feature allocates disk scratch any other way, and none writes its own cleanup.

Why:
- **Cleanup written per feature leaks.** Each feature cleans up on its own happy path, and a stop, an exception
  or a SIGKILL leaves its disk behind. The actor-context bundles and the per-call opencode configs both
  accumulated this way.
- **Deleting by pattern destroys work.** `git worktree prune` destroyed five live lanes on 2026-08-12, because a
  worktree that is briefly missing looks exactly like one that is gone for good.
- **Shared per-role files race.** The old `actor-opencode-<role>.json` beside the lanes was rewritten by every
  lane, so one lane's call could start with another lane's permission fence.

The shape:
- **Scopes.** `run` → `batch` → `iteration` → `call`. `run.py` opens the run scope in the store and installs it.
  `pipeline.run_pool` opens the batch scope and one iteration scope per draw, on the lane's own thread. Every
  actor call and every actor process attempt is a call scope.
- **Release on exit.** A scope releases everything allocated in it when it exits, innermost first. This holds
  for a normal exit, an exception, KeyboardInterrupt, and the SIGTERM stop path, which unwinds through the same
  blocks.
- **Allocators.** `scope.dir(kind, name)`, `scope.file(kind, name)`, `scope.worktree(repo, base, name)` and
  `scope.tmp_env()`.
  - `iterate()` receives `iteration_scope`. Injected callables find the same scope with
    `scratch.current("iteration")`.
  - Each allocation writes an ownership marker and a journal line (`<store>/scratch/scratch-journal.jsonl`).
- **Sweep.** Runs at the start of every run, batch and iteration. It collects only **marked** resources whose
  owner is provably gone: a dead pid (start time checked against pid reuse), or an earlier run in the same
  process. Retained scratch is collected once `--scratch-keep` is `none`. An unmarked path is never touched.
- **Worktrees.** Removed with `git worktree remove --force`, and only when the worktree is marked. If the
  directory has already vanished, the registry removes only that tree's admin entry, and only after checking
  that the entry's `gitdir` points at the registered path. **Never `prune`, never `gc`:** the git wrapper
  refuses both, and a test scans the package for them.
- **Disk guard.** `registry.ensure_free(bytes)` checks against `--scratch-min-free-gb` (default 50). A `False`
  means the caller **degrades** (best-of N→1, ak-check op-test→compile-only). It never means fail.
- **Retention.** `--scratch-keep {none,failed,all}` keeps a failed iteration's scratch for debugging. It stays
  marked, and the next sweep under `none` collects it.

**Enforced, not advisory.** `test_scratch.py::ScratchInventory` scans the loop package's AST for every call that
creates a file or directory:
- mkdtemp, mkstemp and TemporaryDirectory/File;
- mkdir and makedirs;
- copytree;
- write_text and write_bytes;
- `open(..., w|a|x)` and `os.open(O_CREAT)`;
- `git worktree add`.

Each call must be in `scratch.py` or on a reviewed allowlist, where every entry states in one line why it is
**evidence** (kept on purpose) and not scratch. A new creating call, including one added to an allowlisted
function, fails the test. That test is what stops the next feature from forgetting.

**Evidence is not scratch.** The following stay out of the registry because a record binds them by digest:
- the actor-replies (raw replies, call and metrics logs);
- opencode session exports, bound on `actor_call_metrics`;
- the orchestrator's `*.provenance.json` sidecar;
- LOO omission trees, retained with `deletion_authorized: false`.

The persistent pool lanes are also outside the registry, because they are reused across runs by design.

## Related

- [`handoffs/active/autokernel-rebuild-program.md`](../../../handoffs/active/autokernel-rebuild-program.md) — the program this convention came out of, with the five verified causes.
- [AutoKernel local-actor bring-up retrospective (2026-09-26)](../../design/autokernel-local-actor-bringup-retro-20260926.md) — the 57.5 h bring-up behind the new-actor checklist above.
- [`docs/reference/kernel-freeze-runbook.md`](../../reference/kernel-freeze-runbook.md) — where the custody belongs: the promotion boundary, seven steps, and it shipped v7, v8 and v9.
- `agents/shared/OPERATING_CONSTRAINTS.md` → *Parallel Subagent Fan-Out* — the other place this project writes down a working shape rather than describing it.
