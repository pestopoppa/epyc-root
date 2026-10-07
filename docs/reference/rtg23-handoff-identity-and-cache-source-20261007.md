# RTG-23 task identity and persisted-cache source review

W7 is complete: only the checked 2026-07-27 panel-activation title becomes `W3d-panel`; the historical `W3d` superseded-hold record, bodies and measurement artifacts stay unchanged. Task text now resolves both identities without stale line anchors.

The old W10 premise conflates persisted cache and in-memory archive authority. At APP `89ac173a8871b706298d2499b373038325318e0a`, `_apply_journal_archive_authority` removes the legacy persisted `pareto_archive` key after rebuilding from journal payload, and startup synchronization uses this authority. `build_repaired_state` also removes that stale cache. The source test `test_report_accepts_absent_state_cache_as_journal_authoritative` expects `ok=True`, absent state cache and diagnostic `match`; repair tests expect cache removal. Empty or absent persisted cache therefore does not establish silent frontier loss.

MAIN independently verified the worker's five source/test SHA identities; static source and assertion review only, no project import/test execution. W10 is not ticked: this review supplies no current-host file sample, journal identity, live frontier count or historical runtime diagnosis. The runtime owner can reconcile that specific historical observation at its own boundary. No new measurement or grading rule is introduced.

| APP path | SHA-256 |
|---|---|
| `scripts/autopilot/autopilot.py` | `f07d13af377d3f9b5da4bce1628301b1314017add62ab1bdf28742509b5f3c24` |
| `scripts/autopilot/archive_authority_repair.py` | `29c13acdb16ea056406c99ef59372cd532a3aaadf2cdf726b951ededec1aa5bf` |
| `scripts/autopilot/archive_authority_report.py` | `d60352bcd0361e1a59e2991498e4a9a0954dcdf7ab7dfcf7e2d1871b2218b734` |
| `tests/unit/test_archive_authority_report.py` | `d668e774d06c4c48a9e72c3927aa581f8155039e1f560854f5c5f17c16a6b4df` |
| `tests/unit/test_archive_authority_repair.py` | `02007f97b2ff93c5a20d0258004f37f7afd8f21154aef6970a397a94667327bd` |
