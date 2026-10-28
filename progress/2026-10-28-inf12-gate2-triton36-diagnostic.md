# INF-12 Gate2 diagnostic checkpoint — 2026-10-28

## Scope

The initial full-context run with the installed Triton 3.1 stack terminated during AMD Triton lowering, with an OOM request of 539.66 GiB against 29.13 GiB free. That failure predates the Triton 3.6 runtime path and does not evaluate it. A private symlink overlay selected installed Triton 3.6.0 without writing the shared venv. The evaluator's ROCm generation path forces PyTorch SDPA's FLASH_ATTENTION backend and refuses unsupported masks; batch size 1 gives the tested no-padding prefill and incremental decode shapes.

## Verification and smoke

- `SOURCE-SHA256SUMS` passed at `4bf0d4828d066b04e20b5f8268a328b7d9bf2f7a992147468260bb5058423902`; `TRITON36-SHA256SUMS` passed at `39e9ef7b0f5205364ddd1094e87eed057c93ac06624755e68a7475f228a2b300`.
- The model-free actual-entry preflight passed from an arbitrary cwd and selected Triton 3.6.0 from the expected installed package path. Targeted resume-identity and ROCm SDPA/GQA tests passed 11/11; a bounded MI210 compile/runtime probe passed.
- Exact `launch.sh --smoke` ran under R7 (`gpu-quiet exclusive`, `taskset -c 184-185`) from 19:32:52Z to 19:35:37Z on 2026-10-28, rc 0, wall 165 s. Base and Delta each completed two real `eventqa_65536` questions; four output rows were written to JSON and JSONL; total real generation was 134.046 s. Same-PID/start-tick KFD and HIP 6.2 samples bracketed generation. Evidence: `/mnt/raid0/llm/tmp/codex-ni-inf12-g2-20261028/outputs/20261028T193252Z-1510374/` and `/mnt/raid0/llm/tmp/compute-flags/ready/inf12-gate2-triton36-r4.smoke.log`.
- `STATE.json` records rc 0 and direct-child reaped. Cleanup scope is explicitly direct-child-only; descendants were not censused.

## Enrollment correction and limits

The first READY draft used `class=decision` and enrollment commit `a48ff59e938fd06eed59a313acce4ae76082c79b`. That commit predeclares the model/adapter and published target interval, but not the exact four-split/22-source/3,671-row population or Triton 3.6 / ROCm Flash-SDPA protocol. The invalid decision-class draft was withdrawn to `/mnt/raid0/llm/tmp/codex-ni-inf12-g2-20261028/ready-decision-class-withdrawn.json`. The replacement READY is `class=diagnostic`, enrollment `n/a`, and records model/data/source/runtime pins. Keeper-v5 dry-run validated its schema and returned READY-WAIT while the GPU lock was occupied; live keeper recognition remains pending.

This smoke is readiness evidence only. It does not establish a Gate 2 result or the full population's accuracy. The full evaluation and Gate 2 verdict remain open; do not infer either from this smoke.

## Follow-up

Prepare producer-time full-run evidence for `summarize_full.py` and the existing ClaimTuple ladder. Only a complete, input-pinned full run may emit the native measurement envelope; smoke, partial, failed, mismatched-pin, or cleanup-unverified outputs emit no tuple. The owner-apply source-table/task draft is at `/mnt/raid0/llm/tmp/codex-ni-inf12-g2-20261028/wrap-draft/VIDYA-PROSPECTIVE-DRAFT.md`.
