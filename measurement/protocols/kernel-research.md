<!-- RATIFIED 20260803T083005Z. Annex K of MEASUREMENT.md (same trust boundary, same
     amendment rules). Kernel research and release protocol family. Remit and admission
     test below are normative. -->

# Annex K — Kernel research & release protocols

**Remit.** Annex K holds protocols that govern **kernel research and kernel release** across source
trees and backends: instruments whose subject is a *candidate kernel* rather than a measurement
family, and instruments that are cross-backend by construction.

**Admission to Annex K requires ALL of:**

1. the protocol's subject is a kernel candidate, a kernel lineage, or a kernel release decision;
2. the protocol is cross-backend — it governs at least two of `llama_cpu`, `llama_gpu`,
   `whisper_stt`, `qwentts_tts`, `serving_runtime` — **and** it is a search or release instrument
   that produces records which are not claims; and
3. no existing annex (B, Q, G) already **states** the rule this protocol **establishes**.

**Narrowing carve-out (test 3).** A protocol that *narrows* a rule stated in another annex, without
restating or replacing it, is admissible to K **only if the owning annex receives an appended
cross-reference in the same apply** recording that its rule has been narrowed and by what (see §4d).
A protocol that *restates or replaces* another annex's rule is not an Annex K protocol at all; it is
an amendment to the owning annex, and where a rule already lives, the amendment goes.

**Every protocol filed in Annex K MUST state, in its own grammar line, the class of record it
emits** — a claim, or a verdict that is not a claim.

**Comparison scope.** Records emitted under an Annex K protocol are comparable **only within one
backend and one instrument version**. Cross-backend roll-ups are labelled analysis and never gate
(`MEASUREMENT.md:83-84`; owning handoff §1.6). A single Annex K protocol id spanning several
backends does NOT make a cross-backend comparison a within-protocol comparison.

**Prospective.** Creating Annex K neither retro-certifies nor upgrades any artifact. No measurement
taken before the apply timestamp becomes a claim, or a conforming record of any Annex K protocol, by
virtue of this annex existing. Protocols already filed in B, Q or G stay there; Annex K MUST NOT be
used to relocate an existing protocol.

---

## P-AK-SEARCH-1 — Kernel-candidate search authority (RATIFIED 2026-08-03)

**NARROWED 2026-08-03 by `P-AK-SEARCH-1-A1`** (this annex, below): a banked candidate additionally requires a mechanism explanation backed by bytes, FLOPs, counters or a clean A/B; and a backend-capability claim additionally requires both correctness and performance evidence. This protocol as stated below is purely statistical and does not carry either requirement on its own.

**Purpose.** This protocol permits an automated kernel-research controller to **rank, retain,
abandon, branch, and compose candidates inside experimental worktrees**, on the basis of measurements
taken on those experimental candidates. It is the narrow lift of the consumption prohibition at
`measurement/protocols/gpu-cross-device.md:16-21` — *"MUST NOT be consumed by AutoPilot or any
automated optimizer"* — and it lifts nothing else. It creates no new class of claim, no new decision
authority, and no exception to any other rule in this constitution.

**Scope.** Tiers T0, T1 and T2 of the AutoKernel loop, on every declared backend adapter, for
measurements taken inside a campaign's own experimental worktrees. It does **NOT** apply to T3 or any
release gate, which are governed by the release protocols; it does **NOT** apply to any measurement
presented outside the loop; and it does **NOT** apply to any backend adapter not named in the
campaign manifest under which the measurement was taken. A number produced under this protocol that
is subsequently presented in a handoff, an index, an operator report, or any other durable narrative
surface MUST either be re-measured under its owning protocol in Annex B, Q or G, or be carried with
its complete search-record grammar including the words **search record, not a claim**. **Two
surfaces are closed to it entirely:** a registry, lineup or era row, and a dashboard or report
headline. For those two the only sanctioned route is re-measurement under the owning protocol —
a labelled headline is still a headline (`MEASUREMENT.md:85-95`;
`feedback_headline_numbers_must_be_production_optimal`), and denial 2 below forbids the registry
write outright.

