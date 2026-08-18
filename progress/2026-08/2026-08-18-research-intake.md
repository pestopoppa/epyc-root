# 2026-08-18 — research-intake — oh-my-pi / omp cohort (stages 1–4)

**Session**: operator-invoked `/research-intake https://github.com/can1357/oh-my-pi https://omp.sh/`
**Outcome**: 13 entries `intake-1148..1160`, all `dive-verified`; 7 handoffs amended, 1 stub created,
1 index row added. Started 2026-08-16, completed 2026-08-18.

## Problem

Two operator-submitted sources on the **oh-my-pi (omp)** coding agent, whose headline claim is that
changing only the *edit tool* — holding model and prompt fixed — lifts coding pass rate by more than
most model upgrades, at zero training compute. The question for us: is that real, and does it bear on
the open HS-4 harness-selection gate or on our own edit/eval paths.

## What the dives found (root cause of the entry-level corrections)

| Finding | Status |
|---|---|
| Grok Code Fast 1 `6.7% → 68.3%` | **CONFIRMED exactly** — 4/60 → 41/60 in the published run reports |
| "+15 pts avg over patch" | **CONFIRMED** — independently recomputed as **+15.61** |
| "3 runs per task, 180 tasks per run" | **OVERTURNED** — all 134 reports are n=**60**; headline cells are single-shot (`Runs per task = 1`) |
| Effect vs `str_replace` (the realistic baseline) | **NARROWED to +2.97 pp** (14/19, sign p=0.064) vs +19.4 pp against `patch` |
| Noise floor | **MEASURED from the author's own 22 repeated configs**: median test-retest spread 3.75 pp, max 17.8 pp; binomial 95% CI at n=60 is ±15.5 pp unpaired |
| Per-line content hashes (the novel mechanism) | **ABANDONED BY ITS AUTHOR** in `30793c165`/`7c6457652` (May 2026) for a file-level 4-hex tag + **plain line numbers** |
| "hashline is line-granularity vs our file-granularity `current_shas`" | **OVERTURNED** — shipped hashline is file-granularity, the same property we already have |
| Diff-XYZ "contradiction" with the harness claim | **DISSOLVED** — the paper disclaims production prediction and is non-reasoning/greedy/single-pass; its "smaller open models" means sub-7B Qwen2.5-Coder (a floor effect) |
| omp HS-4 cooperation surface | **CONFIRMED SUFFICIENT, config-only, no fork** — `compat.extraBody` → `Object.assign(params, extraBody)` |

**Consequence for us**: the effect that survives is "replacing a diff-blob format with a line-anchored
one is worth a lot *for models not tuned to that blob format*". Against `str_replace` it is inside the
benchmark's own noise. Neither this cohort nor Diff-XYZ measures the band of open-weight models we
actually serve — that is unmeasured, not settled.

## Corrections pushed back onto the entries that carry them

Checking the citations deferred at Stage 1 found intake-1150's **prior-art paragraph** wrong in three
places, while its own measurements (already verified) stand untouched:

- `26% → 59%` attributed to GPT-4 Turbo; the aider primary source says that is **June GPT-4**
  (Turbo went 20 → 61), and drops aider's disclosed **72% ceiling** (28% of tasks don't fit 8k).
- A sentence attributed to Cursor's blog ("full rewrite beats aider-like diffs under 400 lines")
  **is not in it** — Cursor says its *eval set* was built from ~450 files under 400 lines. The
  sentence matches the title of aider GitHub issue #625.
- "GPT-3.5 scored 19%" **not located** on either aider page searched — recorded as unlocated,
  explicitly **not** as fabricated.

Also cross-linked onto intake-1148: Cursor **and** aider independently name line-number emission as
the failure mode to avoid, and both predate hashline — whose shipped format moved toward it.

## Changes

