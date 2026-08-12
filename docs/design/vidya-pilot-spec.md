# Vidya Pilot Spec

**Status:** pilot contract — shadow-only, gates nothing; **all §19 decisions operator-ratified 2026-08-09**
**Date:** 2026-08-09 (V2 revision of the 2026-08-09 v1 draft)
**Owning handoff:** [`handoffs/active/vidya-belief-substrate-program.md`](../../handoffs/active/vidya-belief-substrate-program.md)
**Audit of record:** [`research/deep-dives/vidya-belief-substrate-audit.md`](../../research/deep-dives/vidya-belief-substrate-audit.md)
**Siblings:** [research program](vidya-research-program.md) (R1–R5) · [architecture appendix](vidya-architecture-appendix.md) (non-binding)
**Supersedes as a plan:** `tmp/vidya-epyc-governance-pilot-handoff.md` §§1–16, 18, 22–24

---

## 0. What this document is

The v1 draft mixed three documents: a pilot contract, a formal research program, and a mature-stack
architecture sketch. This is the first of those three, revised against the audit. It defines only
what the shadow pilot must do, and it is deliberately short — everything that does not change the
go/no-go decision was moved to a sibling.

Normative words (MUST / MUST NOT / SHOULD / MAY) are normative within this document. Nothing here
grants an autonomous process new write authority: `MEASUREMENT.md` and its annexes remain
human-amendment-only, `instrument_eras.yaml` remains append-only and human-written, and the
evidence plane remains authoritative for trial/verdict events.

**The pilot's promise, stated once:** a consumer never unknowingly uses stale state as current, and
when the answer is not recoverable the system says exactly what evidence, judgment, or authority is
missing. It does *not* promise that every belief can be made fresh on demand.

---

## 1. Scope

**In scope** — the three gaps the audit verified as genuinely unowned:

1. **Claim-level dependency edges** for research/wiki knowledge. Wiki dependency tracking exists
   nowhere as a design; `.claude/dependency-map.json` carries four repo-level coupling edges and no
   claim graph; the KB-RAG wikilink scorer (K8) is explicitly deferred.
2. **Refusal-semantics freshness gating** of that knowledge at query time.
3. *(Later phase, not this pilot)* provenance-gated actuation.

**Out of scope** — because it already exists per-domain and this pilot rides it rather than
duplicating it: the per-question evidence ledger and sequential verdicts, the AutoKernel journal's
event sourcing, the experiment journal's supersession fold. Also out of scope for the pilot:
semantic fingerprinting and purity-as-evidence (moved to R3), the mature Rust daemon (appendix),
hybrid logical clocks, authenticated Merkle *paths* beyond the L1 checkpoint rung, full
segment/portal contracts, absence certificates (R2), and any multi-writer machinery.

---

## 2. Planes and authority

Four planes, never collapsed:

| Plane | Records | Never does |
|---|---|---|
| **Evidence** | what sources, measurements and executions report | confer authority |
| **Belief** | what follows from active evidence under the rules | create evidence |
| **Intent** | what an authorized actor approved, declined, or froze | upgrade an evidence grade |
| **Actuation** | what was actually changed in a repo or running system | derive its own permission |

The sharpest consequence, retained verbatim from v1: **an operator approval carries no evidence
grade.** "Evidence supports this claim" and "the project should act on this claim" are different
dimensions with different frame types.

---

## 3. Frames

### 3.1 Envelope

The frame envelope adopts the nanopublication decomposition (three parts, not three RDF graphs):

```yaml
frame_type: "epyc.vidya/frame/evidence_supports_claim/v1"   # versioned URI (predicateType discipline)
subjects:                                                    # OPTIONAL; only for frames about artifacts
  - name: "gguf:worker_general"
    digest: {sha256: "<hex>"}
assertion:      {...}   # the claim this frame makes. Nothing else may introduce claims.
provenance:     {...}   # statements ABOUT the assertion: method, derived_from, evidence refs
pubinfo:        {...}   # statements ABOUT the frame: actor, authority_scope, created_at, supersedes
frame_id:       "blake3:<hash of canonical JSON without frame_id and signatures>"
signatures:     []      # reserved; detached, added later without changing frame_id
```

Two lint rules are enforced at append (adopted verbatim from the nanopublication guidelines):

- every `provenance` field MUST reference the assertion — provenance may not smuggle in new
  world-claims;
- `pubinfo` MUST speak only of the frame — never of the world.

**Content addressing.** `frame_id` is the hash of the canonical JSON (RFC 8785 JCS) of the envelope
with `frame_id` and `signatures` omitted. This inverts the nanopublication order (which signs first,
then content-addresses over the signature) so that an unsigned pilot frame and a signed production
frame have the *same* id. Re-serialization MUST NOT change identity: the hash is over canonical
JSON, never over stored bytes.

### 3.2 Time — five clocks, never conflated

| Field | Clock | Meaning |
|---|---|---|
| `created_at` | ledger | when the ledger learned it |
| `expired_at` | ledger | when the fold derived that it ceased to apply (**derived, never stored-mutable**) |
| `valid_at` | world | when the fact became true |
| `invalid_at` | world | when the fact stopped being true |
| `reference_time` | source | the source document's own timestamp |

A 2025 paper read in 2026 asserting a 2024 fact carries three distinct times; a schema with one
timestamp cannot express it. **Trap:** PROV's `invalidatedAtTime` is the *ledger* clock
(`expired_at`), not the world clock — `valid_at`/`invalid_at` deliberately have no PROV equivalent
and keep private names.

### 3.3 Field vocabulary

Field names align to W3C PROV terms via a documented alias table, shipped in the schema doc rather
than implemented as RDF: `derived_from → prov:wasDerivedFrom`, `actor → prov:wasAttributedTo`,
`produced_by → prov:wasGeneratedBy`, `created_at → prov:generatedAtTime`, `expired_at →
prov:invalidatedAtTime`, `supersedes → prov:wasRevisionOf`, `on_behalf_of → prov:actedOnBehalfOf`,
quotes → `prov:wasQuotedFrom`, primary source → `prov:hadPrimarySource`, ledger segments and
certificates → `prov:Bundle`. Grades, freshness policy, authority classes, world-time validity, and
determinism metadata have no PROV equivalent and stay private.

Attribution, association, and delegation stay three distinct fields — the operator → main → subagent
chain is exactly `actedOnBehalfOf`, and collapsing it loses who actually decided.

