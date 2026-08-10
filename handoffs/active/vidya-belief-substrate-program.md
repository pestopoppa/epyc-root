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

## Task list

### Completed — audit session 2026-08-09 (this handoff's origin)

- [x] Critical audit of the v1 draft; 37 sources ingested and dive-verified (intake-1031..1067,
      validator exit 0); all dive-surfaced sources dispositioned ✅ 2026-08-09
- [x] Consolidated deep dive written: `research/deep-dives/vidya-belief-substrate-audit.md`
      (verdict, seven wrinkles, corrections ledger, corrected formal foundations, adoption kit,
      landscape, machine-wide assessment, full reference table) ✅ 2026-08-09
- [x] Program handoff created + registered (master-index A12; research-evaluation-index row) ✅ 2026-08-09
- [x] HTML explainer (Parts A+B) published as a private artifact
      (`tmp/vidya-belief-substrate-explainer.html`) ✅ 2026-08-09
- [x] Intake bookkeeping: `handoffs_created` backfilled on all 37 entries; dispositions on the
      4 worth_investigating entries ✅ 2026-08-09

### Discovered mid-flight — intake-index data defects found while building the gold corpus (2026-08-09)

- [x] D1 A fabricated `/doctor` claim reported "struck" on 2026-07-25 by THREE separate records was
      never removed from `research/intake_index.yaml` and served as "CONFIRMED and understated" for
      15 days. Retracted in the artifact; entry set `dive-overturned` with a `dive_corrections`
      record; dependent `techniques` and `reported_results` lines marked. The governance finding —
      *a correction recorded only in narrative is not a correction* — is recorded in the entry and
      in the gold corpus (E3) ✅ 2026-08-09
- [x] D2 Systemic duplicate-YAML-key defect from the 2026-08-09 citation-graph migration: **538
      entries** carried two `cross_references.intake_entries` blocks (the migration appended the
      corrected list instead of replacing the original). Verified block 2 was a strict superset in
      all 538, so last-key-wins meant no data was lost — but the file was malformed YAML that a
      strict parser rejects. Repaired by deleting the superseded first block; citation graph proven
      identical before/after (2,007 edges, 1,067 entries); 1,840 dead lines removed; validator
      exit 0 ✅ 2026-08-09
- [x] D3 Duplicate-key check added to the intake validator. It had to run at **parse** time — a
      duplicate is last-one-wins in PyYAML, so by the time the validator inspects the parsed
      structure the earlier value is already gone, which is why 538 instances passed cleanly for as
      long as they existed. Implemented as a `SafeLoader` subclass that records duplicates with line
      numbers; tested against BOTH paths (clean file exits 0; an injected duplicate fails with
      `line N: duplicate key 'x'`) ✅ 2026-08-09

### V2 — Spec revision (the amendment sheet; first work package; blocks P1)

- [x] V2.1 Split the v1 draft into three artifacts: (i) pilot spec, (ii) formal research program
      R1–R5, (iii) non-binding mature-architecture appendix (operator-endorsed, steering seq 4) ✅ 2026-08-09
- [x] V2.2 Resolve the Corroborated-in-chain tension: either drop Corroborated from the carrier or
      restrict it to explicit independence-judgment tokens; document that ⊕=max can never derive it ✅ 2026-08-09
- [x] V2.3 Document the product-lattice option (quality × traceability) as an available design
      choice: every load-bearing theorem is algebraic (absorptive/0-stable/fully-continuous);
      cite Abo Khamis p.25 verbatim + what totality actually buys (selection semantics, cut-point
      thresholding) ✅ 2026-08-09
- [x] V2.4 Correct citations: fully-continuous not ω-continuous (Dannert, LIPIcs numbering);
      ≤N-step 0-stable convergence (Cor 5.19) replacing the folklore N×h attribution; "N+1" →
      N Kleene steps + zero-init layer (E&L Thm 6); Carneades 2007 = three standards, five-set =
      Gordon-Walton 2009; Potyka = KR 2018; Baur-Studer = CLAR 2020 ✅ 2026-08-09
