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

### epyc-root divergence reconciled (operator-directed)

`epyc-root` had been unpushable all day: local `main` 17 ahead / 11 behind `origin/main`, so EVERY
session's wrap-up push was rejected non-fast-forward and several sessions' finished work was sitting
un-published. Cause: sessions committing directly to `main` in the shared clone while other sessions
promoted lanes (`codex-inf42-takeover`, `codex-root`) to `origin/main` — neither side reachable from
the other. Not a conflict of content, just two unmerged histories.

Reconciled by merging in an **isolated detached worktree** (never the shared clone, whose working
tree holds several sessions' uncommitted files):

- one conflict, in `handoffs/active/master-handoff-index.md` — purely the **generated** rollup
  counts (473 vs 465 open). Neither side was right: resolved by re-running
  `scripts/handoffs/index_state.py` against the merged tree, which produced `52 | 472` — a third
  value, confirming regeneration was correct rather than picking a side. `--check` → 0 problems.
- superset-verified before publishing: `5fbb38ad..refs/heads/main` and `5fbb38ad..origin/main` both
  `0`, i.e. nothing dropped from either side.
- published **18 commits** to `origin/main` (`725c358f..5fbb38ad`) through
  `serialized_push.py --push` under the push lock — a raw `git push` is correctly hook-blocked here.
  Never forced.

**Left deliberately undone:** the shared clone's local `main` pointer is still 12 behind. A
fast-forward is refused because `wiki/knowledge-management.md` carries another session's
uncommitted edit and is also changed upstream; git aborted atomically and that peer work is
untouched. This is benign — the clone is `ahead=0`, so nothing is unpublished — and any session can
`git merge --ff-only origin/main` once that file is committed or discarded by its owner. **Until
then, sessions committing to `main` in the shared clone will re-diverge**; the workaround that
works today is exactly the pattern used here (detached worktree at `origin/main` → commit → serialized push).

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

## Previously deferred — both since RESOLVED, same session

- ~~Lane → research `main` merge~~ **DONE**: promoted via isolated-worktree merge; research
  `origin/main` = `01f1d2be`, with the sampler fix verified present on main. Future launches get
  the fixes by default.
- ~~epyc-root push blocked by divergence~~ **DONE**: reconciled on operator instruction (below);
  root `origin/main` = `ab970988`.
- **Dead-weight strip + disk expiry**: still open, filed as tasks in the rider. Not blocked — out of
  scope for the "get it running" mandate, and deliberately sequenced after v28 proves stable.

## Operator-invoked wrap-up (15:43Z) — the two deferred operator-cadence steps

Run while v28 continues (turn 4 in flight, `sci: 1`, zero restarts). This was the first
operator-invoked wrap-up since the per-task ones, so **Step 3 pruning** and the **Step 5 wiki
sweep** — which per-task wrap-ups must defer — were finally in scope.

**Step 3 pruning.** The conservative screen returned exactly **one** candidate, INF-40
(`moe-spec-cpu-spec-dec-integration.md`), and it is a **false positive** — do not archive. It reads
prunable only because it has 0 open checkboxes; its actual remaining work is a *pending operator
decision*: the measured architect_critic registry patch (+10.7 % at B=128) is held by the
E8-reseed/**OP-19** gate, stated in prose at line 418 and never as a checkbox. This is the documented
failure shape (a decision living in a handoff body), and it is why the screen is a screen and not a
verdict. Action taken: OP-19's master-queue row amended to name what its non-ruling now costs — a
15-day-old decision is now also parking a measured win. Nothing pruned, nothing archived.

**Step 5 wiki sweep.** `compile_sources.py` reports `total_new: 898` — but `wiki/.last_compile`
has **never existed**, so that number is "no watermark", not "898 uncompiled sources"; the wiki is
demonstrably maintained by hand (32 pages, 27,440 lines, `Compiled Update` sections committed today).
Resolving it by `--touch` would silently assert 898 sources were compiled — the exact silent loss the
routine warns against — so it was **not** touched. Filed as **OP-28** with both options and a
recommendation. What *was* compiled is this session's own knowledge: a new
`## Compiled Update — 2026-08-27` section in `wiki/autonomous-research.md` carrying the generalizable
finding (**an autonomous loop's throughput is bounded by its failure semantics, not its success
path**), with confidence scoped verified-vs-approximate and 5 source references. Page contributes 0
lint errors; all 6 of its link targets verified to resolve.

**Two phantom defects caught by verifying before filing.** (1) `lint_wiki.py` reported 17 errors in
the worktree; 16 were artifacts of `repos/` being an *untracked symlink* absent from every worktree —
the targets all exist in the real clone. (2) The 17th, a dangling
`../handoffs/active/deepseek-v4-flash-0731-dspark.md`, appeared only when linting `/workspace`, which
is 13 commits behind; at current `origin/main` all five references already point to `completed/`.
Both would have become filed-but-nonexistent bugs. **Lint results are only as current as the tree you
run them in — and a worktree is not the deployment tree.**
