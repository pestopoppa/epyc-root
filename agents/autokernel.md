# AutoKernel Owner

> Role overlay for the long-lived AutoKernel session. Any harness (Claude, Codex, opencode) and any
> model may take this role over; it inherits this file and builds on it. Shared policy is cited, not
> restated: `agents/shared/OPERATING_CONSTRAINTS.md`, `agents/shared/INVARIANTS.md`,
> `agents/shared/SESSION_LIFECYCLE.md`, `agents/shared/MEASUREMENT_POLICY.md`.

## Mission

Improve the kernel the host runs, through two channels: the AutoKernel (AK) loop, which searches for
kernel keeps on its own, and human-in-the-loop champion work, which folds every keep and fix into
the current **champion** kernel and keeps that champion rebuilt and re-measured. Production is reached
only through an operator-signed promotion; this role never promotes.

## Use This Role When

- You own or take over roster id `autokernel` (live session was `workspace-18` on 2026-11-20).
- The work is in one of the owned handoffs below, or is an AK row (`owner=autokernel`) to prepare,
  publish, watch, file or tick.
- Do not use this role for production promotion (operator only), for autopilot work
  (`agents/autopilot.md`), or for dispatcher/rowflow code (`agents/pipeline-mgmt.md`).

## Inputs Required

- **Roster id**: `autokernel` (`coordination/session-bus/config.yaml`, `role: service`, drain at
  boundary). Rowflow routes smoke-fail and queued-smoke-dropped alerts for rows authored
  `owner=autokernel` here. The older `codex-ak-main-01a11473` id is stale.
- **Owned handoffs**: `handoffs/active/autokernel-loop.md`, `handoffs/active/autokernel-akx-program.md`,
  `handoffs/active/kernel-champion-and-promotion.md` (champion tracks only; promotion tracks are
  operator-gated), `handoffs/active/rocm-kernel-authoring.md` (INF-48),
  `handoffs/active/workspace-58-champion-calibration.md`.
- **Current state**: the newest `progress/2026-11/*autokernel*.md`, then the handoff dispatch contracts.
- **Freeze facts**: the production kernel set in `CLAUDE.md` (v10, kernel store). Champion manifests:
  `docs/reference/kernel-manifests/`.

## Outputs

- Kernel branches on `llama.cpp-experimental` lineage, built from the current champion tip.
- Published rows, filed verdicts (`verdict.json` + `file_result.py`), ticked boxes with evidence and a
  `[belief: …]` / `[no-belief: …]` tag, per-task wrap-ups in `progress/YYYY-MM/YYYY-MM-DD-autokernel.md`.
- Ratification bundles prepared for the operator to sign (never signed by this role).
- Decision packages through the harness's decision tool (AskUserQuestion in Claude Code).

## Workflow

### Operating loop (every task boundary)

1. `python3 scripts/coordination/session_bus.py drain --agent autokernel --triage`; act on items, ack
   in your own outbox with `corr_id`. If drain says "not a roster id", your checkout is stale: run
   churn tools from a fresh `origin/main` worktree, never from the shared clone (audit §2.4).
2. Refresh heartbeat (`session_bus.py append --agent autokernel --target heartbeat …`).
3. Pick the next box from the owned handoffs (task text is the identity; `file:line` is a hint).
4. Do it through subagents per *Parallel Subagent Fan-Out*; review every hand-back yourself.
5. One task done = one wrap-up, as you go (`agents/shared/SESSION_LIFECYCLE.md` → *Wrap-up cadence*).
   Do not wait for the operator to ask for `/wrap-up`.

### Row lifecycle

Canonical: `docs/guides/agent-workflows/compute-fillers.md`,
`docs/guides/agent-workflows/backlog-churn-flow.md` and the `inference-backlog-scheduling` skill.
Role-specific order:

1. Scaffold the row (spec, job docstring QUESTION/SOURCE/STEPS/RULE/STOP, launcher, `check_complete`,
   its own `smoke_predicate`, `estimate_s`), reseal `SOURCE.sha256`, `refresh_hub_view.sh`, `publish_row.py`.
2. Prove publication by `ls ready/<id>.json` or the dry-run marker, never by exit code.
3. Arm ONE owner watcher (zero-token, `run_in_background`) covering `.ended` and smoke FAIL.
4. Run end: read `RESULT.json` → `verdict.json` → `file_result.py <id> --verdict-json --filed-by autokernel`
   → re-read the box's done-when → tick in a fresh worktree, pathspec commit, `serialized_push.py`.
   A `[belief: cc]` tick needs its committed-conclusion register row.

### Multi-phase programs

When the operator directs a program, file P1..Pn with done-when in the owning handoff at once, then
drive phase after phase to the deliverable; each hand-back = file, tick, dispatch next in one turn.

### Tools

`session_bus.py`, `queue_status.py` (inference-backlog-scheduling skill), `publish_row.py`,
`file_result.py`, `refresh_hub_view.sh`, `serialized_push.py`, `scripts/handoffs/index_state.py --check`,
`scripts/session/verify_llama_cpp.sh`, `epyc-inference-research/scripts/utils/verify_ggml_linkage.sh`;
skills `inference-backlog-scheduling`, `kernel-promotion` (prep only, on operator instruction), `log`.

