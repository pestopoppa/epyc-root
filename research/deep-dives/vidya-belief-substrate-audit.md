# Vidya Belief-Substrate Audit — Consolidated Deep Dive

**Date**: 2026-08-09 · **Session**: research-intake-structured audit (Stages 1–4)
**Subject**: `tmp/vidya-epyc-governance-pilot-handoff.md` (v1 draft, 2,682 lines, dated 2026-08-09)
**Intake entries**: intake-1031 … intake-1067 (37 sources, all `dive-verified`; validator exit 0)
**Owning handoff**: [`handoffs/active/vidya-belief-substrate-program.md`](../../handoffs/active/vidya-belief-substrate-program.md)
**Operator steering**: integration over novelty; split premature detail; product-lattice option
documented; all surfaced sources studied; deliverables = this deep dive + program handoff + HTML explainer.

---

## 1. Mandate & method

The operator asked for a critical audit of the Vidya design — an epistemic substrate proposing an
append-only ledger of typed claim/evidence/intent frames, a deterministic fold to graded beliefs
over a min/max chain semiring, provenance circuits with retraction by zero-substitution, pro/con
bilattice verdicts, refusal-semantics freshness gates, and wiki pages as dependency-declared
projections — with an assessment of sensible-vs-overkill, verification of its research ancestry,
and connection to external work.

Method: one internal verification agent (10 "Current state" claims checked against the actual
repos), four Stage-1 landscape agents, five Stage-2 dive groups covering all 10 first-round
entries plus 17 deferred sources, and a final round of 8 more (operator: dive everything). Every
source landed in `research/intake_index.yaml` with verified claims, adoption extracts, dated
`dive_corrections`, and recorded declines. Retrieval date for all external reads: 2026-08-09.

## 2. Audit of the v1 draft

### 2.1 Verdict

**Worth pursuing, after restructuring.** The draft is unusually honest — it states its own limits
precisely (fold soundness vs graph coverage; "stale is not false"; certificates prove derivation,
not truth), correctly scopes its formal citations, and pre-registers failure criteria. The audit's
systemic findings are about scope, sequencing, and reuse — not correctness:

1. **It under-credits what EPYC already built** (§3): the "append-only ledger of typed frames +
   derived belief state" exists in-project three times over. The honest claim is the three verified
   gaps, not a missing substrate.
2. **It reinvents two layers with mature prior art** (§5): the frame layer (nanopublications,
   in-toto/DSSE, PROV-O) and the authenticated-ledger layer (RFC 9162 / C2SP tile logs). The
   novelty — and all invention budget — belongs to the epistemic kernel: deterministic fold to
   graded belief state, refusal-semantics freshness gates, certificates over an accumulating,
   supersession-aware belief state.
3. **The binding constraint is unpriced**: operator attention (claim atomization, anchor review,
   the Phase-0 gold corpus — a multi-session operator project as drafted).
4. **~50% of the spec is premature detail** (Rust stack, e-graphs/semantic hashing, authenticated
   maps, multi-writer machinery) — operator-endorsed for splitting into a non-binding appendix +
   research notes.

### 2.2 The sound core (keep verbatim)

- **Four-plane separation** (evidence / belief / intent / actuation) — "Stage-3 approval carries no
  evidence grade" is the draft's sharpest sentence and matches the research-intake skill's
  load-bearing rule exactly.
- **The exactness contract**: impact analysis exact *relative to registered edges*, never complete
  *relative to the world*; fold soundness (implementation property) vs graph coverage (empirical
  governance property) measured separately.
- **Freshness gates with honest outcomes** (validate / recompute / reverify / abstain / block); the
  promise is "stale is never served as current", not "everything can be made fresh".
- **Retraction as zero-substitution with full-refold oracle**, correctly restricted to the
  published positive-fragment theorem (but see §4.7 — the negation era changes the primitive).
- **Pro/con independence + 4-valued verdicts**; consumer-policy thresholds as the risk dial.
- **The pilot discipline**: shadow mode, frozen gold corpus, precommitted mutations,
  recall/precision split by failure direction, promotion/rollback criteria.
- **The grade-mapping table** (v1 §7.5), incl. wiki assertions contributing no independent grade.

### 2.3 The seven technical wrinkles (C1–C7)