**Metric.** This protocol declares no metric of its own. Each cell carries the metric and direction
of the phase it measures — decode or prefill tokens/s (higher-better) for instrument-level cells per
`MEASUREMENT.md:34-38`, `task_rate` (higher-better) for whole-system or scheduler cells per
`MEASUREMENT.md:28-33`. Substituting one for the other is forbidden by `MEASUREMENT.md:25-26` and
that prohibition is unaffected here. Records produced under this protocol MUST NOT be pooled,
averaged, differenced, or folded into a composite with records produced under any other protocol
(`MEASUREMENT.md:83-84`).

### What this protocol authorizes

A conforming controller MAY, on the basis of search records produced under this protocol:

1. rank candidates against a named immutable anchor;
2. retain, abandon, or branch a candidate;
3. compose compatible candidates into a champion lineage and re-measure the composition as a whole;
4. select the next experiment; and
5. compute and report an **advisory readiness signal** to the operator, labelled as a search
   product, **computed by a deterministic reducer over journaled records**. A readiness figure that
   originates in controller narrative rather than in records is `INVALID`: the controller may
   request a readiness computation, never declare a readiness value (owning handoff §4 invariant 14).

All five are confined to state inside the campaign's own experimental worktrees, journal, and derived
views.

### What this protocol does NOT authorize

The authority above is the whole of it. In particular:

1. **No gating outside the worktree.** A search record MUST NOT gate any keep / revert / deploy /
   promote / buy / close decision (`MEASUREMENT.md:9-11`). Ranking a candidate above another *inside*
   a campaign is not one of those decisions; adopting, shipping, or recommending either is.
2. **No production write of any kind**, including building in, committing to, or modifying any
   production tree or production-named branch, repointing any stable kernel path, or editing any
   registry, lineup, or era artifact.
3. **No retro-certification by any route.** A search record can never become a claim. This narrows
   no core-file verb and creates no exception to one: `MEASUREMENT.md:177-179` retro-certifies an
   artifact *"provably produced by a now-named protocol"*, and a search record is by construction
   not such an artifact — it was produced under this protocol, which emits verdicts and not claims,
   so the retro-certify precondition is unsatisfiable for it on the core file's own terms. It is
   equally outside the strict route at `gpu-cross-device.md:44-48`, which requires a
   production-named kernel. No later amendment to this annex may be applied backwards to records
   produced before it. A decision-grade number is produced afresh under its owning protocol or it
   does not exist.
4. **No consumption by any other optimizer, and no consumption by a later campaign.** Consumption is
   confined to the AutoKernel controller that produced the record, within the campaign that produced
   it. AutoPilot, the routing planner, the quality scorer, the placement dispatcher, the Pareto
   archive, the strategy store, and any future automated optimizer MUST NOT read these records as
   evidence. A later AutoKernel campaign MAY use a prior record for **hypothesis formation only** —
   never to rank, bank, compose, or contribute to readiness — because a later campaign necessarily
   re-derives its own calibration and a reused record would otherwise be scored against a floor and
   a threshold it was never measured under. A record whose anchor no longer resolves is superseded,
   not reinterpreted.
5. **No human-only write.** Nothing here authorizes any of the writes enumerated at
   `MEASUREMENT.md:141-142` — *"era-registry rows, this constitution and its annexes, AutoPilot
   baseline-state applies, production freezes/cutovers, host reboots"*. A search record MUST NOT be
   cited as a reason one of them may be performed automatically, and a readiness signal is not a
   freeze trigger.
6. **No self-amendment.** The controller MUST NOT modify this protocol, the evaluator bundle, the
   control definitions, the campaign objective, the calibrated thresholds, or any scoring contract.
   These are read-only for autonomous optimization processes (`MEASUREMENT.md:119-120`). A controller
   that discovers a coverage gap in its evaluator RECORDS the gap, blocks release eligibility for the
   affected lineage, continues unrelated research, and MAY draft an amendment for human review. It
   does not patch the instrument, and it does not route around it.
