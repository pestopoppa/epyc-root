# 2026-10-22 HIL-6j: the HIL-6 pilot entrypoint, AutoPilot exclusion and filler job (coordinator 3c4ca599)

**Operator decision, 2026-10-22, decision tool, verbatim choice "Lift for this pilot only":** lift the
2026-09-16 "no loop run" deferment FOR THE HIL-6 PILOT ONLY. Scope: the HIL-6i first-feature pilot
(`hil6i-first-feature`, HS-4 §3.5 architect delegation prompt), run as calendar-granted filler
job(s). Every other loop, design and schedule stays deferred.

Ground rules of this session: no inference, no pilot run, no server started; no other loop or
schedule touched; orchestrator and root work in fresh worktrees from `origin/main`.

## Landed

| Repo | Commit | What |
|---|---|---|
| orchestrator | `a8551a5b` | `src/harness_loop/pilot_run.py` (the one entrypoint), `src/autopilot_core/mutation_exclusions.py` + PromptForge guards, tests |
| root | this shard's commit | HIL-6j record in `handoffs/active/harness-improvement-loop.md`, plan §7 row, this shard |

Off-repo (`/mnt/raid0/llm/tmp/fillers-3c4ca599/jobs/`): `hil6_pilot_job.sh` (the filler job),
`hil6j_stack_render.py` (renders the private stack from the pinned code), `hil6j_ratify_egress.sh`
(operator-only egress clearance). Pinned job worktree: ``/mnt/raid0/llm/worktrees/hil6j-pilot-a8551a5b` (detached at `a8551a5b`; do not remove while armed)`.

## 1. Entrypoint: `python -m src.harness_loop.pilot_run`

- **Refusals.** It refuses unless `WINDOW_CONFIRMED=1`, `--operator-lift 2026-10-22-pilot-only`,
  `--design hil6i-first-feature` (or its feature id), and the pilot validator passes for BOTH cycle
  designs (`pilot.unmet_requirements` empty; `pilot.CHECKLIST` covers HIL-2 items 1–22). Every other
  design id is refused. `exclude-clear` is the only phase that needs no token, so the EXIT trap can
  always clear.
- **Phases.** `freeze` (zero inference), `preflight`, `run`, `status`, `estimate`, `exclude-set`,
  `exclude-clear`.
- **No scheduler hook and no generic entrypoint.** It is the only `__main__` in `src/harness_loop/`,
  and no module under `src/`, `scripts/` or `orchestration/` names it (test-enforced).
- **Freeze.** It draws the splits once with the pure `first_feature.build_splits`.
  - `exclude_qids` is the union of three sets:
    - EV-19 `wrong`/`scorer_error`, computed in-process with `gold_self_check.classify`;
    - `core_v2` members;
    - a declared "seen within 60 days" rule. No host ledger defines "seen", so the rule is any pool
      id named in a `.json`/`.jsonl` file modified on or after the cutoff under the research
      `benchmarks/results/eval`, `data`, `artifacts` and the clone's `orchestration/reports`. The
      rule is pinned in `freeze.json`.
  - It pins the live target bytes as the control.
  - It refuses if the code-execution scorer is unavailable. Dropping that stratum would be a
    re-design, not a silent shrink.
  - A zero-inference real-pool check took 4.3 s: 846 excluded (837 seen-60d from 17 files, 9
    core_v2, 0 EV-19), and every stratum was full (T1 150, V 420, T2 150, T3 150, TEST 240).
- **Resumable per cycle and per arm.**
  - Every `/chat` outcome is cached in an fsynced JSONL, keyed by arm sha256, qid and run.
  - Proposals, the self-judged choice and each judge chunk are cached too.
  - Steps are recorded in `state.json` and as `hil6j_step_done` journal events.
  - `ResumingLedger` resumes an interrupted attempt rather than reserving its alpha twice. A
    closed attempt is never re-opened.
  - The STOP file and deadline are checked before every uncached request (`PilotStopped`, rc 75).
  - A live-target sha change stops the run for a re-freeze (rc 3).
