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

## Wave 3 — RA-13b/c, RC-11/RC-12, CJ-8/CJ-9, and the cross-repo naming ratification

Continuation of the same subagent-dispatch pattern, same day, after AIR-11 landed.

| Row | Commit | Result |
|---|---|---|
| RA-13b/c | `495de160` | blind read-back write-time meter + record format; 48 tests, 9/9 mutants killed |
| RC-11/RC-12 | `ae8ab82b` | PII eval sides split; **`impact.py` ordinal off-by-one fixed**; SC64 filed |
| PII `account_number` fixture | `0c788932` | vacuous negative case given a real side; **`\b`-vs-`_` guard defect fixed** |
| CJ-8/CJ-9 | `9c86adb8` | three-valued gate-verdict contract + per-suite resolved coverage; one worked conversion |
| naming ratification | `10098820`, `3adbd63d` (root) / `8b740065` (orchestrator) | `inconclusive` fixed as the canonical wire spelling |
| rollup refresh | `ecbdc917` | `index_state.py --check` regenerated post-wave |

**RA-13b/c** builds the write-time meter and record format for blind read-back (the reviewer
sub-agent receiving only the artifact, never the task statement). The three counts must partition
the denominator — an undercounted one silently inflates every rate, so it is refused — and
`citable_summary()` raises below n=20, naming n, the threshold, and the bound it failed. RA-13c
closes the source paper's own defect: `verify_brief_binding()` re-derives the sha256 of the
rendered brief, so a run whose context leaked the task statement produces a different hash and
cannot pass as blinded. RA-13a (the actual N=20 pilot) stays open — it needs live model calls and
is operator-gated; only its harness is built.

**RC-11/RC-12 turned up two live defects while auditing, neither of which the row was written to
find:**

1. **`scripts/vidya/impact.py` classified `CLAIM_COMPLETE` on the literal `g.t >= 2`.** That
   ordinal was correct when written — `Anchored` was grade ordinal 2 — but commit `29173208`
   inserted `MachineLocated` at ordinal 2 and pushed `Anchored` up, so the check silently began
   admitting machine-located spans while the local variable and its own docstring still said
   "anchored". It failed in the dangerous direction: `CLAIM_COMPLETE` is what licenses asserting
   `UNAFFECTED`, and the module's own header calls a wrong `UNAFFECTED` "the single most
   dangerous output this system could produce" — machine-located spans are by construction spans
   no person has read. Mutation-confirmed: under the old literal, a belief supported entirely by
   machine-located spans returned claim-complete. Fixed to read the named level; 95 new tests.
2. **`pii_fixture_eval.py` reported one `passed/42`** over 20 must-block and 22 must-not-block
   rows with no side split. Now two counters, own denominators, cause histograms, and an explicit
   statement of the non-computable side (false-reject has no ground truth to convert to a rate).
   The payoff: the account_number rule — the most false-reject-prone rule in the hook, five
   documented over-block repairs — had exactly **one** must-not-block row, at 10 digits, below the
   rule's 12-digit floor. Its entire false-reject surface was untested and the suite was green
   about it.

