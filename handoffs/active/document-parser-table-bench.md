# Document Parser Table-Extraction Benchmark — PaddleOCR-VL-1.6 pipeline vs ODL

**Status**: active
**Created**: 2026-07-20 (via research intake deep dive — intake-864/865 reassessment)
**Priority**: P1 — unblocks the long-open "stronger parser comparison" question in [`opendataloader-pipeline-integration.md`](opendataloader-pipeline-integration.md) (task K35.18)
**Categories**: document_processing, multimodal, benchmark_methodology
**Parent**: [`opendataloader-pipeline-integration.md`](opendataloader-pipeline-integration.md) · [`gemma-challenge-kernel-techniques-v7.md`](gemma-challenge-kernel-techniques-v7.md) K35.18

## Objective

Establish, for the first time on a competent instrument, whether we have a table-extraction quality gap — and if so, close it by running **PaddleOCR-VL-1.6 in its real three-stage pipeline configuration** rather than the off-label single-shot invocation that produced meaningless results on 2026-07-17/18.

## Why this exists — three broken instruments, one void result

The 2026-07-17/18 PaddleOCR-VL runs and the conclusions drawn from them are **retracted**. Root causes, all verified 2026-07-20:

1. **Off-label invocation (void result).** PaddleOCR-VL-1.6 is a *three-stage pipeline* (arxiv:2606.03264 §2): **PP-DocLayoutV3** layout analysis → the 0.9B VLM recognizing **cropped regions** under **element-specific prompts** → a post-processing assembler handling markdown, cross-page table merging and heading hierarchy. Its official card ships exactly six prompts (`"OCR:"`, `"Table Recognition:"`, `"Formula Recognition:"`, `"Chart Recognition:"`, `"Spotting:"`, `"Seal Recognition:"`) and **no page-level markdown prompt**; the VLM was trained on isolated element crops, never on full-page→markdown. We fed whole pages with a generic markdown prompt, so layout detection, table-crop dispatch and assembly never ran. `table TEDS = 0.0` with **zero** `<table>` tags *and* **zero** markdown pipe rows across all 9 table-bearing pages is the expected off-label behaviour, not a model defect. **Do not re-cite the 0.0 / 0.058333 TEDS figures.**
2. **Benchmark subset too small and unrepresentative.** Scoring used `OmniDocBench_demo.json` — **18 pages, 10 `table` regions, 64% simplified Chinese**. Under MEASUREMENT.md that is an observation, not a decision-gating number. ODL's oft-quoted `table.TEDS = 0.783813` rests on **n=10**.
3. **Production corpus cannot measure tables.** The 8-PDF `local-valid-pdf-8` set behind the "zero ODL tables despite 1195 table-like lines" finding is **half figure exports**: `Imgs/overview.pdf` (1p), `Imgs/Statistics.pdf` (1p), `Imgs/RQ5.pdf` (1p) and `llama-star/idea-arch.pdf` (2p) are charts/diagrams; only `HY_MT2_0_Report.pdf` (15p) and `echo.pdf` (13p) are substantial documents. Most contain no tables, so `structured_tables=0` is correct, not a failure. `table_like_line_count` is a whitespace/numeric heuristic, **not** a table count.

**Net: we have no evidence of a table-extraction gap — only evidence that we never measured one.**

## What changed — the instrument is now fixed

Full OmniDocBench acquired and integrity-verified 2026-07-20 at `/mnt/raid0/llm/datasets/omnidocbench/` (1662 files, 1.55 GB, HF `main`, 1651-page release, annotations last corrected 2026-04-09; 1651 images, 1651 JSON pages, 0 missing image refs, 0 `.part`).

| | demo (all prior numbers) | full (now local) |
|---|---|---|
| Pages | 18 | **1651** |
| `table` regions | **10** | **665** (on 458 pages) |
| Language | 64% simplified Chinese | 755 EN / 765 ZH / 116 mixed / 13 trad |

The full set carries a per-page `language` attribute, so an **English-only view** matching our actual PDF workload is scoreable. n=665 makes table TEDS a defensible gating metric for the first time.

Fetch script: `/mnt/raid0/llm/tmp/fetch_omnidocbench.py` (idempotent, skip-if-complete by size, no `curl -C -` resume semantics).

## Assets already on disk — no new downloads required

