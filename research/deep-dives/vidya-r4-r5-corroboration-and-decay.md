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

### Unblocking it — candidate generation, 2026-08-10

"Human-gated" was doing too much work as a reason to stop. The judgment is human; **finding the
pairs worth judging is not**, and nobody was ever going to hand-scan 4,191 claims for 8.8M pairs.
`scripts/vidya/alias_candidates.py` proposes and ranks; a human decides. First run against the
real ledger:

| | |
|---|---:|
| Claims considered | 4,191 |
| Pairs surviving rare-term blocking | 780,140 |
| Pairs scored (≥2 shared rare terms) | 74,948 |
| Candidates at score ≥ 0.35 | **45** |

45 rows is an afternoon of review, not a research programme. Scoring is IDF-weighted Jaccard over
stopword-stripped terms — deterministic, no model call, so a review can be resumed or audited. Two
filters are load-bearing and both are tested: **same-entry pairs are never proposed** (two claims
of one entry are one source, and aliasing them would manufacture the exact fake independence the
statistic exists to detect), and every row starts `pending` with no pre-filled decision.

The worksheet is `artifacts/operator/vidya-alias-worksheet-20260810.yaml`; approved rows become `claim_alias` frames via
`vidya alias-emit`, which refuses any approval that does not name its reviewer.

### What the first run found: source identity is per-entry too

The generator's top candidates were near-verbatim pairs, which is a good sign for recall — and four
of the 45 turned out to be **two entries for one source**. `source_id` in the ledger is minted per
*entry* (`src_intake_418`), so this is the same structural defect as per-entry claim ids, one level
up: intake-418 and intake-797 are both arXiv:2604.08224, and nothing in the ledger says so.

Aliasing those claims is a *correct identity statement* and **not corroboration**. Had the rows
been approved without the distinction, the corroboration statistic would have reported its first
independent supports and every one of them would have been one paper counted twice — a fake
positive strictly worse than the honest zero it replaced. Candidate rows now carry `same_source`,
computed from a normalized locator rather than the ledger's `source_id`.

An index-wide sweep with the same locator key found **5 duplicate-locator groups covering 11
entries**:

| Locator | Entries |
|---|---|
| `arxiv:2505.22954` | intake-772, intake-785 |
| `arxiv:2603.28052` | intake-244, intake-784 |
| `arxiv:2604.08224` | intake-418, intake-797 |
| `url:github.com/avbiswas/fast-rlm` | intake-693, intake-783, intake-901 |
| `url:metauto.ai/neuralcomputer` | intake-315, intake-336 |

The intake validator already errored on duplicate `arxiv_id`; it could not see any of these,
because one entry of each pair records the arXiv id and the other records only the URL.
`check_duplicate_locators` now normalizes both forms to one key and **warns** — deliberately not a
hard error, since a repository or project page can legitimately back two distinct artifacts, and
this project has a recorded lesson against conflating a companion repo with the paper it
accompanies. Reporting prevents the silent failure; a human decides the merge.

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
   one append per authoritative query. **Wired 2026-08-10** and deliberately **opt-out, not
   opt-in**: the failure mode is silent and unrecoverable, so a default of "off" would have left
   R5d blocked indefinitely while every command still appeared to work.
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

### The retrospective series — computed 2026-08-09

I had filed the longitudinal half as time-gated and then contradicted myself two paragraphs
earlier by noting that most of R5 is retrospectively computable. It is. The index carries
`ingested_date` back to 2026-03, so the series exists already:

| Month | Entries | Claims | Dived | Corrected | Overturned | Apparent corr-rate |
|---|---:|---:|---:|---:|---:|---:|
| 2026-03 | 240 | 508 | 0 | 3 | 0 | 1% |
| 2026-04 | 280 | 1,288 | 1 | 7 | 1 | 2% |
| 2026-05 | 135 | 611 | 1 | 3 | 0 | 2% |
| 2026-06 | 76 | 358 | 0 | 0 | 0 | 0% |
| 2026-07 | 206 | 884 | 35 | 49 | 13 | 24% |
| 2026-08 | 130 | 542 | 123 | 88 | 13 | 68% |

**The apparent trend is a trap, and reading it correctly is the finding.** Correction rate appears
to climb from 1% to 68%, which reads as quality collapsing. It is not: corrections are recorded by
*dives*, and dive activity went from ~0/month before July to 123 in August. The series measures
**when verification happened**, not when errors happened. An entry from March has a 1% correction
rate because almost nothing from March was ever dived — its errors, if any, are still there
undiscovered.

The signal that survives that confound is the **overturn rate among dived entries: 27 of 160 =
16.9%**. Roughly one dived entry in six had a load-bearing claim falsified against primary source.
That number is comparable across months because its denominator is dives rather than entries.

This is a worked instance of the substrate's own thesis: an uncorrected claim is not a correct
claim, it is an unexamined one, and a metric whose denominator is "everything" cannot tell the
difference.

### Deliverables status

| R5 deliverable | Status |
|---|---|
| Longitudinal survival / downgrade / expiry distribution | **Computed** (above) — retrospective from `ingested_date`; the 16.9% overturn-among-dived figure is the confound-free signal |
| Time-to-first-reuse, reuse count | Instrument **live 2026-08-10**: `vidya query` appends a `query_served` frame by default (`--no-log` to suppress). The series accrues from here |
| Obligation acceptance / action / dismissal rates | Instrument **live 2026-08-10**: `vidya disposition <id> accepted\|acted\|deferred\|dismissed` |
| Context and labour savings from surviving beliefs | Downstream of the two above |
| Releasable anonymized schema or synthetic benchmark | Not started; the frame schema is already public in-repo |

