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

### 3. Handoff Index Updates

- Update relevant domain index files linked from `handoffs/active/master-handoff-index.md`
- Update the master index priority queue if item status changed (completed, priority shift, new items)
- Strikethrough completed items with checkmark and date

**Index hygiene — prune at wrap-up only (never mid-campaign).** Indices track *outstanding TODOs*, not completed-work narration. Do this pruning only here, at wrap-up, so completed work is reviewed on a controlled cadence rather than vanishing ad-hoc while an agent works:

- **Genuinely complete** handoff/section → archive it (`git mv` to `handoffs/completed/` + a completion banner; repoint its sibling links to `../active/`) and remove its index reference.
- **Not complete, but the index entry has accreted stale completed-narration** → keep the handoff active, trim the index entry to its open items only. Chronology belongs in the progress log, not the index cell (don't append "Update (date):" into index cells).
- Point handoff *status* at the machine-readable source of truth (`execution_manifest.jsonl`, test names) instead of re-narrating it in prose, so the index can't drift.
- **Always archive, never delete.** **List everything you pruned/archived in the wrap-up output** under a `## Index pruning` heading so the operator can review it before it leaves the active tree.

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
