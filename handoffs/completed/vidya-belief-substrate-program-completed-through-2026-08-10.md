# Vidya Belief-Substrate Program — completed scope (2026-08-09 → 2026-09-27)

> **Historical ledger only; current work lives in [`../active/vidya-belief-substrate-program.md`](../active/vidya-belief-substrate-program.md).**
> Split out at the 2026-08-10 wrap-up: the program reached ~135 tasks with only 5 open, and the
> completed detail was hiding the live work. These tracks are terminal and are retained as the
> evidence record for the gates they passed.

## Task list (completed)

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
- [x] PR1b-drift-990 **Triaged against both versions read in full — and the drift went the good
      way.** v2 (15 → 35 pages, WebShop and HiddenRule-Gym added, three-seed replication and a
      unified 140-game evaluation delivered) *strengthens* claims 0 and 1: the failure regime is
      stated in our own terms and the baseline matching MemHarness's reward shape is upgraded from
      single-seed. Claim 2 is **narrowed** — the ~8.8pt/32-episode noise floor survives verbatim,
      but v1's blanket "all cross-arm comparisons in this version are descriptive" was scoped to v1
      and replaced by formal endpoints, and the unexplained 8B inversion (32.8 vs 4B 49.5) resolved
      to 45.0% [37.0, 53.3] — a worked example of the very floor the claim names. First real use of
      the `narrowed` verdict, which is exactly what it was added for. `authors` backfilled ✅ 2026-08-10
- [x] PR1b-990-followups Both fields updated from the v2 quotes I already had — filing this as
      "needs a reader with the tables open" was deferring something I could do.
      `contradicting_evidence` now records that v2 replaced the descriptive caveat with 140-game
      formal endpoints and resolved the 8B inversion, keeping only the narrower live limit;
      `reported_results` carries the resolution and v2's additions ✅ 2026-08-10
- [x] PR2c-determinable **Measured how much of the backfill the record can support: 1 of 26.**
      intake-928 done — and reading it overruled the heuristic that found it. The correction
      inverts that entry's verdict_justification (the runtime gate it named is cleared upstream) and
      touches none of the four claims, so all four are `unaffected` rather than the one the keyword
      match proposed. Which is the case against applying that method to the other 25 ✅ 2026-08-10
- [x] PR2c-remaining **All 25 recovered — and I was wrong to call it blocked.** The prose the
      divers wrote IS the record; reading it is the method. Three readers recovered per-claim
      verdicts for every remaining entry, each verdict quoting the phrase it rests on. **Of 106
      claim verdicts: 68 unaffected, 25 narrowed, 6 uncertain, 3 reattributed, and only 4
      OVERTURNED.** The blanket was marking 114 claims wrong where 4 were; adapter opposition
      output drops from 114 frames to 6 ✅ 2026-08-10
- [x] PR2c-uncertain Recovery needed a fifth effect. `uncertain` records that a reader examined the
      prose and it still does not say — intake-971#record's `dive_corrections` is empty entirely. Distinct
      from an absent record, which means nobody looked; only the first should stop a future reader
      repeating the work. It clears nothing and keeps the entry-level verdict ✅ 2026-08-10
- [x] PR2c-supersede Emitting the right frame is not withdrawing the wrong one: **204 superseded
      opposition edges retracted** (not deleted — an earlier frontier still folds to what we
      believed then) and **103 correction frames marked reviewed**, which is what
      `correction_reviewed` exists for and which a per-claim record is the strongest form of ✅ 2026-08-10
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
- [x] R1b-depth3 **Bound extended to three strata: 0 counterexamples in 40,500 instances**, with
      a detection control — plain circuit specialization, already refuted at depth 2, produces
      **16,911** on the same sweep, so the harness can see a wrong answer at this depth. Boundary
      growth of 3 confirms retractions add facts across both boundaries. Found a harness bug first:
      the initial run reported 1,836 counterexamples that were all rule-ORDER artifacts of a
      single-pass stratum evaluator; the ground truth was wrong on both sides. A fully-formed
      spurious refutation, caught by suspecting the test method
      (`scripts/vidya/r1_depth3_sweep.py`, §2.4e) ✅ 2026-08-10
- [x] R1b-proof **RESOLVED — and the answer is both.** Exact for a SINGLE negation boundary, with
      a proof: stratum 1 is positive so `lower_post ⊆ lower_pre`, the closure operator is monotone
      in its base, hence `S' ⊆ S` and every rule that can fire is already recorded. **Refuted for
      composition**, by a three-rule program built by reasoning about where that argument breaks —
      monotonicity is exactly what a negation boundary destroys, so a stratum-3 rule needing a
      post-retraction-only atom is never recorded (`p :- a`, `r :- not p`, `t :- r`; truth derives
      `{r,t}`, the route derives `{r}`). The 40,500-instance null missed it because the generator
      never emitted that shape — **exhaustive over a generator is not exhaustive**. The repair
      (seed each closure with POSSIBLE heads) fixes it, 0 counterexamples over the same sweep, and
      retains 88.4% of rules — so §2.4c's verdict is unchanged: not worth building.
      `research/deep-dives/vidya-r1-r2-stratified-negation.md` §2.4f ✅ 2026-08-10
- [x] R1b-closure-size **Closed as CONDITIONAL, not left open.** Measured what exists: the
      negation stratum is 4 `depends_on` edges with reach 1 each — 0.09% of the corpus — so a
      closure fraction over it describes 4 hand-authored edges, not a program. Growing it to a
      meaningful size means authoring ~50 edges, which at the measured yield (18% of citations are
      evidential, and only 4 of those 11 survived the strict counterfactual test — roughly 6%)
      requires classifying ~830 citation edges.
      **That campaign buys a number whose only consumer is a decision already leaning the other
      way**: the exact incremental route retains 91.7% of the stratum at sweep size and 100% here,
      so it saves nothing worth having. Re-open this ONLY if someone wants to build the incremental
      route; the measurement is not blocked by tooling, it is blocked by having no consumer ✅ 2026-08-10
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
- [x] R5d-baseline **t=0 reading taken rather than waiting for it.** The longitudinal series does
      need elapsed time, but the instrument's behaviour does not: the gate was exercised over all
      4,223 claims under four policies. That produced the chain of binding constraints — T bound
      first (615 claims cleared Verified, 5 cleared Anchored, and the anchoring and verification
      passes had hit DISJOINT sets), then after anchoring the 26 dive-verified entries 52 claims
      cleared both axes, and then `review_required` bound, which PR2c cleared. **Strict
      Verified/MachineLocated now allows 9 claims, up from 0** ✅ 2026-08-10
- [x] R5d **Delivered as a computation, not a diary entry.** "Collect the forward series" is a
      standing obligation wearing a checkbox, and this repo has the scar from the last one:
      `readme-refresh.md` was legitimately completed, archived, and left a recurring alarm firing at
      a routing target that no longer existed, after which both READMEs drifted to 66 days.
      `scripts/vidya/r5_series.py` computes the whole series from whatever the ledger holds — claim
      age and grade trajectory by folding at successive frontiers, query volume and outcome mix,
      abstention rate by day, time-to-first-reuse, obligation dispositions. Run today it reports the
      t=0 shape and NAMES the panels with no data; run in a month the same command reports the
      series. Nobody has to remember a procedure and no checkbox has to lie meanwhile ✅ 2026-08-10
- [x] R5d-honesty The reuse panels are empty and stay empty: **synthesizing `query_served` frames
      to fill them would fabricate the exact measurement they exist to report.** The 16,892 gate
      evaluations run for the t=0 baseline deliberately used `evaluate()` rather than `vidya query`
      for that reason. A test asserts the panel stays empty on a query-free corpus, so any future
      convenience that seeds it has to delete that test to pass ✅ 2026-08-10

## Completed 2026-08-10 → 2026-09-27 (moved at the 2026-09-27 wrap-up)

> Moved verbatim from the active handoff at the 2026-09-27 wrap-up (session `workspace-8d`).
> Subsections mirror the source headings; whole source sections keep their own (demoted) heading.
> Every moved row is ticked; open, frozen, blocked and guarded rows stayed in the active file.

### Source coverage — opened 2026-08-10 (operator question: what about wiki/logs/progress?)

