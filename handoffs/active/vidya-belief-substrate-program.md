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
- [x] PR1b **Machine anchoring pass built and run; `T2 MachineLocated` is populated.**
      `scripts/vidya/machine_anchor.py` fetches a cited source, finds the sentence-span whose
      distinctive terms match a claim, pins it with `quote_sha256` and stamps `located_by: machine`
      so the adapter caps it below a human anchor. First run over 12 cited entries produced **20
      anchors across 9 entries**, and the ledger now shows `Hinted/MachineLocated: 20` where the
      level had zero occupants this morning ✅ 2026-08-10
- [x] PR1b-guards The review step earned itself twice. Hand-checking the low-coverage tail of the
      first run found **two wrong anchors that had passed every threshold**: a WER claim pinned to
      a sentence that only NAMED the metric, and a token-reduction claim pinned to a span whose
      numbers CONTRADICTED it (claim 57-59% / 9-16 points, span 56% / 3.3 points). Term overlap is
      number-blind and this corpus is numeric. A numeric guard now requires a claim's magnitudes to
      appear in its span — and its own first version passed the contradiction anyway, because
      `MATH-500` contributed "500" to both sides: a shared NAME reading as a shared number.
      Identifiers are now excluded. 13 tests, negative control first ✅ 2026-08-10
- [x] PR1b-scale **Run at scale: 351 anchors applied across 158 entries.** The T axis went from
      **5 anchored claims in 4,191** this morning to **371 at `MachineLocated`** plus the 5 human
      ones. Ledger grade distribution now carries `Hinted/MachineLocated: 371`, a level that had
      zero occupants before today ✅ 2026-08-10
- [x] PR1b-index-bug The hand-review found a third defect, and this one was silent: the anchorer
      filtered non-string claims out of `key_claims` and then enumerated the FILTERED list, so every
      index after a non-string claim shifted — pinning a quote hash to the wrong claim. Seven index
      entries carry a non-string claim; 1 of the 352 proposals was affected. Fixed to enumerate the
      original list, pinned by test, and intake-218 dropped from the batch rather than repaired —
      re-running it under fixed code is cheap, guessing which claim it meant is not ✅ 2026-08-10
- [x] PR1b-218 Re-run under corrected indexing: the anchor lands on `claim_index: 1`, the string
      claim, where the buggy enumeration would have written `0` — the dict-valued claim. Confirms
      both the defect and the fix on the entry that exposed them ✅ 2026-08-10
- [x] PR1b-verify-110 **Not a mis-anchor — the SOURCE was corrected upstream and our record aged
      into falsity.** Verified against full text of arXiv:2603.05433 v1 and v7. Our claim is a
      verbatim copy of the v1 abstract; the authors later found the "+9-16 points" was a SCORING
      ARTIFACT (the base model split answers across two formats, so a boxed-only grader undercounted
      it) and revised the paper. Current Table 2: Qwen3-8B 95.7 → 95.7 (+0.0) and Qwen3-14B
      93.0 → 96.3 (+3.3), against a claimed +9-16. The entry also claimed +10 points on AIME 2024
      where the current table shows **−1.2**. Title updated to the current one, claim[4] marked
      `overturned` with the reason, audit note appended. Nobody touched this record and it became
      false anyway — the freshness failure the substrate exists for, in its purest form ✅ 2026-08-10
- [x] PR1b-upstream-drift **Detector built and validated.** `scripts/vidya/upstream_drift.py`
      batches the arXiv API and flags any entry whose paper was updated after our `ingested_date`.
      First sweep over 120 arXiv entries: **8 drifted (6.7%)**, and it independently re-found
      intake-110 — the case that motivated it — alongside SkillsBench (v4), HiSpec (v2) and
      Speculative Speculative Decoding (v3). What it asserts is deliberately narrow and pinned by
      test: drift means the source moved and nobody has looked since, NOT that the entry is wrong ✅ 2026-08-10
