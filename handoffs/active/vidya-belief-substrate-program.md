# Vidya Belief-Substrate Program

**Status**: active
**Created**: 2026-08-09 (via research intake, operator-approved Stage-3 plan `linear-kindling-possum`)
**Categories**: knowledge_management, agent_architecture
**Audit record**: [`research/deep-dives/vidya-belief-substrate-audit.md`](../../research/deep-dives/vidya-belief-substrate-audit.md) (37 dive-verified sources, intake-1031..1067)
**v1 draft**: `tmp/vidya-epyc-governance-pilot-handoff.md` (2,682 lines; superseded as a plan by this handoff + the audit; retained as the source text for V2.1)

## Objective

Build the claim-level epistemic substrate the audit verified as EPYC's genuine gap: typed
claim/evidence/intent frames on an append-only ledger, a deterministic graded fold, refusal-
semantics freshness gating for research/wiki knowledge, and (later) provenance-gated actuation —
by **adopting** the frame/ledger prior art and spending all invention on the epistemic kernel.
Operator priority: an integrated solution that works, not novelty.

## Relationship & constraints (read before any task)

- **Rides, never rivals**: [`evidence-plane-ledger-and-sequential-verdicts.md`](evidence-plane-ledger-and-sequential-verdicts.md)
  conventions (per-question row shape, supersession folding, era discipline) and the
  `autokernel/journal.py` patterns (fsync-per-event, pure rebuild, `RETRIEVAL_SUPERSEDED`,
  view-consistency checks) are the house style this program extends to the research/wiki domain.
  The H1 non-overlap contract stands: the evidence plane remains authoritative for trial/verdict
  events.
- **Scope = the three verified gaps**: (1) claim-level dependency edges for research/wiki
  knowledge (NOT-FOUND as any existing design); (2) refusal-semantics freshness gating of
  knowledge; (3, later phase) provenance-gated actuation. Cross-worker snapshot coherence and the
  value-divergence axis are *related* diagnoses owned elsewhere — reference, don't absorb.
- **Read-only surfaces**: `MEASUREMENT.md` + annexes (human-amendment-only),
  `orchestration/instrument_eras.yaml` (append-only, human-written). Measurement artifacts are
  evidence; the constitution decides admissibility.
- **Vocabulary: map, don't fork**: `retro-certify`/`demote-to-prior`/`retire-view`
  (MEASUREMENT.md §6); `fresh`/`aging`/`stale`/`missing` + `observed|silent|absent` ×
  `populated|empty|unknown` (`dashboard/freshness.py` is "THE ONE CLASSIFIER" — any new freshness
  state must map onto or extend it explicitly); `accumulating`/`confirmed_improvement`
  (sequential verdicts).
- **Shadow-only until promotion**: nothing here gates a production decision; rollback = stop
  adapters, keep the ledger for diagnosis.

## Key file locations

- **The V2 output (start here — this is now the binding spec, not the v1 draft):**
  [`docs/design/vidya-pilot-spec.md`](../../docs/design/vidya-pilot-spec.md) ·
  [`docs/design/vidya-research-program.md`](../../docs/design/vidya-research-program.md) ·
  [`docs/design/vidya-architecture-appendix.md`](../../docs/design/vidya-architecture-appendix.md) (non-binding)
- Audit + adoption kit (all schemas/specs to copy): `research/deep-dives/vidya-belief-substrate-audit.md` §§4–5
- v1 draft (superseded source text for the V2 split): `tmp/vidya-epyc-governance-pilot-handoff.md`
- Intake entries with paste-ready extracts: `research/intake_index.yaml` intake-1031..1067
  (notably 1063 = byte-exact L1 checkpoint spec; 1062 = proof-standard definitions; 1064 =
  certificate field map; 1035 = judge-discipline rules)
- Existing machinery to ride: `handoffs/active/evidence-plane-ledger-and-sequential-verdicts.md`,
  `repos/epyc-inference-research/scripts/kernel_rnd/autokernel/journal.py`, `dashboard/freshness.py`

## Completed Scope

Landed and validated tracks — audit session, intake-index defects, V2 spec revision, P0 pilot
corpus, P1–P5 pilot build, the promotion track, and the R1–R5 research program — moved to
[`../completed/vidya-belief-substrate-program-completed-through-2026-08-10.md`](../completed/vidya-belief-substrate-program-completed-through-2026-08-10.md)
so the live work is visible here. Nothing was deleted; that file is the evidence record for every
gate this program has already passed.

## Task list

### Open work — start here

Outstanding tasks live in **Source coverage** (`SC6-LIVE`, `SC11`, `SC7`, `SC6-HAZARD`) and
**Consumption** (`SC12-ENTRY`, `SC14-B`, `SC15`, `SC16`, `SC17`). Everything else is complete and lives in the completed sibling
linked under Completed Scope.

The write side is done and the read side now exists: `cli.py cite-check` gates citations,
`cli.py corrections` ranks the adjudication backlog, and `autopilot_settled.py` exposes settled
ground to the planner (SC14-A). The open items are the ones a machine must not do alone —
`SC15` needs a human reading dive text against claims; `SC12-ENTRY`'s two claim-04 hits on
intake-110#record need a dive owner to amend the entry, not a citation edit; `SC14-B` waits on a
durable current-trial attestation. `SC16` and `SC17` are inherited defaults nobody has chosen
deliberately — decide them, do not just implement them.

### Source coverage — opened 2026-08-10 (operator question: what about wiki/logs/progress?)

- [ ] **SC19 — wire `ChatResponse.contention_gate` (A14) on the write side, BEFORE the branch
      lands.** Filed 2026-08-12 by `mainB`, the author of the change, at the change — the property
      that makes a write-side hook trustworthy at all. The surface echoes the contention
      `GateDecision` per request (`admitted`, `waited_s`, `decision`, `candidate_topology_idx`, plus
      a `gate_decisions` list for multi-pass requests). **It is a producer by definition:** its
      entire stated purpose is to convert an inferred verdict into a measured one — ROUTE-A1 today
      infers admit-vs-queue from a fail-closed 503 timeout, and `queued_then_admitted`
      (`admitted=True` with `waited_s > 0`) is *structurally invisible* to that proxy.
      **The window is now and it is narrow:** the code is parked on `a14-gatedecision-echo` @
      `a7d7bdb6` and NOT yet merged. Wiring the write side is cheap while it is unmerged and
      permanent afterwards; retrofitting the read side is impossible, per the standing rule.
      **Locator trap, specific to this source:** the natural locator is the request/chat id, but one
      request can emit MULTIPLE decisions — the `_dispatch` path records every candidate tried, not
      just the winner, deliberately, so the probe can see the walk down the placement priority
      order. A naive per-decision count therefore reads ONE request as N independent witnesses. Key
      on the request, not the decision. (Same class as the run-level trap `mainA` recorded for the
      affinity-preflight source, and as the `benchmarks/results` same-harness case.)
      **Price it first** per the P2 discipline before any bulk adapter: the surface emits nothing
      until the branch lands, so the honest state today is `candidate — ready, unwritten`, not
      `live`. Source-table row added in `scripts/vidya/adapters/README.md`.
      **Self-caught, and the trigger is worth keeping:** I built this surface earlier tonight and
      filed no wiring task until `mainA` published the right test — *"you touched a producer", not
      "you thought about producers"*. A checklist keyed on the diff catches it; one keyed on intent
      does not. Four instances in one day (v9 freeze receipt, mainA's affinity-preflight surface,
      this one, and the standing `benchmarks/results` proof) says the rule is known and the trigger
      is what is missing.

