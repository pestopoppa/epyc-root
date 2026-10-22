# 2026-10-22 HS-PROF-1 reader fix 2 (coordinator 3c4ca599)

Filler `s5-hsprof1-beam` failed rc=1 at 13:23Z past the interpreter preflight. Two causes, both fixed; no inference run.

## Root causes
1. **Empty derivation.** `derive` posted to `/v1/chat/completions` without `chat_template_kwargs.enable_thinking=false`. The Qwen3.6-35B-A3B reader spent the whole `max_tokens=1024` in reasoning: `reader-server.log` shows `n_decoded` 854-919 per request (tasks 0/291/584, ~100 t/s), so `content` came back empty for 20/20 conversations. `derived.json` was written anyway (all `""`), `build` produced 20/20 empty snapshots, and the next run would have skipped derive because `derived.json` was non-empty. The BEAM answering path was already correct (`BEAMAdapter.inference_params.enable_thinking=False` -> `ServerManager.run_inference` -> chat path with `chat_template_kwargs`). The orchestrator deriver is parse-only (`extract_preferences_from_text`), so no orchestrator change was needed; `EPYC_ORCH_ROOT` default is fine.
2. **Canonical preflight.** `run_benchmark` ran `scripts/preflight_canonical.py` (llama-bench tripwire, taskset 0-95), which timed out and refused, even with `--existing-server-port` on our GPU server. That is an unclaimed whole-host CPU bench inside a GPU-only grant.

## Fix (research `hsprof1-belief-write` b513efb36, pushed)
- `build_derive_request` (enable_thinking=false), `check_derived` (SystemExit `DERIVATION EMPTY` on all-empty or no parsable PREF); `build` also refuses all-empty snapshots; `derive` validates before returning, so `derived.json` is never written from an empty derivation. The arm script moves aside a stale/empty `derived.json` instead of reusing it.
- `run_benchmark.canonical_preflight_skip_reason` + `run_canonical_preflight_gate`: skipped with a printed reason under `--existing-server-port` (or `--skip-preflight`); default behaviour unchanged otherwise.
- `PHASE=preflight` now checks the deriver body, the BEAM suite pin, the real `ServerManager` chat payload (HTTP mocked) and the skip-reason.
- Tests `scripts/benchmark/test_hs_prof1_reader_fix.py` (10), subprocess mocked: the gate never calls the runner under `--existing-server-port`; `lib.executor` names no llama-bench. 36 passed with neighbouring BEAM tests (research venv). `PHASE=preflight` ok.

## Pins
Job `s5-hsprof1-beam_job.sh` ARM_COMMIT -> b513efb36718e114cad7e270ba18a0ddb51a3403 (worktree already there). Poller 881865 had only a `sleep` child when edited. Bad outputs kept in `/mnt/raid0/llm/tmp/hs-prof1/bad-20261022T1323/`.