- `/mnt/raid0/llm/models/PaddleOCR-VL-1.6-GGUF/PaddleOCR-VL-1.6-GGUF.gguf` (936 MB) + `-mmproj.gguf` (882 MB), SHA-verified 2026-07-17, revision `511b09642bb324401f15f97cc23bc67e8f0a291d`.
- Dedicated venv `/mnt/raid0/llm/venvs/paddleocr` (Python 3.12) — deliberately isolated from `epyc-inference-research/.venv`, since `odl_bench` only needs to invoke PaddleOCR as a subprocess and PaddlePaddle is a heavy framework that should not enter the research env.
- Scorer + producer: `epyc-inference-research/scripts/benchmark/odl_bench/` (`paddleocr_vl.py`, `compare-existing`, `run-model`).

## Architecture note — this is the *wanted* design, not a workaround

Operator direction 2026-07-20: **the Python orchestrator is desired for the document pipeline precisely because it avoids inference when unnecessary.** PaddleOCR-VL's three-stage shape is therefore a feature: PP-DocLayoutV3 decides *what* needs the VLM, so plain-text pages never trigger inference and only table/formula/chart regions are dispatched. Our `llama-server` remains the compute engine via `--vl_rec_backend llama-cpp-server`. This supersedes the earlier framing that treated "needs a Python pipeline" as a disqualifier.

## Task list

### Phase A — environment (no inference)
- [x] **Install ✅ 2026-07-20**: `paddlepaddle==3.2.2` + `paddleocr==3.7.0` (paddlex 3.7.2) into `/mnt/raid0/llm/venvs/paddleocr` (Python 3.12.13, uv). Venv total **1.4 GB**. **Gotcha recorded**: the resolver pulls `opencv-contrib-python`, which needs `libGL.so.1` — absent in this container, so `import paddleocr` fails with `ImportError: libGL.so.1`. Fixed by swapping to `opencv-contrib-python-headless==4.10.0.84` (uninstall the non-headless first); no system packages required. Re-run this swap after any dependency upgrade that reinstates the GUI build.
- [x] **CLI verified ✅ 2026-07-20**: `paddleocr doc_parser -i ... --vl_rec_backend llama-cpp-server --vl_rec_server_url http://host:port/v1` is available and **`llama-cpp-server` is an explicitly supported backend** (full set: `native`, `vllm-server`, `sglang-server`, `fastdeploy-server`, `mlx-vlm-server`, `llama-cpp-server`). **Do not be misled by `paddleocr --help`** — it lists only `doc2md` and `api` because pipeline subparsers are registered without a `help=` kwarg and argparse omits those from the listing. The subcommand exists and works. Equivalent Python API is `paddleocr.PaddleOCRVL(...)` exposing `layout_detection_model_name`, `vl_rec_backend`, `vl_rec_server_url`, `use_layout_detection`, `merge_layout_blocks` — prefer this for `odl_bench` integration over shelling out.
- [ ] Trigger PP-DocLayoutV3 weight resolution and record the cache path + size (a *separate* download from the GGUF, not yet performed).
- [ ] Confirm the CPU-only path works on EPYC (no GPU assumptions in the layout stage).

### Phase B — correct invocation smoke (bounded inference — **requires operator approval**)
- [ ] Start experimental-v7 `llama-server` with the PaddleOCR-VL GGUF + mmproj on a high port, `--temp 0`.
- [ ] Run the documented pipeline on a handful of **table-bearing** pages from the full set:
      `paddleocr doc_parser -i <page>.png --pipeline_version v1.6 --vl_rec_backend llama-cpp-server --vl_rec_server_url http://127.0.0.1:<port>/v1`
- [ ] **Gate**: confirm HTML `<table>` markup is actually emitted. If still zero, stop — the problem is the harness, not the model, and no full run should be spent.
- [ ] Capture cleanup proof (no stray `llama-server`, 0% VRAM / no KFD PIDs) per existing K35 discipline.

### Phase C — full benchmark (**requires operator approval**; long-running)
- [ ] Re-baseline **ODL end-to-end** on the full 1651-page set. This supersedes `table.TEDS = 0.783813` everywhere it is quoted.
- [ ] Score **PaddleOCR-VL-1.6 full pipeline** on the same set.
- [ ] Report **both** an all-language and an **English-only** (`language: english`, 755 pages) split for every metric. The demo set's 64%-Chinese skew is why prior numbers were misleading.
- [ ] Report table TEDS at **n=665** with TEDS-structure-only alongside, plus text-block edit distance and reading-order edit distance.
- [ ] Persist via `odl_bench compare-existing` into `epyc-inference-research/data/odl_existing_comparison/`.