- [x] SC1 **Measured the gap rather than assuming it.** The substrate models only what we READ:
      across 4,224 beliefs the Q axis is `Hinted 3,503 · Verified 709 · Q0 12` and **zero at
      Witnessed**, because spec §4.5 reserves Q4 for a protocol-admissible measurement with durable
      attestation and the only adapter reads literature. A quarter of the carrier is unreachable
      for a reason that is purely about which door the data came through ✅ 2026-08-10
- [x] SC2 **Priced the retrofit before writing it** (the P2 discipline). Over `progress/`: 4,951
      lines carry a magnitude, **4,687 state a result, and only 105 (2.2%) cite anything durable** —
      most naming a source file, not a measurement artifact. A progress adapter would double the
      corpus and every claim would top out at `Verified/Located`, gating nothing ✅ 2026-08-10
- [x] SC2-C **Corrected SC2's conclusion — it measured the wrong layer.** SC2 generalized a
      progress-markdown statistic into "our own measurements are recorded as prose too". Operator
      challenge: autopilot, autokernel and the kernel-freeze procedure follow an explicit
      measurement constitution. They do, and none of them writes to progress markdown, so the
      statistic said nothing about them. Verified structured corpus: **47 tracked ratification JSONs
      (34 carrying a sha256), 4,562 measurement-shaped tracked json/jsonl in the research repo, 14
      `artifacts/**/manifest.json` of which 6 are `SEALED_FOR_OFFICIAL_SCORING`**. The narrow
      finding (prose narration is unattested) survives; the generalization to the measurement layer
      is withdrawn ✅ 2026-08-10
- [x] SC3 **Instrumented the WRITE for measurements** — `scripts/vidya/measurement_record.py`
      implements `MEASUREMENT_POLICY.md` § The claim rule as a grading function rather than
      paraphrasing it: no protocol → `Judged` (the constitution's OBSERVATION, never
      decision-gating); protocol without attestation → `Verified/Located`; artifact named but
      unhashed → `Witnessed/Anchored`; full tuple with the artifact present and hashed →
      `Witnessed/Attested`. Every downgrade names its own cause. Validation refuses a record it
      cannot grade honestly (category must be exactly one of OPTIMUM/BASELINE/CANDIDATE) ✅ 2026-08-10
- [x] SC4 **Ingested the sealed-manifest corpus** — `scripts/vidya/adapters/sealed_manifest.py`.
      A sealed manifest already carries the constitution's full tuple (`capture_schema_version` →
      protocol, `arms.*.counts` → reps, `observational_provenance.sealed_at_utc` → date,
      `runner_sha256`/`authority/*.sha256` → attestation). **Q4 Witnessed: 0 → 6.** Two refusals are
      deliberate: an unsealed manifest is a run in progress, not a result; and a manifest whose named
      artifacts are absent grades DOWN rather than being skipped, because a hash over a missing file
      proves nothing ✅ 2026-08-10
- [x] SC4-BUG **The adapter reproduced the fake-identity bug it exists to detect.** v1 keyed claims
      on the manifest directory basename; on the real tree `sealed_package` names two runs and
      `input` names three ARMS of one run, so 6 manifests folded into 3 claims and three arms of one
      A/B merged into a single belief. Caught by checking output count against input count, not by
      reading the output. Fixed to a path-relative identity, 12 bad frames retracted (9 collided + 3
      superseded), uniqueness pinned by `tests/vidya/test_sealed_manifest.py` ✅ 2026-08-10
- [x] SC5 **Wiki pages are dependents, not claims** — `scripts/vidya/wiki_dependents.py`.
      **707 dependency edges from 28 pages into 477 distinct intake entries.** Implemented as a
      PROJECTION over the fold, writing nothing to the ledger: a page's citations are re-derivable
      from a file that is already in git, so appending them would have required either a new
      source-level edge frame or one structural "claim" per page — and that second option would put
      28 things in the belief set that are not beliefs. Result: **12 pages carry a stale dependency**
      (all unreviewed corrections), **zero real decay** ✅ 2026-08-10
- [x] SC5-BUG **A coverage gap was being reported as decay.** The first draft flagged intake-12,
      intake-335, 303, 310, 48, 95, 16, 42, 98 as "lost all support". None has ever had a claim
      ingested — the substrate has not read those papers, which is a gap in us, not rot in the page.
      Now classified separately (`uningested` vs `unsupported`), and only decay marks a page stale.
      This moved the headline from 16 stale pages to 12 ✅ 2026-08-10
- [x] SC5-MERGE **Verified the merge redirects rather than trusting a zero.** The report showed 0
      citations resolved through the merge map, which is the kind of silent negative that usually
      means a broken parser. Checked against ground truth: all 4 redirects parse correctly
      (784→244, 336→315, 797→418, 785→772) and the wiki cites none of them, because the merges
      repointed citations at merge time. All 477 cited ids resolve; none dangle ✅ 2026-08-10
- [x] SC6-PRICE **Priced the bulk adapter before writing it, and it does not pay.** Sampled 50
      files from each of the four largest measurement areas (200 total) for the constitution's
      tuple:

      | Area | Files | protocol | reps | date | sha256 | **full tuple** |
      |---|---:|---:|---:|---:|---:|---:|
      | `benchmarks/results` | 2,605 | 12% | 0% | 96% | 0% | **0%** |
      | `benchmarks/root_workload` | 1,156 | 40% | 0% | 40% | 0% | **0%** |
      | `data/batched_decode` | 387 | 88% | 10% | 70% | 0% | **0%** |
      | `artifacts/np_context_study_v8_20260727` | 659 | 42% | 0% | 22% | 64% | **0%** |

      **Zero of 200 carry the full tuple; `reps` is essentially never recorded and `sha256` is
      absent from three of four areas.** An adapter over these would add ~4,500 claims that all top
      out at `Verified/Located`, gating nothing — the identical trap SC2 correctly identified for
      progress prose. The bulk-ingest framing of SC6 is therefore REJECTED, not deferred.
      Correction: the original SC6 note cited `execution_manifest.jsonl`; no such file exists in
      the research repo ✅ 2026-08-10
