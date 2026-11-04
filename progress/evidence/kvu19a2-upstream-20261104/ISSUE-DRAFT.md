# Historical HIP TILE flash-attention repeatability difference with an experimental guarded-loop patch (MI210, D512/D576)

**Draft only — not posted.** This reports two archived experiments from 2026-11-02. It does not establish that current upstream master or a production release is affected. The candidate is a local experimental patch; the baseline also comes from the identified project source commit, not an asserted clean upstream release.

On one AMD Instinct MI210 (`gfx90a:sramecc+:xnack-`, wave64, reported VRAM 65,520 MiB), a model-free `ggml_flash_attn_ext` harness produced bit-identical baseline output across five fresh processes per case, while the guarded-loop variant produced five distinct outputs per case. Actual saved inputs matched byte-for-byte across the two arms and the canonical input digests. Mask skipping was explicitly disabled with `GGML_CUDA_FA_MASK_SKIP=0` after clearing inherited `GGML_*` variables.

Could maintainers help review or further reduce this historical TILE-kernel code-shape sensitivity? We have not established its mechanism. The concrete source patch and standalone harness are attached; this is not a request to merge the candidate or the unsuccessful diagnostic barrier change.

The historical commit's external reachability has not been verified. Reproduction requires a repository or source archive containing that exact compatible source; the attached tile and patch alone do not reconstruct the entire tree. No claim is made that applying this patch to latest master reproduces the observation.

## Source and build identity

Baseline source: `a0d0ae238e714aaab04e973ef4b5a4b7c9917744`. Source archive SHA-256: `87e3cdc13b1859a31dfd3ced43c596e6b9653e2194b1ebd0d5eb6772593c04c2`.

Candidate changes only `ggml/src/ggml-cuda/fattn-tile.cuh`, replacing loop-index advancement over dead KV chunks with guarded calls / `continue` in the tile loop. Patch: [sources/guarded-loop.patch](sources/guarded-loop.patch), SHA-256 `4147d2b65bbb416fdee1bf004d5447238933524bf3c087a69dcf6bbeca73b235`.

Tile SHA-256:

| Arm | Tile SHA-256 |
| --- | --- |
| Baseline | `878a3640f685e68c6c3d3102c331c43054bfb0bce81f68c3224ad271b8d9d844` |
| Guarded-loop candidate | `3f79373e68603691630c7dc38703411456cdf5fa12348d07812323568cdb1e82` |

Both arms used the same recorded container toolchain. Configure logs identify GNU C/C++ 15.2.0 and HIP Clang 18.0.0; complete selected-tool hashes are in [container-toolchain.sha256](sources/container-toolchain.sha256), catalog SHA-256 `2b8ad6a514751640eec363b27a3c9dc29fa17e8479a4a2f144bcf80a648c68dd`. Do not infer a complete ROCm package version from that compiler identification.

The source-bound harness in this experiment is [fa_harness.cpp](sources/fa_harness.cpp), source SHA-256 `b9f352a91ea975c682cbe78c2f4dbf9035c6a40e309b84035bfbdaf49b420091`, executable SHA-256 `a41b12fd64a28af97e13d50bcd28a1bb31a9c7a95c5182d7a08c0fa54fef5ed7`. It is distinct from earlier retained/unbound harness experiments. Build and harness receipts are attached, including their join:

- [root-build-receipt.json](sources/root-build-receipt.json): `3b327e7b729e02e38ed377847f4ea890d42852aa4e2300f681be07e86742511f`.
- [root-harness-receipt.json](sources/root-harness-receipt.json): `15e966e5488629fe0f1c9baf309056dda08ea60b262171e8f5df078647a9f3d3`.
- Baseline HIP DSO: `c1207b369ebe2c9fb36e538431e1bf97e9db4add00163dd29ccdc77a6577351c`.
- Candidate HIP DSO: `dd965b9f875f98ee45961d683e84d646f85cd4d44ad2046a265636beb23a4e88`.

## Model-free cases and observations

No model, tokenizer, sampler, or inference server is involved. The harness uses `mt19937(1234)`, Q in F32, K/V cache in F16, a unified-KV F16 mask, attention scale `1/sqrt(hsk)`, F32 attention precision, zero bias, and zero softcap. Cache backing allocates `kv+256` cells. For case78, V aliases the first 512 components of the 576-component K cache; case80 has a separate V cache. Saved inputs are Q/K/mask for case78 and Q/K/V/mask for case80, in that order.

