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

- Audit + adoption kit (all schemas/specs to copy): `research/deep-dives/vidya-belief-substrate-audit.md` §§4–5
- v1 draft (source for the V2 split): `tmp/vidya-epyc-governance-pilot-handoff.md`
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

### V2 — Spec revision (the amendment sheet; first work package; blocks P1)

- [ ] V2.1 Split the v1 draft into three artifacts: (i) pilot spec, (ii) formal research program
      R1–R5, (iii) non-binding mature-architecture appendix (operator-endorsed, steering seq 4)
- [ ] V2.2 Resolve the Corroborated-in-chain tension: either drop Corroborated from the carrier or
      restrict it to explicit independence-judgment tokens; document that ⊕=max can never derive it
- [ ] V2.3 Document the product-lattice option (quality × traceability) as an available design
      choice: every load-bearing theorem is algebraic (absorptive/0-stable/fully-continuous);
      cite Abo Khamis p.25 verbatim + what totality actually buys (selection semantics, cut-point
      thresholding)
- [ ] V2.4 Correct citations: fully-continuous not ω-continuous (Dannert, LIPIcs numbering);
      ≤N-step 0-stable convergence (Cor 5.19) replacing the folklore N×h attribution; "N+1" →
      N Kleene steps + zero-init layer (E&L Thm 6); Carneades 2007 = three standards, five-set =
      Gordon-Walton 2009; Potyka = KR 2018; Baur-Studer = CLAR 2020
- [ ] V2.5 Pin the fold semantics to a Deletion-satisfying provenance semantics (P^AT); add
      Example 9 (minimal-depth failure) as a negative test vector; provenance store = DAG/circuit,
      never expression store
- [ ] V2.6 Replace iterate-until-stable with closed forms (lfp = F^N(0); gfp = F^N(F^N(1)) on
      ⊗-idempotent lattices); keep the N-step budget as a runtime assertion
- [ ] V2.7 Add the TOKI H1 judge-discipline rules as spec requirements (keyed judgment frames with
      full decoder tuple; first-committed-vote-wins per key; no model invocation during fold/replay;
      temp-0 is not determinism; total-order conflict tie-break)
- [ ] V2.8 Re-ground R1: zero-substitution licensed only for the positive core; specialization of
      dual-indeterminate provenance is the negation-era primitive (GT17 §5); per-stratum base case
      cites 1907.08470 (Def 29/Prop 30/Prop 41/Cor 38); register the residual theorem (cross-stratum
      re-tokenization equivalence + retraction exactness — proven nowhere) and the no-stratified-
      Datalog-provenance negative search result
- [ ] V2.9 Re-ground R2: certified absence = π⟦nnf(¬φ)⟧ over dual tokens; gfp non-specialization
      (Example 42) ⇒ absence certificates route through S∞[X,X̄]; cite Xu et al. 2018 as application
      precedent (decline-with-citation stands unless operator overrides)
- [ ] V2.10 Sever §7.19 semantic hashing / purity-as-evidence into the R3 research note; move §16.2
      mature-stack detail to the non-binding appendix (Rekor-v2/Tessera findings supersede parts)
- [ ] V2.11 Adopt the frame/ledger schemas from the adoption kit (nanopub envelope + lint rules;
      Graphiti bi-temporal fields incl. reference_time; PROV alias table; frame_type URIs +
      subjects[]; signed expiring policy frames; certificate-as-attestation-frame re-entry)
- [ ] V2.12 Adopt lifecycle + policy vocabulary (Active/Stale/Conflicted/Dropped + cite-only-Active;
      Abstain as typed transition; proof-standard grade names with the three EPYC gap closures;
      reconcile with dashboard/freshness.py vocabulary — map, don't fork)
- [ ] V2.13 State the pilot's security posture honestly (intent-frame forgery open in shadow mode;
      pilot-exit check that intent frames match ratification artifacts)