- [x] V2.5 Pin the fold semantics to a Deletion-satisfying provenance semantics (P^AT); add
      Example 9 (minimal-depth failure) as a negative test vector; provenance store = DAG/circuit,
      never expression store ✅ 2026-08-09
- [x] V2.6 Replace iterate-until-stable with closed forms (lfp = F^N(0); gfp = F^N(F^N(1)) on
      ⊗-idempotent lattices); keep the N-step budget as a runtime assertion ✅ 2026-08-09
- [x] V2.7 Add the TOKI H1 judge-discipline rules as spec requirements (keyed judgment frames with
      full decoder tuple; first-committed-vote-wins per key; no model invocation during fold/replay;
      temp-0 is not determinism; total-order conflict tie-break) ✅ 2026-08-09
- [x] V2.8 Re-ground R1: zero-substitution licensed only for the positive core; specialization of
      dual-indeterminate provenance is the negation-era primitive (GT17 §5); per-stratum base case
      cites 1907.08470 (Def 29/Prop 30/Prop 41/Cor 38); register the residual theorem (cross-stratum
      re-tokenization equivalence + retraction exactness — proven nowhere) and the no-stratified-
      Datalog-provenance negative search result ✅ 2026-08-09
- [x] V2.9 Re-ground R2: certified absence = π⟦nnf(¬φ)⟧ over dual tokens; gfp non-specialization
      (Example 42) ⇒ absence certificates route through S∞[X,X̄]; cite Xu et al. 2018 as application
      precedent (decline-with-citation stands unless operator overrides) ✅ 2026-08-09
- [x] V2.10 Sever §7.19 semantic hashing / purity-as-evidence into the R3 research note; move §16.2
      mature-stack detail to the non-binding appendix (Rekor-v2/Tessera findings supersede parts) ✅ 2026-08-09
- [x] V2.11 Adopt the frame/ledger schemas from the adoption kit (nanopub envelope + lint rules;
      Graphiti bi-temporal fields incl. reference_time; PROV alias table; frame_type URIs +
      subjects[]; signed expiring policy frames; certificate-as-attestation-frame re-entry) ✅ 2026-08-09
- [x] V2.12 Adopt lifecycle + policy vocabulary (Active/Stale/Conflicted/Dropped + cite-only-Active;
      Abstain as typed transition; proof-standard grade names with the three EPYC gap closures;
      reconcile with dashboard/freshness.py vocabulary — map, don't fork) ✅ 2026-08-09
- [x] V2.13 State the pilot's security posture honestly (intent-frame forgery open in shadow mode;
      pilot-exit check that intent frames match ratification artifacts) ✅ 2026-08-09
- [x] V2.14 Add the operator-attention cost model (claims/batch sizing, anchor review, equivalence-
      check rate as an explicit metric) and restrict obligation conditions to ≤4 predicate types,
      one nesting level ✅ 2026-08-09
- [x] V2.15 Run the nine-relation coverage check against the frame-type vocabulary (Use, Generate,
      Derive + Support, Depend-on, Contradict, Invalidate, Trigger, Update — explicit
      adopt-or-decline for Trigger and Use/Generate) and score the design against the survey's
      Table-6 six-column rubric; record both results in the spec (intake-1034 derived actionables) ✅ 2026-08-09

### P0 — Pilot corpus (downscoped per audit; blocks P3–P5 evaluation)

- [x] P0.1 Gold corpus = 12–20 claims spanning statuses, seeded from REAL historical corrections
      (ngram 2.8× retraction; quality-NULL scorer artifact; 2026-07-25 fabricated citations;
      2026-08-09 renamed-kernel incident) — ground truth already recorded in dive_corrections/
      incident logs ✅ 2026-08-09
- [x] P0.2 Include one measurement-domain claim family (E8-era baseline slice) so era/frontier
      machinery is tested where it bites ✅ 2026-08-09
- [x] P0.3 Mutation classes introduced incrementally (start with source-edit + retraction; add
      classes as the engine stabilizes); blind gold-review per v1 §18.4 retained ✅ 2026-08-09
