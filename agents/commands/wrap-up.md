# Session Wrap-Up

Update all documentation artifacts to reflect work completed in this session, commit changes, **push each affected repo to its remote**, and report the pushed commits.

> **⚠ MANUAL TRIGGER ONLY.** Run this routine only when the operator explicitly invokes `/wrap-up`. Nothing may auto-trigger it — there is no `Stop`/`SessionEnd`/`PreCompact` hook, cron, or nightshift task that calls it, and there must not be one. Autonomous, scheduled, or nightshift sessions **may commit progress directly** (a focused `git commit` of progress/handoff edits is fine and encouraged for checkpointing) but must **NOT** run the full wrap-up routine: it performs index pruning (Step 3) and broad doc/wiki sweeps the operator wants to review on a controlled, manually-chosen cadence. Checkpoint commits ARE however bound by the **checklist-sync gate** in Step 2: any handoff edit that records completed or newly-discovered work must flip/add the corresponding `- [ ]`/`- [x]` checkboxes, not just append prose — the dashboard's progress metric counts checkbox state only.

## Where this wrap-up runs — read before Step 1

**In your own lane worktree, on your own lane branch.** Every roster main owns
`/mnt/raid0/llm/worktrees/mains/<agent>` on `lane/<agent>`
(`scripts/coordination/WORKTREE_MIGRATION.md`; `tmux_adapter.py spawn` puts you there
from the roster's `worktree:` key). Confirm before you start:

```bash
python3 scripts/coordination/check_lane_worktree.py --strict   # 0 ok · 3 in the shared clone · 4 undeterminable
```

**Never `git worktree prune`, and never `git gc`** (it runs one). This repo is reachable at
two path depths that name one directory, so `prune` reads live worktrees as prunable and
deletes their admin data — it destroyed all five lanes at once on 2026-08-12. The lane-entry
check above replaces it; that is the whole hygiene story.

Three surfaces stay in the ONE shared clone and are not lane-isolated, so only they need
serialization: the coordination runtime plane (session bus, `logs/`), the sub-repos under
`repos/*` (symlinks OUT of every worktree — `epyc-orchestrator` and `epyc-inference-research`
are still one shared clone), and the shared-surface steps named in the lease below.

### ⚠ `git commit -- <path>` BYPASSES THE INDEX — this is the collision mechanism

`git commit -- <paths>` commits the **working-tree** state of those paths, ignoring what you
staged. In a shared file that means it sweeps up **a peer's uncommitted hunks in that same
file** and publishes them under your name and message. Proven: commit `dada0bbc`. This is the
exact mechanism behind "parallel wrap-ups interfere with each other".

Lane worktrees dissolve it for ordinary work-plane files (a peer's edits are in *their*
working tree, not yours). It is still live for anything in the shared clone and for the
sub-repos. So, whenever you commit a file another session may be editing:

```bash
git diff -- <file>          # LOOK FIRST. Any hunk here that is not yours will ride along.
```

If the file holds someone else's hunks, do **not** widen the pathspec — stage only your own
and commit the index:

```bash
git diff -- <file> > all.patch           # split out your hunks (or use `git add -p`)
git apply --cached mine.patch            # stage exactly yours
git commit -m "..."                      # NO pathspec: commits the index, not the worktree
```

`git add -A` is forbidden in every shared tree, always.

### The wrap-up lease — for the four surfaces lane worktrees cannot isolate

Most of this routine is now private to your lane. Four things are not, because they are
*generated from, or shared across, the whole fleet*:

| Shared surface | Step | Why it cannot be lane-private |
|---|---|---|
| the master index's generated block | 3 | regenerated from every index; last writer wins |
| `python3 scripts/handoffs/index_state.py` regen | 3 | rewrites `.index-state.json` + `.index-graph.json`, which nobody authors |
| `wiki/source_manifest.json` | 5 | one manifest of the whole repo's sources |
| `wiki/.last_compile` | 5 | one watermark; two writers lose one session's compile |
| the promotion merge to `main` | 7 | two merges racing the same branch tip |

Take a lease around **those steps only** — not the whole wrap-up. Steps 1, 2, 4 and your own
commits need no lease at all, and holding one through them would recreate the fleet-wide
freeze this program exists to remove.

```bash
LEASE="python3 scripts/coordination/serialized_push.py --agent <your-id> --lock-name wrapup"
$LEASE --acquire        # exit 2 = someone else is in their shared-surface steps; wait and retry
#   ... step 3's index regen, step 5's wiki compile, step 7's promotion merge ...
$LEASE --release        # ALWAYS, including on failure
$LEASE --status         # who holds it, since when, and whether it looks like residue
```

**Order inside the lease matters — SYNC FIRST.** A generated file (the index block,
`source_manifest.json`) is rewritten *wholesale from current state*. If you regenerate it on a
lane that has not seen the wrap-up that just finished, your regen is computed from stale
inputs and your promotion overwrites theirs with an older answer — the lease serialized the
writes and still lost one. So, once you hold it:

```bash
$LEASE --acquire
git fetch origin --quiet && git merge origin/main      # 1. build on whoever went before you
#   2. run the shared-surface steps (step 3 regen, step 5 compile) and commit them on your lane
#   3. promote (the step 7 detach-merge below)
$LEASE --release
```

Sync, regenerate, promote, release — in that order, every time.

It is the same O_EXCL primitive as the push lock, keyed on the git **common dir**'s
device+inode — so all five lane worktrees are one repository and contend for one lease, and
neither `realpath` nor a path string can fool it. It is a *different* lease from the push
lock: holding one never blocks the other. A lease is **never** auto-expired; a stale one is
displaced deliberately and on the record with `--force-release <named holder>`.

If `--acquire` refuses, that is the system working. Do the unleased steps meanwhile and come
back — do not skip step 3 or 5, and do not edit the shared surface without the lease.

## Steps

### 1. Progress Report

- Create or append to **your own** daily progress file:
  **`progress/YYYY-MM/YYYY-MM-DD-<agent>.md`** — the date, a dash, your roster id.
- Document: problem, root cause (if applicable), changes made (with file/repo table), results, and any deferred work
- Follow the existing format — see recent entries for style reference

**Why per-agent, and why you must not use the shared file.** The unsuffixed
`progress/YYYY-MM/YYYY-MM-DD.md` was one file that every main appended to: on 2026-08-12 ten
wrap-up commits hit one 368 KB file, and each pathspec commit of it swept whatever the other
four had half-written (see the warning above). One file per agent per day removes the
contention entirely — nobody merges, because nobody shares. Convention defined in
`scripts/coordination/WORKTREE_MIGRATION.md`.

**Readers merge by glob, not by opening one file.** This is the same sharding the audit log
already uses (`logs/agent_audit-<id>.log`, written by `scripts/utils/agent_log.sh`, read back
merged by `scripts/utils/agent_log_read.sh` — copy that pattern):

```bash
cat progress/2026-08/2026-08-12-*.md          # everyone's day, per-agent shards
ls  progress/2026-08/2026-08-12*.md           # incl. the pre-convention shared file
```

The historical shared files are **not** retroactively split; a reader of any date before this
convention still opens the single unsuffixed file, which is why the glob above keeps the
unsuffixed name in range.

### 2. Handoff Updates

- Update any active handoffs in `handoffs/active/` that were advanced by this session's work
- Check off completed items, add new findings, note any blockers discovered
- If a handoff is fully complete, extract key findings to docs and move to `handoffs/completed/`
- If a handoff is only partially complete but completed history is obscuring live work, do not force an all-or-nothing move; use the partial-compaction rules in Step 3.

**Checklist-sync gate (required — do not skip to Step 3 until it passes).** The handoff dashboard's progress metric counts *checkbox state only*; narrative prose is invisible to it. For every handoff this session advanced:

1. **Flip completed tasks**: change `- [ ]` to `- [x]` and append the completion date inline (`✅ YYYY-MM-DD`) — the timeline generator prefers these in-file dates over commit dates.
2. **Add tasks discovered mid-flight**: any new work item that emerged this session (follow-ups, blockers-turned-tasks, scope found while implementing) gets its own `- [ ]` line in the relevant handoff's task list — even if it was also described in prose. If it was *already completed* this session, add it as `- [x] … ✅ YYYY-MM-DD` so the record stays complete.
3. **Prose describing task state must be accompanied by checkbox state.** "X is done/converged/deferred" in a status paragraph without the corresponding checkbox flip is a wrap-up defect.

**Verify before committing** — count the checkbox flips **that are yours**:

```bash
# From inside YOUR lane worktree. Scoped to your own lane's divergence from main,
# so it counts what this session did, not what the fleet did.
git diff "$(git merge-base main HEAD)"..HEAD -- handoffs/ | grep -cE '^\+\s*[-*] \[[xX]\]'   # committed on this lane
git diff HEAD -- handoffs/                   | grep -cE '^\+\s*[-*] \[[xX]\]'                 # still uncommitted here
```

Sum the two. If it prints `0` but the session completed any handoff-tracked work, go back and sync the checklists. Report the flip count in the wrap-up output.

**Why scoped, and not `git diff HEAD -- handoffs/` alone.** In the shared clone that second
command counted **every** main's in-flight checkbox flips as yours, so a session that flipped
nothing still read as compliant on peers' work — a gate that passes for a reason unrelated to
what it tests. In your own lane worktree the working tree is private, so the uncommitted half
is already yours; the merge-base half is what makes the committed half yours too. If
`check_lane_worktree.py --strict` said you are in the shared clone, this gate is **not
trustworthy** — move to your lane before believing its number.

**Derived-actionables gate (required — the flip-count gate cannot see this).** The flip-count gate catches un-flipped checkboxes; it has no counterpart for conclusions that never became checkboxes at all. A 2026-07-21 audit found **seven** high-ROI items — including the session's single time-sensitive item — that were fully derived in analysis text ("measurable locally today", "worth mirroring", "cheapest experiment in the program") and then filed **nowhere**: not in the owning handoff, not in any index. Before committing, sweep the session's own output (deep-dive results, sub-agent reports, analysis sections appended to handoffs) for every "we could/should/worth X" sentence and give each one exactly one of:

1. a `- [ ]` task in the owning handoff (plus an index row if it is priority-worthy or time-sensitive — a task buried at line 1400 of a long handoff is filed, not discoverable);
2. an **explicit written decline** ("not filed because …") so the drop is a decision, not an accident.

Watch for the three failure shapes that audit found: a conclusion stated in prose but never converted to a task; a fix landed while the flag/config that would make it *run* stays off with no enable task; and a live idea silently discarded because a *sibling* idea was falsified. Report the count of newly filed tasks and explicit declines in the wrap-up output.

### 3. Handoff Index Updates

**Indices follow the thin-row contract (rewritten 2026-08-10)** — read
`docs/guides/agent-workflows/handoff-index-authoring.md` before editing one. Rows are
`| ID | Track | Handoff | Next action | Deps |`; a row carries a pointer and a next step, never status,
evidence, or history. The master index owns **no backlog rows** — it is a router plus the operator
decision queue. Do not re-add a "master index priority queue".

- Update the `Next action` cell of any row this session advanced (one imperative line, ≤140 chars).
- **Do not strike through completed items** — delete the row. Terminal rows do not stay in the queue.
- Each handoff belongs to **exactly one** index. Never add a second row in another domain; use `Deps`.
- **New handoff created this session → it needs a row**, or it is invisible to dispatch (measured: 7
  orphaned handoffs before this contract, one of them a whole v9 kernel item).
- **Operator decisions** go in the master index's operator queue with an `Open since` date. A form-screen
  cannot detect "needs a human choice"; a decision left in a handoff body gets missed (measured: G9-disk,
  two weeks unnoticed, governing 227 GB).

**Required gate — run it under the wrap-up lease, and report the result:**

```bash
$LEASE --acquire                                  # shared surface: generated index state
python3 scripts/handoffs/index_state.py           # refresh generated state
python3 scripts/handoffs/index_state.py --check   # coverage/schema/freshness; non-zero on failure
$LEASE --release
```

The regen and the master index's generated block are the shared surface here — they are
rewritten wholesale from every index, so two concurrent runs mean one session's regen is
simply lost. Your own domain-index **row edits** are ordinary lane work and need no lease.

`--check` must exit 0 before committing. It fails on duplicate ownership, orphans, dead handoff links,
malformed rows, over-long `Next action`, unresolved `Deps`, and a stale generated block.

**Index hygiene — prune at wrap-up only (never mid-campaign).** Indices track *outstanding TODOs*, not completed-work narration. Do this pruning only here, at wrap-up, so completed work is reviewed on a controlled cadence rather than vanishing ad-hoc while an agent works:

- **Genuinely complete** handoff/section → archive it (`git mv` to `handoffs/completed/` + a completion banner; repoint its sibling links to `../active/`) and delete its index row.
- **Not complete, but the row's `Next action` is stale** → keep the handoff active and rewrite that one cell. Chronology belongs in the progress log; superseded narration belongs in `handoffs/archived/<index>-history-through-YYYY-MM-DD.md`, never in a cell.
- Point handoff *status* at the machine-readable source of truth (`.index-state.json`, `execution_manifest.jsonl`, test names) instead of re-narrating it in prose, so the index can't drift.
- **Always archive, never delete.** **List everything you pruned/archived in the wrap-up output** under the `## Index pruning / handoff compaction` heading defined in Output Format below so the operator can review it before it leaves the active tree.

**Handoff compaction — split completed scope out of oversized active handoffs.** Active handoffs should optimize for the next implementer. If completed detail now hides the live task, compact the handoff during this wrap-up step:

- **When to compact**: trigger is qualitative — the first screen of the active handoff no longer clearly answers "what do I do next?" Line count is only a prompt to evaluate: a 300+ line active handoff is worth a read-through, but many large handoffs are large because the open work is large. Do not split those.
- **Active handoff stays authoritative for open work**: preserve the handoff's existing schema, but make sure current status, executor start-here guidance, outstanding tasks, dependencies, decision gates/forks, key files, reporting instructions, and a compact `Completed Scope` table remain easy to find. Keep those sections if present; otherwise use the local structure that already carries equivalent information.
- **Move completed detail to a sibling**:
  - Use `handoffs/completed/<handoff>-completed-through-YYYY-MM-DD.md` for landed/validated phases that remain useful as evidence.
  - Use `handoffs/archived/<handoff>-history-through-YYYY-MM-DD.md` for superseded, obsolete, or no-longer-actionable history.
  - Completed example: a benchmark harness phase passed, changed thresholds, and remains evidence for the next gate.
  - Archived example: a prototype path passed locally but was superseded by a different architecture and is useful only to explain why not to revive it.
- **Split mechanics**: for partial compaction, create or update the sibling file and edit the active handoff in place. Do not `git mv` the active handoff unless the whole handoff is complete. This preserves the active path and its blame/history for future implementers.
- **Repeat compactions**: if a relevant sibling already exists, extend the newest sibling and update its date stamp plus reciprocal links if needed. Create a new dated sibling only when the older sibling is intentionally immutable or canonical.
- **Add reciprocal banners**:
  - Active file: link the completed/archived sibling under `Completed Scope`.
  - Completed/archived sibling: add "Historical ledger only; current work lives in `../active/<handoff>.md`."
- **Index handling after a split**: master and domain indices should point to the active handoff only, with at most a short "completed history linked from active handoff" note. Do not create separate index rows for completed siblings unless a sibling is itself a canonical reference.
- **Safety check**: before moving content, verify no active task, blocker, gate, or key file location is being moved out of `handoffs/active/`.
- **Report it**: list every split under the wrap-up output's `## Index pruning / handoff compaction` heading with active path, sibling path, and reason.

### 4. Repository Documentation

- Update any relevant documentation in the root repo (`docs/`, `CLAUDE.md`, etc.) if governance or process changed
- Update child repo documentation (`epyc-orchestrator`, `epyc-inference-research`, `epyc-llama`) if code-level docs need to reflect changes made this session
- Update model registry, config files, or reference docs if applicable

### 4b. README staleness check (lightweight)

Quick discoverability + freshness check on the three owned repo READMEs. Runs in <1 s and never blocks the wrap-up — just surfaces a warning if anything is stale or missing knowledge-base links.

Run this exact one-liner:

```bash
python3 .claude/skills/project-wiki/scripts/check_readme_freshness.py
```

The script flags any owned-repo README that:
- has not been modified in **≥60 days** (commit-date, not file mtime), OR
- does not link to both `wiki/` AND `research/` (the two knowledge-base entry points a GitHub visitor needs).

If anything fires, include the warning verbatim in your wrap-up output under a `## README freshness warnings` heading, **and refresh the flagged READMEs as part of this wrap-up.** If everything passes, omit the section.

**This routine owns the response — do not route it to a handoff.** A handoff is a finite work item with checkboxes and a terminal state; README freshness is a recurring obligation that has none, so it can only ever be closed wrongly. That is exactly what happened: `readme-refresh.md` was a legitimate one-shot ("all 3 READMEs are 5 weeks stale"), it *introduced this detector* on completion, and was then correctly archived to `handoffs/completed/` — leaving the alarm firing at a routing target that no longer existed. Both owned READMEs then drifted to 66 days before anyone acted (2026-07-29). Prior wrap-ups printed the warning and deferred to the dead handoff, which read as "the operator will decide" and meant nobody did.

Refreshing means a **refresh, not a rewrite** — these READMEs have a deliberate discoverability-first shape; keep their structure and voice. Two hard rules:

- **Verify every factual claim against the repo before writing it.** A README that confidently misstates current state is worse than a stale one. If you cannot verify something, leave the existing text alone rather than guessing.
- **Prefer linking to the authoritative doc over restating it.** Restated content is precisely what rots — a section whose whole purpose is to age (e.g. "Recent Results (last 60 days)") is a standing liability, so point at `progress/` and the master index rather than re-enumerating.

The `wiki/` and `research/` links are load-bearing (the checker re-tests them) — never drop or rename them.

### 5. Wiki Compilation

Compile any loose knowledge into the project wiki so findings don't stay buried in handoffs and progress logs.

**Hold the wrap-up lease for this whole step** (`$LEASE --acquire` … `--release`):
`wiki/source_manifest.json` and `wiki/.last_compile` are one manifest and one watermark for
the entire repo. Two sessions compiling concurrently means the second `--touch` moves the
watermark past sources the first never wrote pages for — the loss is silent and only shows up
as knowledge that never got compiled.

1. Run the source manifest scanner:
   ```
   python3 .claude/skills/project-wiki/scripts/compile_sources.py
   ```
2. If `total_new` is 0, skip to the next step — the wiki is up to date.
3. If there are new sources, follow the **Compile** operation in the `project-wiki` skill (SKILL.md Operation 3):
   - Read and cluster new sources by taxonomy category
   - Create or update `wiki/<category-key>.md` pages with synthesized findings and source citations
   - After compilation, update the timestamp:
     ```
     python3 .claude/skills/project-wiki/scripts/compile_sources.py --touch
     ```
4. Keep compilation incremental — only process sources newer than `.last_compile`.

### 6. Agent Log

If agent logging was active, ensure `agent_task_end` was called for all open tasks.

### 7. Commit, Push, Promote, and Report

- **Commit on your own lane branch, inside your own lane worktree.** `lane/<agent>` in
  `/mnt/raid0/llm/worktrees/mains/<agent>` — never in the shared clone, never on `main`
  directly. Your working tree is private there, which is what makes an ordinary
  `git commit -- <paths>` safe again for work-plane files (re-read the pathspec warning at the
  top for the cases where it still is not: the shared clone and the sub-repos).
- Commit documentation updates in each affected repo separately (root, orchestrator, research, etc.)
- Use descriptive commit messages summarizing what the session accomplished
- **Push each affected repo after committing** — never leave a wrap-up with unpushed commits. This is the historical failure mode: work was committed but never reached GitHub (or only reached a non-default branch), so it never registered as a contribution. Push the current branch to its upstream: `git -C <repo> push`.
  - **Never force-push.** If a push is rejected (non-fast-forward), do NOT `--force`; report it and let the operator reconcile.
- **Promote your lane to `main` at EVERY wrap-up. Not at session end, not when it feels
  worth it — every one.** Two reasons, both measured on 2026-08-12:
  - **Lanes that skip promotion rot.** The five lanes stood at **106 commits behind** `main`,
    and the `inference` lane at **~302 commits**, with zero merges since 2026-07-29. A lane
    branch does not stop accumulating conflict potential while nobody looks at it; it
    *concentrates* it into one much larger eventual merge, against two more weeks of
    unrelated `main` history. The worktree isolates; only promotion syncs. Skipping it trades
    today's small merge for a guaranteed large one.
  - GitHub credits contributions only for commits on the **default branch** (`main`); a
    lane-branch push backs work up but earns nothing on the graph until it reaches `main`.
- **Take the wrap-up lease for the merge** (`$LEASE --acquire` … `--release`) — two promotions
  racing the same `main` tip is the one part of promotion that is not isolated. Release it as
  soon as the merge is pushed, including on the blocked path.
- For each affected repo:
  - If the current branch **is** `main`, the push above already credited it — skip promotion.
  - Otherwise, if `git -C <repo> rev-list --count origin/main..HEAD` is greater than 0, promote via an **isolated, conflict-guarded** merge that never disturbs the live working tree/branch and never force-pushes. **Use exactly this pattern — do not invent a second promotion mechanism**; it is the standing path for every non-`main` branch, lane branches included:

    ```bash
    git -C <repo> fetch origin --quiet
    WT=$(mktemp -d)/promote
    git -C <repo> worktree add --detach "$WT" origin/main
    if git -C "$WT" merge --no-ff \
         -m "Merge <branch> into main (wrap-up promotion YYYY-MM-DD)" "origin/<branch>"; then
      git -C "$WT" push origin HEAD:main          # clean merge -> publish to main
      git -C <repo> branch -f main origin/main    # sync local main pointer
    else
      git -C "$WT" merge --abort                  # CONFLICT -> leave main untouched
      echo "PROMOTION BLOCKED: <repo>"
    fi
    git -C <repo> worktree remove "$WT" --force   # `remove`, NEVER `prune`
    ```

  - **On conflict, STOP** — leave `main` untouched, never auto-resolve or force, and report the repo under the `## Promotion blocked` heading (see Output Format) so the operator reconciles. A divergent `main` usually means an independent PR/commit landed on it directly; see the 2026-07-17 orchestrator promotion for the superset-verification pattern before resolving anything by hand.
- **Return every commit hash, push status, and promotion result** (new `main` SHA, or "blocked") so the operator can confirm each repo reached the contribution graph

## Output Format

If index pruning, archival, or handoff compaction happened, include this section before the commit table:

```
## Index pruning / handoff compaction

| Active path | Sibling/archive path | Action | Reason |
|-------------|----------------------|--------|--------|
| ... | ... | ... | ... |
```

If any branch promotion was blocked by a divergent `main`, include this section before the commit table:

```
## Promotion blocked

| Repo | Branch | Divergence | Action needed |
|------|--------|------------|---------------|
| ... | ... | ... | ... |
```

End your response with a summary block:

```
## Commits Pushed & Promoted

| Repo | Branch | Commit | Pushed | Promoted to main | Message |
|------|--------|--------|--------|------------------|---------|
| epyc-root | <branch> | <hash> | ✅/❌ | <main SHA / blocked / n/a (on main)> | <message> |
| ... | ... | ... | ... | ... | ... |
```

## Guidelines

- Be factual and specific — include file paths, commit hashes, and measured values where available
- Use tables for multi-file or multi-model changes
- **Do not defer work you can do.** Before writing anything into a "Deferred" list, apply the admission
  test in `agents/shared/OPERATING_CONSTRAINTS.md` → *Act, Don't Defer*: name the specific operator
  decision or external event you are blocked on, in one sentence. If you cannot, **finish the work now**
  — a wrap-up is the last place a doable task should be recorded instead of done. If an item appeared in
  the previous wrap-up and its blocker has not changed, that is proof it was never blocked: do it before
  writing this report.
- Note genuinely deferred work explicitly — with its named blocker — so the next session can pick it up
- Keep progress entries self-contained — a reader shouldn't need to look at other files to understand what happened
- **Push and promote after committing** (Step 7) so work reaches GitHub's contribution graph, which counts only the default branch (`main`) — never leave a wrap-up with unpushed or unpromoted commits. Never force-push, and never auto-resolve or force a promotion conflict: if a push is rejected or a promotion hits a divergent `main`, leave `main` untouched and surface it for the operator.
