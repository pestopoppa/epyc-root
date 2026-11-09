# 2026-11-09 autopilot-program refresh (RTG-02)
- Corrected T0.1 last-run date (2026-08-09T19:29Z, trial 1503; two journal shards).
- Verified preflight_audit.py and restart_readiness_report.py DO read both shards (own `_jsonl_paths`, not journal_shards.py); audit claim was wrong.
- Added AP-HOLD-RELEASE-REVIEW, audit-refresh section, selector-menu design decision under AP-DGM-PROV (notes on AP-DGM-SEL, SEQ-SHINKA-1), brand-new-era notes on SEQ-3, SEQ-B1, re-arm.
- Other audit rows not processed in this pass.
