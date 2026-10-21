# 2026-10-21 noninf-vidya

Prospective belief-kernel write-side carriers, root `7335da327`: `adapters/{_native_sidecar,toc_ab,skillbank_ab,harness_improvement,ak_history}.py`, `cli.py ingest` names `toc-ab`, `skillbank-ab`, `harness-improvement`, `ak-history`, adapter-table rows, `tests/vidya/test_prospective_ab_carriers.py` (49 cases). Rows are self-hashed, re-derived and re-hashed on read; `claim_tuple.grade()` decides.

- Ticked: VB-SKILLBANK-AB-WRITE, VB-HIL-WRITE-FIELDS (carrier, reader, tests, adapter row).
- Left unticked: VB-TOC-AB-WRITE, VB-AK-HISTORY (their text requires the live producer write); owed producer calls filed as sub-bullets under the TOC trajectory box, M-23, AK-HR-3 and HIL-6. VB-HIL-WRITE base row noted, not ticked.
- Finding: SC86 `RUN_SIDECAR_FIELDS` has no tool-surface digest.
- Test hygiene: `ufh13_thesis_fixtures.py` now uses the standard research checkout when `UFH13_RESEARCH_ROOT` is unset and skips if it lacks the pinned commit.