### 3.4 `triggered_by` — procedural causation, adopted 2026-08-09

`pubinfo.triggered_by: <frame_id>` records **why this frame was emitted**. It lives in `pubinfo`
because it is a statement about the frame, not about the world, and it is strictly distinct from
`provenance.derived_from`, which records what evidence the assertion rests on.

| Field | Answers | Carries grade? |
|---|---|---|
| `provenance.derived_from` | what evidence supports the assertion | **yes** — it is a support edge |
| `pubinfo.triggered_by` | what event caused this frame to exist | **no** — never |

**The rule that keeps it safe: a triggered frame inherits nothing from its trigger.** Not grade, not
authority, not freshness. This is the same discipline as intent-not-being-evidence, and without it
`triggered_by` would become a back door for laundering a low-grade event into support for a
high-grade claim.

What it buys is an auditable answer to "why is this here?" for the machinery that acts on its own
derivations — an obligation opening because a belief changed, a re-verification frame emitted
because an anchor stopped resolving, a projection marked stale because a belief version moved. The
trigger chain is exactly the record you want when an obligation surfaces and nobody can remember
what opened it. PROV alias: `prov:wasInformedBy`.

### 3.5 Supersession, retraction, dispute

- **`supersedes`** sits in the new frame's `pubinfo`; the old frame is never touched.
- **Retraction is a first-class claim frame** whose assertion is `{retracts: <frame_id>}` — with its
  own provenance, its own actor, and its own grade. It is not a mutation and not a tombstone flag.
- **`disputes`** records third-party disagreement that affects grade without asserting authority to
  remove.

The fold honours `supersedes`/`retracts` when `pubinfo.actor` matches the target frame's actor, or
when an authority rule explicitly grants override. (This is the nanopublication same-key rule,
translated from signatures to authority scopes for the unsigned pilot.)

---

## 4. The grade carrier

**Ratified by the operator 2026-08-09:** drop `Corroborated`, and adopt a **product lattice** rather
than a single chain. The two decisions fit together — removing the independence dimension leaves
exactly the two axes the v1 chain was conflating.

### 4.1 Why the chain was wrong

The v1 carrier was `0 < Hinted < Judged < Corroborated < Traced < Verified < Witnessed`. It mixed
three unrelated questions into one ordering, which produced at least one indefensible comparison —
`Corroborated < Traced` ranked *two independently reviewed sources* below *one exact-but-unverified
anchor*. Factoring the questions apart:

| Question | Where it goes now |
|---|---|
| How strong is the epistemic act behind this? | **Q axis** (below) |
| How precisely can a reader get back to the evidence? | **T axis** (below) |
| How many independent paths support it? | **Not a grade** — a policy predicate over the corroboration statistic (§7.3) |

`Corroborated` had to go regardless of the lattice decision: `⊕ = join` is idempotent, so the fold
can **never derive** it from two independent `Judged` paths. Accrual is impossible in this algebra
by construction — and deliberately so, because accrual *is* non-idempotence, and every accruing
formalism (gradual argumentation, subjective-logic cumulative fusion, Dempster–Shafer) forfeits the
deletion and convergence theorems the carrier exists to inherit. Keeping the label would have meant
one word denoting two different things, with a standing invitation for an implementer to "fix" the
apparent gap by adding a count-the-paths rule inside the fold — silently voiding the Deletion
Property's hypotheses.

### 4.2 The carrier

```text
Q  (warrant quality)     Q0 · Q1 Hinted · Q2 Judged · Q3 Verified · Q4 Witnessed
T  (traceability)        T0 Unanchored · T1 Located · T2 MachineLocated · T3 Anchored · T4 Attested

L  = Q × T               25 elements
a ⊕ b = (max Q, max T)   pointwise join   — alternative support
a ⊗ b = (min Q, min T)   pointwise meet   — joint / chained support
0 = (Q0, T0)             additive identity and annihilator for ⊗
1 = (Q4, T4)             multiplicative identity
```

**Q — what epistemic act stands behind the claim**

| Level | Meaning |
|---|---|
| `Q0` | no active evidence |
| `Q1 Hinted` | extracted or discovered; no verification performed |
| `Q2 Judged` | an identified actor's judgment, within a declared authority scope |
| `Q3 Verified` | passed an applicable verifier or a Stage-2 primary-source review |
| `Q4 Witnessed` | attested by a **protocol-admissible measurement** under the measurement constitution's claim grammar — metric, protocol id, n/reps, date, durable host attestation |

**`Q4` is deliberately narrow (ratified 2026-08-09).** It means exactly one thing: *this claim would
be admissible as a decision-gating measurement claim*. That makes the top grade checkable rather
than a matter of taste — a claim is `Q4` iff it satisfies the constitution's grammar, and the
constitution is the arbiter, not this spec. A passing test, a green build, a successful actuation,
and a verifier result are all real evidence and all stop at `Q3`: they are verifications, not
measurements. The practical effect is that nothing reaches the top of the Q axis without a protocol
id and durable evidence behind it.

**T — how precisely a reader can get back to it**

| Level | Meaning |
|---|---|
| `T0 Unanchored` | no resolvable anchor |
| `T1 Located` | correct document and revision; no span |
| `T2 MachineLocated` | a span found by machine and pinned by `quote_sha256`, **not read by a person** |
| `T3 Anchored` | exact durable span a person located — heading path + content hash, JSON pointer, trial id |
| `T4 Attested` | durable in-repo artifact with an attestation reference per the measurement constitution |

`T4` is deliberately the constitution's own durable-evidence rule: a hash over an artifact that no
longer exists proves nothing, so `T4` requires the artifact to be present and cited, while `T3`
requires only that the anchor resolves.

**Amendment 2026-08-10 — `T2 MachineLocated` inserted (operator-ratified).** Measured on the live
index: 667 entries are cited by active handoffs and design docs and **5** are anchored, so hand-
anchoring the 2,994 cited claims is not a path, and leaving the axis at 5 of 4,191 makes every
traceability policy inert. A span located by matching a claim's distinctive terms against the
fetched source *is* checkable — `quote_sha256` pins the exact text — but it is not the act a human
anchor records, which is a person reading the passage and judging that it says what the claim says.
Recording both at one level would make `Anchored` mean two different things, and the axis exists
precisely to keep that distinction. So machine location gets its own level: strictly above
`Located` (a span, not just a document), strictly below `Anchored` (nobody read it), and policies
choose their own bar rather than inheriting one.