- **Isolation.**
  - Every request goes through `ChatArmEvaluator`, which arms the fence and refuses a non-`active`
    echo.
  - Arms are full prompt-tree copies under the private API's prompt-root base, with only the target
    replaced (the resolver falls back to constants, not the live tree, for files a root lacks).
  - The proposer view carries trace ids, event names and question excerpts only.
  - The tripwire markers are V/TEST expected answers of 16 characters or more, plus the decoy
    canary.
- **Design pieces wired.**
  - Runs = 2: item keys are `<qid>@r<n>`.
  - `RunMeanSignTest`: per-item run mean, then the pinned exact sign test (α 0.00625, min win share
    54/84).
  - The power gate after the A/A runs (design §7.1). It keeps the declared ψ when the A/A
    discordance is 0, because then the replacement is undefined.
  - Two lineages over two cycles on one journal and ledger; T2/T3 released at commit.
  - Verification modes `with`/`none`/`self_judged` evaluated on arrival.
  - The judge matrix in 21-instance chunks (420 instances do not fit one call). The merged choice
    is the chunk majority, and the zero-LLM argmax check runs on the merged counts.
  - The all-off arm (`allow_delegation=False`).
  - The M9 reference-trajectory arm (diagnostic only).
  - The matched-rollout baseline: k = 8, label-free majority.
  - One paired TEST touch (`final_test_paired`, resumable).
  - Report: Wilson and paired-bootstrap 95% intervals; regression readout
    `hil6i-arch-deleg-regress-v1`.
  - VB-HIL-WRITE `finalize_run` per paired comparison, `protocol_id=None`.
- **Signals the response does not carry.** These are recorded as not captured; nothing is
  estimated:
  - the phase-A decision mode and decision-guard rewrites (log-only in the orchestrator);
  - the resolver provenance.

  `treatment_fired` is "delegated phase A ran" (`delegation_diagnostics.phases_count >= 1`) under
  the arm's root, with `PROMPT_VARIANT*` unset in the private API.

## 2. AutoPilot exclusion

`src/autopilot_core/mutation_exclusions.py` holds the exclusion list.

- **Format and location.** It is a JSON file: `$AUTOPILOT_MUTATION_EXCLUSIONS_FILE`, else
  `/mnt/raid0/llm/epyc-orchestrator/tmp/autopilot_mutation_exclusions.json` (the shared clone's
  git-ignored `tmp/`). It is read on every call, so a restarted AutoPilot is covered.
- **Behaviour.** Entries are owner-scoped, writes are atomic under `flock`, and a corrupt file
  fails closed (every prompt is excluded).
- **PromptForge guards.** They are additive and return early when the list is empty:
  - `list_prompts` omits the target;
  - `propose_mutation` (prompt and GEPA) returns `safety_valid=False`
    (`mutation_exclusion:<target>`) without a CLI call;
  - `apply_mutation` and `apply_mutation_in_context` raise.

  `revert_mutation` is left alone, so a revert can always restore bytes.
- **Who sets it.** The pilot sets the exclusion at the start of `--phase run` and clears it in
  `finally`; the job also clears it in its EXIT trap.
- **AutoPilot was not running** during this work (no process). The shared clone (`8b630d27`) predates
  the exclusion commit, so the job refuses (rc 5) until the clone is fast-forwarded. That
  fast-forward is already pending in `PENDING_ORCH_CLONE_FF.md`.

**Parity:** Base `c69ba5a1` vs this tree, with the exclusion list empty. The logs are in
`/mnt/raid0/llm/tmp/hil6j-wt-20261022/parity/`.

| Check | Result |
|---|---|
| S1 golden | `7748354e…` on both trees, equal to the recorded value |
| S2 golden, corpus pinned | 723 records, 0 differences after normalising the embedded tree path |
| S2 golden, live corpus | 736 records, 0 verdict differences; only the two harness corpus-hash records differ (new `src` files) |
| S3 golden | `8d06aaab…` on both trees |
| S4 SafetyGate replay (same journal copy) | `ab9267bd…` on both trees; pure verdict equals `check()` on 5274/5274 |
| S5 final set (77 files) | 1641 passed / 3 skipped on both trees, identical per-file progress |
| harness_loop and new tests | 107 passed / 2 skipped (EPYC_ROOT environmental skips) |