| Repo | File | Change |
|---|---|---|
| epyc-root | `research/intake_index.yaml` | +1,834 lines, pure append + in-place dive fields; 13 new entries, all `dive-verified` with `claim_anchors`, `claim_corrections`, `depends_on`, `dive_corrections` |
| epyc-root | `handoffs/active/harness-selection-and-integration.md` | omp candidate row; **HS-1d** `[x]`, **HS-5** `[ ]` |
| epyc-root | `handoffs/active/batched-edit-parallel-apply.md` | **BEP-6** `[x]`, **BEP-7** `[ ]` |
| epyc-root | `handoffs/active/canonical-judge-suite-revamp.md` | **CJ-7a–d** `[ ]` (judge-free suite designs) |
| epyc-root | `handoffs/active/delegation-context-preassembly.md` | **DCP-7**, **DCP-8** `[ ]` |
| epyc-root | `handoffs/active/speculative-decoding-mtp-refresh.md` | **SR-8** `[ ]` |
| epyc-root | `handoffs/active/architect-model-selection-bench.md` | **CAL-1** `[ ]` |
| epyc-root | `handoffs/active/scoring-infra-standardization.md` | **Phase 3 · 3a, 3b** `[ ]` |
| epyc-root | `handoffs/active/optical-context-compression.md` | **NEW STUB** — OCC-1/2/3 |
| epyc-root | `handoffs/active/routing-and-optimization-index.md` | **RTG-53** row (deps `UFH-07, INF-41`) |
| epyc-root | `handoffs/active/master-handoff-index.md` | regenerated rollup counts only |

## Results

- `validate_intake.sh` **exit 0** (1,156 entries, 0 duplicate ids, 0 duplicate arxiv_ids)
- `index_state.py --check` **exit 0, 0 problems** — new stub owned by exactly one row, no orphans
- **Zero deletions** in `handoffs/` apart from the 4 regenerated rollup rows; rollup arithmetic
  reconciles exactly against what was added (+1 / +7 / +6 / +1 across the four domains)
- Checkboxes: **15 new `- [ ]`**, **2 new `- [x] … ✅ 2026-08-18`** (HS-1d, BEP-6 — both settled by dives)

## Two things worth remembering beyond this cohort

1. **`snapcompact` (intake-1159) — optical context compression.** History rendered to pixel-font PNG
   frames read back by a vision model: local, deterministic, **no LLM call**. A zero-inference
   alternative to what `tool-output-compression.md` and `context-folding-progressive.md` do with a
   model call. It ships **without its evidence** — ~70 experiment scripts, zero committed results —
   which is why it is `worth_investigating`, not `adopt`. Now owned by the new stub (OCC-1).
2. **Copilot Arena (intake-1156).** Static code benchmarks rank-correlate with real in-the-wild
   developer preference at **r_s ≤ 0.1** (vs 0.62 for Chatbot Arena coding), over 4.5M suggestions and
   11,604 votes. An external caution on static-suite model ranking — filed as CAL-1 with its
   counter-reading attached (preference may track latency/verbosity, and it measures neither
   correctness nor throughput).

## Two operator declines that were wrong, recorded because the reasoning should be visible

I recommended declining Copilot Arena ("no read-across") and Qwen2.5-Coder ("low relevance"). The
operator overrode both. Copilot Arena turned out to carry the most useful external number of the
session; Qwen2.5-Coder is what makes the intake-1151 correction *checkable* rather than assertable.

## Deferred

**OCC-1 is the only open measurement**: billed-token cost and QA recall for bitmap frames vs raw
text, on a reader we serve. Blocker is a named external prerequisite — a vision-capable local reader
on the live vision path (`multimodal-pipeline.md`, INF-41) — not a decision. Filed as OCC-1/2/3 with
an index row, not left in prose.

---

# 2026-08-18 (part 2) — the guard sweep that came out of the intake wrap-up

**Trigger**: the intake wrap-up's Step-3 pruning surfaced 15 handoffs reporting `open == 0`. Four
spot-checks were all false positives, so nothing was pruned and the heuristic was reported instead.
The operator then directed five follow-on fixes. Seven commits, all pushed to `main`.

## The through-line: guards that matched TEXT instead of EFFECT

Four independently-written guards had the same defect. Each fired on what a command's characters
*said* rather than on what the command would *do*.

| Guard | What it matched on | Consequence |
|---|---|---|
| prune selection (`index_state.py`) | `open == 0` | reads absence of open checkboxes as presence of completion |
| `check_d9_loop_plane.py` | every token after the first `--`, to end-of-string | a chained `; python3 scripts/coordination/...` was swept into the commit's pathspec |
| `check_commit_hygiene.py` | newline-split segments incl. heredoc bodies | a Python heredoc whose *source* contained `git commit` was blocked for a stale fetch |
| `check_live_holder_interference.sh` | raw command regex | a doc heredoc and a `grep` both matched a drop_caches write |