- [x] P0.4 Adopt HoH scoring (+1/0/−1 + A_C/A_O) and MemStrata protocol rules (marker-free
      construction; forced-answer stale-fact-error) as the pilot's precommitted metrics ✅ 2026-08-09

### P1–P5 — Pilot build (Python + SQLite, shadow mode; full detail lands in the V2.1 pilot spec)

- [x] P1a Foundation modules landed in `scripts/vidya/` + 59 tests passing: `canonical.py`
      (canonical JSON, float ban enforced, envelope hashing), `lattice.py` (Q × T with the algebraic
      laws property-tested over all 20 elements; witness sets; conjunctive-vs-join kept as separate
      functions), `frames.py` (envelope + both lint rules + the no-grade-in-pubinfo guard),
      `ledger.py` (append-only JSONL, fsync, prev_hash chain, torn-tail repair recorded as a
      frame), `checkpoint.py` (RFC 9162 tree math + C2SP notes pinned to v1.0.0), `fold.py` (pure
      fold, zero-substitution retraction, independent pro/con, judge replay-key enforcement,
      first-vote-wins) ✅ 2026-08-09
- [x] P1b CLI landed (`append|fold|checkpoint|verify|ingest`), first real checkpoint committed at
      `.vidya/checkpoints/checkpoint-00009449.txt`. `verify` reports `chain_ok` and
      `checkpoints_ok` SEPARATELY, with a test proving why: a tamperer who truncates and fully
      recomputes the chain leaves `chain_ok=True` and is caught only by the committed checkpoint ✅ 2026-08-09
- [x] P1c-a Golden fixtures written with pinned frame ids, state hash, Merkle root and note bytes
      (`tests/vidya/test_vidya_golden.py`), never regenerated by the test; plus a guard asserting
      the corpus still exercises a synthetic join ✅ 2026-08-09
- [x] P1c-b VERIFIED on aarch64: all 140 tests pass and every pinned hash matches, run under
      qemu-user via `docker --platform linux/arm64` (binfmt registered with tonistiigi/binfmt).
      A bind mount does not work in this devcontainer — the daemon does not share its mount
      namespace — so the suite is piped in as a tarball; the reproduction command is recorded in
      the fixture file ✅ 2026-08-09
- [x] P2a Read-only retrofit adapter over `intake_index.yaml`, run on all 1,067 entries: 4,191
      claims, 9,449 frames, 7.8s. Grades: Hinted/Located 3,449 · Verified/Located 582 ·
      Verified/Located (opposition) 112 · Hinted/T0 48. **Zero claims reach Verified/Anchored** —
      the retrofit cannot reach the T axis's Anchored level because an index entry identifies a
      document, not a span. This prices write-time instrumentation against prose-parsing in the
      policy layer's own currency ✅ 2026-08-09
- [x] P2b `claim_anchors` schema field + adapter grading (span -> T2 Anchored; span + revision +
      quote hash -> T3 Attested) + a Stage-2 obligation in SKILL.md. Demonstrated end-to-end:
      intake-1038's Property 13 claim carries a real anchor and is the first and only claim of
      4,191 to clear a conjunctive Verified/Anchored policy (was 0) ✅ 2026-08-09
- [x] P2c Correction frames from `dive_corrections` (150 entries, 652 claims) carrying verbatim
      text; the fold turns them into `review_required` — a freshness signal, never a grade change.
      The prose is deliberately NOT parsed and not keyword-scanned ✅ 2026-08-09
- [x] P2d Anchored the 5 claims this session's specs actually cite (intake-1038/1039/1040/1065/
      1067) — Property 13, S-infinity universality, the 0-stable N-step theorem, E&L Theorem 6, and
      the gfp non-specialization counterexample. All reach `Verified/Attested`; every quote hash
      verifies against its recorded text. Scoped as the corpus doc says: claims a plan cites, not
      all 4,191 ✅ 2026-08-09
- [x] P3 `impact.py`: impact AS hypothetical retraction (same fold, not a parallel traversal),
      coverage classes, and the exactness contract enforced — `verified_unaffected` is asserted
      only for claim-complete items, everything else reported separately as
      `unaffected_but_unmapped`. Obligations with the capped condition language ✅ 2026-08-09
