# 2026-09-15 — AP-50 decision cockpit (RTG-02)

Scope: `handoffs/active/autopilot-continuous-optimization.md` AP-50. Zero inference, zero process
management; AutoPilot stayed stopped. Offline fixtures plus one read-only parse of the real journal.

## What landed (branches, not deployed)

- **epyc-orchestrator** `sub/ap-50-decision-cockpit`: `scripts/autopilot/decision_cockpit.py`
  (contract `epyc.autopilot.decision_cockpit.v1`), routes `/dashboard/api/decision_cockpit` and
  `/dashboard/api/decision_cockpit/health`, the `decision_cockpit` panel in `dashboard_panels.py`, and
  `tests/unit/test_decision_cockpit.py` (15 tests).
- **epyc-root** `sub/ap-50-cockpit-page`: hub page `/cockpit` (`dashboard/static/cockpit.html`), the
  `cockpit` registry row, a README section, `tests/test_dashboard_cockpit_page.py` (7 tests, including a
  node runtime render against a producer-generated sample), and the AP-50 evidence note.

## Findings from the real journal (read-only)

- 2 shards (`autopilot_journal.jsonl` trials 0–999, `autopilot_journal_1.jsonl` 1000–1505), 1,372 trial
  rows, 18 event rows, 0 bad lines, 0 duplicate trial ids, 119 supersession overrides folded.
- 8 era buckets. The current era (E16, from state `active_instrument_eras`) has **0 journaled trials**.
  The newest trial (1505, 2026-08-09) is E15 and was killed mid-trial.
- E15 view: 26 interventions proposed, 19 executed, 19 valid, 0 kept. The drops were 15 throughput-floor
  and 4 quality-regression reverts. Deltas against the E16 incumbent are correctly fenced as era mismatches.
- The legacy prose baseline regex also matches the throughput-floor sentence ("baseline 45.8" t/s).
  The cockpit reads a pinned quality baseline only from the "Quality regression: X vs baseline Y" sentence.
- Pre-existing failures on origin/main, not caused by this work: orchestrator
  `test_dashboard_panels::…[gepa]` and two `test_dashboard_helpers::test_discover_llama_ports_*` tests.

## Remaining

Merge both branches. Then the owning session does an API-only `:8000` reload and a hub restart, since
`HTML_ROUTES` is read at import. After that, take a live look at `/cockpit`.