- [ ] V2.14 Add the operator-attention cost model (claims/batch sizing, anchor review, equivalence-
      check rate as an explicit metric) and restrict obligation conditions to ≤4 predicate types,
      one nesting level
- [ ] V2.15 Run the nine-relation coverage check against the frame-type vocabulary (Use, Generate,
      Derive + Support, Depend-on, Contradict, Invalidate, Trigger, Update — explicit
      adopt-or-decline for Trigger and Use/Generate) and score the design against the survey's
      Table-6 six-column rubric; record both results in the spec (intake-1034 derived actionables)

### P0 — Pilot corpus (downscoped per audit; blocks P3–P5 evaluation)

- [ ] P0.1 Gold corpus = 12–20 claims spanning statuses, seeded from REAL historical corrections
      (ngram 2.8× retraction; quality-NULL scorer artifact; 2026-07-25 fabricated citations;
      2026-08-09 renamed-kernel incident) — ground truth already recorded in dive_corrections/
      incident logs
- [ ] P0.2 Include one measurement-domain claim family (E8-era baseline slice) so era/frontier
      machinery is tested where it bites
- [ ] P0.3 Mutation classes introduced incrementally (start with source-edit + retraction; add
      classes as the engine stabilizes); blind gold-review per v1 §18.4 retained
- [ ] P0.4 Adopt HoH scoring (+1/0/−1 + A_C/A_O) and MemStrata protocol rules (marker-free
      construction; forced-answer stale-fact-error) as the pilot's precommitted metrics

### P1–P5 — Pilot build (Python + SQLite, shadow mode; full detail lands in the V2.1 pilot spec)

- [ ] P1 Ledger + frames + canonicalization + L1 checkpoints (C2SP byte spec pinned v1.0.0,
      checkpoints committed to git) + full fold with N-step assertion
- [ ] P2 research-intake adapter: instrument the SKILL's own writes (index append,
      dive_corrections, Stage-2b gate, Stage-3 approval) to emit paired frames at write time
- [ ] P3 Reverse impact + coverage labels + obligation fold (compare incremental vs full refold)
- [ ] P4 Shadow wiki projection + sidecars with assertion maps AND omissions lane (PaperTrail
      span-anchor pattern)
- [ ] P5 Freshness gate + certificates (VSA-mapped schema) + evaluation against P0 gold; Phase-6
      style promote/iterate/terminate decision package to operator
- [ ] P5b Author the executable postulate-compliance suite for the fold (Kumiho 49-scenario
      pattern: enumerate satisfied vs deliberately-rejected postulates incl. no-Recovery/
      no-auto-resurrection) using TOKI's Claim-vs-Wire double-verdict format (design-implied vs
      observed-from-code per guarantee) (intake-1033/1035 derived actionables)

### R — Research program (independent of pilot promotion)

- [ ] R1 Composite retraction through stratified negation (residual theorem as named in V2.8)
- [ ] R2 Certified absence (as re-grounded in V2.9)
- [ ] R3 (severed, optional) semantic identity / purity-as-evidence
- [ ] R4 Leaf-disjoint corroboration statistic (unchanged from v1)
- [ ] R5 Belief decay + obligation utility dataset (unchanged from v1)

## Dependency notes

V2 blocks P1 (the pilot spec must exist before the engine). P0 can run in parallel with V2 (it is
operator + curation work). P2 depends on P1 (frames must exist). P3–P5 sequence after P1–P2.
R1/R2 are paper-track and independent; R3 deliberately severed; R4/R5 need pilot data.

## Decision queue for operator

1. P0.1 corpus ratification (which real corrections + which claims).
2. Grade-mapping ratification (v1 §7.5 table, as amended by V2.2/V2.12).
3. Chain vs product lattice for the shipped carrier (V2.3 documents; operator picks).
4. Sidecar location + visible-banner policy for shadow projections.
5. Canonical pilot ledger: append-only SQLite (recommended) vs repository JSONL export.
6. Xu et al. 2018: decline-with-citation (recommended) or ingest as entry.

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