7. **No release activity.** No T3 execution, no release verdict, no freeze eligibility, no waiver
   judgement, no sealing of a release candidate, no assembly of a production transaction.
8. **No host or resource authority.** This protocol does not authorize a name-pattern process check,
   a signal to any process the loop did not launch, a host reboot, a privileged cache action outside
   the sanctioned path, or any inference run outside a held claim.
9. **No new instrument by composition.** A conforming controller MUST NOT synthesise a
   decision-grade quantity by combining search records with each other or with claims, and MUST NOT
   report a cross-backend or cross-protocol roll-up as anything other than a labelled analysis view.

### Preconditions (all enforced or attested per run)

1. **Resource claim held for the whole window.** A CPU region claim covering the exact footprint
   measured, and for GPU work an **exclusive device claim**. Both are ACQUIRED, never inferred:
   observing that a device or region *looks free* is TOCTOU, not exclusion
   (`gpu-cross-device.md:142-143`). The claim receipt identifier is recorded, and the claim MUST be
   re-verified as still held, by the same holder, at window close as well as window open.
2. **No concurrent inference**, established by the **sanctioned preflight substitute** — the
   claim-holder witness plus owned-cgroup enumeration ratified as an equivalent P-BENCH-1 / P-GPU-1
   precondition by the preflight-substitute item presented in the same attestation as this protocol.
   This protocol does not define that substitute, does not restate it, and authorizes no alternative
   to it. If that item is not in force, this precondition has no sanctioned means of satisfaction and
   no run may start.
3. **Host-health tier satisfied** per `bench-cpu.md:17-19`. Uptime ≥ 1 week requires a reboot before
   any further search measurement; reboots are operator authority, so the controller persists,
   requests, and resumes rather than proceeding.
4. **An EXPLICIT IMMUTABLE ANCHOR.** Every performance, coherence, correctness, capacity, or
   determinism comparison names its anchor by source commit, binary SHA-256, and linkage SHA-256, and
   the anchor is re-verified byte-for-byte at window open and window close. A rebuilt anchor is a
   different anchor. **A run without an explicit anchor is `INVALID` — never "correct", never
   "coherent", never "byte-identical".** Absence of a comparison is not evidence of equivalence: a
   coherence or identity label produced without a named anchor comparison is not a verdict, and any
   record carrying one is `INVALID` and MUST NOT be admitted to a correct-only frontier, a champion
   lineage, or a readiness computation.
5. **Evaluator identity.** The immutable evaluator bundle's SHA-256, as recorded in the campaign
   manifest and pinned under the measurement trust-boundary path set, is resolved at run time,
   recorded in every record the run emits, and re-verified at window close. The run additionally
   records a **runtime source-label attestation** — the resolved path and content hash of every module
   actually loaded — so that "the evaluator that ran" is a checkable fact rather than an inference
   from an import statement. Any drift between the pinned hash, the resolved bundle, and the runtime
   attestation voids every record in the window.
6. **Codified recipe.** Every measurement command line emitted **inside this protocol's scope** is
   emitted by a recipe constructor; the constructor's identifier and content hash are recorded with
   the record. Hand-typed argv voids the run (`bench-cpu.md:8-10`, `MEASUREMENT_POLICY.md:37`). This
   precondition reaches only runs under this protocol; a measurement presented outside the loop is
   governed by its own annex, and this protocol states no rule about it.
7. **Storage headroom** at or above `storage_floor_bytes_free`, the campaign storage floor as
   defined by the **evidence-retention clause of `MEASUREMENT.md` §5**, checked at window open and
   re-checked at window close. This protocol defines no floor of its own; there is exactly one
   definition and it lives in the clause whose subject is storage. Reclamation outside the
   enumerated expirable classes of that clause is operator authority; when the already-eligible
   expiry backlog does not clear the floor, the campaign stops.
