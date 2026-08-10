# R1 / R2 — Retraction and certified absence through stratified negation

**Status:** research note. **R1 is UNRESOLVED**; this document states it precisely, records the
partial results obtained, and names what would settle it. **R2 is scoped**, with one hard
constraint that removes an entire implementation approach.
**Date:** 2026-08-09
**Owning handoff:** [`handoffs/active/vidya-belief-substrate-program.md`](../../handoffs/active/vidya-belief-substrate-program.md) §R1, §R2
**Program spec:** [`docs/design/vidya-research-program.md`](../../docs/design/vidya-research-program.md)

Nothing here may be cited as established. The pilot does not depend on any of it: its rule set is
positive, where the published Deletion Property applies directly.

---

## 1. Why the v1 framing was wrong

The v1 draft treated stratified negation as an *optimization* gap — zero-substitution was assumed
correct, and the open question was whether an affected-set algorithm could avoid a full refold. The
2026-08-09 audit inverted this.

**Once absence is tracked, zero-substitution is not merely slow — it is wrong.** Grädel & Tannen
(arXiv 1712.01980) §5 gives a worked counterexample: deleting facts from a model collapses the
positive provenance polynomial to `0` while the updated model still satisfies the query. The
polynomial said "no support survives"; the model says the claim holds. A system that trusted the
substitution would have retracted a true belief.

The correct primitive is **specialization** of a dual-indeterminate, model-compatible provenance
object:

- annotate absence with dual tokens under the contract `x · x̄ = 0` (a quotient, so no monomial
  ever contains both);
- compute provenance once over *both* polarities;
- any update — insertion or deletion — is the specialization that zeroes the tokens of literals
  that fail in the new model.

The derivations a deletion *creates* are therefore pre-materialized as `x̄`-monomials and merely
**activated**. Because the update map is a homomorphism, it commutes with provenance computation,
which is what makes "compute the circuit once, update by substitution" sound rather than merely
convenient.

---

## 2. R1 — the residual theorem, stated precisely

### 2.1 What is already certified

Grädel & Tannen, *Provenance Analysis for Logic and Games* (Moscow J. Comb. Number Theory
9(3):203–228, 2020; arXiv 1907.08470v2) constructs the dual-indeterminate ω-continuous power-series
semiring `N∞[[X, X̄]]` (Def 29) and proves its universality for ω-continuous targets (Prop 30).

For **posLFP** — least fixed points over dual-annotated *input* literals, which is exactly the
semipositive shape of one stratum — provenance is well-defined, Kleene-computable, and provably
equal to the reachability-game valuation (Def 40, Prop 41, Cor 38).

**Consequence for a single stratum:** retraction-as-specialization is sound, because least fixed
points commute with the ω-continuous evaluation homomorphisms of Prop 30.

### 2.2 What is not certified, in the sources' own words

The same paper states (p.19) that its route is *"not available for important fixed-point formalism
such as the modal μ-calculus, **stratified Datalog**, transitive closure logics"*.

A bounded literature search on 2026-08-09 found **no dedicated semiring-provenance treatment of
stratified Datalog at all**. The frontier stops at negated *input* predicates (semipositive) and at
full LFP via `S∞[X, X̄]` (CSL 2021). *Recorded so a future session does not repeat the search.*

### 2.3 The theorem EPYC would have to prove

> **Conjecture (stratum-boundary re-tokenization).** Let `P` be a stratified program with strata
> `P₁ … Pₙ`. Evaluate stratum `k` over `N∞[[Xₖ, X̄ₖ]]`, obtaining for each derived atom `a` a pair
> `(π⁺(a), π⁻(a))` of presence and absence provenance. Freeze those pairs and re-tokenize each as a
> fresh dual pair `(x_a, x̄_a)` in the indeterminate set of stratum `k+1`. Then:
>
> **(a) Agreement.** The object computed by evaluating `P` stratum-by-stratum under this
> re-tokenization coincides with the provenance assigned by the perfect-model semantics of `P`.
>
> **(b) Exactness of retraction across the boundary.** For any retraction of a base fact, applying
> specialization within each stratum bottom-up yields the same result as recomputing `P` from
> scratch without that fact — *including* the case where the retraction flips a lower-stratum
> greatest-fixed-point value and thereby flips a token of the stratum above.