The insertion is ordinal-safe for stored data: grades serialize as **names**, never ordinals
(`{"Q": "Verified", "T": "Anchored"}`), so no existing frame changes meaning. The algebra is
unaffected — a product of two finite chains is still a bounded distributive lattice however many
links a chain has, so every theorem in §4.3 survives the amendment unchanged.

### 4.3 The algebra still holds — every theorem, unchanged

Each axis is a finite chain; a product of finite chains is a bounded **distributive lattice**. That
is exactly the hypothesis class the pilot's formal results require, and two of the sources say so in
their own words: the convergence result states that *"every distributive lattice is also a 0-stable
semiring where we set ⊕ = ∨ and ⊗ = ∧"*, and the circuit result specializes *"actually to any
distributive lattice"*.

| Property | Holds? | Why |
|---|---|---|
| Absorptive (`a ⊕ (a ⊗ b) = a`) | ✅ | lattice absorption, componentwise |
| 0-stable (`1 ⊕ u = 1`) | ✅ | `(Q4,T3)` is top |
| ⊗-idempotent | ✅ | meet is idempotent → `a^∞ = a`, so `gfp = F^N(F^N(1))` |
| Fully continuous | ✅ | finite |
| Deletion Property applies | ✅ | absorptive; semantics pinned to P^AT (§5.2) |
| ≤ N-step convergence | ✅ | 0-stable |
| Poly-size provenance circuits | ✅ | absorptive |

The carrier grew from 6 elements to 20 — still trivially small, still a fixed finite set, and the
fold cost is unchanged (both operations are two integer comparisons instead of one).

### 4.4 What the product lattice costs, and how each cost is paid

**(a) Grades become pairs, and some are incomparable.** `(Q3,T1)` — verified but only
source-located — and `(Q2,T2)` — judged but exactly anchored — neither dominates the other. This is
the *point*: the chain forced a false ranking between them. Displays show both coordinates
(`Verified/Located`), and sorting requires a declared tiebreak rather than a natural order.

**(b) The join can be synthetic — this is the real one.** In a chain, `⊕ = max` is a *selection*
operator: the folded value is always one of the inputs, so you can always point at the path that
produced it. In a product lattice it is not. If path A is `(Q3,T1)` and path B is `(Q2,T2)`, the
join is `(Q3,T2)` — a grade **no single path achieves**.

Read correctly, the join says *"some path is Verified, and some path is Anchored."* It does **not**
say one path is both. Two mechanisms keep that honest:

- **Witness sets.** Every folded grade reports the minimal set of paths that jointly achieve it — at
  most two for a two-axis lattice. "Verified by path A; anchored by path B" is more informative than
  the chain's single number ever was, and it makes the synthetic join self-explaining.
- **Conjunctive policy predicates.** When a consumer needs *one* path to clear both bars, that is a
  different query — `∃ path : Q ≥ q ∧ T ≥ t` — evaluated per-path over the provenance circuit's
  minimal supports, not read off the join. **Authoritative use policies default to the conjunctive
  reading**; exploratory ones may use the join.

Both questions are legitimate and the system answers them separately instead of conflating them,
which is the same discipline that motivated splitting the axes in the first place.

**(c) Thresholds must be upward-closed sets, not cut points.** In practice every policy the pilot
needs is conjunctive — `Q ≥ Q3 ∧ T ≥ T2` — and a conjunction of per-axis floors *is* upward-closed,
so this costs one extra threshold per policy and nothing else. Non-rectangular policies (for
example, "accept `(Q4,T1)` or `(Q2,T3)` but nothing between") are expressible as an explicit set of
minimal accepted pairs, and MUST be written that way rather than as an inequality.

### 4.5 Status-to-grade mapping (replaces the v1 §7.5 table)

Proposed pilot policy; requires operator ratification before any authoritative query uses it.

| Record | Q | T | Qualification |
|---|---|---|---|
| Stage-1 extracted claim, source link only | `Q1 Hinted` | `T1 Located` | discovery only; cannot gate an integration plan |
| Stage-1 extracted claim with an exact span | `Q1 Hinted` | `T2 Anchored` | the anchor is good; the claim is still unverified |
| Identified model or reviewer judgment | `Q2 Judged` | as anchored | scoped to that actor's authority |
| Exact durable anchor, not substantively verified | `Q1` | `T2 Anchored` | **this is what v1 called "Traced"** — a T-statement that had been ranked as a Q-level |
| Stage-2 accepted claim with primary-source anchor | `Q3 Verified` | `T2 Anchored` | entry-level `dive-verified` does not verify every extracted claim |
| Deterministic verifier result under an applicable contract | `Q3 Verified` | `T2`–`T3` | **capped at `Q3`** — a verifier confirms, it does not measure; verifier identity and version required |
| Test pass / green build / successful actuation outcome | `Q3 Verified` | `T2`–`T3` | same cap, same reason; an execution record without protocol grammar is not a measurement |
| Protocol-admissible measurement with durable attestation | `Q4 Witnessed` | `T3 Attested` | the **only** route to `Q4`; for the measured observation only — derived mechanism or generalization claims need their own rules |
| `dive-overturned` | opposition frame | — | does not erase the original proposal |
| Stage-3 operator approval | **no Q** | **no T** | intent plane; authority, not evidence |
| Wiki assertion | **no independent grade** | — | a projection cannot corroborate its own sources |
| Handoff status | **no automatic grade** | — | work state, unless backed by execution or measurement evidence |

The single clearest gain from factoring: the row that v1 called `Traced` is now visibly a
**traceability** statement about a claim whose **quality** is still `Hinted`. Under the chain it
outranked `Corroborated`; under the lattice it is `(Q1, T2)` and nobody can mistake it for a
verification.

### 4.6 Mechanical vs judged evidence

Unchanged from v1 and worth restating: mechanical evidence — content hashes, structural diffs,
schema checks, test results, protocol validators, execution attestations — SHOULD be produced
eagerly because it is cheap, repeatable, and high value, and it is what moves the **T** axis. Model
judgment SHOULD be lazy, memoized by exact input frontier, capped by policy, and it moves the **Q**
axis at most to `Q2`. An unverified model judgment may support a hypothesis or abstain; it may
propose an opposition frame for verification; it cannot by itself produce an authoritative `False`
verdict or retract another actor's evidence.

