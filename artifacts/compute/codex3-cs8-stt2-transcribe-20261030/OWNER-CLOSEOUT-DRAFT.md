# Owner application draft — CS-8.STT2 transcribe.cpp arm

## Handoff addition (do not tick CS-8.STT2)

2026-10-30: transcribe.cpp @ `db678a031cf4c524bcab2c45a0dc6a7813106e4a`, ggml 0.26.0, was CPU-built out of the frozen trees in `/mnt/raid0/llm/tmp/codex3-cs8-stt2-transcribe-20261030/`; tracked source clean, CLI mtime 2026-10-30 versus pinned commit date 2026-10-20, isolated-library linkage PASS in `linkage.txt`. The build ran under the transferred bounded R6 prep supervisor; the scheduled comparison uses a build-role claim. READY `codex3-cs8-stt2-transcribe-cpu-20261030` queues 40 fixed FLEURS clips with descriptive per-clip comparison to the retained CPU reference. Exact publication, pins, same-launcher R11 normal and interruption witnesses: `PUBLICATION.json` in that directory. First real smoke clip text matched reference; this is a single unsealed diagnostic, not the full 40-clip result. Exposure records prevent replay of failed or unknown attempts; terminal incomplete is a terminal scheduler disposition, not successful 40-clip acceptance. The four-runner CS-8.STT2 task remains open, as do CS-22.A1 and T1. Belief source row/task applied by parent at root commit `c79da6de`.

## Progress addition

- Prepared and queued the transcribe.cpp CPU arm of CS-8.STT2; pinned source, build and isolated ggml linkage, R11 real inference/writer/clean-drain smoke, interruption/partial test, and keeper v6/v7b validation are documented in `/mnt/raid0/llm/tmp/codex3-cs8-stt2-transcribe-20261030/PUBLICATION.json`. 40-clip run and remaining runner builds remain open. [no-belief: preparation and one unsealed diagnostic smoke, no full-run finding]
- Acquired canonical pinned Parakeet F16 and Nemotron 3.5 F32 weights, full-hash verified; no A1 streaming acceptance or T1 result claimed.

## Scratch checklist

- [x] Publication receipt; exact READY manifest hash, current file mtime basis, launcher/source pins, smoke and cutoff log hashes, keeper scan outputs and hardlink identity.
- [x] Verify R13 `is_complete` is called after rc0 and the launcher complete command includes both `COMPLETE.json` and `TERMINAL-INCOMPLETE.json`; no packet edit or repeat-loop repair required.
- [x] Prepare fresh-worker CS-22.A1 transfer. Held claims remain untouched.
- [ ] Owner: apply handoff and progress draft, capture conclusion through the ordinary wrap process, and monitor actual scheduled result; keep CS-8.STT2 unchecked.
