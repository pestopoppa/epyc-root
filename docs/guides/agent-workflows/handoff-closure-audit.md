# Handoff Closure Audit (`scripts/handoffs/closure_audit.py`)

`index_state.py --check` checks that a handoff index is **well-formed**. It cannot tell whether a
ticked box is **true**. The closure audit is the read-only check for the second question: for every
`- [x]` box in `handoffs/active/*.md`, does the code the box cites exist on `origin/main`?

**Origin.** The 2026-09-16 audit (`progress/2026-09/2026-09-16-sub-closure-audit.md`) checked 3,359
ticked boxes. Five of them asserted code that was on no ref: RC-9, E1a, UTM-M7, UTM-M8, and one
completed-handoff SQLite exporter. All five were ticked by a single commit, `4762625d`. The follow-up
(`progress/2026-09/2026-09-16-sub-closure-fix.md`) reopened them and promoted the tool into the repo.

## What it checks

It extracts three kinds of reference from each checked box:

- backticked `func()` and CamelCase identifiers
- paths, from backticks and markdown links
- commit SHAs of 7 to 40 hex characters

It checks each reference against `origin/main` of root, orchestrator and research, using only git
plumbing: no checkout and no repository writes. `--fetch` updates remote-tracking refs only.

Anything unresolved on main goes through these fallbacks, in order:

1. unmerged branch tips
2. `log --all -S` history
3. the kernel trees (llama.cpp, whisper, qwentts, ik)
4. every local clone under `/mnt/raid0/llm`
5. a same-subject commit on main
6. a fuzzy match against definitions

| class | meaning | usual action |
|---|---|---|
| `b` | exists on no ref of any repo, and the box asserts it was built | **reopen the box** (checkbox discipline below) |
| `a` | only off main: an unmerged branch, a local-only commit, untracked on disk, or deleted later | annotate; preserve the work if it is at risk |
| `c` | renamed or moved (similar definition, or the same basename elsewhere) | re-point the reference |
| `d` | external: an upstream or kernel-tree symbol | none |
| `e` | an evidence or runtime artifact path, untracked by design | none (not a code claim) |

Most raw `b` SHAs are false positives: upstream pins, digests, store-row ids, or cherry-picked SHAs
that were garbage-collected after landing on main under another SHA. **Always triage by reading the
box.** A raw `b` is a candidate, not a finding.

## Running it

```bash
python3 scripts/handoffs/closure_audit.py --fetch \
  --triage scripts/handoffs/closure_audit_triage.json \
  --json /mnt/raid0/llm/tmp/closure-audit/audit.json \
  --md   /mnt/raid0/llm/tmp/closure-audit/table.md \
  --tsv  /mnt/raid0/llm/tmp/closure-audit/flat.tsv
```

- A full run takes about 30 minutes, mostly the grep over unmerged branch tips. Use
  `--only REGEX` to limit it to certain handoff basenames.
- `--strict-idents` also checks backticked snake_case names (columns, fields, flags) in boxes that
  assert something was built. It is how RC-9 (`rubric_json` / `per_item_grades_json`) was caught.
  It is noisy: most hits are schema keys in external repos or JSON artifacts, or words from the
  design prose. Triage every hit.
- `--root/--orch/--research/--rev/--handoff-dir/--no-external` point the tool at other clones.
  The test uses them.

## Triage overrides

`scripts/handoffs/closure_audit_triage.json` records manual verdicts, so a rerun does not re-triage
rows that were already settled. Every flagged a/b/c row gets `triage_class` / `triage_action`; a row
with no matching override is marked `UNTRIAGED`. That marker is the work queue for the next audit.

- Keys, most specific first: `<handoff>.md:<line>|<ref>`, `<handoff>.md|<ref>`, `<handoff>.md:<line>`,
  `<handoff>.md`, `*|<ref>`.
- **Prefer the forms without a line number.** Line numbers drift as handoffs are edited; the ref
  text does not.
- `sha_equiv` maps an off-main SHA to its same-subject twin on main. Those rows are triaged as a
  cosmetic re-point.
- Add rows to the file; do not rewrite existing ones. A remediated row changes its `action` to
  name the session that fixed it.

## Acting on a confirmed phantom

Follow `agents/shared/SESSION_LIFECYCLE.md` → *Two axioms*:

- Flip the box back to `- [ ]` and keep its original text.
- Add a dated reopen note that gives the checked ref (for example `origin/main @ <sha>`), the words
  "exists on no ref", and the audit file.
- Deleted code that an open box still depends on is not a reopen. Mark the closed box
  SUPERSEDED/REMOVED, cite the deleting commit, and put a note on the dependent box.
- **Never tick or untick another agent's box.** For handoffs owned by a live session (autokernel,
  for example), add a dated factual note and leave the checkbox alone (INVARIANTS 9).
- Local-only commits, staged work and untracked files are **preservation risks for their owner**.
  Note them in the owning handoff; do not push someone else's commits.

## Verification

```bash
python3 tests/test_closure_audit.py   # fixture: one real + one phantom ref per kind, strict flag, triage
```
