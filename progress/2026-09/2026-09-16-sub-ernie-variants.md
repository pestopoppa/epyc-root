# 2026-09-16 — sub-ernie-variants (ERNIE-Image-Turbo ROCm precision variants: build and A/B driver)

Zero-inference build agent. No model was run and no GPU work was done. The only processes started were
cmake/make and the driver's `--dry-run` preflight, which ran rocm-smi and the linkage check.

## Why
The runner refuted the f32 fix (`SD_ERNIE_ROCM_F32`, sd.cpp `a54f50c`). With the patch on or off, 1024²
and 832×1248 are solid white, while 768–960² are fine (research `cf05eefc`, root `befdfcdc`). The operator
decided to build both follow-ups from recipe §5 and run a short GPU A/B that includes the missing
patch-OFF 960² cell.

## Done
- Worktree `/mnt/raid0/llm/worktrees/sub-gpu-prep-stable-diffusion.cpp`. Branch
  `sub/ernie-rocm-variants-20260916`, commit **`f3a7fe957d1e615d8766084f000dc3fabf8d7775`**, whose parent is
  `a54f50c`. Files were staged explicitly: `src/ernie_image.hpp`, `RUNNER_RECIPE.md`,
  `runner/ernie_rocm_variants_ab.py`.
- `src/ernie_image.hpp` knobs, read once per process and applied only on ROCm:
  - `SD_ERNIE_ROCM_F32=0|1|wide`. The default is still `1`, the refuted narrow variant. `wide` also covers
    `to_q/k/v`, `gate_proj/up_proj` and `final_linear`.
  - `SD_ERNIE_ROCM_OUTSCALE=1` (or `=N`) applies `set_scale(1/16)` (or 1/N) on `to_out.0` and
    `linear_fc2`. This copies the pattern at `src/z_image.hpp:50-52`. Its mechanism, the scale-down and
    scale-up around the matmul, is at `src/ggml_extend.hpp:1070-1102`.
  - The server log echoes both knobs, and the driver checks the echo.
- Build `build-rocm-variants-20260916` uses the same cmake flags as `build-rocm-gpuprep-20260916`. The
  `sd-server` sha256 is `d33cbe6f064ae306f4bacd84a854a4539f47dd7d3b41901f3451b24f84d05b50`, and its mtime
  (15:07Z) is later than the source edit (15:05Z). `strings` shows both knobs.
- `verify_ggml_linkage.sh` **PASSES (exit 0)**, both with `LD_LIBRARY_PATH=$B/bin:/opt/rocm/lib` and with it
  empty. The output is in `$B/linkage_verify_20260916.txt`.
- Driver `runner/ernie_rocm_variants_ab.py` is documented in `RUNNER_RECIPE.md` §8. It does the preflight,
  takes the `mi210_0` device claim, runs one server per variant on :18190 with a 1 s VRAM/KFD sampler, and
  records per-request blankness (stddev < 5 counts as blank). It writes a pre-registered `verdict.json`
  and the cost at 896². The plan is 55 requests, about 25–30 min. Only `--dry-run` was executed.
- The prod CPU sd-server (pid 910274) and its tree `/mnt/raid0/llm/stable-diffusion.cpp/build*` were not
  touched.

## Runner notes
- At dry-run time (15:09Z) only **28.6 GiB of VRAM was free**, and the driver refuses to start below
  30 GiB. The runner has to arrange headroom with the MI210 tenants.
- Command: `cd /mnt/raid0/llm/worktrees/sub-gpu-prep-stable-diffusion.cpp && runner/ernie_rocm_variants_ab.py`
- Belief-kernel wiring: the driver emits measurement records (`requests.jsonl`, `verdict.json`). When
  the A/B runs, the owning session should decide whether this GPU-A/B record class needs an adapter row
  in `scripts/vidya/adapters/README.md`.