- [x] P4 `projection.py`: select/render/map/publish with the deterministic three owned here;
      mandatory omissions lane; assertion verification at build time; four freshness states mapped
      onto `dashboard/freshness.py`. Real run: 148 included, 4,043 omissions each with a reason ✅ 2026-08-09
- [x] P5a `gate.py`: five honest outcomes, refusals that name the missing axis, advisory
      standards refused rather than downgraded, VSA-mapped certificates, and the invariant that
      only ALLOW is usable-as-current tested across every outcome ✅ 2026-08-09
- [x] P5c Gold corpus encoded as frames (`gold_corpus.py`), mutation suite run (`evaluate.py`):
      **28/28, recall 1.00, discrimination 1.00, 0 harmful**. It scored 20/28 first time and every
      failure was real — two engine bugs (retraction was per-frame when evidence is per-TOKEN, so a
      discredited source kept supporting its other claims) and two gold-label errors (E2's shared
      root cause modelled as independent; m-c5 given Witnessed warrant, making a downgrade
      arithmetically impossible). Decision package: **ITERATE** —
      `research/deep-dives/vidya-p5c-evaluation-and-decision.md` ✅ 2026-08-09
- [x] P5b `tests/vidya/test_vidya_compliance.py`: governance invariants + deliberately-rejected
      postulates (Recovery, accrual, corrections-as-counter-evidence, model-reachability checked
      structurally against fold.py's source) ✅ 2026-08-09

### Promotion track — opened 2026-08-10 after reviewing the ITERATE verdict

Verdict stands at ITERATE. Requirement status and the anchoring decision package:
[`research/deep-dives/vidya-p5c-evaluation-and-decision.md`](../../research/deep-dives/vidya-p5c-evaluation-and-decision.md) §4b.

- [x] PR0 Reviewed the four promotion requirements against current state. Three moved this session
      (R4b unblocked to 45 reviewable pairs; R5b emission wired; R4b surfaced source identity as a
      second prerequisite); the fourth is unblocked and unstarted ✅ 2026-08-10
- [x] PR1 **OPERATOR DECISION: option B, ratified 2026-08-10.** `T2 MachineLocated` inserted
      between Located and Anchored; carrier is now 25 elements. Spec §4.2 amended, `lattice.py`
      T_LEVELS extended, adapter caps `located_by: machine` anchors at the new level regardless of
      completeness, intake schema documents the field. Ordinal-safe: grades serialize as names, so
      no stored frame changed meaning. The compliance test caught the carrier-size change, which is
      what it is for ✅ 2026-08-10
- [ ] PR1b Build the machine anchoring pass itself: fetch cited sources, match claim terms, record
      `located_by: machine` anchors with `quote_sha256`. Sizing: 662 cited entries / 2,994 claims.
      The level now exists to receive them
- [x] PR2 `live_eval.py` + `vidya eval-live`: 148/148 on a citation-drawn corpus and 149/149 on a
      dived-entry draw, recall and discrimination 1.00, 0 harmful. **The score is not the result.**
      Of the 60 most-cited entries 50 are unverified, so the naturally-drawn corpus never exercises
      retraction at all — 148/148 is floor discipline plus controls, and `--verified-only` exists
      because of it. **Uncoverable claims outnumber scored ones 2–4× (527 and 272)**: they belong
      to entries that *cite* the mutated one, and citation is not an evidential edge, so scoring
      them would manufacture an answer ✅ 2026-08-10
- [x] PR2b Third instance of per-record identity found: evidence tokens are per *claim*
      (`evd_clm_intake_096_00`), so the gold corpus's sharpest family (E2 — one stale extractor
      under several conclusions) is not expressible against live data via token retraction. Source-
      level mutation is the workaround ✅ 2026-08-10
- [ ] PR2c Record per-claim correction labels at dive time. `dive_corrections` is free prose with
      no claim index, so which claims a correction falsified is unreadable by any program — the
      same write-time shape as the query log: seconds at dive time, impossible afterwards. Until
      this exists the live suite cannot score corrections at all
