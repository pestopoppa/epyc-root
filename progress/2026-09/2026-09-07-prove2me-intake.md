# 2026-09-07 — Prove2Me research-intake wave (intake-1297…1310), and a stale-worktree repair

Four-stage research intake on Anthropic's Prove2Me paper (arXiv:2608.28433) and the
Fermat's-Last-Theorem write-up, run to Stage-4 implementation. Two live defects were found and
fixed on the way, four doctrine amendments were ratified, and the session ended by repairing a
repo-wide stale-worktree contamination that was unrelated to the intake but blocking its commits.

## The wave

| | |
|---|---|
| Entries minted | 14 — `intake-1297` … `intake-1310` |
| Dive-verified | 13 of 14 (`intake-1303` deliberately left `stage1-unverified`, never dived) |
| Claim anchors | 42 |
| Claim corrections | 20 |

Stage-2b ingested **and** dived 7 operator-selected sources surfaced by the first round: Gloeckle
et al. `2604.03071`, Rammal et al. `2605.29955`, Urban `2601.03298`, Bourigault et al.
`2605.28365`, two `prove2me_workspace` reference files, and the `anthropics/fermats-last-theorem`
repo. Operator declined items 8–11; the declines are recorded by name in `intake-1299`'s notes so
the drop is a decision rather than an omission.

Context worth keeping: a 2026-08-09 audit found **zero** anchored claims across 1,067 entries. This
wave adds 42.

## All three opening hypotheses were overturned or dissolved

The operator opened the wave with three "worth stealing" hypotheses. The dives killed all three,
which is the wave's most useful output:

1. **DAG-derived work frontier** — overturned. Prove2Me's readiness is *free* from its decomposition
   invariant (a leaf has no children, therefore no unsatisfied prerequisites); nothing computes it.
   And it can skip claiming/locking only because its work units are atomized, immutable and
   kernel-adjudicated — none of which our backlog rows are. **The reason it needs no lock is the
   reason we cannot drop one.**
2. **Statement/proof separation as a cheap refold** — dissolved on both sides. The paper *does*
   argue compile cost (§2, §4.1, §4.2); it simply never measures it. And on our side `chain_grade`
   (`scripts/vidya/fold.py:530`) has exactly one occurrence in the tree — its own definition — so
   there is no claim→claim propagation to make cheap.
3. **NL-description index for reuse** — refuted by the producer's own measurement: roughly two in
   five statements repeat another file *verbatim*, about a fifth of proof-file lines are verbatim
   copies, and one lemma is re-declared in over 300 files. Reuse-via-search measurably failed at
   the scale it was meant to serve.

What survived is filed below, each on its own merits rather than on the premise that led to it.

## Three citation defects found inside the Prove2Me paper

Recorded on `intake-1297` under `contradicting_evidence`. None changes that entry's verdict, and
all three were found only by diving the *cited* sources — none is visible from the citing paper:

- **Attribution error.** §2 describes Urban 2026 as ~130k lines "of Lean". It is **Megalodon**, a
  higher-order set-theory checker with no mathlib (`intake-1306`). The bibliography has the correct
  title, so the error is confined to one body sentence.
- **Half-unsupported citation.** §2's "five-figure budgets per project (Gloeckle et al., 2026;
  Rammal et al., 2026)" rests on Gloeckle alone — Rammal contains no dollar figure of any kind
  (`intake-1305`), and the Gloeckle figure is itself modelled from token logs missing the caching
  field, not billed.
- **Table 1 contradicts §5 on its own cell.** The caption defines the Agents column as a population;
  the cited source counts 30,046 agent *runs* (11.6% merged, 45% of them review passes), and
  Prove2Me's own §5 says "agent runs". That is precisely the cell our fan-out question was aimed at.

Table 1 is in any case disclaimed by its authors three times, so no cost-per-line comparison across
its rows is defensible.

## Two live defects found and fixed

**(1) A dependency cycle in a live index.** `INF-06 ⇄ INF-64` in `inference-research-index.md` — a
*rider-of* relation written into a *blocked-on* column, so each row was permanently unreachable
while rendering as ordinary and dispatchable everywhere. Found by running the readiness computation
the overturned H1 had proposed; the hypothesis failed but the computation earned its keep. Fixed by
clearing INF-64's `Deps` cell — the relation survives untouched as the derived `ref` edge the graph
builder already generates from the markdown link.

The class is now detected rather than merely repaired: `dep_cycles()` in `index_state.py --check`,
12 tests. `BAD DEP` validates that a dep points at a *known* row, which every edge in a cycle does —
each edge is well-formed and only the closure is broken, which is why it was invisible.

