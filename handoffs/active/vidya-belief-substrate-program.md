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

Outstanding tasks live in **Source coverage** (`SC6-LIVE`, `SC10`, `SC11`, `SC7`, `SC6-HAZARD`) and
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
- [ ] SC10 **AutoKernel `evaluation_event` — ready, unwritten.** Its schema already enforces the
      claim rule as a REQUIRED block (stricter than the autopilot hook: `metric_direction`,
      `reps` ≥ 1, `anchor.source_commit`, hex-sha256 `run_id`, INVALID runs journaled not
      discarded). No adapter is needed until the loop emits records — **zero files on disk contain
      `claim_grammar` today**. Wire the read side when the first evaluation_event lands
- [ ] SC11 Survey the remaining candidate sources named in the register — llama-bench sweeps and the
      speech-kernel (whisper/qwentts) runs. Both need a write-side hook before a reader is worth
      anything; price each with the ~50-record sample before building
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
- [ ] SC15 **Drain the queue.** 129 corrections, 81 cited by project documents, top ones cited 5–7
      times. Not startable by a summariser: each verdict needs the dive text read against the claim,
      which is the exact failure intake-896#record memorialises. Start with the cited head — `cli.py
      corrections` ranks it — and record `effect` per claim, never per entry
- [ ] SC16 **Is `uncertain` the right default for a per-claim verdict?** `apply_claim_verdict` keeps
      the ENTRY-level verdict when a dive records `effect: uncertain`, so on a `dive-overturned`
      entry an "a reader could not tell" verdict currently opposes the claim at `Verified` — the
      dive's inability to decide is recorded as a dive-strength refutation. `clm_intake_922_01` is
      the live instance. The conservative reading may still be right (an entry-level overturn is
      evidence about the entry), but it was inherited, never chosen. Decide it deliberately and
      write the reason into the docstring either way
- [ ] SC17 **`fold` does not exclude frames dated after `as_of`.** A frame stamped in the future
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
      `autokernel_aux_receipt.py` projection contract end to end. Older receipts remain untouched.
- [x] SC21 **Classify GEAK/Arena preflight findings deliberately.** Source pin/license, physical
      gfx90a identity, registry shape and spoof refusal are verified findings, not ordinal
      measurements and not literature. Either declare one shared `verification` source-class ladder
      with a documented ceiling or retain preflight solely as dependency evidence; never invent a
      metric direction to force it through `ClaimTuple`. ✅ 2026-08-11 — selected the
      least-commitment option: the writer hash-binds preflight under `dependencies.preflight` with
      `classification=dependency_evidence_only` and mechanically emits no belief measurement for it.
- [ ] SC22 **Wire future AutoKernel MMQ WGM wall-time/counter receipts on the write side before any
      successor launch-order experiment.** Emit separate directional rows for end-to-end wall time,
      all-MMQ TCC hit rate, and read-request volume with the exact WGM arm, scored-repetition basis,
      device claim, producer/source identity, and admitted receipt digest. Project those written rows
      through the existing measurement ladder; do not add a grading rule and do not back-fill the
      admitted 2026-08-11 r2 negative, which predates this hook.
- [ ] SC23 **Wire future AutoKernel IQ2 fancy-SIMD screening and model-confirmation receipts on the
      write side before the OP-12 follow-up run.** Emit separate lower-is-better op-time rows for the
      exact IQ2_XXS `n=1` and `n=512` cells, plus explicit higher-is-better model TG/PP rows when
      available, with scored-block bases, candidate/source/binary identities, device claim, and
      admitted receipt digest. Project only producer-written rows through the existing measurement
      ladder; do not add a grading rule and do not back-fill the admitted 2026-08-11 r5 screening
      receipt, which predates this hook.

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

## Reporting

Standard checkbox discipline (`- [x] … ✅ YYYY-MM-DD`; mid-flight discoveries get their own task
lines). Maintain the master-index and research-evaluation-index rows; on completion, extract
findings to docs, move to `completed/`, delete the master-index row.
