# DeepSeek-V4-Flash 0731 — Q8 Serving + DSpark Speculative Decoding

**Status**: ACTIVE — DSpark support is frozen in production v9 and production-named Q8 `-np 1` parity passes; next work is model/quant research, not kernel promotion. Supersedes [`deepseek-v4-flash-cpu-port.md`](../completed/deepseek-v4-flash-cpu-port.md) (closed: port objective met by upstream PR #24162).
**Created**: 2026-08-09
**Priority**: P2
**Effort**: Medium — kernel integration is complete; the remaining work is an artifact-controlled drafter comparison
**Predecessor**: `deepseek-v4-flash-cpu-port.md` (intake-637, antirez Q4-mixed — artifact deleted 2026-08-09)

## Objective

Serve DeepSeek-V4-Flash-0731 (284B total / 13B active MoE) at lossless Q8 on the EPYC CPU path under frozen production v9 with bounded DSpark drafting. Establish a claim-grade throughput baseline on the **production binary and production recipe** — the predecessor's 8–12 t/s band was measured on an out-of-tree fork with different weights and does **not** carry over.

## Why this is an integration, not a port

Two facts, both verified against the frozen tree on 2026-08-09:

1. **Arch is present.** `LLM_ARCH_DEEPSEEK4` at `src/llama-arch.cpp:81`, landed via upstream `8c146a836` ("DeepSeek V4", PR #24162). Full KV set present: indexer, compressor, hyper-connections (Sinkhorn), `nextn_predict_layers`.
2. **At the v8 starting point, the spec-decode framework was present but the DSpark mode was not.** `common/common.h:170-181` enumerated ten types — `DRAFT_SIMPLE`, `DRAFT_EAGLE3`, `DRAFT_MTP`, `DRAFT_DFLASH`, four NGRAM variants, `DRAFT_TREE`. There was no `DRAFT_DSPARK`. `--spec-type` and `--spec-draft-n-max` already existed as CLI args (`common/arg.cpp:3861,3935`). Production v9 now carries the forward-ported DSpark mode.

The initial estimate treated the kernel delta as a **new draft type inside an existing framework**, with the `DRAFT_DFLASH` integration (`d1b34251b`, PR #22105) as the closest precedent. That estimate is retained below as historical scoping evidence; the 2026-08-10 execution correction records the actual dependency-aware forward-port.

**DSpark ≠ MTP/NextN, but DSpark also is not a separate GGUF architecture.** The DeepSeek-V4 drafter is a separate sidecar whose `general.architecture` is `dflash`. `draft-dspark` selects the DSpark decoding variant implemented on that DFlash backbone: an anchor-first block layout plus a semi-autoregressive Markov head. The target's `deepseek4.nextn_predict_layers` metadata does not substitute for this sidecar.

## Artifacts

Target directory: `/mnt/raid0/llm/models/deepseek-v4-flash-0731/`
Source repo: [`unsloth/DeepSeek-V4-Flash-0731-GGUF`](https://huggingface.co/unsloth/DeepSeek-V4-Flash-0731-GGUF)

| Artifact | Size | Notes |
|---|---|---|
| `UD-Q8_K_XL/…-0731-UD-Q8_K_XL-0000{1..5}-of-00005.gguf` | 167 GB (5 shards) | Lossless. Routed experts (96% of params) kept in **native MXFP4** — no re-quantization error |
| `dspark-DeepSeek-V4-Flash-0731-Q8_0.gguf` | 10,896,057,440 B | Existing control; `dflash`, 81 tensors: MXFP4 9 / F32 41 / Q8_0 25 / BF16 6; block size 5, target layers `[41,42,43]` |
| `DeepSeek-V4-Flash-DSpark-Drafter-Q2_K-Q8_0-dflash.gguf` | 6,971,242,976 B | Checksum-verified standardized comparison artifact; `dflash`, 81 tensors: F32 45 / F16 2 / Q8_0 25 / Q2_K 9; block size 5, target layers `[41,42,43]` |
| `UD-IQ3_XXS/…-0731-UD-IQ3_XXS-0000{1..4}-of-00004.gguf` | 104.208 GB | Research quant; all four published SHA-256 hashes passed 2026-08-11. Routed experts are materially requantized, so this is not a Q8 promotion substitute |

**Quant choice is settled**: UD-Q4_K_XL is 155 GB — only 7 GB below Q8 — because the MXFP4 experts dominate and are preserved either way. Q4 buys nothing here. The real step down, if ever needed, is UD-IQ3_XXS (103 GB) or UD-Q2_K_XL (97 GB).

**Disk**: freed 520 GB on 2026-08-09 (raid0 252 GB → 772 GB avail) by deleting the antirez Q4-mixed V4 (153.3 GB), `unsloth/Qwen3.5-397B-A17B-GGUF/UD-Q4_K_XL` (204.2 GB), and 162.5 GB of zero-reference build intermediates.

### 2026-08-11 standardized drafter acquisition

The operator authorized a smaller, standardized comparison drafter from
[`alessandrobologna/DeepSeek-V4-Flash-DSpark-Drafter-GGUF`](https://huggingface.co/alessandrobologna/DeepSeek-V4-Flash-DSpark-Drafter-GGUF), pinned at revision
`0c8f204aa30677da13c234b4e929212d5d5a0b8c`. Only
`DeepSeek-V4-Flash-DSpark-Drafter-Q2_K-Q8_0-dflash.gguf` was selected. The
publisher manifest declares 6,971,242,976 bytes and SHA-256
`232dd3c3dc3f7082d242e8700940feedc85f6b65cf2991fd35be0a66dad3efa0`.
The completed file at
`/mnt/raid0/llm/models/deepseek-v4-flash-0731/DeepSeek-V4-Flash-DSpark-Drafter-Q2_K-Q8_0-dflash.gguf`
is exactly 6,971,242,976 bytes and its local SHA-256 matches the publisher value. Downloader and
checksum processes exited 0 and were confirmed dead; no incomplete file remains, and the existing
Q8/IQ3 artifacts were untouched.

This is an artifact-control experiment, not a capacity claim. The existing 10.9 GB sidecar and the
selected 6.97 GB sidecar share the DFlash architecture, tensor count, block size and target-layer
map, but their nine low-precision tensors differ (MXFP4 versus Q2_K) and their float carrier types
also differ. With byte count and SHA-256 now passed, run a matched production-v9 cap-0/cap-3 comparison
using the same target, prompt, request settings and host posture, and report throughput, drafted and
accepted tokens, and exact token parity for both sidecars.

## Vendor-recommended runtime

```
--spec-type draft-dspark --spec-draft-n-max 3
```
claimed ~1.9× decode; DSpark costs ~10 GB resident beyond the base model. Sampling: **temp 1.0, top-p 1.0** (0.95 agentic) — this differs from our usual defaults and must be pinned explicitly in any bench per `feedback_bench_defaults`. Max context 1,048,576; Think-Max mode wants ≥384K allocated, so KV sizing dominates planning well before the weights do.

## Phases

### 2026-08-10 execution correction and result

The earlier 14-file greenfield estimate below is retained as historical scoping evidence but is no
longer the execution plan. The sidecar declares `general.architecture=dflash`, and upstream already
merged generic DSpark (#25173), DeepSeek-V4 DSpark (#25784), the DFlash reshape fix (#26577), and the
quantized reshape-stride fix (#26672). The actual work was a dependency-aware manual forward-port
onto exact frozen v8, preserving v8 DFlash/speculation/IQK/ROCm/gfx90a hardening.

Result: `experimental-v9-dspark-autokernel-base` at
`2ac4b32a01a6d97af1c85889443472fbd4a1e12e` (binary 10123), based exactly on
`67a433bf45a8a091d83b4ea0b32ff0735fd51800`. CPU and HIP builds pass candidate-local linkage checks.
The full Q8 target and Q8_0 sidecar load; quantized DFlash reshape and recurrent rollback pass. A
bounded `-np 1`, `n_max=3` smoke achieved exact 16-token greedy parity against request-local vanilla,
while actually drafting 18 and accepting 7 tokens.

Upstream issue #25618 is still open. The initial parallel verifier reproduced it on this CPU target
(first divergence at token 15), so v9 uses a narrow serial target verifier for greedy DSpark on
recurrent targets. This is a correctness fallback, not a performance claim. Any later work to recover
batch invariance is outside the current promotion goal. Multi-slot DSpark is rejected at launch
pending #26741. Raw paths and hashes are sealed in
[`artifacts/audit/v9-dspark-autokernel-base-20260810.json`](../../artifacts/audit/v9-dspark-autokernel-base-20260810.json).

### Promotion qualification result (completed 2026-08-11)

The complete v8-versus-v9 procedure repaired the authorized starting candidate to final tip
`0db32c06e3e550065b78311a6031ef3dd2c4f27c`, rebuilt CPU/HIP, and passed the production-role,
linkage, correctness, quality, topology, rollback, and measurement gates. The versioned cutover and
production-named GPU/DSpark certification passed; Q8 DSpark cap 0 versus cap 3 preserved exact
16-token parity, with 18 drafted and 9 accepted at `-np 1`. Production is now frozen v9 and v8 is
the rollback anchor. AutoKernel initialization remained outside this goal.

### Phase 0 — Acquisition ✅ COMPLETE 2026-08-10
- [x] Download UD-Q8_K_XL 5 shards + DSpark Q8_0 sidecar ✅ 2026-08-10 — completed in ~5 h at ~7–10 MB/s unauthenticated. Log: `/workspace/tmp/ds4_0731_download.log`
- [x] Verify shard sizes and `general.architecture = deepseek4` on shard 1; confirm the 0731 revision in `general.name` ✅ 2026-08-10 — **all five shards byte-exact** against the HF manifest (5,257,408 / 49,215,492,960 / 49,700,372,160 / 49,466,495,968 / 13,481,997,024); DSpark sidecar 10,896,057,440 B. Shard 1 headers confirm `general.architecture=deepseek4`, `general.name=Deepseek-V4-Flash-0731`, `general.size_label=256x8.4B`, and an Unsloth chat template with `thinking`/`reasoning_effort` support. DSpark sidecar header confirms it targets `DeepSeek-V4-Flash-0731`. On-disk 161 GiB at `/mnt/raid0/llm/models/deepseek-v4-flash-0731/`; orphaned `.incomplete` chunk from the aborted first attempt removed; raid0 836 GB free.
- [x] Download and checksum the four-shard `UD-IQ3_XXS` research quant ✅ 2026-08-11 —
  revision `fbbb5b93fb787c21338159b0af3318bb3f4d9768`, 104,207,848,032 bytes, all four
  published SHA-256 hashes pass, and no incomplete files remain. Acquisition alone establishes no
  throughput, parity, acceptance, or role-candidacy result.
- [x] Correct the DSpark/DFlash characterization and inventory the existing 10.9 GB control's
  actual tensor composition ✅ 2026-08-11 — DSpark is a decoding variant on a DFlash-architecture
  sidecar, not a separate GGUF architecture; the control is mixed MXFP4/F32/Q8_0/BF16, not uniform
  Q8_0.
- [x] Download and checksum the pinned standardized Q2_K/Q8_0 DFlash artifact ✅ 2026-08-11 —
  6,971,242,976 bytes; publisher SHA-256
  `232dd3c3dc3f7082d242e8700940feedc85f6b65cf2991fd35be0a66dad3efa0` passed; no incomplete file
  remains.
- [ ] Run the matched throughput, acceptance and exact-parity comparison against the existing
  10.9 GB control.
- [ ] **OPERATOR**: decide whether to configure an `HF_TOKEN` on this host. Downloads currently run unauthenticated at **~9 MB/s** (`hf auth whoami` → not logged in; `hf_xet` is already installed, so a token is the only remaining lever). Blocks nothing — the 0731 pull completes either way — but every future multi-hundred-GB acquisition pays the same ~5.5 h/170 GB tax. Credential provisioning is operator-only.
- [ ] Prune the dead ik_llama branch `feature/deepseek4-port` @ `c04881fc0` and the `antirez` remote on that tree. Left in place 2026-08-09 as harmless; it is now unreachable work (the port was superseded by upstream #24162) and should go whenever ik_llama is next garbage-collected. Not urgent — ik_llama is deprecated as a serving path and consumes no serving resources.

### Phase 1 — Baseline on production v8 (no kernel change)
- [ ] Load Q8 under `production-consolidated-v8`, no drafter. Canonical CPU protocol: `taskset 0-95 -t 96`, full OMP env stack, NPS4 — per `feedback_canonical_baseline_protocol` + `feedback_omp_env_stack_required`
- [ ] Record decode t/s + prefill; pair with a correctness check (`feedback_pair_speed_with_correctness_check`)
- [ ] Index the result by **model/quant, never role** (`feedback_model_not_role_indexing`)

### Phase 2 — DSpark integration (experimental branch only)

**Historical estimate, corrected 2026-08-10.** An earlier note in this handoff called the delta "one enum member
plus loader and verify path". That understates it. The closest precedent — the DFlash spec-type
integration `d1b34251b` (PR #22105) — touched **14 files / ~712 insertions**, including a new
276-line drafter model implementation. This estimate incorrectly inferred a separate DSpark model
architecture; the shipping sidecar is `dflash`, and production v9 implements `draft-dspark` by
specializing the shared DFlash path. The table below is retained only to preserve the superseded
estimate that motivated the later upstream-dependency audit.

The DFlash surface, as the file-level template to mirror:

| File | DFlash delta | DSpark analogue |
|---|---|---|
| `common/common.h` | +3 — the `COMMON_SPECULATIVE_TYPE_DRAFT_DFLASH` enum member | add `..._DRAFT_DSPARK` |
| `common/speculative.cpp` | **+303** — draft generation + verify path | the bulk of the work |
| `src/models/dflash.cpp` | **+276 (new)** — drafter graph | new `src/models/dspark.cpp` |
| `src/models/models.h` | +16 — model decl | ditto |
| `src/llama-arch.{h,cpp}` | +1 each — arch enum + name | only if DSpark declares its own arch |
| `src/llama-model.cpp` | +6 — construction dispatch | ditto |
| `src/llama-graph.cpp` | +7 — graph wiring | ditto |
| `src/llama-context.cpp` | +4 | ditto |
| `gguf-py/gguf/constants.py` | +18 — tensor/KV names | ditto |
| `conversion/{__init__,qwen}.py` | +53 — converter | only if we ever convert; the sidecar ships as GGUF |
| `tests/test-llama-archs.cpp` | +4 | **required** — mirror for `--arch dspark` |
| `docs/speculative.md` | +29 | document the new `--spec-type` value |

Tasks:
- [x] Audit current upstream and identify the merged dependency closure (#25173, #25784, #26577,
  #26672 plus intervening DeepSeek/cache/backend fixes) ✅ 2026-08-10
- [x] Create fresh `llama.cpp-experimental` candidate from exact frozen v8 ✅ 2026-08-10
- [x] Read sidecar metadata; confirm `general.architecture=dflash` and avoid a false new-architecture
  implementation ✅ 2026-08-10
- [x] Manually forward-port the dependency closure while preserving v8 hardening ✅ 2026-08-10
- [x] Build CPU and HIP candidates; prove each binary's local llama/ggml linkage ✅ 2026-08-10
- [x] Validate real target loader/reshape, focused backend ops, recurrent rollback, request isolation,
  single-slot guard, and bounded greedy token parity ✅ 2026-08-10
- [x] Run the complete v8-versus-v9 promotion qualification from the repaired final candidate ✅ 2026-08-11
- [x] Execute the authorized versioned v9 cutover and production-named GPU/DFlash/DSpark
  certification ✅ 2026-08-11 — DFlash capability works, but the Qwen3.6-27B Q8 lane remains disabled
  because pooled acceptance was 35.954% versus the ratified 60% floor.

### Phase 3 — Quality parity
- [ ] Reuse the predecessor's 20-prompt logprob-parity protocol (`v4_quality_gate_runner.py` + `v4_quality_gate_compare.py`, 34 comparator tests pass). The Mac/ds4 external reference dependency is **dissolved** — with the arch in mainline, take parity against a mainline build
- [ ] Measure acceptance rate α for DSpark before drawing any spec-dec conclusions (`feedback_measure_alpha_before_specdec_investment`)
- [x] Run a bounded IQ3_XXS cap-0/cap-3 parity and throughput observation ✅ 2026-08-11 —
  production v9 CPU, `-np 1`, nominal 2,048 context, 64 completion tokens: cap 0
  4.82846 t/s versus cap 3 4.61014 t/s (`0.95478×`, −4.52%). Exact token parity passed;
  cap 3 drafted 67 and accepted 40 (59.70%). This is a one-rep dirty-host observation with the
  resident production stack left online, not a claim-grade speed or quality result. Receipt:
  `epyc-inference-research/data/deepseek-v4-flash/iq3-dspark-quick-20260811T063729Z/summary.json`
  (SHA-256 `950073f53dc56bf7e3629491ec8d0568f8ff86a8b40496f5f565babce70ce26e`).

### Phase 4 — Role candidacy
- [ ] Only after Phases 1–3: evaluate against `architect_general` (which tolerates lower t/s — Qwen3.5-122B at 12 t/s is documented production), not `worker_general`
- [ ] Promotion of any DSpark-carrying binary follows the four-step experimental→production rule; production v8 is never patched in place

## Open questions

- Does upstream PR 25784 apply cleanly to our v8 tip, or has mainline diverged enough to need a manual port?
- Is DSpark's draft compatible with the MXFP4-expert Q8 quant, or does it assume a specific target quant?
- KV footprint at Think-Max (≥384K ctx) on top of 169 GB resident — does the 1.1 TB budget hold with the rest of the fleet co-resident?

## Cross-references

- [`deepseek-v4-flash-cpu-port.md`](../completed/deepseek-v4-flash-cpu-port.md) — predecessor, CLOSED 2026-08-09
- [`moe-spec-cpu-spec-dec-integration.md`](moe-spec-cpu-spec-dec-integration.md) — MoE spec-dec integration surface
- [`speculative-decoding-mtp-refresh.md`](speculative-decoding-mtp-refresh.md) — sibling drafter work
- [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md) — adjacent upstream arch tracking
- [`inference-research-index.md`](inference-research-index.md) · [`inference-research-index.md`](inference-research-index.md) — parent indices

## Progress checklist

- [x] Predecessor closed; upstream #24162 confirmed as the port's resolution ✅ 2026-08-09
- [x] Disk reclaimed (520 GB) and 0731 acquisition started ✅ 2026-08-09
- [x] Phase 0 — acquisition verified ✅ 2026-08-10 — all 5 shards byte-exact + DSpark sidecar; 0731 revision confirmed in `general.name`
- [x] Phase 2 effort re-scoped against the DFlash precedent ✅ 2026-08-10 — 14 files / ~712 insertions, not "one enum member"; file-level template recorded in Phase 2
- [ ] Phase 1 — production-v8 Q8 baseline (claim-grade; required by v9 promotion qualification)
- [x] Phase 2 — DSpark spec-type on experimental branch ✅ 2026-08-10
- [x] IQ3_XXS research quant acquisition and checksum verification ✅ 2026-08-11
- [x] IQ3_XXS bounded DSpark parity/throughput observation ✅ 2026-08-11 — exact 64-token
  parity; 40/67 accepted; cap 3 was 4.52% slower in this single dirty-host repetition
- [x] DSpark/DFlash identity and 10.9 GB control composition corrected ✅ 2026-08-11
- [x] Pinned 6,971,242,976-byte Q2_K/Q8_0 DFlash artifact verified against publisher SHA-256
  ✅ 2026-08-11
- [ ] Run the matched sidecar throughput/acceptance/parity comparison
- [ ] Phase 3 — broaden quality parity beyond the production 16-token exact-parity certification;
  production α observation is 9/18 = 0.50 at `n_max=3`, `-np 1`
- [ ] Phase 4 — role candidacy decision