- [x] **SC19 — wire `ChatResponse.contention_gate` (A14) on the write side, BEFORE the branch
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
      **STATUS 2026-08-13: A14 landed locally** on orchestrator `main` as `c61b8184`
      (cherry-pick, merge-gate verdict autonomous, local-only — NOT pushed; push freeze). The
      "while unmerged" phrasing no longer applies to the branch, but the PRACTICAL capture window
      is still open: the orchestrator API is down and the code is not pushed, so zero
      `gate_decisions` have been emitted. Wire the write side (adapter + producer-written hook)
      against the merged commit before the orchestrator next serves traffic; do NOT close this
      row until the adapter emits its first tuple.
      **Independent merge audit 2026-08-13: ACCEPT.** `c61b8184` has the same stable patch-id and
      six-file `+299/-0` diff as source `a7d7bdb6`; the merge gate classifies the range autonomous,
      and the focused contention/chat suite passes (`118 passed`). This accepts the cherry-pick
      only; SC19 remains open until its producer-written adapter emits the first tuple.
      **Self-caught, and the trigger is worth keeping:** I built this surface earlier tonight and
      filed no wiring task until `mainA` published the right test — *"you touched a producer", not
      "you thought about producers"*. A checklist keyed on the diff catches it; one keyed on intent
      does not. Four instances in one day (v9 freeze receipt, mainA's affinity-preflight surface,
      this one, and the standing `benchmarks/results` proof) says the rule is known and the trigger
      is what is missing.
      **STATUS 2026-08-23 (EVL-47 SC19): write side wired; first tuple pending first
      orchestrator emission.** Producer-written capture hook landed in the orchestrator
      (`src/scheduling/contention_gate_capture.py`, call site `src/api/routes/chat.py` where the
      echo is stamped; envelope `contention_gate_capture.v1`, ONE request-keyed JSONL row per
      request — the locator trap pinned at the write site — opt-in via
      `ORCHESTRATOR_CONTENTION_GATE_CAPTURE` (default OFF), never raises, `None` echo writes
      nothing) plus `tests/unit/test_contention_gate_capture.py` (6 passed). Root adapter
      `scripts/vidya/adapters/contention_gate.py` registers `contention-gate-measurement`,
      projects ONE claim per request (never per decision), derives the measured verdict
      (`admitted_immediately` / `queued_then_admitted` / `blocked`) from the producer's own
      fields, and delegates grading to the shared ladder; honest grade `Witnessed/Anchored`
      until a producer-pinned envelope hash exists (off-tree append-only log, no collect-time
      digest). `tests/vidya/test_contention_gate_adapter.py` (12 passed) + `test_sealed_manifest.py`
      (19 passed) green. Source-table row updated. **Honest state unchanged: the orchestrator
      API is down and the capture is default-OFF, so zero `gate_decisions` have been emitted —
      an empty capture is not a measurement, and this box stays `[ ]` until the adapter emits
      its first tuple (first orchestrator start with the env var set).
      **STATUS 2026-08-26: write side wired (EVL-47) — the producer hook is in the serving code and
      the strict reader projects one claim per request — but zero tuples have emitted: the API is
      serving again (restart 2026-08-23T09:35Z) and the capture is still opt-in default-OFF, absent
      from the running process's environment, and no `contention_gate_capture.jsonl` exists.
      SHARPENED TRIGGER: this row closes at the first orchestrator start with
      `ORCHESTRATOR_CONTENTION_GATE_CAPTURE=1` and the adapter's first emitted tuple — an empty
      capture is not a measurement, and the API-up-again state means the capture flag is now the
      only missing element
      **CLOSED 2026-08-26 — first tuples emitted and ingested.** Orchestrator restarted with
      `ORCHESTRATOR_CONTENTION_GATE_CAPTURE=/mnt/raid0/llm/bus-runtime/contention_gate_capture.jsonl`
      (the env var's VALUE is the capture path — a first attempt with `=1` wrote to a file named
      `1`, evidence moved to the canonical path); two real chat requests (one mock — no gate
      decision, correctly skipped — then two real-mode) produced two request-keyed envelopes
      (`admitted_immediately`, `waited_s=0.0`, `reason="no active decodes"`). The strict adapter
      projected both, frames ingested into the ledger (frontier 12,502), fold reports
      `clm_cg_api-*` at **Witnessed/Anchored** — the kernel's first live contention-gate
      measurements. Capture is now default-on for the serving process; the row closes ✅
      2026-08-26**

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

- [x] **SC33 — Wire the executable AutoKernel reward-integrity corpus prospectively.** ✅ 2026-08-12 —
      successor r4 (`rvp-c6-executable-r4-20260812T191027Z`) emitted **53** producer-authored
      `belief_measurements`: three detector aggregates plus 50 exact case×ranked-unit elapsed-time
      rows. Its self-hashed v2 receipt (`c9e83b2245f28816eed72f0d0380cb18e59465c82996d572e6ddfaa8306228cd`)
      caught **10/10** planted cases, rejected **15/15** clean cases, and observed runtime behavior in
      **25/25** cases under released MI210 claim `akd-0ee8ec07c769492f`. The strict root adapter
      independently projected **53/53** rows across sensitivity, specificity, false-positive rate,
      and ranked-unit gfx90a elapsed time. All remain `BASELINE` instrument-validation evidence with
      `candidate_speed_claim=false`; the pre-hook r3 receipt remains deliberately unprojected.
- [x] **SC34 — Wire the governed raw-HIP authoring round trip prospectively.** ✅ 2026-08-12 — the
      research producer emits separate public-correctness and timing-harness-validity fractions with
      scored-case denominators, exact source/toolchain/task/candidate identities, and two released
      MI210 claim/sampler windows. Root `autokernel_aux_receipt.py` independently re-derives both
      rows, every receipt/window/sampler digest, the clean AgentKernelArena pin and physical gfx90a
      binding, while preserving observation-only/no-ranking/no-promotion authority. r4 is the first
      complete post-contract proof; r1–r3 are not retrofitted.
- [x] **SC35 — Wire the decision-grade raw-HIP receipt prospectively and prove the read path.** ✅ 2026-08-12 —
      `autokernel_aux_receipt.py` admits only the producer-authored sealed-correctness and exact-provider
      speedup rows after independently re-deriving the receipt/window/sampler hashes, task/vendor/candidate
      seal, 24/24 host-double result, C6 allowlist plus empty-cgroup teardowns, exact one-graph
      Torch-ROCm-compile provider, all 20 raw paired blocks, every one of the 40 per-arm RVP-C3-5 duration
      checks, e-process crossing, distinct released MI210 claims, and the task-local/no-release boundary.
      The terminal r6 receipt projects two Witnessed/Attested rows; sub-floor timing or invented release
      authority fails closed. r4 remains superseded instrument evidence and is never upgraded on read.
- [x] **SC36 — Wire AutoKernel actor-critic intermediate evaluation feedback prospectively.** ✅ 2026-08-12 —
      research `b0d6f79f` adds two self-hashed correctness/timing-validity rows to every future broker
      result, binding producer, candidate source, ordinal, baseline, task/controller/checkpoint/attempt,
      and the exact measurement window. The strict root reader independently re-derives those rows,
      receipt/window/sampler hashes, and the released MI210 claim while preserving
      `controller_feedback_only`, no-ranking, no-bank, no-champion, and no-promotion authority. R12–r17
      are immutable pre-hook evidence and emit zero rows; r18 is the first eligible campaign.