**(2) `scripts/vidya/gate.py` erased a distinction `fold.py` exists to preserve.** A belief blocked
purely by a `dependency_alert` was refused with **"0 unreviewed correction(s) recorded against this
claim"** — a count of zero presented as the cause, plus a remedy that does not apply. `fold.py:96-100`
keeps corrections and dependency alerts apart precisely because they "get cleared by different
people". 118 `claim_depends_on` frames exist in the live ledger, so this was a production path.
Fixed to report per condition and name the withdrawn entries; 7 tests, proven non-vacuous by
replaying them against a pre-fix copy.

Suite after both fixes and the tree repair: **810 passing**.

## Stage-4 plan applied — 19 open rows, 2 closed, across 8 handoffs

| Handoff | Rows |
|---|---|
| `vidya-belief-substrate-program.md` | SC56–SC60 (statement-binding above `Judged`; `decided_proposition` adapter contract; judgment-frame digest pinning; `reason` on supersession; obligation leverage ranking) |
| `reviewer-typed-artifacts.md` | RA-13a/b/c — blind read-back, its write-time instrumentation, its record format |
| `handoff-index-and-backlog-graph.md` | 3 open + 2 closed + 1 deliberate non-goal |
| `fleet-fanout-measurement.md` | FM-5 discarded-work accounting, FM-6 reconnection requirement |
| `canonical-judge-suite-revamp.md` | CJ-8 three-valued verdicts, CJ-9 resolved coverage |
| `reviewer-calibration-accounting.md` | RC-11 false-accept/false-reject split, RC-12 threshold-selection audit |
| `glm52-reviewer-capability-gates.md` | GC-6 two-axis reviewer split |
| `session-bus-thin-dispatcher.md` | AIR-11 blocked-on-dispatch rate |

Plus a §4.1 amendment to `docs/design/vidya-pilot-spec.md` recording that Prove2Me independently
instantiates this program's two-plane split — machine-checked correctness idempotent, an accruing
trust score gating nothing — under every commercial incentive to do otherwise.

The deliberate non-goal is filed as a decision so it cannot be silently re-proposed:
**checkbox-level dependency edges**, declined because our `dep` edges are handoff-to-handoff while
dispatch happens on ~1,528 checkbox rows, and per-row deps are closer to status than to pointer
under the thin-row contract.

## Four doctrine amendments ratified — `fb755192`

Applied by the operator via `scripts/operator/ratify_prove2me_doctrine_20260907.sh`:

- `MEASUREMENT_POLICY.md` — a speed claim must name its **unit of work**; an instrument modified by
  the claimant requires a **control run**; **caveat placement** must not be inversely correlated with
  caveat severity.
- `OPERATING_CONSTRAINTS.md` — *"A fan-out's cost is its discarded work, not its width."* Width 3–5
  unchanged; the evidence in fact defends it (3–5 workers beat 1 on both wall-clock and token cost
  at matched completion; the central coordination tier is ~11% of compute). What the clause adds is
  a diagnosis order, because the measured driver was 80% of tokens going to runs that merged nothing.

## Stale-worktree contamination — found, scoped, repaired

While isolating the ratify commit, the working tree turned out to be broadly stale. Root cause is in
the reflog: **`HEAD@{1} reset: moving to origin/main`** — a *non-hard* reset, which moves HEAD and
the index while leaving the working tree at its old state. Every file older than the new HEAD then
presents as "modified" or "deleted" with no author behind it.

Scope, measured: **37 tracked files byte-identical to older commits of their own path**, and **29
tracked files showing as deleted**. Two examples of what was at stake:

- The ratified **OP-32** cluster — the "Artifact and delta are separate axes" block in
  `MEASUREMENT_POLICY.md` with its INF-68 evidence, the `ratify_op32_uniform_iq4xs_20260901.json`
  artifact, and the completed handoff, which had been replaced in `active/` by its own
  pre-ratification text from `3c8c9dd4`.
- The shallow-repository guard in `index_state.py` — the peer diff was the **exact inverse** of
  commit `437f751f`, all 54 deleted lines and nothing else, undoing a CI fix titled *"give
  index_state the history it reads — tests workflow never once passed"*.

Repair was provably lossless and only touched files that could be proven contaminated: an exact
rewind contains no new content by construction, and a deletion has nothing to lose. Files carrying
genuine peer edits were left alone. `git status` went from 91 dirty files to 18, and the two
`--check` problems that the contamination had caused (an orphaned handoff, a dead link from INF-70)
cleared. The restore also recovered 16 deleted test files, which is why the suite went 794 → 810.

**The generalizable lesson, and the reason this is written down:** a non-hard reset produces a
working tree that looks like dozens of peer edits and is actually one stale checkout. The
distinguishing test is cheap — *does this file's worktree blob equal an older commit of the same
path?* If yes it holds no new work, whatever `git status` implies. This is a fourth way to destroy
uncommitted work, alongside the three already in the wiki.

## Commits