8. **Declared campaign controls.** The campaign manifest MUST declare, before the first candidate is
   measured, every quantity the calibration block below consumes. Each MUST be finite and strictly
   positive; a campaign that omits one, or declares it as zero or unbounded, cannot derive its error
   budgets and MUST NOT start:
   - `calibration_block_count` — the number of A/A blocks the calibration block runs over, per
     (backend, phase, cell class);
   - `contribution_floor` — the smallest end-to-end effect the campaign will spend evaluation budget
     on, stated in the phase's own metric and direction;
   - `max_candidates` — the maximum number of candidates the campaign may rank;
   - `confirmation_admission_count` — the maximum number of candidates admitted to the confirmation
     stratum;
   - `max_blocks_per_candidate` — the stopping rule's ceiling (see the stopping-rule clause below);
   - `retention_hold_boundaries`, `storage_safety_factor`, `host_reserve_bytes` and the campaign's
     `namespace_roots` — declared per the evidence-retention clause of `MEASUREMENT.md` §5, which
     owns their definitions.

### Campaign calibration block — every threshold is derived, none is supplied

Before any candidate is ranked in a campaign, the evaluator MUST execute a **calibration block** and
record its outputs, together with the raw samples they were derived from, in the campaign manifest.
The calibration block runs on the campaign's own anchor, host state, backend, phase, and cell class,
under the identical recipe, claim, interleaving and reduction discipline that candidate rounds will
use. Values calibrated under a different host state, backend, phase, or cell class MUST NOT be
reused. Every output is recomputed at each campaign boundary and whenever anchor identity changes.

**Solve order (normative — the outputs are mutually referential and the order is what makes them
well-defined).** The calibration block is evaluated in exactly this order, and a conforming
implementation MUST record that it did:

1. **Inputs are fixed first.** The stopping rule's *shape* and its `max_blocks_per_candidate`
   ceiling are campaign inputs declared under precondition 8, not calibration outputs. They are held
   constant for the whole solve.
2. **`α_sel` is derived from `max_candidates`**, and `α_conf` from `α_sel` and
   `confirmation_admission_count`, per output 3 below. No empirical step yet.
3. **`φ` is estimated** from the A/A control over `calibration_block_count` blocks, per output 1.
4. **`B_min` is solved** by increasing the block count from the constitutional floor upward, with
   the stopping rule and `α_sel` held fixed, until conditions (a) and (b) of output 2 both hold.
   The solution is the smallest such block count.
5. **`α_sel` is validated empirically once, at the solved `B_min`**, per output 3. If validation
   fails, `α_sel` is tightened and the solve restarts at step 2; both the failed and the accepted
   calibration are retained in the manifest.
6. **The anchor-gate band is computed** at the solved `B_min`, per output 4.

If no `B_min` less than or equal to the declared `max_blocks_per_candidate` satisfies both
conditions, the **calibration FAILS and the campaign does not start**. There is no partial
calibration and no fallback ceiling.

Per (backend, phase, cell class), the calibration block derives:

1. **Campaign noise floor `φ`** — the 95th percentile of the `|effect|` distribution observed in the
   A/A control, over at least the campaign's declared `calibration_block_count`, where each A/A effect is
   computed by the same reducer, at the same block size, as a candidate effect. `φ` is a property of
   the instrument under this host state, not of any candidate. An estimate whose magnitude does not
   exceed `φ` MUST NOT be ranked, banked, or composed, whatever its evidence value. The neutral
   control's `|effect|` distribution is compared against `φ` as a consistency check; a neutral control
   materially exceeding the A/A floor FAILS the calibration rather than raising the floor.