- [x] SC6 **Wired into autopilot's result-write path** (operator chose this hook over the
      llama-bench wrapper and a post-run sealing step, 2026-08-10). `ExperimentJournal.record()`
      now captures the constitution's tuple via `measurement_tuple()` — protocol from the schema
      versions plus the objective policy, reps from the scored denominator, date from the trial
      timestamp, attestation from a sha256 over the entry's own content. Replayed over all **1,372
      real historical rows: protocol_id 100%, date 100%, digest 100% (1,372 distinct), reps 86%**;
      the remaining 197 are skipped/invalid/never-scored trials where absence is correct.
      Read half: `scripts/vidya/adapters/autopilot_journal.py`. Grading stays in this repo next to
      `MEASUREMENT.md` so there is no second implementation of the claim rule to drift
      ✅ 2026-08-10
- [x] SC6-REPS **The first extractor silently understated the corpus by 40 points.** It read only
      the modern denominator keys and found reps on 46% of rows. Probing the gap — rather than
      accepting it — found 545 older rows carrying the denominator under `details.total`.
      Recovering it took coverage to 86%. Because `total` counts what was ATTEMPTED while
      `quality_denominator` counts what SCORED, the tuple now records `reps_basis`, and the adapter
      states it in the grade reasons: "n=55 attempted" and "n=55 scored" are different claims
      ✅ 2026-08-10
- [ ] SC6-LIVE The hook takes effect for trials written **after autopilot next restarts** — the
      running process holds the pre-hook module. No restart was performed: reload ownership belongs
      to the session that owns the inference, at its own boundary. Until then
      `adapters/autopilot_journal.py` correctly reports 0 measured rows. Confirm non-zero after the
      next autopilot cycle
- [ ] **SC32 — Wire future architect MMLU-Pro hardened controls prospectively.** The 2026-08-12
      A1/A3/A4 v9 panel carries native captures, exact claims, pinned source/manifest digests and
      an attestation, but no producer-authored `ClaimTuple` row. Add write-side rows plus a strict
      adapter before any successor run; the completed panel remains pre-hook and emits zero.
- [x] SC8 **The ingestion contract, so the next source is not re-derived from scratch.** The spec
      said what the carrier levels MEAN (§4.5) but never how a producer ENTERS it, so every adapter
      brought its own reading of the rule — and two were caught disagreeing on one input
      (`Judged/T0` vs `Judged/Located`). Now: adapters PROJECT into a canonical `ClaimTuple` and
      never grade; vocabulary is AutoKernel's `claim_grammar`; the carrier is shared but each
      **source class** has exactly one ladder (`measurement` → `Witnessed`; `literature` → capped at
      `Verified`, structurally). `register_ladder()` refuses a second, and a conformance test fails
      any adapter returning a lattice level without declaring itself one ✅ 2026-08-10
- [x] SC8-DOC **Persisted in the three places someone will actually look**: spec §4.7 (the
      contract), `scripts/vidya/adapters/README.md` (implementer's guide + the live source
      register), and `CLAUDE.md` → *Belief Kernel — wiring new sources*. Explainer artifact updated
      with section B10 and the source register ✅ 2026-08-10
- [x] SC9 **Standing practice adopted (operator, 2026-08-10): a process that produces measurements
      or verified findings gets its wiring task filed the MOMENT it is noticed** — one row in the
      source register, one task here. Rationale is an asymmetry, not tidiness: wiring the WRITE side
      is cheap and permanent, retrofitting the READ side is impossible, because a tuple invented on
      read claims warrant the original run never captured. `benchmarks/results` is the standing
      proof — 4,562 files, no write hook, 0 of 200 sampled carrying a usable tuple, permanently
      unable to gate a decision ✅ 2026-08-10
- [x] SC10 **Wire the full AutoKernel `evaluation_event` write/read path prospectively.** ✅
      2026-08-12 — research `3f0cb392` journals live v5 events and attaches the producer-written
      `belief_capture` to measured T1 events. Root `2a83b176` plus the `6c9cad04` repetition-axis
      correction admits only complete current journal envelopes, re-derives every paired raw vector
      and identity binding, treats `claim_grammar.reps` as per-arm repetitions and
      `performance.paired_blocks` as the ClaimTuple scored basis, and emits zero rows for historical,
      null-T0, void, malformed or authority-bearing events. The first real post-hook event remains an
      empirical observation, not a static implementation gap.
- [ ] SC11 Survey the remaining candidate sources named in the register — llama-bench sweeps and the
      speech-kernel (whisper/qwentts) runs. Both need a write-side hook before a reader is worth
      anything; price each with the ~50-record sample before building
- [ ] SC13 **E5 cell affinity-preflight artifacts need a write-side ClaimTuple hook** (filed 2026-08-12
      by `mainA`, at the moment of changing the producer rather than afterwards).
      `affinity_preflight.py` cell mode writes `data/contention_matrix/affinity_preflight_*.json` per
      Stage-B cell and that artifact **already gates `decision_grade`** — `live_affinity_verified` is a
      hard gate and `--require-memory-locality` is an operator-requestable one. Anything that gates a
      grade is exactly what the register says needs a tuple.
      Today's change (orchestrator `74806223`, `d83661a5`) ADDED attested fields — `gpu_tenant_overlaps`,
      `smt_only_contention` (sibling-folded, so a GPU host lane sharing physical cores stops reading as
      disjoint), `live_memory_placement_checked`, `memory_locality_vacuous` — so the producer grew new
      measurement surface without a tuple, which is the SC12 shape repeating a third time.
      **Price it first** with the ~50-record sample; the corpus is small (tens of artifacts), so the
      honest answer may be that the volume never justifies an adapter — in which case record that
      verdict rather than leaving the row open. **Locator must be run-level, not file-level**: repeated
      preflights of one cell are the same witness, not N.
- [ ] SC12 **Kernel promotion/certification and K35 paired kernel/speculation receipts need a
      write-side ClaimTuple hook.**
      The first bounded receipt is `artifacts/audit/v9-dspark-autokernel-base-20260810.json`; the v9
      promotion then produced K35 GPU/DSpark and DFlash production-certification summaries. The K35
      runner now also emits quant-specific paired receipts, first
      `data/deepseek-v4-flash/iq3-dspark-quick-20260811T063729Z/summary.json`. The artifacts are
      durable, but their producers still do not emit the full tuple at write time and must not be
      retrofitted on read. Before the next promotion or K35 paired run, add protocol id, scored
      reps/basis, date, durable attestation locator+digest, category, and metric direction to the
      K35, DFlash, qualification, and final-freeze write paths. Project into the existing
      `ClaimTuple`; `claim_tuple.grade()` remains the only grading rule. Only then price/build the
      adapter
