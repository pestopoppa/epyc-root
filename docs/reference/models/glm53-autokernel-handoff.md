# GLM-5.3-Flash source handoff for AutoKernel

**Experimental reuse base — NOT ACCEPTED:** [`pestopoppa/llama.cpp`](https://github.com/pestopoppa/llama.cpp/tree/ak/champion-glm53-candidate-20260909), pushed branch `ak/champion-glm53-candidate-20260909`, commit `c463f601bd39d0e313b744c214b8c22f9455bcd3`. Champion remains `ef81196d5bdd4190b46dff4ae7eecc333a46c8ce`.

**Experimental reference tip:** branch `experimental/glm53-text-mtp-20260908` points to `f8e2668b6a951d7c44f3264f87d1bc882299bae5`.

Commit `c463f601b` is the clean integration core: it is 12 commits ahead of champion `ef81196d5` and contains text/MTP support, the validated Q8-prefill path, row-exact parallel verification, and the long-prefill fix. The branch tip `f8e2668b6` is 16 commits ahead of the champion and preserves the later default-off expert/Q8 experiments plus their tests; `c463f601b..f8e2668b6` contains no retained optimization. Use the core commit as the source base for regression investigation and a future GLM candidate, and use the tip as the source/test reference for future kernel discovery. Admission remains blocked by the measured CPU performance signal below.

Do not start from an ephemeral benchmark binary or mutate the current champion or production kernel: production `production-consolidated-v9` is frozen and predates `glm5next` support. Fetch the private fork, check out the chosen exact commit above, and create a new experimental AutoKernel worktree/branch. The local reference tree at `/mnt/raid0/llm/llama.cpp-experimental-glm53-20260908` is clean at `f8e2668b6`, and `git ls-remote fork refs/heads/experimental/glm53-text-mtp-20260908` resolves to that SHA. No champion mutation or production promotion has been performed.


See the [verified AutoKernel memory receipt](glm53-autokernel-memory-seed-20260909.md) for the four retrievable experiment records, copied evidence and inbox entry.

## Integration acceptance hold (2026-09-09)

The operator approved seeding AutoKernel memory with this work instead of accepting the candidate with unresolved CPU performance. Reuse the implementation and evidence; do not repeat the architecture port from scratch or infer champion acceptance from functional passes.

- Original last-night CPU harness, Qwen3.8-Flash-Next native MTP: **32.152575 tok/s**, versus historical mean **43.280708 tok/s** (−25.71%). All 24 outputs and draft counters match, and both original contention screens pass. This is one candidate launch against historical observations, not a paired causal estimate; the acceptance hold remains unresolved.
- Exact last-night GPU recipe, Qwen3.8-27B DFlash2 single stream: **79.598706 tok/s**, versus historical median **79.245255 tok/s**. One measured sample after the original warmup; no slowdown signal, no claimed speedup. The earlier 65.06 tok/s cold smoke used a different test and is not the matched comparison.
- Fresh c463 GLM validation: 31/31 exact plain/MTP pairs, 5,419 accepted speculative tokens, 2,949 verified rejected tokens, and rollback/replay/state/alias gates passed. This proves GLM capability, not cross-model performance acceptance.

Primary evidence:

- CPU: `/mnt/raid0/llm/tmp/qwen-glm-core-fold-20260909/exact-lastnight-c463-20260909T1224Z/result.json`
- GPU: `/mnt/raid0/llm/tmp/glm53-validation-20260908/exact-maxperf-candidate-c463-20260909T122252Z/result.json`
- GLM: `/mnt/raid0/llm/tmp/glm53-validation-20260908/champion-core-pair-c463f601b-20260909T105800Z/comparison-audit.json`

AutoKernel must resolve the CPU discrepancy before admitting this core. The operator authorized the champion fold conditional on regression clearance; the unresolved Flash-Next CPU throughput result leaves that condition unsatisfied. The memory seed itself authorizes neither champion mutation nor production promotion.

## Supported scope

The branch loads and runs the six-shard text-only GLM-5.3-Flash `glm5next` model, including hybrid KDA recurrent attention, pooled sparse attention, hyper-connections, and the embedded NextN head. Native speculative decoding is supported through `--spec-type draft-mtp`; validation covers actual accepted and rejected drafts, rollback, used-MTP context restoration, recurrent/pool state, chunked long-prefill export, both `glm5next`/`glm5-next` aliases, and real-model row-exact replay. Vision was intentionally excluded.

The model used for all final CPU work is:

```text
/mnt/raid0/llm/models/unsloth/GLM-5.3-Flash-GGUF/UD-Q4_K_XL/GLM-5.3-Flash-UD-Q4_K_XL-00001-of-00006.gguf
```

It resolves the full six-shard UD-Q4_K_XL distribution. Keep the pinned model-manifest checks used by the validation runner; do not substitute a Q8 model when evaluating the Q8 projection experiment.

## Build

A matching CPU build uses Release, native CPU instructions, OpenMP, and no HIP:

```bash
CC=/usr/bin/gcc-15 CXX=/usr/bin/g++-15 cmake -S . -B build-glm53-cpu \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_NATIVE=ON \
  -DGGML_OPENMP=ON \
  -DGGML_HIP=OFF
cmake --build build-glm53-cpu --parallel
```

The final immutable experimental-reference snapshot is `/mnt/raid0/llm/tmp/glm53-validation-20260908/candidate-f8e2668b6/bin`. Its identity manifest is the adjacent `IDENTITY.json`; it reports `llama-server` version 10317, GCC 15.2.0, server SHA-256 `a972f458d680538fcb1d5a026562733201d7c905959df10f77bc9b27e50b40cf`, and `libggml-cpu.so` SHA-256 `e8c93f6c095fa642bef1c72fb156d1ca98a17666fea63dfac702416d3fdcf451`. Rebuild from source for new work and record fresh binary/library identities. The snapshot proves the experimental reference tip; earlier retained-recipe gates are rooted at `c463f601b` and its serving-equivalent build as documented in the CPU report.

## Canonical 48-thread CPU launch

Use an isolated environment, CPUs 0–95, 48 compute threads, and interleaved NUMA placement:

```bash
env -i \
  GGML_FA_SPLIT_KV=0 GGML_FUSED_DECODE_OFF=1 GGML_IQK=1 \
  GGML_IQK_Q8_0=1 GGML_IQK_Q8_0_MIN_ROWS=32 GGML_ROWEXACT_N=16 \
  GGML_NOHUGEPAGE_PROCESS=1 LLAMA_SPEC_EXACT=row LLAMA_TRACE=1 \
  OMP_DYNAMIC=false OMP_PLACES=cores OMP_PROC_BIND=spread OMP_WAIT_POLICY=active \
  LD_LIBRARY_PATH="$PWD/build-glm53-cpu/bin" PATH=/usr/bin:/bin \
  taskset -c 0-95 numactl --interleave=all \
  build-glm53-cpu/bin/llama-server --no-webui -np 1 -c 8192 -t 48 \
  --no-mmap -lv 4 --device none -ngl 0 -fa on -ctk f16 -ctv f16 \
  -m /mnt/raid0/llm/models/unsloth/GLM-5.3-Flash-GGUF/UD-Q4_K_XL/GLM-5.3-Flash-UD-Q4_K_XL-00001-of-00006.gguf \
  --spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-p-min 0 \
  --reasoning off
```

Run under the orchestrator physical CPU-region lock. Preserve `-np 1`, MTP depth 3, `LLAMA_SPEC_EXACT=row`, and the Q8-prefill threshold when comparing kernels. Depth 2 was rejected because it diverged from the reference at generated token 58.

## Experimental-kernel disposition

The source retains two guarded experiments for future discovery, both disabled by default:

- `GGML_IQK_EXPERT_MULTIROW=1` batches exact Q4_K/Q5_K expert rows. Its operator microbenchmark improved, but its exact one-request short full-model screen measured 9.7305 versus 9.8985 tok/s, so it was not retained.
- `GGML_Q8_ROWEXACT_BATCH=2` batches exact dense Q8 verification rows. It passed operator and speculative-replay gates, but the balanced five-request short full-model screen averaged 9.0863 versus 9.2318 tok/s for mode 0, so it was not retained.

The former `GGML_CPY_OUTER_ROWS` experiment was removed by `f8e2668b6`. Route verification proved that the costly recurrent state copies were contiguous and already used the 48-worker block path; the synthetic padded-copy speedup targeted a layout absent from the GLM graph. Do not resurrect it from commits `068db793f`/`a4ec393a9` without new model-route evidence.

This optimization round produced no additional full-model speed gain. The useful existing recipe remains Q8 prefill acceleration plus reference-correct parallel MTP from the earlier candidate. AutoKernel should use output-token throughput with MTP enabled as its decode objective, while requiring exact token trajectories, real accepted/rejected drafts, and rollback/replay parity before accepting a candidate.

## Evidence and required gates

- [Architecture/source audit](glm53-flash-support-audit-20260908.md)
- [Validated CPU recipe and baseline results](glm53-cpu-optimization-20260908.md)
- [Profile and next-lever analysis](glm53-cpu-next-levers-20260909.md)
- [Worker-route correction](glm53-cpu-worker-audit-20260909.md)
- Balanced Q8 repeat: `/mnt/raid0/llm/tmp/glm53-validation-20260908/q8-retained-short-balanced-20260909T094600Z`
- Final speculative regressions: `/mnt/raid0/llm/tmp/glm53-validation-20260908/final-spec-regressions-candidate-f8e2668b6-20260909T094115Z`
- Source-contained fixtures and launchers: `tests/glm53/`, `tests/test-glm5next-mtp-rollback.cpp`, `tests/test-glm5next-mtp-state-kpool.cpp`, and `tests/test-glm5next-rowexact-phase.cpp`

A candidate must first pass focused bitwise/operator tests, then both aliases' rollback/state/export fixtures, then a real-model run with actual draft rejection. Performance selection uses same-build guard-off controls with fixed warmups and bracketed/interleaved server blocks. For a decode-only experiment, failure of the short repeated decode gate stops the longer decode campaign; a prefill-specific candidate still requires its own matched prefill gate. Any integration into a newer champion also requires full cross-model CPU and HIP regression before promotion. Production promotion remains a separate operator decision.

AutoKernel seed completed and independently retrieved: four `measured_null` records in `/mnt/raid0/llm/autokernel/loop-memory/experiments.db`, campaign `ak-external-glm53-core-20260909`. Inbox `24-glm53-core-c463-external.md` is read by the normal loop. Self-contained evidence bundle: `/mnt/raid0/llm/autokernel/loop-memory/external/glm53-core-c463-20260909`; receipt `ingestion-receipt.json`. Envelope SHA-256 `6ab1cd967603a6feb1ef369cc16a3756ea7eb3fd85e924ed847fff1a3cc9507f`. Idempotence verified (four initial inserts, zero duplicate inserts); records are cross-epoch/noncomparable and cannot advance champion.