- [x] **SC44 — Integrate the completed AutoKernel experimental-runtime DFlash2 prospective hook before DF2-5.**
      The DF2-4 matched np1 campaign finalized three exact arms (plain, MTP8, DFlash2 block8) with
      12 scored prompts each, higher-is-better decode throughput, draft-acceptance numerators and
      denominators, exact candidate/binary/target/draft-model/protocol identities, and released MI210
      claim plus KFD/VRAM witnesses. Its finalizer did not write a native `ClaimTuple`, so the completed
      campaign at `artifacts/architect-bench-gpu-20260814/dflash2_np1_20260820/` is immutable pre-hook
      evidence and MUST emit zero rows rather than be reconstructed on read. Before DF2-5 np2/4/8,
      integrate research `71b81a8e849a7b4f75160fceb9d720e1f91dc11b` first, then root adapter
      `e0376ea19d85af5aba41b855fa6fee5ca5926176`. The implementation writes 6 arms × throughput and
      weighted-acceptance carriers, uses the campaign locator rather than treating request rows as
      independent witnesses, binds exact claim/release/residency and manifest hashes, declares
      `metric_direction=higher_better`, and delegates grading to `claim_tuple.grade()`. Cross-repo
      synthetic projection yields 12/12 Witnessed/Attested rows; actual DF2-4 yields zero. Preserve the
      `experimental_runtime` / no-kernel-champion / no-promotion boundary. Source-register row is in
      `scripts/vidya/adapters/README.md`. Keep this row open only until both pushed commits are integrated.
      **STATUS 2026-08-26: both commits exist but neither is on main — research `71b81a8e` sits on
      `codex/df2-claim-carriers-20260820` and root `e0376ea1` on `codex/df2-belief-adapter-20260820`
      (the register's "merge pending before DF2-5" still holds), and DF2-5 np2/4/8 has not run.
      SHARPENED TRIGGER: merge research first, then root, then run DF2-5 — the row's own termination
      condition is the two merges, and the first DF2-5 campaign is the empirical follow-up; DF2-4
      remains immutable pre-hook evidence
      **CLOSED 2026-08-26 — both commits integrated.** Research `71b81a8e` merged into research main
      (`b76d577b`, no conflicts, +5 files; 10/10 tests) and root `e0376ea1` into root main
      (`26a8bcab`, +2 files; 604 passed, 1 known env failure). DF2-4 stays immutable pre-hook
      evidence; the first DF2-5 campaign is the empirical follow-up and is tracked as SC49-G2,
      not by this row ✅ 2026-08-26**

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
- [x] SC11 Survey the remaining candidate sources named in the register ✅ 2026-08-26 — **priced-and-declined, both sub-sources, verdict recorded rather than carried.** (1) llama-bench: the bulk corpus was already REJECTED by SC6-PRICE (0/200 full tuple); the scout subset is 3 records all from 2026-08-12 with no successor producer since — below any adapter's pay line. (2) speech kernels (whisper/qwentts): frozen production serving paths; examination shows no protocol-admissible measurement corpus exists to sample — runs are serving telemetry, and pricing requires a corpus. If a speech benchmark protocol or a new llama-bench scout campaign is ever declared, re-file a wiring row at that moment (the SC9 rule)
- [x] **SC53 — Wire the INF-70 CPU decode roofline ledger on the write side before its first run (filed 2026-09-02).** ✅ 2026-09-02
      — adapter `scripts/vidya/adapters/inf70_roofline_ledger.py` (13bb588c): one ClaimTuple per llama-bench arm / readbw kernel row /
      barrier row through the existing measurement ladder, no new grading rule; strict reader refuses by name what it cannot rederive
      (missing bench log, arms.log/bench-log row disagreement, absent or mismatched `artifact.sha256`); 37 tests + a real-corpus replay
      pinning identity. Write side wired the same day (7d2d2e1d): `cli.py ingest inf70`, dry-run over the corpus = 147 rows / 441 frames,
      zero arm refusals; producer gap closed (bced4565).
      [`cpu-decode-roofline-program.md`](../active/cpu-decode-roofline-program.md) C0/C5/B1/D0 produce the numbers every later
      keep/revert in that program will cite: read-only DRAM bandwidth under the decode recipe, the clean-build
      re-anchor sweep (t1/t48/t64, uniform IQ4_XS, OMP stack on/off), the per-path achieved GB/s and the per-node
      µs floor. Emit one `ClaimTuple` per arm beside the run directory (artifact path + SHA, build id, full recipe,
      `-t`, n, reps, box-state capture) via the existing measurement ladder — no new grading rule. Prepared by the
      INF-70 owner; applied here per ruling (b). Source-table row: `scripts/vidya/adapters/README.md`.

- [x] SC13 **E5 cell affinity-preflight artifacts need a write-side ClaimTuple hook** (filed 2026-08-12
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
      **STATUS 2026-08-26 — priced, and the honest verdict is that volume never justifies an adapter**
      (recorded per the row's own clause rather than left open). The entire corpus is 28 artifacts, the
      newest from the filing day itself (2026-08-12T08:07Z) and every one predates the attested fields
      the change added; zero preflights have been written since, because Stage-B cells do not run while
      autopilot is parked. The locator lesson (run-level, not file-level) stays on record. Re-file this
      row at the first Stage-B batch after the freeze lift, when a successor corpus with the attested
      fields exists to price ✅ 2026-08-26

### Consumption — opened 2026-08-10 (operator question: what consumes these beliefs?)

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
- [x] SC12-ENTRY **Two precise claim-04 citations of intake-110#record remain blocking, and they
      are correct.** The entry's
      `key_claims` still records the stage-1 "+9–16 points" text while its `claim_corrections`
      refutes it — support at `Hinted`, opposition at `Verified`, which is exactly what the record
      says. Clearing them means amending the entry, a dive-owner call, not a citation fix. Until
      then `cite-check` exits 3 on a true finding — and it did so correctly until this closure.
      **CLOSED 2026-08-26 (dive-owner amendment, this session):** `key_claims[4]` amended to the
      corrected position ("57-59% token compression on MATH-500 with +0.0 to +3.3pp accuracy delta
      (authors' revised Table 2); the original +9-16 points accuracy figure was retracted by the
      authors"), the claim-4 `claim_corrections` effect flipped `overturned → unaffected` (the
      intake-1020 fold-in pattern — the claim now STATES the corrected position, so the correction
      is history, not a live refutation), and `reported_results[0]` aligned. Ledger rebuilt
      (gen-2b, same 12,479-frame corpus, checkpoint re-emitted); `clm_intake_110_04` now folds
      `pro=Hinted/Located con=Q0/T0`; the two precise claim-04 citations and the bare `intake-110`
      mentions (knowledge-management.md, this file) all clear. The entry's dive history stays in
      git and in the correction note

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

    **Only ONE correction demands a primary-source dive** (`intake-547#record`, whose text says its claims
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
- [x] SC16 **Is `uncertain` the right default for a per-claim verdict?** ✅ 2026-08-26 — **DECIDED:
      KEEP-conservative, chosen not inherited.** An entry-level overturn is evidence about the
      ENTRY, and a per-claim `uncertain` means the dive did not clear the claim — recording
      inability-to-decide as absence-of-refutation would read "could not tell" as "found fine", the
      exact absence-of-evidence category error this program exists to catch. `clm_intake_922_01`
      stays the live instance (`pro=Q0/T0 con=Verified/MachineLocated` in the 2026-08-26 fold). The
      failure mode of keeping is a true statement about the entry; the failure mode of clearing
      would be a verdict the dive never gave. `unaffected`/`narrowed`/`reattributed` remain the
      affirmative clearances; `uncertain` deliberately is not one. Decision and reasoning written
      into the `apply_claim_verdict` docstring
- [x] SC17 **`fold` does not exclude frames dated after `as_of`.** ✅ 2026-08-12 (`auditor`) — design chosen per the row's own recommendation + spec §fold-purity: `fold` stays pure (created_at remains publication metadata it never reads); the guard is an **append-time refusal** in `ledger.py` (`FrameStampError`, `MAX_FUTURE_SKEW_SECONDS=300`), tolerating absent/malformed stamps (frame-construction's contract; maintenance frames carry none) and past stamps (history untouched — the 895 incident frames are correction-queue territory, out of SC17 scope). 6 new tests both directions incl. yes-paths (`tests/vidya/test_ledger_future_stamp.py`); full vidya suite 371 green. A frame stamped in the future
      takes effect immediately at any earlier `as_of`, which is how 895 future-stamped frames from
      the 2026-08-10 date incident still fold in, and how a frame this session mis-stamped
      `2026-08-11` applied on 2026-08-10 before being re-stamped. Two defensible designs — ignore
      `created_at` entirely (it is publication metadata, and `as_of` ranges over the evidence
      frontier) or refuse future frames at append time. What is NOT defensible is the current
      accident of neither. Pick one; an append-time refusal is the cheaper guard

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
      producer-authored rows. The r15 terminal one-task/K-Search compatibility pilot reused this
      writer and emitted the same two producer-authored correctness/timing-validity rows under
      diagnostic/no-ranking authority; it needs no new source class or grading rule. Older receipts
      remain untouched.
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

### Decision queue — ALL SETTLED 2026-08-09

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

### Reporting

- [x] **SC46 ✅ 2026-08-22 — wired.** Writer `chat_template_ab_capture.py` + strict reader
      `chat_template_ab.py` (registered `chat-template-ab-measurement`), tuple carries the template
      axis (`template_sha256` per arm) alongside model/quant/kernel/serving/sampling/paired-flips;
      well-formed rows grade Witnessed/Attested via the shared ladder, zero local grading logic
      (no-private-ladder sweep passes over both files). Pre-hook runs emit zero rows per the DF2-4
      precedent. Details: CT-8 in `qwen-chat-template-evaluation.md`.
      — wire the CT-1 chat-template A/B into the belief kernel on the write side** (filed
      2026-08-21 at first-measurement time; first run in flight the same hour). Producer: the CT-1
      runner (per-question JSONL + per-suite summary, scored by orchestrator `debug_scorer`).
      Tuple must carry (model, template_sha256, suite, n, sampling config, kernel/binary identity,
      paired-flip counts) — the template axis is the whole point, per the E-7 amendment. Source-table
      row: `scripts/vidya/adapters/README.md`; consumer task: CT-8 in
      `handoffs/active/qwen-chat-template-evaluation.md`.

### SC56–SC60 — Prove2Me intake wave (filed 2026-09-07)

- [x] **SC56 — statement-binding precondition for any grade above `Judged`.** ✅ 2026-09-07 (`51f9ef61`) — unbound verifier caps at `Judged`, bound at `Verified`; T passed through untouched; a FALSE identity binding is refused, never downgraded. 51 tests, 14 mutants, 0 survivors. A verifier-derived
      tuple may be graded above `Judged` only when the adapter records **what proposition the
      verifier actually decided** AND that proposition is bound to the claim being asserted. Absent
      the binding, cap at `Judged`. Evidence: `intake-1307#00` — in one real pipeline an automated
      check labelled 73.6% of proved artifacts non-trivial-and-correct while a manual audit put
      faithfulness at ~43% — and `intake-1307#05`, the certificate "does not certify individual
      mathematical truth". **Cite the precise `#NN` forms, never the whole entry**: that entry's
      headline number is a reweighted projection from a 45-example single-annotator audit and is
      admissible as an existence proof that the gap is large, never as a rate.
- [x] **SC57 — `decided_proposition` on the verifier-class adapter contract.** ✅ 2026-09-07 (`fe91818d`) — Extend the source
      table in [`scripts/vidya/adapters/README.md`](../../scripts/vidya/adapters/README.md) so a
      verifier adapter must emit *what the check asserted*, not only a boolean, and refuse
      registration of one that emits pass/fail alone. **Project, not grade** — no new ladder
      (`docs/design/vidya-pilot-spec.md` §4.7). Retrofit is impossible for the usual reason: a
      proposition invented on read claims warrant the original check never captured.
- [x] **SC58 — verify judgment frames are pinned to the digest of the artifact they judged** ✅ 2026-09-07 (`fe91818d`) — **the check FAILED: this was a P1 defect, not a passing property.**, and
      transition dirty when that digest moves. §5.2 plausibly covers this already, so this is a
      check, not a build; a negative result is a P1 defect. Source: `intake-1308#03` — "a read-back
      of an older version of the code is worse than none, because it testifies about the wrong
      artifact." Note that the source platform enforces this only as prose, and stores no hash of
      the audited text — which is exactly why it cannot detect its own violation.
- [x] **SC59 — optional free-text `reason` on `supersedes`/`retracts` frames** ✅ 2026-09-07 (`fe91818d`) — zero grade effect is structural, not asserted., surfaced on the
      belief's review path. **No grade effect**, deliberately — same rule as corrections, for the
      same reason (we know the ground shifted, not by how much). The consumer is a citer told a
      frame was superseded who currently learns nothing about *why*, and so repeats the rejected
      reasoning at full price. Precedent: Prove2Me makes `reason` mandatory on every milestone
      re-link specifically so solvers do not re-walk rejected paths (`intake-1299#record`).

- [x] **SC62 — wire FM-5 fan-out outcome accounting into the belief kernel.** ✅ 2026-09-07 — `scripts/vidya/adapters/fanout_outcome.py`, 5 tuples, all **`Judged/Located`**: no protocol id exists for transcript forensics and none was invented, so the ladder caps it as an OBSERVATION. The bounds are structurally non-optional — `value` is a `Bound` whose `.point`/`float()`/`int()` RAISE, and because `to_frames` emits only the generated claim TEXT and never `value`, the guard is on the text (a guard on `value` alone would be inert exactly where it matters). **86.5% is the LOW end of a band whose high end is 99.7%**, the two ends resting on different evidence, not different confidence. FM-5 landed
      2026-09-07 (`5f1c4ba4`) and **produces measurements**: per-subagent outcome buckets with token
      totals over a committed, non-reproducible corpus. Filed here the same day per CLAUDE.md —
      wiring the WRITE side is cheap and permanent, retrofitting the READ side is impossible, and
      `benchmarks/results` (4,562 files, no write-side hook, 0 of 200 sampled carrying a usable
      tuple) is the standing proof. **Project, never grade** — no new ladder (§4.7).
      **The bounds must ride in the tuple or the projection is a lie:** `produced-and-used` is an
      UPPER bound (2,094 of 2,265 verdicts rest on a substring hit; the proven floor is
      `git-landed` = 171), `blocked = 0` is a floor not a finding, token totals are
      provider-cumulative and dominated by a handful of very long threads, and 501 `unknown` must
      stay unfolded. A tuple that reports 86.5% without its band is not a projection of this
      measurement — it is a different, stronger claim than the one that was made.
      Source-table row added to `scripts/vidya/adapters/README.md` (state: UNWIRED).

- [x] **SC61 — `claim_statement_binding/v1`, the producer for SC56's `attested` binding.** SC56
      (below/adjacent) accepts two binding kinds: `identity`, machine-checkable by normalized string
      equality, and `attested`, a human judgment that a claim follows from a proposition the checker
      decided. **`attested` has no producer**, so only `identity` is reachable in practice and the
      more useful half is inert. Build the frame type parallel to `claim_alias/v1` — human-authored,
      with the fold only *applying* it, never deriving it — plus the review worksheet and the fold
      pass. Filed separately on purpose: this is a **build**, and letting it ride inside SC56 would
      have turned a one-function cap into a new frame type, a worksheet and a fold pass under one
      checkbox. Surfaced by the SC56 design pass, 2026-09-07.
      **✅ 2026-09-08 (`5d7f14be`) — landed.** New `scripts/vidya/statement_binding.py` +
      `cli.py binding-candidates`/`binding-emit`: frame type `epyc.vidya/frame/claim_statement_binding/v1`
      asserts `{claim_id, decided_proposition}` verbatim with human reviewer + worksheet digest in
      provenance (parallel to `claim_alias/v1`); candidates only where a binding is missing
      (identity-eligible pairs are never proposed — the machine needs no human); worksheet rows are
      `pending` until a human `follows` with a named reviewer. Fold pass: `binding_ref` must resolve
      to a LIVE binding naming the SAME claim and the SAME proposition (claim_tuple's own
      normalization), else FoldError — a false attestation is refused, never downgraded; a binding
      naming a claim absent from the ledger is refused (it cannot create a belief — SC70's shape one
      level up); retracting a binding withdraws it; resolved bindings surface on
      `FoldResult.statement_bindings`. 20 unit tests + 1 CLI e2e.

### SC65–SC68 — research-intake wave 2026-09-07 (filed 2026-09-07)

- [x] **SC67 — wire `tulving_episodic` on the WRITE side before M-12a runs** (`intake-408#record`).
      ✅ 2026-09-14, root `baaa6741` (+ the research-side CLI hook in `dcb769c1`).
      `tulving_episodic_capture.py` is the write side the scorer calls at score-time
      (`score_tulving_run.py --belief-measurements --arm <none|retrieved|full> --variant … --chapters …`);
      `tulving_episodic.py` is the strict reader, registered as `tulving-episodic-measurement` under
      the shared `measurement` ladder — it projects and `claim_tuple.grade()` decides, with a test
      asserting no `register_ladder` in the adapter. TWO claims per arm, never one: Simple Recall
      (`get=="all"`) and Chronological Awareness (`latest` + `chronological`) are disjoint subsets, so
      separate metric ids and `reps` = the subset each metric is about. Rows carry run id, variant +
      chapter count, arm, scorer version, n scored, metric direction, the five Simple Recall bins with
      bin 0 included, the bin basis actually used, and the count of tau questions failed closed for
      partial coverage. **`scorer_version >= 2` is refused at BOTH ends** (a pre-M-12e figure is a
      different quantity under the same name: 0.5530 vs 0.5684 on the same run) and `--arm` is
      mandatory and never inferred. **Locator = the run**, pinned by a test. Pre-hook runs — including
      `20260619_141212` AND its 2026-09-14 re-score, whose arm the harness never recorded — emit zero
      rows, permanently. 22 tests in `tests/vidya/test_tulving_episodic_adapter.py`; full vidya suite
      1068 → 1092 passed with the 2 pre-existing failures / 12 pre-existing errors unchanged; source
      row updated in `scripts/vidya/adapters/README.md`.

- [x] **SC68 — wire the BEAM adapter on the write side AT AUTHORING TIME, and record BOTH folds**
      (`intake-1337#record`). File at adapter-authoring time (CME-1), not after the first run. The
      **BEAM-fold headline is the claim**; the rubric-item micro-average and the binarised pass count
      are **recorded context in the same tuple**. A claim tuple that does not record WHICH fold
      produced the number cannot be compared to any external BEAM figure later — this wave's dive is
      the proof (49.0 vs 55.7 on the same run). Source-table row in
      `scripts/vidya/adapters/README.md`; task here. Project, do not grade.
      ✅ 2026-09-15 — root branch `sub/sc68-beam-write-side` + research `5fb27644` (CME-1/CME-2).
      `beam_memory_capture.py` is the write side `score_beam_run.py --belief-measurements --arm …`
      calls at score-time; `beam_memory.py` is the strict reader, registered as
      `beam-memory-measurement` under the shared `measurement` class — it projects and
      `claim_tuple.grade()` decides (a test asserts no `register_ladder`). ONE claim per arm, the
      BEAM-fold headline; the rubric-item micro-average and binarised pass count ride in `extra` of the
      same tuple. The validator re-derives `value` as the mean of the ten recorded per-ability columns,
      so the other fold cannot be written under this metric; fewer than ten columns is refused. Judge
      model + prompt version + `question_in_judge_prompt` are mandatory and part of id and locator
      (`beam:<run>:<split>:arm-<arm>:judge-<model>`). 27 tests in
      `tests/vidya/test_beam_memory_adapter.py`; full vidya suite 1120 passed, the only failures being
      the pre-existing `test_autokernel_serving_feedback` set (1 failed / 12 errors, `EPYC_RESEARCH_ROOT`
      unset). Source row updated in `scripts/vidya/adapters/README.md`.

### SC75 — VB-INF70-ARMS: the INF-70 serving-harness arm records (filed 2026-09-08)

Source: **INF-70** (CPU decode roofline) closed 2026-09-08 and its evidence base is now in git —
`data/inf70-retest1-2026-09-08/` in `epyc-inference-research` at commit `1780fa7b` (on main as `56ef1404`), branch
`inf70/evidence-2026-09-08`. Its serving-harness **arm records** are a measurement source this substrate
does not read. Filed **immediately**, per the standing rule: wiring the write side is cheap and permanent,
retrofitting the read side is impossible. Source row added to
[`scripts/vidya/adapters/README.md`](../../scripts/vidya/adapters/README.md).

- [x] **SC75 (VB-INF70-ARMS) — wire the INF-70 serving-harness ARM records on the WRITE side, and make the
      per-arm CONTENTION VERDICT the field the hook exists for.**
      **The load-bearing point:** the write-side hook that matters is **the per-arm contention verdict**. It
      is a property of the host *during* the arm and is **unrecoverable after the fact** — a verdict invented
      on read claims warrant the original run never captured. Everything else in the tuple (model + GGUF
      digest, kernel commit + binary version, launch recipe **including the `GGML_NOHUGEPAGE_PROCESS` state**,
      pinning, n, between-launch sd, metric direction) can at least be argued from artifacts; the verdict
      cannot.
      **Pre-2026-09-07 arms are WORSE THAN ABSENT.** The sampler read cores **184-191 as disjoint** until
      2026-09-07, so the labels already on those arms are **WRONG, not merely missing** — a false negative
      that reads as a clean arm. They must emit **zero rows** and must never be reconstructed on read;
      back-filling them would put incorrect contention labels behind a graded ladder.
      **Locator = the arm/launch the producer ran**, never a per-sample file (SC6-HAZARD class).
      **Do NOT write a new grading rule.** An adapter **projects** its native record into a `ClaimTuple` and
      `claim_tuple.grade()` decides (`docs/design/vidya-pilot-spec.md` §4.7); the carrier is shared, each
      source class has exactly one ladder, and `register_ladder()` refuses a second.
      **Same class as autokernel R23-60** (`autokernel-rebuild-program.md`) — the serving path proves no GPU
      residency because `serving.py` samples nothing. Both are **write-side hooks that cannot be
      retrofitted**, and both should be recognised as one failure mode rather than two coincidences.
      Trigger: the next serving-harness arm produced on either surface. Zero compute to file; the adapter is
      ~40 lines of projection.
      ✅ 2026-09-16 — root `685a72bc` (branch `sub/memeval-root-20260916`): `inf70_serving_arm_capture.py`
      (writer; CLI called at ARM END → `<label>.belief_measurements.jsonl`) + `inf70_serving_arm.py` (strict
      reader, `inf70-serving-arm-measurement` under the shared `measurement` class). One tuple per arm
      (`reps` = 1 launch), verdict CONTENDED/CLEAN with DIRECT and SMT-SIBLING counts kept separate, in the id
      and the locator. The writer refuses: a missing or empty coresidency, CLASSIFY-ERROR, legacy sampler
      vocabulary, an arm start before 2026-09-07, and a capture more than 1 h after the rows file was written.
      A forged pre-fix row is voided on read. 36 tests. A mutation that disables the date gate fails 3 of them.
      The real 2026-09-07 HARNESS-1 arms have no sidecar and project zero rows. **Producer hook still to
      add:** the harness scripts are scratch-only (`/mnt/raid0/llm/tmp/inf70/agents/harness1/arm_{hot,cold}.sh`).
      The next serving-harness author adds, after the per-arm `coresummary.sh` line, a single call:
      `python3 <root>/scripts/vidya/adapters/inf70_serving_arm_capture.py --run-dir "$OUT" --label "$lbl"
      --launch-json "$OUT/$SESS.launch.json" --arm-started-at "$(date -u -d @$A0 +%FT%TZ)"`. It needs a
      `launch.json` written once per launch (launch_id, model_path, gguf_sha256, kernel_commit,
      binary_version, launch_recipe{env,args}, pinning, bench_cpus).
      ✅ 2026-09-16 — **producer hook wired (VB-WIRE-2, `sub-own`)**: harness promoted to root
      `scripts/inf70/harness1/` (`b57b1efb`, verbatim), capture wired in `3c5a4b30`
      (`sc75_capture.sh` + `sc75_launch.py`, sourced by both arm scripts; the call sits right after the
      per-arm `coresummary.sh` line; `launch.json` comes from the live server's `/proc` environ and
      cmdline; a missing field or a writer refusal is loud and never aborts the arm). The scratch copies
      under `/mnt/raid0/llm/tmp/inf70/agents/harness1` got the same edit (originals kept as
      `*.pre-sc75-20260916`). Test: `tests/vidya/test_inf70_harness_sc75_hook.py` (7): a fixture arm goes
      through the capture step and `ingest inf70-arms` projects 1 row.

### SC69–SC73 — kernel audit survivors, 2026-09-07 (filed 2026-09-07)

- [x] **SC69 (P1) — `Attested` never verifies the digest it is named after.** `claim_tuple.py:189`
      length-checks `attestation_sha256` (64 chars) and `:350` branches on its mere presence;
      `hashlib` does not appear in the file at all. Demonstrated: `attestation_path="MEASUREMENT.md"`
      with `attestation_sha256="0"*64` grades **`Witnessed/Attested`** — the top of BOTH axes, on a
      digest of nothing. The T ladder's own contract is that `Attested` means the artifact was
      re-read and matched; today it means a 64-character string was typed. Fix is not merely "call
      `hashlib`": `grade()` is a **pure function** and hashing is I/O, so the digest check belongs at
      the adapter/write boundary with the result carried in the tuple — decide that placement first,
      because putting I/O inside `grade()` would make grading unreproducible from a stored frame.
      Pair every fix with the mutation that reverts it (`"0"*64` must not reach `Attested`).
      **✅ 2026-09-08 (`5d7f14be`) — P1 closed.** Placement decision: `grade()` stays pure —
      verification happens at the adapter/write boundary and the result is CARRIED in the tuple:
      new field `attestation_verified: bool | None` (`None` = never checked → can never reach
      `Attested`; `True` = digest recomputed against the artifact bytes at write time and matched;
      explicit `False` is refused — an admitted mismatch asserts two contradictory facts).
      `claim_tuple.verify_attestation()` does the I/O for boundaries that want it. `Witnessed/Attested`
      now requires the carried `True`; hashed+present+unverified lands `Witnessed/Anchored` with the
      "attestation sha256 never verified against the artifact's bytes" reason. Ten wired producers
      carry the recompute result (sealed_manifest, measurement_record, autopilot_journal,
      autokernel corpus/evaluation_event/property, memento_lora, pareval, chat_template_ab,
      contention_matrix, eval_tower_band). The REAL sealed corpus and REAL autopilot writer keep
      `Attested` through genuine recomputation; receipt rows whose digest cannot be re-derived from an
      artifact in hand grade honestly `Anchored` until their write path implements its own recompute.
      Mutation-pinned: `"0"*64` no longer reaches `Attested`. 12 red-first tests.
- [x] **SC70 — `fold.py:530` `claim_depends_on` never calls `claims.add`.** A `depends_on` edge into
      an id the ledger has never otherwise seen registers no claim, so the dependent silently has no
      belief to alert on. This is the same file whose `chain_grade` the wave already found to be a
      single unreferenced definition — the claim→claim plane is thinner than it reads.
      **✅ 2026-09-08 (`5d7f14be`).** `FT_DEPENDS` now canonicalizes and `claims.add`s the dependent.
      Red-first: a dependent seen only via a depends_on edge had no belief; withdrawal alerts for it
      vanished; discharge classified the entry discharged while its only dependent never existed. 3
      tests in `tests/vidya/test_vidya_depends_on_fold.py`.

- [x] **SC72 — `gate.py:121` manufactured corroboration + `frames.py:139-142`/`:90` presence-only
      subject validation.** The gate can count a single source twice as corroboration; `frames.py`
      validates that a subject is *present*, not that it is *well-formed*, so `sha256:aa` passes one
      layer below where SC69 bites. Filed together because the digest-shaped-string-is-not-a-digest
      defect appears at both layers and a fix at one alone leaves the other reachable.
      **✅ 2026-09-08 (`5d7f14be`).** (a) Fold keys that name no source map to one shared
      `UNNAMED_SOURCE_KEY` instead of minting a pseudo-source per evidence label; (b) the gate's
      disjoint-supports fallback counts an unaccounted belief as ONE unnamed source, never its labels;
      (c) `frames.validate_frame` refuses any subject digest that is not exactly
      `{sha256: 64-hex}` and any unnamed subject. One existing test encoded the defect (two
      source-less paths satisfied a 2-source policy) — its fixture now names two real sources, and a
      mutation case pins that unnamed paths abstain. 11 red-first tests.
- [x] **SC73 — `ledger.verify()` returns clean on an empty or deleted ledger.** A verifier that
      passes on the absence of the thing it verifies is the fail-open shape
      (`feedback_fail_open_defaults_conceal_their_own_corruption`): the strongest possible reading of
      "chain=OK" is produced by having no chain. Require a non-empty frontier and a declared expected
      count before reporting OK.
      **✅ 2026-09-08 (`5d7f14be`).** `verify(expected_count=None)` now reports problems for a
      missing/empty ledger and flags a ledger shorter than a declared count; `cli.py cmd_verify`
      passes the newest published checkpoint tree size as the declared count (a ledger truncated to a
      consistent prefix now fails chain — same-length rewrites remain the L1 case). Live-ledger smoke
      after the fix: frontier 13,141, chain OK, checkpoints OK. 5 red-first tests in
      `tests/vidya/test_ledger_empty_verify.py`.

### VB-GPU-PREP — write-side hooks for three GPU-runner producers (filed 2026-09-16, sub-gpu-prep)

- [x] **VB-PRB-T4 — wire `eval_tale_budget.py` at write time** ✅ 2026-09-17 (closed by the main session: write-time capture ran through the hook on the first PRB-T4 run, 24 rows ingested, and the driver is on research main `0b295a25`. The sample-scope caveat is tracked separately in VB-PRB-T4-CAVEAT.) (research `a454b7fd`, ported as
  `76f5132b`, on research `main` via `a280853d`): project `.jsonl` + `.meta.json` + `.summary.json` per suite×arm into ClaimTuples
  (accuracy; answer-only AND incl-estimator tokens/latency; budget_unit, temperature+seed, served GGUF identity,
  chat_template_kwargs) BEFORE the PRB-T4 run. Locator = the run×suite×arm, never per question. No new grading rule.
  - 2026-09-16 (sub-runner-adapters): root writer + strict reader ported onto origin/main and wired as
    `cli.py ingest tale-budget` (end-to-end test in `tests/vidya/test_ingest_sources.py`). The writer now also
    emits answer-only latency. Rows project `protocol_id=""` (no TALE protocol is codified), so tuples cap at
    `Judged/Located`. The writer reads the per-question `.jsonl` + `.meta.json`, not `.summary.json`; its formulas
    match `summarize()`. Left unticked until the driver (research `sub/gpu-runner-20260916`) merges.
  - 2026-09-17 (sub-gpu-collect2): **first run emitted through the hook.** PRB-T4 wrote 3 per-suite
    `.beliefs.jsonl` sidecars (research `b4d38ebc`). `ingest tale-budget` projected math and olympiadbench:
    24 rows, 0 refused. The livecodebench sidecar was withheld because its accuracy uses the vacuous
    `substring 'def '` scorer. This needs a tuple-level exclusion or a scorer fix; do not ingest it as-is.
    Still unticked: the driver has not merged.
  - 2026-09-17 (sub-vb-wire): **the driver blocker is cleared.** `prb_t4_tale_gpu.py` is on research main
    (`0b295a25`, VB-RUNNER-PATHS), and the harness now refuses the vacuous code oracle. Left for the owner
    to close.

- [x] **VB-REVIEW-F1 — wire review_f1 `_summary.json` (EV-13b) at write time** (research `e70b6974` → `726e2676`;
  the `_summary.json` producer `ev13b_run.py` is on unmerged `sub/gpu-runner-ev13b-20260916`): micro
  P/R/F1 with n_runs≥3 and sd, reader AND judge identity, `golden_manifest_checksum`, matcher-spec sha,
  `cross_family_ok`, judge-swap delta. Refuse a summary with judge==reader or no manifest checksum. Locator =
  reader model/quant × judge × run, never per finding.
  - 2026-09-16 (sub-runner-adapters): root writer + strict reader ported onto origin/main and wired as
    `cli.py ingest review-f1` (end-to-end test). The field names match `semantic_judge.py score` at research
    `0627a5d9`. Rows project `protocol_id=""`, so tuples cap at `Judged/Located`. Left unticked until
    `ev13b_run.py` merges.
  - ✅ 2026-09-16 (sub-gpu-collect2): **first run landed through the hook.** `ev13b_run.py` merged to research main
    (`59d0bc73`). The EV-13b run emitted both `_summary.semantic.<judge>.beliefs.jsonl` sidecars at write time, and
    `cli.py ingest review-f1` projected 2 units → 6 rows (0 refused) into the shared ledger. Evidence: research `aac025a4`.

### VB-EVCONF2 — eval-tower confidence-source calibration axes (filed 2026-09-16, sub-evconf2)

- [x] **VB-EVCONF2 — give `confidence_source_compare.py` a `belief_measurements` writer before the EV-CONF-2
  math probe runs.** ✅ 2026-09-16 — root `c8c68662` (branch `sub/evconf2-root-20260916`, merged at `1e1de5fb`, fix `4fe47225`):
  `scripts/vidya/adapters/confidence_source_capture.py` (writer and CLI, run right after `compare --out`) and
  `confidence_source.py` (strict reader), with 15 tests; the conformance suite passes. It emits one row per
  arm × source × {AUROC, ECE, reweighted ECE}. The resolved spec state is carried in `extra.spec` and stated
  in the claim. The writer refuses when an identity's `eval_batch_id` does not match the report's sidecars.
  The report is observation-grade, so `protocol_id` is empty and the shared ladder answers `Judged/Located`.
  The probe runner preamble calls it (orchestrator `7cc118da`, merged at `88a2902d`). Original task text: Orchestrator branch `sub/evconf2-20260916`. Today the tool emits only an observation-grade
  JSON report. Emit one row per run × role × confidence source, carrying:
  - AUROC with its CI (higher is better) and ECE (lower is better, `closed_top_bin_stat_tests`)
  - n, the sidecar sha256s, dataset sha256 and seed
  - model/quant/kernel/serving identity
  - the speculative-decoding placeholder fraction. A spec-on run's geomean is saturated by fake p=1.0 tokens,
    so it must never read as the same measurement as a spec-off run.

  Add a strict reader under `scripts/vidya/adapters/`. It only projects; the grading stays with
  `claim_tuple.grade()`. The E7c and EV-4c aggregates are pre-hook: zero rows, never reconstructed on read.

### P5c promotion gate — requirement-4 evidence (executed 2026-08-26, gen-2 ledger)

Verdict: **ITERATE (not promote).** Requirement 4 is now EXECUTED for the first time — the
"never started" evidence gap (§4b of `research/deep-dives/vidya-p5c-evaluation-and-decision.md`)
is closed — and the run surfaced two eval-harness defects, now fixed. Requirements 1–2 remain
operator-gated. No termination indicator (§5) fires.

**Requirement-4 evidence** (as-of 2026-08-26, floor Verified/Anchored, count 6, 12,479-frame
gen-2b ledger), after the harness fixes (`live_eval` now indexes `evidence_opposes_claim` frames
by source, and never-supported dependents are carved out, not failed):

- default draw: **161/161**, invalidation_recall 1.0, discrimination 1.0, harmful 0, uncoverable 1011
- verified-only draw: **155/155**, recall 1.0, discrimination 1.0, harmful 0, uncoverable 537
- The pre-fix run's 3 harmfuls were harness artifacts, engine exonerated: `_index_claims` indexed
  only `evidence_supports_claim` frames, so a source retraction never retracted its dive
  refutations; the three failing claims were con-only. The second gap: 13 declared `depends_on`
  dependents of dive-overturned intake-664#record failed "propagated" because OP-11 alerts are already
  active pre-mutation (source never had support) — the eval expectation was unsatisfiable for
  that class; the carve-out counts them, never scores them.
- Uncoverable bucket on gen-2 ledger: 1011 / 537 (was 527 / 272 on gen-1) — larger citation graph,
  same open question (no cross-entry evidential edge).
- Gold corpus re-measured: **28/28**, harmful 0 (4 rounds, unchanged). Test suite: 598 passed
  (+1 pre-existing environmental failure: `test_autopilot_journal_adapter` needs the orchestrator
  `src` package). Ledger: frontier 12,479, chain=OK, checkpoints=OK. Corrections: 0 unadjudicated.

**Requirement status:**

| # | Requirement (§4) | Status |
|---|---|---|
| 1 | Anchor the claims that get cited (P2d) | MET at B semantics — machine-anchor admissibility RATIFIED 2026-08-26 (operator): option B, the implemented §4.2 amendment; machine-located spans grade `MachineLocated` (quote-pinned, unreviewed), never `Anchored` without a human reading. Decision recorded in `vidya-p5c-evaluation-and-decision.md`; coverage backlog (cited entries unanchored) is write-time growth, tracked not gated |
| 2 | Cross-entry claim identity (R4b) | MET — operator passed all 43 pairs (`node`, 2026-08-26): 18 same / 25 different; 17 `claim_alias` frames emitted (one transitive group 144_03=254_04=411_04); worksheet `.vidya/aliases-worksheet.yaml` pinned by frame digests |
| 3 | Query log + obligation disposition (R5b) | MET |
| 4 | Re-run the eval against the live-ledger corpus | EXECUTED — 161/161 + 155/155 above; harness defects fixed and re-run on the unchanged ledger |

**VERDICT 2026-08-26: PROMOTE.** All four requirements met (the alias-bearing draws needed
one final harness fix — alias resolution in `score_live_family`, regression-tested — and then
came back clean: 161/161 and 155/155, harmful 0). Decision recorded in
`vidya-p5c-evaluation-and-decision.md` §6 with the full evidence block; shadow status ends.
The standing open rows below (freeze-gated producer triggers) are tracked work, not gate
conditions.

### SC87 — AutoKernel spawn-lineage write-side capture (filed 2026-09-17)

- [x] **SC87 — wire RB-lineage telemetry on the WRITE side before its first run.** The AutoKernel journal/run producer emits a producer-authored, self-hashed ClaimTuple-shaped sidecar binding run id, parent/run identity, logical branch id, ordered width×depth trajectory, source commit, and immutable run-artifact digest. A strict reader may consume only post-hook sidecars and delegates grading to the existing `claim_tuple.grade()` ladder; it must not reconstruct missing tuples from old journals. This is a verified lineage finding, not a performance measurement or promotion warrant. Source: `autokernel-rebuild-program.md` RB-lineage telemetry (intake-1439#record). Write-side producer `a6288858` is tested; the separate strict read-side consumer remains pending.

### VB-AK-CODEGEN — retained AutoKernel codegen diagnostics (filed 2026-09-17)

- [x] **VB-AK-CODEGEN — bind retained-variant codegen summaries on the WRITE side before the first governed use.** For `epyc.autokernel.codegen_summary.v1`, capture the executed KEEP/attempt identity, exact retained source commit/tree, backend, compiler/toolchain and build-recipe identities, immutable code-object hashes, summary digest, and explicitly unavailable fields in a producer-authored ClaimTuple; project through the shared `claim_tuple.grade()` ladder on read. A disassembly/instruction-mix observation is diagnostic only: it is neither a throughput measurement nor a correctness or occupancy claim. HIP/gfx90a evidence must not be described as PTX/SASS/CUBIN. Source: `autokernel-research-loop.md` AK-PORT-3. **2026-09-17 live source-KEEP path:** research `09bc8fc3` writes the immutable sidecar and tuple; root `7e46f3ca` verifies it through the shared grader. Runtime-only KEEP has no new compiled object and reports that fact; legacy campaign summaries are pre-hook. No throughput or occupancy authority was added.

### Research Intake Update — 2026-09-17 (typed-decision / PAW measurement wiring)

**VB-TDP-1 disposition — read side implemented; remaining write-side envelope consolidated into `VB-RI-SCREEN-1`.** Root commits `412ab689`, `effa71c1`, `1d0bf68d`, and `28edb2b8` provide the registered `typed-decisions-measurement` adapter, CLI/source registration, strict study and metric handling, tests, and projected TD-2/TD-3/routing receipts. This does not complete the original write-side promise: the current producer writes study receipts and explicit metric directions, but it does not yet mint the generic self-hashed run envelope, durable run identity/location, category, and protocol fields required for prospective decision-bearing evidence. `VB-RI-SCREEN-1` owns that missing producer envelope; `VB-TDP-EXT` owns the bounded external/shadow projection. Do not duplicate the existing adapter or backfill old receipts. (Consumers: `typed-decision-plane.md` RTG-56 and `paw-compiled-specialists.md` INF-76.)
*Verified 2026-09-26 (operator-directed tidy):* the 2026-09-17 progress note's "Belief-kernel write side wired first (VB-TDP-1)" (`progress/2026-09/2026-09-17-intake-jev-sageattn.md`) describes this READ-side adapter plus a `metric_direction` producer fix; no typed-decision producer in `epyc-orchestrator` `src/typed_decisions/` mints a self-hashed ClaimTuple or calls `research_screen.write_receipt()` (orch `6a712866`). The write side exists as the root-side `epyc.research_screen.v1` writer (VB-RI-SCREEN-1 / VB-TDP-EXT) awaiting its first prospective typed-decision shadow producer; historical receipts stay unbackfilled.

### VB-EXL3-CPU-GFX90A — prospective EXL3 CPU/MI210 evidence (filed 2026-09-25)

- [x] **VB-EXL3-CPU-GFX90A — wire EXL3 experimental receipts on the WRITE side before the first measured run.** ✅ 2026-09-26
  Before the first correctness, performance, or quality-producing run, add producer-authored native schemas
  `epyc.exl3.measurement.v1` and `epyc.exl3.verifier.v1`, plus strict projections for both source kinds. Measurement
  rows use the locator run × arm × backend × operator × shape × metric; verifier rows use run × fixture × backend/path
  × proposition. Both carry schema and producer identity/hash, run/row IDs, self-hash, date, exact category, protocol
  ID (empty when ineligible), attestation path/digest, comparator/arm identity, experimental/no-promotion authority,
  and model/artifact/source/binary/library/toolchain/hardware/residency identities. Measurement rows contain exactly
  one metric with units and `metric_direction`, repetitions and `reps_basis`, and the raw vector. Verifier rows add
  checker identity/hash, fixture and read-set digests, exact `decided_proposition`, and verdict. Strict adapters accept
  only post-hook rows, project eligible native records into `ClaimTuple`, and delegate grading to `claim_tuple.grade()`.
  Historical runs are pre-hook and emit zero tuples; no new grading rule or production authority.

  Completed by research commit `bc9ac47b` and root commit `6b8f9e85`. The producer supplies both closed schemas with writer SHA-256 `8caeb33dbb12986fadc385afe25d22bd791b036253c736f9527e67a55f85e268`; the strict adapter and registered `exl3-measurement` / `exl3-verifier` CLI sources project only producer-authored values through the existing grading path. Independent main review passed all 44 adapter and dispatcher tests, including actual directory discovery and projection of 78 native rows into 234 claim frames with zero refusals or declines. No new grading ladder or production authority was added.

### VB-ARCH-CPU-QUAL — architect quality gate, CPU live-serving and GPU (filed 2026-09-23)

- [x] **SSU-F6 — `promotion_gates.yaml gates.quality` must record `max_tokens` explicitly, and that the cap
  is NOT model-neutral.** The 64 was carried by CONVENTION into the v9 and v10 qualifications — precisely
  the failure that file was created to end. Measured 2026-09-23: at that cap the retired Qwen3.5-122B
  truncated 0/200 while Flash-Next truncated 46/200, because one answers with a letter and the other
  derives in the visible channel. A gate cap that silently favours terse models is not a quality gate.
  Record the value, and record that a per-model truncation audit is required before any accuracy from it is
  comparable. **RESOLVED 2026-09-23**: `max_tokens: 64` recorded as what v9/v10 actually ran, plus a
  `truncation_audit` sub-gate (`required: true`) carrying the measured non-neutrality, the
  method, and the caution that the cap may only be raised once the truncated rows are shown
  non-degenerate. Verified the required-gate set is unchanged (the sub-gate is nested under
  `quality`, so `package.sh`'s top-level enumeration does not see it as a seventh gate).

- [x] **SSU-F7 — the live `:8074` process is missing two env knobs its own registry recipe declares.** **ROOT-CAUSED 2026-09-23, and it is larger than two knobs — see SSU-F11.**
  `GGML_NOHUGEPAGE_PROCESS=1` and `GGML_FA_SPLIT_KV=0` are in `recipe.env` for architect_critic but absent
  from the running process's environ (verified 2026-09-23). One of them is the THP shim. The served process
  is not running its own recipe, and nothing detects that. Decide whether the recipe or the launcher is
  wrong, then make the disagreement detectable rather than discoverable by accident.
  **Blocker: none.**

### VB-AK-SEAT — AutoKernel actor-seat efficiency records (filed 2026-09-24, main-ak-seat)

- [x] **VB-AK-SEAT-a — contract + strict read-side adapter, registered and tested.** ✅ 2026-09-24
  Contract (the exact producer field list, closed schemas, reference writers `build_call_record` /
  `build_arm_record`, validators): `scripts/vidya/adapters/autokernel_actor_seat_capture.py` —
  `epyc.autokernel.actor_call.v1` (one `actor-calls.jsonl` line per call → `actor_call_wall_s`) and
  `epyc.autokernel.seat_ab_arm.v1` (one `result-<arm>.json` per arm → wall / steps / tool calls /
  decoded tokens / compactions, totals over root + scouts). Reader:
  `scripts/vidya/adapters/autokernel_actor_seat.py`, `@register("autokernel-actor-seat")`, class
  `measurement`, no ladder; `cli.py ingest ak-actor-seat --path <dir|file>` (`Source` row in
  `ingest_sources.py`). Every tuple is an OBSERVATION (`Judged/Located`: empty `protocol_id`, n = 1);
  pre-hook lines/results emit zero rows (the real 2026-09-24 corpus replays to 0 — pinned); a v1 record
  that fails validation, predates `HOOK_SINCE` (2026-09-24T12:00Z) or is backfilled is refused;
  timeout/signal sessions emit zero rows (censored wall). Tests:
  `tests/vidya/test_autokernel_actor_seat_adapter.py` (33) + the `ak-actor-seat` end-to-end fixture in
  `test_ingest_sources.py`.
- [x] **VB-AK-SEAT-b1 — call-record producer in `actors._record_call`.** ✅ 2026-09-24 Research `1c7d0a2d`
  (lane `lane/ak-actor-seat-20260924-followups`, rides with the DS41-C20 seat merge). Every actor call appends
  an `epyc.autokernel.actor_call.v1` line built by THIS repo's `build_call_record`, loaded by file from
  `EPYC_ROOT_REPO` (default `/workspace`), so writer and reader share one definition. Role from the call's
  schema; seat arm/knobs from env keys `_seated` adds; per-run config, instructions and global
  `opencode.jsonc` digests; opencode version from its npm `package.json`; producer commit read from the git
  files (no subprocess per call); reply files bound by sha256/bytes; timeouts as `timed_out` with rc −1. When
  the contract cannot be met, the line keeps the pre-hook shape plus `v1_refused: <why>` (projects nothing,
  says why). Proof: two post-hook records (planner via opencode, critic via codex) →
  `cli.py ingest ak-actor-seat --dry-run`: `projected=1 declined=0 refused=0 rows=2`. Tests:
  `test_actor_call_record.py` (7). Note: the producer reads the contract from the ROOT checkout at
  `EPYC_ROOT_REPO`; until `/workspace` carries this commit's module, a campaign run writes `v1_refused` lines.

- [x] **VB-AK-SEAT-b1v — prove the producer on a real campaign call.** ✅ 2026-09-24 Run 8 (research `21ca61b0`,
  `EPYC_ROOT_REPO` = the ak-seat-handoffs lane worktree) is the first campaign carrying b1; at 13:19Z its first
  planner call had not returned, so no line exists yet. When one does: read
  `state-run8/**/actor-replies/actor-calls.jsonl` (read-only), confirm the lines are `actor_call.v1` with no
  `v1_refused`, and run `cli.py ingest ak-actor-seat --path <that dir> --dry-run` → `refused=0`. A `v1_refused`
  line names its own cause; fix that in the producer rather than relaxing the contract.
  **Proven (wrap-up, read-only):** run 8 wrote exactly one line before it stopped:
  `state-run8/targets/71f54ec4…/workers/actor-replies/actor-calls.jsonl`, planner, `epyc.autokernel.actor_call.v1`,
  rc 0, `wall_s` 1235.7, 13:12:03→13:32:39Z. Its stdout is 0 bytes. That is batch 0's reply lost to the 98,304-token
  slot overflow, which the record captures faithfully. `cli.py ingest ak-actor-seat --path <that dir> --as-of
  2026-09-24T18:00:00Z --dry-run` → matched=1 projected=1 declined=0 **refused=0**.

### Research Intake Update — 2026-09-25 (shared screen evidence)

- [x] **VB-RI-SCREEN-1 — Define the shared minimum research-screen receipt before the selector replay or new typed-decision shadow.** The producer-authored, self-hashed envelope binds `schema`, receipt/run ID, timestamp, source and producer revision, frozen input-manifest digest, incumbent baseline identity, raw per-item output path and digest, holdout or later-window identity, scored/failure/invalid/abstention counts, predeclared stop or promotion rule, and terminal disposition. Deterministic primitives may mark a holdout inapplicable only with a concrete conformance/provenance reason. The strict reader projects only fields the producer wrote and delegates grading to `claim_tuple.grade()`; this adds no source-specific ladder and grants no promotion authority. Direct consumers are `VB-DGM-1`, `VB-TDP-EXT`, `AP-DGM-PROV`, `SEQ-SHINKA-1`, and `AP-DGM-SEL`. **Completed 2026-09-26:** root commit `1f957fa0` adds the producer-sealed `epyc.research_screen.v1` envelope, immutable evidence digests, full-denominator validation, deterministic holdout exception, strict projection, CLI/ingest registration, and shared-grader coverage.

- [x] **VB-DGM-1 — Add the selector-replay profile and strict projection on the shared screen receipt before the first replay.** Bind the frozen EPYC journal/candidate graph, policy and scorer revisions, task order and holdout, selector/scheduler/archive/endpoint identities, eligibility denominator, per-decision parent choices, raw paired continuation outcomes, tokens/cost when present, and final disposition. Cover Shinka-style, current, score-only, DGM, and HGM arms in one profile and one replay run; preserve `claim_class ∈ {mechanism_feasibility, benchmark_performance, selector_causality, license_status}` and refuse projections that collapse classes. Historical journals remain inputs to a new replay receipt, never retroactively authored evidence. **Completed 2026-09-26:** root commit `1f957fa0` adds the five-arm selector profile, exact parent/continuation row matching, frozen holdout identity, selector stack and cost identities, and claim-class-preserving strict projection.

- [x] **VB-TDP-EXT — Add one bounded typed-decision shadow profile and strict projection on the shared screen receipt.** Extend the existing typed-decision evidence path for the immediate fixture/shadow consumers only. Bind requested and resolved model identity, model/base/head or hosted revision, adapter/config and dataset manifest, per-row outputs and probabilities, failure/invalid/abstention denominator, raw component and sequential timing digests, billed cost when hosted, metric direction, and protocol scope. Missing row bytes, model identity, or billing/timing evidence remain explicit and cannot support governed comparison. GLiNER/Fast Decisions, CLM/JevBench, PhishNChips, and BTZSC receive source-specific fields only when their parent trigger fires; do not build four speculative readers now. **Completed 2026-09-26:** root commit `1f957fa0` adds the bounded shadow profile with resolved identity, normalized per-row probabilities, component and sequential timing evidence, hosted billing evidence, dataset/config digests, denominator checks, and refusal tests for missing governed evidence.
