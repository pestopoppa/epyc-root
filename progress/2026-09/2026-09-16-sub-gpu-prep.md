# 2026-09-16 — sub-gpu-prep (zero-inference prep for the GPU runner)

Research worktree: `/mnt/raid0/llm/worktrees/sub-gpu-prep-epyc-inference-research`, branch
`sub/gpu-prep-20260916` (base `lane/autokernel-unified-20260908` @ `142fd1e3`). No inference was run and no
processes were managed. Nothing is merged or pushed.

## 1. INF-62 SL-2 — estimated target steps/s next to `aggregate_tok_s` (`loop/serving.py`)
- Champion tree `ef81196d5` (`/mnt/raid0/llm/tmp/champ2`, read-only): `n_draft_verif_steps` is counted
  (server-context.cpp:343/4216) but is **not exported** in `result_timings`. Only `draft_n` and
  `draft_n_accepted` are exported.
- Emitted `target_sample_steps_est`:
  - estimator: `predicted_n - draft_n_accepted`, i.e. verify steps plus plain steps;
  - per-slot rate: steps / `predicted_ms`, summed over slots (the same shape as tok/s);
  - it prefers a server-exported counter if one ever appears.
- Where it appears: per launch through a new `_measure_once(target_sample_steps=)` sink; per arm in
  `compare()`; A/A in `calibrate_floor()` (legacy + matched, inside the seal). It is reporting only; the gate
  is unchanged.
- Request rows and the observation shape stay closed, as native capture requires.
- Changing `_measure_once` changes its pinned callable identity, so this must land at a run boundary.
- SL-2 is **not ticked**: the exact metric needs the champion server to export the counter.
- Tests: `test_serving_target_steps_est.py`.

## 2. PRB-T4 harness — research `a454b7fd` (14 tests). Runner released by main.
## 3. CJ-1d/1e/3d — research `b1c7dedb` (19 tests). CJ-1d ticked with n=198. CJ-1e recipes are in
`docs/design/cj1-gpqa-sample-and-cj1e-gpu-pair.md`. CJ-3d defaults to native `bfcl_v3` (not an operator decision yet).
## 4. EV-13b — research `e70b6974`.
- The upstream golden set has **no licence**, so we commit only the fetch script and manifest.
- The set is actually 137 bugs (97 scored) across 50 PRs.
- Matcher spec: `data/review_f1/SEMANTIC_MATCHER_SPEC.md`.
## 5. ERNIE ROCm sd-server
- sd.cpp worktree `/mnt/raid0/llm/worktrees/sub-gpu-prep-stable-diffusion.cpp` @ `a54f50c`; build
  `build-rocm-gpuprep-20260916`.
- Linkage check PASS. Recipe: `RUNNER_RECIPE.md`.
- Prod `build/` and `build-hip/` untouched.
## 6. fable5 §5 #1 — gemma-4-31B and Qwen3.6-27B are DENSE (GGUF headers)
- The corrected MoE list and sweep spec were added under the handoff box.
- Scan script: `/mnt/raid0/llm/tmp/sub-gpu-prep/hdr.py`.

## Belief kernel
- New rows in the vidya README: TALE and review_f1.
- CJ sample note added.
- New tasks: VB-PRB-T4, VB-REVIEW-F1, VB-SL2-STEPS in `vidya-belief-substrate-program.md`.
- The serving belief reader `autokernel_legacy_serving.py` is absent on root main.

## SL-2 commit
- Research `5368766b`.
- Regression: the affected loop subset (`-k` serving/recipe/floor/…, 1243 selected) shows no new failures
  versus the unmodified lane tip. The base itself already has ~31 failures/errors, including
  `test_matched_serving` (missing root serving reader).
- One strict test stub (`test_serving_residency._stub_measure`) now accepts the new kwarg.
- The SL-2 handoff note was added and the box left unticked.