2. **Minimum paired-block count `B_min`** — solved per step 4 of the order above: the smallest block
   count at which BOTH (a) the realized crossing rate of the campaign's own stopping rule, evaluated
   over resampled A/A windows with the rule held fixed, does not exceed `α_sel`, and (b) the MDE
   derived from the A/A dispersion at that block count is no larger than the campaign's declared
   `contribution_floor`. `B_min` is floored by, and MUST NEVER fall below, the P-BENCH-1 reps rule
   (`bench-cpu.md:21-22`). Where the cell's own phase is governed by a protocol that states a
   stricter or a *fixed* rep rule, **that protocol's rule governs its own cells and this calibration
   never overrides it** — in particular `bench-cpu.md:174-178` (P-BENCH-4, *exactly five*, no retry,
   replace, discard or pooling) is a fixed count, not a floor to be raised, and
   `gpu-cross-device.md:146-147` (P-SHED-1, n ≥ 10 paired blocks) binds inside P-SHED-1's own
   `task_rate` comparison and is cited here as a precedent for the shape of the floor, not imported
   as a universal constant over instrument-level `tokens/s` cells. A calibration that would license
   fewer blocks than the owning protocol already requires is discarded, not applied.
3. **E-process rejection thresholds** — `1/α_sel` for selection and `1/α_conf` for confirmation. The
   selection error budget `α_sel` MUST NOT exceed the reciprocal of the campaign's declared
   `max_candidates`, so that the expected number of false selections across the entire campaign is at
   most one. The confirmation error budget `α_conf` MUST NOT exceed `α_sel` divided by the declared
   `confirmation_admission_count`, and MUST NOT be looser than `α_sel`. `α_sel` is then validated
   empirically **once, at the solved `B_min`** (step 5 of the order above): the A/A control, replayed
   through the campaign's own stopping rule, MUST NOT cross the selection threshold at a rate
   exceeding `α_sel`. If it does, the calibration FAILS; the threshold is tightened and the solve
   restarts, and both the failed and the accepted calibration are retained in the manifest.
4. **Anchor-gate acceptance band** — the interval containing the central 95% of the anchor cell's own
   calibration values under the identical recipe and host state, computed at the solved `B_min`.

**There is no fifth output.** The campaign storage floor is NOT derived here: it is
`storage_floor_bytes_free`, defined once by the evidence-retention clause of `MEASUREMENT.md` §5 and
referenced by precondition 7. Two definitions of one manifest field, in two scopes, is the defect
this note exists to prevent.

No value in this list may be supplied as a literal — not by a controller, not by a proposal, not by an
operator convenience flag, and not by this protocol. The **e-process construction itself** (its
supermartingale or betting form, its reducer, and its resampling method) is a property of the
evaluator bundle, fixed at the bundle hash; a campaign selects among constructions the bundle already
implements and records which one it selected. A campaign that cannot complete its calibration block
MUST NOT rank any candidate.

### Statistical requirements

- **Reps.** Per the P-BENCH-1 rule (`bench-cpu.md:21-22`) — ≥5 for ≥5% effects, ≥10 for ≤2% effects —
  and never fewer than the calibrated `B_min` paired blocks, except where the owning protocol of the
  cell's phase states a fixed count, which governs. Report median + MAD.
- **E-process, never an ad-hoc bound.** Every rate comparison goes through the non-inferiority /
  improvement e-process (`MEASUREMENT.md:30-32`), never a single trial. E-processes are anytime-valid,
  which is precisely what a controller that inspects its evidence every round requires. The term
  "LCB" appears **nowhere** in this constitution. A lower-confidence-bound construction MUST NOT be
  the test that ranks, retains, abandons, branches, composes or contributes to readiness, MUST NOT be
  substituted for the e-process, and MUST NOT be reported as though equivalent to it. An LCB MAY be
  carried **beside** the e-value as a labelled descriptive statistic — a magnitude summary for a
  human reader — provided the record carries the e-value and its threshold, the LCB is labelled
  `descriptive`, and no decision in the enumerated authority is taken on it.
- **Pre-committed stopping rule.** Declared at campaign start per `MEASUREMENT.md:136-137` and
  `MEASUREMENT_POLICY.md:59-61`, and fixed as a calibration *input* per the solve order above: name
  the table that is FINAL, the decision each outcome triggers, the `max_blocks_per_candidate`
  ceiling, and the bounded extension rule. Extension follows the declared rule
  only, in the manner of `bench-cpu.md:85-86` (a bounded number of fresh reversed-order pairs pooled to
  a pre-declared threshold) rather than unstructured continuation while the answer might still change.
  Anytime-validity licenses **inspecting** at every block; it never licenses **changing the rule**. Any
  post-hoc change to the stopping rule voids every affected record.
