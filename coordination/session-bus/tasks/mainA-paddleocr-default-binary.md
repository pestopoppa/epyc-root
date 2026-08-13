# mainA — Fix paddleocr_vl.py default binary, then resume ODL-011

**You are mainA** (roster id `mainA`, lanes `[cpu, none]`). Bootstrap: run
`session_bus.py provision --agent mainA`, then `drain --agent mainA --triage`, then execute.

## Task 1 — paddleocr default binary (row P2-L615)

Premise (mainD finding `msg-20260813T112442Z-32-mainD`): `odl_bench/paddleocr_vl.py` line ~29 sets
`EXPERIMENTAL_BIN_DIR = /mnt/raid0/llm/llama.cpp-experimental/build-hip/bin` — a directory that does
not exist on host (only `build-v8-hip`, `build-v9-hip`, `build-v9-hip-factorial-*` are present). The
PaddleOCR-VL arm fails with `FileNotFoundError` unless `--binary` is passed explicitly. The new
`unlimited_ocr.py` producer already defaults to `build-v9-hip` (version 10125 = production tip
`0db32c06e`).

Do: update `paddleocr_vl.py` default to `build-v9-hip` (matches production tip, has PaddleOCR-VL
support). Verify the path exists before committing the default.

## Task 2 — resume ODL-011-L512

Your in-flight lane (stale heartbeat recorded this task before the reboot). Re-verify the row's
premise is still current, then continue it. This is code work needing no compute.

## Constraints

- lanes `[cpu, none]`: CPU work only via a compute window **granted by inference** (rule 11). Your
  A7 / contention re-bench requests are already filed to inference; they wait on inference's grant,
  not on you. Do the non-compute ODL work now.
- **Do NOT push.** Commit locally only — push freeze pending operator ruling.

## Notes

- `fleet_watch` is already running again (your stale-842-min finding is resolved — confirmed by fresh
  log + held lock, PID derived from the lock file, not a name pattern).
