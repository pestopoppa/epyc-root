# Vidya Pilot Gold Corpus

**Status:** **RATIFIED by the operator 2026-08-09** (decision-queue item 1) — 19 claims, frozen at the commit that lands this file
**Date:** 2026-08-09
**Owning handoff:** [`handoffs/active/vidya-belief-substrate-program.md`](../../handoffs/active/vidya-belief-substrate-program.md) §P0
**Spec:** [`vidya-pilot-spec.md`](vidya-pilot-spec.md) §17

---

## 0. Why real corrections instead of synthetic mutations

The v1 draft proposed inventing ~9 mutation classes and hand-deriving an expected impact report for
each — including the exact *unaffected* set. That is the single largest operator cost in the pilot,
and it produces test cases nobody has ever seen fail.

EPYC has something better: **four fully documented correction events**, each with a claim that was
believed, evidence that changed, and a propagation outcome already written down in
`dive_corrections`, incident logs, and progress records. Their gold labels are nearly free, and —
decisively — they are the exact failure modes this substrate claims to catch.

They also differ from each other in the way that matters. One propagated cleanly, one propagated
*too far*, one was caught just before a verdict shipped, and one **failed silently and was still
wrong at HEAD when this corpus was assembled**. A substrate that scores well on all four is being
tested against real variance, not a synthetic distribution.

Every fact below was verified against the tree on 2026-08-09 with file:line citations.

---

## 1. Corpus composition

| Family | Claims | What it exercises |
|---|---|---|
| **E1** ngram drafter retraction | 4 | magnitude retracted, mechanism retained; over-propagation |
| **E2** quality-NULL scorer artifact | 4 | a scorer bug flipping a verdict; two-hop supersession |
| **E3** fabricated citations | 3 | fabricated evidence; a correction that never landed |
| **E4** renamed-kernel incident | 3 | anchor rot; role survives, label does not |
| **M** E8-era measurement family | 5 | era scoping, frontier, protocol-grammar claims |
| **Total** | **19** | inside the 12–20 target |

---

## 2. E1 — The ngram drafter retraction (2026-07-30 → 2026-07-31)

**Record:** `master-handoff-index.md:271` (N26) · `speculative-decoding-mtp-refresh.md:166-184` ·
`numa-placement-defect-20260730.md:1278-1300` · `INCIDENT_LOG.md:85-94` ·
`cpu-inference-optimization-index.md:76` · progress `2026-07-31.md:52-58`

**What happened.** A speedup claim for a context-drafting path was retracted one day after it was
made: the benchmark repeated a single prompt against a warm server, so the drafter was copying the
model's own prior generation. Corrected values sit flat around zero (−17.4% to +2.7% across 16
cells); an independent re-run with three distinct prompts per rep put the composed path at −4.2% to
+1.3%.

**Claims:**

| id | Claim | Gold behaviour on retraction |
|---|---|---|
| `e1-c1` | the drafter delivers a large decode speedup on the composed path | **retracted** — unsupported after the artifact is withdrawn |
| `e1-c2` | the composed production recipe is the right default | **untouched** — carried by standing operator decision at an accepted ~−1.6% cost; "retracting the speedup does not retract the recipe" (`numa-placement-defect-20260730.md:1293-1296`) |
| `e1-c3` | the ngram path needs no draft model, so it is the only speculative path available to the SSM-hybrid role | **untouched** — explicitly marked still true; only the magnitude was withdrawn |
| `e1-c4` | the `MONOTONE CLIMB` harness flag indicates an invalid cell | **should never have been believed** — a control cell trips it too; it means "inspect", not "void" |

**Why this family is load-bearing.** It is the corpus's clearest **over-propagation** test. The
correction generalized into "do not deploy this path ANYWHERE" (`speculative-decoding-mtp-refresh.md:178`,
SR-5, still open), which now contradicts the live operator decision — *both statements are in the
tree and a reader cannot tell which governs*. A substrate that marks `e1-c2` and `e1-c3` stale here
reproduces a real, currently-open defect. It also **failed to generalize**: hours later a different
benchmark reproduced the identical artifact, because the first fix screened *prompts* when the
copied text was the model's own *generation* (`INCIDENT_LOG.md:85-94`).

---

## 3. E2 — The quality-NULL scorer artifact (2026-07-24, n=533)

**Record:** `architect-model-selection-bench.md:7-20, :411-417` · `architect-bench-runbook.md:219-228` ·
`scoring-infra-standardization.md:6-14, :18-25, :31-51` · `wiki/benchmark-methodology.md:542` ·
progress `2026-07-23.md:505-513`, `2026-07-24.md:28-52`

**What happened.** Pooled per-question data (n=533) showed two arms significantly beating a third
(p=0.005 / 0.043). The cause was a stale answer extractor that dropped bare-letter final-line
answers, leaking **15% of one arm's items to false parse failures against 0% for another** — a
systematic bias against models that show their work. Offline re-scoring from stored responses (zero
GPU) moved that arm 43.4% → 53.0%; every pairwise comparison became null (p ≥ 0.23).

