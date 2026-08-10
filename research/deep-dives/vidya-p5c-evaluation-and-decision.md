# P5c — Gold-corpus evaluation and promotion decision package

**Date:** 2026-08-09 · **Verdict: ITERATE** (not promote, not terminate)
**Owning handoff:** [`handoffs/active/vidya-belief-substrate-program.md`](../../handoffs/active/vidya-belief-substrate-program.md) §P5c
**Corpus:** [`docs/design/vidya-pilot-corpus.md`](../../docs/design/vidya-pilot-corpus.md) (ratified)
**Harness:** `scripts/vidya/evaluate.py`, `scripts/vidya/gold_corpus.py`

---

## 1. Results

19 claims across four documented real corrections plus the E8 measurement family, run through the
four incremental mutation rounds.

| Round | Mutation class | Score |
|---|---|---:|
| 1 | source edit / retraction (E1, E3) | 7/7 |
| 2 | correction narrowing scope / anchor rot (E2, E4) | 7/7 |
| 3 | supersession + derived-claim propagation (E2, M) | 9/9 |
| 4 | era boundary / expiry / conflicting source (M) | 5/5 |
| **Total** | | **28/28** |

| Metric | Result |
|---|---|
| Invalidation recall | **1.00** |
| Discrimination (correct non-invalidation) | **1.00** |
| Harmful outcomes (−1: reported affected-as-untouched) | **0** |
| Incremental vs full-refold mismatches | **0** |
| Determinism (repeat + reorder) | stable across both, and across x86-64 and aarch64 |

Scoring is the HoH scheme adopted in the spec: **+1 correct / 0 abstained / −1 harmful**. Recall and
discrimination are reported separately and never merged — an engine that flags everything scores
perfect recall and zero discrimination, and one number would hide precisely that.

## 2. What the first run found — the part worth reading

The suite did not pass first time. It scored **20/28 with 4 harmful outcomes**, and every one of the
four traced to a *defect the evaluation existed to find*:

**Two were real engine bugs.**

1. **Retraction was per-frame; evidence is per-token.** One evidence token routinely supports several
   claims through several edges, and retracting a single edge left the same discredited evidence
   still supporting its other claims. This is the exact shape of the 2026-07-24 scorer artifact —
   one stale extractor underpinning two separate conclusions — so the corpus reproduced a real
   failure mode and the engine failed it. Fixed with `impact_of_retracting_evidence`, which
   retracts every edge carrying the token.

2. The same bug hid a second symptom in the M family, where a derived claim kept a stale support
   path after its source measurement was retracted.

**Two were gold-label errors, and correcting them is not grading on a curve.**

3. **E2's encoding gave two claims independent evidence** when in reality both rested on the same
   stale extractor. That models a world where one scorer fix could move one conclusion and not the
   other, which is not what happened. The encoding was wrong.

4. **m-c5 had been given `Witnessed` warrant outright**, which made a downgrade arithmetically
   impossible — a derived prior is not itself a protocol-admissible measurement, so under the
   ratified §4.2 definition its own warrant is `Verified`, and it inherits `Witnessed` only through
   the measurement it derives from. Retracting that measurement now correctly drops it to its own
   weaker warrant.

Both corrections make the corpus *more* faithful to what actually happened, and both were forced by
a failing test rather than noticed by inspection. That is the strongest evidence available that the
suite is doing work: it caught two engine bugs and two modelling errors in a system its own author
had just written and believed was correct.

## 3. Why the verdict is ITERATE and not PROMOTE

A perfect score on the gold corpus is necessary and nowhere near sufficient. Three findings from the
same session bound what this result means:

**The corpus is 19 hand-built claims; the real index is 4,191 and behaves nothing like it.** Every
gold claim is anchored, so every one is `claim-complete` and the impact report can verify
non-invalidation. On real data, **1 of 4,191 claims is anchored**, so the same engine reports
`0 verified unaffected / 4,190 unaffected-but-unmapped`. The engine is correct in both cases; the
*usefulness* differs entirely, and the corpus cannot show that.

