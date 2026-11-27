# 2026-11-27 — handoff cpu-decode-roofline

## 15:44Z — Triage withdrawn Q15 replay event and identify the already-published replacement

Q15 replay q15-head-replay-cpu-20261127 was automatically filed WITHDRAWN after rc=1 with no result; acknowledged its earlier smoke alert. Its owner corrected the launcher and published superseding q15-head-replay-cpu-20261127-r2 with a passing smoke; the replacement was already running. Do not attribute its output to the withdrawn row. WRAP-8 remains open: correct the repeat protocol and identity/KEEP gates before preparing a repeat.

## 15:45Z — File Q15 replay diagnostic NO_KEEP verdict

Filed q15-head-replay-cpu-20261127-r2 as fail / NO_KEEP (rc=0). No new Q15 mismatches among 48 held-out decisions at any width; native Q8 also had none. Q15 restored one calibration and five stress mismatches. Median paired Q15/native throughput t1/t8/t24 was 0.9381/2.0697/1.7840; throughput gate failed t1 and t24; matched Q8 A/A median absolute ratio deviations were 0.0238/0.3888/0.3548, limiting timing interpretation. Signed-word oracle checked 4098 cases and 5696 block records. Diagnostic only. Result /mnt/raid0/llm/tmp/q8-q15-tie-replay-20261127/out/RESULT.json SHA-256 a18504856e17a41fd59ac031a2733ee1c58b374cac87f88cc72e2d9e319204a0. file_result.py issued the receipt but could not tick: the manifest points to Q15-HEAD-REPLAY-CAPTURE, which does not exist in this handoff. [belief: cc]

## 15:46Z — Complete Q15 replay verdict filing and receipt

Correction to preceding entry: first file_result.py invocation wrote the verdict but did NOT issue a FILED receipt because the manifest points to nonexistent Q15-HEAD-REPLAY-CAPTURE. Refiled the same NO_KEEP verdict without a tick for that nonexistent box; file_result.py exited 0 and created the receipt. The result and rationale remain in the preceding progress entry and the verdict record. [belief: cc]