- [x] PR2d-measurement Two hand-classified samples settle it. A 20-edge uniform sample suggested
      "a citation from a dived entry is a candidate dependency" at 4/6 precision; a **60-edge sample
      stratified over the 672 dived-source edges refutes it — 18% evidential, 75% topical, 7%
      companion**. The n=20 result was a small-sample artifact of the semiring-provenance intake.
      Two mechanical rules also failed on the same 60 (names-the-target: precision 0.50 / recall
      0.09; verification-language: 0.50 / 0.27) ✅ 2026-08-10
- [x] PR2d **`depends_on` adopted 2026-08-10.** Schema field (`entry` / optional `claim_index` /
      required `why`), validator shape-check that refuses an unexplained dependency, a
      `claim_depends_on/v1` frame emitted by the adapter, and a Stage-2 obligation in the intake
      skill carrying the counterfactual test: *if that entry's claim were retracted tomorrow, would
      a claim in this entry have to change?* Citation edges are left untouched ✅ 2026-08-10
- [ ] PR2d-backfill Author `depends_on` on dived entries whose dependencies are already known — the
      11 evidential edges the 60-edge sample identified are the obvious first batch. Reasoning kept
      below.

      Adopt an explicit `depends_on` edge, authored at dive time. **Do NOT infer dependency
      from citation** — at 18% precision, promoting the 672 dived-source edges would create ~550
      false dependencies, which is worse than the uncoverable bucket it was meant to fix: a false
      dependency propagates invalidation into work that never depended on anything. Accepted cost:
      the live suite keeps reporting a large unscored bucket until `depends_on` edges accumulate,
      which is the honest reading — the propagation structure does not exist yet
- [ ] PR3 Reconcile every `human_intent_recorded` frame against an actual ratification artifact
      (spec §15 pilot-exit check) before any promotion proposal is written

### R — Research program (independent of pilot promotion)

- [x] R1a Theorem stated precisely with the partial result recorded: the construction is
      well-typed (Props 12+14/Thm 17), and the obvious reduction to the positive case is shown NOT
      to close — a cross-boundary retraction is a deletion composed with an insertion, which
      Property 13 does not cover. Negative literature result recorded so it is not re-searched.
      `research/deep-dives/vidya-r1-r2-stratified-negation.md` ✅ 2026-08-09
- [x] R1b-search Exhaustive counterexample search executed: **5,670 instances, 0
      counterexamples**, boundary growth confirmed present (retractions added up to 2 facts), and
      the harness mutation-tested — a deliberately naive route A yields 2,715 counterexamples from
      the same instances, so the null has detection power. Classification: unresolved WITH
      SUPPORTING EVIDENCE ✅ 2026-08-09
- [x] R1b-vacuity **The 2026-08-09 null was vacuous and is retracted.** Route A and Route B were
      the same computation — specializing the base to ⊥ then dropping ⊥ entries *is* deleting the
      fact — so 5,670 agreements measured nothing. The mutation test was sound but proved only that
      the harness detects disagreement, not that the routes differed. Equivalence now pinned by
      `test_reevaluation_route_is_ground_truth_by_construction` so it cannot be re-reported as a
      result ✅ 2026-08-10
- [x] R1b-refutation Genuinely incremental routes implemented and swept over the same 5,670
      instances: **circuit specialization is REFUTED, 2,241 counterexamples (39.5%)**, minimal case
      `p :- a`, `r :- not p`, retract `a` — a rule that did not fire has no circuit node to fire in
      when the retraction makes it true. Dual tokens cut it to 270 (4.8%); the residue is entirely
      intra-stratum chaining off a negation-derived atom ✅ 2026-08-10
- [x] R1b-exact-route Dual tokens **+ intra-stratum dependency closure**: 0 counterexamples over
      the full sweep — a sharper bounded result than the one it replaces, since the two weaker
      routes are now refuted rather than unverified. Caveat recorded and load-bearing: the exact
      route keeps **91.7% of stratum-2 rules** as circuit nodes, so it saves 8.3% over full
      re-evaluation at this size and is not yet worth building ✅ 2026-08-10