- **MDE published WITH the result.** The minimum detectable effect is computed from the calibrated
  dispersion and the realized block count and is written into the same record as the estimate, not
  afterwards (`gpu-cross-device.md:147-148`). `|effect| < MDE` yields the verdict **no detectable
  difference**, which is a result and a decision, not a failed experiment
  (`gpu-cross-device.md:149-150`).
- **Order control.** Candidate and anchor are interleaved and order-randomized within every paired
  block (`gpu-cross-device.md:136-137`); the randomization seed derives from the campaign seed
  committed before the first candidate was measured, and is recorded. Blocked designs
  (candidate × n, then anchor × n) are forbidden — thermal and page-cache drift alias onto the arm
  effect. A retry is a fresh reset in reversed order (`bench-cpu.md:48-49`).
- **Anchor gate.** The anchor cell is measured FIRST in every window and compared against the
  calibrated acceptance band. Outside the band ⇒ the window is **VOID** and may not be reported —
  the `bench-cpu.md:231-233` pattern. A VOID window is journaled as `INVALID`; it MUST NOT be
  recorded as a candidate failure, because a drifted anchor says nothing whatever about the candidate.
- **Selection/confirmation split.** The measurement material — shapes, seeds, and blocks — is
  partitioned into disjoint **selection** and **confirmation** strata by a rule recorded in the
  campaign manifest and keyed on the campaign seed, before the first candidate is measured. Selection
  evidence MAY promote a candidate into the champion lineage. The readiness signal is computed ONLY
  from confirmation-stratum evidence gathered after the candidate entered the lineage. No block may
  serve both strata; a record mixing strata is `INVALID`. The confirmation stratum's contents MUST NOT
  appear in planner context, and a proposal that targets a confirmation shape is rejected before it
  consumes a window. Confirmation shapes and control seeds rotate on the schedule declared in the
  evaluator bundle. The reason for the split is mechanical, not ceremonial: selecting the maximum over
  many candidates biases the selected estimate upward, so the evidence that promotes a candidate is
  structurally unfit to report how ready it is.

### Controls — four mandatory, plus one accept-side control run under a declared contract

Control definitions, fixtures, expected directions, and seeds live inside the evaluator bundle under
the measurement trust boundary and MUST NOT be modified by any process inside the loop. **A campaign
that cannot run controls 1–4 MUST NOT rank any candidate.** Control 5 is a contract that names its
supplier and has a declared unavailable branch; it is never silently skipped.

1. **Positive** — a known-correct optimization with a real, bounded mechanism. MUST rank above the
   anchor. Failure is a gate defect.
2. **Neutral** — a correct change whose true effect is centred on zero. MUST NOT advance, and its
   dispersion is checked against the calibrated floor.
3. **Degraded-negative** — deliberately fast-looking but wrong: cheating, silently falling back,
   reducing work, or serving a cached result. MUST receive **no speed rank at all**.
4. **A/A** — the anchor measured against itself, through the full candidate pipeline. Runs
   **periodically on its declared cadence, not once per campaign**: it calibrates the false-positive
   rate and it is what detects host drift mid-campaign. A failing A/A **VOIDS** the enclosing
   measurement window.