| Commit | Contents |
|---|---|
| `fb755192` | the four doctrine amendments (operator-run ratify script) |
| `f87ccc36` | task rows across 6 handoffs, spec §4.1, both regression-test files, the ratify script + patch |
| `6491eccf` | the 14 intake entries, SC56–SC60, GC-6, and both defect fixes |

All three were staged with deletion-count verification, because the stale tree meant a plain
`git add` of several files would have deleted committed content — `glm52-reviewer-capability-gates.md`
alone would have dropped 31 committed lines.

## Gates

| Gate | Result |
|---|---|
| `validate_intake.sh` | OK — 1326 entries (baseline was RED with 4 dangling refs; repaired this wave) |
| `index_state.py --check` | **0 problems** |
| `cite-check` | exit 0 — zero refuted, conflicted or dangling |
| `pytest` (vidya + index_state + handoff parser) | **810 passed** |

## Open

- [ ] **This wave's claims are not yet gradeable.** `cite-check` classes the wave's own citations as
      `unknown` — the entries exist but no claim of them has been ingested into the belief ledger.
      Non-blocking (the gate exits 0), but any row resting on them rests on an ungraded citation
      until the ledger ingest runs.
- [ ] **`main` is 2 ahead / 233 behind `origin/main`.** Note the standing OP-11 posture on divergent
      `main` before any promotion; this is a large merge, not a fast-forward.
- [ ] **A concurrent research-intake session holds `intake-1311`…`1330` uncommitted** in
      `research/intake_index.yaml`, plus its own `.research-session.json` state. Deliberately excluded
      from `6491eccf` and left intact for that session to commit. `.research-session.json` is likewise
      left uncommitted — both sessions write it, and committing either version misrepresents the other.

---

## Execution — the filed rows, worked the same day

Waves 1–2 of the 19 filed rows, run as Opus subagents with the main thread reviewing and applying.

| Row | Commit | Result |
|---|---|---|
| wiki compilation | `18cfd5fa` | 5 pages, 360 lines, 0 deletions |
| ready/blocked derivation (`index_graph.v2`) | `457abd40` | 136 ready / 24 blocked / 10 no_open |
| SC57/58/59 | `fe91818d` | **SC58 was a P1 defect, not a passing check** |
| FM-5 / FM-6 | `5f1c4ba4` | fan-out outcome accounting; orphan rate 35.0% |
| SC56 | `51f9ef61` | statement-binding cap; SC61 filed for its producer |
| SC62 | `5a630e2a` | FM-5 projected into the belief kernel, bounds enforced |
| AIR-11 | `85d27f53` | measured; AIR-12/13/14 filed from the result |

### The fan-out numbers are BANDS, and the first form we published was one-sided

FM-5 first reported *"≥86.5% of tokens went to work never used"*. SC62, projecting it into the
belief kernel, established that this is the **low end of a band whose ceiling is 99.7%**:

| quantity | band |
|---|---|
| head-count waste | 40.0% – 95.5% |
| token waste (`total`) | 86.5% – 99.7% |
| token waste (`new`) | 83.8% – 99.6% |
| blocked share | ≥ 0.0%, no upper bound |
| unclassifiable | exactly 501, held out of every denominator |

**The ends rest on different evidence, not different confidence.** The low end counts 2,265
`produced-and-used`, of which 2,094 are `parent-reference` substring hits — evidence the parent
*saw* the output, not that it *used* it. The high end counts 171 `git-landed`, the only proven
floor, and those 171 hold just 2.85B of 1,110.7B tokens.

The projection makes the band non-optional rather than documented: `value` is a `Bound` whose
`.point`, `float()` and `int()` raise, and the guard sits on the generated claim **text**, because
`to_frames` emits the text and never the value — a guard on the number alone would be inert exactly
where it matters. All five tuples grade `Judged/Located`: there is no codified protocol for
transcript forensics and none was invented to clear the bar.

**Correction of record:** commit messages `5f1c4ba4` and earlier session reporting quote the
one-sided `≥86.5%`. That is true as a lower bound but incomplete, and the band form above
supersedes it everywhere.

### Two defects found by doing the work, not by looking for them

**SC58** was specified as a check that might already pass. It failed on three counts: the judgment
check validated field *presence* and never content, no `dirty` state existed, and the branch
discarded `claim_id` so a judgment could not reach a belief at all. The shipped fixtures used
`["a"]` and `"sha256:aa"` — **the suite asserted the bug**. Fail-closed and prospective; the live
ledger holds zero judgment frames.

**AIR-11** found that the instrument built to answer it has answered it zero times:
`premise_screener` has 9 lifetime verdicts, 0 of them `stale`, 5 `unknown` because the probe bundle
lacked the settling artifact. Its verdict — a screening fix, not a dependency-edge subsystem — is
recorded in `session-bus-thin-dispatcher.md` with AIR-12/13/14 filed from it.
