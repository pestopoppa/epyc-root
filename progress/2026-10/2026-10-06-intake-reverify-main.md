# 2026-10-06 progress

## EVL-51 / IRV-1–2 — intake re-verification inventory

- Worked from isolated lane baseline `d1749eaf81666f680ab9b453a5360e078e126753`.
- IRV-1 found **352 at-risk entries of 889 dived**: A=191, B=100, C=109. The TSV and stderr summary are in `/mnt/raid0/llm/tmp/intake-reverify/`.
- IRV-2 cite-check used a scratch snapshot of the canonical ledger (SHA-256 `a852a9d66ca89244fac4677e950a883338c9da311c0e4c4c328221e0437e931d`), as-of `2026-10-06T04:39:08Z`; exit 0 across 3,382 citations in 189 documents: ok=1,503, record=840, review=216, unknown=819, weak=4, blocking=0.
- The initial lane-local cite-check was inadequate because that lane lacked `.vidya/ledger.jsonl`; it is retained as diagnostic only and superseded by the canonical-ledger rerun. Unknown means substrate coverage gap, not evidence that a citation is invalid.
- Citation references preserve entry, claim, and `#record` forms. Triage and classification remain pending; no intake, handoff, index, or wiki changes were made.

## EVL-51 / IRV-3 — reviewed triage and execution scope

- Main reviewed the complete 352-entry triage: **322 KEEP, 22 RE-DIVE, 8 DEMOTE**. The three partitions cover every at-risk ID exactly once. KEEP leaves the intake index unchanged; DEMOTE corrects unsupported dive-verification depth while preserving applicability verdicts, claims, source identity, and existing per-claim corrections.
- Intake-1580 remains KEEP after corroboration against primary-source records intake-1586–1588. This is a bounded synthesis with corroboration, not an unqualified vendor assertion. The consumer scan and nearby-open-task field served as locators; the reviewed classifications came from entry/context evidence and the canonical citation gate, not proximity alone.
- Seven overlapping entries in the newer origin consumer report (1900, 1906, 1907, 1911, 1918, 1919, 1921) changed integration metadata only; the report identifies `yarn-context-extension-research.md` and no classification changes. The lane was not silently merged.
- The exact RE-DIVE IDs, reasons, citation forms, and frozen 10/10/2 waves are in `artifacts/intake-reverification-20261006/PLAN.md`. No producer result is called verified until an independent semantic second read is complete.
- Demotion rehearsal preparation binds 22 active support frames across eight entries to the canonical snapshot and preserves existing correction effects. A prior whole-index scratch ingest was discarded as nonconforming. The corrected filtered-index CLI rehearsal has not run: the required CPU region lock was held, and the wrapper returned exit 75. No canonical ledger or intake-index mutation occurred.

## EVL-51 / IRV-4 — primary-source re-dives reviewed; native preparation only

- All 22 primary-source re-dives have completed and passed independent review (wave sizes 10/10/2). Wave 1 initially checked 119 anchors: four needed repair, yielding 118 literal quotes plus two bound inventory receipts (120 checks); two additional intake-975 relevance anchors were added later. Wave 2 checked 87 anchors and 31 artifact receipts. Wave 3 checked 15 initial quotes and 12 artifact hashes, then added two literal anchors for the intake-989 trial-budget correction. These are separate denominators; earlier failures and dated correction history remain preserved.
- The 22 source proposals cover 110 native key-claim slots; this differs from the wave-1 expanded assessment denominator of 57 groups. The 30-target candidate (22 source entries plus eight demotions) is prepared but unapplied. The eight demotions are depth/status repairs only; current applicability verdicts and claim semantics are retained.
- The generic native-correction helper has 19 unique conformance cases passing in the root-owned region-locked run; three separate scratch rehearsals also passed. Duplicate executions shared inputs and are not independent corroboration. Candidate-wide 22-source and combined-30 validation remain pending; no native projection, ledger/fold, intake-index, handoff, or wiki write occurred here.
- Source gate/operator selection remains pending before any ordinary Stage-3 plan. Consumer corrections, source wiring, actionables, and evidence-bundle drafts remain preparation only; the proposal is not filed or applied.


