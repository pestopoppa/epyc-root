# Sources: TensorFold 1.1.4 review (2026-10-24)

The reads were done between 2026-10-24 21:30 and 23:00 UTC. Every external file was downloaded by `curl`
into `/mnt/raid0/llm/tmp/tensorfold-114-review-20261024/dl/` and read from disk. Nothing downloaded was
executed. No clone, build or benchmark was run, and no git write was made.

## Pinned revisions

| What | Value |
|---|---|
| Repository | https://github.com/ashhart/TensorFold (`curl -sIL` returned HTTP/2 200 with no redirect, so the canonical owner/name is unchanged) |
| v1.1.4 tag object | `585df8ba3e307d9e4bcea1d6c28a58c8dc1b5682` → commit **`eab8582819688325e371907e4706e1c602b8a273`** (published 2026-10-24T19:16:45Z) |
| v1.1.3 tag object | `9c3b5ecacf005b70f726e1d3e036e884e53a69df` → commit **`36415df4f76e4458e82d0fa729ecb28e287ebf38`** (published 2026-10-23T21:26:56Z) |
| Range v1.1.3...v1.1.4 | 214 commits, 564 files (compare API with 3 pages; the `.diff` has 564 `diff --git` headers) |
| Prior coverage | intake-1924#record (stage1-unverified) covered v0.2.0 to v0.6.5 (2026-10-03). Its scratch REPORT `/mnt/raid0/llm/tmp/tensorfold-research-20261004/REPORT.md` is **no longer on disk**: the directory is gone. The 0.6.5 coverage was therefore reconstructed from the intake-1924#record record (`research/intake_index.yaml` L246326-246390) and from the 27B inbox note 10, which cites that REPORT's §3/§4. |

## Release-level documents (sha256 of the downloaded bytes)

| URL | Local file | sha256 |
|---|---|---|
| https://api.github.com/repos/ashhart/TensorFold/releases?per_page=15 (v1.1.4 and v1.1.3 release bodies) | `dl/releases.json` | `f044f1dbf4b34c6802212943a0e3bd0413cc11488ebad5486d2c8da3c89b51d7` |
| https://github.com/ashhart/TensorFold/releases/tag/v1.1.4 | (body from the API above) | — |
| https://raw.githubusercontent.com/ashhart/TensorFold/v1.1.4/CHANGELOG.md (the §1.1.4 section is L5-87) | `dl/CHANGELOG-v1.1.4.md` | `e582af69baca752c51860f9acc45509b6da368c246a04e0bf5bb3e2d8f2c290c` |
| https://github.com/ashhart/TensorFold/compare/v1.1.3...v1.1.4.diff | `dl/v113_v114.diff` (split per file into `dl/split/`) | `2e9d5c4fe4ecc82af38523e5510c33be2cc7284ed074a1d004c3c523fc8790b8` |
| https://api.github.com/repos/ashhart/TensorFold/compare/v1.1.3...v1.1.4 (pages 1-3) | `dl/compare*.json`, `dl/compare_shas.txt` | — |
| https://api.github.com/repos/ashhart/TensorFold/git/trees/eab85828…?recursive=1 | `dl/tree-v114.json` (7,671 entries, not truncated) | — |
| https://raw.githubusercontent.com/ashhart/TensorFold/eab85828…/docs/kernel-contract.md | `dl/v114files/kernel-contract.md` | `fef8bb1c1927f5f1e77b546f2f7f6581502e60a65fb99b9b24fc6eca705fa576` |
| https://raw.githubusercontent.com/ashhart/TensorFold/eab85828…/zig/kernels/cuda/ggml.cu | `dl/v114files/ggml.cu` | `5a2290c2095fa925faebcc64afc11216161e9addb2e4aa87bf2e3deb8e9c32bc` |

## Pull requests read (bodies saved as `dl/prs/<n>.json` and `.body.txt`; hashes in `dl/prs/SHA256SUMS`)

| PR | Title (short) | Author/receipt hardware |
|---|---|---|
| https://github.com/ashhart/TensorFold/pull/1079 | Qwen3.8-27B decode 9-15% faster with DFlash2 | RTX 5090 |
| https://github.com/ashhart/TensorFold/pull/1080 | long-prompt prefill 5.4x (4096-row chunks, TC attention, delta-rule chain) | RTX 5090 |
| https://github.com/ashhart/TensorFold/pull/1168 | decode attention on tensor cores (fp8 and bf16 caches) | RTX 5090 |
| https://github.com/ashhart/TensorFold/pull/1138 | segmented split-K for the decode projections of one input | A10, RTX 3090 |
| https://github.com/ashhart/TensorFold/pull/1219 | attention partials with rows fastest in the grid (L2 reuse); merge commit `d189172aaa59f3716f12ad311cf32e5f2ead9fe3` | GB10 |
| https://github.com/ashhart/TensorFold/pull/1069 | Flash Next: several streams' drafted windows verified in one pass | GB10 |
| https://github.com/ashhart/TensorFold/pull/1155 | Flash Next: batched MTP heads across streams | GB10 |
| https://github.com/ashhart/TensorFold/pull/1217 | Flash Next: prompt DeltaNet block in one kernel per value head | GB10 |
| https://github.com/ashhart/TensorFold/pull/1195 | Flash Next: PLE gather worker pool | GB10 |
| https://github.com/ashhart/TensorFold/pull/1176, /1054, /1173 | int8 prompt; GLM Metal DSA scan; window-cost table | fetched, summarised from the commit messages |

