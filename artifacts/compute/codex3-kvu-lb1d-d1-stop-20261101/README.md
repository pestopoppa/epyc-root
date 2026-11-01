# KVU-LB1.d D1 owner admission stop, 2026-11-01

Run `codex3-kvu-lb1d-t96-quiet-r1-20261031` ended rc 75 after the owner withdrew it under D1: the armed packet lacked a pre-grant qualification receipt and its smoke used a control, not the Q38FN target. The target subsequently loaded during the run; this does not establish pre-grant qualification. The result is partial, not an inference verdict.

The native JSONL records four cells in the first HYBRID arm and one cell in the first F32 arm, each with ten samples. The six-arm comparison and independent correctness assessment remain incomplete. The watch receipt reports cleanup verified and all captured birth-identified processes absent. Raw evidence remains at `/mnt/raid0/llm/tmp/codex3-next-wholehost-prep-20261031/packet/run-20261101T055048489124Z-2398194/`; `raw-samples.sha256` records hashes relative to that run directory. The previously declared FILLERS result path belongs to a prior run.

`result.json`, `watch-result.json`, `ended.txt`, and `withdrawal.json` are unchanged source copies. No raw sample arrays or environment are included in this capsule.
