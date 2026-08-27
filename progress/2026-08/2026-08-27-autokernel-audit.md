# 2026-08-27 — AutoKernel audit, v27 stop, crash-fix, and v28 launch

**Agent**: operator audit session (ad-hoc, operator-spawned; no roster lane in epyc-root — code
work was done in an epyc-inference-research lane worktree
`/mnt/raid0/llm/worktrees/mains/autokernel-restructure-20260827` on
`lane/autokernel-restructure-20260827`). Self-contained close-out.

## Mandate

Operator: the deepseek-v4-flash opencode session (owning GPU) had spent weeks trying to get
AutoKernel working, had blocked the GPU with its lease, and had nothing to show. Audit it
independently. Then: stop it, remove dead weight, and **get it running** — it must run
autonomously, not as a hand-driven manual loop. Operator then granted this session GPU compute
and directed latching autokernel.

## Findings

- **0 scientific attempts across every campaign v3→v27**, 0 champion promotions, ever. The one
  real result in the period (§22 64-VGPR occupancy cliff) came from a human running two
  `llama-bench` commands; the loop never reproduced it and its catalogue mentions IQ4_XS zero times.
- **Root cause was a self-inflicted restart loop, not a hard kernel problem:**
  1. The planner shells out to `codex exec` (external API). A codex 401 token outage on 08-26
     produced **284 failures in 23 minutes** because the transient path retried with zero backoff.
  2. `discovery_supervisor` forced `max_restarts=0` for `kind==deployment`, so every crash was a
     permanent exit and **the operator became the restart loop** (≥9 hand relaunches in 48h). Since
     recovery mints a fresh sealed deployment, `iterations`/`scientific_attempts` reset to 0 each
     time — which is why weeks of relaunches produced a counter that never moved.
- **v27 crash forensics**: all 11 crashes mapped to raise sites and classified. 4 were the KFD
  residency sampler (including one where it flagged the controller's OWN child, pid 964901, as
  "foreign"), 2 the codex outage, 1 a worktree branch-name collision after a killed attempt.
- **Structural**: ~15-40 LOC of real measurement inside ~278K LOC of custody scaffolding
  ("receipt" ×2735, "authority" ×824 in non-test source); ~49:1 governance-to-science commit ratio;
  the last 15 commits were one subsystem re-hardening itself.
- **Dead-weight estimate corrected**: an earlier static grep claimed ~40K LOC dead. A two-pass AST
  audit found that WRONG — it missed `campaign.py`'s parenthesized import and the
  `scripts/benchmark/` runners; **51 of 82 candidates are live**. 19 modules / 10.5K LOC are
  provably dead.

## Changes

| Repo | Path | Change |
|---|---|---|
| research (lane) | `controller/discovery_controller.py` | planner exponential backoff + streak → `operator_attention`; transport→transient reclassification |
| research (lane) | `controller/codex_container_actor.py` | `DEFAULT_ACTOR_TIMEOUT_S=1800` bounds one actor invocation |
| research (lane) | `controller/discovery_supervisor.py` | lifted the `max_restarts==0` deployment clamp |
| research (lane) | `controller/gpu_residency_sampler.py` | `owner_root_pid` (own subtree ≠ foreign) + `wait_until_clear()` |
| research (lane) | `controller/gpu_source_evidence.py` | optional `preflight_clear` gate before the timed child spawns |
| research (lane) | `execution/worktree.py` | `checked_out_branches()` + guarded `prune_orphan_branch` |
| research (lane) | `controller/discovery_deployment_factory.py` | wire sampler/preflight; resolve the rotted Claude critic pin |
| research (lane) | 3 test files | 6 new tests (sampler ×4, worktree ×2); supervisor clamp test rewritten |
| root | `handoffs/active/autokernel-restart-and-strip.md` | new rider (this work) |
| root | `progress/2026-08/2026-08-27-autokernel-audit.md` | this file |
| runtime | `/mnt/raid0/llm/autokernel/` | v27 STOP marker; v28 bundle + LAUNCH marker; monitor script |

## Results

- **Suite fully green: 779/779.** The 3 long-standing "pre-existing env artifact" failures were
  the rotted Claude version pin and are now fixed too.
- **Disk: 371 G → 589 G free** (144/146 stale autokernel worktrees removed, dirty state backed up).
- **v28 LAUNCHED 14:23Z and advancing** — latched `--max-restarts 1000`, running a closure verified
  to contain the fixes, reached `planner_started` on iteration 1 within seconds with no crash.
- **FIRST SCIENCE AT 15:19Z — `scientific_attempts: 1`.** The milestone no campaign v3→v27 ever
  reached, ~56 minutes after launch. Turn 1 `authoring_refused` (critic caught undeclared
  file-scope symbols — a legitimate gate, no science spent); turn 2 `inconclusive` on
  `akh-v2-q5-type-specific-dequant` with exact attribution **+0.129 %** and target runtime
  **−0.015 %** → conjunctive rule ⇒ inconclusive. A **null result recorded with evidence**, sealed
  as receipt `34f836cc…`. Both arms proved real GPU residency (anchor KFD pid 3623562, candidate
  3623486, both exit 0) through the full stage chain. **Zero crashes**; loop self-advanced to
  turn 3. This also confirms the GPU-path fixes on real hardware: two arms ran back-to-back with
  distinct KFD pids and neither was misflagged "foreign" — the condition behind 4 of 11 v27 crashes.

### Monitoring defect found and fixed (worth recording)

The first monitor watched only iteration-completion fields, so a normal 15-min single-threaded
(`-j1`) HIP build was indistinguishable from a wedge — it produced a false "no progress" reading at
14:55Z while the anchor arm was actively compiling. Compounding it, two of my own diagnostic probes
lied: a `ps | head` truncated away the very processes I was checking for (I briefly and wrongly
concluded the campaign was down), and a `find -newermt` reported "0 files in 10 min" while the build
was writing files that same second. **Lesson, consistent with the observation-window doctrine:
liveness of a long build must be proven by build-tree file activity + a live child process, never by
a phase-boundary state file, and never through a truncating pipe.** Monitor v2 does that, plus
two-sample persistence before declaring a stall, and baselines the science counter so it wakes on an
*increase* rather than on "non-zero".

## Deferred (with named blockers)

- **Lane → research `main` merge**: blocked on the shared research clone having 1,212 dirty files
  from other sessions; merging there now would sweep peers' work. The lane is the source of truth
  and the running closure was staged from it.
- **epyc-root push**: root `main` is 13 ahead / **11 behind** `origin/main` — divergent. Per the
  wrap-up contract I do not force-push or auto-reconcile; the operator reconciles.
- **Dead-weight strip + disk expiry**: filed as open tasks in the rider; not blockers, just not
  this task's scope (the mandate was to get it running).