> **Operator ratification 2026-08-09 — C1 and C2 are settled.** `Corroborated` is **dropped from
> the carrier** (independence becomes a policy predicate over the §7.3 statistic), and the carrier
> is a **product lattice `Q × T`** (warrant quality × traceability) rather than a single chain.
> Both are implemented in [`docs/design/vidya-pilot-spec.md`](../../docs/design/vidya-pilot-spec.md) §4.
> The two decisions compose: removing the independence dimension leaves exactly the two axes the
> chain was conflating, and the row v1 called `Traced` is now visibly `(Q1 Hinted, T2 Anchored)` —
> a traceability statement about an unverified claim, which the chain had ranked *above*
> `Corroborated`.

- **C1 — Corroborated-in-the-chain tension (highest-value fix).** ⊕=max is idempotent:
  `Judged ⊕ Judged = Judged`. The algebra can never *derive* `Corroborated` — it can only be minted
  as an asserted leaf grade, while mechanical corroboration lives in the separate leaf-disjoint
  packing statistic. The draft never says this plainly; a naive implementer adding a
  count-the-paths rule inside the fold would silently void the Deletion Property's hypotheses.
  The external algebra sweep confirmed the trade is fundamental: **accrual is non-idempotence** —
  every formalism with in-algebra accrual (QBAF gradual semantics, subjective-logic cumulative
  fusion, Dempster–Shafer) forfeits the absorptive-semiring deletion/convergence inheritance.
  Fix: drop Corroborated from the carrier, or restrict it to explicit independence-judgment tokens.
- **C2 — The chain conflates three dimensions** (support quality, anchor traceability,
  independence); `Corroborated < Traced` is a contestable value judgment. See §4.6: no theorem
  requires the total order, so a quality × traceability product lattice is an available option.
- **C3 — Dirty vs stale** — bind the states to object classes (beliefs go dirty;
  projections/obligations go stale).
- **C4 — Obligation condition language is a DSL bomb** — pilot restricts to ≤4 predicate types,
  one nesting level.
- **C5 — The anchor-repair loop smuggles LLM judgment into the "mechanical" path** — the
  equivalence-check rate must be an explicit pilot metric (it is the recurring operating cost).
- **C6 — Pilot-scope trims**: HLC, authenticated Merkle paths, full segment/portal contracts,
  absence certificates, multi-writer machinery — all future-scoped; cut from pilot scope explicitly.
- **C7 — Intent-frame forgery is open in the pilot** (any local process can emit a
  `human_intent_recorded` frame in shadow mode). Acceptable only because shadow state gates
  nothing; say so, and add a pilot-exit check that intent frames match ratification artifacts.

### 2.4 Gaps the v2 must close