5. **Historical-win replay (accept-side control, declared contract).** The campaign manifest
   declares a `historical_win_replay` entry carrying `{win_id, backend, phase, reference direction,
   reference magnitude band, in-repo evidence locator, durability class}`. The evaluator bundle
   resolves that entry at run time and replays the win end-to-end through T0–T2; it **MUST promote**.
   A failure to promote is a **gate defect**, not a research finding: it halts the campaign and is
   escalated to the operator. This control exists because the other four all test the gate's ability
   to *reject*, and without a test of its ability to *accept*, a quietly dead gate is
   indistinguishable from an exhausted search surface.

   **Unavailable branch (normative, not a silent skip).** A campaign whose backend has no qualifying
   durable win — no entry, or an entry whose evidence locator does not resolve in-repo per
   `MEASUREMENT.md:146-156` — records **`HISTORICAL_REPLAY_UNAVAILABLE`** in its journal and its
   manifest, naming the backend and the reason, and **escalates to the operator**. It MUST NOT
   silently run four controls and report as though it ran five: every record emitted by such a
   campaign carries `controls=4/5 (HISTORICAL_REPLAY_UNAVAILABLE)` in its grammar, and the readiness
   signal computed by such a campaign carries the same marker. Whether the campaign proceeds on four
   controls is the operator's call, taken once, on the record — not the controller's.

### Correctness precedence

Correctness, quality, numerical safety, integrity, and stability are **lexicographically prior** to
speed. A candidate failing any of them receives **no speed rank at all — not a penalised one**. A
penalised rank is still a rank, and any search that ranks incorrect candidates will eventually
surface one whose penalty is smaller than its apparent speed gain. This is the search-side form of
the rule already in Annex B, where *"model-load, correctness/coherence, numerical-safety,
attribution, or cleanup failure = FAIL regardless of throughput"* (`bench-cpu.md:89-90`).

Correctness verdicts are produced by the evaluator against declared oracles and are NEVER
self-reported by the candidate. A candidate output MUST NEVER be cached or reused as a correctness
oracle. Cache state is declared in every record.

### Search-grade requires ALL of

This ratified protocol; every precondition above; a completed and accepted calibration block for the
cell's (backend, phase, cell class); the pre-committed stopping rule unmodified; `B_min` paired
blocks under order-randomized interleaving; a passing anchor gate; a passing A/A control within its
declared cadence; controls 1–4 available and passing; control 5 either passing or explicitly
recorded `HISTORICAL_REPLAY_UNAVAILABLE` with an operator escalation on the record; an e-value
against the calibrated threshold; a published MDE; the correct stratum; the complete record grammar
below; and raw samples from which the reduction is reproducible.

Missing ANY of these makes the record `INVALID`. There is no weaker-but-usable state: an `INVALID`
record is retained in the journal and MUST NOT rank, bank, compose, or contribute to readiness.
**Neither state is ever a claim** — a conforming search record is still an observation with respect
to `MEASUREMENT.md:9-11`, licensed only for the narrow authority enumerated above.

### Record grammar

A search record is not a claim, and its grammar must say so. Every record carries `category=CANDIDATE`
per `MEASUREMENT.md:85-95`; the tier; the evaluator bundle hash and runtime source-label attestation
reference; the resource-claim receipt; the host-health receipt; the anchor identity (source commit,
binary and linkage SHA-256); the recipe-constructor identity; the stratum; the scope denominator of
what was actually measured; the determinism class; and a reference to the raw samples. A record whose
reduction cannot be recomputed from its raw samples is `INVALID`.

**Grammar** (every field the paragraph above makes mandatory appears here; a record conforming to
this template is a complete record, and a record omitting any field of this template is `INVALID`):

`<metric> <value> <higher-better|lower-better>, tier <T0|T1|T2>, vs anchor
<anchor_commit[:12]>/<anchor_binary_sha256[:12]>/<anchor_linkage_sha256[:12]> — SEARCH RECORD, NOT A
CLAIM [P-AK-SEARCH-1, category=CANDIDATE, blocks=<n>, e=<e-value>, thr=<1/α>, MDE=<mde>, floor=<φ>,
stratum=<selection|confirmation>, det=<determinism-class>, scope=<denominator of what was measured>,
controls=<4/5|5/5>[ (HISTORICAL_REPLAY_UNAVAILABLE)], campaign=<campaign_id>,
eval=<bundle_sha256[:12]>, srclabel=<runtime_source_label_attestation_ref>,
recipe=<recipe_constructor_id>@<recipe_sha256[:12]>, res=<claim_receipt>, host=<host_receipt>,
raw=<raw_samples_ref>, YYYY-MM-DD]`.

