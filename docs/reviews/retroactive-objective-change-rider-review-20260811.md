# Review: "Rider — retroactive objective change" (f272bb4e)

**Reviewer**: auditor (Fable 5, xhigh), 2026-08-11, at operator request for an independent read.
**Method**: every number and code cite independently re-derived (subagent sweep over the journal
shards, live re-run of the readjudication script, test-suite execution — 39 green); judgment on
this thread. Verdict first, then the four questions, then what I got wrong myself.

## Verdict: AGREE, WITH THREE AMENDMENTS — the rider mostly breaks the pattern it fears

The architecture claim is the genuine article, not articulate description: the journal stores raw
**components**, never scalarizations; the objective vector is **derived at read time** from the
row's own recorded policy; and that path is not just exercised-once-in-anger — it is **pinned by
passing yes-path tests** on both the policy-tagged and policy-absent branches
(`test_objective_rate_flip.py`, re-run green tonight). That is the write-side discipline that
`benchmarks/results`, the Gemma capture, and the era-inference mess all lacked. The coverage
table is honest: **every cell re-derived exact** (1372 trial rows; 1372/1147/523/534/0), the
shard set is complete (the `_1` rotation shard is included; the 18 `.bak`/archived siblings are
timestamped duplicates of the same trial-id space, not missed history), and the "gaps" in the
partial fields decompose entirely into crash/skip/invalid trials plus one benign probe type —
**the writer never silently broke**. Coverage since the hook is effectively 100% of
eval-executing trials; the boundary is clean and temporal, which is era-boundary-shaped, exactly
as the rider recommends treating it.

But the operator's summary sentence — *a decision made now can be unmade later at acceptable
cost* — survives only in an amended form: **forward at full fidelity; history re-scorable but
era-stratified; stopped AND starved candidates re-identified but re-priced, never unmade.** The
three amendments:

### Amendment 1 (to F1): the silent legacy fallback cannot refuse — the lens finding

`_policy_aware_objectives_from_row` on a policy-absent row silently returns the legacy
interpretation: the tokens/s `speed` field read as if it were the live rate axis
(`tier_specs.py:368-369`; pinned by `test_unstamped_row_defaults_to_legacy`). This is designed
and tested — but it means a cross-policy aggregate (any re-aim spanning trial ~778) silently
**commensurates tokens/s with qph and nothing can say no**. The reject-path lens inverts here:
the yes-path is tested; what is missing is a refusal path for cross-policy comparison. "The
4-axis re-aim is fully retroactive" should read "fully re-scorable, **within policy-era strata**"
— and the machinery already stratifies (the sequential re-adjudication groups by candidate×era,
141 groups). Make the stratification a stated condition of F1, and add an incommensurability
guard at any aggregation point that would mix strata.

### Amendment 2 (to F2): stopping is the discrete half — ALLOCATION is the continuous exception

F2 is right and deep, but it names only the visible case. The sequential allocator does not just
stop candidates; it decides **who gets the next trial**, so the evidence *density* everywhere is
shaped by the old metric. Re-derived tonight: across 141 candidate×era groups, **min 1 / median 1
/ max 41 trials; 63.8% of candidates have exactly one trial; the five evidence-dense candidates
(k≥15, 96 of 393 trials) are ALL refuted.** Rescoring a k=1 candidate under a new metric is
retroactive in arithmetic and void in inference — **scores are retroactive; statistical power is
not, and gates act on power.** This is the class the rider calls safe that is actually
irrecoverable-in-place: cross-candidate comparability under the new metric at today's trial
distribution. What survives: the power map is itself recomputable from the journal, so a re-aim
can *price* its own regeneration budget — which is what "acceptable cost" must be defined to
mean. The rider should say this in F2's own voice.

### Amendment 3 (to SEQ-B2): right task, insurance not capability — and fix the tense

The refutation counterfactual is **already recoverable read-side today**: re-running the
readjudication attributes every refuted candidate cleanly (6 quality-axis, 3 rate-only, 0
unexplained), and the three named candidates (`70902e4b` k=40, `dd793a6e` k=24, `85c3dcf2` k=15)
are confirmed **rate-only refutations with healthy quality** — precisely the
quality-favoured class the operator may later want. So SEQ-B2's write-side capture adds
insurance against the `seq` fields ever going partial (the `benchmarks/results` lesson), not a
new capability — worth doing for exactly that reason, cheaply. The false-comfort risk is real
but is a tense problem: the record must identify who deserves **re-evaluation** and must never
read as **re-runnable** — a regenerated trial is new-era evidence of a new
candidate-environment pair. Stamp the era tuple at stop time and word the record accordingly.

## The four questions, directly

1. **F1 sound, table honest?** Yes and yes — every figure re-derived exact, no shard
   undercount, no broken writer. Two of its cites need cosmetic fixes
   (`tier_specs.py:344-366` should be `:344-369` — the cited range currently stops short of the
   very dispatch/fallback lines it is about; `JournalEntry` is 191-264). Amendment 1 applies.
2. **F2 the right exception?** Right but half. Amendment 2 names the bigger, continuous one.
   The direction the rider worried about — something called irrecoverable that is actually safe
   — has one instance: axis attribution of past refutations, which is derivable today (see
   Amendment 3), so F2's implicit "we cannot even tell who to reconsider" is too pessimistic.
3. **F3 load-bearing?** Yes, at exactly one-line strength — keep it because the operator's own
   context names the knee, and pre-registering "normalization is a ratified quantity" is the
   cheapest possible guard against the normalization silently doing the real work later. One
   addition: hypervolume *forces a reference point to exist*, not to be ratified — name the
   current reference point in the same future era row.
4. **SEQ-B2 false comfort?** As written, mildly — Amendment 3 fixes it. File it with the era
   stamp and re-evaluation wording, and note the read-side derivation as the current source of
   truth it insures.

## What I got wrong en route (symmetry requires it)

- I planned an era-validity attack on the quality axis via the `E9-routing-reward` boundary
  (pre-2026-07-21 reward values demote-to-prior). **Withdrawn**: my re-derivation subagent
  caught the scope conflation — `routing_reward` governs the QScorer/routing-reward pipeline,
  structurally disjoint from the journal's eval-harness `quality` (`fraction_correct × 3`).
  The rider's own independence section guards against exactly this error class; I nearly made
  it while reviewing for it. The general point survives only via `eval_quality` eras, which the
  candidate×era stratification already handles.
- I expected no yes-path test of the recompute path. Wrong: both branches are pinned and green.
  The lens finding is Amendment 1's refusal gap, not a missing yes-test.

## One hygiene flag (outside the rider, found during re-derivation)

`orchestration/` holds 18 backup/`.bak`/archived copies of the same trial-id space beside the 2
live shards; a recursive glob would count **7568 trial-like rows against the true 1372** (5.5×).
Nothing live mis-counts today, but the trap is armed. Recommend the backups move out of
`orchestration/` (or a manifest names the canonical shard set) before some future tool globs
recursively.

## Bottom line for the operator

Accept the rider **as amended**. Your position is safe in its forward direction and priceable
backward — but "unmade at acceptable cost" is the wrong verb. A metric change re-prices history:
scores recompute (within policy strata), power does not (median candidate has one trial), and
the price list — era stratification, an incommensurability guard, the regeneration budget for
the stopped-and-starved, ratified normalization if knee-selection ever lands — must be written
at decision time, which is what the amended SEQ-B2 and the era-row recommendation do. The rider
is the first artifact today that mostly earns the claim; with the three amendments it fully
earns it.