### Phase D — decision
- [ ] Decide the table path: ODL alone / ODL + PaddleOCR-VL for table regions / PaddleOCR-VL pipeline wholesale. Gate on the **English-only table TEDS**, with latency and the inference-avoidance property as secondary criteria.
- [ ] Only if PaddleOCR-VL underperforms: consider **MinerU2.5-Pro** or **GLM-OCR**. Architecture pre-check already done 2026-07-20 (below) — **neither is single-pass**, so neither is an `odl_bench` model swap. Nothing to download until a pipeline harness is scoped.
- [ ] Domain-transfer refinement (**not** a blocker): assemble a modest corpus of the PDF types the orchestrator actually ingests and confirm the OmniDocBench-chosen parser holds up. OmniDocBench's English subset is a legitimate gating instrument on its own; this only checks transfer.

## Success criteria

1. PaddleOCR-VL-1.6 emits real HTML tables under its documented pipeline (binary gate, Phase B).
2. A table TEDS number for ODL and for PaddleOCR-VL at **n=665**, English-split, both from the same scorer and GT.
3. A defensible answer to "do we have a table-extraction gap, and does a VLM parser close it?" — replacing today's three void instruments.

## Guardrails

- **No inference without explicit per-run operator approval** (`feedback_no_concurrent_inference`). Phases B and C are inference; Phase A is not.
- **Production kernels are frozen.** Any llama.cpp work uses the experimental tree only.
- Pair every speed number with a correctness check (`feedback_pair_speed_with_correctness_check`).
- Published leaderboard scores are **priors, not results** — neither PaddleOCR-VL's 96.33 nor Unlimited-OCR's 93.92 appears on the official OmniDocBench leaderboard; both are vendor self-reports. Only our own scored runs gate the decision.

## Reporting

On completion of each phase: flip the checkbox with `✅ YYYY-MM-DD`, cite the artifact path, and mirror the outcome into `opendataloader-pipeline-integration.md` (task K35.18) and today's `progress/YYYY-MM/`. Record any newly discovered work as a fresh `- [ ]` line rather than prose.

## Key file locations

| Purpose | Path |
|---|---|
| Full benchmark | `/mnt/raid0/llm/datasets/omnidocbench/` |
| Annotations | `/mnt/raid0/llm/datasets/omnidocbench/OmniDocBench.json` |
| Model weights | `/mnt/raid0/llm/models/PaddleOCR-VL-1.6-GGUF/` |
| PaddleOCR venv | `/mnt/raid0/llm/venvs/paddleocr` |
| Producer/scorer | `epyc-inference-research/scripts/benchmark/odl_bench/` |
| Eval suite + leaderboard | `/mnt/raid0/llm/opendataloader-bench/` |
| Prior (void) artifacts | `/mnt/raid0/llm/tmp/odl-paddleocr-vl-*` |

## Research context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-864 | Unlimited OCR Works (Baidu, arxiv:2606.23050) | high | worth_investigating |
| intake-865 | DeepSeek-OCR: Contexts Optical Compression (arxiv:2510.18234) | medium | worth_investigating |

Official OmniDocBench **v1.6_full** leaderboard (shipped in `/mnt/raid0/llm/opendataloader-bench/README.md`), for priors only:

| Model | Size | Overall ↑ | TableTEDS ↑ |
|---|---|---|---|
| MinerU2.5-Pro | 1.2B | 95.75 | 93.42 |
| GLM-OCR | 0.9B | 95.22 | 92.83 |
| PaddleOCR-VL-1.5 | 0.9B | 94.93 | 91.67 |
| PaddleOCR-VL | 0.9B | 94.18 | 90.65 |
| *PaddleOCR-VL-1.6 (self-reported, arxiv:2606.03264)* | *0.9B* | *96.33* | *94.76* |
| *Unlimited-OCR (self-reported)* | *3B-A0.5B* | *93.92* | *90.16* |
| dots.ocr | 3B | 90.77 | 87.18 |
| DeepSeek-OCR 2 | 3B | 90.25 | 83.89 |

## Architecture pre-check — MinerU2.5-Pro and GLM-OCR (2026-07-20, no downloads)

Run *before* downloading, because architecture — not leaderboard rank — is what decided the 2026-07-17 failure. **Verdict: NEITHER is a single-pass whole-page parser.** Both are element-level recognition models whose published scores come from a Python pipeline (layout → per-element crops → element-specific prompts → assembler). Handing either a full page image would reproduce the exact PaddleOCR-VL mistake.