---


### 4.7 The ingestion contract — one carrier, one ladder per source class

Added 2026-08-10, after the gap it closes had already cost something.

Heterogeneous producers write measurements in different shapes: an autopilot trial row, an
AutoKernel `evaluation_event`, a sealed benchmark manifest, an intake entry. §4.5 says what the
levels *mean*; until now nothing said how a producer *enters* the carrier. Each adapter therefore
arrived with its own reading of the rule, and on 2026-08-10 two of them were caught disagreeing
about the same input:

| input | `measurement_record.grade()` | `sealed_manifest.grade()` |
|---|---|---|
| no protocol, no attestation | `Judged/T0` | `Judged/Located` |

One constitution, one rule, two answers on the T axis. Neither reading is obviously wrong, which is
the point — a rule reimplemented per source becomes N dialects of itself, and the divergence
surfaces later as unexplainable grade differences between corpora, long after anyone remembers
there were two functions. A substrate built to detect exactly this may not contain it.

**The contract.** An adapter's only job is *projection*: map its native record into the canonical
`ClaimTuple` (`scripts/vidya/claim_tuple.py`). It never grades, and it never invents an element it
cannot find — a missing element is reported and grades the claim down, which is a true statement
about the measurement rather than a hole in it.

```
native record  --project-->  ClaimTuple  --grade()-->  (Q, T, reasons)  --> frames
```

The tuple's vocabulary is not invented here. It is AutoKernel's `claim_grammar`
(`epyc-inference-research` `scripts/kernel_rnd/autokernel/schemas.py`), which already enforces
`MEASUREMENT.md:13` as a REQUIRED schema block — category ∈ {OPTIMUM, BASELINE, CANDIDATE},
`protocol_id`, `metric`, `metric_direction` ∈ {higher_better, lower_better}, `reps` ≥ 1,
`attestation_ref`. The strictest existing producer defines the shape; the newest adapter does not
get to redefine it.

**Source classes.** The carrier is shared. The grading rule is not, and pretending otherwise would
be its own category error:

| class | graded by | ceiling | ladder lives in |
|---|---|---|---|
| `measurement` | the constitution's claim rule (protocol / n / date / attestation) | `Witnessed` | `claim_tuple.py` |
| `literature` | verification status (anchored, dive-verified, dive-overturned) | `Verified` | `adapters/research_intake.py` |

The literature ceiling is structural, not a limitation to be lifted: an intake entry records what
someone else reported, and no amount of careful reading turns it into a protocol-admissible
measurement.

**Dependency-evidence boundary.** Dependency evidence is deliberately not forced through this
carrier. The current tuple structurally requires a metric, direction and measurement category, and
the current frame path turns every tuple into a claim-support edge. A process-recovery rehearsal or
dependency preflight has no honest values for those fields and does not thereby become an
independent corroborating witness. Such a producer may prospectively write self-hashed native
dependency rows, and an adapter may integrity-check and classify them, but it MUST NOT register a
`ClaimTuple` projection or emit `evidence_supports_claim` until a shared dependency-evidence carrier
and warrant rule are declared. Multiple legs from one rehearsal key support on the rehearsal run,
not on each leg, so one run remains one potential support path.

**The invariant, and how it is enforced.** *Each source class has exactly one ladder.* A new class
is a legitimate extension and registers via `register_ladder(class, module)`; a second
implementation of an existing class's rule is a defect and the registry refuses it. A conformance
test (`tests/vidya/test_claim_tuple.py`) fails if any adapter returns a lattice level without
having declared itself a ladder — the check that would have caught the 2026-08-10 divergence on the
day it was written instead of weeks later.

Two structural properties follow from routing every source through one path, and both are pinned by
tests because both have already failed in this program:

* **Identity is derived once**, from `measurement_id`, so an adapter cannot quietly adopt its own
  claim-id scheme. Two adapters previously collided distinct records into one belief — merging
  three arms of a single A/B into one claim.
* **Absence is recorded, never filled.** A row that predates a producer's provenance hook is
  skipped rather than back-filled, because a tuple invented on read claims warrant the original run
  never captured.

## 5. The fold

### 5.1 Determinism inputs

A fold is a pure function of: accepted frames up to a ledger frontier; schema and canonicalization
version; rule-set version; grade/authority/freshness policy version; the source and instrument-era
registries the rules read; an explicit `as_of` timestamp; and the pinned implementation version.
Wall-clock time MUST NOT be read inside the fold. Identical inputs MUST produce bit-identical
derived state.

### 5.2 Provenance semantics — pin it, and know what breaks

The fold's provenance semantics MUST be an **all-trees semantics (P^AT)** or another semantics
proven to satisfy the Deletion Property. This is not a free choice:

- Deletion (Property 13, KR 2022) holds for P^AT / P^NRT / P^AM / P^SAM;
- it **fails for minimal-depth semantics** (P^MDT, P^HMDT).

A minimal-depth or "shortest-derivation" optimization — the natural thing for an engineer to reach
for — silently destroys exact retraction. Example 9 of that paper is adopted as a **negative test
vector**: any candidate fold optimization MUST reproduce it and fail closed.

On an absorptive carrier, P^AT / P^NRT / P^AM / P^SAM coincide, so pinning P^AT costs nothing and
buys insertion-monotonicity as well.

### 5.3 Provenance representation

Provenance is stored as a **hash-consed directed acyclic circuit**, never as a flat expression:
polynomial-size circuits exist for absorptive semirings, while formula/sum-of-products
representations are provably exponential. The implementation MUST NOT eagerly expand to disjunctive
normal form; minimal supports are enumerated lazily and only for bounded explanation requests.

Adopted construction details: layered build (one layer per iteration), two-level compaction (only
top and bottom layers retained), semi-naive embedded construction, and self-dependency removal —
the last is licensed specifically for distributive lattices, which the carrier is.

### 5.4 Evaluation — closed forms, no fixpoint test

```text
lfp = F^N(0)                     exactly N applications; no convergence check needed
gfp = F^N(F^N(1)^∞)              and a^∞ = a on ⊗-idempotent lattices, so gfp = F^N(F^N(1))
N   = number of ground IDB atoms
```