**What is already in hand:** the construction is **well-typed**. Derived `(presence, absence)`
pairs again satisfy the dual-token contract — GT17 Prop 12 shows that if `π(L)·π(¬L) = 0` for all
literals then `π⟦φ⟧·π⟦¬φ⟧ = 0` — and Prop 14 / Prop 30 universality then make substituting them for
fresh indeterminates a well-formed homomorphism. So the object exists and is of the right shape.

**What is missing is that the object is the *right* one** (part a), and that specialization stays
exact across a boundary where a retraction can *add* higher-stratum facts (part b). Part (b) is the
harder half and the one with no analogue in the positive fragment: within a stratum, deletion is
monotone downward; across a boundary it is not.

### 2.4 Attempted reduction, and why it fails

The natural attempt is to reduce (b) to the positive case by treating each stratum's inputs as base
facts and applying the Deletion Property per stratum, then composing by induction.

**Where it breaks.** The Deletion Property (Bourgaux et al., KR 2022, Property 13) is stated for a
*fixed* base-fact set with annotations set to `0`. Across a stratum boundary the base set of
stratum `k+1` is not fixed under the retraction: zeroing a token in stratum `k` can make a negated
condition true and thereby **introduce** an atom into stratum `k+1`'s input. That is an insertion,
not a deletion, and Property 13 says nothing about it. Table 1 of the same paper does list an
Insertion property — but it holds for a different (overlapping) set of semantics, and composing a
deletion-at-stratum-`k` with an insertion-at-stratum-`k+1` is not covered by either result
individually.

So the induction has a genuine gap at exactly the step the conjecture is about. This is a partial
result, not a proof: it establishes that the obvious route does not close, and localizes the
difficulty.

### 2.4b Counterexample search — executed 2026-08-09, no counterexample found

> **⚠ Superseded by §2.4c (2026-08-10): this null is vacuous.** The two routes below are the same
> computation, so their agreement is not evidence. Read §2.4c for the result that replaces it.
> Retained unedited because how a vacuous comparison passed a mutation test is the useful part.

The conjecture was not left as an assertion. Two independent evaluators were implemented
(`scripts/vidya/r1_search.py`) and compared exhaustively over small two-stratum programs:

- **Route A (incremental)** — evaluate stratum 1, specialize by zeroing the retracted token,
  freeze and re-tokenize the resulting pairs, evaluate stratum 2 against them.
- **Route B (ground truth)** — delete the fact and recompute both strata from scratch.

| | |
|---|---:|
| (program × fact-assignment × retraction) instances checked | **5,670** |
| Counterexamples found | **0** |
| Max facts **added** by a retraction (boundary growth observed) | **2** |

Two things make this a result rather than a null:

1. **The search exercised the phenomenon.** Boundary growth was observed — retractions genuinely
   added higher-stratum facts in the corpus, which is the exact case the conjecture is about. A
   sweep that never triggered growth would have proved nothing.
2. **The harness has demonstrated detection power.** A mutation test replaced route A with the
   naive-but-plausible implementation that evaluates negation against the *pre-retraction* lower
   stratum. That variant produced **2,715 counterexamples out of the same 5,670 instances**. So
   the comparison can see a wrong answer; it simply does not see one for the real implementation.

**This is a bounded verification result, not a proof.** It rules out the conjecture failing for a
simple structural reason at this program size, and nothing more. Larger programs, deeper strata,
and non-two-valued absence remain unexplored. The honest classification is *unresolved, with
supporting evidence* — which is a materially better position than *unresolved* and is exactly the
kind of result the R-track was supposed to produce.

### 2.4c Retraction — the 2026-08-09 null was vacuous, and the real result is a refutation plus an exact route

