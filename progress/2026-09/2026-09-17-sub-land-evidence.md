# 2026-09-17 — sub-land-evidence: land the unmerged 2026-09-16 research commits

Scope: research commits dated 2026-09-16 on `sub/gpu-runner-20260916`, `sub/gpu-prep-20260916` and
`sub/nextaction-sweep-20260916` that `git cherry origin/main` reported as not on main. No inference was
run and no processes were managed. `38d82ebe` (`sub/misc-fixes-research-20260916`, autokernel fix
held for its owner) was left alone.

## Classification (paths and blobs compared with research origin/main at `ae92ac5c`)

| commit | content | class | where it is on main |
|---|---|---|---|
| `c2204c21` | 8 GPU runner drivers | LANDED-DIFFERENT (2), MISSING (6, declined) | `inf61_q38_np_depth_grid.py` is `a280853d`; `prb_t4_tale_gpu.py` is `0b295a25`, and both main versions are newer and path-clean. The other six are declined (below). |
| `18d1d7c8` | §5 MoE driver, Option-A pre-registration | LANDED-DIFFERENT | Pre-registration and evidence are in `6cbdd856` (`data/s5-moe-batched-np-20260916/PREREGISTRATION.json`, byte-identical to the run's scratch copy); top-up is in `f5179054`. Driver declined. |
| `6b585b58` | INF-62 SL-1 evidence, `occ1_gpu_driver.py` | LANDED (data) | `8146880b`, 4/4 blobs identical. Driver declined; main has `scripts/benchmark/occ1/` and the OCC-1 evidence. |
| `416cd853` | INF-62 SL-5 A/A evidence | LANDED-DIFFERENT | `8146880b`: 18/24 blobs identical. The 6 `records.json` became `records.digest.json`, which drops completion text over OlympiadBench prompts. Main's version is the deliberate, complete-for-git one. |
| `0608f2f2` | INF-61 fence (`taskset -apc` twice) | LANDED-DIFFERENT, fix MISSING | Main's `a280853d` port lacked the fence that produced the `0a711890` evidence. **Ported as `c6e63877`.** |
| `91d66725` | PRB-T4 venv fix | LANDED-DIFFERENT | `0b295a25` (VB-RUNNER-PATHS), newer. Not re-landed. |
| `7a876f23` | DF2-6 serial-exact confirmation | LANDED-DIFFERENT | `8146880b`: 20/26 blobs identical, 6 `records.json` digested as above. |
| `c72e5ad2` | CJ-1e GPQA pair summaries | LANDED | `8146880b`, 6/6 identical. |
| `5368766b` | INF-62 SL-2 steps/s (`scripts/kernel_rnd/autokernel/loop/**`) | MISSING, declined | Autokernel-owned; see below. |
| `1780fa7b` | INF-70 retest1 docs, upstream patches, PROD-1 recipe draft | MISSING (docs), LANDED-DIFFERENT (draft) | **Docs landed as `56ef1404`** (34 files, unchanged). The draft is on main as `scripts/lib/qwen38_flash_next_recipe.py` (`fc8c44de`), which is newer (+334/-22, pin resolved). |

## Landed (research, pushed `ae92ac5c..c6e63877`)
- `56ef1404`: `data/inf70-retest1-2026-09-08/` (24) and `data/inf70-upstream-patches-2026-09-08/` (10).
  - Largest file 31 KB.
  - No Augment or EV-13b content.
  - The patches are our own ggml contributions; none is submitted.
- `c6e63877`: INF-61 fence port, plus a note in `data/inf61-q38-np-depth-mtp8-20260916/README.md`.
  - Checks: py_compile passed, and a dry plan (no `--execute`) printed 48 launches.

## Declines
- **Six one-off drivers** in `c2204c21`, each hard-coding a `/mnt/raid0/llm/tmp` build or a per-run
  worktree: `cj1e_gpu_pair`, `df26_serial_exact_confirmation`, `ernie_rocm_rebench`,
  `s5_moe_batched_np_sweep` (with `18d1d7c8`, which adds a tmp `APPROVED` gate), `sl1_dflash2_nmax_pmin_sweep`
  and `sl5_df26_aa_control`. The same applies to `occ1_gpu_driver.py` (`6b585b58`). None is path-clean,
  and all their evidence and pre-registrations are on main.
- **Raw `records.json`** (`416cd853`, `7a876f23`): these hold model completions over OlympiadBench
  prompts. Main keeps the sha256 digests. The raw files are also the largest in scope, up to 1.06 MB each.
- **`5368766b`**: the SL-2 reporting change touches only autokernel loop code (`serving.py`, two tests).
  It is autokernel-owned and left for that owner. It is on **no remote**, only local branch
  `sub/gpu-prep-20260916`.
- **PROD-1 recipe draft** (`1780fa7b`): superseded on main (see table). A second
  `test_qwen38_flash_next_recipe.py` would also collide in pytest. It stays on
  `origin/inf70/evidence-2026-09-08`.

## Root citations annotated
There are 43 "(on main as `<sha>`)" annotations across 18 files. History text is unchanged, and no `*-index.md` file was edited.
- `8146880b`: `6b585b58`, `416cd853`, `7a876f23`, `c72e5ad2`. Files: dflash2 handoff (4), canonical-judge (1), `2026-09-16-sub-gpu-runner` (4), `2026-09-17-main-handoff-sweep` (3), `wiki/speculative-decoding` (1).
- `56ef1404`: `1780fa7b`. Files: autokernel-rebuild (3), autokernel-unified-surface (2; the recipe-draft row points at `fc8c44de`), cpu-decode-roofline (1), vidya (1), `2026-09-08-ak-rebuild` (1), sub-closure-audit (4), sub-closure-fix (2), sub-integrate (1), sub-preserve (1), `wiki/hardware-optimization` (4).
- `c6e63877`: `0608f2f2` (sub-gpu-runner, 2).
- `0b295a25`: `91d66725` (vidya 1, sub-gpu-runner 2, sub-vb-wire 1).
- `6cbdd856` (pre-registration): `18d1d7c8` (fable5 window-2 §5, sub-gpu-runner 2, sub-gpuprep-port 1).
- Not annotated, because nothing is on main: `5368766b` (dflash2 `:116`, vidya `:1965`, sub-gpu-prep, sub-gpuprep-port, `wiki/speculative-decoding` `:22`), and `c2204c21` (sub-gpuprep-port `:14`, the declined drivers).

## Cleanup
- Removed my worktrees `land-evidence` and `land-evidence-root`.
- Removed the source worktrees `sub-gpu-runner-`, `sub-gpu-prep-` and `sub-sweep-epyc-inference-research`: every remaining `git cherry` entry is landed or an explicit decline. Branches are kept.
- `sub-misc-research` and `sub-akfix` were not touched.
- Preservation note: `sub/gpu-runner-20260916` (HEAD `c72e5ad2`) and `sub/gpu-prep-20260916` (`5368766b`) exist only as local branches in the shared clone.