### Native correction preparation checkpoint (2026-10-06; scratch only)

- Root's region-locked validation passed 19 unique generic-helper cases and three separate scratch rehearsals; a distinct root run passed all nine record-status tests. The portable 28-case test patch is prepared but has not been run.
- The previous combined full-native refresh stopped at preflight before append on a stale intake-664 CURRENT-text hash. The repaired refresh manifest changes only that CURRENT binding; 109/110 target records are unchanged and a static check confirms all 110 target claim-text bindings match the prepared candidate. The failed run remains preserved; no combined passing receipt exists.
- An optional pure-kind metadata guard has a prepared design to keep ordinary ingestion from certifying status-only intake-967 slot 2 and intake-972 slot 4. The guard is not integrated or applied. No native ledger, index, handoff, or wiki write occurred.
- The corrected consumer patch passes current-lane `git apply --check`; it remains a proposal. Full combined native validation and operator source-selection remain pending.

- Root reports integrated validation session `48536` queued from 06:54 under CPU 0–95, queues q0–q3, while `autokernel-experimental-serving` holds the hardware; at 07:04 the portable 28-case patch and combined full-native run are still unstarted with empty outputs. No process interference is authorized or reported. The selected-source gate still awaits the operator's external source-selection choice; scope approval cannot substitute for that choice.

### Native validation outcome checkpoint (2026-10-06 07:16 UTC; root-owned run)

- Portable 28-case suite passed (exit 0; 28 tests in 0.033 s). The combined full refresh failed before append (exit 1) when the unrelated-effective-target preflight found 13 IDs: `clm_intake_1093_00`–`05`, `clm_intake_1094_00`–`05`, and `clm_intake_1245_00`. No correction/demotion is claimed complete.
- Canonical-baseline cite-check exited 3; receipt retained and under investigation. Three scratch rehearsals matched exact frames/folds and immutable prefixes, but shared fixtures/receipt paths (zero independent replications).
- The 17 surfaced source identities remain outside the authorized 22+8 round pending operator source choice; composition is 6 companions, 10 distinct sources/artifacts, 1 journal edition. Mercury_Eval had a provisional relevant read; source fingerprints remain as recorded.
- Detailed checkpoint and strict result manifest: `artifacts/intake-reverification-20261006/wrap-checkpoint-20261006-0716.md` and `.manifest.json`. Main owns full wrap-up and any filing; no ledger/index/handoff/wiki writes occurred.
# Operator-requested wrap checkpoint — 2026-10-06

The operator instructed proceeding with the reviewed 22 re-dives and eight demotions, and requested wrap-up while subagents run. Main synchronized the tracked lane to `c714fe1c`, preserved peer changes, and applied dated completion checks for IRV-1–3. The original seven tasks remain: IRV-4–7 cover corrective-plan filing, source updates, demotions and final reporting. This checkpoint does not claim corrections applied.

Twenty-two primary-source reads and independent reviews are complete. Portable 28 native-helper/assertion-kind tests passed in the isolated tree; its combined refresh stopped before append on 13 downstream dependency-alert changes. Independent review confirmed those changes contain no new downstream evidence or grading change. V2 is prepared with full Belief-field auditing and five native fixtures; main owns its one-attempt launch. Recorded historical baseline: 4,341 citations, 282 documents, exit 3, 11 blockers. The current-documents scan and citation repairs remain part of the ongoing corrective round.

Reviewed compact evidence is copied under `artifacts/intake-reverification-20261006/reviewed-bundle/`; its manifest preserves the triage and consumer provenance. Earlier raw artifacts remain preserved in the declared scratch root. All 79 recommendation records and existing task bindings are retained; 17 additional source identities are outside the authorized round, not dismissed and not a blocker to the existing audit.

Main audit shard uses `intake-reverify-main-20261006`. No registered bus identity is established: `drain` rejects this session label, so main does not impersonate a roster agent or change the roster. Publication leases use this attributable session label and an operation-private token; those leases do not assert roster authority. CPU validation and wrap checks use the required region lock. The first queued README command had an incorrect relative cwd; main terminated only its captured PID 535606 and verified it absent before preparing the corrected runner.