Two independent results give the same N: absorptive (1-bounded) semirings reach the least fixpoint
in N plain Kleene steps — no ω-continuity and no commutativity required — and 0-stable semirings
converge in ≤ N steps. **The fold therefore asserts its own budget: exceeding N iterations is an
implementation bug, not a slow case.** The v1 draft's "N+1" is N steps plus the zero-initialization
layer; it is not the Newton bound of n+1, and the two MUST NOT be conflated in the code or the docs.

The greatest-fixpoint form is what makes coinductive rules ("presumed X until contradicted")
implementable at the same cost — roughly 2N iterations.

### 5.5 Retraction

Within the **positive fragment**, retraction is substitution: set the retracted token to 0 in every
circuit that depends on it and re-evaluate. `B = (a⊗b) ⊕ (c⊗d)` with `a := 0` becomes `c⊗d`. Impact
analysis is the same mechanism run in a sandbox without committing the frame.

**This licence stops at negation.** Once absence is tracked, zero-substitution is provably wrong —
deleting facts can collapse the positive polynomial to 0 while the updated model still satisfies the
query. The negation-era primitive is *specialization* of a dual-indeterminate provenance object; it
is developed in the [research program](vidya-research-program.md) §R1 and is **not** in the pilot.
The pilot's rule set MUST therefore be positive, or stratified with the negated strata explicitly
excluded from incremental retraction and handled by full refold only.

**The always-correct shipping path, in every case:** append the retraction frame, apply active-frame
semantics for the requested frontier, and refold from the ledger. Incremental retraction is an
optimization that MUST be continuously checked against the full refold; it can affect latency, never
correctness.

---

## 6. Judgment frames (the LLM-in-the-loop rules)

Any model judgment that can affect a derived result enters as a frame, and the fold's replay
consistency depends on three properties. These are not style guidance: keyed logging of a boundedly
nondeterministic judge has been proven *necessary* for replay consistency (and, with the
first-vote rule, sufficient — a tight characterization).

1. **Key completeness.** A judgment frame MUST be keyed by the read-set it saw plus the full decoder
   tuple: `(prompt, seed, model_version, temperature, tool_output_hash)` — or a content-addressed
   equivalent. A judgment frame that does not record what the judge saw is not a replay key.
2. **First-committed-vote-wins per key.** A re-run judge MUST be short-circuited by the existing
   frame, never appended as a competing vote for the same key. (An append-only ledger permits both;
   the fold enforces the rule.)
3. **No model invocation during fold or replay.** Ever. Any code path that could call a model from
   inside the fold is a defect.

**Trap:** temperature-0 / greedy decoding does **not** make a judge deterministic under this result —
the nondeterminism space includes sampling state and hardware numerics. "We run greedy" is not a
substitute for logging.

**Conflict tie-breaks MUST form a total order** (`grade → timestamp → frame_id`). A partial order
silently breaks n-ary confluence, so the same conflict set can resolve differently depending on
arrival order.

---

## 7. Belief state

### 7.1 Pro/con and verdicts

Positive and negative support fold independently; refutation never subtracts from support, it
creates or strengthens an opposition circuit.

| pro | con | verdict |
|---|---|---|
| below policy threshold | below threshold | `Unknown` |
| meets threshold | below threshold | `Supported` |
| below threshold | meets threshold | `Opposed` |
| meets threshold | meets threshold | `Conflicted` |

### 7.2 Evidence lifecycle

Per-evidence states adopt the LedgerMind vocabulary: **`Active` · `Stale` · `Conflicted` ·
`Dropped`**, with the structural rule that gives them teeth — **a claim may cite only `Active`
entries.** This is a precondition enforced at fold time, not a prompt-level preference; it is the
mechanism form of "stale is never served as current" at claim granularity.

Object classes take different states (closing the v1 dirty/stale ambiguity): **beliefs go `dirty`**
when a registered input changed and recomputation has not completed; **projections and obligations
go `stale`** when they represent an older frontier.

### 7.3 Corroboration statistic

Independence is reported as the maximum number of leaf-disjoint minimal supports, computed
incrementally, cached by circuit hash, searched upward from 1, displayed as `1 · 2 · 3 · 4 · 5+`,
and **explicitly under-approximate when the cap binds**. It stays out of the correctness-critical
fixpoint. Near-duplicate supports MUST be merged before the count (product-style aggregation
otherwise rewards redundancy), with the similarity threshold recorded in the output.

**This statistic is now load-bearing, not decorative.** With `Corroborated` removed from the carrier
(§4.1), it is the *only* mechanical notion of independence in the system, and any policy of the form
`disjoint_supports ≥ k` reads directly from it. Two consequences: a cap that binds MUST be reported
as an under-approximation at the point of use, never silently; and a policy MUST NOT treat "cap
reached" as "≥ cap satisfied" without saying so.

---

## 8. Freshness gating

### 8.1 Mapping onto the existing classifier — not a fork

`dashboard/freshness.py` declares itself "THE ONE CLASSIFIER" for the project. The pilot's states
MUST map onto it rather than introduce a parallel vocabulary:

| Pilot state | Maps to | Note |
|---|---|---|
| `current` | `fresh` | evaluated at the required frontier and policy |
| `dirty` | `aging` | registered input changed; recomputation pending |
| `stale` | `stale` | known to represent an older frontier |
| `expired` | `stale` + validity-interval reason | TTL or validity window ended |
| `unresolved` (anchor) | `missing` | an age nobody could compute is not "fine" |
| `conflicted` / `unsupported` / `unknown` / `blocked` | *(not freshness)* | verdict and policy outcomes, reported on their own axis |

The classifier's independent axes (`observed|silent|absent` × `populated|empty|unknown`) are reused
as-is for adapter reporting. Likewise `MEASUREMENT.md`'s reconciliation verbs
(`retro-certify` / `demote-to-prior` / `retire-view`) are the only vocabulary for reconciling
historical claims — the pilot never invents a synonym.

### 8.2 Query-time gate

Every authoritative query declares: intended use, minimum grade, conflict policy, maximum age or
required frontier, required authority class, whether automatic re-verification is permitted, and
what to do when freshness cannot be established. The gate has five honest outcomes — **validate,
recompute, reverify, abstain, block** — and `Abstain` is a typed terminal transition, not a failure.

### 8.3 Why refusal rather than a warning banner

Recorded as design rationale, because it is counter-intuitive and was measured by others:

- A controlled n=26 study of a claim-level provenance interface found it **significantly lowered
  trust while not changing reliance** — advisory display did not change what people did.
