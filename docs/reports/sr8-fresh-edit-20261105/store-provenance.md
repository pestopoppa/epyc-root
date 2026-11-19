# gpu-20260921-ffc1bac82 — PRODUCTION (v10), promoted 2026-09-22

- commit `ffc1bac82` on `ak/champion/llama-cpp-0db32c06e3e5`, build **10303**
- `llama-server --version` verified: `10303 (ffc1bac82)`
- built with `CMAKE_BUILD_RPATH_USE_ORIGIN=ON`; `verify_ggml_linkage.sh` PASS under `env -u LD_LIBRARY_PATH`
- source tree: `/mnt/raid0/llm/tmp/champ2` (the worktree holding the champion branch)
- outgoing kernel archived at `kernels/archive/gpu-20260810-0db32c06e` (v9, build 10125)

## Lineage — two defect fixes on top of the previous champion

```
ffc1bac82  graph: emit the fused MoE top-k op only on CPU-only graphs
d0d70c5fe  model: restore v9's NextN read ordering for gemma4-assistant
ef81196d5  fold: INF-70 CPU champion-3 into the autokernel champion
```

`d0d70c5fe` — the champion could not LOAD the gemma-4-26B MTP drafter (4 of 8 gated CPU roles
unservable) because `8136b3221` replaced this arch's own `nextn == n_layer_all` invariant with a
generic assert demanding the opposite relation. `ffc1bac82` — `ae6031aaa` added
`GGML_OP_MOE_TOPK_NORM` with NO CUDA/HIP implementation, so every MoE model on GPU split its graph
at each routing node and round-tripped through host memory: **-30% on Qwen3-VL-30B**, found by
bisect over 89 revisions. Dense models never build that node, which is why the 27B cell passed and
it sat in the champion for three weeks.

## Qualification

`artifacts/operator/v10-qualification-20260921-ffc1bac82.json` (epyc-root). CPU speed 4/4 models
(1.0655-1.5787 vs v9), CPU quality 4/4 suites equal-or-better with 0 errors, GPU 27B 1.088-1.319,
GPU VL-30B 1.0047-1.0897, gated against the post-BIOS serving floor 7.249% [6.024, 9.371] n=24.

## Known residue

RUNPATH ends in an EMPTY element (`$ORIGIN:` cpu / `$ORIGIN:/opt/rocm/lib:` gpu), so the loader also
searches the CWD. v9's archived binaries are clean `[$ORIGIN]`. Not exploited here — every launcher
sets an explicit cwd — but fix it at the next rebuild, and assert it mechanically rather than with a
`grep RUNPATH | grep ORIGIN`, which passes on `/some/abs/path:$ORIGIN`.

Executable set: 91 vs v9's 92 — `test-gguf-model-data` and `test-quant-type-selection` (TEST targets)
are absent, `llama-rowexact` is new. All five binaries `executor.py` resolves are present.
