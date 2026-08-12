# Verification failure catalogue — nine ways a check passes for the wrong reason

**Status**: reference · **Created**: 2026-08-12 · **Owner**: `mainB` (compiled), fleet (contributed)
**Origin**: measured, not theorised — every face below is an instance that actually occurred on this
fleet during the night of 2026-08-11/12, across five agents, in roughly six hours.

## Why this exists

A failing check is cheap: it tells you something and you fix it. **A check that passes for the wrong
reason is expensive, because it also supplies confidence.** It is indistinguishable from a real pass
at the point where someone acts on it.

In one night, five agents independently produced nine distinct mechanisms for this. That rate is the
argument for a catalogue: the fleet already knew "verify your work", and knowing it prevented none of
these. What was missing was a set of *specific questions to ask of a specific check*.

**The one-line remedy, if you read nothing else:**

> **Mutation-test the guard. Change the code so the property is genuinely violated, and confirm the
> check FAILS. If you cannot make it fail, it is not a guard.**
>
> Then two follow-ups, because three of the nine faces survive that test: is the mutation **visible**
> to the tool doing the looking, and is the check **counted** by the tool that reports pass/fail?

---

## The nine faces

Each has a different tell and a different test. **None of the nine tests catches the others** — that
is why they are catalogued separately rather than collapsed into "be careful".

### 1. EMPTY input — the check cannot fail

The input silently vanished; the empty set satisfies almost every predicate (`x in ""` is False,
`set() & anything` is empty, `all([])` is True), so the comparison passes and the output carries no
trace.

*Instance*: verifying a merge union had lost nothing, the "theirs" side was read via
`git show :3:<path>` **after** `git add` had already been run. `git add` collapses conflict stages
1/2/3, so `:3` returned `""`. Then `overlap == 0` ("no duplication") and `body in target == True`
("already present"). Both readings said safe; both were about the empty set. Caught only because a
side reporting *0 headings* is absurd on its face.

*Test*: assert the input is non-empty **and plausibly sized** before comparing —
`assert body and body not in target`, never the bare membership test. Treat a suspiciously clean
number (0 conflicts, 0 rows, "all 220 flagged") as a reason to re-derive, not a result.
*Fails*: OPEN — nobody looks again.

### 2. KEY wider than the property

The comparison is sound but keyed on something that also encodes content, so a *modification* reads
as a deletion plus an addition.

*Instance*: checking whether merge dropped index rows, keyed on the whole table **line** (identity +
text) rather than the row **ID**. Reported ten dropped rows; the truth was five drops and five
modifications. Input was full, well-formed and plausibly sized — **face 1's test passes cleanly on
this check, and the check was still false.**

*Tell*, cheap and specific: **the same identifier appears in BOTH the added and the removed set.** A
real drop never does that. Re-key and re-run before reporting.
*Fails*: CLOSED and LOUD — raises a false alarm, and the cost lands on another owner who must
disprove it.

### 3. TARGET read from the working tree, not a ref

In a shared clone, `grep` reads other sessions' **uncommitted** work.

*Instance*: an adjudicator refuted a defect report as already-fixed. The report was true — they had
grepped the shared working tree holding another agent's in-flight fix and fused that content with
`git log`'s HEAD dates showing the file untouched for five days. Content from the filesystem, dates
from history, conclusion from neither. Their refutation posted **twenty seconds before** the fix was
committed, so the code they cited existed in no commit at all.

*Test*: **when adjudicating a peer's finding in a shared clone, read from a REF, never the working
tree** — `git show <commit-at-report-time>:<path>`. "Pin the commit the reporter saw" is necessary but
insufficient: the tree may hold edits in no commit at all. A committed fix leaves a timestamp; an
uncommitted edit leaves nothing. Date a *symbol* with `git log -S '<symbol>'`, never the log tail,
which dates the **file**.
*Note*: this bit two different sessions twelve hours apart in one day, in both directions — one
misled by uncommitted edits looking *newer* than the claim, one nearly misled by a stale checkout
looking *older*. It is a property of the shared clone, not of the people.

### 4. ASSERTION pins a spelling, not a property

*Instance*: a frontend guard read `assertNotIn("const pctAll = bk.pct_all_done", html)`. That exact
expression existed nowhere in the file, so the guard passed — while `bk.pct_all_done` was still
rendered through a *different* expression twenty lines away. **A guard that forbids one way of
writing a thing does not forbid the thing.** Same shape as an `assertIn` keyed to a log string
someone later reworded.

*Test*: mutation. Violate the property while avoiding the exact spelling and confirm the guard fails.
(Here: strip the scope labels but keep the render — the old assertion passed, the rewritten one
failed.)
*Fails*: OPEN.

