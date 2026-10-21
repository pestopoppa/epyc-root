# 2026-10-21 ak-repack-gate (DS41-W8c)

The operator asked to act on the advice that the DS41 AutoKernel served-shape correctness check never runs the
repacked MXFP4 kernel. test-backend-ops allocates weights in the plain CPU buffer, so it never reaches
`mxfp4_8x8_q8_0` (CPU_REPACK → `forward_mul_mat_id` → `gemv_q4_b32_8x8_q8_0_lut_avx<block_mxfp4x8>`). That is
why its MXFP4 NMSE reads exactly 0.0. Seeds S1–S5 change exactly that path.

**Option chosen: (b).** The W5a harness (research `73aab47cc`) was generalised into a gate probe, and
test-backend-ops was left unchanged. Reasons:

- test-backend-ops' eval copies the graph with `ggml_backend_graph_copy`. That copy needs `get_tensor`, which the
  repack buffer leaves null, and the buffer stores a different layout.
- Its reference arm is the generic kernel on random weights, not an independent decode of the served experts.

## What landed locally (not pushed)

Research branch `ak-ds41-repack-gate-20261021` @ `63d7b920e`, worktree
`/mnt/raid0/llm/tmp/ak-repack-gate-20261021/research`, based on origin/main `2a40ce4b4`.

- `autokernel/loop/cpu_repack_probe.cpp`:
  - runs MUL_MAT_ID on the same bytes in CPU_REPACK and in a plain buffer, at widths 1–512;
  - compares both with a double reference built from an independent scalar decode of MXFP4, Q4_0 and IQ4_NL;
  - reports two metrics: `nmse` and `maxrel` (max |err| / rms(ref)), which catches a single wrong block scale that
    aggregate NMSE cannot;
  - proves engagement per case: `extra` is set, the layout changed, and a one-scale witness in the repacked buffer
    moves exactly expert 0 / row 0 and restores bit for bit;
  - `-DAK_REPACK_FIXTURE=1|2` builds a test-only broken-scale version.
- `autokernel/loop/cpu_repack_cases.py`:
  - DS41 lane: 4 real 1017 MXFP4 slices (8 experts, 6 used), the W5a set.
  - Shared template: Q4_0 cases (run with GGML_IQK=0, because iqk diverts Q4_0 away from the repack) and IQ4_NL
    cases on served shapes.
  - Manifest calibrated on the anchor. The nmse bound uses the served-shape formula (×3, cap 5e-4). The maxrel
    bound is ×3, cap 0.25.
  - Fails closed on any missing or stale piece, on a binary that lacks the case-set literals or carries the fixture
    literal, and on any case that did not engage.
  - CLI subcommands: `calibrate`, `check`, `fixture-regression`.
- `gates.check_cpu_repack_case_set`:
  - Runs inside ppl_contract layer (a) when the lane has `<store>/cpu_repack/manifest.json`.
  - Adds the shared cases for repack routes and at the bundle tier.
  - `run.py` also runs it for every other CPU keep on DS41.
- New route `cpu_repack_gemv` (`arch/x86/repack.cpp`: the GEMV template body plus the MXFP4 entry).
  `cpu_repack_mmid` and `cpu_repack_gemv` are still refused on lanes without a manifest.

**Tests:** `test_cpu_repack_cases.py` passes (43 tests), and these existing suites still pass: test_gates,
test_served_shape_cases, test_cpu_fa_route, test_roofline_coverage, test_structural_routes, test_scope_widening,
test_op_metric_receipt and test_existing_cpu_run.

The C++ has not been compiled. All four quarters were held by `kvu12-redo`, with gpu-quiet exclusive. During that
quiet window about 70 s of single-thread pytest ran at nice 19.

## Runner (queued, not run)

FILLERS row `ak-ds41-repack-gate` (block-correctness, one quarter, not DS41-class, ready y). Launcher:
`/mnt/raid0/llm/tmp/ak-repack-gate-20261021/runner/launch.sh`. Inner script: `runner/inner.sh`. The inner script runs
these steps in order:

1. checks identity;
2. calibrates on anchor `06b169e27` `build-cpu`;
3. runs the gate on the anchor (it must pass);
4. runs the fixture regression: both fixtures must be refused and judged `wrong` with the plain arm clean, and
   Q4_0 under GGML_IQK=1 must report "did not engage";
5. runs pytest;
6. installs the manifest into the campaign store `cpu_repack/`.

**No DS41 keep can land before this:** without the manifest the gate refuses. That is handoff task DS41-W8c.
