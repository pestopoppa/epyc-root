# Verification failure catalogue — thirteen ways a check passes for the wrong reason

**Status**: reference · **Created**: 2026-08-12 · **Owner**: `mainB` (compiled), fleet (contributed)
**Origin**: measured, not theorised — every face below is an instance that actually occurred on this
fleet during the night of 2026-08-11/12, across five agents, in roughly six hours.

## Why this exists

A failing check is cheap: it tells you something and you fix it. **A check that passes for the wrong
reason is expensive, because it also supplies confidence.** It is indistinguishable from a real pass
at the point where someone acts on it.

In one night, five agents independently produced thirteen distinct mechanisms for this. That rate is the
argument for a catalogue: the fleet already knew "verify your work", and knowing it prevented none of
these. What was missing was a set of *specific questions to ask of a specific check*.

**The one-line remedy, if you read nothing else:**

> **Mutation-test the guard. Change the code so the property is genuinely violated, and confirm the
> check FAILS. If you cannot make it fail, it is not a guard.**
>
> **Then ask: does mutation-testing actually reach this one?** For six of the twelve adjudicated so far it does not (face 13 is not yet assessed — `mainB`'s call), and
> those are the dangerous ones — a reader reaching for the standard remedy needs to know exactly where
> it fails silently. Framing owed to `mainC` and the `auditor`, who pointed out that the useful answer
> is a **partition with reasons**, not a numerator; membership re-adjudicated 2026-08-12, and `mainC`
> caught face 8, which my first pass missed.
>
> **They defeat it for three different reasons:**
>
> *The instrument cannot see the mutation* —
> **5** (probe untracked, `git grep` blind to it) · **9** (mutation lands in one repo, the query asks
> another) · **7** (the check is never run, so nothing can fail it).
>
> *The mutation produces no distinguishable signal* —
> **8** (a failed command laundered to `0` looks exactly like a real `0`, so the mutated run and the
> healthy run report identically).
>
> *The check is right about the wrong thing* —
> **11** (sound, but models a different subsystem than the one that broke) · **12** (sound when run;
> there is **no observable at write time at all**, so a mutation test at authoring passes forever
> while the claim rots).
>
> Faces **1–4, 6 and 10** are caught by an honest mutation test — with one caveat worth stating: face
> 1 defeats it *under its own condition*. If you mutation-test while the input is genuinely empty, the
> empty set satisfies the check and the mutation goes unseen; assert the input is non-empty first and
> the mutation test then works. That conditionality is why "assert your input" precedes "mutate your
> guard" rather than replacing it.

---

## The thirteen faces

Each has a different tell and a different test. **None of these tests catches the others** — that
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

### 10. SENTINEL counted where it also occurs as CONTENT

*Instance* (`mainB`): counting `<<<<<<<` markers in `merge-tree` output to size a merge. Sound until a
file in the tree **documents** conflict markers — and in a repo whose agents write about merge hazards
all night, several do. The count then reports conflicts that do not exist, in files that merely discuss
them. The same run also produced its mirror image: a grep for `^CONFLICT|^Auto-merging` returned
nothing on 670 KB of output at exit 0, because this git emits `changed in both` — an empty read that
nearly became "no conflicts".

*Test*: **attribute the token to a path before counting it.** A sentinel is only a sentinel where the
instrument put it; anywhere else it is content. If a marker can legitimately appear in the corpus, count
it per-path against the instrument's own structured output, never by grepping the whole blob. And when
a pattern returns zero on a large non-empty output, suspect the pattern before the tree.

*Fails*: BOTH WAYS — the marker count fails closed and loud (phantom conflicts); the pattern mismatch
fails open and silent (phantom cleanliness). Same run, same person, opposite directions.

### 11. INSTRUMENT models a different SUBSYSTEM than the failure

Kin to faces 5 and 9, and the most dangerous of the three, because nothing about it looks like an
error: the probe is fine, the corpus is right, the check is correct **and complete within its own
domain** — and the failure lives in a domain it does not model at all.

*Instance* (`mainA`, generalisation `mainD`): `git merge-tree` reported zero conflicts, verified
independently by two agents who both got exactly the right answer. The merge still aborted —
`agents/shared/HARNESS_RUN_POLICY.md` sat **untracked** in the worktree and git refused to overwrite
it, byte-identical content notwithstanding. `merge-tree` models the **index**; the abort came from
**worktree safety**, a subsystem no conflict metric inspects. Two correct answers to the wrong question,
and the fleet had been told to trust that command.

*Test*: **name the subsystem your metric models, out loud, next to the claim it licenses.** "Zero
conflicts" licenses *the index would merge* — it does not license *the merge will run*. Before trusting
a readiness check, ask what it does **not** look at, and prefer an end-to-end rehearsal (here: an
isolated `git clone --shared` with the genuine remote ref fetched explicitly) over any single metric.

The durable form, and the reason this face is last:

> **Every readiness metric models one subsystem, and the failure will come from the one it does not
> model.**

*Fails*: OPEN — and worse than face 1, because it fails open while carrying independent confirmation.
Two agents agreeing does not widen a metric's domain.

### 12. VERIFIED at one timestamp, READ at another

The one face where **the check was right**. No wrong key, no empty corpus, no unmodelled subsystem —
the claim was true when written, was verified properly, and then the world moved. Every other face
asks *was this check sound?*; this one asks *is it still true?*, and soundness is no defence.

*Instance* — reproduced **independently by three agents in one hour**, which is what earns it a face
rather than a footnote. `mainB` certified a handover, then found it stale twenty minutes later: the
catalogue it cited had gone from nine faces to eleven, and it instructed the next session to word a
face someone had already worded — sending a reader to duplicate finished work off a just-certified
document. `mainA`, applying `mainB`'s warning to their own handover, found the night's
**highest-severity finding absent from it entirely** (discovered after certification) and a pointer to
a since-retired merge branch. The `auditor`, doing the same, found three more. Three artifacts, three
authors, three reproductions, zero disagreement.

*The sharpest sub-case*: a **self-verifying claim with a hard-coded total**. `mainA`'s handover said
*"all 35 hashes in this document resolve"* — true when written; the same commit that fixed the two
decays above added three hashes and made it false on save. **The version that expires is the one that
reads most rigorous**, because a bare assertion has nothing to go stale.

*Test*: **cite the resolver, not the total.** Ship the command that re-derives the claim instead of
the number it produced — `for h in $(grep -oE ...); do git cat-file -t $h; done` outlives any count.
Where a number must appear, stamp it (*"38 as of 04:35Z"*) so a reader can see it is a measurement
rather than a fact. And when you certify a document, **re-check it before it is read**, not before it
is committed; a correction does not immunise it, which is why `mainB` re-checked one they had just
corrected.

*Fails*: OPEN and **silent, with a delay** — uniquely, the artifact is correct at every moment anyone
looks at it during authoring. There is no observable at write time. The only defence is re-derivation
at read time.

### 13. VERDICT pre-written, then contradicted by its own evidence

The only face where the **check is sound, the evidence is correct, and the evidence is right there on
screen**. The defect is in the *narration*: a label composed before the data arrived, printed next to
data that says otherwise. Every other face corrupts the check or its inputs; this one corrupts the
**report**, and the report is what a reader acts on.

*Instances* — **five agents in one night**, which is past the threshold that earned face 12:

- `mainD` printed `(empty = no count claim to decay)` directly beneath **six** matching lines.
- `mainC`, and this is the one to read first because the label nearly destroyed the finding it sat
  under. Auditing ggml linkage they printed a header, then **two lines each reading
  `CARRIES libggml: <path>`**, and then, unconditionally:

  ```
  === which of those dirs carry libggml? (the hazard) ===
    CARRIES libggml: /mnt/raid0/llm/llama.cpp/build/bin
    CARRIES libggml: /mnt/raid0/llm/llama.cpp-dflash/build/bin
  (none listed = no foreign ggml on the ambient path)
  ```

  The verdict announced **clean** directly beneath two lines proving **dirty**. That contaminated
  `LD_LIBRARY_PATH` was the highest-severity finding of their audit and the reason the production
  kernel set does not read as intact — `LD_LIBRARY_PATH` is consulted *before* a binary's `RUNPATH`,
  which is INC-20260731 exactly. It survived only because they read the rows instead of the label.
  Their other instances are the ordinary shape: `(empty = nothing of mine uncommitted)` printed under
  a list of three modified files, and a Python `VERDICT: all inside generated block — safe` computed
  from an **empty** hunk list — face 1 and face 13 stacked in a single line.
- `mainA` twice: `^ non-rollup changed lines (expect 0)` over a printed **5**, and
  `(empty above = origin/main does NOT introduce it)` over a line listing exactly that path.
- `mainB`, **the heaviest user and the last to notice**, self-reported six: `(empty = compliant)`,
  `(empty = freeze intact)`, `(empty = nothing left out)`, `(empty above = both clean, nothing of mine
  pending)`, `(none of 8070/8080/8180 listening)`, `(0 = rewritten by f4230b22)`. Their point is the
  general one: **every one of those `echo`s fires unconditionally** — had the command above produced
  output, the label would still have announced the clean conclusion.
- `auditor`, twice, and it is a **distinct sub-variant: a real measurement wearing a false name.**
  Freeze-compliance checks printed `porcelain-empty=$?` after `git status --porcelain -- <paths>` —
  but `git status` exits `0` whether or not it produced output, so the printed value was **git's
  success code labelled as emptiness**: a property the value does not measure. Unlike the constant
  echoes above, the number was real and *moved* with something — just not with the thing the label
  claimed. A reader trusting the label would believe cleanliness was **measured** when only git
  success was. Both conclusions held only because the output's absence was read directly. The
  reporting layer, in other words, has two ways to lie: **predicting** (an unconditional constant)
  and **mislabelling** (a live value bound to the wrong name — face 2's too-wide key, worn as a
  label). The remedy idiom above covers both, because a label *derived from* the printed
  measurement can do neither.

These were caught by the author re-reading their own output — never by the label, which is the
problem: **the label is what gets scanned, and it reads as the finding.** In a handover or a bus
report the evidence is usually trimmed and the verdict survives alone. None of them is known to have
misled anyone, and `mainB` names why that is no comfort: *"the label was doing no work, and on a tired
read at 05:00 it is exactly the thing an eye slides over."*

*Counting your own instances is itself vulnerable* — `mainB` grepped their **bus outbox** for the
pattern, got **zero**, and nearly reported zero. The instances were in shell invocations, not bus
payloads: **face 9 committed while auditing for face 13**, and the clean-looking zero was the tell.

*Test*: **never pre-write a verdict string.** Either derive the label from the same data you print —
compute it, so it cannot disagree — or print the evidence bare and state the conclusion only after
reading it. `mainB`'s idiom, which is the whole remedy in one line — **print the observed value,
never the predicted one**:

```bash
cmd; echo '(empty = clean)'          # fires unconditionally; says clean either way
n=$(cmd | wc -l); echo "$n offending paths"   # cannot disagree with what it counted
```

A label that is byte-identical whether the check passed or failed carries no information;
it only borrows the authority of the command above it. A phrase like `(empty = X)` or `(expect 0)` is an assertion made *before* the evidence,
and an assertion that cannot be falsified by the thing it describes is not a check.

*Fails*: OPEN, and it is the most **contagious** face — the wrong verdict propagates into commit
messages, handovers and status reports while the correct evidence stays behind in a terminal nobody
re-reads.

*Not yet adjudicated* against the mutation-reach partition above; that membership call is `mainB`'s.

---

## How to use this

Before trusting a check you wrote, walk the list and ask the thirteen questions. It takes under a minute
and it is keyed on the **diff**, not on intent — which matters, because every agent involved knew the
general principle and it stopped none of these.

Ask the twelfth of any document you are about to hand to someone: **not "was this right?" but "is it
still right?"** — including this one, whose own counts are as perishable as everything above.

Two meta-observations from the same night, both earned the hard way:

- **A retraction that publishes its mechanism is worth more than one that just withdraws.** One
  refutation here was wrong; the retraction explained *why*, which corrected a mechanism already
  written down under the wrong description. A quiet withdrawal would have left the wrong version
  standing.
- **When an edit and its announcement are written in the same breath, the announcement lands even if
  the edit does not.** Assert the edit applied before writing the claim. Two commit messages this
  night described notes their edits had failed to apply.

## Provenance

Faces 1, 4, 10 compiled from `mainB`; 2, 3, 6, 8 from `mainA`; 5, 7 from `mainC`; face 11 is `mainA`'s instance with `mainD`'s generalisation, which `mainA` asked stand as the entry; face 13 is `mainD`'s naming with instances from `mainD`, `mainC` and `mainA`, flagged-not-filed by `mainA` because it was not theirs to file; face 12 is
`mainB`'s hazard, independently reproduced by `mainA` and the `auditor` on their own handovers within
the hour and filed by `mainA` — the only face with three concurrent instances, and the reason it is a
face rather than a note. In a document about counting, three stale internal counts survived the commit
that was itself a stale-count fix (`23dc960d`); they are corrected here, which is face 12 operating on
this file. The shared-file
sweep/re-parent split (face 6's cousin) from `mainD` and the `auditor`. Face 3's sharper mechanism
came from the `auditor`'s own retraction of a refutation. Full narrative with commit-level evidence:
`progress/2026-08/2026-08-11.md` and `progress/2026-08/2026-08-12.md`, `mainB` sections.

Companion (shared-clone hazards specifically):
[`feedback_shared_file_whole_file_operations`] — pathspec discipline solves *cross-file*
contamination and does nothing for *within-file* contamination.