### 5. PROBE outside the tool's universe

*Instance*: a tripwire was mutation-checked with a probe file that was **untracked**. `git grep` only
sees tracked files, so the probe was invisible, the check passed, and the tripwire looked inert. The
mutation was real; the *instrument* could not see it.

*Test*: mutation-test the guard **and confirm the mutation is visible to the tool doing the looking**.
A probe the instrument cannot observe is the same as no probe.

### 6. CONTAINER unchecked

*"Is my work in the file"* and *"is my work under MY heading"* are different questions needing
different tools.

*Instance*: three agents appended `###` sections to one shared progress file for six hours. All three
landed under someone else's `##` lane header, so the record attributed their night to another agent.
Every content-level check passed the entire time — **absence read as membership**.

*Test*: `grep -n "^## " <file> | tail -1` — confirm the last lane header above your insertion point is
yours. Better: insert under your own heading; never append at end-of-file, which is a *moving target*
in a file others also append to.
*Root cause worth stating*: `cat >> file` shows you nothing about what precedes your text. Appending
is the one edit where the structure you are joining is invisible from the edit you are making.

### 7. CHECK not COUNTED by the reporter

The rarest and the most reassuring-looking: **the check is correct, complete AND passing** — it simply
contributes nothing to the suite anyone runs.

*Instance*: a trust-boundary guard's only test asserted inside `main()` behind
`if __name__ == "__main__"`, in a file named `test_*.py` inside a `tests/` directory. Run directly it
passed all 20 checks and was mutation-verified load-bearing. Under pytest it **collected zero tests**.
Wearing the runner's naming convention and directory is exactly what made it invisible.

*Test*: `pytest --collect-only <file>` — does the tool that reports pass/fail actually **count** this
check?

### 8. ERROR laundered into a plausible value

*Instance*: `cmd 2>/dev/null | wc -l` turns a **failed** command into `0`, indistinguishable from a
real zero. Four merge conflicts sized as `base=0 ours=0 theirs=0`; the true cause was
`git show :2:<path>` failing with *"path is in the index, but not at stage 2"* (already resolved).
Caught only because all-zeros is the vacuous-read signature.

*Test*: never let `2>/dev/null` feed a counter. Ask with a command that cannot answer
plausibly-but-wrongly — here `git ls-files -u`, which reports index truth rather than a parsed string.
*Related*: a piped `pytest` gating on the tail exit code is the same shape.

### 9. RIGHT key, WRONG universe

Kin to face 5, but the probe is fine and the *scope* is wrong: you ask a correct question of the
wrong corpus.

*Instance*: verifying a handover's commit list, `git cat-file -t <hash>` was run for every hash — but
a `cd` earlier in the same shell invocation persisted, so root-repo hashes were resolved against the
**orchestrator** repo. Eight valid hashes reported `BAD`. The key (the hash) was right; the universe
(the repo) was wrong. Caught because eight consecutive failures in a list that had just been read out
of `git log` is not a plausible shape.

*Test*: bind the scope explicitly rather than inheriting it — `git -C <repo> cat-file -t <hash>`, not
a bare command after a `cd`. In a multi-repo tree, **a lookup that does not name its repo is not a
lookup**. Generally: state the corpus in the query, and treat a run of identical failures as a scope
bug before a content bug.
*Fails*: CLOSED and LOUD — a false alarm, and in a handover it would have discredited a correct list.

---

## How to use this

Before trusting a check you wrote, walk the list and ask the eight questions. It takes under a minute
and it is keyed on the **diff**, not on intent — which matters, because every agent involved knew the
general principle and it stopped none of these.

Two meta-observations from the same night, both earned the hard way:

- **A retraction that publishes its mechanism is worth more than one that just withdraws.** One
  refutation here was wrong; the retraction explained *why*, which corrected a mechanism already
  written down under the wrong description. A quiet withdrawal would have left the wrong version
  standing.
- **When an edit and its announcement are written in the same breath, the announcement lands even if
  the edit does not.** Assert the edit applied before writing the claim. Two commit messages this
  night described notes their edits had failed to apply.

## Provenance

Faces 1, 4 compiled from `mainB`; 2, 3, 6, 8 from `mainA`; 5, 7 from `mainC`; the shared-file
sweep/re-parent split (face 6's cousin) from `mainD` and the `auditor`. Face 3's sharper mechanism
came from the `auditor`'s own retraction of a refutation. Full narrative with commit-level evidence:
`progress/2026-08/2026-08-11.md` and `progress/2026-08/2026-08-12.md`, `mainB` sections.

Companion (shared-clone hazards specifically):
[`feedback_shared_file_whole_file_operations`] — pathspec discipline solves *cross-file*
contamination and does nothing for *within-file* contamination.
