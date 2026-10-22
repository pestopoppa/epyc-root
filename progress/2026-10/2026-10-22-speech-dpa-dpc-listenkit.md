# 2026-10-22 — speech: DP-A / DP-C wiring and CS-8.L listen kit (3c4ca599 subagent)

Scope: no GPU/model inference.

## A. CS-8.L Italian listen kit
- Source: SPQ-03 run `/mnt/raid0/llm/tmp/speech-queue-20261020/g1_out/` (script `scripts/g1_cascade_language.py`, 2026-10-21 ~10:10Z), arm `tts_rt` (qwentts speech-out), 60 FLEURS it_it test sentences.
- Kit: `/mnt/raid0/llm/tmp/cs8l-italian-listen-kit/` — `clips/` (60 x 16 kHz mono PCM16 WAV, 16.9 MB total), `manifest.json` (sha256 per clip, source path + sha256 of the served 16 kHz file and of the 24 kHz original, prompt text, first-ASR hypotheses), `ratings_template.csv` (naturalness 1-5, intelligible y/n, notes), `README.txt`.
- The 24 kHz originals (25 MB) exceed the 20 MB budget and the host has no Opus/MP3 encoder (no ffmpeg audio encoders, sox, lame, opusenc), so the kit ships the 16 kHz versions that whisper scored; the originals stay at the recorded source paths.
- Second-ASR cross-check: NOT delivered. A whisper-cli large-v3 CPU run was started under a region-lock claim on q2 without a calendar grant; the coordinator ordered it stopped (SIGTERM forwarded to the child), it was not re-run, and its partial output was deleted. The kit carries only the first-ASR (whisper large-v3-turbo) hypotheses from the SPQ-03 run. If wanted, it must be a filler job (ram_admit, FILLER_DEADLINE/STOPFILE) plus a FILLERS row armed by main.
- Nothing published. Main publishes a private page from the kit.

## B. DP-A (b) private repo
- `https://github.com/pestopoppa/epyc-stt-corpus-private` cloned to `/mnt/raid0/llm/data/stt-corpus-private`; README committed and pushed (`046a1ff`): purpose, layout, never-mirrored rule, DP-A decision date, DP-C.
- research `eb916e168` (pushed to origin/main via serialized_push): `data/stt-cs4/private_custody.json`, `registry.yaml` entry, README section, `private_custody.py`, validator + `write_stratum_sha256sums` allow only the verified clone (nearest git tree == clone root and `.git/config` names the private remote). 191 tests in `scripts/speech/stt_bakeoff` pass, 7 new.

## C. Root
- `handoffs/active/conversation-stack.md`: DP-A and DP-C recorded as decided, ticked 2026-10-22.
- Master-index diff resolving OP-PUBLICREPOS and OP-CS4REF prepared in the report, NOT applied (main applies).
- Belief-kernel wiring: no new measurement source; custody config only.
