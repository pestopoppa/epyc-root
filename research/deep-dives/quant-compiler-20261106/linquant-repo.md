---
entry: intake-2642
title: "LinQuant code release: functional invariances and INT8 Triton chunk kernels for quantized linear recurrences"
stage: 2 (deep dive)
analyzed_at: 2026-11-06T17:40:00Z
head: 624a1a27049cbc50a0dfa3a0a6a9140c9ed6c2a8  (2026-11-03 06:38:35 +0100, "README: the zoo models are not released; drop the training-repo link")
clone: /mnt/raid0/llm/tmp/dive-quant-compiler-20261106/repo-LinQuant (shallow, 83 files tracked)
lane: /mnt/raid0/llm/worktrees/intake-quant-compiler-20261106 (handoffs/docs read here; never /workspace)
read_depth: >
  Code-primary. Every Python file in `linquant/` and `tests/` was opened; `linquant/reference.py` (239 lines),
  `linquant/invariances.py` (138), `linquant/harness.py` (228), `linquant/run.py` (95) and all four
  `linquant/kernels/zoo/*` kernels read in full. `linquant/kernels/mamba2/` read in part: `state_passing.py`
  (121) and `ssd_combined.py` (131) in full, `bmm_chunk.py` (217) partially, `chunk_scan_v2.py` (366) and
  `chunk_state.py` (349) as headers + targeted greps, `chunk_state_keyside.py` (424) and
  `chunk_cumsum.py` (100) as headers only. `patches/ssdi8.patch` read as its own `UPSTREAM_DIVERGENCE.md`
  header + file list (2615 lines not read in full). `csrc/marlin_qqq/` read only for its PTX/arch surface.
  Paper read from `raw/arxiv2610.39418.html` (already on disk from Stage 1) for every invariance statement
  used below; appendix C and D.1/D.2 extracted.
