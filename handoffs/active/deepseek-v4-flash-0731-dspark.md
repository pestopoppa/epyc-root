# DeepSeek-V4-Flash 0731 — Q8 Serving + DSpark Speculative Decoding

**Status**: ACTIVE — created 2026-08-09. Supersedes [`deepseek-v4-flash-cpu-port.md`](../completed/deepseek-v4-flash-cpu-port.md) (closed: port objective met by upstream PR #24162). The `deepseek4` architecture is **already in production** `production-consolidated-v8`; what is missing is (a) the 0731 weights at lossless Q8 and (b) a `draft-dspark` speculative type in our spec-decode framework.
**Created**: 2026-08-09
**Priority**: P2
**Effort**: Medium — a new spec-decode type in an existing framework (~14 files/~712 insertions by the DFlash precedent), not an architecture port
**Predecessor**: `deepseek-v4-flash-cpu-port.md` (intake-637, antirez Q4-mixed — artifact deleted 2026-08-09)

## Objective

Serve DeepSeek-V4-Flash-0731 (284B total / 13B active MoE) at lossless Q8 on the EPYC CPU path under the frozen v8 kernel, then add DSpark drafting to close the decode-rate gap. Establish a claim-grade throughput baseline on the **production binary and production recipe** — the predecessor's 8–12 t/s band was measured on an out-of-tree fork with different weights and does **not** carry over.

## Why this is an integration, not a port

Two facts, both verified against the frozen tree on 2026-08-09:

1. **Arch is present.** `LLM_ARCH_DEEPSEEK4` at `src/llama-arch.cpp:81`, landed via upstream `8c146a836` ("DeepSeek V4", PR #24162). Full KV set present: indexer, compressor, hyper-connections (Sinkhorn), `nextn_predict_layers`.
2. **Spec-decode framework is present, DSpark is not.** `common/common.h:170-181` enumerates ten types — `DRAFT_SIMPLE`, `DRAFT_EAGLE3`, `DRAFT_MTP`, `DRAFT_DFLASH`, four NGRAM variants, `DRAFT_TREE`. There is no `DRAFT_DSPARK`. `--spec-type` and `--spec-draft-n-max` already exist as CLI args (`common/arg.cpp:3861,3935`).

So the kernel delta is a **new draft type inside an existing framework**, mirroring the `DRAFT_DFLASH` integration (`d1b34251b`, PR #22105) as the closest precedent — measured at **14 files / ~712 insertions**, including a 276-line drafter model. This is **not** the multi-thousand-line arch addition the predecessor scoped (that problem is solved), but it is real implementation work, not a flag flip. File-level breakdown in Phase 2.

**DSpark ≠ MTP/NextN.** DeepSeek replaced naive MTP with DSpark; it ships as a separate sidecar GGUF, not as tensors inside the quant. The `deepseek4.nextn_predict_layers` metadata present in the weights does not provide it.

## Artifacts

Target directory: `/mnt/raid0/llm/models/deepseek-v4-flash-0731/`
Source repo: [`unsloth/DeepSeek-V4-Flash-0731-GGUF`](https://huggingface.co/unsloth/DeepSeek-V4-Flash-0731-GGUF)

| Artifact | Size | Notes |
|---|---|---|
| `UD-Q8_K_XL/…-0731-UD-Q8_K_XL-0000{1..5}-of-00005.gguf` | 167 GB (5 shards) | Lossless. Routed experts (96% of params) kept in **native MXFP4** — no re-quantization error |
| `dspark-DeepSeek-V4-Flash-0731-Q8_0.gguf` | 10.9 GB | DSpark draft sidecar (BF16 variant 11.3 GB also exists) |

**Quant choice is settled**: UD-Q4_K_XL is 155 GB — only 7 GB below Q8 — because the MXFP4 experts dominate and are preserved either way. Q4 buys nothing here. The real step down, if ever needed, is UD-IQ3_XXS (103 GB) or UD-Q2_K_XL (97 GB).

**Disk**: freed 520 GB on 2026-08-09 (raid0 252 GB → 772 GB avail) by deleting the antirez Q4-mixed V4 (153.3 GB), `unsloth/Qwen3.5-397B-A17B-GGUF/UD-Q4_K_XL` (204.2 GB), and 162.5 GB of zero-reference build intermediates.

## Vendor-recommended runtime

```
--spec-type draft-dspark --spec-draft-n-max 3
```
claimed ~1.9× decode; DSpark costs ~10 GB resident beyond the base model. Sampling: **temp 1.0, top-p 1.0** (0.95 agentic) — this differs from our usual defaults and must be pinned explicitly in any bench per `feedback_bench_defaults`. Max context 1,048,576; Think-Max mode wants ≥384K allocated, so KV sizing dominates planning well before the weights do.

## Phases

### Phase 0 — Acquisition ✅ COMPLETE 2026-08-10
- [x] Download UD-Q8_K_XL 5 shards + DSpark Q8_0 sidecar ✅ 2026-08-10 — completed in ~5 h at ~7–10 MB/s unauthenticated. Log: `/workspace/tmp/ds4_0731_download.log`
- [x] Verify shard sizes and `general.architecture = deepseek4` on shard 1; confirm the 0731 revision in `general.name` ✅ 2026-08-10 — **all five shards byte-exact** against the HF manifest (5,257,408 / 49,215,492,960 / 49,700,372,160 / 49,466,495,968 / 13,481,997,024); DSpark sidecar 10,896,057,440 B. Shard 1 headers confirm `general.architecture=deepseek4`, `general.name=Deepseek-V4-Flash-0731`, `general.size_label=256x8.4B`, and an Unsloth chat template with `thinking`/`reasoning_effort` support. DSpark sidecar header confirms it targets `DeepSeek-V4-Flash-0731`. On-disk 161 GiB at `/mnt/raid0/llm/models/deepseek-v4-flash-0731/`; orphaned `.incomplete` chunk from the aborted first attempt removed; raid0 836 GB free.
- [ ] **OPERATOR**: decide whether to configure an `HF_TOKEN` on this host. Downloads currently run unauthenticated at **~9 MB/s** (`hf auth whoami` → not logged in; `hf_xet` is already installed, so a token is the only remaining lever). Blocks nothing — the 0731 pull completes either way — but every future multi-hundred-GB acquisition pays the same ~5.5 h/170 GB tax. Credential provisioning is operator-only.
- [ ] Prune the dead ik_llama branch `feature/deepseek4-port` @ `c04881fc0` and the `antirez` remote on that tree. Left in place 2026-08-09 as harmless; it is now unreachable work (the port was superseded by upstream #24162) and should go whenever ik_llama is next garbage-collected. Not urgent — ik_llama is deprecated as a serving path and consumes no serving resources.

### Phase 1 — Baseline on production v8 (no kernel change)
- [ ] Load Q8 under `production-consolidated-v8`, no drafter. Canonical CPU protocol: `taskset 0-95 -t 96`, full OMP env stack, NPS4 — per `feedback_canonical_baseline_protocol` + `feedback_omp_env_stack_required`
- [ ] Record decode t/s + prefill; pair with a correctness check (`feedback_pair_speed_with_correctness_check`)
- [ ] Index the result by **model/quant, never role** (`feedback_model_not_role_indexing`)

### Phase 2 — DSpark integration (experimental branch only)

**Effort corrected 2026-08-10.** An earlier note in this handoff called the delta "one enum member
plus loader and verify path". That understates it. The closest precedent — the DFlash spec-type
integration `d1b34251b` (PR #22105) — touched **14 files / ~712 insertions**, including a new
276-line drafter model implementation. DSpark is a *new drafting algorithm* with its own sidecar
architecture, so expect a comparable shape. Still far smaller than the multi-thousand-line arch
port the predecessor scoped (the arch is already done), but it is a real integration, not a flag.

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
- [ ] **First, check whether any of this is already upstream.** Before writing code, `git fetch` mainline and look for a merged DSpark spec-type. The whole predecessor handoff was obsoleted by exactly this failure mode — a hand-rolled port that upstream landed independently (PR #24162). If upstream PR 25784 is merged or mergeable, take it instead of hand-rolling.
- [ ] Fresh `llama.cpp-experimental` off current production tip (never a long-lived branch — INC-20260706)
- [ ] Read the DSpark sidecar's GGUF metadata first (`dspark-DeepSeek-V4-Flash-0731-Q8_0.gguf`) to learn its tensor names and whether it declares its own `general.architecture` — that determines how much of the `llama-arch`/`llama-model`/`llama-graph` column above is actually needed
- [ ] Implement per the table; add the `tests/test-llama-archs.cpp` case in the same commit as the model file, not after
- [ ] Validate no regressions vs production, GPU **and** CPU
- [ ] Measure DSpark uplift at `--spec-draft-n-max 3`; sweep n-max rather than accepting the vendor default (`feedback_always_sweep`)

### Phase 3 — Quality parity
- [ ] Reuse the predecessor's 20-prompt logprob-parity protocol (`v4_quality_gate_runner.py` + `v4_quality_gate_compare.py`, 34 comparator tests pass). The Mac/ds4 external reference dependency is **dissolved** — with the arch in mainline, take parity against a mainline build
- [ ] Measure acceptance rate α for DSpark before drawing any spec-dec conclusions (`feedback_measure_alpha_before_specdec_investment`)

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
- [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) · [`inference-acceleration-index.md`](inference-acceleration-index.md) — parent indices

## Progress checklist

- [x] Predecessor closed; upstream #24162 confirmed as the port's resolution ✅ 2026-08-09
- [x] Disk reclaimed (520 GB) and 0731 acquisition started ✅ 2026-08-09
- [x] Phase 0 — acquisition verified ✅ 2026-08-10 — all 5 shards byte-exact + DSpark sidecar; 0731 revision confirmed in `general.name`
- [x] Phase 2 effort re-scoped against the DFlash precedent ✅ 2026-08-10 — 14 files / ~712 insertions, not "one enum member"; file-level template recorded in Phase 2
- [ ] Phase 1 — production-v8 Q8 baseline (claim-grade)
- [ ] Phase 2 — DSpark spec-type on experimental branch
- [ ] Phase 3 — quality parity + α measurement
- [ ] Phase 4 — role candidacy decision
