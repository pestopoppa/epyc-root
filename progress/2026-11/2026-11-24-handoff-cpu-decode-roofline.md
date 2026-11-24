# 2026-11-24 — handoff cpu-decode-roofline

## 10:57Z — Handle stale Q8PK-DECODE-OPBW run-end event: verdict and filing receipt already existed.

Q8PK-DECODE-OPBW run-end was already filed and ticked; RESULT.json SHA-256 fb4ab52a4ee4100094c8addac58c07dbfef4260e8b43579b141f5471af0d6b31 reports ANSWERED, with all >=10 MB cells at 0.8576–1.1219 of stream. Existing filing receipts also cover the Q6K and A3B alerts; acknowledged all five stale alerts. No new measurement or verdict was produced.

## 12:47Z — Handle filed stopped CDR-A3B-Q4KV-32K run; no comparison was completed.

CDR-A3B-Q4KV-32K row cdr-a3b-q4kv-32k-cpu-20261124 ended rc=75 reason=stopped; file_result.py filed WITHDRAWN, no finished result and no performance claim. One q8-0 unit completed (12.011773 tok/s, 450.3 s); q4-0 did not complete. The stop's cause is not established. Rowflow resume is owner-only and this row's owner is autokernel; do not impersonate the owner or bypass an unexplained stop with a replacement. The warning alert was acknowledged.