- [ ] SC12-ARTIFACT **Model artifact acquisition/integrity receipts need a prospective write-side
      ClaimTuple hook.** The standardized DeepSeek-V4 DFlash acquisition established the source
      repository and pinned revision, expected/observed byte count, publisher/local SHA-256,
      selected-file scope, metadata summary, process exit and incomplete-file cleanup, but those
      facts were captured in session prose rather than a native receipt. Before the next model
      acquisition, emit one run-level record with those fields plus timestamp, protocol id,
      category, metric direction and durable attestation locator+digest. Project it into the
      existing `ClaimTuple`; `claim_tuple.grade()` remains the only grading rule. Do not retrofit
      this completed acquisition on read
- [ ] SC7 Ingest autopilot trials into the ledger once SC6-LIVE confirms rows are landing. Deferred
      deliberately: appending 1,372 retro-graded claims now would record provenance the original
      runs never captured, and the corpus is worth ingesting only once it is born attested. Note
      `data/benchmark_artifact_inventory.json` is EMPTY (0 rows), which is its own finding
- [ ] SC6-HAZARD Before any bulk ingest is ever reconsidered: support is counted by **source
      locator**, so 2,605 separate result files measuring the same thing would read as 2,605
      independent witnesses. Same-harness runs are not independent evidence. A bulk adapter needs a
      run-level (not file-level) locator or it manufactures corroboration

### Consumption — opened 2026-08-10 (operator question: what consumes these beliefs?)

Audit finding that opened this section: **nothing outside `scripts/vidya/` read the fold.** A grep
across `scripts/`, `repos/epyc-orchestrator/scripts/` and `.claude/` returned zero references, and
the only projection on disk was a 2026-08-09 demo. The engine was complete and had no drivetrain.

- [x] SC12 **Citation gate** — `scripts/vidya/citation_gate.py`, `cli.py cite-check`. Scans project
      documents for `intake-NNN` citations, resolves them forward through the merge map, and applies
      a use policy to what they actually rest on. Live result over **1,754 citations in 142
      documents: 6 overturned, 3 conflicted, 144 resting on an unadjudicated correction.** Blocking
      is exactly `{dangling, overturned, conflicted}` — the three states a citer can act on today;
      `review` warns, per §10's auto-downgrade rule, because blocking on 571 review-required claims
      would fail most of the repository on the first run and get the tool switched off. Precise
      citations (`intake-NNN#03`) gate one claim and are the escape hatch ✅ 2026-08-10
- [x] SC12-FIND **The gate found one real defect and three false positives, and the false positives
      were the more useful finding.** Real: **three documents asserted intake-110#record's
      "+9–16 points" accuracy uplift**, which the authors revised away upstream (their Appendix D —
      the base model was mis-scored by a boxed-only grader; current Table 2 is +0.0 and +3.3pp at
      ~56% compression). Corrected in `reasoning-compression.md` and `wiki/cost-aware-routing.md`.
      **Not real:** the three intake-896#record hits were the documents that *recorded* the fabrication —
      `intake-derived-work-2026-07-25.md` literally says the description "was invented and has been
      struck". The gate could not tell *relying on* a claim from *discussing* the record, which is
      50% of its headline finding, so `#record` was added ✅ 2026-08-10
- [x] SC12-RECORD **`intake-NNN#record` — a reference that discusses the index record rather than
      asserting its claims.** Non-blocking by construction, and deliberately still reports
      `dangling`, because an entry that does not exist cannot be discussed either. The distinction is
      the GATE's, not SC5's: `cited_ids` still counts a record reference as a dependency edge,
      because "which pages name this entry" and "which pages rest on its claims" are different
      questions and collapsing them would silently shrink the graph ✅ 2026-08-10
- [x] SC13 **Correction adjudication queue** — `scripts/vidya/correction_queue.py`,
      `cli.py corrections`. The 103 `correction_reviewed` frames in the ledger came from a one-off
      backfill and **no code path emitted them**, so 571 claims were permanently BLOCKed for
      authoritative use. Now: `list` (ranked by how many documents cite the entry — a queue drained
      in id order is a queue nobody finishes), `worksheet` (every decision `pending`, which emits
      nothing), `emit` (writes `correction_reviewed` + the `claim_corrections` block for the index).
      **129 distinct corrections blocking 571 claims; 81 are cited.** End-to-end verified on a ledger
      copy: 6 claims BLOCK → ALLOW, pending rows untouched ✅ 2026-08-10
- [x] SC13-DEFECT **Two silent defects found while building it.** (1) A correction recorded N times
      — 485 correction frames carry **155 distinct corrections**, because `per_claim_effects` was
      added as `{...} or None` and an explicit null changed the dedup key, re-emitting the corpus.
      `fold` blocks while ANY copy is unreviewed, so reviewing 3 of 4 leaves the claim blocked with
      nothing to show why; the queue now groups by content and emits one frame per copy, and
      `_dedup_key` drops informationless nulls so the next additive field cannot repeat it. (2) The
      queue read claim ids from the correction's own assertion and missed `clm_intake_374_03`, which
      only matches after alias resolution — claim ids are now read back out of the fold ✅ 2026-08-10
- [x] SC12-REGEX **Fixed a live defect in the shared citation scanner.** `citation_gate` reported a
      dangling citation to entry 2602, which does not exist. Source text (hyphen removed here so
      this line does not itself mint a citation): `(intake‑374/378/2602.11149 synthesis)` — the SC5
      run-form pattern ate `/2602` out of an arXiv
      id. The first fix then let the engine backtrack into the partial number `260`; a `\b` anchor
      closes it. SC5's own numbers are unchanged (707 edges, 28 pages) — the bad citation was in a
      handoff, not a wiki page ✅ 2026-08-10
- [x] SC12-FIX **Fixed the citations the gate flagged, and the grading defect underneath one.**
      Documents: `reasoning-compression.md` and `wiki/cost-aware-routing.md` now state the revised
      OPSDC figures (~56–59% compression at **+0.0 to +3.3pp**, not "+9–16 points"); the three
      intake-896#record hits and eight identifier-style cross-references became `#record`; two
      genuine content citations were made precise against claim 04 of intake-110#record. Blocking citations **10 → 5**, and intake-896#record is
      fully clear ✅ 2026-08-10