- [ ] R1b-proof The proof remains open — now for the *dual-closed* route, which is the one worth
      proving. Deeper strata and non-two-valued absence are still unexplored
- [ ] R1b-closure-size Measure the closure fraction on realistic programs. The exact route is only
      worth implementing if a retraction's negation-reachable set is a small part of the stratum;
      at sweep size it is 91.7%, which would make it pointless. **BLOCKED, and correctly so: the
      pilot has no negation stratum to measure.** Spec §12 requires the rule set to be positive, or
      to exclude negated strata from incremental retraction and full-refold them. So there are no
      realistic programs — the prerequisite is a USE CASE that needs negation (§R1b-usecase), not
      more compute
- [ ] R1b-usecase Name the first rule that genuinely needs negation. Candidates worth weighing:
      "no unretracted opposition exists", "no fresher measurement supersedes this", "no obligation
      is outstanding on this claim". Until one of these is wanted, R1b is a paper track and the
      exact route should stay unbuilt
- [x] R2a Scoped, with the constraint that removes an approach: gfp does NOT specialize
      (Example 42), so absence certificates cannot use the incremental path and must route through
      S-infinity[X,X-bar] — affordable here because the carrier is meet-idempotent. Also recorded:
      no reasons are available for absence of a DERIVED fact, and no dual-indeterminate circuit
      theorem exists ✅ 2026-08-09
- [x] R2b `absence.py`: key-non-membership and scan-completeness certificates, each naming the
      exact domain it covers. Derived emptiness REFUSES — kept as a named function that raises
      rather than being absent, because a plausible implementation would be an unprovable absence
      that looks like a proof. Scan completeness refuses on a gap: a hole in a scan is not evidence
      the hole is empty ✅ 2026-08-09
- [x] R3-narrow The one slice that IS load-bearing here: anchor stability under reformatting
      (`normalized_quote`/`quote_hash`). Whitespace-only licensed rewrites — deliberately NOT
      case-folding or punctuation-normalizing, both pinned by tests, because this project has a
      recorded scorer defect from treating a comma as insignificant ✅ 2026-08-09
- [ ] R3-full (severed by the ratified split, deliberately not started) purity-as-evidence,
      licensed rewrites, e-graphs — concerns CODE identity, which this pilot does not track
- [x] R4a Measured on real data and the result is a negative one: **100% of 4,191 beliefs are
      fragile**, 0 have independent corroboration — because claim IDs are per-entry, so two sources
      can never support the same claim. Cross-entry claim identity is a PREREQUISITE for any
      corroboration measurement; until it exists, `disjoint_supports >= 2` is unsatisfiable by
      construction ✅ 2026-08-09
- [x] R4b-mechanism `claim_alias` frame + fold support: a human-authored assertion that two claim
      ids denote the same proposition; the fold applies it and records that it did, never making
      the judgment. Union-find ordered by canonical id so the representative does not depend on
      frame arrival order ✅ 2026-08-09
- [x] R4b-candidates `scripts/vidya/alias_candidates.py` + `vidya alias-candidates` /
      `vidya alias-emit`. "Human-gated" was doing too much work as a reason to stop: the judgment
      is human, finding the pairs to judge is not. First real run reduced 4,191 claims / 8.8M
      possible pairs to **45 candidates** — an afternoon of review. Deterministic IDF-weighted
      Jaccard, no model call; same-entry pairs never proposed; every row starts `pending`; an
      approval without a named reviewer is refused ✅ 2026-08-10
- [x] R4b-source-identity First run found the same defect one level up: `source_id` is minted per
      *entry*, so two entries for one paper look like two sources. 4 of the 45 candidates are
      same-source; approving them unexamined would have produced the statistic's first "independent
      supports" and every one would have been one paper counted twice. Rows now carry `same_source`
      from a normalized locator ✅ 2026-08-10
- [x] D4 Intake validator gained `check_duplicate_locators`: normalizes `arxiv_id` and arXiv URLs
      to one key, so the existing duplicate-`arxiv_id` error finally sees pairs recorded one way
      each. **5 duplicate-locator groups over 11 entries** found. WARNING not error — a project page
      can legitimately back two artifacts, and this project has a recorded lesson against
      conflating a companion repo with its paper ✅ 2026-08-10