| Case | hsk / hsv | nh / nr2 | kv | nb / nseq | run / free | Q shape | F32 output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 78 | 576 / 512 | 1 / 16 | 8192 | 4 / 4 | 1024 / 1024 | `[576,4,16,1]` | 32,768 elements; 131,072 bytes |
| 80 | 512 / 512 | 1 / 8 | 8192 | 4 / 4 | 1024 / 1024 | `[512,4,8,1]` | 16,384 elements; 65,536 bytes |

The output dimension is **hsv**, not hsk. Each process computed the selected case once. Arm order alternated by repetition. Five samples describe this experiment only; a matching set of five does not prove universal determinism.

| Case | Arm | Distinct output SHA-256 / 5 runs | Varying F32 elements across runs | Maximum within-arm absolute spread |
| --- | --- | --- | --- | --- |
| 78 | Baseline | 1 / 5 | 0 / 32,768 | 0 |
| 78 | Guarded-loop | 5 / 5 | 16,384 / 32,768 | 0.0017658434808254242 |
| 80 | Baseline | 1 / 5 | 0 / 16,384 | 0 |
| 80 | Guarded-loop | 5 / 5 | 4,096 / 16,384 | 0.000479917973279953 |

All 20 processes returned0; saved output values were finite and logs reported zero NaNs. Each run has an executable/library mapping witness and positive own-PID KFD/VRAM samples collected during the recorded process window. Logs also contain `load_backend: failed to find ggml_backend_init in .../libggml-hip.so.0.16.0`; this warning is retained rather than hidden. GPU execution evidence comes from the MI210 device log, mapped HIP bytes and in-window own-PID residency together, not from that warning or executable path alone.

The source-bound native record is preserved at research commit `f8878bf145490c43458aab0fad27eac6514918d5`, path `artifacts/kvu19a2-repeat-20261102/root-bound-native/result.json`, SHA-256 `88af22831fda196b7995bda933769fa3f4720d25253720712bed90f3b6e21c91`. [EVIDENCE-INDEX.json](EVIDENCE-INDEX.json) lists every committed raw-output path and digest, input matches, runtime library pins and independently recomputed descriptive metrics.

## Reproduction recipe from the recorded build

The following commands document the source/build/run recipe; they were **not executed while preparing this draft**. Use an isolated experimental checkout and an approved GPU window. `$SOURCE_REPO` must actually contain the historical commit; it is not assumed available in a current upstream clone. `$REPRO` is a new private directory; copy the attached patch and harness there first. Historical build receipts retain the actual `/dev/shm/...` paths, sealed-memfd harness compile argv and source inventory binding. The archive digest above identifies the historical experiment only; this recipe creates worktrees and makes no new source archive or checkout copies.

```bash
set -euo pipefail
# Create isolated worktrees at exactly the same historical source commit.
git -C "$SOURCE_REPO" worktree add --detach "$REPRO/base" a0d0ae238e714aaab04e973ef4b5a4b7c9917744
git -C "$SOURCE_REPO" worktree add --detach "$REPRO/candidate" a0d0ae238e714aaab04e973ef4b5a4b7c9917744
patch -d "$REPRO/candidate" -p1 < "$REPRO/guarded-loop.patch"
# Verify the attached patch, baseline tile and candidate tile digests above.
# The original source snapshots were root-owned/read-only to the build UID;
# keep equivalent source custody and before/after inventories for a new result.

for arm in base candidate; do
  env -i PATH=/opt/rocm/bin:/usr/bin:/bin ROCM_PATH=/opt/rocm HIP_PATH=/opt/rocm \
    CXX=/usr/bin/g++ CC=/usr/bin/gcc HIPCXX=/opt/rocm/llvm/bin/clang++ HOME="$REPRO" \
    /usr/bin/cmake -S "$REPRO/$arm" -B "$REPRO/build-$arm" \
      -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a \
      -DLLAMA_BUILD_TESTS=ON -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BUILD_TOOLS=OFF
  env -i PATH=/opt/rocm/bin:/usr/bin:/bin ROCM_PATH=/opt/rocm HIP_PATH=/opt/rocm \
    CXX=/usr/bin/g++ CC=/usr/bin/gcc HIPCXX=/opt/rocm/llvm/bin/clang++ HOME="$REPRO" \
    /usr/bin/cmake --build "$REPRO/build-$arm" --target test-backend-ops --parallel 24
done
/usr/bin/g++ -std=c++17 -O2 -x c++ "$REPRO/fa_harness.cpp" \
  -I"$REPRO/base/ggml/include" -L"$REPRO/build-base/bin" \
  -lggml -lggml-base -lggml-cpu -o "$REPRO/fa_harness"

# Fresh output and input directories for every invocation; never overwrite.
mkdir "$REPRO/runs"
for case_id in 78 80; do
  for repeat in 1 2 3 4 5; do
    arms='base candidate'
    if (( repeat % 2 == 0 )); then arms='candidate base'; fi
    for arm in $arms; do
      run="$REPRO/runs/case${case_id}-${arm}-r${repeat}"
      mkdir "$run"
      mkdir "$run/input" "$run/output"
      env -i PATH=/usr/bin:/bin LANG=C.UTF-8 \
        LD_LIBRARY_PATH="$REPRO/build-$arm/bin:/opt/rocm/lib" \
        GGML_BACKEND_PATH="$REPRO/build-$arm/bin/libggml-hip.so" \
        GGML_CUDA_FA_MASK_SKIP=0 FA_CASE="$case_id" \
        FA_INPUT_DIR="$run/input" FA_DUMP_DIR="$run/output" \
        "$REPRO/fa_harness" ROCm0 exact > "$run/native.log" 2>&1
    done
  done
done
```

