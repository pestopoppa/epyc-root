# 2026-10-22 GPU-grant hardening (coordinator 3c4ca599)

From the CPU-in-GPU-grant audit (`/mnt/raid0/llm/tmp/3c4ca599-gpu-cpu-preflight-audit-20261022.md`). No inference.

- speech-d1-probes: `--cpuset-cpus "${FILLER_CPUS:-184-191}"` added to `docker run` in `overnight-gpu-arm-20261022/filler_job2.sh` and `job2_d1.sh` (poller 435446 was idle on `sleep 45`; row ARMED, not complete; fixed for the next run).
- `fillers-3c4ca599/filler_run7.sh` = run6 + exit 64 for `--class gpu --gpu-quiet exclusive` without `--claim-cpus`/`--no-fold-siblings`. `dryrun7_test.sh` proves error rc 64, explicit 0-95 works, no-fold GPU-only works (PASS, `dryrun7_out.txt`).
- Dirty-tree refusal (`git status --porcelain` non-empty) added to `s5-hsprof1-beam_job.sh` (exit 5) and `s5-hil18a_job.sh` (exit 8). Skipped: `yarn_gate_lib.sh` / `yarn_judge1_job.sh` (yarn-native-gate job live: pids 804136/816708, llama-server running).
- FILLERS.md: whole-host grant note on v11-050/051/052-gpu; each row validates rc 0 (backup `FILLERS.md.bak-pre-wholehost-notes-20261022`).
- Docs: Owner duties item on run7 in `docs/guides/agent-workflows/compute-fillers.md`.