- [x] R4b-authoring Operator reviewed all 45 candidates 2026-08-10: **10 same, 35 different**
      (19 judged by hand; 26 auto-classified as different on numeric mismatch or low similarity and
      accepted). Frames emitted via `vidya alias-emit` ✅ 2026-08-10
- [x] R4b-independence The 10 aliases would have manufactured corroboration without a second fix:
      `_disjoint_supports` counted evidence LABELS, which are minted per claim. It now counts by
      **source locator**, and alias groups their author marked non-independent collapse to one
      witness. On the live ledger 7 of the 10 groups (same-source or linked) correctly produce no
      corroboration and exactly the 3 genuinely-independent ones do ✅ 2026-08-10
- [x] R4b-remeasure **The corroboration statistic is no longer degenerate.** Distribution over
      4,181 beliefs: 0 supports → 112, 1 → 4,066, **2 → 3**. First non-zero `disjoint_supports ≥ 2`
      in the program's history, and the 3 are real rather than double-counted records ✅ 2026-08-10
- [x] D5 **All 5 groups dispositioned 2026-08-10** (operator checklist). Merged 785→772, 784→244,
      797→418, 336→315: 16 claims folded into survivors, 13 citations repointed, index 1,067 →
      1,063, each survivor carrying a `merge_history` note. The fast-rlm trio (693/783/901) stays
      three entries with a `shared_locator_rationale` on each, and the duplicate-locator check now
      suppresses a group whose members all explain the sharing — a warning that keeps firing after
      the decision trains people to ignore it. Text surgery throughout, never a YAML round-trip
      (SKILL.md rule), verified field-by-field against the intended structure ✅ 2026-08-10
- [x] D8 Merging leaves permanent id gaps, which tripped the sequential-id check. A survivor now
      declares what it absorbed in a structured `merged_ids` field, so a gap is forgiven only where
      some entry names that exact id. The first version regexed the `merge_history` prose, which
      made a validation rule depend on sentence wording; it also compared formatted strings, so a
      zero-padded `intake-002` silently failed to match — invisible on the live index because every
      current id is three digits. Six cases pinned in
      `tests/skills/test_research_intake_id_sequencing.py`, including that declaring an id you did
      not absorb buys no pass ✅ 2026-08-10
- [x] D11 **The gap policy needed a forward pointer to be honest.** "A merged id resolves to
      nothing rather than to the wrong paper" only holds if *nothing* is recoverable, and it was
      not: 44 references to the 4 absorbed ids sit in 20 tracked files with no way to learn where
      they went. Now published as a generated redirect map (`research/intake_merge_map.md`) plus
      `resolve_intake_id.py` for single lookups and `--audit`; `validate_intake.py` fails if an
      absorbed id is missing from the map. Deliberately NOT a bulk repointer — inspection found
      that the live references must not be rewritten: the MI210 handoff cites intake-797 inside a
      correction saying intake-797 was a mis-stamp, and `recommendations.yaml` uses it as a range
      endpoint naming a historical batch ✅ 2026-08-10
- [x] D12 **Classified all 57 references to absorbed ids to test whether editing beats mapping.**
      13 are the mechanism itself, 29 record the merge, 7 are historical narration, 8 are live
      citations — and of those 8, exactly **one** is mechanically safe to rewrite. Four would be
      corrupted by a naive repoint (three are the KernelBench mis-stamp where intake-797 is named
      *because* it was wrong; one pair is a `intake-779 through intake-797` range endpoint).
      Editing is not the cheaper path; it is the path that requires per-site judgment ✅ 2026-08-10
- [ ] D13 `rec-001` in `research/recommendations.yaml` carries two pre-existing citation
      mis-stamps, surfaced by that audit: `Self-Harness (intake-785)` is Darwin Gödel Machine, and
      `ACE (intake-788)` is AFlow. Annotated as unverified rather than guessed. Needs whoever knows
      what rec-001 meant