- A staleness benchmark found one outdated passage cuts overall scores by >24% and raises harmful
  outputs, and that retrieval-side mitigation still surfaced stale content ~50% of the time.
- The strongest deterministic-supersession result in the literature stops at *suppression* and
  reports no refusal semantics — the gap this pilot occupies.

---

## 9. Projections

**Sidecar location and banners (ratified 2026-08-09).** Manifests live under `.vidya/projections/`,
keyed by projection id and **bound to the article's content hash** — the binding is what stops a
sidecar from silently describing a different revision of the prose than the one on disk. The wiki
tree itself is left untouched: no front-matter, no adjacent files, nothing in the compiler's scan
set.

**No visible banner in shadow mode.** A banner in shadow can only be advisory, and the audit turned
up direct measured evidence that advisory provenance display *lowers trust without changing
behaviour* (n=26, controlled). Adding wiki noise for a measured non-effect is a bad trade. Freshness
lives in the machine-readable manifest, and at promotion the **gate** does the work — it refuses,
which is the thing banners were failing to do.

A projection (a wiki section, a context pack, a report) MUST declare what it consumed. Its sidecar
manifest records: section id and content hash; belief ids and exact versions rendered; the evidence
frontier and fold version; minimum grade and conflict policy used; unresolved conflicts;
**omissions**; source-set frontier; freshness state; and the review decision that authorized
publication.

**Assertion mapping** uses extract-then-anchor: a model proposes atomic claims, then a
**deterministic** pass locates their exact spans and the manifest is keyed on the located span's
hash. The stochastic step never touches the anchor. Claim criteria are adopted from the published
interface work: atomic, faithful, decontextualized, verifiable, declarative.

**The omissions lane is mandatory.** A manifest reports both what the page asserts and which
relevant beliefs it does *not* surface. A projection that can only enumerate its assertions can be
invalidated only coarsely, and silent omission is the failure mode a reader cannot see.

Anchor preference order: structured record key or trial id → JSON pointer / YAML key path / row id →
AST or heading path plus normalized content hash → byte range plus content hash → line hint plus
quoted-span hash → file hash (conservative fallback). **Line numbers alone are never authoritative.**
When an anchor cannot be resolved the token becomes `unresolved`, dependents recompute
conservatively, and the system MUST NOT infer that the claim is false.

---

## 10. Obligations

An obligation is a governed requirement with an activation expression, a satisfaction expression, an
authority frame, a risk class, and a derived status.

**The condition language is capped for the pilot** (the v1 `any/all` sketch is a DSL waiting to
happen): at most **4 predicate types**, **one nesting level**, and **no user-defined functions**.
The four: `belief_state_in [...]`, `belief_changed <claim_id>`, `projection_current <projection_id>`,
`review_status <status>`. Anything that does not fit routes to explicit human review rather than
growing the language.

Obligation surfacing carries an auto-downgrade rule: if a class of automatically surfaced
obligations exceeds a ratified no-action threshold, that class stops interrupting and reverts to a
passive queue until recalibrated.

---

## 11. Ledger and certificates

### 11.0 Storage — JSONL is canonical (ratified 2026-08-09)

**The ledger is an append-only JSONL file with fsync-per-append. SQLite is a derived, disposable
index rebuilt from it.** Not the other way round.

This follows the house pattern rather than inventing one: the AutoKernel journal and the experiment
journal are both append-only JSONL with fsync-per-event and pure view rebuilds, and this program's
whole premise is riding existing conventions rather than duplicating them. Three concrete
consequences:

- **The canonical record is reviewable in a diff.** A frame append shows up in `git diff` as one
  readable line. A binary ledger would make the one artifact that must never be silently altered the
  one artifact nobody can inspect in review.
- **It is consistent with governance invariant 3** — derived state is disposable and reproducible.
  If the index is canonical, that invariant has an exception at its centre.
- **Adapters keep SQL** — they query the derived index, which is rebuilt by the fold and may be
  deleted at any time.

Ledger records carry: sequence, `prev_hash`, frame content hash, canonical payload, actor, schema
version, and acceptance status. Sharding follows the AutoKernel pattern; shard boundaries SHOULD
align with measurement eras (§11.1). Torn-tail handling is adopted verbatim from that journal: a
crash can only leave a partial trailing line, which the reader drops and the next append truncates
and records — so the loss is itself durable rather than silent.

### 11.1 The authentication ladder

| Rung | What it is | When |
|---|---|---|
| **L0** | append-only JSONL, fsync-per-append, per-record `prev_hash` chain | day one; tamper-*evident* only |
| **L1** | RFC 9162 Merkle roots (domain-separated `0x00`/`0x01`) + C2SP signed-note checkpoints emitted at wrap-up boundaries and **committed to git**; each new checkpoint consistency-proved against the last | **pilot target**, ~200 lines, zero new services |
| **L2** | tlog-tiles / Tessera materialization | only on a real trigger: a second writer, an external verifier, millions of entries, or HTTP-served proofs |

An externally held checkpoint is what upgrades tamper-evident to tamper-proof for all prior history;
git history gives ordering and a second holder for free. Formats are chosen at L1 so that a later L2
migration changes storage, not hashes.

**Pin the spec tags** `signed-note/v1.0.0` and `tlog-checkpoint/v1.0.0`. Upstream main has drifted to
recommending post-quantum ML-DSA-44 cosignatures; a naive "follow main" implementation would diverge.
Watch item, no action until upstream tags a checkpoint version that requires it.

Authenticated surface = entries + proofs + checkpoints. SQL queries are a local convenience layer and
never an authority. Ledger shards SHOULD align with measurement eras so frozen shards become static
artifacts. The ledger is not a time oracle.

### 11.2 Certificates

A query response MAY carry a certificate whose field set is mapped from the SLSA verification-summary
attestation: verifier identity and version; **policy digest** (the ratified grade config by content
hash); `input_attestations` enumerating every consumed frame by ledger coordinate and digest — the
replayability hook; result; grades attained per track; a frontier summary (frame counts per grade);
and the certificate grammar version. A three-valued result vocabulary is reserved now
(`PASSED` / `FAILED` / `ADVISORY`) so certifiable and advisory grades never share a boolean.

**A certificate is itself an attestation frame that re-enters the ledger.** It gets a Merkle leaf, is
covered by the next checkpoint, and is citable by digest in a later query's `input_attestations`.
Verification composes because certificates close over the frame algebra instead of being terminal
artifacts.