- [x] PR1b-drift-triage **Reframed after measuring the split, and 67 of the 68 dissolve.** The
      sweep found 68 of 617 arXiv entries (11%) whose source was revised after we recorded them —
      but **64 are `unverified` and 3 `stage1-unverified`; exactly ONE is dived.** For an unverified
      entry drift is not a correctness problem: the record already says nobody checked it, so
      reading 67 papers to confirm that unverified things are unverified is work with no consumer.
      What the finding licenses instead is a Stage-2 rule — *dive the CURRENT version and record
      which one you read* — now written into the intake skill, which prevents the class rather than
      draining it ✅ 2026-08-10
- [ ] PR1b-drift-990 The one drifted DIVED entry: intake-990, dived 2026-08-03, source updated to
      v2 the next day. Verifying whether v2 changed anything bearing on its three claims
- [x] PR2c-determinable **Measured how much of the backfill the record can support: 1 of 26.**
      intake-928 done — and reading it overruled the heuristic that found it. The correction
      inverts that entry's verdict_justification (the runtime gate it named is cleared upstream) and
      touches none of the four claims, so all four are `unaffected` rather than the one the keyword
      match proposed. Which is the case against applying that method to the other 25 ✅ 2026-08-10
- [ ] PR2c-remaining Backfill `claim_corrections` on the remaining **25** `dive-overturned`
      entries. Their prose either names no claim or echoes several ambiguously, so this genuinely
      needs whoever ran each dive — **108 claims stay blanket-opposed** until then. Guessing the
      mapping is the failure the field exists to prevent
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
- [x] PR2d-backfill **4 edges authored, 7 declined — and the strict test is much narrower than the
      sample's label.** Applying the counterfactual test (*would a claim in THIS entry have to
      change?*) to the 11 edges the 60-edge sample called evidential, only 4 survive: 1062→1050
      (an originality claim about what the 2007 paper does not contain), 1043→1067 (Theorem 17 is
      transported by Gradel–Tannen's universal property), 976→972 (Mercury is in the measured
      corpus), 982→939 (the claim is *about* 939's citation being faithful). One runs OPPOSITE to
      the citation that suggested it — 1067 is 2020 and 1043 is 2021, so the dependency is the
      reverse. All 7 declines are recorded with reasons in the authoring script ✅ 2026-08-10
- [x] PR2d-eval `live_eval` now scores a `propagated` class: a claim that declares `depends_on` a
      mutated entry MUST move, while a claim that merely cites it stays uncoverable. This is the
      first scorable propagation the system has had ✅ 2026-08-10
- [x] PR2d-finding **The result is 0 of 4.** The dependency frames are inert — the fold lists
      `claim_depends_on` under `ignored_frame_types`, so nothing propagates along an authored edge.
      The edges record a human judgment that the engine does not act on. That is the measurement
      PR2d existed to produce, and it could not have been seen before the edges existed ✅ 2026-08-10
- [x] PR2d-semantics **OP-11 ratified 2026-08-10: `review_required`, no grade change.** A dependency
      whose source has lost all support flags its dependents; no grade moves. Mirrors the correction
      rule — we know the ground shifted, not by how much. Not cosmetic: `allow_review_required`
      defaults False and the gate refuses on it. Alerts are tracked separately from `corrections` so
      the REASON stays legible ✅ 2026-08-10
- [x] PR2d-propagation **The propagation test now scores 4/4, up from 0/4.** Two engine gaps had to
      close, and the second is the interesting one. (1) The fold set the flag correctly but
      `impact_of_retracting` compared grades and broken paths only, so a review-only effect read as
      "unaffected" — a report that cannot see the one effect the ratified rule produces is not
      reporting impact. (2) Two of the four dependents were ALREADY `review_required` from their own
      `dive_corrections`, so the flag could not flip; a NEW dependency alert now counts as impact in
      its own right, because "my source was corrected" and "something I rest on was withdrawn" are
      two obligations cleared by different people ✅ 2026-08-10
- [x] PR2d-tests Six regression tests pin both halves of the ratified rule (flag set / no grade
      moved / dependent reaches the impact report / already-flagged claims still register a new
      alert / an undeclared citation propagates nothing) ✅ 2026-08-10

- [x] PR2d-idempotence Re-ingest was not idempotent: `frame_id` hashes `created_at`, so a fresh
      `--as-of` re-emitted the whole corpus — measured 9,599 → 19,270 frames with zero new
      information. Adapter dedup is now keyed on (frame_type, assertion). Verified: re-ingest with a
      new timestamp emits 0. **The locator-based support counting absorbed the damage** — the
      independent-support distribution was unchanged at 0→112, 1→4,108, 2→3 across the duplicate;
      under the old label-counting every claim would have shown 2 supports ✅ 2026-08-10

- [x] PR3 **Reconciliation implemented as a STANDING check, not a pilot-exit one.**
      `scripts/vidya/intent_reconcile.py` resolves every `human_intent_recorded` frame to a real
      ratification artifact on disk. It passes today because the ledger holds **zero** intent frames
      and nothing emits them — which is worth nothing on its own, so the check is wired to fail the
      moment an unbacked frame appears rather than waiting to be remembered at promotion time. Six
      tests exercise the paths that matter on a synthetic ledger (real artifact / missing file / no
      reference / path escaping the repo), because a suite that only asserted the vacuum would lock
      it in ✅ 2026-08-10

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
- [ ] R1b-closure-size Measure the closure fraction on a realistic program. **Blocker narrowed
      again 2026-08-10**: the negation stratum now EXISTS (R1b-discharge) but holds only 4
      dependency edges, so a closure fraction over it would measure the fixture, not the program.
      Needs PR2d-backfill at scale — perhaps 50+ authored `depends_on` edges — before the number
      means anything
- [x] R1b-usecase **Named: correction discharge over the transitive dependency closure.** Two of
      the three shortlisted candidates turned out NOT to need negation — "no unretracted opposition"
      and "no fresher measurement supersedes this" are both materialized by the fold and then tested
      positively, which is evaluation plus a filter, not negation-as-failure. The rule that
      qualifies is *a correction is DISCHARGED when no claim transitively depending on it remains
      flagged*: the dependent relation is recursive (`depends_on` composes) and the flag is derived
      in the same program. It is wanted, not hypothetical — **678 claims sit `review_required`
      today with no closure rule**, the same one-way ratchet the `correction_reviewed` frame broke
      at single-claim level, reappearing over a correction's whole blast radius.
      `research/deep-dives/vidya-r1-r2-stratified-negation.md` §2.4d ✅ 2026-08-10
- [x] R1b-discharge **Implemented — the pilot has its first negation stratum.** A correction is
      DISCHARGED when no claim transitively depending on it remains flagged; computed after the
      positive fixpoint closes, which is exactly what stratification licenses. On the live ledger:
      **2 discharged** (intake-939, intake-972) and **2 held open** by dependents still flagged from
      their own corrections. Seven tests, the load-bearing one being transitivity — discharging on
      direct dependents alone would call a correction finished while its reach was still flagged.
      Two bugs found on the way: the closure walked `claim → what it depends on` instead of
      `claim → what it belongs to`, and `sorted()` on (label, Grade) pairs crashed on the live
      ledger whenever two labels tied, a latent defect that needed the duplicate ingest to reach
      and that every test still passed through ✅ 2026-08-10
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
- [x] R3-full **DECLINED, not pending** — severed by the ratified V2 split and closed as a
      decision rather than left as an open box. Purity-as-evidence, licensed rewrites and e-graphs
      concern CODE identity, which this pilot does not track. The one slice that was load-bearing
      (anchor stability under reformatting) shipped as R3-narrow. Recorded position if ever
      resumed: the directed normalizer, with equality saturation earning its place only on measured
      need. Re-open by filing a new item with a use case, not by un-ticking this ✅ 2026-08-10
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
      correction saying intake-797 was a mis-stamp, and `recommendations.md` uses it as a range
      endpoint naming a historical batch ✅ 2026-08-10
- [x] D12 **Classified all 57 references to absorbed ids to test whether editing beats mapping.**
      13 are the mechanism itself, 29 record the merge, 7 are historical narration, 8 are live
      citations — and of those 8, exactly **one** is mechanically safe to rewrite. Four would be
      corrupted by a naive repoint (three are the KernelBench mis-stamp where intake-797 is named
      *because* it was wrong; one pair is a `intake-779 through intake-797` range endpoint).
      Editing is not the cheaper path; it is the path that requires per-site judgment ✅ 2026-08-10
- [x] D13 **Citation audit across all curated paths; 8 mis-stamps repaired.** Built a
      label-vs-title checker (271 files; the naive version produced 780 hits, almost all prose
      before a parenthetical, so it was tightened to name-like labels in curated paths only).
      Repointed with arXiv-id confirmation: KernelBench 797 to **664** (3 files), SIA 793 to
      **789**, DGM 786 to **772**, MCE 789 to **787**, AFlow 790 to **788**, PaperBench 795 to
      **794**. In the SIA and DGM cases the citation's own arXiv id already named the right entry
      — the intake id was the only wrong part ✅ 2026-08-10
- [x] D13b **Four citations name papers that were never ingested** — ADAS, Hyperagents,
      Self-Harness, ACE — each given a *neighbouring* entry's id, which reads as provenance and is
      not. Same family as the D1 `/doctor` fabrication. Marked `NOT IN INDEX` rather than
      repointed; inventing a target would repeat the failure. All four sit in the 2026-07-08
      batch — the same batch that produced the duplicate entries ✅ 2026-08-10
- [x] D16 All 101 placeholder titles resolved in one batched arXiv sweep (25 ids per request,
      5 requests, zero unresolved), with author lists added alongside. Cleared four false positives
      from the citation audit — YaRN, Sarathi-Serve, Cascade and SkillRL were correct citations
      with no title to match against ✅ 2026-08-10
- [x] D13c **All five phantom-cited sources ingested; two headline claims overturned.**
      intake-1068 ADAS (2408.08435), 1069 Hyperagents (2603.19461), 1070 Self-Harness (2606.09498),
      1071 ACE (2510.04618), 1072 RE-Bench (2411.15114) — each identified by a parallel subagent and
      verified against primary source. Every paper was real; the CLAIMS were wrong. rec-001's
      "LLM-as-judge benchmark design is optimizable" is supported by none of its three sources (all
      three optimize harness or context against a FIXED benchmark) and is rewritten. rec-002's
      "trajectory toward fully autonomous task generation" is supported by none of the lineage —
      Hyperagents lists "a fixed task and evaluation distribution" among its own limitations — and
      is rewritten to metacognitive self-modification ✅ 2026-08-10
- [x] D13d **`research/f1-dgm-scoping-2026-07.md` scoped F1 work on a capability DGM does not
      have**, taking "only the task-generation half" of a system with no task-generation half.
      Premise-correction banner added at the section head; the scoping itself is left to its owner
      to re-cut ✅ 2026-08-10
- [x] D13e **OP-10 ratified 2026-08-10: re-attribute, keep the pipeline.** Only §1 was affected —
      §2 (verifier matrix) and §3 (Simula QC) come from our own code and a different source. The
      three patterns F1 borrows (archive, branching, empirical validation) ARE in DGM; DGM applies
      them to agent variants and F1 transposes them to task variants, which F1 owns as an analogy
      rather than inherits as precedent. Pipeline unchanged — it was always seeded from our W3
      ledger and workload taxonomy. `dgm_provenance` renamed to `genprov` (the old name asserted a
      provenance those rows do not have), and the F1-DGM-1 completion note in
      `frontier-f1-real-task-corpus.md` corrected. Recorded as still needing its own justification:
      nothing in the index shows archive-based evolution works for generating TASKS ✅ 2026-08-10
- [x] D14 `research/recommendations.yaml` had never been parseable YAML — markdown headers and
      prose wrapped around an embedded list. Renamed to `research/recommendations.md`, which is
      what it is; 5 live references repointed, historical ones in `progress/` and
      `handoffs/archived/` left as written ✅ 2026-08-10
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