**The PII fixture follow-up (`0c788932`) turned that vacuity into a live guard defect.** Negative
coverage for `account_number` went 1 → 9 rows, each pinning one named exemption branch. The new
negative control caught it immediately: the config-exemption guard read
`\b(account|card|customer|iban|routing|ssn)\b`, and `\b` does not treat `_` as a word boundary
separator the way the rule assumed — so `\baccount\b` never matched `account_number`, and
`account_number: <16 digits>` sailed through the branch built to refuse it. (The literal
digits live in the fixture, which the hook allow-lists; quoting them here would trip the very
hook this paragraph describes — as they did, on the first attempt to commit this note.) Both guards
now match on non-alpha boundaries (so `_` separates, but a mid-word hit still doesn't fire); two
trap rows (`discarded_bytes`, `wildcard_shard_size`) pin that legitimate exemptions keep working.
Eval after the fix: false-accept 0/21, false-reject 0/30, sides reported separately, a real
account number verified still blocking end-to-end. `tokens` was also added to the
self-describing-key exemption alternation, closing the over-block that hit `5f1c4ba4` earlier the
same day.

**CJ-8/CJ-9 ship the contract, not the migration.** `gate_verdict.py` (829 new lines) enforces:
verdicts are `pass`/`fail`/`out-of-coverage`; any bool, `0`/`1`, or other non-member is refused;
`out-of-coverage` without a cause is refused; a cause outside a closed 9-code registry is refused;
a cause attached to a *decided* verdict is refused; `refuse_two_valued()` refuses a suite that
declares only two values at all; `min_resolved_coverage` is mandatory per suite (never defaulted —
one global number would be a threshold nobody derived), and a suite under its own floor reports
`out-of-coverage/insufficient_coverage`, never `fail`. One conversion was done as the worked
example — `granite_embedder_conversion_preflight.py`, where "tree not downloaded" and "staged
weight wrong size" both used to produce `blocked`/exit-1 and now report `out_of_coverage` with a
cause code. The commit message is explicit that **CJ-8/CJ-9 stay open**: roughly 94 more
call sites across two child clones were surveyed and left unconverted, several deliberately —
`v7_quality_gate_compare.py` must become exit-2 rather than pass, or a thin candidate promotes,
and that blast radius is not a mid-pass unilateral call.

**Cross-repo naming ratification.** Two three-valued contracts existed for the same state:
epyc-orchestrator's `verification_report.schema.json` (already ratified) spells it `inconclusive`;
this session's CJ-8 module, one day old, spelled it `out-of-coverage`. Ratified rather than
picking a winner by fiat: `inconclusive` is canonical **on the wire** (already-ratified, and
renaming a cross-repo schema to match a one-day-old module would run backwards); `out-of-coverage`
survives as CJ-8's in-code vocabulary, because at the gate plane the useful thing to say is which
items the checker never reached; `to_verification_outcome()` is the mandatory boundary translator.
The schema's own `inconclusive_reason` field was widened from free text to the closed 9/10-code
registry (root vs. orchestrator side each name their own count) so reasons are countable instead of
each producer inventing its own string. Landed via
`scripts/operator/ratify_three_valued_verdict_naming_20260907.sh`: `3adbd63d` in epyc-root
(comment-only, +8/-0, no rename/test/behaviour change), `8b740065` in epyc-orchestrator.

## Rows filed BY today's work, not planned in advance

Seven rows exist only because executing the original 19 surfaced them, not because Stage-3 planned
them: **SC61** (`claim_statement_binding/v1`, the producer SC56's `attested` binding is missing),
**SC62** (wire FM-5 into the belief kernel — filed and closed same day), **SC63** (wire RA-13b's
blind read-back outcomes into the belief kernel), **SC64** (the sequential-certification-that-
cannot-fail gap `impact.py`'s fix exposed), **AIR-12/AIR-13/AIR-14** (probe-bundle repair,
advisory `.index-graph.json` consult, and a nullable `screen_result` field — all filed from the
single AIR-11 measurement). Counting only rows still open at end of session against this wave:
SC60, SC61, SC63, SC64, RA-13a, CJ-8, CJ-9, RC-11, RC-12, GC-6, AIR-12, AIR-13, AIR-14 — 13 open
rows carried forward, against 6 closed same-day (SC56, SC57, SC58 [closed as a found defect,
not a pass], SC59, SC62, AIR-11).

## A peer session's status update, superseding the note below

The "Open" item below about a concurrent research-intake session holding `intake-1311`…`1330`
uncommitted describes a state that **no longer holds**. That peer (session
`session_01R5dfS8fW7GueW8AMHxsvWm`, Fable 5.1, same shared clone) committed its own work directly
to `main` between 19:37 and 19:41: `660203a1` (`intake-1311`…`1345` + an `intake-408` re-dive, 26
entries), `38af710b` (Vidya source rows SC65–SC68, Tulving provenance fixes in the wiki), `e3880ef6`
(Stage-4: 224 ledger rows routed, 3 new stubs INF-72/RTG-55/EVL-50, riders in 37 handoffs, OP-42),
and `10daa1c8` (its own progress note on merge posture). None of those four commits carry this
session's `Claude-Session` trailer and none is reviewed or claimed by this wrap-up — they are
reported here only so the open item above is not read as still-true.

## This wrap-up is PARTIAL — two subagents still running, not reported here

1. **A presence-vs-integrity audit of `scripts/vidya/`** (row Q.1) — result not in.
2. **The CJ-8/CJ-9 gate-conversion batch across three repos** — continuation of the ~94-call-site
   conversion the `9c86adb8` commit message left explicitly unconverted. Result not in.

Neither is guessed at here. The next wrap-up must fold their results in once they land.

## Also true at close of this wrap-up, neither is this session's to resolve

- `main` is **~233 commits behind `origin/main`** (own-session commits are 2 ahead of the same
  merge-base check the earlier note ran; this is a large merge, not a fast-forward — standing OP-11
  posture applies before any promotion).
- Current `git status` in `/workspace` carries live coordination/dashboard churn
  (`coordination/session-bus/advisory.jsonl`, `alarm_state.json`, `relay_state.json`,
  `dashboard/static/loop.html`, `scripts/vidya/fold.py`, `scripts/vidya/projection.py`, plus several
  `.bak-*` files and untracked coordination lock/state files) that this session did not stage and
  this wrap-up does not touch — consistent with the two subagents above still being in flight and
  with this being a shared, multi-session working tree.

## Index-state check (read-only, run for this wrap-up)

`.../epyc-orchestrator/.venv/bin/python scripts/handoffs/index_state.py --check` → **`0 problem(s)`**,
exit 0. No prune candidates surfaced by the check itself. Per the standing caveat, `open == 0` on a
row is **not** proof of completion by itself — compatibility pointers, prose-stated work, and
notes-only files are known false positives for that signal, and none of today's newly-closed rows
(SC56/57/59/62, AIR-11) were verified via `open == 0` alone; each closure above is backed by a named
commit and diff-stat, not the generated rollup.

## One-line status per remaining open row from this wave

- **SC60** (obligation discharge-leverage ranking) — filed, unworked; no subagent dispatched against it yet.
- **SC61** (`claim_statement_binding/v1` producer) — filed as a dependency of SC56 the same day SC56 landed; not started.
- **SC63** (wire RA-13b outcomes into the belief kernel) — filed the moment RA-13b landed (same-day-as-producer rule); not started.
- **SC64** (sequential certification that cannot fail) — filed from the `impact.py` fix's own audit trail; design question flagged as not fixable inline, not started.
- **RA-13a** (blind read-back N=20 pilot) — harness built and tested; the pilot run itself needs live model calls and is operator-gated, so it cannot self-execute.
- **CJ-8 / CJ-9** (three-valued gate verdicts / resolved coverage) — contract shipped and one call site converted as the worked example; ~94 more call sites surveyed and left unconverted, several deliberately (blast-radius risk to live promotion/safety gates in two child clones) — this is the batch the still-running subagent is continuing.
- **RC-11 / RC-12** (false-accept/false-reject split / threshold-selection audit) — one worked example fixed (the PII fixture); the wider ~110-threshold audit is recorded in a subagent report, not yet actioned into fixes.
- **GC-6** (two-axis reviewer split evaluation) — filed from intake-1304/1305; no work started, no subagent dispatched.
- **AIR-12 / AIR-13 / AIR-14** (probe-bundle repair, advisory readiness consult, nullable `screen_result`) — all three filed from the single AIR-11 measurement the same day; none started.

## Contract compliance note

Per `agents/commands/wrap-up.md` and the *Wrap-up cadence* section of `SESSION_LIFECYCLE.md`: this
extension is the progress-report and checkbox-sync step for the rows closed this wave; the checkbox
edits themselves were already applied inline by the commits above (`fe91818d`, `51f9ef61`,
`85d27f53`, `5a630e2a`, `157f075d`), not by this file. Index **pruning** and the **wiki compilation
sweep** are the two steps that stay on operator cadence — nothing here performs either; the
`index_state.py --check` run above is read-only and found nothing to prune. No git commit, `git
add`, `git checkout`, checkbox flip, or index-row edit was made in preparing this note — per ruling
(b), those are the owning session's to apply.