## 3. Cloud transports

The reference editor (`gpt-5.6-luna`, `codex_exec`) and the judge (`claude-sonnet-5-5`,
`claude_cli`) are both `verified_live: false` in `orchestration/cloud_judges.yaml`. The registry was
not edited.

- **Live verification.** Preflight makes one tiny schema-bound call to each (`{"ok": true}`, no suite
  content). The result goes into `run/manifest.json` under `cloud_live_verification`. A failure
  is BLOCKED (rc 5).
- **Call count** (upper bound, printed at preflight): **84**, made up of:
  - 2 preflight calls;
  - 2 codex editor proposals (1 per cycle);
  - 80 claude judge chunks (20 per lineage-cycle with survivors).
- **Egress.** Content leaves the host only under an operator-issued clearance file
  (`/mnt/raid0/llm/tmp/hil6j-pilot/egress_clearance.json`, written by `hil6j_ratify_egress.sh`).
  Without it, preflight is BLOCKED (rc 5) before any server starts. Design §5 names this as the
  operator's step before any run.

## 4. Local editor and private stack

- **Local editor.** `Qwen3.6-35B-A3B-MTP-Q8_0` on the private frontdoor server :18982. The same
  server is the `worker_general` delegatee, as in production. Every editor request sends
  `chat_template_kwargs {enable_thinking:false}`, and an empty reply fails loudly.
- **How the stack is rendered.** By production's own `build_server_command` from the pinned code,
  with private ports, `-t FILLER_THREADS`, a private `--slot-save-path` and `--cache-ram 4096`:
  - architect_general :18981;
  - architect_critic/coder_escalation :18983 on the MI210;
  - a private uvicorn API :18980 with every role URL private.

  The API also runs with the fleet and placement flags off and every state directory redirected.
- **Each server:**
  - `ram_admit 160` first;
  - store v10 builds with their own `LD_LIBRARY_PATH` plus `verify_ggml_linkage.sh`;
  - own-PID port proof;
  - `--reasoning off` and the first-reply preflight on architect and frontdoor;
  - verified-dead teardown.
- **Coder exception.** The coder keeps production's registry-declared thinking setting
  (`disable_thinking: false`), which is the pre-registration exception of rule 15.

## 5. Filler job and dry run

`hil6_pilot_job.sh`:
- pins the orchestrator code at the sha in a dedicated worktree, and refuses a dirty tree and a
  `src` that resolves outside it;
- freezes once, then runs preflight, the stack and the pilot;
- writes COMPLETE only when the report carries the TEST touch (`ENDED_UNDERPOWERED` when the power
  gate stops it);
- passes `bash -n`.

**Dry run** through `filler_run7.sh`, with a fake grant, a fake region-lock and fake backends
(`/mnt/raid0/llm/tmp/hil6j-wt-20261022/dryrun/`):
- Window 1 (deadline already past): rc 0, resumable stop before the first request, exclusion
  cleared.
- Window 2: full pilot with 9,150 fake requests and 82 fake cloud calls. COMPLETE, then the launcher
  marked the row COMPLETE. No exclusion file was left behind.

Unit tests: `test_harness_loop_pilot_run.py` 17/17 and `test_hil6j_mutation_exclusions.py` 7/7.

## 6. Wall time (ESTIMATE, low confidence)

- **Request count:** 14,850–19,230 `/chat` requests. Upper and lower bound depend on commits, and on
  whether the verification modes pick other arms.
- **Per-request time:** about 56 s mean. No delegated `/chat` latency exists for Flash-Next. The
  means are set above the medians of the March–April 2026 delegated runs and the 2026-09-23
  Flash-Next direct bench. Concurrency is 1, because architect_general serves one slot.
- **By phase:**

  | Phase | Hours |
  |---|---|
  | Cycle 1 (incl. A/A and diagnostics) | ~162 |
  | Cycle 2 | ~116 |
  | TEST | ~23 |
  | **Total** | **~232–300** |

  Add 15 minutes of bring-up per window.
- **Over-run rule:** a run beyond 1.5× is an owner duty to explain.
