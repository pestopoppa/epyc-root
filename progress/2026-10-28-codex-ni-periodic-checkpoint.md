# NI periodic checkpoint — 2026-10-28

This is a scoped coordination checkpoint, not a queue/index update. It records the accepted terminal artifacts and the live items visible at 18:46Z. It does not create a measurement warrant, reclassify a diagnostic row, or claim a P-GPU-1/W1 decision.

## Accepted rows and actual terminal evidence

- **INF-75 W1, r11** — Owner reported the complete run ended `rc=0` and accepted the diagnostic witness. The private result at `/mnt/raid0/llm/tmp/codex-ni-20261028-inf75-w1-r11/w1/LAST-RESULT.json` says `state=DIAGNOSTIC_CAPTURED`, `diagnostic_only=true`, `w1_claim=false`, `decision=null`, and binds its capture journal and summary digests. The exact run12 launcher output is `/mnt/raid0/llm/tmp/compute-flags/ready/inf75-c5-w1-constructed-prefill-512-r11.launcher.out` (job rc 0, ended 17:39:52Z). Older failed attempts remain preserved; r11 does not establish a W1/P0d decision.
- **INF-73 RUS-3, r3** — `.complete` records `rus3-repeated-samples-r3` ended `2026-10-28T15:18:31Z`; the direct smoke artifact is `/mnt/raid0/llm/tmp/codex-ni-rus3-runprep-20261028/direct-smoke-1793195145943975925/`. This checkpoint records completion status only, not a new quality verdict.
- **EVL-50 CME-7T, r1** — The exact launcher output `/mnt/raid0/llm/tmp/compute-flags/ready/evl50-cme7t-bounded-rationale-r1.launcher.out` records job rc 0 and completion at 17:51:48Z. The READY row and its scheduler state remain authoritative; no additional inference conclusion is asserted here.
- **RTG-57 KVU-16h** — `/mnt/raid0/llm/tmp/compute-flags/ready/rtg57-kvu16h-dedicated-runner-20261028.launcher.out` records the native run at `/mnt/raid0/llm/tmp/codex-kvu16h-runner-20261028/run-20261028T160623Z-105416/`, `rc=0`, `partial=false`, wall 4776.752s, runner dead and server cleanup verified. This is a run-completion fact only.

## INF-12 Gate 2 current state

A first actual-entry smoke at 18:29:52Z failed `rc=1` after 23s with HIP OOM while requesting 539.66 GiB with 29.13 GiB free. That trace predates the current ROCm fused-SDPA wrapper: `official_eval_utils.py` was changed at 18:39:40Z and `common.py` at 18:42:06Z. The owner refreshed the source pins after that change. The current hook disables native GQA dispatch on ROCm so Transformers expands KV heads, forces the FLASH_ATTENTION backend, and refuses non-all-one masks. The enrolled evaluation batch size is one, so `padding=True` creates no padded positions; its prefill and single-token cached decode cases match the hook's tested mask assumptions. This is source review, not a full-evaluator result.

A corrected exact-entry smoke began at 18:45:26Z under `gpu-quiet`; it was intentionally stopped at 18:47:08Z with `rc=75` after its child was reaped. It did not pass or produce an eligibility result. The owner then began a fresh two-question/two-arm smoke; at this checkpoint that retry is active and has no outcome yet. No READY manifest has been prepared for the corrected source.

## INF-34 DR-3e P-GPU-1 preparation

The private packet is `/mnt/raid0/llm/tmp/codex-ni-inf34-dr3e-pgpu1-20261028/`. Its launcher/job no longer depend on legacy `dryrun_check.py admit`, seals, or proof receipts; the normal path still pins canonical run12 grants, region lock, STOP, deadline, hard end and cleanup. Model-free validation ran 25 focused tests on R6 sibling CPUs 130-131, OMP/OpenBLAS 1, mutex `34-35.lock`: 0.88s and 49,840 KiB sampled peak RSS. No inference or GPU smoke has run from this packet.

The pinned Q4 verifier artifacts are present and verified. The IQ2 drafter download remains active: watcher PID 2702438, HF downloader PID 975263 (start ticks 133259790), pinned revision `907becb33103ab66b23da06a2dc74a5fca0583bd`, expected 40,377,862,848 bytes and SHA-256 `744dd2373bb4616def73cdd97eb3401dc7c64027762a3f178b1de00d42f2e9cd`. At 18:41:43Z its cache `.incomplete` was 33,895,586,067 bytes. The reservation watcher conservatively reserves the full expected model until the verified final file appears. At 18:45Z free space was 263,415,439,360 bytes, above the floor/reserve/full-artifact threshold; do not stop or restart either captured acquisition process. After exact model size/SHA verification and once `gpu-quiet` is free, the next step is the same-launcher 60–300s real smoke, then a diagnostic READY manifest if it passes. No P-GPU-1 conclusion follows from the smoke.

## Candidate reconciliation and claims

- The apparent GNX ESRCH candidate is not new work: the nativeproof packet has `TERMINAL-OBSERVED.flag`; recorded poller PID 437285 is no longer live. Its recovery closeout describes old failed proof/source-only proposal, while the parent supplied current RESULT-READY/WATCHER-ENDED/source-publication evidence. I did not reclaim or rerun it.
- The locally cached priority JSON is dated 2026-10-25, so it is stale. Origin/main is at `cb08aeef6` and its backlog snapshot is dated 2026-10-28 10:38Z. That snapshot says INF-60 Q38-T7b is closed; I did not claim it. Other top-ranked items already have active packets, ownership, or explicit gates, so I kept INF-34 as the current active claim rather than duplicate those tasks.
- Prep-lock claims visible at 18:45Z: `claim-INF-34`, `claim-KPF64-FB-repair`, `claim-USAGE-PROV-1-audit`, `claim-q3-class-arbitration`, and `claim-refactor-01a16fc3-b2-baseline-20261026`. This is an observed snapshot, not an ownership mutation. INF-12's current exact-entry smoke is also live under the GPU lock.

## Current next actions

1. Let the INF-12 current smoke reach terminal state; preserve its prior OOM artifact and publish only if the actual corrected smoke passes.
2. Keep the IQ2 acquisition and conservative disk watcher running. Do not launch INF-34 inference until full pinned size/SHA verification and a fresh free-space/region-lock check.
3. After INF-34 smoke, write only its diagnostic READY row/manifest if the same launcher passes; keep P-GPU-1 evidence pending independent protocol requirements.
4. Re-resolve the live priority/task text after these boundaries before taking another row; do not use the stale local priority snapshot as authority.