The grammar carries no `attest <ref>` field. Attestation in this constitution refers to a claim
(`MEASUREMENT.md:13`), and this record is not one; the `res`, `host`, `srclabel` and `raw` receipts
are what make it auditable. **Reconciliation note for the owning design:** where the design's own
evaluation-event schema requires an `attestation_ref` field (owning handoff §3.4, §7.4), that field
is satisfied by `res` + `host` + `srclabel` together, and the design's schema is amended to say so
in the same bundle as the evaluator. This protocol does not create an `attest` field for a
non-claim.

### What voids a run

A resource claim not held, not re-verified, or held by a different holder at window close; a
host-health tier violation; a failed anchor gate; a failed A/A control; a missing, drifted, or
unverifiable evaluator bundle hash or runtime source-label attestation; a missing or mutated anchor;
hand-typed argv; contamination by concurrent inference; storage exhaustion mid-window; a strata
violation; any post-hoc change to the stopping rule, the calibration outputs, the objective, or the
control definitions; or an incomplete calibration block. A voided run is journaled as `INVALID` with
its reason, and is **never silently discarded** — primary records are never destroyed
(`MEASUREMENT.md:174-175`).

**Prospective.** This protocol applies only to runs started after ratification. It upgrades no
pre-ratification artifact, creates no retro-certification route, and **issues no ruling over any
existing corpus**. The standing of the pre-ratification kernel-research strategy-store rows is a
core-file §6b matter and is addressed, if the operator so chooses, by a separate strikeable line in
the same package (`RATIFICATION_PACKAGE.md` item 7), which appends to `MEASUREMENT.md` §6b rather
than ruling from inside an annex.

## P-AK-SEARCH-1-A1 — mechanism and capability clauses (RATIFIED 2026-08-03)

Appended to Annex K as a narrowing of `P-AK-SEARCH-1`, which it does not restate or replace.

**Clause 1 — mechanism plausibility.** A banked candidate requires an explanation backed by bytes,
FLOPs, counters, or a clean A/B. *“It got faster and I don’t know why” is a reason to keep measuring,
not to land.* `P-AK-SEARCH-1` as ratified is purely statistical — pass the e-process, clear φ, publish
the MDE — which permits banking a candidate nobody can explain. This clause is directly
anti-reward-hacking and is the cheapest available strengthening of the C6 differentiator.

**Clause 2 — capability-claim gate.** Do not claim that a backend supports a kernel, dtype, quant or
performance tier unless that backend has **both correctness and performance evidence**. This governs
what may be *said* about a backend, not how it is measured — structurally different from every other
gate in this constitution, and the gap this project has actually tripped on: three different answers
for one decode edge case across seven backend sites, undetected because nothing compared them.

**Adopted as SHAPE, not as thresholds.** The source of these clauses pairs them with fixed literal
thresholds (land at ≥3% median, or ≥8–10% with added complexity) and **no statistical test at all** —
median and p20/p80 only. That is materially weaker than `P-AK-SEARCH-1`’s anytime-valid e-processes and
published MDE. **Importing those literals would be a downgrade dressed as an adoption.** They are
explicitly not adopted.



## P-AK-SEARCH-1 — owning-annex set extended 2026-08-03 (Annex S)

`P-AK-SEARCH-1`'s scope clause requires a search record presented on a durable surface to be
re-measured under *"its owning protocol in Annex B, Q or G"*. Annex S
(`measurement/protocols/speech.md`, ratified 2026-08-03) creates the owning protocols for the
`whisper_stt` and `qwentts_tts` backends, which had none when this protocol was ratified. That
set now reads **B, Q, G or S**.

This narrows nothing and lifts nothing. It records that the re-measurement route this protocol
requires now EXISTS for the two speech backends; before Annex S it did not, which made the
requirement unsatisfiable for them rather than strict.