**Claims:**

| id | Claim | Gold behaviour on re-score |
|---|---|---|
| `e2-c1` | arms A1/A3 are significantly higher quality than A4 | **overturned** → the pooled comparison is null |
| `e2-c2` | the parse-failure rate is a model property | **overturned** → it is a scoring artifact |
| `e2-c3` | AutoPilot's eval-tower grading is affected by the same bug | **must stay untouched** — its grader is LLM-judge-based with zero regex extraction; independently audited with 59 file:line citations |
| `e2-c4` | the separate math-scorer null result is affected | **must stay untouched** — a different scorer (symbolic), already null |

**Two properties make this the best propagation test in the set.** First, *a scorer fix in code does
not propagate to already-stored per-question files* — the stored fields are point-in-time, and "one
un-regenerated file flipped the verdict" (`architect-bench-runbook.md:219-222`). That is precisely a
projection-staleness event with a mechanical trigger. Second, the conclusion **moved again**: a later
sealed tool-use comparison superseded the "quality-tied" reading. A substrate must represent
supersession of a superseding claim without erasing either.

---

## 4. E3 — Fabricated citations (2026-07-25) — including one that was still wrong at HEAD

**Record:** progress `2026-07-25.md:53-58, :90-96, :269-273` · `intake-derived-work-2026-07-25.md:81`
(ID-10b) · `research/intake_index.yaml` intake-888 / intake-895 / intake-896 · commit `c942728e`

**What happened.** Two Stage-1 summariser agents invented specifics that were persisted to the index
and read as evidence. One was an ablation table that does not exist in its paper — and which had
additionally been **cross-pasted into an unrelated entry**. The other was a four-step tool behaviour
absent from a blog post that contains two generic sentences on the subject.

**Claims:**

| id | Claim | Gold behaviour |
|---|---|---|
| `e3-c1` | the fabricated ablation figures | **retracted**; the real figures are load-bearing elsewhere and stay valid |
| `e3-c2` | the same figures appearing in an unrelated entry | **retracted from that entry only** — that entry's own independently-verified finding must survive |
| `e3-c3` | the fabricated four-step tool behaviour | **retracted** |

**This family carries the corpus's sharpest finding.** Three separate records — a progress file, a
governance handoff, and a later re-source note — each assert the second fabrication was "struck" or
"purged". **It was never removed from the index.** It sat at HEAD for fifteen days serving the
fabricated mechanism as "CONFIRMED and understated", while every narrative record said it had been
handled. Verified during this corpus build and **repaired 2026-08-09** (entry now
`dive-overturned` with a `dive_corrections` record).

The generalizable rule, now written into that entry: **a correction recorded only in narrative is
not a correction.** It is strictly worse than an uncorrected entry, because a reader who checks the
record is told the problem was handled. This is the single strongest argument in the corpus for
machine-checked correction propagation — the failure was invisible to every human process that
looked at it.

*Discrimination test:* a crude "quarantine the contaminated entry" response would have destroyed
`e3-c2`'s host entry, whose own dive had independently **overturned a claim in the opposite
direction** (two metrics diverge by up to 26.5 points on weak models) — a good result that a naive
blast radius would have deleted.

---

## 5. E4 — The renamed-kernel incident (2026-08-09)

**Record:** `research/intake_index.yaml:57821-57834` (intake-1030 amendment) ·
`k28-fused-chunked-gdn-kernel-research.md:457-464` · `.claude/skills/research-intake/SKILL.md:183-200` ·
`wiki/hardware-optimization.md:1783`

**What happened.** Two independent sources — an undated article and a maintained upstream catalog
pinned to a head six weeks before ingest — both named a kernel symbol that no longer exists under
that name. Neither was wrong when written; both were wrong when read; neither recorded the head it
was true at.

**Claims:**

| id | Claim | Gold behaviour on the upstream rename |
|---|---|---|
| `e4-c1` | the stage-2 kernel is named `..._kkt_solve_kernel` | **anchor unresolved** → the claim is dirty, not false |
| `e4-c2` | the prefill decomposes into four separately-autotuned stages | **untouched** — the decomposition is correct and load-bearing; only the *label* rotted |
| `e4-c3` | the symbol is absent from upstream | **should never have been believed from one file** — a single-tree grep nearly produced a false fabrication call |

**Why it belongs.** This is the corpus's **anchor-rot** case and its best-propagated correction:
the rule was authored at discovery time and landed in an executable artifact (the intake skill), not
only in prose. It is the positive control against E3's negative one. `e4-c3` also encodes the
opposite error — the near-miss where a correct source was almost declared fabricated.

---

## 6. M — The E8-era measurement family

**Record:** `MEASUREMENT.md:81, :107-108, :201-203` ·
`epyc-orchestrator/orchestration/instrument_eras.yaml:140-172` ·
`cpu-inference-optimization-index.md:75` · `non-inference-backlog.md:185`

