# 2026-11-17 — handoff publication-upstream

## 22:52Z — Consume superseded INF-85 W3 alerts after handoff completion

Handled and acknowledged all 12 INF-85 W3 alerts (three failed initial runs, three filing reminders, three r2 smoke failures, three successful r3 completions). All six ended rows already carried FILED receipts; no duplicate filing or benchmark rerun was needed. W2 and W3 were already completed and the handoff archived by 633b2ce6b at handoffs/completed/publication-upstream-program.md. No open publication-program box remains. External site launch remains owned by engineering-hygiene-backlog WEB-2. [no-belief: alert consumption; no new measurement claims]

## 22:54Z — Acknowledge duplicate W3 Qwen3-VL r3 completion

Duplicate completion event for inf85-w3-qwen3vl-30b-a3b-q4km-r3-20261111 acknowledged through its existing FILED receipt. Prior PASS verdict and W3 completion remain authoritative; no new measurement or rerun. Handoff already archived at handoffs/completed/publication-upstream-program.md on origin/main (633b2ce6b); prior alert-consumption wrap-up c99102f79.

## 22:55Z — Acknowledge replay of superseded W3 Qwen3-VL initial failure

Acknowledged duplicate run-end event for inf85-w3-qwen3vl-30b-a3b-q4km-20261110 through its existing FILED receipt. Initial rc=1 failed host-health attestation; successful r3 superseded it and W3 was completed. Existing verdict remains authoritative. Publication handoff is already archived on origin/main at handoffs/completed/publication-upstream-program.md; no open boxes or new rows.

## 22:56Z — Acknowledge duplicate W3 Qwen3.8 Flash r3 run-end event

Acknowledged replay of inf85-w3-q38-flash-iq4xs-r3-20261111 using its existing 2026-11-11 filed PASS verdict and FILED receipt. Existing result: 25.59 +/- 0.16 tok/s, n=10, attestation hh-b758c7787cc5. W3 is already completed and publication-upstream-program.md is already in handoffs/completed/ on origin/main. No open boxes or new rows; preserve the authoritative verdict.

## 22:58Z — Acknowledge replay of superseded Qwen3.8 initial W3 failure

Acknowledged duplicate run-end event for inf85-w3-q38-flash-iq4xs-20261110 (rc=1). Existing 2026-11-11 filing.supersede verdict is SUPERSEDED by inf85-w3-q38-flash-iq4xs-r2-20261111; its existing FILED receipt acknowledges the event. Preserve that verdict. The later r3 PASS result already completed W3; publication-upstream-program.md is archived in handoffs/completed/ on origin/main. No open boxes, new measurements, or rows.

## 23:01Z — Acknowledge duplicate Qwen3.6 Q8 r3 W3 run-end event

Acknowledged replay of inf85-w3-q36-35b-a3b-q8-r3-20261111 using the existing 2026-11-11 workspace-f2 PASS verdict and FILED receipt. Preserve that verdict: 57.01 +/- 0.64 tok/s, median +/- MAD, n=10, P-BENCH-1, v10 build 10303; already recorded in completed W3. Publication handoff remains archived at handoffs/completed/publication-upstream-program.md on origin/main. No open boxes or new rows.

## 23:02Z — Acknowledge replay of superseded Qwen3.6 Q8 initial W3 failure

Acknowledged duplicate run-end event for inf85-w3-q36-35b-a3b-q8-20261110 (rc=1). Existing 2026-11-11 filing.supersede verdict is SUPERSEDED by inf85-w3-q36-35b-a3b-q8-r2-20261111; refreshed the existing FILED receipt to acknowledge this event. Preserve the authoritative verdict. The later r3 PASS result already completed W3; publication-upstream-program.md remains archived in handoffs/completed/ on origin/main. No open boxes or new rows.