A certificate proves that the evidence, rules, and derivation are exactly as represented. It does not
prove the underlying proposition is true.

---

## 12. Policy grades

Consumer policies name their thresholds using the argumentation literature's proof standards, which
encodes the certification boundary in the vocabulary itself:

| Grade | Definition | Certifiable? |
|---|---|---|
| **SE** (scintilla) | at least one applicable pro path | **yes** — from the lattice core |
| **DV** (dialectical validity) | at least one applicable pro path and no applicable con path | **yes** — the Belnap `Supported` cell |
| **PE** (preponderance) | `max_pro > max_con` over advisory degrees | advisory only |
| **CCE** (clear and convincing) | PE ∧ `max_pro > α` ∧ `(max_pro − max_con) > β` | advisory only |
| **BRD** (beyond reasonable doubt) | CCE ∧ `max_con < γ` | advisory only |

Because grades are now pairs, a policy states **two floors and a reading**:

```yaml
use: "wiki-authoritative"
standard: DV                      # certifiable from the lattice core
min_grade: {Q: Q3, T: T2}         # Verified, exactly anchored
reading: conjunctive              # ONE path must clear both floors (§4.4b)
independence: {min_disjoint: 2}   # optional; reads the §7.3 statistic
conflict_policy: reject
```

`reading: conjunctive` is the default for authoritative use; `reading: join` is permitted only for
exploratory policies, and any answer served under it carries the witness set so the reader can see
that two different paths supplied the two coordinates.

Aggregation is **max, never sum** (arguments cannot be assumed independent; accrual is done by
linking premises, not adding weights). `α, β, γ` are policy constants recorded in the versioned,
digested policy object — never chosen per query.

Three gap-closures are **EPYC amendments**, not the source's text, and are marked as such wherever
cited: `max(∅) := 0`; an applicable argument with no weight caps the claim at SE/DV; the frame graph
MUST be acyclic before any standard is evaluated.

**Citation discipline:** SE/BA/DV come from the 2007 paper; the five-standard α/β/γ set comes from the
2009 chapter. "The five Carneades 2007 proof standards" is a citation error.

---

## 13. The advisory overlay (optional)

A read-time degree overlay MAY be computed for ranking and reviewer UX. It is **never** a
certification input.

- Semantics: DF-QuAD, **reimplemented from the published formulas** (~20 lines). Both reference
  implementations are unusable: one repo is under a bespoke non-commercial academic licence, and the
  library it vendors has no licence at all.
- Evaluation is **exact** on the acyclic condensation of the provenance graph — one topological pass,
  no iteration, no tolerance parameters, no convergence knobs. Pin float64 and a canonical node
  order and the overlay is deterministic. If cycles are ever admitted, pin and record semantics id,
  tolerances, a fixed iteration count (never wall-clock), per-node converged flags; non-converged
  nodes render as "no advisory degree", never a stale number.
- Base scores are reviewer-asserted; unscored nodes default to 0.5. Degrees inherit the epistemic
  status of their inputs — measured sensitivity to base-score choice reaches ~0.19 accuracy swing,
  which is precisely why they rank and never certify.
- Reviewer affordances: contest-a-base-score and contest-a-polarity, with deterministic recompute.
- Deduplicate near-identical pro/con items before computing degrees.

---

## 14. Coverage check against the field taxonomy