**Correction to §2.4b.** Route A and Route B as implemented on 2026-08-09 are the same
computation. Route A specialized the base by setting the retracted token to ⊥ and then dropped ⊥
entries; that yields exactly Route B's "base with the fact deleted", after which both call the
identical stratum-1 and stratum-2 evaluators. Two names for one expression cannot disagree, so
5,670 agreements measured nothing. The mutation test recorded alongside it remains sound — it
showed the *harness* detects disagreement — but it could not show the routes were distinct, which
is how it was read. `test_reevaluation_route_is_ground_truth_by_construction` now pins the
equivalence so the vacuity cannot be rediscovered as a result.

The conjecture only has content for a route that **reuses prior work**. Three such routes were
implemented and swept over the same 5,670 instances on 2026-08-10:

| Route | What it reuses | Counterexamples / 5,670 |
|---|---|---:|
| Re-evaluate each stratum (the 2026-08-09 "route A") | nothing | 0 — *by construction; vacuous* |
| **Circuit specialization** — record stratum-2's provenance circuit over frozen tokens, substitute new lower values | the recorded rule nodes | **2,241 (39.5%)** |
| **+ dual tokens** — record a node whenever the *positive* body is derivable, evaluate the negative guard at substitution time | nodes + deferred guards | **270 (4.8%)** |
| **+ intra-stratum closure** — additionally record any rule whose positive body atoms are heads of already-recorded rules | the closed node set | **0** |

**The naive incremental route is refuted, with a two-rule counterexample**: `p :- a`, `r :- not p`,
retract `a`. Before the retraction `p` holds, so `r :- not p` never fires and the circuit has no
node for `r`; after it, `r` should hold and the circuit has nowhere to derive it. This is the
"deletion composed with an insertion" that §2.4 predicted from Property 13's shape — now exhibited
rather than argued.

**The dual-token repair is the one R2 independently arrived at**, and it removes 88% of the
failures: carrying a negated atom as a dual token x̄ into the circuit, instead of baking its
record-time value into the decision to record a node at all, lets a rule that *starts* firing have
a node to fire in. The 270 residual failures share one shape — intra-stratum chaining off a
negation-derived atom, `s :- r` where `r` itself only becomes derivable after the retraction — and
closing the recorded set under intra-stratum positive dependency covers exactly those.

**The bounded positive result** is therefore sharper than the one it replaces: *dual tokens plus
intra-stratum dependency closure is exact across a negation boundary over an exhaustive sweep of
small two-stratum programs*, and the two weaker routes are refuted rather than unverified. The
proof remains open, and so does the question that decides whether any of this is worth doing:

> **The exact route retains 91.7% of stratum-2 rules (8,910 of 9,720) as circuit nodes.** At this
> program size it saves 8.3% of the work versus full re-evaluation, which is not a reason to build
> it. The closure is small only when a retraction's negation-reachable set is a small fraction of
> the stratum, and whether real programs have that shape is **unmeasured**.

### 2.4e Depth 3 — the dual-closed route survives composition (2026-08-10)

The §2.4c result bounded two-stratum programs. The obvious way an exact-at-one-boundary route can
still fail is COMPOSITION: a re-tokenization that is exact once need not stay exact when its own
output is re-tokenized again. So the sweep was extended to three strata —
`scripts/vidya/r1_depth3_sweep.py`.

| | |
|---|---:|
| (program × assignment × retraction) instances | **40,500** |
| Counterexamples to dual tokens + intra-stratum closure | **0** |
| Counterexamples to plain circuit specialization (*detection control*) | **16,911** |
| Max facts added by a retraction (boundary growth across two boundaries) | **3** |

The control is what makes this a result rather than a null. Plain circuit specialization was
already refuted at depth 2, so running it here asks whether the harness can see a wrong answer at
this depth: it sees 16,911 of them. Boundary growth of 3 confirms retractions genuinely add facts
across both boundaries, so the composition case is exercised rather than skipped.

**A bug found first, and it matters more than the number.** The initial depth-3 run reported 1,836
counterexamples to the dual-closed route. Every one had the shape `s :- r` listed BEFORE the rule
deriving `r` in the same stratum — `_eval_stratum2` was a single pass, so rule ORDER changed the
meaning of a stratum and the *ground-truth* evaluator was wrong on both sides of the comparison. A
refutation was sitting there, fully formed and completely spurious, and the only thing between it
and the record was suspecting the test method before believing the result. The evaluator now
iterates to a fixpoint; the two-stratum numbers are unchanged (those rule sets happened to be
order-independent) and the property is pinned by test.