The loop is a minimal invocation illustration, not a replacement for the attached [recorded producer](sources/repeat_rootbuild.py): for accepted evidence also pin actual compiler-visible source and executable/runtime bytes, compare every captured input against [canonical-input-hashes.json](sources/canonical-input-hashes.json), and capture own-PID birth, mappings and positive KFD/VRAM **during** every process. Missing/incomplete observations remain unknown. The original input generator includes C++ distribution/conversion behavior; the seed alone is not a portable input identity.

## Negative barrier diagnostic

A source review suggested that producer warps returning before a workgroup barrier might explain the variation. An experimental change moved that return after `__syncthreads()`; commit `18d030309a57071c32ffd0db42994ae473d2722a`, attached [barrier.patch](sources/barrier.patch), was tested against the original guarded-loop candidate with the same two cases, five fresh processes per arm/case and matched canonical input bytes.

Both arms again produced five distinct output hashes in each case, with 20/20 mapping and positive in-window residency witnesses. Case78 varied in 16,384/32,768 elements in both arms (maximum spreads 0.0027541331946849823 before and 0.0021391240879893303 after); case80 varied in 4,096/16,384 elements (0.0005635109264403582 before and 0.0006801867857575417 after). All outputs were finite. These descriptive spread changes have no prespecified improvement threshold.

**The barrier change did not restore repeatability.** This experiment does not establish synchronization as the cause, and does not establish that no synchronization defect exists. It is not a proposed fix or a promotion result. Research commit `7a8a2d8fade9ee17368c374c3da42df4f69dfbd6` preserves the result, build receipt and 20 raw outputs under `artifacts/kvu19a2-sync-build-20261102/`; result SHA-256 `515bc1211a2661d02fe47d2c05c13efaa0481b3c871868266070d1b002def607`.

## Limits and related reports

Source snapshots were root-owned and read-only to the build UID, with before/after inventory checks. They were not immutable against privileged root. Selected compiler/tool hashes were pinned, but the full transitive toolchain, dependencies and host environment were not sealed. Receipts and mapped-file hashes do not remove that trust boundary. This is a historical model-free repeatability observation for these exact builds and inputs; it establishes no current-master defect, model-quality loss, speed difference, production defect, deployment need, or general causal mechanism.

A bounded related-issue search on 2026-11-04 found the following context; it is not an exhaustive novelty audit:

- [#30175](https://github.com/ggml-org/llama.cpp/issues/30175): RDNA3 D256 WMMA FA model nondeterminism; different architecture/path and workload from this CDNA2 D512/D576 TILE harness.
- [#14727](https://github.com/ggml-org/llama.cpp/issues/14727): closed RDNA3 model-output nondeterminism report; sameness to this source-pinned standalone case is not established.
- [#31555](https://github.com/ggml-org/llama.cpp/issues/31555): Volta D576 MMA dispatch abort; different architecture, kernel path and failure mode.
- [#28495](https://github.com/ggml-org/llama.cpp/issues/28495): unified-KV throughput limitation; not established as this repeatability difference with mask skipping disabled.

Posting this draft requires explicit operator authorization. No upstream issue has been created by this preparation.
