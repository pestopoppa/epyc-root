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
sole product is an entry in `experiments.md` and a commit on the champion branch, no
agent can spend a week on receipts and call it progress.

**Hypotheses are generated, not selected from a frozen list.** A static portfolio goes
stale exactly when the loop starts working, because every accepted patch moves the
hotspot distribution. Generating against a live profile also dissolves the
do-not-repeat ledger: a planner that reads its own history sees what was tried. Dedup
is a property of having memory, not a mechanism you install.

---

## Operating the existing loop across targets

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
  --batch-iterations 5 --rounds 1 \
  --state-dir /absolute/dedicated-serial-state --dry-run
```

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

`glm-cpu.args.json`:

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
  "--champion-branch", "ak/champion/llama-cpp-0db32c06e3e5",
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
This option does not reload an existing PID: the current trial has not been restarted
to load these hooks, and real post-hook hardware/live-ingest proof is still outstanding.

Use distinct target worktree/store/worker roots and a separate routing state
directory. The wrapper owns `--iterations`, `--out` and `--resume-run`; do not
put them in target files. Positive `--rounds N` runs N roster passes; 0 keeps
rotating but exits if every target fails. Failed targets are not repeatedly relaunched.
Each batch keeps its own full result and logs; canonical history stays in the
original GPU store. Router status names the active target and its original store.

For a new CPU workload with no matching floor, the existing optional
`--cpu-calibrate-serving N` may be supplied for its first batch. Omit it when
reusing an original matching floor. On later visits the wrapper reopens that floor
and the actual retained current/COR builds; switching alone does not trigger an
anchor rebuild or recalibration. Normal hypothesis builds still occur. Original
recipe/request bytes and the existing provenance checks remain required.

To stop, create `STOP` in the routing state directory, or signal the captured
wrapper PID with SIGTERM/SIGINT. It signals only its captured child and waits for
the existing owner to drain. STOP persists across wrapper restarts. Exit 0 without
the same-target, same-input terminal continuation is not a successful batch.
An unreconciled active batch refuses automatic relaunch rather than overlapping
an unknown child. No broad process-name kills are part of this CLI.

A direct single-target restart may pass
`--resume-run /absolute/prior-batch/loop-continuation.json` with the same original
inputs; the loop loads and verifies the actual retained current/COR builds. Without
that file, a restored COR differing from the current anchor requires its original
`--cor-build`: the current build cannot be relabelled as the old COR.

The published connector has hermetic rotation/keep/resume/STOP coverage, not a live
CPU/GPU serial-hardware acceptance result. Production promotion and scientific
qualification remain with the existing owners.

## Related

- [`handoffs/active/autokernel-rebuild-program.md`](../../../handoffs/active/autokernel-rebuild-program.md) — the program this convention came out of, with the five verified causes.
- [`docs/reference/kernel-freeze-runbook.md`](../../reference/kernel-freeze-runbook.md) — where the custody belongs: the promotion boundary, seven steps, and it shipped v7, v8 and v9.
- `agents/shared/OPERATING_CONSTRAINTS.md` → *Parallel Subagent Fan-Out* — the other place this project writes down a working shape rather than describing it.
