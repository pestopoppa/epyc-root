# Vidya Research Program (R1–R5)

**Status:** open research obligations — none of these results may be cited as established
**Date:** 2026-08-09 (V2 revision; split out of the 2026-08-09 v1 draft)
**Owning handoff:** [`handoffs/active/vidya-belief-substrate-program.md`](../../handoffs/active/vidya-belief-substrate-program.md)
**Audit of record:** [`research/deep-dives/vidya-belief-substrate-audit.md`](../../research/deep-dives/vidya-belief-substrate-audit.md) §4
**Siblings:** [pilot spec](vidya-pilot-spec.md) · [architecture appendix](vidya-architecture-appendix.md)

---

## 0. Why this is a separate document

The formal program advances independently of whether the pilot is promoted, and the pilot must not
be able to depend on an unproven result by accident. Splitting them makes the dependency direction
explicit: **the pilot may use only what is already published and in-scope** (§1); everything here is
either an EPYC obligation or an optional line.

Two outcomes are independently legitimate and MUST be reported separately: the formal composition can
be sound while the deployment economics fail, and the deployment can pay for itself while a theorem
remains open.

---

## 1. What is already established (and may be relied on, within scope)

Verified against primary text during the 2026-08-09 audit. Scope limits are load-bearing — each one
is a place where a plausible engineering choice silently voids the result.

| Result | Scope limit that matters |
|---|---|
| **Deletion Property** — provenance on a reduced database equals the old provenance with deleted base tokens set to 0 | **Positive** Datalog; holds for P^AT/P^NRT/P^AM/P^SAM; **fails for minimal-depth semantics** |
| Semantics coincidence on absorptive semirings | requires absorption (and +-idempotence for the model-based pair) |
| Absorptive polynomials: finiteness of maximal monomials, universality | requires **fully continuous** semirings — ω-continuity is provably insufficient for greatest fixed points |
| Convergence in **≤ N steps** for 0-stable semirings | 0-stable = absorptive; the general p-stable bound is exponential and needs a separate result |
| Kleene termination in **N steps** for 1-bounded (absorptive) semirings | needs neither ω-continuity nor commutativity |
| Closed forms: `lfp = F^N(0)`, `gfp = F^N(F^N(1)^∞)` | absorptive, fully continuous, **commutative** |
| Poly-size provenance **circuits** for absorptive semirings | circuits, not formulas — formulas are provably exponential |
| Depth dichotomy Θ(log m) vs Θ(log² m); linear programs are NC²-parallelizable | covered program classes only |
| Replay consistency requires keyed logging of a nondeterministic judge (necessity + sufficiency) | boundedly nondeterministic oracles in a relational schedule model; deterministic or precomputed verdicts fall outside |
| Four-valued paraconsistent verdicts | thresholds remain a policy choice |

**Citation hygiene, corrected this revision:** say *fully continuous*, not ω-continuous; cite the
published LIPIcs numbering (the extended preprint renumbers everything); the "N × carrier-height"
bound is Kleene folklore and must not be attributed to the convergence paper — the citable result is
stronger; "N+1 iterations" is N Kleene steps plus a zero-init layer, distinct from the Newton n+1;
the five proof standards come from the 2009 chapter, not the 2007 paper; and the argumentation
dynamical-systems paper is KR 2018, with two distinct libraries (Java and Python) that are commonly
conflated.

---

## R1 — Exact retraction through stratified negation

### The problem, restated correctly

The v1 draft treated zero-substitution as *the* retraction primitive and named stratified negation
as an optimization gap. The audit found the framing inverted:

**Once negation is tracked, zero-substitution is provably the wrong primitive.** Deleting facts can
collapse a positive provenance polynomial to 0 while the updated model still satisfies the query —
there is a worked counterexample. The correct primitive is **specialization** of a dual-indeterminate,
model-compatible provenance object: annotate absence with dual tokens under the contract `x · x̄ = 0`,
compute once over both polarities, and let any update (insert *or* delete) be the specialization that
zeroes the tokens of literals failing in the new model. Deletion-created derivations are
**pre-materialized** as x̄-monomials and merely *activated*. The update map is a homomorphism, so it
commutes with provenance computation.

