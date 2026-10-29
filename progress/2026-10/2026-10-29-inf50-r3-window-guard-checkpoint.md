# INF-50 r3 window/guard checkpoint — 2026-10-29

This checkpoint records the r2 refusal, the corrected r3 admission contract, the final bounded smoke, and the live state as observed at 00:52:42Z. It does not claim a completed full-C5 graph audit, fold, promotion, or performance result.

## r2 refusal and r3 correction

The r2 attempt (`codex-ni-inf50-writerrace-resume-r2-20261028`) ended rc6 at 00:37:23Z with `C5_GUARD_REFUSED:filler_id`. Its row/runner ID was r2, while private `guard.sh` accepted only the predecessor ID; the guard also expected a 3,600-second duration. Separately, r2 declared a 2,700-second minimum, although `body.sh` requires at least 3,300 seconds remaining before `FILLER_DEADLINE` and run13 sets `FILLER_DEADLINE=END-90`.

The corrected r3 uses one exact ID (`codex-ni-inf50-writerrace-resume-r3-20261029`) across launcher and guard, with guard duration and manifest window both 4,500 seconds. The launcher and manifest min window is 3,900 seconds. The admission arithmetic is: 3,300 seconds body requirement + 90-second run13 end reserve = 3,390 seconds at job entry; the 3,900-second minimum therefore leaves 510 seconds for setup. The 4,500-second requested window adds 600 seconds over that minimum. The body/guard safety checks were retained.

`packet/test_window_guard_contract.py` passed 3/3: the exact successor ID, 4,500-second synthetic grant, 0-23 CPUs and valid deadline pass the actual private `canonical_guard`; wrong ID and short-window cases refuse. The later successful fixture run was under q0 region-lock with taskset 0-23. The private `validate_fillers.py --row` copy check returned zero refusal and zero row warning after correcting the row delimiter and allowed pre-arm `blocker=missing launcher` marker; shared FILLERS was not used for that validation.

## Final-source smoke

The final captured run was `smoke-window-guard-r3c-20261029`, using the exact r3 launcher under `region-lock --role build` on CPUs 120-121 (q1). It finished successfully in 118.54 seconds (109.08 seconds analyzer child time). On the pinned 600-file, one-chunk fixture, the warm pass created one worker pool; the cache pass observed one hit, zero misses, and zero worker-pool creations while retaining the normal 19-worker shape.

- Launcher SHA-256: `4c2ab6415dfa643a02fd2f712ab246e3fde058beed99cf96e90a5f745be27feb`
- `packet/PACKET.sha256` SHA-256: `aba24fa93aa12317facfb0da6151b0638cb227fb7793f5fa107bb7f98cabb973`
- Smoke launcher log: `/mnt/raid0/llm/tmp/codex-ni-inf50-writerrace-resume-20261028/smoke-runs/smoke-window-guard-r3c-20261029.launcher.log`, SHA-256 `53e6dc5c0a141f6539546cc1aa3cb69d6b2d1a471fabb7f0d02b49dabc470073`
- Smoke result: `/mnt/raid0/llm/tmp/codex-ni-inf50-writerrace-resume-20261028/smoke-runs/smoke-window-guard-r3c-20261029/SMOKE-RESULT.json`, SHA-256 `672d819715f9839f355640991da5fbdc8f2fe4b3f96393f598d4917c374941ce`

This is a bounded 600-file smoke, not the normal 3,072-path eligibility run or five-symbol native audit. It does not support a fold, promotion, or speed claim.

## Armed metadata and live run

The r3 row and JSON are in `/mnt/raid0/llm/tmp/compute-flags/ready/` and `/mnt/raid0/llm/tmp/compute-flags/ready/armed/`, respectively. The armed manifest originally retained the r2-era top-level `source_manifest.sha256`; it was corrected atomically to the current `PACKET.sha256` hash above. All manifest hash fields were then checked against the current launcher, body, packet manifest, smoke log and result. The correction changed metadata only; launcher/source, row, grant, queue and live job were untouched.

At 00:52:42Z, r3 had grant `regions=0-23 start=2026-10-29T00:49Z end=2026-10-29T02:04Z`. The exact row PID 4160417 was alive. No r3 `.ended` or `.complete` file existed at that check. The normal job outcome remains in progress and is not asserted here.

## q0 fixture coactivity caveats

1. An earlier quick invocation of `test_window_guard_contract.py` included a taskset case on CPUs 0-23 but was run without region-lock. It had no contemporaneous q0 live-grant census. Its exact interval/coactivity is therefore unknown; no impact is inferred.
2. The next `canonical_guard` fixture run acquired q0 through region-lock, but I had not checked live grants immediately before it. A post-run census at 00:44:16Z saw only an active 48-71 LB4.9 grant (q2); that cannot establish the exact q0 grant state during the fixture. No impact is inferred.

A subsequent q0 row-validation command was preceded by a q0/q1-free region-lock status and a live-grant census showing only a 48-95 W3 grant in q2/q3. That was metadata validation, not an inference run. These caveats are retained rather than retroactively resolved.

## Next action

Observe the existing r3 PID/grant to terminal state without starting a duplicate poller or modifying grants/queues. If it refuses, preserve the refusal and diagnose the exact entry path before any successor attempt. No shared handoff/index edits or diagnostic receipts/seals were made for this checkpoint.
