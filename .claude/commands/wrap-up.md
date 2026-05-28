# Session Wrap-Up

Update all documentation artifacts to reflect work completed in this session, commit changes, and return commit hashes for manual push.

> **⚠ MANUAL TRIGGER ONLY.** Run this routine only when the operator explicitly invokes `/wrap-up`. Nothing may auto-trigger it — there is no `Stop`/`SessionEnd`/`PreCompact` hook, cron, or nightshift task that calls it, and there must not be one. Autonomous, scheduled, or nightshift sessions **may commit progress directly** (a focused `git commit` of progress/handoff edits is fine and encouraged for checkpointing) but must **NOT** run the full wrap-up routine: it performs index pruning (Step 3) and broad doc/wiki sweeps the operator wants to review on a controlled, manually-chosen cadence.

## Steps

### 1. Progress Report

- Create or append to today's progress file: `progress/YYYY-MM/YYYY-MM-DD.md`
- Document: problem, root cause (if applicable), changes made (with file/repo table), results, and any deferred work
- Follow the existing format — see recent entries for style reference

### 2. Handoff Updates

- Update any active handoffs in `handoffs/active/` that were advanced by this session's work
- Check off completed items, add new findings, note any blockers discovered
- If a handoff is fully complete, extract key findings to docs and move to `handoffs/completed/`
- If a handoff is only partially complete but completed history is obscuring live work, do not force an all-or-nothing move; use the partial-compaction rules in Step 3.

### 3. Handoff Index Updates

- Update relevant domain index files linked from `handoffs/active/master-handoff-index.md`
- Update the master index priority queue if item status changed (completed, priority shift, new items)
- Strikethrough completed items with checkmark and date

**Index hygiene — prune at wrap-up only (never mid-campaign).** Indices track *outstanding TODOs*, not completed-work narration. Do this pruning only here, at wrap-up, so completed work is reviewed on a controlled cadence rather than vanishing ad-hoc while an agent works:

- **Genuinely complete** handoff/section → archive it (`git mv` to `handoffs/completed/` + a completion banner; repoint its sibling links to `../active/`) and remove its index reference.
- **Not complete, but the index entry has accreted stale completed-narration** → keep the handoff active, trim the index entry to its open items only. Chronology belongs in the progress log, not the index cell (don't append "Update (date):" into index cells).
- Point handoff *status* at the machine-readable source of truth (`execution_manifest.jsonl`, test names) instead of re-narrating it in prose, so the index can't drift.
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

If anything fires, include the warning verbatim in your wrap-up output under a `## README freshness warnings` heading so the operator sees it. **Do not auto-fix** — the rewrite cadence is the operator's call (the `readme-refresh.md` handoff in `handoffs/active/` tracks scheduled rewrites). If everything passes, omit the section.

### 5. Wiki Compilation

Compile any loose knowledge into the project wiki so findings don't stay buried in handoffs and progress logs.

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

### 7. Commit and Report

- Commit documentation updates in each affected repo separately (root, orchestrator, research, etc.)
- Use descriptive commit messages summarizing what the session accomplished
- **Return all commit hashes** so the user can manually push each repo

## Output Format

If index pruning, archival, or handoff compaction happened, include this section before the commit table:

```
## Index pruning / handoff compaction

| Active path | Sibling/archive path | Action | Reason |
|-------------|----------------------|--------|--------|
| ... | ... | ... | ... |
```

End your response with a summary block:

```
## Commits Ready to Push

| Repo | Path | Commit | Message |
|------|------|--------|---------|
| epyc-root | /mnt/raid0/llm/epyc-root | <hash> | <message> |
| ... | ... | ... | ... |
```

## Guidelines

- Be factual and specific — include file paths, commit hashes, and measured values where available
- Use tables for multi-file or multi-model changes
- Note deferred work explicitly so the next session can pick it up
- Keep progress entries self-contained — a reader shouldn't need to look at other files to understand what happened
- Do NOT push — only commit locally and report hashes
