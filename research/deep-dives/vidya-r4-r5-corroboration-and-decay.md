# R4 / R5 — Corroboration, fragility, and belief decay: first measurements

**Status:** first empirical pass, run against the real 9,599-frame ledger on 2026-08-09.
**R4 has a result, and it is a negative one about the current data, not about the statistic.**
**R5 is time-gated**: the instrument is specified below; the data accrues by running.
**Owning handoff:** [`handoffs/active/vidya-belief-substrate-program.md`](../../handoffs/active/vidya-belief-substrate-program.md) §R4, §R5

---

## R4 — Corroboration and fragility

### The measurement

Leaf-disjoint support count over all 4,191 beliefs derived from the intake index:

| Independent support paths | Beliefs |
|---:|---:|
| 0 | 112 |
| 1 | 4,079 |
| 2+ | **0** |

**100% of beliefs are fragile** — every single one rests on at most one support path, so retracting
that path drops it to unsupported. Not one claim in the corpus has independent corroboration.

### Why, and why it is not a bug in the statistic

The retrofit adapter mints claim IDs **per entry**: `clm_intake_1038_00` belongs to intake-1038 and
to nothing else. Two entries citing the same underlying fact produce two *different* claims, each
with one support path, rather than one claim with two. So the corroboration statistic cannot
observe independence, because the data model forecloses it before the statistic runs.

That is the finding, and it is structural rather than incidental:

> **Cross-entry claim identity is a prerequisite for any corroboration measurement.** Until two
> sources can support the *same* claim, `disjoint_supports ≥ k` is unsatisfiable for every `k ≥ 2`,
> and any policy using it is a policy that always abstains.

This also re-prices the C1 decision from the audit. Dropping `Corroborated` from the carrier moved
independence onto this statistic; the statistic now turns out to be degenerate on current data. The
decision stands — the algebra reason for dropping it (⊕ is idempotent, so the fold could never
derive it) is unaffected — but the practical consequence is sharper than expected: **independence
is currently not measurable at all**, and saying so is more useful than reporting a number that is
1 by construction.

### What the sources say about cost, and why it does not bite yet

Maximum leaf-disjoint set packing is NP-hard, and W[1]-hard parameterized by the count alone; it is
fixed-parameter tractable only in (count, support-size) jointly. The implemented rule follows the
spec: compute incrementally, cache by circuit hash, search upward from 1, display `1 · 2 · 3 · 4 ·
5+`, and treat any binding cap as an **under-approximation** rather than an exact count.

On current data the hard case never arises — with one path per belief, the packing is trivially 1.
The algorithm is in place ahead of the data, which is the right order, but its cost profile is
**unmeasured** and will stay so until cross-entry claim identity exists.

### Deliverables status

| R4 deliverable | Status |
|---|---|
| Exact bounded algorithm for leaf-disjoint packing | Implemented (`gate._disjoint_supports`, capped at 5) |
| Proof of exactness below the cap | Trivial at the current cap; unproven in general |
| Under-approximation semantics when bounds bind | Implemented and surfaced in the certificate |
| Runtime/memory distribution on real circuits | **Not measurable** — every circuit is a single path |
| Evidence the statistic beats naive source count | **Not measurable** for the same reason |

### The task this generates

Cross-entry claim identity: a mechanism by which two intake entries can be recorded as supporting
the same claim. That is a claim-aliasing problem, it is human-gated (deciding two differently-worded
claims are the same proposition is exactly the judgment the spec keeps out of the fold), and it is
the prerequisite for everything else in R4.

---

## R5 — Belief decay and obligation utility

### Why this one cannot be finished in a session

R5 asks two longitudinal questions:

- Do beliefs survive long enough to compound, or expire before they are reused?
- Do surfaced obligations change behaviour, or become noise people learn to dismiss?

Both need observations separated **in time**. No amount of compute today produces a survival curve
for claims that have existed for one day. This is time-gated, not inference-gated: the correct
deliverable now is the instrument, and the discipline that makes later data trustworthy.

### The instrument

The ledger already provides most of it, which is the point of event sourcing — a snapshot is just a
fold at a frontier, so history is queryable after the fact rather than needing to have been
recorded prospectively.

**Available today, retrospectively, from any ledger:**

- claim age (first `claim_proposed` frame per claim);
- grade trajectory per claim (fold at successive frontiers; the `as_of` argument makes this exact);
- retraction and correction events with their timestamps;
- time-to-first-reuse, once a projection or query cites a claim, because both record which beliefs
  they consumed.

**Missing, and needing a write-time decision now** — these cannot be reconstructed later:

1. **Query log.** Reuse is unobservable unless queries are recorded. A `query_served` frame
   (claim, policy digest, outcome, frontier) makes reuse and abstention rates measurable, and costs
   one append per authoritative query.
2. **Obligation disposition.** Acceptance / action / dismissal must be recorded when it happens.
   An obligation whose outcome is not written down cannot be scored, and this is precisely the
   metric the spec's auto-downgrade rule depends on: a class of obligations exceeding a ratified
   no-action threshold must stop interrupting people.

Without (1) and (2), R5 is unanswerable no matter how long the pilot runs — which is why they are
named here rather than deferred with the rest of R5.

### Baseline, 2026-08-09

Recorded so a later comparison has something to compare against:

| Quantity | Value |
|---|---:|
| Beliefs | 4,191 |
| Claims with a correction recorded | 652 (15.6%) |
| Entries carrying a correction | 150 of 1,067 (14.1%) |
| Opposition-only beliefs (`dive-overturned`) | 112 (2.7%) |
| Anchored claims | 1 |
| Beliefs with independent corroboration | 0 |
| Beliefs passing a conjunctive `Verified/Anchored` policy | 1 |

The 15.6% correction rate is the most interesting number here: roughly one claim in six from a
dived entry has had *something* corrected about it. Whether that reflects a healthy correction
culture or a high initial error rate is exactly the kind of question a longitudinal series answers
and a single snapshot cannot.

### Deliverables status

| R5 deliverable | Status |
|---|---|
| Longitudinal survival / downgrade / expiry distribution | **Time-gated**; retrospectively computable once time passes |
| Time-to-first-reuse, reuse count | **Blocked on the query log** (write-time decision above) |
| Obligation acceptance / action / dismissal rates | **Blocked on disposition recording** (write-time decision above) |
| Context and labour savings from surviving beliefs | Downstream of the two above |
| Releasable anonymized schema or synthetic benchmark | Not started; the frame schema is already public in-repo |

---

## R3 — semantic identity and purity as evidence

Severed from the pilot and **not started**, per the audit and the ratified split. It has no bearing
on a substrate that tracks research claims and wiki prose rather than code identity; the recommended
position if it is ever resumed is the directed normalizer, with equality saturation earning its
place only on measured need. See
[`docs/design/vidya-research-program.md`](../../docs/design/vidya-research-program.md) §R3.