### What is certified, and where it stops

Certified: the per-stratum base case. Provenance for least fixed points over dual-annotated **input**
literals (posLFP / the semipositive shape) is well-defined, Kleene-computable, and provably equal to
the reachability-game valuation; retraction-as-specialization is sound *per stratum* because least
fixed points commute with the evaluation homomorphisms.

Not certified, and the papers say so: the same source states its route is **"not available for …
stratified Datalog"**. A bounded literature search on 2026-08-09 found **no dedicated
semiring-provenance treatment of stratified Datalog at all** — the frontier stops at negated input
predicates and full fixed-point logic. *(Recorded so a future session does not re-run this search.)*

### The EPYC obligation

> **R1 theorem to prove or refute.** Freeze stratum *k*'s (value, dual-value) pairs and re-tokenize
> them as fresh `(x, x̄)` pairs for stratum *k+1*. This composition is **well-typed** — derived
> (presence, absence) pairs again satisfy the dual-token contract, and universality makes the
> substitution well-formed. Prove that the composed object coincides with stratified / perfect-model
> provenance, and that specialization-based retraction remains exact **across** the boundary, where a
> retraction can flip a lower-stratum greatest-fixed-point value and thereby flip a token of the
> stratum above.

Deliverables: formal statement with every algebraic and program-fragment hypothesis; proof or
counterexample; explicit handling of negation-induced *additions* at the boundary; asymptotic and
empirical boundary-growth analysis; executable fixtures comparing incremental results against full
refold; and a result classification — proven, restricted, falsified, or unresolved.

**Until then:** the pilot's rule set stays positive, or excludes negated strata from incremental
retraction and handles them by full refold only. No implementation benchmark substitutes for the
proof, and no proof substitutes for boundary-cost measurement.

---

## R2 — Certified absence

### Grounding

Absence is expressible in the same discipline: certified absence of φ is the provenance of
`nnf(¬φ)` over dual tokens, and a value of 0 there is certified validity. An absence certificate is
an absorption-dominant Falsifier-side strategy.

### The hard constraint discovered by the audit

**Greatest fixed points do not specialize.** There is an explicit counterexample showing gfp values
fail to specialize correctly from the dual-indeterminate power-series semiring down to a concrete
target. Two consequences, both binding:

1. Absence certificates **cannot** be computed by the incremental specialization path that works for
   presence. They must route through the absorptive, chain-positive generalized-polynomial semiring
   (with dual indeterminates), where well-definedness, closure ordinal ≤ ω, and universality are all
   proven for the class the carrier belongs to.
2. On the ratified product lattice this is affordable: meet is idempotent, so `a^∞ = a` and
   `gfp = F^N(F^N(1))` — roughly 2N iterations. (The property is meet-idempotence, not totality;
   it survived the 2026-08-09 carrier change unchanged.)

Also recorded: for derived (fixed-point) facts, the base-case source explicitly gives **no** reason
why a query is false when its value is 0 — negation of a least-fixpoint formula is a *safety* game,
not a reachability one. Absence-of-a-derived-fact is therefore strictly harder than
absence-of-an-input-fact, and the pilot claims neither.

### Deliverables

Formal query classes for key non-membership, range completeness, segment/export completeness, and
derived emptiness; certificate formats and verifier rules; composition rules through positive strata;
a proof or a scoped limitation for stratified negation; adversarial tests for omitted ranges, stale
roots, and incomplete exports. **No size or complexity bounds exist for both-polarity provenance
under recursion** — there is no dual-indeterminate circuit theorem, so EPYC would be proving the
first one.

Application precedent worth citing (not foundation): the missing-answer-explanation and
integrity-repair line applies the dual-indeterminate treatment to explaining absent query answers.

---

## R3 — Semantic identity and purity as evidence *(severed; optional)*