Operator-attention cost model (typical batch = 15–50 claims; Phase 0 as drafted demands
hand-derived expected-impact reports incl. exact *unaffected* sets for ~9 mutation classes plus a
blind review pass — realistically 2–4 dedicated operator sessions before any code); in-flight
reconciliation (§3); a real-corrections gold corpus (§7 of the handoff's P0); one
measurement-domain claim family; the intake-skill-as-first-adapter strategy (instrument the skill's
own writes rather than retro-parsing prose).

## 3. In-project reconciliation (verified 2026-08-09)

The internal verification agent checked all ten "Current state" claims. Result: the draft's
architecture is *already partially landed* in EPYC, per-domain:

- **`evidence-plane-ledger-and-sequential-verdicts.md`** — 13/14 checkboxes done (only W8b
  evidence accrual open; master-index N2, restart-bundle owner, operator lane): per-question
  append-only ledger, typed `seq` blocks, capped-Kelly e-process with belief states
  `accumulating`/`confirmed_improvement`, per-candidate views rebuilt by fold, era-reset rule,
  verdicts in MEASUREMENT.md claim grammar.
- **`evidence-plane-event-sourcing-and-narrative.md`** (master-index A8) — journal-as-authority,
  append-only supersession substrate + read-side folding across seven consumer surfaces.
- **`autokernel/journal.py`** (2,179 lines) — fsync-per-event, 7 schema-bound record kinds
  validated at append, pure `rebuild_views()` bound to `events_digest()`,
  `check_view_consistency()` with PASS/FAIL/COULD_NOT_CHECK, `RETRIEVAL_SUPERSEDED` ("an immutable
  log has no way to stop believing something"), narrative-stripping on retrieval.
- **`experiment_journal.py`** — typed ledger events + supersession fold; baseline authority
  cutover to `ledger_fold` already live. (Blacklists remain mutable YAML; `autopilot_state.json`
  remains a 66-key mutable document — the known exceptions.)

**The three verified genuine gaps** the program claims: (1) **claim-level dependency edges** — wiki
dependency tracking was NOT-FOUND as any design; `.claude/dependency-map.json` is 4 repo-level
edges; kb-rag K8 wikilink scorer explicitly deferred; (2) **cross-worker snapshot coherence**
("does not hold across the 6-worker pool"); (3) **a value-divergence axis alongside age**
(diagnosed at `wiki/agent-architecture.md:1051`) — related, not owned by this program.

**Mandatory vocabulary reuse** (map, don't fork): `retro-certify` / `demote-to-prior` /
`retire-view` (MEASUREMENT.md §6, exact names confirmed); `fresh`/`aging`/`stale`/`missing` plus
`observed|silent|absent` × `populated|empty|unknown` (`dashboard/freshness.py` declares itself
"THE ONE CLASSIFIER" — the draft's 8-state taxonomy collides and must be mapped);
`accumulating`/`confirmed_improvement` (already a graded belief state for measurement claims).

**Hard constraints**: MEASUREMENT.md + annexes read-only to autonomous processes;
`instrument_eras.yaml` append-only human-written; evidence durable in-repo; the H1 non-overlap
contract ("evidence plane remains authoritative for trial/verdict events"). The name "Vidya" is
unused anywhere in the tree — no namespace collision. One draft correction: `compile_sources.py`
does inventory/hash/drift/policy (confirmed), but synthesis is an unautomated skill-level LLM
step, not part of the compiler.

## 4. Corrected formal foundations

Theorem-by-theorem, with the session's corrections. All primary texts read; citations pinned.

### 4.1 Deletion Property (retraction by zero-substitution)
**Property 13, by that exact name** — Bourgaux, Bourhis, Peterfreund, Thomazo, *Revisiting
Semiring Provenance for Datalog*, KR 2022 pp. 91–101 (arXiv 2202.10766) [intake-1038]. Holds for
semantics P^AT/P^NRT/P^AM/P^SAM (Props 39/40/46/52); **FAILS for minimal-depth P^MDT/P^HMDT
(Example 9)** — a Soufflé-style minimal-depth engine silently loses exact retraction; Example 9 is
the negative test vector for any "optimized fold". Correction to the draft: deletion is *not*
hypothesis-conditioned on +-idempotence — idempotence/absorption are what make the competing
semantics coincide (Props 3, 12). Prop 56: no polynomially computable circuit for P^NRT on
N∞⟦X⟧ unless P=NP — the reason to store per-iteration circuits.

### 4.2 Absorptive polynomials (the provenance carrier)
Dannert, Grädel, Naaf, Tannen, *Semiring Provenance for Fixed-Point Logic*, **CSL 2021, LIPIcs
183:17** (cite LIPIcs numbering — the arXiv extended version renumbers) [intake-1039]. Correction:
the framework requires **fully continuous** semirings (chain sups AND infs preserved; Def 4 + Def
8) — Example 5 (Łukasiewicz) shows ω-continuity insufficient for gfp; the ω-flavored result is
Prop 19 (closure ordinal ≤ ω). Prop 14: antichains of monomials are finite (a Dickson-style wqo on
(N∞)^k — itself a product of chains). Thm 17: S∞[X] universality.

### 4.3 Convergence budget
Abo Khamis, Ngo, Pichler, Suciu, Wang, PODS 2022 / **JACM 71(2):8, 2024** (arXiv 2105.14435)
[intake-1040]. Correction: the draft's "N variables × carrier-height" bound is Kleene folklore,
**misattributed** — the citable result is stronger: **0-stable semirings converge in ≤ N steps**
(Thm 1.2 bullet 3; general POPS form Cor 5.19), a hard runtime assertion for the refold oracle.
Exact general bound ∑_{i=1..N}(p+2)^i (note the internal i=0/i=1 index discrepancy between Thm
5.12 and Cor 5.18). p.25 verbatim: "**every distributive lattice is also a 0-stable semiring**".
Extension insurance: Im, Moseley, Ngo, Pruhs (PACMMOD 2(5):221, 2024; arXiv 2312.14063)
[intake-1044] gives polynomial convergence for p ≥ 1 — it does **not** supersede the N-step result
at p = 0.

### 4.4 Termination license and closed forms
Esparza & Luttenberger, CALCO 2011 (LNCS 6859:19–35) [intake-1065]: **Theorem 6** — for 1-bounded
(= absorptive) semirings, plain Kleene iteration reaches lfp in **N steps**, "even if the semiring
is not ω-continuous", no commutativity needed. The draft's "N+1" = N steps + zero-init layer
(Deutch et al.'s count; Theorem 5's n+1 is a *Newton* count — do not conflate). Naaf, RAMiCS 2021
(arXiv 2106.00399) [intake-1043]: **no fixpoint test needed** — lfp = F^N(0) exactly; gfp =
F^N(F^N(1)^∞), and on ⊗-idempotent lattices a^∞ = a, so gfp = F^N(F^N(1)) (~2N iterations) — the
implementable path to coinductive rules and certified absence.

### 4.5 Circuit representation
Deutch, Milo, Roy, Tannen, ICDT 2014 [intake-1041]: poly-size provenance **circuits** for the free
absorptive semiring Sorp(X), specializing "actually to any distributive lattice"; formulas are
provably exponential (Thm 1) — **the provenance store must be a DAG/circuit store, never an
expression store**. Deletion propagation is the paper's motivating application — the license for
the incremental-retraction path (with full refold as oracle). Adopt: two-level circuit compaction,
semi-naive embedded construction (Alg 2), self-dependency removal (licensed for distributive
lattices). Fan, Koutris, Roy, PODS 2025 (arXiv 2504.08914) [intake-1042]: depth dichotomy
Θ(log m) vs Θ(log² m); linear rule programs get NC²-parallelizable circuits.

### 4.6 The product-lattice finding (operator-flagged)
**No theorem in the loop requires the total order.** Every load-bearing hypothesis is algebraic
(absorptive / +-idempotent / 0-stable / fully continuous); Abo Khamis states distributive lattices
qualify verbatim; Deutch states "any distributive lattice"; Dannert's own S∞[X] is a non-chain;
Prop 14's wqo is a product of chains. A quality × traceability product lattice stays inside every
theorem. What totality actually buys: (i) ⊕/⊗ become *selection* operators (every folded value is
an input annotation — explainability); (ii) trivial σ (element count); (iii) thresholding at any
cut point is a homomorphism onto B, whereas product lattices need upward-closed sets — real but
designable-around. The draft's "the total order makes the semiring absorptive" is
sufficient-not-necessary; the v2 documents the product lattice as an available design choice.

### 4.7 Retraction with negation — the R1/R2 re-grounding (the audit's most consequential finding)
Grädel & Tannen, arXiv 1712.01980 [intake-1066]: **once negation is tracked, zero-substitution is
provably the wrong retraction primitive** — §5's worked counterexample: deleting facts collapses
the positive polynomial to 0 while the updated model still satisfies φ. The correct primitive is
**specialization** of a dual-indeterminate (X, X̄ with x·x̄ = 0), model-compatible provenance
object: deletion-created derivations are pre-materialized as X̄-monomials and merely *activated*;
the update map is a homomorphism, so it commutes with provenance computation. Certified absence =
π⟦nnf(¬φ)⟧; π⟦¬φ⟧ = 0 is certified validity.

Grädel & Tannen, *Provenance Analysis for Logic and Games*, Moscow J. Comb. Number Theory
9(3):203–228, 2020 (arXiv 1907.08470 v2) [intake-1067]: the construction paper for the
dual-indeterminate power series N∞[[X,X̄]] (Def 29; universality Prop 30 — note the printed typo
omitting the ∞ superscript) and the **per-stratum base case**: posLFP (least fixed points over
dual-annotated *input* literals) provenance is well-defined, Kleene-computable, and equals the
reachability-game valuation (Def 40, Prop 41, Cor 38); retraction-as-specialization is sound
per-stratum because lfp commutes with the ω-continuous evaluation homomorphisms. **Two hard
constraints**: (i) the paper itself states the route is "not available for … stratified Datalog"
(p.19) — the cross-stratum composition (freeze stratum k's (value, dual-value) pairs, re-tokenize
as fresh (x, x̄) for stratum k+1; well-typed by Props 12+14) is **EPYC's named residual theorem**,
certified stratum-locally and proven nowhere end-to-end; (ii) **Example 42: greatest fixed points
do not specialize** from N∞[[s,t]] to N∞ — absence certificates cannot be incrementally
specialized via the power-series route and must use the absorptive chain-positive S∞[X,X̄]
semirings (CSL 2021). Also nowhere: size/complexity bounds for both-polarity provenance under
recursion (no dual-indeterminate circuit theorem — EPYC would be proving the first). Negative
search result (2026-08-09, recorded to stop re-searching): no dedicated semiring-provenance
treatment of stratified Datalog exists; the frontier stops at negated input predicates /
posLFP / full LFP. Application precedent for R2 (cite-only): Xu, Zhang, Alawini, Tannen, IEEE
Data Eng. Bull. 41(1):39–50, 2018 (missing-answer explanation and integrity repairs).

### 4.8 Judge discipline (the LLM-in-the-loop theorem)
TOKI (arXiv 2606.06240) [intake-1035]: **Theorem 17** — keyed logging of a boundedly
nondeterministic adjudicating judge is *necessary* for replay consistency (and with Cor 6,
sufficient: a tight characterization). Translated into three fold requirements: (1) judgment
frames keyed by (read-set, decoder tuple = prompt, seed, model_version, temperature,
tool_output_hash); (2) first-committed-vote-wins per key (a re-run judge is short-circuited, never
a competing vote); (3) no model invocation during fold/replay. Trap: temp-0/greedy decoding does
**not** make a judge deterministic in this model. The n-ary confluence proposition additionally
requires conflict tie-breaks to form a **total order** (grade-then-timestamp-then-frame-id).

### 4.9 Formal-claims corrections ledger (before → after)
| Draft claim | Corrected | Source |
|---|---|---|
| "N variables × height h" convergence | ≤ N steps (0-stable), Cor 5.19; folklore bound is folklore | intake-1040 |
| ω-continuous suffices (fixed-point provenance) | fully continuous required; Example 5 | intake-1039 |
| "N+1 iterations" | N Kleene steps + zero-init layer (Thm 6); Newton's n+1 is distinct | intake-1065 |
| Deletion conditioned on +-idempotence | Deletion unconditional for AT/NRT/AM/SAM; fails for minimal-depth | intake-1038 |
| Total order buys absorption | Lattice absorption law does; product lattices in every hypothesis | intake-1038/39/40/41 |
| Zero-substitution = the retraction primitive | Only for the positive core; specialization under negation | intake-1066/1067 |
| Carneades "five 2007 proof standards" (session's own Stage-1 error) | 2007 = SE/BA/DV; five-set = Gordon-Walton 2009 | intake-1050/1062 |
| Potyka AAAI-18; Attractor=Uncertainpy | KR 2018; two distinct libraries | intake-1049 |
| Baur-Studer LFCS 2020 | CLAR 2020 (and arXiv v2 corrects the conference completeness proof) | intake-1045 |

## 5. The adoption kit (integration-first)

What the program **adopts instead of inventing**, with the owning intake entry:

- **Frame envelope** [1031]: nanopub three-part decomposition (assertion / provenance / pubinfo) +
  two lint rules (provenance must reference the assertion; pubinfo speaks only of the frame);
  **hash-without-id-and-signature** canonical-JSON addressing (RFC 8785 JCS), id derived, detached
  signature over id (inverting nanopub's sign-then-hash so unsigned frames get stable ids);
  supersedes (pubinfo) / **retracts as a first-class claim frame with its own grade** / disputes;
  same-actor fold gating with explicit authority override; KeyDeclaration intro-frame pattern.
- **Bi-temporal fields** [1032]: `created_at` / `expired_at` (ledger clock, fold-derived) /
  `valid_at` / `invalid_at` (world clock) / `reference_time` (source clock); closure rule
  `loser.invalid_at := winner.valid_at ∧ loser.expired_at := now`, **gated by authority class**
  (Graphiti's actual rule is "later valid_at wins, no authority weighting" — the anti-lesson);
  two-stage contradiction scoping (structural candidates + retrieval, then a small judge) with the
  verdict **reified as a ledger frame**; bidirectional claim↔evidence index.
- **PROV-O alias table** [1046]: field → PROV IRI mapping documented once (derived_from →
  wasDerivedFrom; actor → wasAttributedTo; expired_at → invalidatedAtTime; subagent chains →
  actedOnBehalfOf; segments/certificates → Bundle). **Two-clocks trap**: `invalidatedAtTime` is
  record-lifecycle, not world-truth — `valid_at`/`invalid_at` stay PROV-less.
- **Typed predicates + policy frames** [1047]: `frame_type` as versioned URI (predicateType
  discipline); optional `subjects[{name, digest}]`; SLSA predicate shape for build/bench frames;
  fold policy as a **signed, expiring policy frame** with per-frame-type authority_scope +
  attestation threshold (a freshness gate for the policy itself); one artifact rule kept as a fold
  invariant (MATCH digest continuity between pipeline stages); DSSE as later-authentication.
- **L1 ledger ladder** [1048, 1063]: L0 prev-hash chain → **L1 pilot target** (~200 lines): RFC
  9162 Merkle roots (0x00/0x01 domain separation) + C2SP signed-note checkpoints **pinned to tags
  signed-note/v1.0.0 + tlog-checkpoint/v1.0.0** (main has drifted to ML-DSA-44 — watch item),
  checkpoints committed to git, consistency-proof against the prior trusted checkpoint → L2
  (tlog-tiles/Tessera) only on a real trigger (second writer, external verifier, HTTP-served
  proofs). Byte-exact emitter/verifier spec recorded in intake-1063's dive.
- **Certificates** [1064]: VSA-mapped schema (verifier.id/version; policy.digest = ratified grade
  config; inputAttestations = every consumed frame by ledger coordinate + digest — the
  replayability hook; verifiedLevels per track; dependencyLevels = frontier summary; three-valued
  result vocabulary reserved). **The load-bearing idea: a certificate is itself an attestation
  frame that re-enters the ledger** — Merkle leaf, covered by the next checkpoint, citable
  downstream. Verification composes because certificates close over the frame algebra.
- **Lifecycle + policy vocabulary** [1056, 1062]: `{Active, Stale, Conflicted, Dropped}` with
  **cite-only-Active as a structural precondition** (the mechanism form of "stale is never served
  as current"); Abstain as a typed terminal transition; proof-standard grade names (SE = ∃
  applicable pro; DV = pro ∧ no applicable con — both certifiable from the min/max core;
  PE/CCE/BRD with α/β/γ protocol-owned thresholds — advisory-only, they consume subjective
  weights) with three EPYC gap closures (max(∅) := 0; unweighted applicable argument caps at
  SE/DV; acyclicity precondition); burden vocabulary (production; tactical burden = interior-stage
  certificate under closing policy).
- **Advisory overlay** [1037, 1049, 1051, 1052, 1053]: DF-QuAD reimplemented from the published
  formulas (~20 lines; exact one-pass evaluation on the acyclic condensation — no iteration, no
  tolerances; **two license walls**: ArgLLMs is non-commercial academic, Uncertainpy is
  unlicensed); the two proven contestability (monotonicity) properties as the reviewer-facing
  contract; dedup-before-aggregate (product aggregation double-counts near-duplicates); contest-
  base-score + contest-polarity as renderer challenge affordances; uniform-0.5 default for
  unscored nodes; base-score sensitivity (up to 0.19 accuracy swing from UQ-method choice alone)
  as the recorded justification for **degrees advisory, never certified**.
- **Eval instruments** [1054, 1036]: HoH's +1/0/−1 (perfect/missing/harmful) scoring + A_C/A_O
  awareness metrics; snapshot-diff eval-set construction over EPYC's own wiki; the demonstrated
  failure of retrieval-side staleness filtering as design rationale for serve-time refusal.
  MemStrata's marker-free construction + forced-answer stale-fact-error metric ("RAG hides its
  failure by refusing to answer"); **AUROC 0.5926** (cosine cannot separate contradiction from
  duplicate) as the empirical basis for the no-similarity-threshold retraction axiom; the
  write-time-merge regression as support for compress-at-projection-never-at-write.
- **Claim atomization + assertion maps** [1060]: PaperTrail's atomic/faithful/decontextualized +
  verifiable/declarative criteria; **extract-then-programmatically-anchor** (the stochastic step
  never touches the anchor — hash the located span, key the manifest on it); the **omissions
  lane** (manifests report beliefs relevant to a page but not surfaced); the trust-behavior gap
  (advisory provenance badges lowered trust but did not change reliance, n=26 CHI study) as
  empirical support for refusal semantics.
- **Actuator schema** [1061]: per-argument provenance (name, value, source_set, derivation ∈
  {verbatim, derived, generated}) with **the ledger, not the LLM, as witness** (self-reported
  provenance = named anti-pattern); tri-state cascade with priced overhead (deterministic layers
  ~free; judge routed <5% of decisions); groundable/free-text argument split + (tool, argument,
  value) allowlists; verbatim-integrity check as a strong deterministic gate.
- **Compliance patterns** [1033, 1035]: Kumiho's executable postulate-compliance suite (enumerate
  which AGM/Hansson-style postulates the fold satisfies, which it rejects — Recovery rejection as
  precedent for no-auto-resurrection); ground/propositional scope guard at the fold layer (Flouris
  2005 via Kumiho); TOKI's Claim-vs-Wire double-verdict audit format.

## 6. Landscape position (brief, per operator steering)

The 2026 agent-provenance survey (arXiv 2606.04990 v4, 11 authors) [intake-1034] documents in its
own §6.4/Table 6 that no surveyed memory system reaches Yes on conflict handling + staleness
handling + evidence-aware verification simultaneously; its nine-relation vocabulary (Use, Generate,
Derive + Support, Depend-on, Contradict, Invalidate, Trigger, Update) is the coverage checklist for
frame types (Trigger and Use/Generate need explicit adopt-or-decline decisions). Closest systems,
each verified: **Kumiho** [1033] (AGM-compliant versioned memory; advisory impact traversal only),
**TOKI** [1035] (bitemporal contradiction operators + the replay theorem), **MemStrata** [1036]
(deterministic supersession; suppression not refusal; headline numbers not citable), **Graphiti**
[1032] (industrial bi-temporal KG; LLM-mediated, ungraded), **Eywa** [1055] (evidence-before-
belief; no grades, no runtime refusal — its admitted gaps are exactly the program's two
differentiators), **esper** [1059] (a 440-line existence proof of the as_of pure fold),
**LedgerMind** [1056] (episodic lifecycle vocabulary), **Hindsight** [1058] (epistemic-stance
partition + tri-temporal fields), **NeuSymMS** [1057] (the TMS-on-mutable-store anti-pattern).
Treated as a shopping list; the composition-level gap is real but closing quarter by quarter
(five near-misses landed Mar–Jul 2026).

## 7. Machine-wide generalization

What generalizes: the four planes, graded evidence with honest abstention, refusal-semantics
freshness gates, event-sourced derivation, the judge discipline. What does not scale: claim
atomization and anchor registration over arbitrary prose (per-claim, human-gated cost). Expansion
order should be **structured-evidence-first**: the session bus (inbox/outbox/heartbeats/
adapter-ledger are already typed JSONL frame streams) → MEASUREMENT-governed results (already
typed claims with eras and attestation — the closest thing to Witnessed frames the machine
produces) → registry compilations (projections awaiting manifests) → memory-file sidecars (the
Claude memory system is an ungraded belief store with known staleness failure modes). The wiki
remains the right *governance* beachhead (richest existing process), but the pilot adds one
measurement-domain claim family so era/frontier machinery is tested where real stakes live.

## 8. Reference table (all session sources; retrieval 2026-08-09; all dive-verified)

| Intake | Source | Verdict | One-line takeaway |
|---|---|---|---|
| 1031 | Nanopublications ecosystem | adopt_patterns | Frame-layer prior art: 3-graph claims, normalized-content addressing, same-key retraction |
| 1032 | Zep/Graphiti (2501.13956 + repo @425bf24) | adopt_patterns | 5-timestamp bi-temporal fields + closure rule; reify judge verdicts; decline as dependency |
| 1033 | Kumiho (2603.17244) | worth_investigating | AGM-compliant versioned memory; compliance-suite pattern; ground-propositional scope guard |
| 1034 | Agent-provenance survey (2606.04990 v4) | adopt_patterns | The field's gap analysis (§6.4/Table 6); nine-relation coverage checklist |
| 1035 | TOKI (2606.06240) | worth_investigating | Replay-consistency necessity theorem → three fold requirements; temp-0 ≠ determinism |
| 1036 | MemStrata (2606.26511) | worth_investigating | AUROC-0.59 no-similarity axiom; marker-free + forced-answer eval protocol; numbers not citable |
| 1037 | ArgLLMs (2405.02079, AAAI-25) | adopt_patterns | DF-QuAD advisory overlay; two contestability properties; license wall — reimplement |
| 1038 | Bourgaux et al. KR-22 (2202.10766) | adopt_patterns | Deletion = Property 13; fails for minimal-depth semantics; no totality hypothesis |
| 1039 | Dannert et al. CSL-21 (1910.07910) | adopt_patterns | Absorptive polynomials; FULLY continuous; LIPIcs numbering; S∞[X] is a non-chain |
| 1040 | Abo Khamis et al. JACM-24 (2105.14435) | adopt_patterns | ≤N-step 0-stable convergence; distributive lattices verbatim in scope |
| 1041 | Deutch et al. ICDT-14 | adopt_patterns | Poly circuits for absorptive; DAG-store-never-expression-store; incremental-retraction license |
| 1042 | Fan-Koutris-Roy PODS-25 (2504.08914) | adopt_patterns | Depth dichotomy; linear programs NC²; no poly formulas for recursion |
| 1043 | Naaf RAMiCS-21 (2106.00399) | adopt_patterns | Closed forms: lfp = F^N(0), gfp implementable; no fixpoint test |
| 1044 | Im et al. PACMMOD-24 (2312.14063) | adopt_patterns | Extension insurance for p ≥ 1; does not supersede N-step at p = 0 |
| 1045 | Baur-Studer (2308.05506, CLAR-20/JLC-21) | adopt_patterns | Motivation-grade typed-⊕ reading; venue corrected; thin adoption |
| 1046 | W3C PROV-O/PROV-DM | adopt_patterns | Alias-layer field mapping; the expired_at/invalid_at two-clocks trap |
| 1047 | in-toto attestation + SLSA | adopt_patterns | frame_type URIs; signed expiring policy frames; certificate epistemic stance precedent |
| 1048 | RFC 9162 + C2SP/Tessera/Rekor-v2 | adopt_patterns | The L0→L1→L2 authentication ladder; authenticated surface = entries+proofs+checkpoints |
| 1049 | Potyka KR-18 + Uncertainpy (1811.12787) | adopt_patterns | Exact DAG evaluation removes tolerance nondeterminism; libraries declined (license/maturity) |
| 1050 | Carneades 2007 + carneades-4 | adopt_patterns | Three standards in 2007; proof-standard names as policy vocabulary; acyclicity precedent |
| 1051 | MArgE (2508.02584) | adopt_patterns | Dedup-before-aggregate for the overlay |
| 1052 | ArgRAG (2508.20131) | adopt_patterns | Contest-base-score/contest-polarity renderer affordances; uniform-0.5 default |
| 1053 | ArgLLM-UQ (2510.02339, EMNLP-25) | adopt_patterns | Base-score sensitivity → degrees advisory, never certified |
| 1054 | HoH (2503.04800) | adopt_patterns | +1/0/−1 + A_C/A_O pilot metrics; retrieval-side filtering fails |
| 1055 | Eywa (2605.30771) | worth_investigating | Nearest near-miss; validates projections-as-idempotent-rebuilds; two gaps unoccupied |
| 1056 | LedgerMind (2607.28374) | adopt_patterns | {Active,Stale,Conflicted,Dropped}; cite-only-Active; Abstain as typed transition |
| 1057 | NeuSymMS (2605.17596) | not_applicable | The TMS-on-mutable-store anti-pattern (knowledge-only) |
| 1058 | Hindsight (2512.12818) | adopt_patterns | Epistemic-stance axis; tri-temporal fields; confidence is Opinion-network-only |
| 1059 | esper (repo @bf4d2d0) | adopt_patterns | as_of purity + calibrated-confidence/source-reliability separation; siblings re-attributed |
| 1060 | PaperTrail (2602.21045, CHI-26) | adopt_patterns | Claim criteria; span anchors; omissions lane; trust-behavior gap → refusal semantics |
| 1061 | Agent-Sentry (2603.22868) | adopt_patterns | Argument provenance schema + cascade; self-reported provenance anti-pattern |
| 1062 | Gordon-Walton 2009 chapter | adopt_patterns | The five-standard α/β/γ definitions (primary-sourced via Wayback); max-not-sum |
| 1063 | C2SP signed-note + tlog-checkpoint | adopt_component | Byte-exact L1 checkpoint spec; PIN v1.0.0 tags (ML-DSA-44 drift on main) |
| 1064 | SLSA VSA v1.1 | adopt_patterns | Certificate field template; certificates re-enter the ledger |
| 1065 | Esparza-Luttenberger CALCO-11 | adopt_patterns | Theorem 6 termination license; the algebraic ladder guard |
| 1066 | Grädel-Tannen (1712.01980) | adopt_patterns | Dual indeterminates; specialization replaces zero-substitution under negation |
| 1067 | Grädel-Tannen Moscow-J-2020 (1907.08470) | adopt_patterns | N∞[[X,X̄]] construction; per-stratum base case; gfp non-specialization (Ex. 42) |

**Recorded declines** (each named in the bearing entry's `dive_corrections`): Flouris 2005
(transitive cite); WorldDB, MIRIX, LoCoMo-Plus, LongMemEval-S, MultiTQ (benchmarks/poles);
PROV-AGENT, A-MemGuard; spec references DSSE / PROV-JSON / PROV-CONSTRAINTS / RFC 8785 /
trustyuri-spec / static-ct-api / rekor-tiles / ITE-6/10 (cited in-entry); EKL JACM 2010 +
Luttenberger-Schlund 2016 (carried by CALCO survey); Progent, belief-ledger-pramana,
tlog-cosignature (monitor/trigger); endoxa, cato-ledger, anchor-db; selP 2018; subjective logic +
Dempster-Shafer in load-bearing roles; Uncertainpy/ArgLLMs imports (license walls); Kumiho
depth-bounded traversal; TOKI N2/N3 taxonomy; full in-toto layout toolchain; Tessera sidecar until
an L2 trigger; **Xu/Zhang/Alawini/Tannen 2018** (decline-with-citation as R2 application
precedent — operator may override).