## Commits read (`.patch` from `https://github.com/ashhart/TensorFold/commit/<sha>.patch`; hashes in `dl/commits/SHA256SUMS`)

All of these are inside the v1.1.3...v1.1.4 range (checked against `dl/compare_shas.txt`).

| Short SHA | Subject (short) |
|---|---|
| `a56d0ce2fa` | attention partials, rows fastest in the grid, K/V shared in L2 (#1219) |
| `ffa87d9960`, `595c135a74` | fp8 / bf16 decode attention on tensor cores (#1168) |
| `c50b59a234`, `184a938e3a` | 4096-row prompt chunks, TC prompt attention, head-major and e4m3 caches, delta-rule chain, 2x2-warp prompt tile (#1080) |
| `bdab57f7a9`, `11e9b4db18`, `fc746287e2`, `39ffc1605a`, `8a09bcfc9d`, `997844743e`, `eb0d391600`, `995f98af68`, `dac4d9632a`, `e475e90fb9`, `d9373fef16`, `8a15c8a4bf` | the 27B DFlash2 verify-round series (#1079) |
| `69e491cbc5` | `--prompt-precision int8` (w4a8 prompt GEMM) (#1176) |
| `7c1f090391` | segmented split-K (#1138) |
| `14ae735699` | window-cost table keeps the fastest timed run (#1173) |
| `aa6fbd8903` | GLM-5.3 Metal DSA indexer scan, blocked (#1054) |
| `d0d179497e` | Flash Next fused GDN prompt block (#1217) |
| `cb60c86d0d`, `5e77d736c5` | Flash Next shared verify, batched MTP heads (#1069, #1155) |
| `89a762a47f`, `6587f77b76`, `2d27f39973`, `e72a34ae38`, `0c73b158de`, `ef757394b7`, `f573774d2a`, `269bdf5626`, `166272881a` | Nemotron-H native HIP series (#1082-#1103) |
| `1b67f7c897` | DeepSeek-V4.1 four-rank prefill planning (host-side only) |

## Local (EPYC) sources read, read-only

| Path | Revision / note |
|---|---|
| `/mnt/raid0/llm/llama.cpp` (production v10 tree) | HEAD `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`. Files: `ggml/src/ggml-cuda/fattn.cu` (chooser L408-600), `fattn-common.cuh` (whole-view K/V to-f16 conversion L1022-1041; grid L1176-1178), `fattn-wmma-f16.cu` (L100-103, no GQA packing), `fattn-tile.cuh` (ncols2 GQA packing present), `tools/server/server-context.cpp` (L500 drafts join the shared batch; L3078-3143 one `common_speculative_draft` call per iteration), `ggml/src/ggml-cpu/ops.cpp` (L11134-11154 GDN in-kernel snapshot slots), `src/models/qwen4exp*.cpp` |
| `/mnt/raid0/llm/autokernel/campaigns/ak-27b-gpu-verify-20261004/store/inbox/10-fable-gpu-multirow-gemv-20261004.md` | §0 arithmetic, rocprof B (FA 29 ms + kv_convert 8 ms at 80k), H1-H13, §4 "do not re-seed" |
| `/mnt/raid0/llm/autokernel/campaigns/ak-ds41-1017-cpu-decode-20261021/store/inbox/30-ds41-1017-mxfp4-seeds-20261021.md` | house style of a seed note, S1-S5 |
| `/mnt/raid0/llm/autokernel/campaigns/ak-q38fn-cpu-decode-20261003/store/inbox/60-…`, `61-…`, `62-q38fn-structural-falsifier-verdicts-20261004.md` | census: CPY 9.4%, GDN 8.3%, routed-and-shared DROP (0%), sibling pack KEEP |
| `/mnt/raid0/llm/epyc-inference-research/scripts/kernel_rnd/autokernel/controller/inbox.py:34`, `loop/run.py:3808`, `loop/actors.py:1569, 2971-2974`, `loop/seed.py`, `loop/seeds/hypotheses/` | the seed-loading mechanism (read through a subagent) |
| `/workspace/handoffs/active/autokernel-all-devices-all-dimensions.md` | AKX-ALL-19, -24, -25, -29.x, -LB1..LB4; on origin/main `6f2011142` the highest ID is AKX-ALL-29, so AKX-ALL-30 and up are free |
| `/workspace/handoffs/active/deepseek-v41-flash-evaluation.md` | L1211-1224 (DS41-C123: the indexer and top-k grow with context), L1748 (DS41-C123.1) |
| `/workspace/handoffs/active/kv-unified-stack-rollout.md` | KVU-19b (L717-851), KVU-16f/g |
| `/workspace/research/intake_index.yaml` | unbounded dedup sweep: the URL `https://github.com/ashhart/TensorFold` matches exactly at L246328 (intake-1924#record); TensorFold is also mentioned in intake-1923, -1937, -1951, -1956 and -1959; the last ID on origin/main is intake-2510 |
