# 2026-11-09 filing five ended keeper rows

Question: what state did the five ended rows end in, and what does each row's own decision_rule allow us to record. No inference, no process control, raw results untouched.

| Row | Prior state | End | Verdict | Box |
|---|---|---|---|---|
| td16-label-word-bias-r2-20261109 | ended, no FILED | rc=0 complete | valid RESULT.json; C does not beat N on AUROC (+0.008, CI95 [-0.009, +0.028]) | routing-program TD-16-R2 ticked; TD-16 stays open (amendment arms) |
| parser-odl-hybrid-200pdf-r2-20261109 | ended, no FILED | rc=0 complete | 199/200 scored, overall 0.9035, doc 141 censored after 2 attempts | PARSER-ODL-HYBRID-R2 note, open |
| dripreview1-r4-20261109 | `.ended` rc=3, no `.complete` | driver voided by design | valid-false void; 7/7 `bad_final`; cause: model assigns `FINAL = ...` instead of calling `FINAL(...)` | D-RI-PREVIEW-1.1-R4 ticked; new R5 box; parent open |
| parser-marker-200pdf-20261109 | ended, no FILED | rc=0 complete | not a finding (one-document scoring defect unfixed) | Parser-quality parent note, open |
| vidya-r18d-aa-wire-20261109-r3 | ended, no FILED | rc=0 complete | clock_stable=false on 136/136 invocations; dry-run ingest refused=1; no floor | VB-AK-R18D-AA-WIRE note, open |

Filing mechanism: `filing-done/<id>.FILED` is written by `scripts/coordination/churn/file_result.py <id> --receipt <commit>:<handoff>#<BOX>` and the receipt must be a commit on origin/main. This branch is not pushed, so the receipts were NOT written; the five rows stay UNFILED-ENDED until the branch lands and the owner runs the receipt command (add `--no-reclaim` unless raw reclaim is wanted).
