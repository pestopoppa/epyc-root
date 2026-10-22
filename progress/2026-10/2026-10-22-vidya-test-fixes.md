# 2026-10-22 — vidya test fixes and CS-8.L1/L2 ticks (coordinator 3c4ca599)

## Fixed
- `tests/vidya/test_mhs_guard_adapter.py::test_producer_source_still_writes_the_pinned_vocabulary`:
  HIL-6 seam S1 (orch `7e9dcfad`) moved the MHS guards into `src/autopilot_core/mutation_guards.py`
  (confirmed at orch origin/main: `effect_risk_gate:` only there; `prompt_forge.py` re-exports). The
  test now searches prompt_forge plus mutation_guards; the pinned prefixes are still asserted.

## Real regression (not masked) — 16 tests with EPYC_RESEARCH_ROOT set
- Files: `tests/vidya/test_autokernel_profile_adapter.py` (12), `test_loop_cpu_profile_adapter.py` (3)
  plus the MHS test above (fixed). One root cause, not stale expectations.
- Research commit `07333b884` (2026-09-17, "Capture sampled CPU topology in original-request CPU
  profiles") inserts a limitation string into `LIMITATIONS`, adds a per-phase `topology` field,
  `--sample-cpu`, and changes the source-closure digest. `scripts/vidya/adapters/autokernel_profile.py`
  still pins the original scope: `LIMITATIONS` (line 49), `_PHASE_FIELDS` (85), limitation compares
  (254, 382, 395, 459), source-digest allow-list (32-47). Result: `ProjectionError: target profile
  exceeds the original CPU observation scope`, `direct loop capture identity/scope differs`.
- Owning task: AKU-06q / VB-AK-UNIFIED-PROFILE (`scripts/vidya/adapters/README.md` row, "2026-09-17
  extension": the strict reader may project only fields actually sampled under that capture version).
  The adapter needs a new reader version (legacy limitations OR current; topology phase field;
  new pinned source digest), not a test edit.

## Ticks
- conversation-stack CS-8.L1 and CS-8.L2 ticked; CS-8.L3 left as monitor.

## Also fixed
- `tests/vidya/test_ingest_sources.py::test_every_source_has_an_end_to_end_fixture_or_a_named_exemption`:
  new source `speech-listen-rating` (VB-SPEECH-LISTEN-1) lacked a named exemption; it is exercised
  end to end (real aggregate, ingest, CLI) by `test_speech_listen_rating_adapter.py`, so a named
  exemption was added.
