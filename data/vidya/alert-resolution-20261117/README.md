# Vidya alert resolution, 2026-11-17

All 15 matching unacknowledged alerts were handled and acknowledged with rowflow. The full-run verdicts and FILED receipts already existed; no verdict was rewritten. This directory preserves their original verdict records and the alert acknowledgment transcript.

Canary B r2 and R234 h are filed PASS. R234 c/d are filed superseded, and b/c smoke failures and e/f queued-WAIT messages are historical readiness events superseded by h. R18D r3 is inconclusive for clock eligibility. R18D r4 is filed FAIL: 135 of 136 invocations met the ratified band; SETTLED pair 5 candidate had 62 request samples and minimum 1575 MHz, below 1580 MHz. The capture was refused and produced no floor claim. The earlier r4 smoke residency warning was superseded by later readiness PASS, which does not change the full-run result.

KVQ's 30 launches completed but post-run identity validation failed because raw ldd load addresses changed; both depths were void and the sidecar had zero rows. It remains filed FAIL, with no salvage. The prospective comparison-only fix is separate under `data/vidya/kvq-linkage-fix-20261117/`.
