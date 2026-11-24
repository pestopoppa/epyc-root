# 2026-11-24 — handoff batched-decode-measurement

## 10:57Z — Resolve r7 run-end filing event

r7 run-end event: the existing owner-withdrawal verdict records WITHDRAWN, rc=75, superseded by r8, with no measurement; file_result confirmed the filing receipt already exists. Acknowledged the r7 end, filing-due and contamination alerts. RE-MEASURE remains open.

## 10:58Z — Investigate r8 partial run and replacement feasibility

RE-MEASURE: r8 already filed WITHDRAWN (rc=75), no finished result. Campaign log records four r8 clean-runtime refusals on foreign llama-server PID 2003761; it is no longer present at this check. Log SHA-256 548eef53768365650be53604a576381b83457d02a890a06438b06511b6a4d492. The separate q0 contamination record SHA-256 ed1f0f9fddb1a23bc5a82102d78372ecfaffeb67d649ef9130a5919507842f83 reports PID 4006054 at 40.9% for two samples. Host uptime is 2 weeks 2 days, beyond the host-health limit; the recorded uptime waiver was for r8 only. A replacement cannot be run decision-grade until reboot or an applicable operator waiver. No new cells or tick; r6 and r8 alerts acknowledged.