### MinerU2.5-Pro — the only candidate that keeps us on ONE kernel
- **Two-stage, but both stages are the SAME weights, prompt-selected**: `"\nLayout Detection:"` on a 1036×1036 downsample emits bboxes as text; Python then crops at native resolution and re-calls with `"\nTable Recognition:"` / `"\nFormula Recognition:"` / `"\nText Recognition:"` / `"\nImage Analysis:"`. **There is no second model to download** — this is the key differentiator vs PaddleOCR-VL and GLM-OCR.
- `mineru-vl-utils` `two_step_extract()` is the *only* parsing entrypoint; no single-pass method exists in the API. A 30-block page = **31 model calls** plus client-side crop/rotate/mask, per-block-type sampling params, and a ~20-module post-processor (tables emit **OTSL**, not HTML — needs conversion for TEDS).
- `config.json` is generic `Qwen2VLForConditionalGeneration` / `qwen2_vl`, already supported by llama.cpp `conversion/qwenvl.py` + `PROJECTOR_TYPE_QWEN2VL`. **But zero upstream awareness** (`repo:ggml-org/llama.cpp MinerU` → 0 hits), no official GGUF, and no correctness attestation on any community GGUF. Some community GGUFs ship **no mmproj — unusable**.
- License **Apache-2.0** for Pro-2604/2605; the older 2509 is **AGPL-3.0** and most GGUFs are of *that* one — check provenance carefully.
- Size: GGUF Q8_0 531 MB + mmproj Q8_0 709 MB ≈ **1.24 GB** (mmproj is larger than the decoder — 675M vision tower vs 0.5B LLM). Genuinely bilingual; olmOCR-bench (English-only) **75.2**.

### GLM-OCR — better llama.cpp citizenship, worse architecture for us
- **Requires an EXTERNAL detector**: `glmocr/layout/layout_detector.py` imports `PPDocLayoutV3ForObjectDetection` — a separate 133 MB **PaddlePaddle** model llama.cpp will never run. Same shape as PaddleOCR-VL. llama.cpp discussion #19721 states plainly it "can only recognize text"; you must run PP-DocLayoutV3 yourself.
- Its published English score is self-declared as measured through the **hosted API** (`.eval_results/olmocrbench.yaml`: `value: 75.2`, `notes: "... Using ZAI API"`) — i.e. the full pipeline, not standalone weights.
- Upside: **merged upstream support** ([PR #19677](https://github.com/ggml-org/llama.cpp/pull/19677), 2026-02-18), dedicated `clip_graph_glm4v`, and an **official first-party GGUF** (`ggml-org/GLM-OCR-GGUF`, Q8_0 950 MB + mmproj 484 MB). License **MIT**.
- Operational: **`--flash-attn off` is required**; PR notes degraded quality via Web UI (use the API with specific prompts); bbox prediction reported unreliable; vLLM/SGLang/transformers support is nightly/git-only.

### Bearing on the MTP track (separate finding, worth carrying over)
GLM-OCR ships `num_nextn_predict_layers: 1`, but llama.cpp `src/models/glm4.cpp` comments the NextN/MTP tensors as *"preserved but unused"*. Its headline decoder speedup is **not realized under llama.cpp** — we would carry the tensors and get plain autoregressive decode. This is a banked-but-unexploited MTP lever; cross-reference [`speculative-decoding-mtp-refresh.md`](speculative-decoding-mtp-refresh.md).

### Consequence
- [x] **Do not download MinerU2.5-Pro or GLM-OCR as `odl_bench` model swaps** — the harness invokes models single-pass and both would produce void results. ✅ 2026-07-29 — this guardrail is now the operative Phase-D condition; either candidate requires a separately scoped multi-call pipeline harness before any download or benchmark.
- [ ] If PaddleOCR-VL's pipeline proves the concept and we want a one-kernel alternative, scope **MinerU2.5-Pro-2605 as a separate pipeline-harness project** (multi-call orchestration + OTSL→HTML assembler). Its in-model layout stage is the reason it is the right target: `llama-server` + mmproj can serve *both* stages, with pure Python glue and no second inference runtime. `mineru-vl-utils` has an `http-client` backend for OpenAI-compatible servers that llama-server plausibly drops into, though it is not a listed/tested backend.
