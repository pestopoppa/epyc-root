# 2026-09-16 — sub-gpuprep-port (integration prep, not pushed)

Branch `sub/gpuprep-port-20260916` (research), worktree `/mnt/raid0/llm/worktrees/sub-gpuprep-port`, cut from origin/main `fb8a8273`.
The lane base `142fd1e3` is already an ancestor of origin/main, so the ported commits bring no lane-only code with them.

## Commits on sub/gpu-prep-20260916 that are not in lane/autokernel-unified-20260908
| old | new | class | note |
|---|---|---|---|
| a454b7fd | 76f5132b | PORT | PRB-T4 eval_tale_budget + tests; applied cleanly |
| e70b6974 | 726e2676 | PORT | EV-13b fetch script, manifest, matcher spec; applied cleanly |
| b1c7dedb | bababea8 | PORT | CJ-1d GPQA sample, CJ-1e doc, belief sample identity; applied cleanly |
| 5368766b | — | EXCLUDE | touches only `scripts/kernel_rnd/autokernel/loop/**` (SL-2 steps/s) |

## sub/gpu-runner-20260916 (c2204c21, 18d1d7c8); worktree not touched
- Ported: `inf61_q38_np_depth_grid.py` → a280853d. The pinned question file is now `--questions-in` (same default path), the run refuses when the file is missing, and its sha256 is recorded in meta.json. The default pin (`artifacts/architect-bench-gpu-20260720/questions_olympiadbench_hard.json`) is UNTRACKED. A dry plan with no `--execute` printed "48 launches".
- Not ported, because each hardcodes a /mnt/raid0/llm/tmp build or a per-run worktree:
  - cj1e_gpu_pair: CJ worktree + tmp build-fold
  - df26_serial_exact_confirmation: tmp champion build
  - ernie_rocm_rebench: sd.cpp gpu-prep worktree build
  - prb_t4_tale_gpu: TALE worktree
  - sl1_dflash2_nmax_pmin_sweep and sl5_df26_aa_control: tmp build-fold
  - s5_moe_batched_np_sweep (incl. 18d1d7c8): tmp APPROVED gate file + a run-specific pre-registration

## Tests
- test_eval_tale_budget, test_cj_gpqa_sample, test_augment_v1_manifest, test_harness: 51 passed.
- test_autokernel_gpu_discovery_beliefs + test_dflash2_beliefs: 13 passed.

## EV-13b data policy
The policy still holds:
- The manifest holds only refs, SHAs, sha256s, counts and PR titles; no golden comment text (longest string is 157 chars).
- Upstream `license: null` is recorded.
- The fetch output `data/external/` is gitignored.
- `fixtures/raw_augment_sample` is the synthetic fixture that was already on main (aa74ca61).