The pilot's frame types are audited against the nine-relation provenance vocabulary from the 2026
agent-provenance survey. Covered: **Support** and **Contradict** (pro/con edges), **Derive**
(provenance circuits), **Depend-on** (claim-level manifests), **Invalidate** (retraction frames — and
note the survey's own distinction, that agent-Invalidate marks a claim epistemically invalid *while
the record persists*, exactly this design's semantics), **Update** (supersession).

**Settled 2026-08-09 (decision-queue item 6):**

- **`Trigger` — ADOPTED** as `pubinfo.triggered_by` (§3.4), carrying no grade, no authority, and no
  freshness. It answers "why does this frame exist?", which the obligation and freshness machinery
  needs in order to be auditable about its own derivations.
- **`Use` / `Generate` — DECLARED COVERED.** `provenance.derived_from` and `provenance.produced_by`
  *are* these relations; they are already the PROV aliases `prov:used` and `prov:wasGeneratedBy`.
  Closed by documenting the mapping rather than by adding fields.

All nine relations of the survey's vocabulary are therefore accounted for: Support and Contradict
(pro/con edges), Derive (provenance circuits), Depend-on (claim-level manifests), Invalidate
(retraction frames), Update (supersession), Trigger (`triggered_by`), Use and Generate
(`derived_from` / `produced_by`).

### Self-score against the survey's rubric

Scored honestly against the survey's six columns, using its own scale (Yes / Partial / Limited / No).
No surveyed system reached `Yes` on the last three simultaneously; the best scored
Limited/Partial/Partial. This is what the pilot claims, and what it does not:

| Column | Pilot | Basis |
|---|---|---|
| Write provenance | **Yes** | every frame carries actor, authority scope, method, anchored source revision, and content-addressed identity (§3) |
| Retrieval provenance | **Partial** | projection manifests record which belief versions were rendered and what was omitted (§9); ad-hoc reads outside a projection are not yet manifested |
| Update / evolution | **Yes** | supersession and retraction are first-class frames; belief versions carry their fold inputs; history is never rewritten (§3.4) |
| Conflict handling | **Yes** | pro and con fold independently into four-valued verdicts; conflict is a served state, not an averaged-away one (§7.1) |
| Staleness handling | **Yes** | five distinct clocks, an evidence lifecycle where only `Active` may be cited, and a query gate that refuses rather than warns (§3.2, §7.2, §8) |
| Evidence-aware verification | **Partial** | certificates enumerate consumed frames and the policy digest, and replay is deterministic (§11.2) — but authentication is deferred (§15), so a certificate currently proves derivation, not emitter identity |

The two `Partial` cells are the honest edges: unmanifested ad-hoc reads, and unauthenticated
emitters. Both have named closure paths (projection coverage; the reserved signature fields) and
neither is claimed as done.

---

## 15. Security posture (honest, for shadow mode)

The pilot trusts the local repository and the current execution identity. Consequences stated plainly:

- **Intent-frame forgery is open.** Any local process can emit a `human_intent_recorded` frame. This
  is acceptable **only** because shadow state gates nothing. It MUST NOT survive promotion.
- **Pilot-exit check:** every intent frame in the ledger is reconciled against an actual ratification
  artifact before any promotion proposal is written. A frame with no matching artifact is a defect.
- Schema reserves `signatures` and an actor key-declaration frame now, so authentication is additive
  later and does not change any `frame_id`.
- Content addressing prevents silent byte substitution; it does not authenticate the emitter.
- Adapters read external content under the existing intake quarantine: fetched material is data,
  never instructions.

---

## 16. Cost model (the binding constraint)

Operator attention, not compute, is what this pilot spends. Sizing it is a spec requirement because
the v1 draft's Phase 0 was a multi-session operator project disguised as a checklist item.

| Cost | Estimate | Note |
|---|---|---|
| Claim atomization + review | 15–50 claims per intake batch (5–10 entries × 3–5 claims) | each needs a boundary decision a human must accept |
| Anchor acceptance | one per evidence token | the cheap part, if anchors are structured |
| Dependency-edge declaration | per claim pair | the expensive part; unmapped is a valid, labelled state |
| Gold expected-impact authoring | per mutation class | the v1 killer: hand-deriving the exact *unaffected* set |
| **Recurring** equivalence checks | per anchor-preserving source edit | **MUST be an explicit pilot metric** — it is the operating cost, not the setup cost |

Mitigations built into this spec: the gold corpus is downscoped to 12–20 claims seeded from real
historical corrections whose ground truth is already written down (§17); mutation classes are
introduced incrementally rather than all nine up front; atomization is required only for claims that
cross a governance, projection, or actuation boundary — ordinary prose stays at section granularity.

---

## 17. Evaluation

### 17.1 Corpus

12–20 claims spanning the interesting statuses, seeded from **documented real corrections** rather
than synthetic mutations, plus one measurement-domain family (an E8-era baseline slice) so era and
frontier machinery is exercised where real stakes live. See
[`vidya-pilot-corpus.md`](vidya-pilot-corpus.md).

Real corrections are strictly better than synthetic ones here: their ground truth is already
recorded in `dive_corrections` and the incident log (so gold labels are nearly free), and they are
exactly the failure modes this substrate claims to catch.

### 17.2 Metrics

Adopted from the staleness literature so the pilot is not scored on a home-made scale:

- **+1 / 0 / −1** — correct / abstained / harmful-stale. This rewards refusal over confidently stale
  answers, which is the whole point of the gate.
- **Current-awareness and outdated-awareness** reported separately.
- **Forced-answer stale-fact-error rate** (abstention disabled) — because abstention otherwise masks
  staleness and makes a bad system look safe.
- **Marker-free construction**: stale and current versions must be textually identical except for
  the changed value. Marker-laden benchmarks let a system read the label instead of reasoning.
- Plus: invalidation recall and precision reported separately by failure direction; unaffected-set
  accuracy; grade- and obligation-transition accuracy; coverage-defect rate; determinism
  (incremental vs full-refold mismatches — target zero); and the §16 registration and
  equivalence-check costs.

### 17.3 Determinism suite

Full refold produces a stable state hash; incremental equals full refold; different insertion orders
of causally independent frames converge; repeated folds at the same `as_of` are identical; sorted
impact output is byte-identical; a schema/policy/fold-version change produces an explicit new state
identity; **and Example 9 fails closed** under any candidate optimization.

---

## 18. Governance invariants

1. Primary records are appended, versioned, superseded, or demoted — never silently rewritten.
2. Frames are immutable after acceptance; derived state is disposable and reproducible.
3. A hash proves content identity — not truth, authority, independence, or durability.
4. A projection is never independent corroboration of its own sources.
5. Evidence status and integration disposition stay separate.
6. Human intent authorizes work; it cannot manufacture evidence.
7. Agents may read governing policy; they may not amend human-only policy surfaces.
8. A stale projection is never served as current under an authoritative use policy.
9. An unresolved source change yields dirty / unknown / downgraded / conflicted / blocked — never
   fabricated continuity.
10. Exact impact claims are always qualified by graph coverage.
11. Full refold is the correctness oracle for incremental derivation.
12. Historical decisions remain historical facts even when their premises weaken.
13. Actuators keep their own safety, rollback, and approval gates.
14. External content stays quarantined until the existing intake boundary accepts it.

---

## 19. Open decisions (operator)

**All open decisions were settled 2026-08-09.** The table is retained as the ratification record;
nothing in it blocks P1.

| # | Decision | Recommendation on record |
|---|---|---|
| 1 | ~~Gold corpus contents~~ | **RATIFIED** — 19 claims, four documented corrections + one E8 slice ([corpus doc](vidya-pilot-corpus.md)) |
| 2b | ~~Status-to-grade table~~ | **RATIFIED with the tightening**: verifiers, tests, builds and actuation outcomes cap at `Q3`; `Q4` requires protocol-admissible measurement (§4.2, §4.5) |
| 2 | ~~Grade mapping, incl. Corroborated~~ | **RATIFIED 2026-08-09** — dropped from the carrier; independence is a policy predicate (§4.1). The status-to-grade *table* (§4.5) still needs ratification. |
| 3 | ~~Chain vs product lattice~~ | **RATIFIED 2026-08-09** — product lattice `Q × T` adopted (§4.2) |
| 4 | ~~Sidecar location + banners~~ | **RATIFIED** — `.vidya/projections/` bound to article content hash; **no banner in shadow** (§9) |
| 5 | ~~Canonical pilot ledger~~ | **RATIFIED** — append-only **JSONL is canonical**, SQLite is a rebuildable derived index (§11.0) |
| 6 | ~~Trigger / Use / Generate~~ | **RATIFIED** — `Trigger` **adopted** as `pubinfo.triggered_by`, grade-free (§3.4); `Use`/`Generate` declared covered (§14) |
| 7 | ~~Xu et al. 2018~~ | **RATIFIED** — decline-with-citation; cited as R2 application precedent only |

---

## 20. Rollback

Stop adapters and subscriptions; remove Vidya freshness as a blocking condition anywhere it was
consulted; preserve the ledger and reports for diagnosis; existing workflows continue unchanged;
remove or regenerate any visible stale banners through the existing wiki compiler. Because the pilot
is additive and shadow-only, rollback never requires deleting or rewriting a primary record.