---

## R3 — semantic identity and purity as evidence

Severed from the pilot and **not started**, per the audit and the ratified split. It has no bearing
on a substrate that tracks research claims and wiki prose rather than code identity; the recommended
position if it is ever resumed is the directed normalizer, with equality saturation earning its
place only on measured need. See
[`docs/design/vidya-research-program.md`](../../docs/design/vidya-research-program.md) §R3.

---

## The substrate models what we READ, never what we MEASURED (2026-08-11)

The pilot was built around `research/intake_index.yaml`, so every belief in it descends from a
literature record. That was the right first target — it is the corpus with the worst provenance
discipline — but it leaves a hole shaped like the organisation's actual work.

**Q4 Witnessed is empty, and cannot be otherwise.** Across 4,224 beliefs the Q axis reads
`Hinted 3,503 · Verified 709 · Q0 12` and **zero at Witnessed**. Spec §4.5 reserves Q4 for "a
protocol-admissible measurement with durable attestation", and an intake entry is a literature
record by construction, so the only adapter that exists cannot reach the top of its own carrier.
A quarter of the warrant axis is unreachable, and the reason is which door the data came through.

**There is no shortage of material.** Outside the index, in curated tracked documents:

| Source | Files | Files carrying magnitudes | Magnitude tokens |
|---|---:|---:|---:|
| `progress/` | 272 | 216 | 9,776 |
| `handoffs/active/` | 180 | 159 | 6,229 |
| `wiki/` | 31 | 29 | 3,885 |
| `research/deep-dives/` | 141 | 131 | 3,408 |

**But the ceiling measurement says an adapter is not the bottleneck.** Applying the P2 discipline —
price the retrofit before writing it — over the 272 progress files: **4,951 lines carry a
magnitude, 4,687 state a result rather than a plan, and 105 (2.2%) cite anything durable.** Reading
those 105, most name a *source file* (`orchestration/task_ir.schema.json`, 249 lines), not a
measurement artifact. The genuinely attested fraction rounds to zero.

So a progress adapter would roughly double the corpus — 4,687 new claims against 4,224 — and every
one of them would top out at `Verified/Located`, gating nothing. **The gap is not a missing reader.
It is that our own measurements are recorded as prose too**, and worse than the literature: a
literature claim at least names a retrievable paper, while

> `**Model Stack:** Qwen3-Coder-30B-A3B-Instruct (45.3 t/s with MoE 4 experts)`

names nothing at all. Nobody can re-derive 45.3 from that line, and in a month nobody will remember
which lineup, which flags, or which era it was measured under.

**What follows.** The fix is the one that has worked twice already in this program — instrument the
write, do not parse the prose. A recorded measurement should cite its artifact the way a dive
records `claim_anchors` and a dependency records `depends_on`. Until then a second adapter would
add volume without adding warrant, which is the opposite of what the substrate is for.

---

## CORRECTION to the section above: the 2.2% figure measured the wrong layer (2026-08-10)

The section above concluded: *"The gap is not a missing reader. It is that our own measurements are
recorded as prose too."* **That conclusion is withdrawn.** The premise measured `progress/` markdown
— the NARRATION layer — and generalized it to the organisation's measurement discipline. The
operator challenged it directly: autopilot, autokernel and the kernel-freeze procedure follow an
explicit measurement constitution. They do. None of them records anything in progress markdown, so
a statistic over progress markdown carries no information about them.

This is the wrong-sample error, committed by the session cataloguing wrong-sample errors, in a
document whose subject is provenance. It is recorded here rather than edited away, because the
corrected number is less interesting than the fact that the method failed where it was being taught.

**What the structured corpus actually looks like** (verified 2026-08-10):

| Corpus | Count | Attested |
|---|---:|---:|
| `artifacts/operator/*.json` (ratifications) | 47 | **34 carry a sha256** |
| research repo, measurement-shaped tracked json/jsonl | 4,562 | — |
| `artifacts/**/manifest.json` | 14 | 6 `SEALED_FOR_OFFICIAL_SCORING` |

A sealed manifest carries the constitution's full claim tuple, field for field:

| `MEASUREMENT_POLICY.md` § The claim rule | sealed manifest field |
|---|---|
| protocol-id | `capture_schema_version` / `schema_version` |
| n/reps | `arms.*.counts` |
| date | `observational_provenance.sealed_at_utc` |
| attestation ref | `runner_sha256`, `hashes_json_sha256`, `authority/*.sha256` |

So `Q4 Witnessed` was never unreachable in principle. It was unreachable because **nothing read
this directory.** Ingesting the six sealed manifests took `Witnessed` from 0 to 6 — the first
decision-gating evidence the substrate has ever held, and it required no new schema, only an
adapter pointed at records that already complied.

**The corrected finding is narrower, and it survives.** Results that live only in progress prose
really are unattested — 105 of 4,687 cite anything durable — and a progress adapter really would add
volume without warrant. But that is a statement about **narration**, not about measurement. The two
were conflated, and the conflation produced a false ceiling on the whole program.

**And the adapter reproduced the bug it exists to detect.** Its first version keyed claims on the
manifest directory's basename. On the real tree `sealed_package` names two different runs and
`input` names three different ARMS of one run, so six sealed manifests folded into three claims —
three arms of one A/B silently merged into a single belief. Fake identity: the same failure already
fixed twice this session at the intake layer, now committed by the instrument built to catch it. It
surfaced only because the output count was checked against the input count (`6 manifests -> 3
claims`) instead of being read as a result. `tests/vidya/test_sealed_manifest.py` pins the
uniqueness property on paths shaped like the ones that broke.