**Independence is unmeasurable on real data.** 100% of real beliefs are fragile — zero have
corroboration — because claim IDs are minted per entry, so two sources can never support the same
claim (R4). Any policy using `disjoint_supports ≥ 2` currently always abstains.

**The retrofit cannot reach the traceability the policies want.** One claim clears a conjunctive
`Verified/Anchored` policy. The mechanism to fix that exists (P2b) and is written into the intake
skill as a Stage-2 obligation, but the backlog of unanchored dived claims is real.

Promotion criteria from the spec are otherwise met: determinism targets hit, high-risk invalidation
recall perfect on the gold corpus, no stale-as-current leak (tested across every gate outcome),
assertion and obligation mappings reviewable, rollback trivial because the pilot is additive.

## 4. What promotion should require

Ordered by what the evidence says matters, not by implementation cost:

1. **Anchor the claims that get cited** (P2d). The single number that would change the pilot's
   usefulness most is anchored-claim count. Scope it to claims a handoff or plan actually cites —
   not all 4,191.
2. **Cross-entry claim identity** (R4b). Without it, corroboration is permanently unmeasurable and
   one third of the policy vocabulary is inert. Human-gated by nature: deciding two differently
   worded claims are the same proposition is exactly the judgment the fold must not make.
3. **A query log and obligation-disposition recording** (R5b). These are write-time decisions;
   reuse and obligation-utility rates cannot be reconstructed later, so R5 stays unanswerable
   however long the pilot runs until they exist.
4. **Re-run this suite against a corpus drawn from the live ledger**, not hand-built frames — the
   gap between 28/28 here and `0 verified unaffected` there is the whole remaining question.

## 4b. Where the four requirements stand — reviewed 2026-08-10

The verdict stands at ITERATE, but three of the four requirements moved, and the reason the fourth
has not is now a priced decision rather than a vague one.

| # | Requirement | Status 2026-08-10 |
|---|---|---|
| 1 | Anchor the claims that get cited (P2d) | **The gap, and it is large**: 667 entries are cited by active handoffs, design docs and deep dives; **5 are anchored**. 662 cited entries / 2,994 claims remain unanchored. Needs an operator decision on machine-located anchors — see below |
| 2 | Cross-entry claim identity (R4b) | **Unblocked**: candidate generation reduced 4,191 claims to **45 reviewable pairs**. Awaiting the operator's `same`/`different` pass, which is a bounded afternoon, not a programme |
| 3 | Query log + obligation disposition (R5b) | **Done**: the frames existed but nothing emitted them, so the clock had not started. `vidya query` now logs by default; `vidya disposition` records outcomes |
| 4 | Re-run the suite against a live-ledger corpus | **Not started, and no longer blocked by anything.** This is the largest remaining evidence gap and the next executable step |

Requirement 2's unblocking also re-priced requirement 1. The alias generator found that
`source_id` is minted per entry, so two records of one paper read as two sources; four of the 45
candidates are same-source, and an index sweep found 5 duplicate-locator groups over 11 entries.
Corroboration measurement therefore needs source identity *and* claim identity, and both are now
instrumented.

### The decision requirement 1 needs

Anchoring 2,994 claims by hand is not going to happen, so the real question is whether a
**machine-located** anchor is admissible, and at what traceability level. A span found by matching
the claim's distinctive terms against the fetched source is checkable — `quote_hash` pins the
exact text — but it is not the same act as a person reading the passage and deciding it says what
the claim says. Recording it at T2 Anchored alongside human anchors would make the T axis mean two
different things; refusing it entirely leaves the axis permanently at 5 of 4,191.

Three coherent positions, with what each costs:

- **A — Machine anchors at T2, provenance-tagged.** Fastest path to a usable T axis; risk is that
  a confident wrong match is indistinguishable from a right one at query time, which is the
  fabrication shape this project has already been bitten by once.
- **B — A distinct level between Located and Anchored** (machine-located, quote-pinned, unreviewed).
  Keeps the axis honest and lets policies choose; costs a carrier change, which is a spec amendment.
