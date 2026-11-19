# Delivered smoke controls and packet repairs

[Delivered PASS review](delivered-pass-review.json) consumes the original ROPE, SOFT_MAX/FLASH_ATTN_EXT and elementwise publisher events without republishing those packets. Native smoke replay yielded 1, 2 and 7 operator projections, respectively. The adapter refused smoke ingestion. Elementwise retained 17 unsupported cases and passed its 13 authored controls; unsupported is never a passing reference comparison.

[MUL_MAT_ID repair](matmul-repair-review.json) preserves the original failure, restores and pins the missing `frames.py` dependency, and corrects the control to require three linked carrier frames for one tuple. Fifteen custody controls passed. Publication queued GPU qualification; this is not a smoke PASS or official acceptance.

[KVU19 review](kvu19-repair-review.json) verifies the already queued deadline/capture-path repair against the archived failure and deployed byte hashes. It leaves that unchanged packet queued. Both repaired lineages have PASS and FAIL event registrations. Official capture and planning-context acceptance remain open for every row described here.

2026-11-18 delivered events: `kvu19-delivered-PASS.json` qualifies the original successor smoke; the full 20-launch result and planning canary were already filed in `../kvu19a2-native-20261118/`. `matmul-id-delivered-PASS.json` qualifies publisher smoke only (partial-native-incomplete); official 370-case acceptance and planning context remain open. Neither unchanged packet was republished.