Still not a proof, and the same caveat as §2.4c applies: the exact route retains most of the
stratum, so this bounds the conjecture without making the route worth building.

### 2.4d R1b-usecase — the first rule that genuinely needs negation, named 2026-08-10

R1b has been a paper track because the pilot's rule set is positive (spec §12), so there was no
negation stratum to measure a closure fraction on. Naming the rule that creates one is the
prerequisite, and it turns out **two of the three candidates on the shortlist do not need negation
at all**:

| Candidate rule | Needs stratified negation? |
|---|---|
| "no unretracted opposition exists" | **No.** The fold materializes opposition, so the gate tests it positively after the fixpoint closes (`con_ok`). |
| "no fresher measurement supersedes this" | **No.** Same shape — supersession is materialized, then read. |
| "this correction is discharged" | **Yes**, and it is the first one that is. |

Negation-as-failure is only *needed* when a derived fact depends on the non-derivability of another
fact **inside the same fixpoint**. Testing a materialized relation afterwards is not that; it is
ordinary evaluation followed by a filter, which is what the gate does today.

**The rule that qualifies: correction discharge over the transitive dependency closure.**

> A correction is DISCHARGED when no claim that transitively depends on it remains flagged.

Both halves are load-bearing. *Transitively* makes the dependent relation recursive — `depends_on`
edges compose, so a claim can inherit a flag through a chain. *No claim remains flagged* is
negation over a relation derived in the same program: whether a dependent is still flagged is
itself computed from corrections, dependency alerts, and their reviews. That is a genuine
stratified-negation rule, not a post-hoc filter.

It is also wanted rather than hypothetical. **678 claims currently sit `review_required` with no
closure rule at all** — the flag is set by corrections and dependency alerts, and nothing in the
system can ever say a correction is finished. That is the same one-way-ratchet shape the
`correction_reviewed` frame was introduced to break at the single-claim level, reappearing at the
level of a correction's whole blast radius.

**What this unblocks, and what it does not.** With this rule the pilot acquires a negation stratum,
so `R1b-closure-size` becomes measurable on a real program rather than on toy sweeps — and the
91.7% closure fraction that made the exact incremental route look pointless can finally be
re-measured where it matters. It does not unblock `R1b-proof`; the theorem is unchanged.

### 2.5 What would settle it

1. Either a proof of (a) + (b), likely via the game semantics — the posLFP result is proved through
   reachability games, and stratified negation corresponds to alternating reachability/safety, so
   the game-theoretic route is the one with a shape that might extend.
2. Or a counterexample: a two-stratum program and a base-fact retraction where stratum-wise
   specialization disagrees with a from-scratch recomputation. **A counterexample is a perfectly
   good outcome** and would immediately settle the engineering question — full refold across strata,
   permanently.
3. Either way: asymptotic and empirical boundary-growth measurement. A proof that does not bound
   how many higher-stratum facts a single low-stratum retraction can add is not usable for
   scheduling.

### 2.6 What the pilot does meanwhile

The pilot's rule set is **positive**. Where negation is eventually wanted, the spec requires the
negated strata to be excluded from incremental retraction and handled by full refold, which is
exact by definition relative to the ledger. **The unresolved theorem can therefore affect latency
and nothing else** — which is the property that lets the pilot ship while the question stays open.

---

## 3. R2 — certified absence, and the constraint that removes an approach

### 3.1 Grounding

Absence is expressible in the same discipline: certified absence of `φ` is the provenance of
`nnf(¬φ)` over dual tokens, and a value of `0` there is certified validity (GT17 Cor 21; CSL 2021
Prop 20). An absence certificate is an absorption-dominant Falsifier-side strategy (CSL 2021
Thm 23).

### 3.2 The hard constraint

**Greatest fixed points do not specialize.** GT17/1907.08470 Example 42 gives an explicit
counterexample: gfp values fail to specialize correctly from `N∞[[s, t]]` down to `N∞`.

Two binding consequences:

1. Absence certificates **cannot** use the incremental specialization path that works for presence.
   That is not a performance note — it removes an entire implementation approach.
2. They must route through the absorptive, chain-positive generalized-polynomial semiring with dual
   indeterminates, `S∞[X, X̄]`, where well-definedness (CSL 2021 Thm 6), closure ordinal ≤ ω
   (Prop 19) and universality (Thm 17) are all proven for the class the carrier belongs to.

**The good news is that this is affordable on EPYC's carrier.** `Q × T` is meet-idempotent, so
`a^∞ = a`, and Naaf's closed form collapses to `gfp = F^N(F^N(1))` — roughly `2N` iterations, no
fixpoint test. The expensive-sounding route is cheap here specifically because the carrier is a
finite lattice.

### 3.3 A second, sharper limitation

For *derived* (fixed-point) facts, the base-case source is explicit (1907.08470 p.18): when
`π⟦φ⟧ = 0` we get **no reason why**. Negation of a least-fixpoint formula is a *safety* game, not a
reachability one, and the machinery that explains presence does not run backwards.

So absence-of-a-derived-fact is strictly harder than absence-of-an-input-fact. **The pilot claims
neither**, and any absence answer it gives must be scoped to the exact authenticated domain it can
actually prove — key non-membership over a canonical key set, or completeness over a declared scan
boundary — never "we looked and found nothing".

### 3.4 Complexity: an unmeasured surface

There are **no size or complexity bounds for both-polarity provenance under recursion**. The
circuit results (Deutch et al. ICDT 2014; Fan–Koutris–Roy PODS 2025) are for the positive fragment.
There is no dual-indeterminate circuit theorem — EPYC would be proving the first one. GT17's own toy
example inflates 6 monomials to 34 before quotienting, and absorption (finite antichains, CSL 2021
Prop 14) is the only stated mitigation.

### 3.5 Application precedent

Xu, Zhang, Alawini & Tannen, *Provenance analysis for missing answers and integrity repairs* (IEEE
Data Eng. Bull. 41(1):39–50, 2018) is the only published application of the dual-indeterminate
treatment to explaining *missing* query answers — the R2 use case. Cited as precedent, not
foundation (operator decision 7, 2026-08-09).

---

## 4. Truth-preservation caveat for both tracks

`N[X, X̄]` and `S∞[X, X̄]` are `+`-positive but **not positive** — they have zero divisors by
construction, since that is what `x · x̄ = 0` means. So "value ≠ 0 iff true" holds only for the
model-defining and model-compatible interpretation shapes (GT17 Props 9–13; CSL 2021 Prop 20).

Any certifier built on this must check that its interpretations stay in that shape. A certifier
that assumed positivity would silently accept a `0` as "false" when it actually means "these two
tokens cancelled".

---

## 5. Status summary

| Item | Status |
|---|---|
| Per-stratum specialization is sound | **Certified** (1907.08470 Def 29/Prop 30/Def 40/Prop 41/Cor 38) |
| Cross-stratum re-tokenization is well-typed | **Established** (GT17 Prop 12 + Prop 14/Thm 17 universality) |
| Cross-stratum agreement with perfect-model provenance | **UNRESOLVED** — conjecture §2.3(a) |
| Cross-stratum retraction exactness | **UNRESOLVED** — conjecture §2.3(b); obvious reduction shown not to close (§2.4) |
| Stratified-Datalog provenance in the literature | **Does not exist** (bounded search 2026-08-09) |
| Certified absence via `nnf(¬φ)` over dual tokens | **Grounded**, scoped to input-level absence |
| gfp specialization | **Refuted** (Example 42) — route through `S∞[X, X̄]` |
| gfp cost on the `Q × T` carrier | **Cheap**: `F^N(F^N(1))`, ~2N iterations |
| Reasons for absence of a *derived* fact | **Not available** in this framework |
| Complexity of both-polarity provenance under recursion | **Unmeasured**; no dual-indeterminate circuit theorem exists |

**Neither R1 nor R2 gates the pilot.** Both would gate a promotion that wanted incremental
retraction over a rule set with negation, which is not what is being built.
