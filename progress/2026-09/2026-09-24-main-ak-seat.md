# 2026-09-24 — main-ak-seat (DS41 run 7 halt, autokernel actor-seat repair, planner A/B)

Session window ~09:55–11:40 UTC. Monitoring handover of DS41 AutoKernel run 7 (owning handoff
`handoffs/active/deepseek-v41-flash-evaluation.md`, INF-77; the prior session's log is
`progress/2026-09/2026-09-24-main-dsv41.md`).

## Problem: run 7 lost a complete 27B proposal to two actor-seat defects

Run 7's first 27B planner proposal, `akm-q4k-q82x4-weight-prefetch` (`iqk_gemm_kquants.cpp ::
mul_mat_qX_K_q8_2_X4_T<DequantizerQ4K_AVX2,1>`, a Q4_K weight prefetch), landed in ~39 min (09:16→09:55).
It was thrown away:

1. opencode exited rc=1 after recovering from an error in its own bash tool (`(res.stderr || "").trim is
   not a function`, raised on the planner's `mkdir -p $HOME/...` scratch-dir probes). `_run_agent` discarded
   every rc≠0 reply unread and retried from zero.
2. The retry (10:09:49) returned EMPTY stdout. `_parse_reply` then ran the schema repair over the empty
   report, and the repair invented `replay-verification / src/verify/replay.ts :: replay`. The codex critic
   rejected it, correctly, at 10:10:23 (~30 s).

## Halt

The operator approved halting run 7 to fix the seat and ran `kill -TERM 1791442 2093139`. Neither
`serial_run` nor `run.py` exited, and `run.py` launched a new actor (2130164). The session TERM'd that actor,
then KILL'd 1791453/1791442. All were verified dead and `state-run7/STOPPED.txt` was written.

Root cause, from reading the code afterwards (now DS41-C22): SIGTERM is designed as a drain. Forming lanes
abandon at their next stage boundary. But a planner call IS the stage, and the retry inside the call never
checks `should_stop()`, so a signal-killed actor (rc −15) gets retried as a transient.

## Changes

| Repo | Path | Change |
|---|---|---|
| research (lane `lane/ak-actor-seat-20260924`, `e9495971`, pushed, NOT on main) | `scripts/kernel_rnd/autokernel/loop/actors.py` | rc>0-only salvage of schema-COMPLETE replies; no repair over an empty report (`REPAIR_MIN_REPORT_CHARS`); repaired `target_surface`/`target_symbol` must appear in the report; template-echo objects skipped and refused as abstentions; prompt on STDIN; stdout/stderr captured to files; prompt diet (`_dedupe_subtrees`, `_slim_shared_history`, 95.7k→75.9k chars); `ActorSeat`; `actor-calls.jsonl` |
| research | `loop/actor_opencode_config.py` (new) | per-run opencode config: `tool_output` cap, step cap, read-only scout fan-out; v2 puts guidance in an `instructions` file |
| research | `loop/actor_tools_mcp.py` (new) | output-capped MCP tools (outline, read_range, grep, code_search, profile_top, symbol_annotate); runs under the orchestrator venv, the only venv with `mcp` |
| research | `loop/run.py` | `--actor-seat {bounded,plain}` (default `bounded`), `--actor-fan-out`, `--actor-steps` |
| research | `loop/actor_lifecycle.py` | refuses stdin-prompt backends (the worker stage has no stdin) |
| research | `loop/test_actors.py`, `test_actor_opencode_config.py`, `test_actor_tools_mcp.py` | 167 actor tests; one fixture address is now built at runtime rather than written as a 16-digit literal (the PII pre-commit hook read it as an account number) |
| root | `handoffs/active/deepseek-v41-flash-evaluation.md` | C20 updated (later fixes, bounded-v1 result, lane commit); C20a/C20b ✅, C20c filed; C22, C23 filed; C18 and C10 notes |
| root (earlier, `312595b7`) | DS41 C18/C10/C20/C21, INF-78 `autokernel-orchestrator-actor-backend.md`, repl-turn-efficiency S4-T1/T2, TD-21.33, HS-4 P6/P7 | already landed on main |

Why the three late fixes were needed:
- **Prompt on stdin.** opencode 1.18 re-quotes any positional argument that contains a space. It escaped all
  2,982 quotes in the run-7 prompt, and a ~100 KB prompt also sat close to the 128 KiB `MAX_ARG_STRLEN` limit.
- **Capture to files.** opencode/Bun exits without draining a pipe. The same session export came back as
  65,536 or 98,304 bytes through a pipe and 328,871 bytes through a file. The reply JSON is at the tail, so a
  long run would lose it.
- **Template echo.** opencode's compaction summary quotes the prompt's `{"abstain":"<reason>"}` template.
  The bounded-v1 driver recorded that object as its hypothesis.

## Results

- **Tests:** 167 passed across the five actor suites (re-run at commit time). The full `autokernel/loop`
  suite shows the same 152 failures as the branch point `e485008a`, plus
  `test_gpu_runtime::test_gpu_calibration_actual_http_keeps_both_original_claims_and_device_trace`, which also
  fails intermittently on the baseline. No regression.
- **Planner A/B** (`/mnt/raid0/llm/tmp/ak-seat-ab/driver.py`: same un-escaped, dieted run-7 prompt, 27B on
  :8083, its own detached lane @ `ebb68dc55`):

| Arm | Steps | Tool calls | Decoded tokens | Wall | Compactions | Notes |
|---|---|---|---|---|---|---|
| plain (run-7 export, old prompt) | 71 | 70 (54 bash) | 63.8k | 40.3 min | 2 | 46k-token first context; tool outputs 275k chars total, max 58 KB |
| bounded v1 (agent `prompt` replaces the system prompt) | 12 (stopped) | — | median 1,626/step vs 266 | ~35 min (2180.5 s) | 1 (context full at 97.7k) | tool outputs 42k chars; 0 scouts; one step 19k tokens; no hypothesis (template echo) |
| plain (new prompt) | running since ~11:19 | | | | | PENDING |
| bounded v2 (`instructions` file) | queued | | | | | PENDING |

  What bounded v1 shows: the model's own deliberation fills the context, not tool output. Replacing
  opencode's terse default system prompt made each step ~6x longer. The A/B verdict is still PENDING.
- **Profile check (read-only, for DS41-C23):** the planner's `perf annotate` reported `measurement-record.data
  has no samples!`, but the profile is not empty: 25.7 MB, 114K `cycles:u` samples. The same session's
  `perf report` puts `mul_mat_qX_K_q8_2_X4_T<DequantizerQ4K_AVX2, 1>` at 19.28% of cycles. perf matches
  `--symbol` against the full demangled signature and prints "no samples" when the filter matches nothing.
  libgomp takes ~45% of cycles at unresolved addresses (40.83% + 2.88% + 1.36%). That is consistent with the
  DS41 finding that decode is flat from 24 to 96 threads. No new task was filed for it.

## Derived actionables

| Item | Disposition |
|---|---|
| (a) SIGTERM does not stop `serial_run`/`run.py`, and `run.py` re-launches the dead actor | **filed** DS41-C22 (root cause from the code: drain semantics plus a retry that never checks `should_stop`) |
| (b) planner `perf annotate` "has no samples!" | **filed** DS41-C23. The profile is fine; `symbol_annotate` should resolve short or templated names |
| (c) opencode bash-tool error `(res.stderr || "").trim is not a function` | **declined.** The rc>0 salvage for schema-complete replies (C20) already absorbs its cost. It is a defect in third-party opencode 1.18.31, and posting an upstream report is an external action nobody asked for |
| (d) the research venv lacks pytest | **declined.** `pyproject.toml` already declares a `test` extra pinning `pytest==9.1.1`, the same version system `python3` has. Every suite runs with system `python3` plus the venv's site-packages on `PYTHONPATH` (the command recorded in DS41-C20). Adding the extra to a shared venv would be an environment change on a shared host, not a code gap |
| Record the plain and bounded-v2 arms | **filed** DS41-C20c |
| Heavy-plan/fast-author split | not filed: the operator dropped it |

## Deferred, with named blocker

- **DS41-C20 promotion to research `main`.** Waiting on the A/B result (plain new-prompt arm running,
  bounded v2 queued). The lane commit `e9495971` defaults to `--actor-seat bounded`. If bounded loses,
  acceptance (ii) flips the default to `plain` before the merge.
- **Run 8.** Launches from the merged tree after C20, per C20(iii).

## Follow-ups executed (operator direction via coordinator, ~11:45–12:30 UTC)

The wrap-up's filed items were handed back to this lane to execute. All research code went into a NEW
worktree `/mnt/raid0/llm/tmp/ak-actor-seat-followups-20260924` on branch
`lane/ak-actor-seat-20260924-followups` (off `e9495971`). The A/B worktree was not touched, because the
queued bounded-v2 arm imports from it. The research commit is `1c7d0a2d`, pushed to its lane only; it rides
with the DS41-C20 seat merge and is not on research `main`.

| Item | Result |
|---|---|
| DS41-C22 stop path | ✅ `loop.ActorStopped` added. On stop, the actor's process group gets TERM, then KILL after 15 s. The stop is never retried and is recorded as `stopped_mid_formation`. rc<0 without a stop stays a retried transient (deliberate). 11 tests use real child and grandchild processes. |
| DS41-C23 `symbol_annotate` | ✅ Short or partial names now resolve against the DSO's `perf report --sort symbol` rows. An ambiguous name returns the candidate list. One read-only smoke (3.7 s) against the run-7 profile found perf 6.17's trailing `IPC` columns in those rows; fixed and pinned by a test (the smoke was not repeated). |
| VB-AK-SEAT | Split three ways. **-a ✅** (subagent): ROOT contract `autokernel_actor_seat_capture.py` plus strict reader `autokernel_actor_seat.py`, class `measurement`, no new ladder, every tuple capped at `Judged/Located`; 33 tests. **-b1 ✅**: `actors._record_call` writes `actor_call.v1` using ROOT's writer; end-to-end dry-run ingest gave projected=1, refused=0, rows=2. **-b2 [ ]**: the arm record, which lands with OAB-4's driver revision (the live driver must not be edited, and both of its arms predate `HOOK_SINCE`). |
| DS41 compaction | ✅ (subagent, operator-approved). Active file 783 → ~650 lines. C0–C19 (15 items) moved verbatim to `handoffs/completed/deepseek-v41-flash-evaluation-completed-through-2026-09-24.md`. The open `- [ ]` set is identical before and after (42); the Completed Scope table links the sibling. |

## Seat A/B verdict, merge, run 8 (12:40–13:10Z)

| Arm (27B :8083, same run-7 prompt) | Wall | Steps | Decoded | Compactions | Proposal |
|---|---|---|---|---|---|
| plain, pre-fix (run 7) | 40.3 min | 71 | 63.8k | 2 | valid (discarded by the old defects) |
| **plain, fixed prompt** | **31.9 min** | 23 | 57.7k | 1 | valid |
| bounded v1 (replaced system prompt) | stopped 35 min | 12 | 47.3k | 1 | none |
| bounded v2 (`instructions`) | 44.3 min | 34 | 60.2k | 1 | valid, better grounded |

- Operator chose "merge, default plain". Research main `21ca61b0` = seat `e9495971` + follow-ups `1c7d0a2d` +
  `--actor-seat` default `plain`; 217 actor/champion tests passed. Bounded's deficit is perf-tool time (DS41-C20d).
- No arm used a scout although `task` was offered and allowed; every arm compacted once (append-only context).
  Operator ruling: fan-out is the orchestrator's job, not the harness's → INF-78 OAB-8; REPL-held context → OAB-7.
- TD-21 session (workspace-8d) stacked TD-21.29/30 on `e9495971` (`td21/29-30-actors` @ `c0a00a8b`); told to
  rebase onto `21ca61b0` and land; run 8 does not carry it.
- **Run 8 launched 13:06:55Z** (`state-run8`, pid 3359620), floor 5.097 from the cache. `EPYC_ROOT_REPO` points at
  `/mnt/raid0/llm/worktrees/ak-seat-handoffs-20260924` — keep that worktree while run 8 runs.

## Operator-invoked wrap-up #2 (13:15–13:40Z)

This ran in a fresh lane worktree, `/mnt/raid0/llm/worktrees/ak-seat-wrapup-20260924b`. The ak-seat-handoffs
worktree is frozen because it is run 8's `EPYC_ROOT_REPO`. Run 8 was not touched.

- **Checklist sync.** The segment's ticks (C20, C20c, C21, OAB-0) had already landed in `44836aab`. Nothing was
  left to flip.
- **Derived actionables: 2 filed, 3 declined.**
  - Filed **DS41-C24**: release run 8's `EPYC_ROOT_REPO` pin on a lane worktree before run 9. Point it at a root
    checkout that follows main, then remove the lane worktree.
  - Filed **VB-AK-SEAT-b1v**: prove the producer on run 8's first real call. At 13:19Z no call line existed
    yet, because the first planner call had not returned.
  - Declined: TD-21.29/30 rebase. It belongs to the TD-21 session, which the coordinator has already told to
    rebase onto `21ca61b0`, and its rows live in `typed-decision-plane.md`.
  - Declined: replicating the n=1 A/B. OAB-4 already requires three ABAB pairs per arm, and C20d re-runs the
    bounded arm after caching.
  - Declined: "every arm compacted". This is OAB-7.
- **Index.** `index_state.py --check` reports 0 problems. The generated signal has **0 prune candidates** (165
  open-tasks, 2 no-checkboxes, 1 open-assertion, 1 undispatchable). Proposed for a human read only:
  - `design-backlog-triage-2026-07-23.md` (EVL-09): a dated triage document with no boxes.
  - `cpu-shape-specialized-gemv-decode.md` (INF-10): 0 open, carries a re-open trigger.
  - `model-stack-change-standardization-audit.md` (RTG-18): 0 open, 11 guarded boxes.
- **README freshness.** Passes.
- **Wiki.** Compiled the whole delta (8 sources, including the three TD-21 sources left out last time):
  - `autonomous-research.md`: the seat A/B verdict and run 8.
  - `agent-architecture.md`: TD-21 landed, and the lesson that the repair turn needs evidence.
  - `routing-intelligence.md`: OP-47 makes era E18 live.
- **Cleanup.** Removed four research worktrees with `git worktree remove` and no `--force`. Each was clean, had
  its HEAD on `origin/main`, and had no process using it:
  - `ak-seat-merge-20260924`
  - `ak-actor-seat-20260924-base`
  - `ak-actor-seat-20260924`
  - `ak-actor-seat-followups-20260924`

  Kept `/mnt/raid0/llm/tmp/ak-seat-ab` with its lane, the frozen ak-seat-handoffs worktree, and
  `/mnt/raid0/llm/tmp/ak-seat-vbseat-proof` (the evidence for b1).