A guard that fires on text blocks the documentation about itself, the grep looking for it, and the
bus message reporting it — and a guard that stalls a session for a reason it cannot see teaches
people to route around it. Routing around a control is how the unguarded direct-commit path D9 was
written to close came to exist in the first place.

## Fixes

| Commit | Change |
|---|---|
| `428c7bb6` | `index_state.py` emits `prune: {candidate, blocker, evidence}` — conservative by construction; 15 candidates → 5. Blockers: `pointer`, `frozen`, `not-a-task-list`, `prose-open`, `no-checkboxes`, `undispatchable-tasks`, `open-tasks`. 11 tests |
| `7e3bab6e` | Archived `tree-draft-forward-port-plan.md` (INF-55). The other 4 candidates reported as live work with evidence |
| `66c9d724` | Archived `moe-aggregate-deployment-wins-brief.md` (INF-39) and `fable5-window2-findings-05b` (INF-14) on operator direction, after verifying every open item has a live owner |
| `a1294552` | D9 asks **git** which paths a commit records: `git diff --cached` (plain) or `git diff HEAD -- <pathspec>` (pathspec), pathspec scoped to the commit's own shell segment. 11 tests |
| `cdbbd761` | commit-hygiene strips heredoc bodies before segmentation; opener lines kept, shell-fed heredocs kept enforced. 4 tests |
| `5202e98e` | Swept all 13 registered hooks; found and fixed `check_live_holder_interference.sh` via `drop_caches_write_scan.py`. 7 tests |
| `2f5a0c63` | Extracted `shell_scan.py`; four scanners now share one implementation. −73/+17 |

## Results

- Prune heuristic: **17 handoffs report `open == 0`, 0 are candidates** after the second tightening
  (`open-section`, `open-assertion`). The screen is not vacuous — the handoff archived in the same
  commit still evaluates to `candidate: true`.
- Three archives, all with routing banners naming where each open item went; 22 inbound links
  repointed across wiki pages, active handoffs and one dated runbook.
- Hook suite: commit-hygiene ✓ · d9 (11) ✓ · live-holder (18) ✓ · worktree (12) ✓ ·
  operator-apply (25) ✓ · agents-reference (3) ✓
- `shell_scan.py` extraction verified as a **pure refactor**: a 22-command corpus through three
  verdict functions, before and after, byte-identical.

## Four corrections to my own work, recorded because the reasoning should be visible

1. **A misattribution found while archiving.** Two active handoffs asserted findings-05b "owns MI210
   residency (Gate R)". It doesn't — 05b is a supplement; Gate R lives in findings-02 (EVL-20).
   Archiving would have turned a wrong ownership claim into a dangling one. Both repointed.
2. **I nearly dropped the `| sudo tee` form** when porting the drop_caches regex: `_SEPARATORS`
   splits on `|`, so the pipe is gone by the time a segment is tested. Caught by probing; named
   regression case added.
3. **The live-holder test suite was passing for the wrong reason.** Every `expect: 2` case *skipped*
   when no region was held — 5 of 5 — while the suite printed "all checks passed". Block cases now
   run under a synthetic flock in an isolated temp dir. 18 cases, 0 skips.
4. **My first D9 verification probe was wrong**, reporting "want 2, got 0" on the real-change case.
   The file was clean, so nothing could be recorded. Re-probed with it dirtied: refuses correctly.

## Deferred, with named blockers

- **`test_hook_worktree_resolution.py` — 2 pre-existing failures** (`test_env_override_wins_over_everything`,
  `test_sparse_worktree_fallback_allows_a_clean_commit_too`). Confirmed pre-existing by stashing this
  work and re-running: identical 2 failed / 6 passed. **Not blocked on anything** — they are simply
  outside the operator's directed scope this session, and are filed as a task rather than left in prose.
- **`git stash` is unsafe in this shared tree while daemons write.** Using it to verify the above
  collided with a runtime file created between stash and pop. All work was intact and the redundant
  stash entry was dropped after verifying all 10 files were present. A checked-out copy is the better
  instrument here.