**Scope caution, verified:** the v8 cutover produced **three era rows with three naming
conventions**, and only `E8-cpu-kernel` is still current — the `autopilot_speed` and bare `E8`
(`eval_quality`) rows were superseded (now E15). Era ordinals do **not** track kernel versions, and
there is no `E7-cpu-kernel` at all. That trap is itself worth encoding: a naive
pattern-bump produces a phantom era id.

| id | Claim | Protocol / evidence |
|---|---|---|
| `m-c1` | frontdoor decode 40.22 tok/s with speculative decoding on | `P-BENCH-PLACEMENT-1`, n=3, 2026-07-30, durable attestation |
| `m-c2` | ingest-role decode 10.12 tok/s, `category=OPTIMUM` | `P-BENCH-1`, n=5, 2026-07-31 |
| `m-c3` | two roles were served at 46% / 54% of canonical throughput (placement defect) | `P-BENCH-PLACEMENT-1`, r=10, fixed 2026-07-31 |
| `m-c4` | first-touch placement moved fleet decode 40.91 → 52.13 tok/s | `P-BENCH-PLACEMENT-1`, 2026-07-31 |
| `m-c5` | corrected router throughput priors (24.3 → 40.22; 38.46 → 56.86) | derived from `m-c1`, 2026-07-31 |

**What this family exercises that the prose families cannot:** era scoping (a claim valid only
within its era), the protocol-grammar requirement (metric + protocol id + n + date + attestation),
durable-evidence rules, and derived-claim propagation — `m-c5` is *derived from* `m-c1`, so
retracting `m-c1` must propagate to it.

`m-c5` is also independently instructive: it repaired a **silent-fallback defect** where a router
read an optimized value with a fallback default, making an unmeasured prior indistinguishable from a
measured one at the read site. The repair set the field to null — *not measured, and not
fabricated* — which is exactly the `unknown`-vs-`unsupported` distinction the substrate must
preserve.

**Excluded, with reasons** (recorded so they are not re-litigated): a preliminary results table
whose cells are all `TODO-FILL`; a GPU decode row (the era registry has no GPU scope, so labelling
it E8 would be a category error); and an AutoPilot quality baseline that was measured, stamped
applied, and then **silently lost to a lost-update** — excellent negative-control material for a
later phase, but not a live claim.

---

## 7. Mutation schedule (incremental, per spec §16)

Not all nine v1 classes at once. Order by what the corpus already proves:

| Round | Mutations | Families |
|---|---|---|
| **1** | source edit (anchor-preserving) · retraction | E1, E3 |
| **2** | correction narrowing scope · anchor rot (rename) | E2, E4 |
| **3** | supersession of a superseding claim · derived-claim propagation | E2, M |
| **4** | era boundary · expiry · conflicting source | M |

Rounds 3–4 open only after rounds 1–2 pass, so the engine is never chasing nine failure modes at
once.

---

## 8. Gold-labelling protocol

1. For each mutation, the expected affected set **and** the expected untouched set are written
   before the engine runs — sourced from the records above, not re-derived.
2. At least one reviewer labels each mutation **without seeing** the engine's impact output.
3. Disagreements are resolved and recorded before scoring.
4. If the gold set changes after results are known, both pre- and post-amendment scores are retained.
5. The corpus is frozen at a named commit; changing it to make a test pass requires an explicit
   amendment record.

**Carrier note (ratified 2026-08-09).** Gold labels are recorded as `Q × T` pairs, not single
grades. This materially improves several corpus cases: E4's renamed kernel is a pure **T**
regression (the anchor stopped resolving) with **Q** untouched, which under the old chain could only
be expressed as a vague downgrade; and E2's scorer artifact is a pure **Q** event (the evidence was
always exactly anchored — it was the verification that was wrong). A substrate that moves the wrong
axis on either case is measurably wrong in a way the chain could not have detected.

**Scoring** uses the metrics in spec §17.2: +1 / 0 / −1 (correct / abstained / harmful-stale),
current- and outdated-awareness separately, forced-answer stale-fact-error, marker-free
construction, and invalidation recall/precision reported separately by failure direction.

---

## 9. Ratification (decision-queue item 1) — GRANTED 2026-08-09

The operator ratified the four families and the measurement slice, the claim list per family, the
mutation schedule, and the freeze commit. Changing any of it now requires an explicit amendment
record retaining both the pre- and post-amendment versions. Nothing here has been used to score
anything yet — the engine does not exist.

**Carrier note:** gold labels are `Q × T` pairs, and `Q4` is reachable only by protocol-admissible
measurement (spec §4.2, ratified 2026-08-09). That caps the `M` family's claims at `(Q4, T3)` and
every prose-family claim at `(Q3, T2)` or below — which is correct: none of E1–E4 is a measurement.

**One finding does not wait for ratification** — the E3 defect was a live data error in
`research/intake_index.yaml` and was repaired on discovery (2026-08-09). Its retraction record now
lives in the entry itself, which is also what makes it usable as a corpus case.