- [x] SC12-GRADE **A per-claim `overturned` was inheriting the entry's warrant.** intake-110#record was the
      only conflicted claim in 4,233 beliefs and the only entry carrying a per-claim overturn with
      no entry-level `dive-overturned`: the override flipped the DIRECTION but kept `Hinted`, so a
      dive-established refutation tied with the stage-1 support it refutes. `apply_claim_verdict()`
      now raises an overturn to at least `Verified` (never touching T, never downgrading a stronger
      entry-level verdict) and is called by **both** the emitter and the run report, which had
      already drifted apart once. One frame re-ingested; `clm_intake_110_04` is now
      `pro=Hinted/Located con=Verified/Located` ✅ 2026-08-10
- [x] SC12-DATE **Re-stamped my own frame.** That ingest ran `--as-of 2026-08-11` on 2026-08-10.
      Append-only means it could not be removed, so the same assertion was re-appended at the true
      date and the future-dated frame retracted — a false `created_at` on a provenance frame is the
      defect this program exists to catch. (The 895 other future-stamped frames are the earlier
      session's known, documented, fold-neutral set; untouched) ✅ 2026-08-10
- [x] SC12-REMAIN **Cleared the remaining three.** All three citing documents were already careful
      in prose and none rested on the overturned claim, so two were provenance references and became
      `#record`: `intake-991#record` in `autopilot-continuous-optimization.md` (which states outright
      that the weakness result "is not adopted as a selector: its original proof and empirical
      comparison are not decision-grade") and three `intake-922#record` refs in
      `context-folding-progressive.md` (one of which is the line recording AREX's +11.8pt ACU figure
      as NON-CITABLE). The third was a **real correction**: `wiki/memory-augmented.md` called Mem0 a
      "$24M cloud memory platform", and the 2026-08-07 dive overturned exactly that — the Apache-2.0
      repo self-hosts via Ollama/LiteLLM/local vector stores, so the $249/mo managed tier is one
      option, not the only path. That mattered beyond wording: "cloud-only" would have disqualified
      Mem0 under the self-hosted-only sourcing policy ✅ 2026-08-10
- [ ] SC12-ENTRY **Two precise claim-04 citations of intake-110#record remain blocking, and they
      are correct.** The entry's
      `key_claims` still records the stage-1 "+9–16 points" text while its `claim_corrections`
      refutes it — support at `Hinted`, opposition at `Verified`, which is exactly what the record
      says. Clearing them means amending the entry, a dive-owner call, not a citation fix. Until
      then `cite-check` exits 3 on a true finding
- [x] SC14-A **Planner read-side seam.** AutoPilot's
      planner has independently reinvented much of this kernel: a mandatory falsifier, an append-only
      resolution ledger (confirmed/refuted/inconclusive), and `evidence_trial_ids: []` refused on a
      prior because *"being the operator's idea is not new evidence"* (`operator_hypotheses.py`).
      The stale file-ownership marker was cleared after confirming AutoPilot was stopped. The inbound
      operator-hypothesis channel is now wired into every planner turn and records resolutions only
      after the cited trial is durable. `scripts/vidya/autopilot_settled.py` folds AutoPilot
      supersessions, grades the cited measurement tuple with Vidya's canonical ladder, fails explicit
      on ambiguous recycled trial ids, and renders sealed/provisional/review-required ground through
      `vidya_planner_bridge.py`. This is advisory for proposal selection and never gates generation
      ✅ 2026-08-10
- [ ] SC14-B **Promotion gate and shared resolution frames.** Gate only the CANDIDATE →
      BASELINE/OPTIMUM transition with `gate.evaluate`; append resolution/evidence links so AutoKernel
      sees the same negative, and use `impact_of_retracting` to reopen downstream promotions. Do not
      activate until the pre-promotion journal ordering supplies a durable current-trial attestation
- [x] SC15 **Drain the queue.** 129 corrections, 81 cited by project documents, top ones cited 5–7
  - **✅ 2026-08-12 — QUEUE FULLY DRAINED by `mainC`. 129 → 0 unadjudicated; blocked claims 571 → 0;
    the `review` bucket is empty.** 233+ `correction_reviewed` frames across 13 batches, each with
    its `claim_corrections` block written into `research/intake_index.yaml` so the next re-ingest
    grades opposition PER CLAIM. Ledger chain and all three checkpoints verified after EVERY apply;
    index entry count held at 1,097 throughout; `conflicted` unmoved at 3, so no batch introduced
    one. Commits: root `12cc6529`, `6e70bc0a`, `9548160c`, `40e783da`, `e18f7858`, `7af3cf70`,
    `4b653d3e`, `80b54438`, `d3e2674b`, `6142085c`, `fc70b9d7`, `c9897ca2` + this batch.
    - **Adjudicated per claim, by reading each correction against each claim** — which is what this
      row demanded and what a summariser cannot do. The single most useful distinction: **a heavily
      corrected ENTRY is not the same as corrected CLAIMS.** Roughly two-thirds of these corrections
      land on Stage-1 prose, a verdict justification, an applicability call, or an actionable about
      *our own* repo — not on any key claim. Propagating the entry-level label would have
      mass-downgraded claims that are fine.
    - **Three systematic hazards now on record for anyone re-running this**: (1) correction texts
      number claims against a DIFFERENT list than the ledger's `claim_index` — hit three times
      (`intake-916`, `intake-920`, `intake-929`), so adjudicate on CONTENT, never on that numbering;
      (2) several entries were written WITH their dive corrections already folded in, so their
      claims STATE the corrected position and must read as confirmed rather than corrected
      (`intake-1020` is the clean example); (3) a citation-hygiene family — `intake-1068/1069/1070/1071`
      were each ingested only because a recommendation cited them with a NEIGHBOURING entry's id
      attached. Four wrong ids in one batch is a pattern, not four accidents.
    - **`SC12-ENTRY` is now the live consumer defect.** Draining moved ~140 citations out of
      `review`, which unmasks the real grade underneath — mostly `ok`, but one bare `intake-110`
      citation in `wiki/knowledge-management.md` surfaced as `conflicted`, inheriting a pre-existing
      overturned claim 4. Surfaced, not caused; it needs narrowing to `#NN` or `#record`.
      times. Not startable by a summariser: each verdict needs the dive text read against the claim,
      which is the exact failure intake-896#record memorialises. Start with the cited head — `cli.py
      corrections` ranks it — and record `effect` per claim, never per entry
  - **TRIAGED 2026-08-11 (`mainC`) — no verdicts written. The queue is far more tractable than "129
    unadjudicated" suggests, and the reason it looked intractable is that it was never split.**
    Classifying each correction by the adjudication its OWN text demands:

    | adjudication needed | n | share |
    |---|---|---|
    | scope / framing | 37 | 29% |
    | numeric / metric | 31 | 24% |
    | provenance / citation | 16 | 12% |
    | superseded or duplicate | 6 | 5% |
    | needs a PRIMARY-SOURCE dive | **1** | 1% |
    | unclassified — needs a read to say | 38 | 29% |

    **Only ONE correction demands a primary-source dive** (`intake-547`, whose text says its claims
    "remain unverified against arXiv:2603.02615" — filed during the intake-901 Stage-3 audit and
    explicitly *not* a dive on its own entry). It is also the single most-cited entry in the queue
    (7 citations), so the highest-leverage item is also the only one that needs real research: it
    should be packaged for the operator, not desk-adjudicated. The other ~99 desk-resolvable ones do
    not need to wait behind it.
    - **Where to start:** the cited head. 81 of 129 are cited by a project document; entries at
      `citations >= 3` block **65 claims** between them. Drain those first — an uncited correction
      blocks nothing a reader can currently rely on.
    - **Caveat on the table, stated rather than hidden:** the split is a regex over each
      `correction_text`, so it is a routing hint, not a verdict. The 29% "unclassified" bucket is
      the honest residue, and any row may reclassify on a real read. It orders the work; it does not
      do it.
    - **Not started deliberately.** `disposition` records a *human* verdict via `--actor`, and SC15
      is explicit that this is not summariser-safe work. Writing 129 verdicts from a triage pass
      would inject exactly the unwarranted warrant the substrate exists to prevent. The ordering
      above is the deliverable; the verdicts are not mine to manufacture.
- [ ] SC16 **Is `uncertain` the right default for a per-claim verdict?** `apply_claim_verdict` keeps
      the ENTRY-level verdict when a dive records `effect: uncertain`, so on a `dive-overturned`
      entry an "a reader could not tell" verdict currently opposes the claim at `Verified` — the
      dive's inability to decide is recorded as a dive-strength refutation. `clm_intake_922_01` is
      the live instance. The conservative reading may still be right (an entry-level overturn is
      evidence about the entry), but it was inherited, never chosen. Decide it deliberately and
      write the reason into the docstring either way
- [x] SC17 **`fold` does not exclude frames dated after `as_of`.** ✅ 2026-08-12 (`auditor`) — design chosen per the row's own recommendation + spec §fold-purity: `fold` stays pure (created_at remains publication metadata it never reads); the guard is an **append-time refusal** in `ledger.py` (`FrameStampError`, `MAX_FUTURE_SKEW_SECONDS=300`), tolerating absent/malformed stamps (frame-construction's contract; maintenance frames carry none) and past stamps (history untouched — the 895 incident frames are correction-queue territory, out of SC17 scope). 6 new tests both directions incl. yes-paths (`tests/vidya/test_ledger_future_stamp.py`); full vidya suite 371 green. A frame stamped in the future
      takes effect immediately at any earlier `as_of`, which is how 895 future-stamped frames from
      the 2026-08-10 date incident still fold in, and how a frame this session mis-stamped
      `2026-08-11` applied on 2026-08-10 before being re-stamped. Two defensible designs — ignore
      `created_at` entirely (it is publication metadata, and `as_of` ranges over the evidence
      frontier) or refuse future frames at append time. What is NOT defensible is the current
      accident of neither. Pick one; an append-time refusal is the cheaper guard
- [ ] SC18 **Wire the `test-backend-ops` property layer as a measurement source — write side FIRST**
      (filed 2026-08-10 per CLAUDE.md's belief-kernel rule, at the layer's *design* time rather than
      after it ships). The property layer specified as `RVP-C2-2` in
      [`rocm-verify-profile-backend.md`](rocm-verify-profile-backend.md) **produces measurements**:
      a per-op, per-backend, per-shape property residual. Two things make it a good source and both
      are cheap only right now — `RVP-C2-1` adds a deterministic `suite_seed`, which is what makes a
      residual re-derivable rather than an anecdote; and the layer is reference-free, so its residual
      is a claim about the candidate alone rather than about a candidate/reference pair. Add the
      adapter row (already recorded in [`scripts/vidya/adapters/README.md`](../../scripts/vidya/adapters/README.md))
      and the `ClaimTuple` projection. **Do not write a new grading rule** — the adapter projects into
      a `ClaimTuple` and `claim_tuple.grade()` decides; the `measurement` ladder already exists and the
      registry refuses a second. This is the case `benchmarks/results` is the standing proof of: 4,562
      files with no write-side hook can never gate a decision, and no read-side pass can repair that.
      **2026-08-11 static implementation:** research commit `70766412` parses `AK_PROP_V1`, re-derives
      its verdict, refuses suite-seed mismatches and preserves each residual as a structured
      `evaluation_event` gate measurement. Root `autokernel_property.py` projects only those written
      rows into the single measurement ladder and explicitly yields nothing for older events. This
      row remains open until the experimental `test-backend-ops` producer is committed and its first
      real event proves the write path.
- [x] SC19 **Wire the new AutoKernel ROCm auxiliary receipts prospectively — write side FIRST.**
      ✅ 2026-08-11 — the rocprof-v1 attribution, HipKittens LDS solver, and Omniperf fallback
      producers now emit explicit `belief_measurements` only on successful future runs. Root
      `autokernel_aux_receipt.py` projects those rows into the one measurement ladder, binds the
      native schema as protocol id, and returns zero rows for receipts predating the hook. Current
      2026-08-11 receipts are deliberately not retrofitted. The adapter's GEAK round-trip schema seam
      is ready, but no round-trip producer vector is claimed by this closure.
- [x] SC20 **Add the write-side `belief_measurements` vector to the GEAK/Arena round-trip producer
      before the matched controller A/B.** Emit correctness pass rate and timing-harness validity as
      separate directional rows with scored-repetition bases. Do not infer them later from the
      completed 2026-08-11 receipt; that record predates the hook. ✅ 2026-08-11 — research
      `controller/arena_roundtrip.py` is the prospective writer; its two rows pass the root
      `autokernel_aux_receipt.py` projection contract end to end. INF-03 r3's terminal 2h and 8h
      Claude/Codex checkpoints are the first post-hook live evidence: belief receipts
      `05cb70a0d6f670796f93bdc06c4a681578d044f7929839688a4b2c5b7a491370` and
      `4c01642993c1120eac4885714e3e2780845e618913c11676c6decef290fded61` each carry the two
      producer-authored rows. Older receipts remain untouched.
- [x] SC21 **Classify GEAK/Arena preflight findings deliberately.** Source pin/license, physical
      gfx90a identity, registry shape and spoof refusal are verified findings, not ordinal
      measurements and not literature. Either declare one shared `verification` source-class ladder
      with a documented ceiling or retain preflight solely as dependency evidence; never invent a
      metric direction to force it through `ClaimTuple`. ✅ 2026-08-11 — selected the
      least-commitment option: the writer hash-binds preflight under `dependencies.preflight` with
      `classification=dependency_evidence_only` and mechanically emits no belief measurement for it.
- [x] SC22 **Wire future AutoKernel MMQ WGM wall-time/counter receipts on the write side before any
      successor launch-order experiment.** Emit separate directional rows for end-to-end wall time,
      all-MMQ TCC hit rate, and read-request volume with the exact WGM arm, scored-repetition basis,
      device claim, producer/source identity, and admitted receipt digest. Project those written rows
      through the existing measurement ladder; do not add a grading rule and do not back-fill the
      admitted 2026-08-11 r2 negative, which predates this hook. ✅ 2026-08-11 — research producer
      `epyc.autokernel.mmq_wgm_profile.v1` writes three per-arm measurements plus raw observations,
      exact evidence/source/producer identity, released MI210 claim, and stable receipt digest;
      root projects only those rows through the existing shared ladder. Historical r2 schemas remain
      unsupported. Research `36717bd1` (main `acb7e840`); root reconciliation `0126f598`
      (main `ba0b0450`).
- [x] SC23 **Wire future AutoKernel IQ2 fancy-SIMD screening and model-confirmation receipts on the
      write side before the OP-12 follow-up run.** Emit separate lower-is-better op-time rows for the
      exact IQ2_XXS `n=1` and `n=512` cells, plus explicit higher-is-better model TG/PP rows when
      available, with scored-block bases, candidate/source/binary identities, device claim, and
      admitted receipt digest. Project only producer-written rows through the existing measurement
      ladder; do not add a grading rule and do not back-fill the admitted 2026-08-11 r5 screening
      receipt, which predates this hook.
  - [x] **SC23a — Wire the micro-A/B screening rows.** ✅ 2026-08-11 — the prospective research
    producer emits exact lower-is-better `n=1` and `n=512` op-time rows with scored-block and
    candidate/source/binary identity; the root adapter admits only the new native schema. Historical
    r5 remains untouched. Research `f19e5eaf` (main `a207c56f`); root main `9cd32a64`.
  - [x] **SC23b — Add explicit model TG/PP rows to the first model-confirmation producer.** ✅
    2026-08-11 — the prospective research producer emits four higher-is-better rows covering
    TG/PP × anchor/candidate only after T1+T2 have passed, the raw vectors match exactly, and the
    candidate/build/model/anchor identities plus released CPU claim bind. The root adapter
    independently reconstructs final/source/row hashes and every candidate, model, anchor, claim,
    execution, sample, and denominator binding. Fixture interoperability accepts exactly four rows;
    this completes the writer/reader seam but supplies no model-confirmation evidence before OP-12.
    Research `0efd7201` (main `6771cfea`); root `be7426b2` (main `328b2ba4`).
- [x] SC24 **Wire future INF-37 Q4_K direct-PMC receipts on the write side.** ✅ 2026-08-11 — the
      prospective producer emits separate Q4_K-minus-Q4_0 and Q4_K-minus-Q8_0 VALU/wave,
      INT32/wave, and diagnostic dispatch-duration rows, all bound to exact arm/control/shape/block,
      counter, source, binary, producer, profiler, device-claim, evidence, row, and receipt digests.
      The root adapter re-derives every binding and refuses promotion or fused-unpack wall-share
      authority. Historical r7 remains unchanged and projects zero rows. Research `5c333a4c`
      (main `d88ce6ee`); root `c37850e1` (main `9bfa1eae`).
- [x] SC25 **Finalize structured ROCm profile receipts without rewriting their evidence.** ✅
      2026-08-11 — research `07b303cc` adds a separate producer for immutable G15, C4, and
      standalone-WGM receipts. It emits performance and target-selection rows separately, reduces C4
      only from the formal production-optimization trace, and marks WGM proxy rows as design priors
      that do not transfer to real MMQ. The root auxiliary adapter admits the new
      `epyc.autokernel.profile_beliefs.v1` schema through the existing measurement ladder; 16 rows
      from four current artifacts project end to end. This is a new hash-bound derived receipt, not a
      mutation or prose reconstruction of the source evidence.
- [x] SC26 **Wire the P2-5j placement receipt prospectively before its first real campaign.** ✅
      2026-08-11 — research `f17116de` emits 16 self-hashed rows covering decode throughput,
      p50/p95 latency, and paired ratio for all four arms with ten scored blocks and exact claim
      identities. Root's auxiliary adapter re-derives every value, row digest, arm/topology field,
      and receipt digest while preserving the observation-only no-selection/no-speedup/no-carve/
      no-activation boundary. No grading rule was added and no historical result was back-filled.
- [x] SC27 **Wire AutoKernel live-control and governed replay receipts on the write side before the
      next run.** ✅ 2026-08-12 — research `730adb1d` adds prospective producer-written belief rows
      to live controls and the async-prefetch replay; root `2a4e170a` adds the
      `autokernel_governed_receipt.py` projection and source-register entry. Protocol, direction,
      scored-block basis, source/binary/model/claim/producer identities, native verdict, and immutable
      evidence digests are independently re-derived before the shared measurement ladder grades the
      tuple. Focused producer tests pass 23/23 and adapter tests 24/24. The 2026-08-12 smoke, controls,
      and GPU replay predate the hook and remain deliberately unprojected; only future receipts may
      enter this source.
- [x] SC28 **Wire RVP-T0-1 saturation and AK-BH-1 vendor-baseline diagnostics before either runs
      again.** ✅ 2026-08-12 — research `1434ed1a` adds a shared prospective writer used by both
      live runners. RVP-T0-1 emits separate sustained-throughput, nominal-clock-hold, peak-power and
      cap-headroom rows; AK-BH-1 emits one provider ratio per exact shape. Root
      `autokernel_rocm_diagnostic.py` independently re-derives the sample statistics, provider
      ratios, scored bases, source/binary/device-claim/producer identities, row hashes and logical
      receipt hash, then delegates grading to the existing measurement ladder. Every row is
      diagnostic-only and grants no campaign/promotion authority. The 2026-08-12 pre-hook receipts
      remain deliberately unprojected; successor runs are the empirical follow-up.
  - [x] **Capture and independently project the first post-hook successor receipts.** ✅ 2026-08-12 —
    research `75ff5767` and root `1edf47fd` align both sides with canonical `ClaimReceipt` release
    semantics (`released_at` on the last held/draining state). RVP-T0-1 post-hook r2 emitted **4**
    producer-authored diagnostic measurements and AK-BH-1 post-hook r1 emitted **9** exact-shape
    measurements; the root adapter re-derived **4 + 9 ClaimTuples**. Focused producer/adapter tests
    pass **8/8** and **12/12**, respectively. No row grants ranking, campaign, release, or production
    authority.
- [x] SC29 **Wire AK-LE planner prefilter/reduction receipts before the corrected panel runs.** ✅
      2026-08-12 — research `16ad9c2c` prospectively emits four self-hashed search-persistence rows
      per complete cell only after re-running the source-pinned reducer; corrected r3 produced **32**
      rows from **8/8** cells. Root `47400351` registered the source and root `803a90b5`
      implemented the fail-closed canonical reader. It projects
      producer-authored `ClaimTuple` rows for the predeclared per-cell search-persistence measures
      (`novel_nonduplicate_count`, `prefilter_survival_count`, explicit already-optimized
      termination, and elapsed wall time), with model/quant/effort/target-arm identity, direction,
      scored-cell basis, exact manifest/panel/prefilter/evidence digests, and run-level locator. The
      under-specified 2026-08-12 r1 panel remains a durable refusal and projects zero rows; the r2
      malformed-Claude-wrapper attempt failed before one complete cell and also projects zero rows.
  - [x] **Implement the root read-side adapter for the live AK-LE planner-reduction schema.** ✅
    2026-08-12 — `autokernel_planner_reduction.py` independently replays the pinned structural
    prefilter and planner receipt, re-derives every producer row, then delegates grading to the
    shared measurement ladder. The real r3 artifact projects **32/32** unique rows; r1/r2 project
    zero without reconstructing historical tuples. Focused tests pass **8/8** and the complete
    Vidya suite passes **512**, with one pre-existing skip.
- [x] SC30 **Classify and wire the AutoKernel real host-process fault rehearsal before it runs
      again.** ✅ 2026-08-12 — research `5c8714a1` writes three self-hashed dependency-evidence rows
      and root `7077f1cc` independently re-derives them while refusing ClaimTuple projection. Preserve
      `epyc.autokernel.host_process_fault_rehearsal.v1` as dependency evidence:
      project each of the three recovery legs with exact source/producer/process identities and the
      immutable receipt digest, but do not coerce PASS into a performance measurement, corroborating
      witness, release claim, or campaign authority. Key support on the rehearsal run, not each leg.
- [x] SC31 **Wire AK-LE-3 scaffold-panel measurements on the write side before any successor panel.**
      ✅ 2026-08-12 — research `loop_scaffold_runner.py` now emits four exact model/scaffold speedups
      plus two same-model split/direct effects only after a complete measured panel, with scored-case,
      source/evaluator/candidate and released-claim evidence and diagnostic-only authority. Root
      `autokernel_scaffold_panel.py` independently re-derives panel, cell, evaluation, claim and row
      hashes. Terminal r1 remains pre-hook and projects zero rows; no history was reconstructed.

## Dependency notes

V2 blocks P1 (the pilot spec must exist before the engine). P0 can run in parallel with V2 (it is
operator + curation work). P2 depends on P1 (frames must exist). P3–P5 sequence after P1–P2.
R1/R2 are paper-track and independent; R3 deliberately severed; R4/R5 need pilot data.

## Decision queue — ALL SETTLED 2026-08-09

Retained as the ratification record. Nothing here blocks P1.

- [x] **1. Gold corpus** — ratified as drafted: 19 claims, four documented corrections + one E8
      measurement slice ✅ 2026-08-09
- [x] **2. `Corroborated`** — dropped from the carrier; independence is a policy predicate over the
      leaf-disjoint statistic ✅ 2026-08-09
- [x] **2b. Status-to-grade table** — ratified **with the tightening**: verifiers, tests, builds and
      actuation outcomes cap at `Q3`; `Q4 Witnessed` requires a protocol-admissible measurement, so
      `Q4` now means exactly "would be admissible as a decision-gating claim" ✅ 2026-08-09
- [x] **3. Carrier shape** — product lattice `Q × T` (warrant quality × traceability) ✅ 2026-08-09
- [x] **4. Sidecars + banners** — `.vidya/projections/` bound to article content hash; **no visible
      banner in shadow** (advisory display is measured not to change behaviour) ✅ 2026-08-09
- [x] **5. Canonical ledger** — append-only **JSONL is canonical** (house pattern: fsync-per-append,
      torn-tail handling), SQLite is a rebuildable derived index ✅ 2026-08-09
- [x] **6. Frame-type coverage** — `Trigger` **ADOPTED** as `pubinfo.triggered_by`, carrying no
      grade / authority / freshness; `Use`/`Generate` declared already covered by
      `derived_from`/`produced_by`. All nine survey relations now accounted for ✅ 2026-08-09
- [x] **7. Xu et al. 2018** — decline-with-citation; cited as R2 application precedent only ✅ 2026-08-09

## Cross-cutting concerns

- Any new freshness state must name its mapping onto `dashboard/freshness.py` classes.
- Any measurement claim consumed by the pilot cites protocol + era per MEASUREMENT.md; the pilot
  never re-grades measurement evidence.
- The P2 adapter changes the research-intake skill's write path — coordinate with any parallel
  intake session; never edit the skill mid-run.
- Judgment frames (any LLM verdict entering the ledger) must satisfy the V2.7 keying rules from
  day one — retrofitting replay keys is not possible.
- **A field used to discriminate KIND must BE an explicit kind, never a present/absent test.**
  Raised 2026-08-11 by `mainA` from four absence-inferred fields found in one night — and the
  generalisable point is not carelessness: **two of the four were introduced by the person fixing
  that exact class, hours apart.** Presence/absence is the cheapest discriminator available at
  design time, and its whole cost lands on whoever reads the store months later, who cannot tell
  *"this kind has no value"* from *"nobody wrote one"* from *"the writer predates the field"*.
  Same asymmetry as the write-side rule above: cheap and permanent to state now, impossible to
  retrofit — a reader cannot recover a distinction the writer never recorded.
  Three independent instances the same day show it is not confined to manifests: `mainB` read merge
  stage `:3` after a `git add` (which collapses stages 1/2/3, so `:3` returned EMPTY and empty made
  every comparison pass); `mainD`'s `backfill-receipts --check` reported "index is current" while
  covering only bus-known gates; the `auditor`'s receipt index asserted `ratified` over files that
  were untracked. **Each was true about a smaller set than it appeared to speak for** — the read-side
  face of the same defect.

## Reporting

Standard checkbox discipline (`- [x] … ✅ YYYY-MM-DD`; mid-flight discoveries get their own task
lines). Maintain the master-index and research-evaluation-index rows; on completion, extract
findings to docs, move to `completed/`, delete the master-index row.
