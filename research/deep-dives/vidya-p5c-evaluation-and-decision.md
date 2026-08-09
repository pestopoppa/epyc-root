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