- [ ] D14 `research/recommendations.yaml` is not parseable YAML and never has been (markdown
      headers plus prose above an embedded list). Pre-existing, unrelated to this session — but any
      tool that tries to consume it by extension will fail
- [x] D15 Propagated a verified 2026-07-22 KernelBench correction from
      `mi210-speed-campaign-summary.md` to `agentic-rocm-kernel-authoring.md`, where the identical
      mis-stamped `**Source**: KernelBench (intake-797, arxiv 2606.20128)` line was still live and
      uncorrected. Same failure this program was created over: a correction recorded in one place
      is not a correction ✅ 2026-08-10
- [x] D10 **Renumbering to close the gaps: assessed and declined**, rationale recorded in
      `intake-schema.md` § ID Sequencing so it is not re-litigated. Closing 4 gaps would renumber
      728 entries, rewrite 5,565 references across 479 files, and change 731 of the 1,067 intake
      ids embedded in ledger claim/source identifiers — which the append-only log cannot absorb,
      since changing frame content changes the content-addressed `frame_id` and breaks the chain
      the published checkpoint attests to. The decisive argument is independent of the ledger: a
      reused id resolves to the WRONG paper in older documents, which is a silent misdirection,
      whereas a gap is a benign absence ✅ 2026-08-10
- [x] D9 Repaired 84 dangling cross-refs left by commit b208d9ce, where another session's index
      consolidation removed `inference-acceleration-index.md` and
      `cpu-inference-optimization-index.md`. Repointed at `inference-research-index.md`; intake
      validation had been failing for every session and is now exit 0 ✅ 2026-08-10
- [x] D6 **Root-caused the duplicate entries — the intake skill needed fixing, and does now.**
      Dedup was working: it *labelled* the collisions `novelty: duplicate` and then persisted them
      as full entries anyway, each with its own `key_claims`, 12 in total and 10 cited by other
      entries. Worse, all 3 arXiv cases carry a null `arxiv_id` despite an arXiv URL — exactly 3
      such entries exist in 1,067, all 3 collide with an existing id, so **each would have failed
      validation had the field been filled in**. The check was passed by deleting what it inspects.
      SKILL.md §2/§2b/§2c now forbid minting an entry for a collision, require locator
      normalization before comparing, and forbid the null-`arxiv_id` shape;
      `check_laundered_arxiv_ids` warns on it ✅ 2026-08-10
- [x] D7 `check_laundered_arxiv_ids` promoted from WARNING to a hard error — the D5 merges removed
      the last three instances, so the blocker that kept it advisory is gone ✅ 2026-08-10
- [x] R5a Instrument specified + 2026-08-09 baseline recorded (4,191 beliefs; 15.6% of claims
      carry a correction; 1 anchored; 0 corroborated). Most of R5 is retrospectively computable
      from the ledger, which is the payoff of event sourcing ✅ 2026-08-09
- [x] R5b `query_served_frame` and `obligation_disposition_frame` implemented. The query frame
      records the OUTCOME, not just the hit — an abstention is the datum that tells you the gate
      refuses too much, and a success-only log would hide exactly that ✅ 2026-08-09
- [x] R5c Computed retrospectively from `ingested_date` (2026-03 onward) — I had filed this as
      time-gated while my own note said it was retrospective. The apparent 1%→68% correction-rate
      climb is a TRAP: it tracks when diving happened, not when errors happened. The confound-free
      signal is the overturn rate among dived entries, **27/160 = 16.9%** ✅ 2026-08-09
- [x] R5d-instrument The frames existed but nothing emitted them, so the clock had not started.
      `vidya query` now appends a `query_served` frame **by default** (`--no-log` to suppress) and
      `vidya disposition` records obligation outcomes. Opt-out rather than opt-in because the
      failure is silent and unrecoverable: a default of "off" keeps R5d blocked forever while every
      command still looks like it works ✅ 2026-08-10
- [ ] R5d Collect the forward series now that emission is live (genuinely elapsed-time gated —
      reuse cannot be reconstructed for queries nobody logged). Earliest useful read: ~30 days of
      real query traffic

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