- **C — Human-only anchors, scoped hard.** Anchor only claims cited by *ratified* specs rather than
  all cited claims — a few dozen, not 2,994. Slowest coverage growth, zero new trust surface.

Recommendation: **B**, because it is the only one that lets the backlog shrink without redefining
what an existing anchor means, and because the pilot's whole thesis is that a distinction worth
acting on is worth recording. C is the right answer if the carrier change is judged too expensive
for shadow mode.

## 4c. PR2 — the live-ledger evaluation, run 2026-08-10

`scripts/vidya/live_eval.py`, `vidya eval-live`. Two draws over the 9,599-frame ledger, six
mutation families each; the mutation is a **source retraction** (every support frame carrying an
entry's `source_id`), which is the "this source is discredited" event the gold corpus models.

| Draw | Score | Recall | Discrimination | Harmful | Retraction rows | **Uncoverable** |
|---|---:|---:|---:|---:|---:|---:|
| By citation count (most-cited entries) | 148/148 | 1.00 | 1.00 | 0 | **0** | **527** |
| Dived entries only (`--verified-only`) | 149/149 | 1.00 | 1.00 | 0 | 29 | **272** |

**The engine is correct on everything the live corpus can score. The finding is how little that
is.** Three results, none of them the score:

**The naturally-drawn corpus does not exercise retraction at all.** Of the 60 most-cited live
entries, 50 carry no verification and 9 are dived, so every family drawn by citation count comes
back `never_believed` and 148/148 measures floor discipline plus controls — not invalidation. The
retraction path only gets tested by deliberately drawing the other stratum, which is why
`--verified-only` exists. A suite reporting the first row alone would have looked like a pass.

**Uncoverable claims outnumber scored ones 2–4×.** 527 and 272 claims belong to entries that
*cite* the mutated entry. The engine reports them unaffected because the ledger holds no
cross-entry evidential edge — citation is not support — so scoring them either way would
manufacture an answer to the open question. They are counted and excluded. This is the honest
version of the 28/28-versus-real-data gap: the live graph has no propagation structure to test.

**Per-claim correction labels are not derivable at all.** `dive_corrections` is free prose with no
claim index, so which of an entry's claims a correction actually falsified is recorded nowhere a
program can read. That is a write-time gap of the same family as the query log: cheap at dive
time, impossible afterwards.

**A third instance of per-record identity.** Evidence tokens are minted per *claim*
(`evd_clm_intake_096_00`), so a token retraction reaches exactly one claim and the gold corpus's
sharpest family — E2, one stale extractor underpinning several conclusions — is not expressible
against live data through a token retraction. Claim identity, source identity, and now evidence
identity are all per-record. The source-level mutation is the workaround, not a fix.

A bug found while building it is worth recording, because it is the shape this project keeps
hitting: a leaked loop variable made every family retract the *last* candidate's source while
still reporting a plausible per-family score. It was caught by the test that asserts *which*
claims moved, not by the one that asserts a number came out.

## 5. What would justify termination

Recorded now, while the answer is not yet known, so the bar cannot drift later:

- anchoring cost per claim proving high enough that (1) does not repay itself across a few
  correction cycles;
- claim identity requiring constant human adjudication rather than converging;
- the gate blocking so often that consumers route around it — the risk the `correction_reviewed`
  frame was added to prevent, after the first live run found 652 claims permanently blocked with no
  way to clear;
- or the substrate turning into a second governance system rather than executing the existing one,
  which remains the stop-trigger the original audit named.

None of these is currently indicated.

## 6. Reproduce

```bash
repos/epyc-orchestrator/.venv/bin/python -c \
  "import sys;sys.path.insert(0,'scripts/vidya');import json;from evaluate import run_all;print(json.dumps(run_all(),indent=2))"
```

Deterministic: no clock, no network, no model. The corpus is frozen at the commit that lands this
file; changing it to make a later test pass requires an explicit amendment record retaining both
the pre- and post-amendment scores.