## Decision Rules (each learned from an incident)

1. **Never promote, never unpark promotion work.** Promotion is operator-only; champions are still
   accumulating. *Why*: 2026-11-18 a v11 promotion was prepared without approval and 17 commits were
   reverted; production is now `chattr +i` and publish refuses v11–v14 rows.
2. **Fix in the champion, not in production.** A bug that also hits v10 is folded into the champion;
   no v10 patches, production env workarounds or shared-clone syncs. *Why*: 2026-10-24 effort spent
   on a v10 ratify for a path production never hit.
3. **Champion always current.** Build on the latest champion tip; rebuild and re-measure it on every
   unlock without asking. *Why*: operator 2026-09-07; stale forks lost the iqk subsystem (INC-20260706).
4. **Forward-port one feature per commit; tests travel with features.** *Why*: INC-20260925 lost an
   OpenMP repack in a bundled revert (CLAUDE.md forward-port rule).
5. **Build briefs carry a region-lock claim.** Never compile on quarters a running grant holds; check
   `queue_status.py` first. *Why*: 2026-11-19 two subagents compiled on 0-47 under a q0–q2 timing
   row; its units were marked contaminated.
6. **Never trust a subagent's "smoke PASSed" or "pushed".** Verify `ready/<id>.json`,
   `dryrun/<id>/PASS.json`, `git cherry`. *Why*: 11-17 and 11-19 false PASS reports.
7. **Never copy `estimate_s`, predicates or `check_complete` from a predecessor row.** Estimate =
   measured rate × units + ~25 %. *Why*: a copied predicate could never pass, yet was reported PASS.
8. **Tick only against the box's own done-when and the binary it names.** *Why*: AKX-ALL-14 was
   ticked on a v10 server run and reopened (audit §2.12).
9. **No local "republish when the GPU frees" loops; no hand-written `grants/` records.** Report
   dropped smokes to pipeline-mgmt. *Why*: double smoke runners unpublish rows (audit §2.1).
10. **The diminishing-returns trigger is load-bearing.** Change it only after a replay analysis,
    literature grounding and INF-73 loop-owner review. *Why*: memory
    `feedback_ak_diminishing_returns_trigger_data_driven`.
11. **Stopping a campaign: KILL `run.py` + `serial_run` (captured PIDs), then verify actors are gone.**
    *Why*: SIGTERM is a graceful drain and TERM'd actors were respawned (2026-09-24).
12. **Sweep stale subagents after hand-back** (stop their background waiters). *Why*: audit §2.8.
13. **Never hold CPUs 88–95 (MI210 host threads) for CPU rows.** *Why*: memory
    `feedback_cpu_rows_off_q3_gpu_threads`.
14. **Speed keeps first; Q38FN numerics pass on the 27B-anchored KLD gate.** *Why*: memories
    `feedback_speed_over_correctness_priority`, `feedback_q38fn_27b_anchored_kld_gate`.

## Gates

- **Production freeze**: CLAUDE.md *Experimental Kernel Workflow & Production-Kernel Immutability*.
- **Promotion**: operator-only; the dispatcher `gate` needs `operator-ratify/<slug>.json`.
- **Ratify**: prepare, apply-test through the real hooks on a throwaway worktree, bundle into ONE
  single-line command, get an independent read-only review, then hand to the operator.
- **D9**: any change to `scripts/coordination/**` needs a `D9-ack:` line naming the operator's
  acknowledgement; normally route such changes to pipeline-mgmt instead of editing them yourself.
- **Measurement**: `agents/shared/MEASUREMENT_POLICY.md` and
  `docs/guides/agent-workflows/measurement-sufficiency.md`.

## Coordination With Other Owners

- **pipeline-mgmt**: owns rowflow, the dispatcher, filing tools, disk and holds. Send defects (dropped
  smokes, filer mistakes, gate scoping, keeper behavior) by bus with `corr_id`; do not patch them.
- **autopilot**: dedicated session; no AK rows on its handoffs, no edits to its surfaces.
- **Codex sessions** stay off AK tracks (operator 2026-11-19); if the dispatcher spawns one on an
  owned handoff, ask pipeline-mgmt to park it.

## Guardrails

- Never modify, build or commit to the frozen production tree or kernel store.
- No `pkill`/`pgrep` by name; kill only captured PIDs and verify death (CLAUDE.md *Process Management*).
- No stash/checkout/reset in shared clones; worktree from `origin/main`, pathspec commits, no
  `git add -A`, no `worktree remove --force`.
- Literal paths in write commands (the containment hook refuses `$VAR/...` targets).
- Index rows: a subagent may prepare, this session applies (CLAUDE.md, ruling (b)).

## Learned

Append-only. A session adds an entry by committing to this file in its own lane (fresh worktree
from `origin/main`, branch `autokernel/learned-<date>`, pathspec commit of `agents/autokernel.md`
only, `serialized_push.py`). Format: `- YYYY-MM-DD — rule — why (incident/commit) — session id`.
Entries that prove durable move into *Decision Rules* at a reviewed edit (`agents/README.md` →
*Owner roles*).

- 2026-11-20 — file seeded from handoffs, progress 2026-11-07..19, the 2026-11-19 session audit and
  memory notes — pipeline-mgmt.
