# 2026-11-25 — pipeline-mgmt

## Publish outage: INSTALL.manifest gaps (root cause: new modules not in the manifest)

- **Outage**: publish ~12:14-12:47Z; reclaim-at-filing ~11:54-13:2xZ. New modules were not added to INSTALL.manifest, so the deployed rowflow lacked them.
- **Fixes**: `family_strikes` + `estimate_history` (0f25f2a25); `keep_failed` (218793b4c, after 421a2f4ca). A manifest-coverage test (92f2a927c) found the keep_failed gap.

## Changes

| Item | Commits |
|---|---|
| ak_gate harness | 8545b50ec, 8bb2d9e06, 6820416db, aa32438ba, fb2ddbe80, 2e2de9fdf; A ac90f161b; B bd99b5c66 |
| Generator gap fixes | 4a3e4add4 |
| Waste-audit remediations R2/R3/R5/R6/R7 | fe7f62b35, fe1de3b52, fbd84419e, 2fae96236, bc6beba9c |
| R8 (smoke hold release, keeper wake) | 05d00706f |
| Evidence keep | dbadf99d5 |
| Narrow HOST-DRAIN (operator-approved) | e0552f74a, ee2beb1ec, 9cdaf78f8 |
| Audit doc | docs/design/ak-waste-audit-20261125.md (d10a97ec0) |

Reviews: `/mnt/raid0/llm/tmp/review-akgate-20261125.md`, `/mnt/raid0/llm/tmp/review-r8-keep-20261125.md` (F7/F8/F2 trims in flight in another agent).
Boxes already filed and ticked by their agents: AKWASTE-R2..R7, AKW-R8, PM-HOST-DRAIN-NARROW.

## Codex lanes

cx12, cx14, cx17, cx18, cx19 landed; cx20 not ticked. **Operator-relevant**: the "5 unassisted" bar was met only for code-writing; Claude ran the tests and pushed every lane.

## Derived actionables filed (churn-pipeline track)

- PM-CODEX-UNASSISTED-DEF: redefine unassisted (own tests on cores 84-87, push via serialized_push); 5 such lanes before the PM-CODEX-DISPATCH-DETERMINISTIC port.
- PM-REPLAY-RECEIPT-ENFORCE: flip PREFLIGHT_ENFORCE replay_receipt; update 3 tests in test_ak_gate.py.
- PM-R8-KEEP-TRIMS-FOLLOWUP: F3, F4, F9 (F7/F8/F2 in flight elsewhere).