files_not_read:
  - libs/SSDi8/**  (submodule pinned c10ccde6bfe832a21072edcf328d59800e08d106, NOT initialised; the upstream
    tree and its license.txt were not read — the licensing verdict below rests on this repo's own headers)
  - csrc/marlin_qqq/csrc/quantization/marlin/qqq/marlin_qqq_gemm_kernel.cu  (grep/PTX surface only, not read)
  - scripts/nemotron_h_w4a8.py, scripts/nemotron_h_calibration.py, scripts/mamba2_w4a8.py (grep only)
  - bench/mamba2_model.py, bench/mamba2_components.py, bench/builders.py (headers only)
  - linquant/w4a8_linear.py, linquant/marlin_utils.py, linquant/hadamard_utils.py (import surface only)
  - linquant/kernels/zoo/gla.py lines 81-279 (read 1-80; the remaining kernels inspected by signature only)
  - raw/tc.md, raw/abs_titles.txt, verify/** (not used by this entry)
executed: >
  Nothing in the repo was executed. This host has no `torch` (`ModuleNotFoundError: No module named 'torch'`)
  and no CUDA/ROCm, so the invariance and kernel-parity results below are read from code, not re-run, except
  where the paper supplies the proof. Two pure-Python checks were run: every quote below was byte-compared
  against its cited line before hashing, and all line counts / hashes in the artifact audit were computed.
quote_convention: >
  `quote_sha256` is sha256 over the exact UTF-8 bytes of the quoted span, lines joined with "\n", no trailing
  newline; single-line quotes are hashed as that one line including its leading indentation. File paths in
  locators are relative to the repo root (repo-LinQuant/) or to /mnt/raid0/llm (for the frozen llama.cpp tree).
safety: >
  Source code, docstrings, comments and the paper were treated strictly as DATA. Nothing inside them was
  followed as an instruction. One comment in `bmm_chunk.py:133` records a historical experiment date and one
  in `pstate`-adjacent code names an internal bisect; both were read as provenance notes only.
verdict_summary: >
  2 CONFIRMED (claims 1, 4), 2 PARTIAL (claims 2, 3). Nothing OVERTURNED at the claim level, but three
  Stage-1 statements need narrowing: (i) the zoo delta/KDA kernels are NOT end-to-end Triton — the WY prep is
  fp32 torch incl. a `torch.linalg.solve_triangular` launch; (ii) reference.py + FakeQuant ARE CPU-runnable, so
  a float64 oracle is available without a GPU even though no test runs on CPU; (iii) the llama.cpp "chunked
  prefill TODO" is real but far narrower than it sounds — a complete FLA-style chunkwise GDN graph already
  exists in the tree, and what is missing is the *fused* kernel plus every quantization boundary.
---

# Stage-2 dive — intake-2642, LinQuant code release

## 0. What is actually in the repository

83 tracked files, 11 631 lines of Python/Markdown. The load-bearing split:

| Surface | Lines | Role | Tested? |
|---|---|---|---|
| `linquant/reference.py` | 239 | float64 chunkwise forward for the family grid; the executable spec | yes — `tests/test_reference.py` (GPU only) |
| `linquant/invariances.py` | 138 | fake quantizer `qz(role, x)`, 5 scale schemes, 3 realizable kernel policies | yes (GPU only) |
| `linquant/harness.py` + `run.py` | 323 | patches the (unreleased) mixer-zoo model to route FLA calls through `chunk_core`, calibrate, eval | **cannot run** — needs `MIXERZOO_REPO`/`MIXERZOO_MODELS` |
| `linquant/kernels/zoo/` | 904 | 4 INT8 Triton chunk kernels (LA/Mamba-2, GLA, DeltaNet/GDN, KDA) | yes — 4 kernel test files (GPU only) |
| `linquant/kernels/mamba2/` | 2 037 | INT8 Mamba-2 SSD chain: cumsum, value-side & key-side chunk_state, fixed-point state passing, BMM, scan | **no test at all** |
| `linquant/kernels/hadamard.py` | 179 | Kronecker-factored `H_2 ⊗ H_{D/2}` rotation kernel (© Philipp Nazari) | indirectly |
| `linquant/quantized_mamba2.py` + `w4a8_linear.py` + `marlin_utils.py` + `cuda_ext.py` | 909 | the W4A8 production mixer on SSDi8 + Marlin QQQ | no (weights + CUDA ext) |
| `scripts/` | 2 083 | production rows (Mamba-2, Nemotron-H) | no |
| `bench/` | 970 | kernel / stage / model timing | no |

Two structural facts the entry's title hides. First, **the two halves of `linquant/kernels/` are different
implementations of different things**: `zoo/` is the controlled-study *timing panel* (its kernels never serve a
production row), `mamba2/` is the production INT8 SSD that the W4A8 numbers run on. Second, they disagree on
rounding — `zoo/_q8` rounds half away from zero (`simple_gla.py:16-20`), the mamba2 kernels call
`libdevice.rint` (half to even, `bmm_chunk.py:135`), and `FakeQuant.round_away` exists precisely to switch
between them (`invariances.py:97-100`). Any cross-family emulation must parameterise rounding.

## 1. Claims table

| # | Claim | Verdict | Quote (verbatim) | Locator | quote_sha256 |
|---|---|---|---|---|---|
| 1 | `linquant/reference.py` is a self-contained, torch-only float64 chunkwise forward for the whole family grid, quantization entering only via a per-role callable; the executable spec | **CONFIRMED** (two of the seven invariances live outside it — see §B) | `    dt = torch.float64` | `linquant/reference.py:37`; `import torch` is the only import (line 19) | `7790cc13446a11f5b605ea24369bcb3faa4c67dcff926ecf07b30b665ed28dfd` |
| 1b | quantization enters only through a per-role callable | CONFIRMED | `               read_post=False, storage="rotated", tau=1.0, out_dtype=None, act_dtype=None):` | `linquant/reference.py:25` (signature: `qz` is the only quant argument) | `3060eef9fd3da3463d964c3a3525bf00fdc0496a4e5d76860b5fd9a6bbec141f` |
| 1c | same, stated by the author | CONFIRMED | ``([B,T,H] scalar, [B,T,H,K] diagonal). All math in float64; quantization enters only through `qz`.`` | `linquant/reference.py:5` | `305969de85f7fa1ee11397d58aa42d3d6ab8020edbddce04938d48745fc8aaf9` |
| 2 | `kernels/zoo/` holds **pure-Triton** INT8 chunk kernels (LA, GLA, DeltaNet, GDN, KDA) | **PARTIAL** — the INT8 contractions are Triton; the WY prep of the three delta-family kernels is fp32 **torch**, including a `torch.linalg.solve_triangular` launch | `    """fp32 WY prep in torch. Returns (L, Hw, W, U, fw): Gram left factor (unused after), readout/write key` | `linquant/kernels/zoo/gated_delta_rule.py:21`; also `kda.py:22-53`, `bench/zoo_kernels.py:5` | `5c8b6859c0a0a2ce9bb8c79c84e7062c037e92142147af0764e63ce73223ddcc` |
| 2b | `kernels/mamba2/` is a ~2k-line INT8 SSD chain | CONFIRMED | — | 7 modules, 2 037 lines: cumsum 100, state_passing 121, ssd_combined 131, bmm_chunk 217, chunk_state 349, chunk_scan_v2 366, chunk_state_keyside 424 (+ fused_split_rotate_xBC 329 = 2 366 incl. the R_QK fuse) | n/a |
| 2c | including an all-INT8 fixed-point inter-chunk state pass | CONFIRMED | `The inter-chunk recurrence runs in INT32 on the INT8 chunk states with the gate` | `linquant/kernels/mamba2/state_passing.py:3`; recurrence at `:78-81` | `50cc44edba6e6ddff9de187929a97bb6436ccc0cfebc82e861bb4f9d4cf46b1f` |
| 3 | tests prove invariance exactness at float64 (<1e-9) | CONFIRMED (tolerance and dtype exactly as stated) | `        assert err < 1e-9, f"{cell}/{kind}: {err:.2e}"` | `tests/test_reference.py:89` (also `:113`, `:121`, `:153`, `:168`, `:182`, `:228`) | `5665c7b2262724e0ed311d0c298d55df1a922d08e8b435c1db7938b2d960df92` |
| 3b | kernel-vs-emulation equivalence within a noise-relative bound | CONFIRMED | `    assert torch.isfinite(out).all() and err_max <= max(5e-3, 2 * noise_max) and err_mean <= max(2e-4, 2 * noise_mean), \` | `tests/test_kernel_simple_gla.py:23` (`check()`, `:12-24`) | `66535aedef101c7a6b882c6b10f5773c1e7b04b643b78359a363da4aea5a73fa` |
| 3c | no CPU CI | CONFIRMED — stronger than stated: there is **no CI at all** (no `.github/`; `.pre-commit-config.yaml` runs ruff only) and every fixture is built with `.cuda()` | `"""Parity + invariance tests for the reference chunk core (run on a GPU node with the pla env)."""` | `tests/test_reference.py:1`; `.cuda()` at `:28`, `test_kernel_simple_gla.py:34-37`, `test_kernel_delta.py:15-19` | `78b0d0d41e79e89d115da65923ddeb8527b59111fb694e26178c4b7871f9f6c9` |
| 3d | no mamba2 tests | CONFIRMED | — | `tests/` = `test_reference.py`, `test_kernel_{simple_gla,gla,delta,kda,regimes}.py`; zero imports of `linquant.kernels.mamba2` in any test | n/a |
| 4 | controlled-study zoo models and training code are not released | CONFIRMED | ``The controlled study uses models that differ only in their sequence mixer (linear attention with no, scalar, or diagonal decay, each with and without a write gate, plus DeltaNet, Gated DeltaNet, and KDA), trained by us at 340M and 1.3B parameters. These checkpoints and their training code are not released. Everything the harness does to a model is in `linquant/harness.py` (which recurrence tensors are intercepted and how they are routed through `reference.py`), so the study can be rerun on any model exposing the same Q/K/V/decay/gate tensors.`` | `README.md:115` | `915f4ebd399452e08c1d0cc819fdedf70308bfe45df61e88d9ea329272c5f3c9` |
| 4b | production rows are single runs, ~5e-3 PPL spread | CONFIRMED | `* The production rows are not bit-reproducible run to run (Triton autotuning and cuBLAS pick kernels by timing; the sequential compensation amplifies the differences): on Mamba-2 1.3B the same command on the same H100 gives WikiText-2 perplexities about 5e-3 apart, and the paper's rows were likewise single runs. Compare rows at that resolution. The zoo (fake quantization against a float64 reference) is deterministic.` | `README.md:121` | `33f5307309ca178f454b8341d3e4978ddce722480824b10b9e96ad160556a8be` |

Two claims need one caveat each, neither enough to downgrade the verdict:

* **Claim 1** — the core is genuinely family-generic: `family ∈ {linear, delta}` × `decay ∈ {none, scalar,
  diagonal}` is dispatched at `reference.py:67` (`fn = _chunk_linear if family == "linear" else _chunk_delta`)
  and the cell table at `harness.py:20-36` maps all 15 zoo cells onto it. But it is *not* a complete
  implementation of the paper's seven invariances: `D_QK` and `D_V` are applied by the harness outside the core
  (`harness.py:81-88`), and for the linear family `rho` is a caller-side relabeling of `beta` between `k` and
  `v` (`harness.py:164-168`; `_chunk_linear` accepts `bt` and never reads it). So "executable spec for the
  invariances" is right for five of seven and right-with-a-driver for the other two.
* **Claim 3** — the tolerance is real but the *inputs* are not float64 literals: `make_inputs` builds fp32
  tensors (`torch.randn(...)` default dtype) which `chunk_core` then casts to fp64 at `reference.py:41`. The
  arithmetic is fp64, the operands are fp32-derived. Only `test_diagonal_scaling_exact` /
  `test_value_axis_scaling_exact_on_delta_cells` / `test_linear_beta_placement_exact` feed `.double()` inputs.
  Also, `test_invariances` sweeps only `qk`, `v`, `eta`, `rho`; `tau`, `read_post`, `storage` and the two
  diagonal rescalings are covered by separate tests, not by that sweep.

## A. Can `reference.py` be lifted as a float64 oracle into a ggml/HIP GDN prefill port?

**Yes — as a test oracle, and that is the whole value; it cannot become runtime code.** Three reasons it is
liftable at all: it imports nothing but `torch` (line 19), it contains no `.cuda()` call (grep: the only
`device=` occurrences are `device=like.device` / `device=Q.device` / `device=None`), and it is fp64 by
construction (`dt = torch.float64`, line 37). It therefore runs unmodified on a CPU-only host — pending a torch
install, which this host does not have, so I did not execute it.

**The mapping onto our frozen tree is exact, not approximate.** `llm_build_delta_net_base::build_delta_net_chunking`
computes: decay mask `exp(g_cs_j − g_cs_i)` tril'd (`delta-net-base.cpp:131-136`), `attn = tril(k ⊗ k_b) ⊙ mask`
(`:139-144`), `lhs = I + attn`, `T = solve_tri(I+A, −A) + I` (`:163-168`), `W = k_cd` from
`kbg = (βk ⊙ e^{g})ᵀ @ T` (`:179-183`), `U = v_bᵀ @ T` (`:171`), `F = U − W·S` (`:243-248`), read with `q`
pre-scaled by `exp(g)` (`:186-188`, `:255`), write with the whole terminal decay on the key
(`kg = k ⊙ e^{g_cs−g_last}`, `:219-222`), state `s ← s·e^{g_last} + kgᵀ·v_new` (`:266-273`). That is exactly
`chunk_core(family="delta", decay=none|scalar|diagonal, rho=1.0, tau=1.0, eta=0.0, read_post=False,
rot_qk=None, rot_v=None, qz=none)`. Stating the cell parameters is the single most useful artefact this dive
produces: it turns "does our GDN chunking match FLA" from a judgement call into a cell choice plus four knobs
(`rho`, `tau`, `eta`, `read_post`).

**MIT-clean vs SSDi8-derived, per file.** The repo top-level LICENSE is MIT with a third-party section that
names only two carve-outs:

```
* libs/SSDi8 (git submodule): our fork of SSDi8 (https://github.com/cau-hai-lab/SSDi8),
```
— `LICENSE:26`, sha256 `7dc0625a21f02fe51d5e2ab09da6b48a0ffb9b98597172087b22fdf10461274e` (section `LICENSE:23-30`,
sha256 `6fcca9e8ef9bd809dccc491d00284d2551e1813fbc8693eb663bbece0c8bb000`).

| Path | Declared status | Actual provenance as stated in the file | Safe to copy into our MIT-ish trees? |
|---|---|---|---|
| `linquant/reference.py` | MIT | own work, torch only | **yes** (attribute) |
| `linquant/invariances.py`, `harness.py`, `run.py`, `tests/*` | MIT | own work | **yes** |
| `linquant/kernels/zoo/*.py` | MIT | own Triton, FLA *structure*; FLA itself is MIT and only imported at runtime (`gated_delta_rule.py:145-155`) | **yes** |
| `linquant/kernels/hadamard.py` | MIT | `# Copyright (c) 2026, Philipp Nazari` (`:1`, sha256 `ed4b8f2c65a90c799960d3f2b7928d4288fc07cdcd3065ef9947a6aadfab094b`) | **yes** (keep notice) |
| `linquant/kernels/mamba2/*.py` (7 files, 2 037 lines) | **not declared third-party** | SSDi8-derived, self-declared: `Copied from SSDi8's quant_chunk_scan.py (their faster kernel): INT8 C × INT8` (`chunk_scan_v2.py:4`, sha256 `d92affdd86d80fb56f8e5718949c4cce3546bb503f0990cf74b85aa6518045a7`); `ssd_combined.py:1` sha256 `1a459078af505fc2538282763c64d938210aa1d951d950f866627bec05453d8d`; `state_passing.py:1` "matches SSDi8" | **no** — treat as UT Austin Research License (non-commercial) |
| `linquant/hadamard_utils.py`, `cuda_ext.py` | not declared | import/`dlopen` the SSDi8 extension | **no** (runtime dep only) |
| `csrc/marlin_qqq/**` | Apache-2.0 (declared) | vLLM Marlin QQQ | yes under Apache-2.0, but see §C |
| `libs/SSDi8/**` | UT Austin Research License (declared) | submodule, **not initialised here** | **no** |

So per-file the answer is clean for everything an oracle needs, and dirty for exactly the code that would be
tempting to lift for performance. **The LICENSE file under-declares the in-tree copies** — `kernels/mamba2`
says in its own docstrings that it is SSDi8 code, while the LICENSE names only the submodule. That is a
documentation defect in the release, not a permission: I would not vendor those files into our public repos
(`epyc-root` and `epyc-inference-research` are public per OP-PUBLICREPOS).

**What must be re-implemented rather than copied:** every Triton kernel (obviously), the `FakeQuant` scale
machinery as a C++/ggml-side policy (~100 lines, but the *policy* is what carries the paper's claim, so
re-derive rather than transliterate), the anchored local rotation for diagonal decay if we ever want INT8 KDA
(`reference.py:133-151` is the spec, `gla.py`/`kda.py` the kernels), the fused triangular solve (we have
`GGML_OP_SOLVE_TRI` as a separate op, `ggml-cuda/solve_tri.cu`, so no new primitive is needed — only fusion),
and a Hadamard rotation op, which **ggml does not have** and which is the single largest *new* primitive this
line of work would require.

## B. Are the seven invariances actually implemented as claimed?

Yes — all seven, in code, at the lines below. The honest qualifier is *where*: five live in `reference.py`,
two live in `harness.py`, and none of the seven exists in the kernels as a *knob* (in the kernels, rescaling
folds into the scale tensors and absorption folds into pre-scaled operands, exactly as the paper says).

| # | Invariance | Implemented at | Mechanism |
|---|---|---|---|
| 1/7 | `R_QK` | `reference.py:42-44` (persistent) and `:62` + `:136-145` (anchored local) | `persistent = rot_qk is not None and decay != "diagonal"` → `q,k = mat(q @ rot_qk)`; under diagonal decay the same matrix is applied only to the *anchored* per-16-block operands, and only when a role is actually quantized (`:135`, `:142-144`) |
| 2/7 | `D_QK` | `harness.py:73-75` (`D = (max\|k\| / max\|q\|)^α`), applied `:84-85` | outside the core; exact by construction (`q·D`, `k/D`) |
| 3/7 | `R_V` | `reference.py:45-46` (`v = mat(v @ rot_v)`), `:71-72` (exit un-rotation), `:63` + `:174-179` (`_un` per product) | persistent; two storage bases |
| 4/7 | `D_V` | `harness.py:76-78`, applied `:86-88`, un-scaled by the caller `:178-179` | outside the core |
| 5/7 | `eta` (decay split) | `reference.py:155-163`, called at `:196` and `:226` | `Om**(1-eta)` on the key, `Om**eta` on the value; **for diagonal decay it is a scalar envelope only**: `s = Om.amax(dim=-1, keepdim=True)`, `kf = Om * s**(-eta)`, `wv = s**eta` — the channel-dependent remainder stays on the key, exactly as the paper requires |
| 6/7 | `rho` (Gram exponent σ) | `reference.py:209-210` | `L = β^ρ k` (Gram left), `Hg = β^(1-ρ) k` (Gram right) |
| 7/7 | `tau` (outer write-factor placement) | `reference.py:211-212` | `Hm = β^((1-ρ)τ) k`, `fw = β^((1-ρ)(1-τ))` on the pseudo-values |
| extra | `read_post` | `reference.py:167-171` | `(qz("q_read", Q) @ S) * pq` vs `qz("q_read", Q*pq) @ S`; scalar-decay only by construction (`decay != "diagonal"`) |
| extra | `storage=rotated\|canonical` | `reference.py:63`, `:71-72`, `:218-219`, `:195`, `:225`, `:227` | rotated: state stored rotated, one exit un-rotation. canonical: every value-side product un-rotated *before* it is combined or stored (`unrot = rot_v.T`), and the delta cell rotates the canonical read `(W·S)·R_V` while keeping `E` rotated |

Verbatim anchors:

```
    persistent = rot_qk is not None and decay != "diagonal"
```
— `reference.py:42`, sha256 `bf4ba00740029bb9e3a6d38c6e164b403993c74571614ab5b2443d8eed407941`

```
    local_rot = rot_qk if (rot_qk is not None and decay == "diagonal") else None
```
— `reference.py:62`, sha256 `390b835f1a3a2c214b1cce64f5247c0e92c1071ec739985630daeb9ec8d4abb8`

```
        s = Om.amax(dim=-1, keepdim=True)  # scalar envelope per token
        kf = Om * s ** (-eta)
```
— `reference.py:159-160` (quoted from `_write_weights`, `:155-163`; the hash is of the whole `:155-163` span,
sha256 `3be6100456ff4d7f704a1f839db8dca19a3c87f83722823da56d0698ef03a62b`)

```
    unrot = rot_v.T if (rot_v is not None and storage == "canonical") else None  # applied to value-side products
```
— `reference.py:63`, sha256 `2aa230c89ce1863d60876faa90da131090f3c3946133548c4e7eb34d9e2560ab`

```
        return (qz("q_read", Q) @ S) * pq
```
— `reference.py:170`, sha256 `52b3b4a1df349417ef8d47c9b285adf72e1c843c73eed0f74e0691b7c6e4f80e`

Two implementation notes that matter to anyone reading the invariants off this code:

* **The `R_QK` diagonal-decay branch is the paper's "local rotation" and it is a strict no-op when nothing is
  quantized** (`quantized = any(r is not None and qz.scheme_for(r) != "none" ...)`, `:135`). That is why
  `test_invariances` can assert 1e-9 for `qk` on GLA/KDA at all: a global rotation genuinely does not commute
  with diagonal decay, and the code does not pretend it does.
* **`rho` for the linear family is not in the core at all.** `_chunk_linear` takes `bt` and never reads it
  (`:190-199`); the harness moves `β^ρ` onto `v` and `β^(1-ρ)` onto `k` before the call (`harness.py:164-168`),
  which is why `test_linear_beta_placement_exact` (`test_reference.py:156-168`) can exist as a pure operand
  relabeling.

## C. What does a HIP/gfx90a port actually cost?

Four separable cost classes, in increasing order of pain.

**(C1) CUDA-only intrinsics — 9 call sites, 3 files, all mechanical.**

| Site | Count | What it is | gfx90a replacement |
|---|---|---|---|
| `tl.extra.cuda.libdevice.rint` | 9 (`fused_split_rotate_xBC.py:134,137,205,208`; `chunk_state_keyside.py:287,298,320`; `bmm_chunk.py:115,135`) | half-to-even round | `tl.extra.libdevice.rint` does not exist on the ROCm backend; use `tl.floor(x+0.5)` / `tl.ceil(x-0.5)` like `zoo/_q8`, or `tl.inline_asm_elementwise` with `v_rndne_f32` |
| `from fla.ops...` | 2 (`gated_delta_rule.py:145-155`, `kda.py:59-64`) | optional FLA fused WY prep | FLA is Triton-only and vendor-neutral in principle; on ROCm it would need its own port. Falls through to the fp32 torch path, which is fine |
| CUDA PTX in `csrc/marlin_qqq` | whole file | `mma.sync.aligned.m16n8k16...satfinite.s32.s8.s8.s32` (`marlin_qqq_gemm_kernel.cu:83`, sha256 `79e48317333c21cf32f3a4de9393de5a1ff4fb7838b4de0e53939092651a1c41`), `cp.async.ca.shared.global`, `ldmatrix`, `lop3`, `prmt`; `setup.py:28-31` emits `sm_80/sm_86/sm_90/sm_90a` **only** | **no HIP path exists and none is cheap**; this is an NVIDIA-assembly GEMM. Our W4A8 weight side must map to ggml quant types, not to Marlin |

```
            tl.minimum(tl.extra.cuda.libdevice.rint(y0_b * inv_scale_b), 127.0), -128.0
```
— `fused_split_rotate_xBC.py:134`, sha256 `52a12cc4c0157062fe9d26160fae294bea90a69578aa43a7c0ef85d7c44ee334`

**(C2) `torch.cuda.device` guards — 5 files, trivial but load-bearing.** `chunk_state.py:304`,
`chunk_state_keyside.py:381`, `chunk_cumsum.py:86`, `bmm_chunk.py:190`, `state_passing.py:111`. All are
`with torch.cuda.device(x.device.index):` wrappers around a launch. On ROCm `torch.cuda.device` is the same
API (HIP is aliased into `torch.cuda`), so these are *not* blockers — but they are also the reason "no CPU
execution path" is literally true: there is no `torch.device`-generic wrapper to fall back on.

```
    with torch.cuda.device(states_i8.device.index):
```
— `state_passing.py:111`, sha256 `109152ff3ccd80bb31e21b48b938b1dd9d5b2c131d8001749bec82b224637cab`

**(C3) smem assumptions vs gfx90a's 64 KiB LDS.** gfx90a (CDNA2) has 64 KiB LDS per CU; H100 has 228 KiB per SM.
The mamba2 autotune panels were tuned on the latter and several configs cannot fit the former. Arithmetic for
the worst config in `chunk_state.py:26-37` (`BLOCK_M=128, BLOCK_N=256, BLOCK_K=64, num_stages=3`, INT8
operands, FP16 x): A tile 128×64 B = 8 KiB, B tile 64×256 B = 16 KiB → 24 KiB per stage → **72 KiB at 3
stages, 96 KiB at 4** — over the gfx90a limit before epilogue buffers. `num_stages=5` configs at
`BLOCK_M=64,BLOCK_N=32` (4+2 KiB/stage = 6 KiB → 30 KiB) are fine; it is the *large-N, deep-pipeline* corner
that has to be pruned. This is a measured-fact-shaped claim I could not measure here: the *allocation* is
computable, the *failure mode* (compile-time `OutOfResources` vs a silently reduced occupancy) is Triton-version
dependent on ROCm and must be observed, not assumed.

The zoo kernels are materially safer: fixed configs, `num_stages` 1-2, tiles 64×64 / 64×128 INT8 → 12 KiB per
stage → ~24 KiB, well inside 64 KiB. Their real constraint is the other direction —
`_delta_state_body` keeps the whole `[BK, BV]` fp32 accumulator **in registers** ("full K in registers (E = U −
W·S needs the whole K reduction)", `gated_delta_rule.py:59`) and canonical storage **forces** `BV == V`
(`tl.static_assert(BV == V, ...)`, `:134`), i.e. a 128×128 fp32 accumulator = 64 KiB of VGPR per workgroup.
Feasible on both vendors, but it pins occupancy at 1-2 workgroups and it is why they had to disable pipelining:

```
    # loop is not software-pipelined (the two (V,V) rotation operands would be multi-buffered past the smem limit)
```
— `gated_delta_rule.py:194`, sha256 `c6ebf405d26deb73f71792def0e2b8d36a34e682a8ec396f432c47e36730c367`

**(C4) Are the zoo Triton kernels the portable half?** **Yes, with two asterisks.** They contain zero
`tl.extra.*`, zero PTX, zero arch conditionals; `tl.dot(int8, int8, out_dtype=int32)` is the only primitive that
needs a vendor lowering, and **gfx90a has it**: our own tree already emits CDNA2 integer MFMA —

```
        acc[0] = __builtin_amdgcn_mfma_i32_16x16x16i8(A.x[0], B.x[0], acc[0], 0, 0, 0);
```
— `llama.cpp/ggml/src/ggml-cuda/mma.cuh:1314`, sha256 `bae6cb6eeb5e2d580fb459bd0bdfe3fdef5f82850f93f4a15e1201129474087d` (CDNA2/CDNA1 branch of the 16×16 int8 tile; CDNA3+ uses the wider `..._32_i8` form at `:1312`). So the "gfx90a integer-dot primitive" question left open by intake-2641 has a concrete answer: **it exists, at half the k-depth of CDNA3 (16 vs 32)**. Whether MMQ actually *instantiates* that tile for `Q8_0 × Q8_0` on CDNA2 is a separate question I did not settle (`mmq.cuh:227` branches on `GGML_CUDA_CC_IS_CDNA`, and the int8 path has a dp4a fallback via `ggml_cuda_dp4a`, `common.cuh:694-724`) — that needs one targeted read plus a microbench, and it is the single highest-value open item in this whole line of work.

The asterisks: (i) the delta/GDN/KDA kernels are not end-to-end Triton — the WY prep is `torch` fp32 with a
`torch.linalg.solve_triangular` launch per layer, so "portable" there means "runs on rocBLAS/rocSOLVER", and the
kernel-panel timings include it by the authors' own statement (`bench/zoo_kernels.py:5`, sha256
`10f41c51c193fe27b6e64b5c91d67c9925199598c6b738dd6c064cfad0c44dac`); (ii) the 16-token diagonal blocks are
computed in **FP32 on dequantized** operands, not INT8 (`gla.py:70-90`, `reference.py:146-151`) — that is a
design choice from the paper, and it halves the INT8 win for KDA.

## D. Is anything runnable on CPU? What did the author say tests need?

**Runnable on CPU today, with a torch install:** `linquant/reference.py` and `linquant/invariances.py`, i.e. the
entire float64 core and the entire fake-quantizer. They are device-agnostic (no `.cuda()`; the only hardcoded
`device="cuda"` in either file is `invariances.py:107`, inside `kernel_scales()`, which exists only to build
tensors for the Triton kernels). One test in the whole suite is CPU-clean and proves the point:
`test_calibrate_stats_pass_with_native_policy` calls `calibrate(Dummy(), arm, [torch.ones(1)], device="cpu")`
(`test_reference.py:185-201`).

**Everything else needs a GPU.** The author's statement:

```
`python -m pytest tests/` checks the INT8 zoo kernels against `reference.py` and the invariances themselves; it needs no model weights.
```
— `README.md:47`, sha256 `74631aed36aa707cb55345e46d82cde97dd221369b8ab4457213cc850b9905bf`

```
Tested with Python 3.11, CUDA 12.8, torch 2.8.0, triton 3.4.0 on H100 (perplexity) and A5000 (timing).
```
— `README.md:28`, sha256 `3687856c7127c875b0ffe0d0f95bd113716892201ea4e6148d2b5ba0b15f2a0d`

plus the module docstring "run on a GPU node with the pla env" (`test_reference.py:1`). So: **no weights
needed, but a GPU node with a pinned CUDA 12.8/torch 2.8/triton 3.4 stack** — and `fla-core` for the parity
tests (`test_reference.py:32-36`). Decode is out of scope by construction:

```
                "QuantizedMamba2 is prefill-only: cached/stateful decoding (past_key_values, inference_params) is not "
```
— `quantized_mamba2.py:223`, sha256 `2167b68f4622ad035ea88fb702bdaeb07555151704384caddd8c6289748ca535`

## E. Which invariant/testing harness could become a cheap conformance test in our tree, and what would it prove?

**`chunk_core` at fp64 + the ggml chunked GDN graph.** Not the kernel tests (they need Triton and a GPU, and
they test code we will not import), and not the mamba2 chain (untested by its own authors, non-MIT). The
liftable unit is ~380 lines (`reference.py` + `invariances.py`, both MIT) plus a driver.

Shape of the test, and why each half is cheap:

1. A C++ case next to `test_gated_delta_net` in `tests/test-backend-ops.cpp` that dumps `q,k,v,g,beta,state`
   and the output to `.npy`-style raw buffers for one small config (`S=64, H=2, T=64/128, kda true/false`).
   No new op, no model, no weights.
2. A pytest (CPU, fp64) that loads those buffers, runs `chunk_core(family="delta", decay=none|scalar|diagonal,
   rho=1.0, tau=1.0, eta=0.0, read_post=False, qz=none)` and asserts relative max error `< 1e-9` against the
   ggml *fused-op* output and against the ggml *chunked-graph* output.
3. A second assertion that the two ggml implementations agree with each other at fp32 tolerance — the
   chunked-graph vs per-token-op equivalence that no current test covers.

**What it would prove, precisely:** that our `build_delta_net_chunking` WY prep, decay placement and state pass
implement the same algorithm as the reference cell — currently unverified, because `test-backend-ops` only
compares *a backend against the CPU of the same code*, which cannot catch a shared algorithmic error, and no
test compares the chunked graph to the sequential op. It also gives us a ready-made grading harness for any
future quantized variant: swap `qz=none` for a real `FakeQuant` policy and the same oracle grades the INT8
kernel, using the authors' own noise-relative gate (`err_max ≤ max(5e-3, 2·noise_max)`, `test_kernel_simple_gla.py:23`)
rather than an invented one.

**What it would not prove:** anything about performance, anything about a *fused* kernel (the graph path is what
we would be testing), and nothing about quantization quality — the oracle grades *dataflow*, not accuracy.

## F. The llama.cpp gap: is the "chunked prefill TODO" real at the frozen head?

Read at `/mnt/raid0/llm/llama.cpp` @ `ffc1bac82eeca6f9099e1ccd9ba49703c460a115` (the v10 frozen tree;
untracked `coordination/`, `tools/math-tools/`, `.gitnexusignore` present, no tracked modifications).

**Yes, the TODO is real, verbatim, and on the default prefill path — but it is much narrower than "no chunked
prefill exists".**

```
    //TODO: Add chunked kernel for even faster pre-fill
```
— `ggml/src/ggml-cuda/gated_delta_net.cu:191`, sha256 `48f61a5c4729f65df957bbeedacd8c818a59547c4a6d78a502f7802eb3bba516`

The kernel it sits in is per-token by construction: one warp owns one state column, the state lives in registers
(`s_shard[]`), and the whole sequence is a scalar loop

```
    for (int t = 0; t < n_tokens; t++) {
```
— `gated_delta_net.cu:74`, sha256 `da30488ef866b7bfe4e1449c33279ca73a2c3424cac2989198e63df7e0d3b208`

with a `warp_reduce_sum` per token for `kv` and another for `attn` (`:104`, `:118`). There is no matmul, no
INT8, no chunk state. Two things make this the *live* path rather than a decode-only path:

* `cparams.fused_gdn_ch = true` by default (`src/llama-context.cpp:251`),
* the fused node resolves on CUDA — the probe only *reserves* a graph of `n_tokens_per_seq * n_seqs` tokens to
  check device placement (`llama-context.cpp:506`; the `16` at `:55`, sha256
  `12ac5ce0f188a68fe4308ec8a8e388d132d5efa6a4e95cc98e3cbd9839f8160e`, is a probe size, not a threshold), and
* the dispatch condition is any multi-token batch (`delta-net-base.cpp:442`, sha256
  `fba02d9197492abcef53bd0275944f979e7e324c122585ec812882e43085a6a0`; full dispatch at `:433-446`, sha256
  `cc87415d42857e22168056e6e70b471dac71deed68662063c250804775d78a92`), which passes all `n_tokens` to one
  `ggml_gated_delta_net` call — i.e. **every prefill, not only long ones**, lands in the per-token kernel.

**What is *not* missing:** a complete FLA-style chunkwise algorithm already exists in the graph layer, and it is
what runs when the fused op is not resolved:

```
    const int CS = kda ? 16 : 64; // chunk size
```
— `delta-net-base.cpp:61`, sha256 `11d331142b74793e7b63c24461dbc293ccc1a30ec4cc72e988c78b460f7f40d6`

```
    ggml_tensor * lin_solve = ggml_solve_tri(ctx0, lhs, attn, true, true, false);
```
— `delta-net-base.cpp:166`, sha256 `a836ac54888c9f4dfffc530f5a9fa58d1333f5ddfb0568f500922fbf2d6ff394`

```
    for (int64_t chunk = 0; chunk < n_chunks; chunk++) {
```
— `delta-net-base.cpp:235`, sha256 `f46b51fd8fa90b1cd54f47661245c0ffbf7e28a735d5605f4848590c2eff8c72`

That path is chunked, uses `ggml_mul_mat` + `ggml_solve_tri` (CUDA `solve_tri.cu` exists and is registered in
`ggml-cuda.cu:2412`, `:5212`, template sizes at `solve_tri.cu:203-215` for exactly CS=64), and is correct-shaped
against the LinQuant reference cell (§A). So the TODO means: **the chunked *algorithm* exists, the chunked
*kernel* does not** — prefill pays the per-token serial cost whenever the fused op is chosen.

**What exactly is missing, enumerated against a LinQuant-style port:**

1. **A fused chunkwise GDN CUDA/HIP kernel** (the TODO). Today: either a per-token fused kernel (fast path) or
   an n_chunks-long host-side graph loop of ~6 separate ops per chunk (`delta-net-base.cpp:235-274`), each a
   full HBM round trip, with a graph whose node count scales as `T/64`.
2. **Every quantization boundary.** The ggml recurrence has none: `q,k,v,g,beta` come in as F32 (the op asserts
   `ggml_is_contiguous_rows` on F32 pointers, `gated_delta_net.cu:292-304`), the state is F32 or BF16 only
   (`[TAG_GDN_STATE_BF16]`, `gated_delta_net.cu:4-13`), and there is no per-role static scale anywhere in the
   op's parameter list. LinQuant's `kernel_static` policy needs 10 role scales
   (`invariances.py:14-16`) and an INT8 stored state with an fp32 carry (`reference.py:77-103`).
3. **The INT8 stored state.** Our state is the *memory* that LinQuant quantizes; we already halve it with BF16
   under a compile flag, so INT8 would be the next step — but it needs a per-(H,V) scale calibrated on the
   fp32 carry, and the op has no calibration surface.
4. **The fused split-and-quantize + rotation epilogue** (`linquant/kernels/mamba2/fused_split_rotate_xBC.py`,
   329 lines) — the piece that makes R_QK free by fusing it into the kernel that already materialises B and C.
   We have no Hadamard op at all, so this is new work, not a port.
5. **The parameterisation** (`rho`, `tau`, `eta`, `read_post`, `storage`) — ggml hardcodes one point in that
   space (ρ=τ=1, η=0, read-pre, rotated storage equivalent). Adding knobs is cheap in the graph and expensive
   in a fused kernel.

**Sharpest statement for the ledger:** the port is *not* "write a chunked GDN algorithm" — that exists and
matches FLA. It is "fuse the chunked graph, then add quantization boundaries to the fused kernel". Those are
very different costs, and the first one is a pure performance item we can measure today.

## Derived actionables ledger

Owners are the lane handoffs that carry the relevant rows today (verified in
`handoffs/active/inference-research-index.md`): INF-80 → `quantization-and-low-bit.md`, INF-33 →
`model-architecture-readiness.md`, INF-48 → `rocm-kernel-authoring.md`, INF-65 →
`kernel-champion-and-promotion.md`.

| ID | Action | Owner (lane) | Disposition | Why / why not |
|---|---|---|---|---|
| LR-1 | Land a CPU-only fp64 conformance oracle for the chunked GDN graph: vendor `linquant/reference.py` + `invariances.py` (MIT, attributed) plus a dump case in `tests/test-backend-ops.cpp`, assert 1e-9 vs `chunk_core(rho=1,tau=1,eta=0,read_post=False,qz=none)` and chunked-graph ≡ per-token-op | INF-33 `model-architecture-readiness.md` | **PROPOSE — do it.** No GPU, no weights, ~1 day, closes a real hole (`test-backend-ops` compares backends, not algorithms) | This is the only durable asset from the entry that survives even if we never quantize the recurrence |
| LR-2 | Record the cell mapping (ρ=1, τ=1, η=0, read-pre, no rotation) in the delta-net base header so future readers can locate the algorithm against a published spec | INF-33 | **PROPOSE — do it** with LR-1 | Cheap; prevents the next agent re-deriving it |
| LR-3 | Settle whether MMQ on CDNA2 actually instantiates `mma.cuh`'s `mfma_i32_16x16x16i8` tile for `Q8_0 × Q8_0`, or falls back to dp4a: read `mmq.cuh:180-260` + `mmq-load-tiles.cuh`, then one microbench | INF-48 `rocm-kernel-authoring.md` | **PROPOSE — highest value open question.** It decides whether *any* INT8-activation path on gfx90a is worth designing | The primitive exists (`mma.cuh:1314`); the dispatch is unverified. Do not claim throughput either way until measured |
| LR-4 | Do not vendor `linquant/kernels/mamba2/**` into any public repo; treat as UT Austin Research License despite the LICENSE file naming only the submodule | INF-80 `quantization-and-low-bit.md` | **DECLINE the code, KEEP the design** — record the boundary explicitly | Public repos (OP-PUBLICREPOS). The *design* (INT8 stored state + fp32 carry, no error feedback into the carry) is unencumbered and is the durable idea |
| LR-5 | Do not pursue Marlin QQQ W4A8 on gfx90a; map the weight side to ggml quant types instead | INF-80 | **DECLINE with reason** — `mma.sync`/`cp.async`/`ldmatrix` PTX built for `sm_80/86/90/90a` only (`csrc/marlin_qqq/setup.py:28-31`) | There is no HIP lowering of that kernel; the cost is "write a new MFMA W4A8 GEMM", which is a different project |
| LR-6 | Adopt the *noise-relative* kernel-vs-emulation gate (`err ≤ max(5e-3, 2·noise)`) as the house pattern for kernel conformance, instead of absolute tolerances | INF-65 `kernel-champion-and-promotion.md` | **PROPOSE — adopt as a pattern**, no new handoff | It encodes "a dataflow bug shows as ≥100× the noise floor" and removes per-kernel tolerance bikeshedding |
| LR-7 | Do **not** copy the fixed-point gate quantizer as-is: at `GATE_SHIFT=7` the `+0.5` rounding of `exp(dA)·128` clamps to 127 for any gate ≥ 0.9922, so a no-forget channel loses ~0.78 % of its state per chunk (≈22 % over 32 chunks at T=2048) | INF-33 (or INF-80 if it lands as a state-cache design) | **FLAG — verify before any reuse**; not a claim that their numbers are wrong (SSDi8 inherits the same convention) | `state_passing.py:72-81`: `S = 1 << GATE_SHIFT`, `gate_scaled = gate_fp * S`, clamp to ±127. Arithmetic is exact; whether it bites depends on the layer's `dA` regime, which the repo does not report |
| LR-8 | Do not attempt `eta`/`rho`/`tau` as knobs on our GGUF weight quantization | INF-80 | **DECLINE with reason** — those invariances redistribute *token-wise activation* factors; ggml's per-32-block scales live on the output dimension of a weight and the split changes none of them | Re-openable only if we add *activation* quantization to the recurrence — which is LR-3's downstream |
| LR-9 | Do not treat the entry's Section-4 numbers as evidence for anything in our tree | INF-80 | **DECLINE** — no zoo weights, no training code, single-run production rows at ~5e-3 PPL resolution (`README.md:115`, `:121`) | They are the authors' own reported results, correctly labelled; they are simply not replicable here |

## Dive-surfaced sources (not already in the index)

| Source | What it would settle |
|---|---|
| `flash-linear-attention` (fla-org), the chunk kernel structure every zoo kernel reproduces (`README.md:141`) | Whether the *placement* convention we would test against (ρ=τ=1, read-pre) is FLA's, and whether FLA has since moved to a different WY form. Cheap to check; would harden LR-1's oracle choice |
| SSDi8 upstream `cau-hai-lab/SSDi8` @ the pinned `c10ccde6` + its `license.txt` | The exact scope of the non-commercial restriction on `kernels/mamba2`, and whether the fixed-point gate quantizer (LR-7) is upstream or LinQuant's. **Not readable here — submodule uninitialised** |
| SSDi8's paper (arXiv, Kim et al. 2026, cited as the production baseline) | Whether the 3.5e-3-class PPL deltas LinQuant claims over SSDi8 are within SSDi8's own run-to-run spread — i.e. whether the production rows mean anything at 5e-3 resolution |
| vLLM Marlin QQQ PR #24722 (cited by the repo's own `UPSTREAM_DIVERGENCE.md` as *replacing* QQQ entirely) | Whether the Marlin QQQ path is already dead upstream; would convert LR-5 from "expensive" to "moot" |
| `ggml/src/ggml-cuda/mmq.cuh` + `mmq-load-tiles.cuh` (in-tree, not a source) | LR-3. Listed here because it is the deciding artefact and nobody has read it for CDNA2 int8 |
| Quamba2 (intake-2646), already indexed — but its *kernel* section is what matters here | Whether the "INT8 stored state with FP32 carry" idea has a second independent implementation, which would raise confidence in LR-4's design-only keep |

## Artifact audit

All hashes computed on this host from the shallow clone; every quote above was byte-compared to its cited line
before hashing (no quote failed).

| File | Bytes | sha256 |
|---|---|---|
| `linquant/reference.py` | 13 180 | `b9817b7e83cee759b1772ac3ca2c7afd7b6697842fa40d2ff634dd95c2367c50` |
| `linquant/invariances.py` | 7 604 | `d71ee34c516480817b6279c7684799b4795d70e688b3ea841c31c09b7b59e95d` |
| `linquant/harness.py` | — | `0667f87805e2ebeefc275e1b324cdae799d2245e26945ffd8f45bc8bf1ef6fd2` |
| `linquant/run.py` | — | `03ac9d822418680f791714aed71d22a9d3821c85ddf9fc23aa83e8a6190d7cfb` |
| `linquant/quantized_mamba2.py` | — | `abfa861b27faa4c98c335c03da9db36ce71d3af47306c75546375afc019d747c` |
| `linquant/kernels/zoo/gated_delta_rule.py` | — | `682f96e9c1af8c24a37eef8a66685fc95771d14d8bb144e9aa6c67fa97247ac2` |
| `linquant/kernels/zoo/gla.py` | — | `a0c07a322a9629768b1b7030ea0446b6556c573d77ba262a12ca8f905cee390b` |
| `linquant/kernels/zoo/kda.py` | — | `6582c170b2b7975d9abe3e3a003ed725192cd5d1cabdbf285e1d4943efa9aa03` |
| `linquant/kernels/zoo/simple_gla.py` | — | `de0fe10a25b13f42697d94e766c4e515aca2df1405f16f5b79b5479be48c5d40` |
| `linquant/kernels/mamba2/state_passing.py` | — | `0681072d4bd8874959b10c0711dbc5186be1293f06712b9206c22c3c1e3b95ca` |
| `linquant/kernels/mamba2/ssd_combined.py` | — | `d411b616ca984d9abefa0822b9f2dfc408fc4e3044c23040182a29572ea92750` |
| `linquant/kernels/mamba2/bmm_chunk.py` | — | `bb7e7e68d69fec57d8d080e82c4c7fdc7404c74cc63fd126494c5f777f0e92d3` |
| `linquant/kernels/mamba2/chunk_scan_v2.py` | — | `393b81cd6ce8dec4d7cc3824252c4f6cb455a3f3e1a78daac9edb7be31be9478` |
| `linquant/kernels/mamba2/chunk_state.py` | — | `c14a3986dce82853d586a8735a79a23f73f03364453efeb12353fd858fb3d66e` |
| `linquant/kernels/mamba2/chunk_state_keyside.py` | — | `267f6878de0e6949eee476b06bd08d2996418a9bf009fbe2a2210ddcef4adc4e` |
| `linquant/kernels/mamba2/fused_split_rotate_xBC.py` | — | `48b7fc14b0811432eabf2593a2bdb4fd6daa242064ee984693dc3b541d9d2ada` |
| `linquant/kernels/hadamard.py` | — | `b6c3494cca7222d968492f257a984d7c1ee84e5747183e6a31cd1f95338df70c` |
| `tests/test_reference.py` | 10 931 | `6b5f27777d83c75df7115bf4a1a657606da8ebdbe93366b3626bfc7b8a9c97ff` |
| `tests/test_kernel_simple_gla.py` | — | `1574746954f33812cc784dfae9d814e4b1b68446dde4ac9234ce52b0e03b5b1c` |
| `tests/test_kernel_delta.py` | — | `110415c14588b05b8e1d14fa9c739ef779cdbeb338f09da6badbdf6b06e44d53` |
| `tests/test_kernel_gla.py` | — | `a132cd54c5f89258d31125f802788514c6d07ff9b8a37143b0b49fa85ba63bd7` |
| `tests/test_kernel_kda.py` | — | `86e9cb7e94e611c6d94ebe9fee604d9c0345d4bcf1678bda3db4d86663deac08` |
| `tests/test_kernel_regimes.py` | — | `0945f70a7cf5b0da52a8b460100a39c1f0fd4edb9e92db23ffb15301ffe495d2` |
| `LICENSE` | 1 781 | `500cda702bfbaf1cd49f00c4ee8a437377db3056d81cfb0354362174abd7e686` |
| `README.md` | 12 008 | `09b9d823ef352044a21a40ab2daa31cb1004e68ea93ad74bc9e83a42e722d5b4` |
| `pyproject.toml` | — | `71e692b1861b0a065792118e88698e23df527f014b090915ea3b206754e509dd` |
| `patches/ssdi8.patch` | — | `24672e8580c4e4da767643bcd31d324bc076fa7c1918b54a6f85a22ad1722375` |
| `raw/linquant-readme.md` (dive dir, pre-existing) | 12 008 | `09b9d823ef352044a21a40ab2daa31cb1004e68ea93ad74bc9e83a42e722d5b4` — **byte-identical to `README.md` at HEAD**, so Stage 1's read was against the current file |
| `raw/arxiv2610.39418.html` (dive dir, pre-existing) | — | not re-hashed; used only to quote the paper's invariance statements |

Cross-check on the `raw/` artefact: the README on disk and at HEAD hash identically, so no Stage-1/Stage-2
drift in the source of claim 4.

## What this dive changed about the Stage-1 read

1. **"Pure-Triton INT8 chunk kernels" → PARTIAL.** The delta-family WY prep is fp32 torch with a
   `torch.linalg.solve_triangular` launch (and the authors' own timing note says so). This changes the port
   estimate: the hard part of the delta kernels is not Triton at all, it is a host-side solve per layer.
2. **"No CPU execution path" → narrowed to "no CPU *test* path".** `reference.py` + `invariances.py` run on CPU
   as written. That is what makes LR-1 cheap, and it was the single most useful correction.
3. **The llama.cpp gap is smaller and differently shaped than recorded.** The chunked GDN *algorithm* already
   exists in the frozen tree (`build_delta_net_chunking`, CS=64, `solve_tri`, per-chunk state loop). The TODO at
   `gated_delta_net.cu:191` is about the *fused* kernel, and that fused per-token kernel is on the default
   prefill path — so the gap is "fusion + quantization", not "algorithm".
4. **A licensing defect in the release, not just an asymmetry.** `LICENSE` names only `libs/SSDi8` and
   `csrc/marlin_qqq` as third-party while seven in-tree files declare SSDi8 provenance in their own docstrings.
   Treat `kernels/mamba2/**` as non-MIT. Stage 1 recorded the *asymmetry*; the sharper point is that the
   release's own LICENSE under-declares it.
5. **New, not in Stage 1:** the fixed-point gate quantizer saturates the no-forget case (LR-7), and gfx90a's
   INT8 MFMA primitive is present in our tree at `mma.cuh:1314` — which answers intake-2641's open
   "gfx90a integer-dot primitive" question at the *instruction* level while leaving the *dispatch* question
   open (LR-3).
6. **Claim 1's "executable spec" is right but incomplete as a spec of the paper:** two of seven invariances are
   harness-side. Anyone using `reference.py` as the normative artefact needs `harness.py:73-88` too.