Moved here wholesale from the v1 draft's §7.19. It has **no bearing on the pilot**, which tracks
research claims and wiki prose, not code identity — a fact that was obscured while it occupied ~12%
of a document nominally about a knowledge pilot.

The line, if ever resumed: a semantic fingerprint over a canonical form produced by *licensed*
rewrites, where the licence is itself retractable evidence. Purity is graded and non-local
(monkey-patching and environment changes alter a callee's behaviour), so a purity belief anchors to
`(function fingerprint, module-graph state)`, trace-grade evidence licenses only narrow intra-function
rewrites, cross-function reordering needs differential-test evidence, and an observed side effect
retracts the licence and cascades.

The deterministic fallback — and the recommended position if the line is ever picked up — is a
directed, terminating normalizer (canonical binder numbering, directed constant/dead-code rules,
hash-sorted children for proven-commutative operations). Equality saturation earns its place only if
non-orientable equivalences demonstrably increase useful identity preservation, and it must satisfy
cross-platform golden-hash tests or fall back.

**The primary outcome of R3 is not "semantic hashing works."** It is the measured frontier at which
identity preservation becomes unsafe or too expensive. Stable explicit claim IDs remain the
production design regardless.

---

## R4 — Corroboration and fragility

Define corroboration over **leaf-disjoint** minimal supports: the maximum number of pairwise
disjoint support sets. Computing maximum set packing is NP-hard, and W[1]-hard parameterized by the
count alone; it is fixed-parameter tractable only in (count, support-size) jointly.

Product rule, unchanged from v1 and still correct: compute incrementally, cache by circuit hash,
search upward from 1, display `1 · 2 · 3 · 4 · 5+`, use branch-and-bound for ordinary instances,
treat any cap as an **under-approximation** rather than an exact count, and keep the statistic out of
the correctness-critical fixpoint.

New from the audit: **deduplicate before counting.** Near-identical supports inflate any
aggregate — the argumentation literature added a semantic-merge step for exactly this reason — and
the similarity threshold used MUST be recorded in the output.

Deliverables: exact bounded algorithm; proof of exactness below the cap; under-approximation
semantics when bounds bind; runtime/memory distribution on real circuits; and evidence that the
statistic predicts retraction fragility better than a naive source count.

**Interaction with the carrier decision — now settled.** The operator ratified dropping
`Corroborated` from the carrier on 2026-08-09 (pilot spec §4.1), so this statistic **is** the only
mechanical notion of independence in the system. That moves R4 from nice-to-have to load-bearing for
any policy of the form `disjoint_supports ≥ k`, and makes the under-approximation semantics
(what a bound-hitting cap is allowed to claim) a correctness question rather than a display detail.

---

## R5 — Belief decay and obligation utility

The two primary deployment uncertainties, answerable only by running the thing:

- Do beliefs survive long enough to compound, or expire before reuse?
- Do surfaced obligations change behaviour, or become noise people learn to dismiss?

Deliverables: longitudinal distribution of claim survival, downgrade, conflict, expiry and
re-verification by claim class; time-to-first-reuse and reuse count; obligation acceptance, action,
dismissal and false-positive rates; context and labour savings attributable to surviving beliefs; and
a releasable anonymized schema or synthetic benchmark if the raw frames cannot be published.

An external anchor now exists for the freshness half: a public benchmark constructs evolving-knowledge
question sets by diffing successive encyclopedia snapshots, which is directly transferable — diff
successive wiki/belief-store snapshots to generate an EPYC freshness eval set without hand-labelling.

---

## Reproducibility requirements (all tracks)

Every formal or empirical result records: exact repository commit and corpus frontier; schema, rule,
policy, fold and adapter versions; deterministic seeds where randomized algorithms are used; host and
architecture attestation for performance results; the full-refold oracle output; precommitted
stopping and scoring rules; and durable evidence hashes under the governing measurement constitution.

Performance, accuracy, or efficiency numbers that do not satisfy the governing measurement protocol
remain **observations** and MUST NOT gate promotion.
