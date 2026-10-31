# Document Parser Table-Extraction Benchmark — PaddleOCR-VL-1.6 pipeline vs ODL

**Scratch**: `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/pip02-current-provenance-source-20261007`, `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/pip02-selected-library-native-root-20261007`, `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/pip02-current-original-run-37602237437`, `/mnt/raid0/llm/tmp/codex3-pip-t1-r27-20261030`, `/mnt/raid0/llm/tmp/codex3-pip-head-r26-20261030`, `/mnt/raid0/llm/tmp/codex3-pip-relocatable-r25-20261030`

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

- [x] **PIP02-SELECTED-LIBRARY-SOURCE** — complete the prospectively enrolled `VB-PIP02-SELECTED-LIBRARY-CONFORMANCE` source gate: derive the launcher library directory from the selected resolved experimental executable and retain the complete original whole-module controls. No actual model/kernel/linkage, table quality or speed acceptance. ✅ 2026-10-07 — [MAIN current-source/original30/30 acceptance](../../artifacts/ni08/pip02-current-provenance-source-acceptance-20261007/README.md); exact current-provenance two-file publication5fd103e8.

Accepted PIP02 selected-binary library source correction: **VB-PIP02-SELECTED-LIBRARY-CONFORMANCE** owns the bounded source/native gate. The published launcher derives LD_LIBRARY_PATH from the selected resolved binary parent. The fresh original whole module passed30/30, preserving current raw-byte/FIFO/provenance guards and real temporary symlink argv controls, with hosted-only deterministic PDF and flock controls. No local import/test/model/kernel execution and no parser-quality or linkage/residency acceptance are claimed. Existing table/three-stage/corpus tasks remain open.

- [x] **Install ✅ 2026-07-20**: `paddlepaddle==3.2.2` + `paddleocr==3.7.0` (paddlex 3.7.2) into `/mnt/raid0/llm/venvs/paddleocr` (Python 3.12.13, uv). Venv total **1.4 GB**. **Gotcha recorded**: the resolver pulls `opencv-contrib-python`, which needs `libGL.so.1` — absent in this container, so `import paddleocr` fails with `ImportError: libGL.so.1`. Fixed by swapping to `opencv-contrib-python-headless==4.10.0.84` (uninstall the non-headless first); no system packages required. Re-run this swap after any dependency upgrade that reinstates the GUI build.
- [x] **CLI verified ✅ 2026-07-20**: `paddleocr doc_parser -i ... --vl_rec_backend llama-cpp-server --vl_rec_server_url http://host:port/v1` is available and **`llama-cpp-server` is an explicitly supported backend** (full set: `native`, `vllm-server`, `sglang-server`, `fastdeploy-server`, `mlx-vlm-server`, `llama-cpp-server`). **Do not be misled by `paddleocr --help`** — it lists only `doc2md` and `api` because pipeline subparsers are registered without a `help=` kwarg and argparse omits those from the listing. The subcommand exists and works. Equivalent Python API is `paddleocr.PaddleOCRVL(...)` exposing `layout_detection_model_name`, `vl_rec_backend`, `vl_rec_server_url`, `use_layout_detection`, `merge_layout_blocks` — prefer this for `odl_bench` integration over shelling out.
- [ ] Trigger PP-DocLayoutV3 weight resolution and record the cache path + size (a *separate* download from the GGUF, not yet performed).
- [ ] Confirm the CPU-only path works on EPYC (no GPU assumptions in the layout stage).

### Phase B — correct invocation smoke (bounded inference — **requires operator approval**)
- [x] **PIP02-PHASEB-CPU-DIAGNOSTIC — bounded three-stage CPU pipeline on the two scheduled English table pages.** ✅ 2026-10-29 — The scheduler accepted `pip02-phaseb-20261028` at 00:03:03 UTC; the real grant run ended rc0 at 00:04:58. Native output reports two completed pages, partial=false, 67.84 s and drained children; both original page artifacts contain HTML `<table>` markup. Retained result `/mnt/raid0/llm/tmp/pip02-phaseb-20261028/results/real-*/`, completion marker `/mnt/raid0/llm/tmp/pip02-phaseb-20261028/DONE`, launcher log `/mnt/raid0/llm/tmp/compute-flags/ready/pip02-phaseb-20261028.launcher.out`. This run used the private experimental-v9 CPU server, not the v7 server specified below. It establishes this bounded pipeline execution and cleanup, not table quality or a decision-grade benchmark. Phase C and the prospective `VB-PIP02-PIPELINE-WIRE` remain open. [no-belief: unsealed diagnostic, no decision warrant]
- [ ] Start experimental-v7 `llama-server` with the PaddleOCR-VL GGUF + mmproj on a high port, `--temp 0`.
- [x] Run the documented pipeline on a handful of **table-bearing** pages from the full set:
      `paddleocr doc_parser -i <page>.png --pipeline_version v1.6 --vl_rec_backend llama-cpp-server --vl_rec_server_url http://127.0.0.1:<port>/v1`
- [x] **Gate**: confirm HTML `<table>` markup is actually emitted. If still zero, stop — the problem is the harness, not the model, and no full run should be spent. ✅ 2026-10-29
  - 2026-10-29 `pip02-phaseb-20261028` (rc0 complete 00:04:58Z, CPU 24-47, 67.8 s, `/mnt/raid0/llm/tmp/pip02-phaseb-20261028/results/real-*`): **gate MET.** Two annotated English table pages (first two in OmniDocBench order; `pages.json`), three-stage PaddleOCR-VL-1.6 via the llama-cpp-server backend on the experimental `build-v9-cpu` llama-server (`-ngl 0 -np 1 -c 8192`, GGUF + mmproj). Both pages emitted real HTML: page-1 one `<table>` (7 rows, 35 cells), page-2 one `<table>` (6 rows, 12 cells), each present in `page.md` and `native.json`; `completed=2`, `partial=false`, `children_drained=true`, server exited cleanly (PID confirmed gone). The gate was predeclared as binary (FILLERS row: "HTML markup presence is a binary invocation gate, not a quality comparison"), so this is invocation evidence only: no TEDS, structure or cell-content correctness, and n=2 says nothing about speed or the 665-table set. Harness-not-model suspicion is cleared, so Phase C is no longer blocked on the gate (it still needs its own operator approval). Caveats: the server was launched without `--temp 0` (the first Phase B box stays open), the run used the Python pipeline rather than the `paddleocr doc_parser` CLI, and the row's `VALIDATION-INCIDENT.md` records an unguarded 23:12-23:17Z OCR-weight hash overlapping INF-12 r6 / LB4.9 FU04 runs (impact not established; irrelevant to a binary gate). [belief: cc]
  - [ ] Follow-up: spot-read both `page.md` tables against the OmniDocBench GT cells (descriptive only; Phase C owns scoring) before treating the markup as faithful, since page-2 equation cells contain dropped-operator OCR (e.g. `d_{0}\quad S^{\prime}`).
  - [ ] Follow-up: record the cleanup proof box from retained evidence (`server-vm.jsonl`, `server_before_cleanup`, `children_drained`) and re-run with `--temp 0` only if Phase C needs a temperature-pinned smoke.
- [ ] Capture cleanup proof (no stray `llama-server`, 0% VRAM / no KFD PIDs) per existing K35 discipline.

### Phase C — full benchmark (**requires operator approval**; long-running)
- [x] **Operator approval: Phase C APPROVED, English-only.** ✅ 2026-10-29 — The operator approved Phase C on 2026-10-29 after Phase B passed (5947aef8c). The scope is the 755 English pages (`language: english`) only, with both arms: the ODL end-to-end re-baseline and the PaddleOCR-VL-1.6 full pipeline. The Phase D decision is gated on English-only table TEDS. The full 1651-page set and the all-language split below are out of this approval, so their boxes stay open and unrun. [no-belief: not-a-result]
- [ ] **PIP02-PHASEC-ENGLISH-RUN** — stage and arm the approved English-only run: 755 pages, ODL plus PaddleOCR-VL-1.6, with the same scorer and GT for both arms. Report table TEDS with structure-only TEDS alongside, and persist via `odl_bench compare-existing`. The row needs `est_output` and a `scratch_root` + `keep` (R10), and it points at weights in `/mnt/raid0/llm/models/` (R9). Done when the English-only TEDS for both arms is filed against the Phase D gate.
  - 2026-10-29 r7 group14 first partial ended23:17:28Z rc75: four assembled original pages have validated start/result/markdown hashes; remaining original region starts/responses and unmatched exposures are retained separately. The final native attempt explicitly reports disk floor and no new factory. Later automatic resumes are separate captures. The waiting r7 group107 dispatch was canceled before start for its relocatable r8 successor. [Original partial snapshot](../../artifacts/compute/results-filing-20261029-2328.json). No table-quality/full-cohort tick. [belief: cc]
  - 2026-10-29 keeperv6 is live (PID257469, started22:37:02Z). Published five Paddle r8 and five ODL r2 packets as `any-cpu-quarter`; each launcher takes `WS58_REGIONS` for its CPU claim and `FILLER_CPUS` for taskset. Both exact native smokes passed and drained (Paddle76.60s/fiveHTTP200 responses; ODL71.89s/markdown+projection+DONE). New ODL starts capture producer row/source-manifest identity before the client request. Only unstarted/waiting predecessor packets were replaced; the running r7 group14 continues. [Source/publication evidence](../../artifacts/compute/codex3-relocatable-and-sala-z9-20261029.json). Collection and full quality gate remain open. [belief: cc]
  - 2026-10-29 ODL parallel shard7 completed25/25 native pages at22:23:52Z; page result/DONE/prediction hashes and drained status verified. Paddle r4 group11 ended22:17:24Z rc78; its last native attempt explicitly records disk-floor admission, following earlier saved-layout refusals. R7 passed a58.80s real native smoke (five HTTP200 responses,5.31GB sampled RSS, rc75 partial and drained), then four immutable replacements were published two on q2 and two on q3. Excess pending q0/q1 manifests and five waiting PIP pollers were withdrawn at the operator's queue-cap boundary, without stopping a live grant; the310 recovery stays prepared and unexposed. [Original events, page hashes and native disk trace](../../artifacts/compute/results-filing-20261029-2239.json). No quality/full-cohort tick. [belief: cc]
  - 2026-10-29 23:40 filing: relocatable ODL shards16/17/5/8/9 each completed25/25 original fresh English pages,125 newly verified total. Every original image/PDF, pre-client plan/protocol/producer source pin, prediction, result and matching DONE digest was reopened; all native children drained. This meets those native collection criteria only. Phase C full matched scoring and its coverage/source-lineage follow-up stay open. Current waiting Paddle packets g5/g11 target q2 and g8/g26 target q3 under the latest direct operator placement instruction, at most2 queued per quarter; unchanged launchers use WS58_REGIONS and FILLER_CPUS. Original waiting any-quarter JSON copies are archived; g107 had already armed and was left unchanged. [Native results and placement](../../artifacts/compute/results-filing-20261029-2340.json). [belief: cc]
  - 2026-10-29 first common scoring snapshot: ODL435/755 completed pages and131/243 tables, available-output table-weighted TEDS0.656652 and structure-only0.799800. Paddle1 completed page/zero scored tables, so the comparison is undefined. Native output hashes pass; current source-lineage reader supports97 ODL pages/35 tables and explicitly refuses unregistered generic/parallel origins. All decision cells remain null; missing/censored outputs are not scored zero. [Preserved report and native compare-existing artifacts](../../artifacts/compute/pip02-partial-teds-20261029/README.md). Phase C remains open. [belief: cc]
  - 2026-10-29 Paddle parallel group107 ended22:04:05Z rc78 after six partial batches: 25 original RPC starts have25 retained responses across shards107/109, no unmatched RPCs, but zero assembled pages. The terminal batch refused all15 saved layouts. A model-free-dispatch native layout rerun found identical pixels and54 identical regions except36 confidence scores differing in their final decimal places; strict full-layout equality caused the refusal. Queued46 affected r4 packets were withdrawn, active grants retained, and an immutable r5 repair preserves original scores while still requiring exact pixels/geometry/order/labels and exact original request bytes. Native smoke remains in progress; this is a harness finding, no table-quality verdict and no Phase C tick. [Evidence](../../artifacts/compute/results-filing-20261029-2222.json). [belief: cc]
  - 2026-10-29 `codex3-pip02-fresh-odl-s0-20261029` first attempt ended 19:17:11Z rc75: 7/25 cohort ordinals complete (0–6), one unknown (7), 17 missing (8–24), from native `odl-batch-attempts/9311e5ef-77b1-4d42-b726-d1a3078526a1.json` under `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029`. Preserve per-page original input/source/grant/result records; unknown ordinal7 is never redrawn. Later 19:20–20:20 grant is a separate resume, not a rewrite of this snapshot. No TEDS/quality verdict or full-cohort completion; the existing Phase C collection and common scoring task remains open. [belief: cc]
  - **Operator decisions, 2026-10-29:** use a newly declared full 755-page English cohort (243 annotated table regions), reusing no earlier diagnostic outputs or warrants, including for the eleven formerly unknown pages. Preserve completed and unknown exposures within this new cohort without redraw. The comparator is ODL 2.5.0 + Docling 2.91.0 docling-fast hybrid full mode on lossless image-only PDF wrappers of the same canonical images; this warrants raster hybrid behavior only. Paddle remains native layout → region recognition → assembly. Use the same GT and scorer for both arms, reporting TEDS, structure-only TEDS and explicit coverage/censoring. Declaration: `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/NEW-COHORT.md`; plan SHA-256 `63028e74950ba7250f33cbce13f4f0bdd165bba2a075242db4475c26f645ed68`. [no-belief: operator-approved prospective scope]

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
| Eval suite + leaderboard | `/mnt/raid0/llm/omnidocbench/` |
| Prior (void) artifacts | `/mnt/raid0/llm/tmp/odl-paddleocr-vl-*` |

## Research context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-864 | Unlimited OCR Works (Baidu, arxiv:2606.23050) | high | worth_investigating |
| intake-865 | DeepSeek-OCR: Contexts Optical Compression (arxiv:2510.18234) | medium | worth_investigating |

Official OmniDocBench **v1.6_full** leaderboard (shipped in `/mnt/raid0/llm/omnidocbench/README.md`), for priors only:

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
- [ ] **Do not download MinerU2.5-Pro or GLM-OCR as `odl_bench` model swaps** — the harness invokes models single-pass and both would produce void results. ✅ 2026-07-29 — this guardrail is now the operative Phase-D condition; either candidate requires a separately scoped multi-call pipeline harness before any download or benchmark.  *(Restored to `- [ ]` 2026-08-11 by `mainC` — standing constraint with no completion state; the dated evidence below is kept, the rule is live again.)*
- [ ] If PaddleOCR-VL's pipeline proves the concept and we want a one-kernel alternative, scope **MinerU2.5-Pro-2605 as a separate pipeline-harness project** (multi-call orchestration + OTSL→HTML assembler). Its in-model layout stage is the reason it is the right target: `llama-server` + mmproj can serve *both* stages, with pure Python glue and no second inference runtime. `mineru-vl-utils` has an `http-client` backend for OpenAI-compatible servers that llama-server plausibly drops into, though it is not a listed/tested backend.

2026-10-30 results filing: ODL relocatable shard20 completed25/25 original English pages; all image/PDF/source/result/prediction/DONE hashes and cleanup were reopened. This meets its collection criterion, not Phase C quality. Six further ODL packets were published23:44 with the unchanged qualified launcher. Own delegated scorer tests without bytecode suppression then created21pyc files in three shared-venv cache directories and correctly tripped R8g107 and later R7g14 integrity guards. All22613 original files and4links were verified unchanged. The affected pending packets were withdrawn, own failed groups stopped at their boundaries, and original accepted/unknown records retained. R9 uses a fresh complete runtime inventory and explicit isolated bytecode lookup; its70.259s real smoke retained five matched HTTP200 responses,5.364GBsampledRSS and verified cleanup. Six R9 successors are published: two fixed q2, two fixed q3, and two relocatable continuations; no fixed quarter has more than2queued manifests. Native prospective page-finish receipts now bind capture/source/grant/result/markdown, without historical backfill. [Evidence](../../artifacts/compute/results-filing-20261030-0000.json). [belief: cc]

2026-10-30 00:20 filing: original ODLs21 completed25/25 fresh English pages (525–549), with original image/PDF pixel identity, plan/source/grant, prediction/result/DONE and page-level cleanup reopened. Original first partials s24/s25 at00:01 ands28/s29 at00:03 each recorded25missing,0complete,0unknown; contemporaneous logs show25pre-output151GiBadmissionrefusals per shard. Later rearms are separate snapshots and may change present coverage. No unknown is redrawn and no TEDS/full-cohort gate is claimed. R9group5 is liveq2; five other R9packets were rejected before engine launch because owner publication omitted packet engine/DONE links. Links are fixed; fresh-ID R11replacement is being real-smoked after the known hourly backup interval, with R9g5 untouched. R10 controls retained2HTTP200 and2unknown requests before00:17diskreserveinterruption and are not reused. [Native evidence](../../artifacts/compute/results-filing-20261030-0020.json). [belief: cc]

R11 replacements passed real58.883s smoke (5nativeHTTP200,0unmatched,5.917GBsampledRSS,cleanupverified) andfive newIDs arepublished withfullychecked filesystemclosure; liveR9g5 isunchanged. [no-belief: dispatch and bounded diagnostic qualification]

2026-10-30 event-bound Paddle filing: originalR9g5 andR11g107 each retained10newRPCstarts/10matchedHTTP200/0unmatchedRPCs overtwofive-requestbatches, thenexplicitdisk-floorstop; originalR11g11 had0RPCs beforedisk-floorstartupstop. No attributablepage-finishreceipts wereproduced; existingpage-levelunresolvedjournals remainunknown and laterrearms areseparate. Nativeownerresult lacks anexplicitcleanupboolean, so no cleanupclaim is inferredfromrc75. SDKfixture provesbudgetTimeoutErrorcanbe wrapped asConnectionerror, but originalworkererrorcause remainsunproven and isnot called aserveroutage. [Audit](../../artifacts/compute/results-filing-20261030-0038.json). [belief: cc]

Strictlineage implementation shipped Researchmain46244248728c: registeredpre-clientODLsource andnativeR9–R11finishbinding replace mtime/overlapinference. Nineoffline tests andfreshsourcepinpreflight pass; TEDS/matching/denominator/thresholds unchanged. Legacyinsufficientlineageremainsunverified; fullcohortqualitygate staysopen. FivefurtherR11groups17/23/29/32/35 werepublishedany-cpu-quarter withsamequalifiedlauncher andcompletepacketclosure afterfreshoriginal-exposure/portchecks;75newpages notduplicatecohortwork. [no-belief: code/tests anddispatch, notcohortquality]


2026-10-30 original Paddle R11 g14 completed all15 native page results; exact input/result/markdown hashes validate. All214 retained RPC origin chains pass source, grant-interval and body-hash checks (185 from R7,29 fromR11). Seven completed pages have original R11 finisher receipts; eight remain assembler-lineage unverified and are never retrospectively backfilled. This is collection, not a full755-page TEDS or parser-selection verdict. Existing full-cohort gate remains open. [Native audit](../../artifacts/compute/results-filing-20261030-0102.json). [belief: cc]


### 2026-10-30 original seven Paddle continuation partials


Each outer job exited rc75; the last capture started before that exit reports disk floor. Attempt result JSON does not record finished_at, so pairing that last pre-end capture with the outer end is inferred from sequential launcher execution, not a separately timestamped native finish. RPC counts below use native originated_at/completed_at and original capture hashes, at each outer end; they are not the later 00:52 cumulative snapshot. Unknowns remain unknown and are never redrawn. No TEDS or parser quality claim.

| Group | Outer end UTC | Last capture start UTC | Result SHA256 | RPC starts / matched / unmatched | Later captures excluded |
|---|---|---|---|---|---|
| 17 | 2026-10-30T00:41:29Z | 2026-10-30T00:39:31Z | 4d586aa6c4332afec4e753eeb727ed5d158a3f79f3e3e6a9fb2cafc16f113e82 | 10 / 5 / 5 | 0 |
| 23 | 2026-10-30T00:41:24Z | 2026-10-30T00:40:43Z | 3d933176729a49e9b9327b3dc3532ca533a27ef3e4cb082a2101bb9dd599353c | 5 / 5 / 0 | 0 |
| 29 | 2026-10-30T00:41:41Z | 2026-10-30T00:41:15Z | 030ede2987d5d89d01f1c2658a5eb9d176fa49a426eee7cc93a4e1068eb72f7d | 10 / 10 / 0 | 0 |
| 26 | 2026-10-30T00:42:25Z | 2026-10-30T00:42:01Z | a9b135ae459d73889f0cd84faccc18abc9d914d6ace652de14f13d0d066c273a | 0 / 0 / 0 | 2 |
| 32 | 2026-10-30T00:44:24Z | 2026-10-30T00:44:00Z | d22b9ec090f362e3ed92e50107172e53c94844aea2dc489842fb1448bbb0ac08 | 0 / 0 / 0 | 0 |
| 35 | 2026-10-30T00:44:25Z | 2026-10-30T00:44:01Z | 36e4f2a4e36eb72542b473cc5821a6aedca15f4b1fea454d84b2ec47e85f605b | 0 / 0 / 0 | 0 |
| 8 | 2026-10-30T00:46:42Z | 2026-10-30T00:46:18Z | dc3b5c60abd6ebccc341d8db968935f599732410115c0e51eb322d05abed2839 | 0 / 0 / 0 | 1 |

All seven last pre-end results record `reason: disk floor`; g17/g23 also report timeout deadline/admission/output limit; g29/g26/g32/g35/g8 report timeout admission. Full native result paths, hashes, capture-bound start receipts, later capture identities and exact end_line evidence are in original-seven-events.json. Matched means the native result carries the matching start hash and completed by the event; it is not a source-grade or quality assertion.

[Committed original audit](../../artifacts/compute/results-filing-20261030-0107.json). Existing collection/full-cohort boxes remain open. [belief: cc]


### 2026-10-30 original eight Paddle collection partials


Each outer job exited rc75. The last capture started before each exit reports disk floor and TimeoutError: admission. Attempt result JSON has no finished_at: pairing that last pre-end capture with the outer end is inferred from sequential launcher execution, not a separately timestamped native finish. RPC counts use originated_at/completed_at and original capture hashes at each event end; matched means native result has matching start hash and completed by then, not a quality or full source-grade claim. Unknown remains unknown; no redraw.

| Group | Outer end UTC | Last capture start UTC | Result SHA256 | RPC starts / matched / unmatched | Later captures excluded |
|---|---|---|---|---|---|
| 38 | 2026-10-30T01:12:11Z | 2026-10-30T01:11:44Z | bcf50dbfc8d8bde3369100c26891d3993b8c5c43a0eac1b009215516389b83aa | 20 / 20 / 0 | 0 |
| 41 | 2026-10-30T01:12:00Z | 2026-10-30T01:11:36Z | b6b6720907778b35b95f9ba013286e9f78c09e9554605d81534de39b9b205316 | 0 / 0 / 0 | 0 |
| 44 | 2026-10-30T01:15:04Z | 2026-10-30T01:14:40Z | ac7f3dee9269038959a882960739bdf540b2f9605ed0d3424c8d6e5cef3b16fa | 0 / 0 / 0 | 0 |
| 47 | 2026-10-30T01:15:06Z | 2026-10-30T01:14:42Z | ccd0b132022f27db012961ff958d2ee0aa42ef805f4607cc9b60a0f4f66a0dde | 0 / 0 / 0 | 0 |
| 50 | 2026-10-30T01:15:07Z | 2026-10-30T01:14:43Z | 8379d2d768c14470a1ac49ce2322a43385310c3431d5c5ccaa514cf43fb22279 | 0 / 0 / 0 | 0 |
| 53 | 2026-10-30T01:15:09Z | 2026-10-30T01:14:45Z | 87de7abb1ef069e7b4e0d983759e5b8bb5462e75bec535655f3dba1423fd3e8d | 0 / 0 / 0 | 0 |
| 56 | 2026-10-30T01:20:16Z | 2026-10-30T01:19:52Z | 02cc7d71893cc4d0b02095a040280596c897d2ac9c4220729bcb8377f7d0d767 | 0 / 0 / 0 | 0 |
| 59 | 2026-10-30T01:20:17Z | 2026-10-30T01:19:53Z | 26a59f5f9809e4c26249c089d24c111b3858ef272da4b0e19596cb13f2a28166 | 0 / 0 / 0 | 0 |

Full exact native paths, capture SHA256, source registry, grant, result SHA256 and individual request-origin files are in original-eight-events.json. Native collection partial only; no TEDS, parser comparison, adoption, or completed scientific-cohort claim.

[Committed native audit](../../artifacts/compute/results-filing-20261030-0138.json). [belief: cc]


### 2026-10-30 three first-client recoveries and partial QC


Original scheduled `codex3-pip02-odl-recover-50-118-310-r1-20261030` completed rc0 at 2026-10-30T01:28:32Z. Its native batch DONE reports three complete first-client pages, 3 workers, 17,177,640,960-byte sampled tree RSS and no batch error. Native results and DONE, prediction hashes, canonical page image/PDF identity, prospective captured source/plan/protocol, grant interval, drained children and the original pre-client evidence were reopened and verified. Ordinals 50, 118 and 310 have respectively 0, 1 and 0 ground-truth tables. Original source branch and logs place the prior failures before the HTTP client; prior files remain retained. This is image-only PDF ODL2.5 + Docling2.91 hybrid collection, not original-PDF performance.

The pinned dependency manifest and source assert the canonical CPU Docling asset set; the original producer calls its asset-digest verification before the first-client start. This observation does not invent a separate per-model runtime receipt. Native per-page audit: `recovery-native-audit.json` SHA256 `08f78a15aa64de56404a4eef2df3f9d4ef9ab794c8563ea5da00bbfe6a5ab9dc`. Source manifest `b2ce8fc980bba8d6aaca2bfc73508e24db33e798baa799e55d782af78ef449cd`.

Fresh offline scorer pin `pins.json` SHA256 `1a71361536d7dc2a5abde8366f565888a844d24c1f5740ed05b13c59d71e4c7c` includes current producer registries plus original recovery producer, failure-log and input evidence. Common scorer completed rc0 under SMT126/127 and pair mutex; 94.94 s, sampled peak 450,068,480 bytes, no model calls. Raw snapshot (`report/coverage-and-scores.json` SHA256 `44478bba72b2221160c8617629a9a5fae6d80bfea19e04828514ddae83f35fe3`): ODL 638/755 complete pages and 224/243 GT tables scored, with source lineage verified for 178 of 638 complete pages; Paddle 17/755 pages and 1/243 tables, lineage verified for 7 of 17. Missing or unverified records remain unverified. These are observational coverage counts, not a matched complete comparison.

The one GT table on recovered ordinal 118 has descriptive native TEDS 0.4005603400 and structure-only TEDS 0.9287020110 (higher is better); ordinals 50 and 310 have no GT tables. The raw aggregate ODL table-weighted values 0.5236367252 and 0.6641641385 include pages without verified source lineage and are descriptive only. Paddle raw 1.0/1.0 is from one table, not a cohort comparison. Both full-population and gate eligibility flags are false; all decision metric values in `report/row_set.json` remain null. No parser-quality, adoption, full-755 or production-performance verdict follows.

[Committed native audit and frozen QC files](../../artifacts/compute/results-filing-20261030-0157.json). Existing full-population/adoption gate remains open. [belief: cc]


### 2026-10-30 original Paddle groups62/65/68/71


All four original outer events exited rc75. Their last captures before those ends record disk floor and TimeoutError: deadline, admission or output limit. Pairing each native result with its outer event is inferred from sequential capture starts and the outer end; result.json has no finished_at. No new quality or completed-cohort claim.

| Group | Original end UTC | Last capture start UTC | Result SHA256 | Original RPC starts/matched/unmatched | Later captures excluded |
|---|---|---|---|---|---|
| 62 | 2026-10-30T01:36:25Z | 2026-10-30T01:35:19Z | 11abe846ab210a39f0e2fe7de9301ef6ccc287e88618895eb4c8f3e7525b73cf | 0/0/0 | 12 |
| 65 | 2026-10-30T01:36:23Z | 2026-10-30T01:35:20Z | 27e4280ce2f64c39b9f557b8cc73d916aa1a03ad7b209b72f04945b190a85364 | 0/0/0 | 2 |
| 68 | 2026-10-30T01:36:25Z | 2026-10-30T01:35:22Z | ba44e2d13e04f18d442407526944abfde5c78bf8b1395cf4f6a0350cec154a10 | 0/0/0 | 12 |
| 71 | 2026-10-30T01:36:23Z | 2026-10-30T01:35:23Z | 74a384cb815ca891b9eac40f4e90fd1a068f77c57a24b2f25ce897d410262d16 | 0/0/0 | 12 |

RPC counts use native originated_at/completed_at and capture hash at the original end, not later cumulative state. Later captures are retained separately. Full original paths, grant/source identities and hashes are in original-four-events.json. Unknowns are never redrawn.

[Committed original audit](../../artifacts/compute/results-filing-20261030-0206.json). [belief: cc]


### 2026-10-30 R4 original collection outcomes


The original `codex3-pip02-odl-relocatable-r4-s24-20261030` and `...-s25-20261030` scheduled runs completed rc0 at 02:29:48Z and 02:29:50Z on 2026-10-30, respectively. Each native batch DONE has 25/25 completed pages; their complete DONE SHA256 values are `715cf83af802c4ee6274f3579d18b2b3f760d8eee187483557d51ce5d1edce1b` and `cc35eac49a886459d459b28c757e10df3bb58a277eaf7e7ba469008613f7afee`. The 50 original page records were individually checked against canonical image hashes, frozen plan, PDF identity, result and DONE/prediction links, captured grant intervals and the registered R4 producer/source manifest `af6262aaf380b3a69031fc5b7f5b11ec0f8b697f314c410c159568bccf4cc62a`. They cover respectively 5 and 0 GT tables. Sampled peak tree RSS was 62,442,586,112 and 94,929,620,992 bytes. This is native collection on image-only wrappers, not a TEDS, parser-selection or original-PDF performance verdict.

The original `...-s28-20261030` ended rc75 at 02:27:57Z. Its original batch result `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/odl-relocatable-r4-20261030/attempts/2aa57e09ad5a4f37afe39545d9694784.json` SHA256 `2de7d4d14a24efce05f767bf664bca848f9f88d208d8971e217d5c96d257a543` recorded 12 unknown pages (ordinals 700–711), 13 missing pages (712–724), no completed page and zero GT tables across these positions at the original boundary. All 12 partial result writers report forced cutoff after owned-subtree drain; original pre-client producer/grant/plan start captures were checked. Unknown exposure remains unknown and cannot be redrawn. The later 02:29 grant is a separate continuation and is not used to reconstruct this original result.

The original s28 sampled tree-RSS peak was 103,174,090,752 bytes, 94,875,648 bytes above the 96 GiB threshold (103,079,215,104 bytes). The batch record has `error: null` and does not capture which stop predicate fired; a unique stop cause or disk-floor attribution is not established. Native audit with all page paths and digests is `/dev/shm/codex3-pip02-r4-original-audit-20261030/native-audit.json`. Audit ran model-free on SMT126/127 under the pair mutex with a sampled peak of 26,296,320 bytes and rc0. No quality or full-755 completion claim.



`codex3-pip02-odl-relocatable-r4-s29-20261030` ended rc78 at 2026-10-30T02:40:04Z, observed 02:40:41Z. The final native batch result `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/odl-relocatable-r4-20261030/attempts/4617a9016a1d45e9b5c6b7248569071d.json` SHA256 `c9d4a37bd89f1ec34c86cbcde7010d23c9ad71a9860a2cd722ade9fb3c286003` records 13 complete pages, 12 unknown and no missing pages; `error` is null. The result is partial, not completed cohort or parser quality.

The earlier grant at 02:31 produced the separate rc75 batch `/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/odl-relocatable-r4-20261030/attempts/959d4b96101b4415973af23ef6135b49.json` SHA256 `652519dbe64376bb77ec885a09519f5d703df467642bd83b90a64a107996e35b`, with ordinals 725–736 unknown and 737–749 unstarted at that boundary. Its sampled tree-RSS peak was 103,783,727,104 bytes, above the 96 GiB threshold; the native record does not identify a unique stopping predicate. All 12 unknown pages have client backend-routing and sidecar document-processing evidence; their captured partial writers report forced cutoff after owned subtree drain. No unknown page may be redrawn.

The later 02:37 grant completed ordinals 737–749, preserving the 12 earlier unknowns; its sampled tree-RSS peak was 62,807,142,400 bytes. All 25 images, PDF identity, plan, pre-client start, producer/source and grant links were checked; all 13 completed pages also passed result, prediction and DONE bindings and registered source lineage. These 13 pages contain 3 GT tables; the 12 unknown pages contain 1. There are no remaining unexposed pages to repair or schedule in this shard. The safe next action is to retain its terminal partial and unknown evidence; the full-cohort gate remains open. No quality verdict or TEDS is asserted.

Per-page native audit: `/dev/shm/codex3-pip02-s29-original-audit-20261030/native-audit.json` SHA256 `bd5132a6b0365f4a02f6ccb7a8e3fdbe2148bd5e5c0ee39fef41ad2306b7c846`. Model-free audit ran on SMT126/127 under pair mutex, rc0, sampled peak 27,877,376 bytes.

[Committed native audits](../../artifacts/compute/results-filing-20261030-0252.json). Preserve terminal unknowns; no replacement when all pages exposed. [belief: cc]


2026-10-30 original Paddle groups74/77/80:

Each original outer job exited rc75. The last pre-end capture reports disk floor; results have no finished_at, so attribution to the outer event uses sequential capture start order and the launcher end, and is an inference. Request counts use native origin/completion times and matching start hash by the original boundary; they are not later cumulative snapshots.

| Group | Original end UTC | Last capture started UTC | Result SHA256 | RPC started / matched / unmatched | Later captures excluded |
|---|---|---|---|---|---|
| 74 | 2026-10-30T03:00:13Z | 2026-10-30T02:59:21Z | d721ee391ffe3f3014acab54d6fcc22db07a8f043812836bc45978d37834ebb8 | 65 / 65 / 0 | 1 |
| 77 | 2026-10-30T03:00:21Z | 2026-10-30T02:59:53Z | e2e9368b9d33a6ae66c8e4fda69b6020e6dc8538ee16e50e95055da099ef2861 | 65 / 65 / 0 | 1 |
| 80 | 2026-10-30T03:00:15Z | 2026-10-30T02:59:47Z | 0ab2d32b262302deac8f308bc34690e339568ec2bde9cc93c370dd8651768cb9 | 45 / 45 / 0 | 1 |

g74 final native error was `TimeoutError: deadline, admission or output limit`; g77 and g80 recorded `TimeoutError: admission`. All original captures match the 74-file prospective source registry `20b60b7ac3fb6fcd4db6d49163eea7d3158a4be0c6b4a94e04a2fab850226ebb`, protocol and recorded grant interval. Each group has zero original-capture-bound page finish receipts among its 15 pages. One g80 finish belongs to a later capture and is excluded; the finish record itself has no finish timestamp. Preserve all unknowns; no full-page completeness, TEDS, quality, adoption or full-cohort claim.

Native capture/hash/time details: `original-three-events.json`; exact page-finisher classification: `original-finish-audit.json`; source/grant audit: `source-capture-audit.json`.


[belief: cc] [Durable audit references](../../artifacts/compute/20261030-0310/results.json).


2026-10-30 original Paddle g104/g89/g95 windows:

Each original outer job exited rc75. Its last pre-end capture reports disk floor and TimeoutError: admission. Result JSON has no finished_at; association with the outer event follows sequential capture start order and launcher end and remains an inference. Request counts use native timestamps and matching start hash at the original boundary; later captures are separate.

| Group | Original end UTC | Last capture start UTC | Result SHA256 | RPC started / matched / unmatched | Later captures excluded |
|---|---|---|---|---|---|
| 104 | 2026-10-30T03:11:36Z | 2026-10-30T03:11:12Z | 53cae3967f30c2494e069052e1971319d46f75bc4d1e95577e3bf8e39a05d31f | 0 / 0 / 0 | 2 |
| 89 | 2026-10-30T03:14:44Z | 2026-10-30T03:14:20Z | 2722b981fd8f0d07157aee2c2a4ed53551d8edc3415a0167a8f4218ab68d9132 | 0 / 0 / 0 | 0 |
| 95 | 2026-10-30T03:14:45Z | 2026-10-30T03:14:21Z | c553cd3bc2681e411eb1f30f57589cbd172488d4794294bb6c9d503b453ecd55 | 0 / 0 / 0 | 0 |

All original captures match the 74-file R11 source registry `20b60b7ac3fb6fcd4db6d49163eea7d3158a4be0c6b4a94e04a2fab850226ebb`, protocol and captured grant intervals. No original-capture-bound page finish receipts exist among the 15 pages of each group. Preserve unknowns, no redraw; no page-completeness, TEDS, quality, adoption or full-cohort claim.

Native details in original-three-events.json, original-finish-audit.json and source-capture-audit.json.


[belief: cc]

[Original native audit references](../../artifacts/compute/results-filing-20261030-0320.json).


### Original Paddle R11 partial events — 2026-10-30

Each original attempt ended rc75 after `TimeoutError: admission`; its native owner result records `disk floor`, `partial=true`, and `factory=null`. Exact event-block source and grant captures were checked against original end time. In each attempt the worker and server logs were absent, and no region start, response or source-bound page finish was attributed to that capture. These are original-event counts, not a claim about later rearmed attempts; preserve any previously exposed or unknown requests without redraw. [belief: cc]

- `codex3-pip02-paddle-relocatable-r11-g110-20261029`: capture 2026-10-30T03:16:32Z, rc=75 time=2026-10-30T03:16:56Z reason=job-rc-75:exited; attempt result SHA256 `523a35d52ff64d1c18ee6c674755dc15620fa362b5b32dfc05b2e5b6d199e208`, capture SHA256 `9621eb66d24f4b55fa67248948bf648fcc3d36c3e25e6e743448c53ec14ec327`; source pins verified (74). Original-event counts: 0 starts, 0 responses, 0 finish receipts.
- `codex3-pip02-paddle-relocatable-r11-g113-20261029`: capture 2026-10-30T03:16:33Z, rc=75 time=2026-10-30T03:16:57Z reason=job-rc-75:exited; attempt result SHA256 `199367e2d9f3cfb02b715a4573a31f706f4e2b8858f928fc175eb5f215d7e04b`, capture SHA256 `e0392410d24aafc9eb1ad8b20d7caf969ecb87cbce708083116236fef94b2099`; source pins verified (74). Original-event counts: 0 starts, 0 responses, 0 finish receipts.
- `codex3-pip02-paddle-relocatable-r11-g119-20261029`: capture 2026-10-30T03:20:29Z, rc=75 time=2026-10-30T03:20:53Z reason=job-rc-75:exited; attempt result SHA256 `1cf991c00793f5b1ea19a15f534425de1626090af1f0349efef65f14bcf32dc7`, capture SHA256 `218b14745f4e208d50c4754089571fb39d1b5180f05a99adcad93a88848c8ab5`; source pins verified (74). Original-event counts: 0 starts, 0 responses, 0 finish receipts.
- `codex3-pip02-paddle-relocatable-r11-g83-20261029`: capture 2026-10-30T03:20:21Z, rc=75 time=2026-10-30T03:20:45Z reason=job-rc-75:exited; attempt result SHA256 `cb3f16c78ceade53ef25d43c67718c2f615161fe92b9103f66616590c70ba1f4`, capture SHA256 `4fc3e86d8da150651812b2c12481c13427d25f70d626df1f7cb523072c1ebd9c`; source pins verified (74). Original-event counts: 0 starts, 0 responses, 0 finish receipts.

No quality, TEDS or adoption verdict. Full native paths, captured grants, exact boundary and file hashes: `[durable audit references](../../artifacts/compute/results-filing-20261030-0343.json)`; model-free sampled peak 18,220 KiB, cleanup verified.


### Original Paddle R11 partial events — 2026-10-30

Both original attempts ended rc75 after `TimeoutError: admission`; their native owner results record `disk floor`, `partial=true`, and `factory=null`. Source and captured grant bindings were verified against each exact original event block and end time. Neither original attempt has worker or server logs; no region start, response, or source-bound page finish was attributed to its capture. These counts concern the original attempts only; later rearmed attempts remain separate. Preserve any previously exposed or unknown requests without redraw. [belief: cc]

- `codex3-pip02-paddle-relocatable-r11-g92-20261029`: capture 03:20:26Z; ended 03:20:50Z rc75; result SHA256 `4f91a3f47cbec9de1da3ff2c42dc71427428e5e0384e88cf04bf71a24da000f6`; capture SHA256 `5a5e3007d97408f6b52afbedea9a3299791dd837593e1e16a44f724a478ad2f6`; 74 source pins verified. Original capture: 0 starts, 0 responses, 0 finish receipts.
- `codex3-pip02-paddle-relocatable-r11-g98-20261029`: capture 03:20:28Z; ended 03:20:52Z rc75; result SHA256 `82a6fcbb7bf67752c6ef6e8607b03faeb15a09d94d8ddf47bff45c0664222e9e`; capture SHA256 `4aab48bffdd1fac6839f972f36aab1b4c17e806fb01ec0afc13d7e0475d34c74`; 74 source pins verified. Original capture: 0 starts, 0 responses, 0 finish receipts.

No TEDS, quality, adoption or full-cohort verdict. Exact native paths, grants and hashes: `[durable audit references](../../artifacts/compute/results-filing-20261030-0343.json)`. Model-free sampled peak 45,756,416 bytes; descendants drained.


### Original Paddle R11 events — 2026-10-30 04:03 UTC

- `codex3-pip02-paddle-relocatable-r11-g125-20261029`: original event ended 04:03:27 rc75; seven attempt captures within that event, with 30 capture-bound region starts and 30 matching HTTP 200 responses before the end, zero unmatched starts at that boundary, and no timestamp-proven page finish receipt. Final native partial records disk floor. [belief: cc]
- `codex3-pip02-paddle-relocatable-r11-g86-20261029`: original event ended 04:03:26 rc75; seven attempt captures within that event, with 30 capture-bound region starts and 30 matching HTTP 200 responses before the end, zero unmatched starts at that boundary, and no timestamp-proven page finish receipt. Final native partial records disk floor. [belief: cc]

Each original event was isolated by its exact start/end log block and attempt capture hashes; request/response body and lineage hashes and source pins were checked, and any later rearm was excluded. These are region-request counts, not complete-page, whole-cohort, TEDS or adoption results. Preserve all original requests and any unknowns without redraw. Full native paths and hashes: [durable original audit references](../../artifacts/compute/results-filing-20261030-0415.json); sampled guard peak 36,240 KiB, cleanup verified.

Prospective R13 source projection is published in research commit569b3b6336f0: exact source registry, nine permitted producer IDs and their27 exact shard bindings, all existing native request/grant/finish checks retained. Fifteen actual tests pass, including rejection of old R4 origins missing their original warrant fields. No scoring formula, population, denominator or grade changed; no missing historical warrant was backfilled. [belief: cc]


### 2026-10-30 overdue original-event filing (HIL, Paddle R14, FA4 and DCA)

Correction to the earlier R14 admission inference: R14 did receive actual CPU grants; a manifest output estimate alone does not establish admission refusal. Original events for pool0, pool2, pool1 and pool3 each contain native `TimeoutError: admission`, `reason: disk floor`, `factory: null` partial records and zero capture-bound region starts or finishes. Pool1 and pool3 each have two separately recorded original events. Later attempts, including native compute, are separate. No per-grant credit sample or cohort-quality conclusion is established. Original filing deadlines had elapsed before this audit. [Native event audit](../../artifacts/compute/results-filing-20261030-0520.json). [belief: cc]


2026-10-30 05:26Z operator quarter rebalance: withdrew seven captured own ungranted PIP pollers and verified all dead, preserving native outputs and source. Actual remaining waiting registrations are q0=0, q1=0, q2=2 and q3=2. Retained pool0/pool2 on q2 and pool1/head on q3; own armed manifests and staged row artifacts now name those exact regions with unchanged verified launcher hashes. No scheduler queue, grant, or canonical FILLERS edits. A separately declared pool3 successor is being prepared to replace the head registration within the same two-item q3 cap; it is not yet smoke-qualified or published. [Placement receipts](../../artifacts/compute/pip02-quarter-rebalance-20261030-0523.json). [belief: cc]


2026-10-30 05:33Z: research source projection `55e24b6fd2dc` pushed and verified for exactly four R15 producer IDs, all 49 declared groups and their 146 shards, including the two-shard tail. Parent supervised 18 tests passed, including incorrect pool/group/source/grant refusal and legacy missing-warrant refusal; sampled peak260012KiB and cleanup verified. Scoring, fixed population/denominators and grade rules are unchanged. [belief: cc]

Fresh five-second quarter verification found q0/q1 waiting0/0 and q2/q3 waiting2/2 with exact actual48–71/72–95 arguments and zero active PIP grants. Mean CPU utilization including SMT siblings was2.13%,4.69%,3.80%,3.47%; queue placement does not establish useful inference progress. None of60 previously retired IDs reappeared. Full snapshot is bound by the placement artifact's durable reference. [belief: cc]


### 2026-10-30 06:05 original EVL, Paddle and YaRN resource events

- Paddle R15 pool1 original grant ended 05:53:51Z rc75. Its `[8,9,10]` native attempt recorded `TimeoutError: admission`, `reason=disk floor`, `factory=null`; no region starts were bound to that attempt's capture hash. Prior group evidence and later rearm events are distinct. No whole-cohort quality verdict. [Native event audit](../../artifacts/compute/results-filing-20261030-0605.json).
  - [belief: cc] Original native records and unchanged criteria are linked above.


PIP split-storage R22 published all four disjoint logical pools: pool0/pool2 targetq2 and pool1/pool3 targetq3, maximum two queued offers per quarter. One identical-outer61.026s native control produced five matched HTTP responses with durable result markers,5.508GB sampled RSS, rc75/partial and verified descendant drain. Sampled native Micron growth442368bytes and RAID metadata12288bytes; each declared per-grant budget remains1GiB Micron and0.125GiB RAID above independent150GiB floors. The exact original read-only measurement recipe uses the source-pinned v9 binary10125, explicitly distinguished from production-store v10 version10303. Original checkpoint bytes and unknowns remain retained; missing lock metadata was initialized with same-inode flock and directory fsync. Individual publications followed natural old-producer boundaries, with no aggregate-capacity publication gate. The49 original group starts cover730 pages; the25-page head is separate, and this is not a whole-cohort completion or TEDS verdict. [Publication/native proof references](../../artifacts/compute/results-filing-20261030-0605.json). [belief: cc]


Runtime cleanup: the full2a172b09 phase-C linked checkout was removed through the gate. Its required source files remain byte-identical and at the same inodes in a small compatibility directory; R22/R24 full source checks passed after removal, without modifying their manifests or historical launchers. The exact commit capsule and490-launcher restore index are retained under `/mnt/micron/codex3-pip02-phasec-capsule-20261030`. Reusable analysis edits now use `/mnt/micron/codex3-lanes/research`; the old temporary research tree was removed after its wrapper was migrated and both CLI help checks passed. This is operational custody, not a new cohort-quality or lineage verdict. [no-belief: checkout cleanup]

**2026-10-30 Codex3 R25 relocatable cutover:** pools 0 and 3 were published after a final same-entry control: five matched HTTP200 responses, no unmatched RPCs, rc75 partial and verified drain. They request `any-cpu-quarter`; fixed-quarter R24 predecessors were archived before native exposure. R25 pools 1 and 2 remain prepared behind live R22 predecessors; their zero-token watcher refuses cutover while the owner keeper can rearm those predecessors. The R26 head successor retains all 25 pages through group starts 0 and 3, verifies 49 historical response bindings and preserves unknown starts; its final control has five matched durable responses and verified drain. See [publication audit](../../artifacts/compute/codex3-publications-20261030-1415.json). These are preparation results; quality grading still requires explicit source registration and complete native coverage. The legacy PIP binary remains version10125, distinct from production10303. [no-belief: bounded admission and source-custody checkpoint]

**2026-10-30 final T1 successors:** PIP R27 pools 0, 3, and head have final relocatable packets. Pool1/pool2 registrations remain unchanged behind live R22 predecessors; successor rows stay held by the owner watcher until those predecessors are retired. No pool1/pool2 cutover or quality result is claimed. The NEMO C3 and KPF item-4 r2 entries are model-free build packets only; each still requires the full linked build and its declared help/linkage/knob checks. At the 15:54:53Z keeper snapshot, candidate rows were READY-WAIT for lack of a free CPU quarter. [T1 successor ledger](../../artifacts/compute/codex3-t1-successors-20261030.json). [no-belief: packet preparation and admission only]

### PIP-02 running English shard TEDS — 2026-10-30
  - *(2026-10-31, Paddle R27 head and pool0.)* **FAILED-RUN `codex3-pip02-paddle-relocatable-r27-head-20261030`** and **FAILED-RUN `codex3-pip02-paddle-relocatable-r27-pool0-20261030`**, class=harness, both outer rc1 before page processing: the head pool identity guard hardcoded R26 and pool0 hardcoded R25 while the actual grants were R27. These are harness failures; neither is a page or quality verdict. Preserve prior outputs, exposed unknowns, original group lists and checkpoints; successor must use a fresh identity and validate real launcher normal/STOP/drain. No full 755-page verdict. [belief: cc]

Same Phase C native scorer and ground truth, locked fresh English cohort `pip02-english-fresh-20261029` (755 pages/243 GT tables). Both metrics are table-weighted means; higher is better. These are descriptive partial-cohort scores; full-cohort and paired parser-selection gates remain open. Complete pages with no GT table do not enter the table mean. Missing/error pages remain visible in coverage and are not silently counted as successful pages.

| Arm / shard | Complete pages | GT tables scored / planned | Table TEDS ↑ | Structure-only TEDS ↑ |
|---|---:|---:|---:|---:|
| ODL+Docling hybrid fresh s05 | 25/25 | 8/8 | 0.554871 | 0.640090 |
| ODL+Docling hybrid fresh s08 | 25/25 | 10/10 | 0.733307 | 0.815572 |
| ODL+Docling hybrid fresh s09 | 25/25 | 7/7 | 0.842202 | 0.916755 |
| ODL+Docling hybrid fresh s16 | 25/25 | 7/7 | 0.243788 | 0.562940 |
| ODL+Docling hybrid fresh s17 | 25/25 | 1/1 | 0.951119 | 1.000000 |
| ODL+Docling hybrid fresh s20 | 25/25 | 47/47 | 0.137642 | 0.290202 |
| ODL+Docling hybrid fresh s21 | 25/25 | 8/8 | 0.078004 | 0.116914 |
| ODL+Docling hybrid fresh s24 | 25/25 | 5/5 | 0.518804 | 0.538788 |
| ODL+Docling hybrid fresh s25 | 25/25 | 0/0 | — | — |
| ODL+Docling hybrid fresh s28 | 4/25 | 0/0 | — | — |
| ODL+Docling hybrid fresh s29 | 13/25 | 3/4 | 0.312108 | 0.333333 |

Native complete-page records passed prediction/output, original source/protocol/dependency/input and frozen plan bindings. PlanSHA `63028e74950ba7250f33cbce13f4f0bdd165bba2a075242db4475c26f645ed68`; GTSHA `a45cd84b04ad8b793e775089640e6b681209abea33ead54c1828ddca35fae496`; scorerSHA `27f0b630b6812aecad35d1c65329841a5011e421326e81f9f14c8c66a6fdbe5e`; pinmanifest `262462c58402db48aa88063cdb1817915dcdef0c1933e72869682dd905c34cf0`. English inputs, native matched GT/prediction indices and every per-table score are committed in [s20](../../artifacts/compute/pip02-shard-teds-20261030/odl-s20.json) and [s21](../../artifacts/compute/pip02-shard-teds-20261030/odl-s21.json). An independent repeat under the correct original26-27 mutex on admitted SMT122/123 reproduced both files byte-for-byte;17.466s, sampled503,226,368 bytes and descendants drained. [belief: cc]

- [x] **PIP-02 incremental score filing: ODL s20/s21.** Both verified25-page shards scored with the unchanged Phase C English scorer/GT and filed above; this closes only their incremental score reporting. ✅ 2026-10-30 [belief: cc]
- [ ] Continue this table for every verified completed ODL/Paddle shard as it finishes, with epoch/source and coverage preserved. Do not wait for the755-page full-cohort gate.

Incremental scoring also verified completed s05/s08/s09 (originalR2 source) and s24/s25 (originalR4 source `af6262aaf380b3a69031fc5b7f5b11ec0f8b697f314c410c159568bccf4cc62a`), with the same scorer/GT. Their per-table records are committed in the same artifact directory; s25 has no GT table and therefore no table mean. The first seven filed rows cover175complete pages/85GTtables, as a descriptive partial cohort only. [belief: cc]


#### Paddle English scores by original finish epoch

The current full151-shard snapshot has251 verified complete pages and78 scored GT tables. Its other504 pages remain476 unknown,20 errors and8 with request origins but no verified finishing-capture binding. All755 original page IDs and243 planned GT tables remain represented. Per-epoch rows below are components of fixed shards: their repeated planned denominators must not be summed. A case is deduplicated only when original prediction/finish hashes and native table values match; conflicting complete snapshots refuse, and later partials cannot erase an earlier complete observation.

| Paddle shard | Finish epoch | Verified pages / planned | GT tables scored / planned | TEDS | Structure-only TEDS | Case artifact |
|---|---|---:|---:|---:|---:|---|
| s008 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s008.json) |
| s009 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s009.json) |
| s010 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s010.json) |
| s011 | r22 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-watch-s011.json) |
| s012 | r22 | 4/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-watch-s012.json) |
| s013 | r22 | 1/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-watch-s013.json) |
| s014 | r11 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-watch-s014.json) |
| s015 | r11 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-watch-s015.json) |
| s016 | r11 | 3/5 | 0/1 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-watch-s016.json) |
| s020 | r22 | 3/5 | 3/5 | 0.959600 | 0.979550 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s020.json) |
| s021 | r22 | 5/5 | 5/5 | 0.966403 | 0.995597 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s021.json) |
| s022 | r22 | 2/5 | 3/6 | 0.946595 | 0.973352 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s022.json) |
| s023 | r22 | 5/5 | 5/5 | 0.969951 | 0.986704 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s023.json) |
| s024 | r22 | 5/5 | 6/6 | 0.985741 | 0.999556 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s024.json) |
| s025 | r22 | 4/5 | 5/5 | 0.900181 | 0.952941 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s025.json) |
| s026 | r14 | 3/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s026.json) |
| s026 | r22 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s026.json) |
| s027 | r14 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s027.json) |
| s027 | r22 | 3/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s027.json) |
| s028 | r14 | 2/5 | 0/3 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s028.json) |
| s028 | r22 | 3/5 | 3/3 | 0.990874 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s028.json) |
| s032 | r22 | 5/5 | 3/3 | 0.417395 | 0.424469 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s032.json) |
| s033 | r22 | 3/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s033.json) |
| s034 | r22 | 3/5 | 0/5 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s034.json) |
| s035 | r22 | 5/5 | 4/4 | 0.909152 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-watch-s035.json) |
| s036 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s036.json) |
| s037 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s037.json) |
| s038 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s038.json) |
| s039 | r22 | 1/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s039.json) |
| s040 | r22 | 4/5 | 2/2 | 0.900544 | 0.925306 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s040.json) |
| s047 | r22 | 5/5 | 1/1 | 0.997619 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s047.json) |
| s048 | r22 | 3/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s048.json) |
| s049 | r22 | 2/5 | 1/3 | 0.997727 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s049.json) |
| s050 | r22 | 3/5 | 6/7 | 0.950152 | 0.985481 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s050.json) |
| s051 | r22 | 5/5 | 7/7 | 0.948362 | 0.957008 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s051.json) |
| s052 | r22 | 3/5 | 4/6 | 0.997927 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s052.json) |
| s056 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s056.json) |
| s057 | r22 | 5/5 | 1/1 | 1.000000 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s057.json) |
| s058 | r22 | 5/5 | 3/3 | 0.938161 | 0.950000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s058.json) |
| s059 | r22 | 5/5 | 4/4 | 0.964214 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s059.json) |
| s060 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s060.json) |
| s061 | r22 | 5/5 | 1/1 | 1.000000 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s061.json) |
| s064 | r11 | 3/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s064.json) |
| s077 | r11 | 1/5 | 2/3 | 0.969781 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s077.json) |
| s080 | r22 | 4/5 | 2/2 | 0.667766 | 0.740260 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s080.json) |
| s081 | r11 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s081.json) |
| s081 | r22 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s081.json) |
| s082 | r11 | 1/5 | 1/3 | 0.851760 | 0.933333 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s082.json) |
| s082 | r22 | 3/5 | 1/3 | 0.909740 | 0.956522 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s082.json) |
| s083 | r22 | 5/5 | 2/2 | 0.931377 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s083.json) |
| s084 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s084.json) |
| s085 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s085.json) |
| s086 | r11 | 4/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s086.json) |
| s087 | r11 | 4/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s087.json) |
| s088 | r11 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s088.json) |
| s092 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s092.json) |
| s093 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s093.json) |
| s094 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s094.json) |
| s095 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s095.json) |
| s096 | r22 | 5/5 | 1/1 | 0.952341 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s096.json) |
| s097 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s097.json) |
| s098 | r11 | 3/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s098.json) |
| s099 | r11 | 2/5 | 2/2 | 0.935813 | 1.000000 | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s099.json) |
| s100 | r11 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s100.json) |
| s105 | r22 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s105.json) |
| s108 | r22 | 5/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s108.json) |
| s109 | r22 | 1/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-watch-s109.json) |
| s119 | r11 | 1/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s119.json) |
| s119 | r22 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s119.json) |
| s120 | r11 | 1/5 | 0/1 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s120.json) |
| s120 | r22 | 1/5 | 0/1 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s120.json) |
| s121 | r11 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s121.json) |
| s121 | r22 | 2/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s121.json) |
| s126 | r11 | 1/5 | 0/0 | — | — | [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-split-v3-s126.json) |

Descriptive English fresh cohort snapshots, table weighted, higher better; denominators repeat where a shard spans epochs and must not be summed. Native request origins may span earlier epochs and are preserved per case. Each case is counted once; matching completed snapshots deduplicate by prediction, finisher and table values, while conflicting completions are refused. Current non-complete cases and every historical non-complete event are retained in [case data](../../artifacts/compute/pip02-shard-teds-20261030/paddle-snapshot-paddle-running-refusals.json); no paired or full-population claim.


The native Phase C TEDS scorer, GT, table matcher and English cohort remain unchanged. Research main `243067bed40d0ed5e08827ed4c7c760a0250b196` adds only strict original capture/finish joins across RAID/R14/R22/R25/R26/R27 layers;18 lineage controls and actual mixed-epoch cases passed. Missing original R4 warrant and orphan/native-finish failures remain refused, not repaired by guessing. These partial descriptive observations do not establish a full755-page quality gate or paired parser winner. [Full151-shard inventory](../../artifacts/compute/pip02-shard-teds-20261030/inventory-1840.json). [belief: cc]

Both source-bound, bounded scoring watchers are active: ODL PID2373051 and Paddle PID2341453 at this checkpoint. They score newly finished shards through the same native scorer/GT, with the standing R6 mutex, admission, memory and wall limits. The original case snapshots and all earlier unknown/error events remain in the declared KEEP root. Future outputs still need incremental filing here; the full cohort is not a filing prerequisite.


### 2026-10-30 incremental scorer and watcher checkpoint

The incremental writer and strict projection are landed in root 55bbca49e9e8b87e8d020f52b3e655336da5ee7c; research source 6d2ab2803c6cc742a102ed18021247427d6b7be4 supplies the writer. Immutable begin/end inputs and selected native warrants are bound by hashes, including image warrant and original request/finish lineage. The real Paddle r3 receipt at /mnt/raid0/llm/tmp/pip02-vidya-draft/actual-paddle-s21-r3/s021.score-receipt.json (SHA-256 dd41924d02e279cb76eae7c56fc388bf1818199d543de2015bbe2eb5884c599d) covers five pages and five tables, table-weighted TEDS 0.9664026497276218 and structure-only 0.9955969634230504; runtime was 14.6s and peak RSS 573 MB. It is a model-scoped Paddle observation, not a full-cohort result.

Across 20 native ODL DONE batches, 9 are strict-eligible. Eleven batches (255 pages) lack original producer_source_manifest_path/id; retain these as separately audited UNVERIFIED ordinary native TEDS rows, never project or include them in strict totals. Receipts without model-scope identity remain explicitly UNPROJECTED; raw ODL TEDS remains valid. Do not invent weight identity or add a pipeline filter. Shard widths are not matched-arm comparisons: ODL r25 uses 25-page s20/s21 shards at positions 500–524 and 525–549, while Paddle uses a five-page s21 shard at positions 105–109. Same shard number does not identify the same cohort slice. The approved eligible Paddle model-scoped planning-context canary passed. Both scoring watchers have since finished; outputs added after watcher repair need a fresh canary before extending the wired/complete claim. The v2 epoch-watcher checkpoint and restart/runtime set are preserved at [epochwatch-v2](../../artifacts/compute/pip02-shard-teds-20261030/epochwatch-v2/): it records the 20 ODL completed batches, 11 separately unverified 255-page snapshots, five partial Paddle snapshots, and replacement watcher births/PIDs. At 20:35Z, ODL PID 790668 (birth 151477532) and Paddle PID 793354 (birth 151478825) were verified active. Five new Paddle epoch generations had been processed; none created a newly eligible completed shard, and unchanged inputs are not replayed. This is an as-of checkpoint, not a future liveness promise. Preserve immutable partial snapshots and the running/refusal history. The full 755-page quality gate remains open.

### Completed ODL shards with unverified producer provenance

The exact 11-row, 255-page UNVERIFIED inventory follows; all native page inputs, plan/GT/images/predictions, start/DONE custody, and native weighted means were rechecked, but the missing original source binds keep these records outside the strict-source-verified aggregate. Zero-GT-table rows have undefined means. [Inventory JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-completed-inventory-20261030.json) · [source-custody audit v2](../../artifacts/compute/pip02-shard-teds-20261030/odl-new-shards-strict-audit-20261030-v2.json)

| ODL shard | Native pages | GT tables | TEDS | Structure-only TEDS | Producer provenance | Native score artifact / SHA-256 |
|---|---:|---:|---:|---:|---|---|
| s03 | 25/25 | 7/7 | 0.544025 | 0.760523 | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s03.json) / 146684bb1e3f918289d7aa64cd54545dc553762644ffff3092bd00665653c8dc |
| s06 | 25/25 | 10/10 | 0.853327 | 0.888682 | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s06.json) / b30075d67bad6cd5384a80014d5d93ab7452f8ac5415ccb6754f10e71185f66b |
| s07 | 25/25 | 4/4 | 0.863587 | 0.965278 | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s07.json) / 1747fc697d5db7a3ac431b6fab3adde34d5d757c6dca6b09977f5a007734db57 |
| s10 | 25/25 | 36/36 | 0.603236 | 0.767011 | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s10.json) / e2ea4cf3510782cecff325d1e5c3fa6cce8ee00fbbbc0382ddbb392d197369fc |
| s13 | 25/25 | 5/5 | 0.591423 | 0.701263 | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s13.json) / 841f3dd5e4ad32433321a59c218245099f71faacc38902a0cb2f65a5a41bf787 |
| s18 | 25/25 | 0/0 | — | — | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s18.json) / b96643f7b2be90c0b0641ea4240b95b29b0316bb472ca3e56593b95a33c3b895 |
| s19 | 25/25 | 3/3 | 0.387989 | 0.666667 | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s19.json) / 9c82822b495150764eb744cdfed5d5cf97bb222819a361bf0df8e19e534ca070 |
| s23 | 25/25 | 0/0 | — | — | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s23.json) / 383e7b5253305984c313471c5237612e28707b4896ae81b3ededc8a030cd9b7b |
| s26 | 25/25 | 0/0 | — | — | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s26.json) / 74f769136b621bedf69879a30eca71456bbda0cca5e1fc6c166950218a4c1505 |
| s27 | 25/25 | 5/5 | 0.795710 | 0.964456 | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s27.json) / 713d9df128fac71ac85580b2e177d0615b658809feee19bdb43dc80333c2f129 |
| s30 | 5/5 | 0/0 | — | — | missing original producer ID and source manifest | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/odl-legacy-recheck/odl-s30.json) / ffb4a78e49901bfd8ce56c60d17fb74b3a9c858eded1a992fd08292bcadc52a2 |

### 2026-10-30 22:18 incremental Paddle filing

Four more completed English Paddle shards have been scored with the unchanged Phase C scorer, GT and matcher. Each has five verified pages and zero GT tables, so both TEDS means are undefined rather than zero or a passing score. Deduplicated verified coverage is now **271 pages and 78 GT tables**, up20 pages from251; repeated native epochs are never summed. Higher TEDS remains better where defined. The755-page and paired-parser quality gates remain open. [Running table](../../artifacts/compute/pip02-shard-teds-20261030/epochwatch-v2/paddle-running-table.md), [refusal history](../../artifacts/compute/pip02-shard-teds-20261030/epochwatch-v2/paddle-running-refusals.json), [hash-checked transfer audit](../../artifacts/compute/pip02-shard-teds-20261030/TRANSFER-AUDIT-2218.json). [belief: cc]

| Paddle shard | Verified pages | GT tables | TEDS | Structure-only TEDS | Native score artifact |
|---|---:|---:|---:|---:|---|
| s104 | 5/5 | 0/0 | — | — | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/paddle-watch/epochs/s104/e76b365d2845b1cf299fe7dbc17a0212ab5014722084ccc1d5ce21b692b0f8ee/s104.json) |
| s131 | 5/5 | 0/0 | — | — | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/paddle-watch/epochs/s131/769b96c0920aa2e2860c79006548fdb85e9c9ea6f71cdccacccf3b1de7a2625c/s131.json) |
| s132 | 5/5 | 0/0 | — | — | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/paddle-watch/epochs/s132/174cbd8d3c96ebc3d1153df28796a35b0ee8140a8688846fb25eb3b34be70e4a/s132.json) |
| s133 | 5/5 | 0/0 | — | — | [JSON](../../artifacts/compute/pip02-shard-teds-20261030/paddle-watch/epochs/s133/58ff5bb791fbb48b33fdccd4a9e52ea6c978c855a5123543df00542c64234c74/s133.json) |


### 2026-10-30 23:26 incremental Paddle filing

Five newly completed shard generations add **23 unique verified pages and 4 GT tables** to the prior 271/78: **294 pages and 82 GT tables**. s105 replaces its prior two verified pages, adding three; the other four add five each. Counts use unique positions and completed native status, never summed epoch planned denominators. Zero GT means undefined. The 755-page and paired-parser gates stay open; the 11 ODL unverified batches remain ordinary results outside strict totals. [Current running table](../../artifacts/compute/pip02-shard-teds-20261030/epochwatch-v3/paddle-running-table.md), [refusals](../../artifacts/compute/pip02-shard-teds-20261030/epochwatch-v3/paddle-running-refusals.json), [verified transfer hashes](../../artifacts/compute/codex3-speech-v2-transfer-20261030.json). [belief: cc]

| Shard | Verified pages | GT tables | TEDS | Structure TEDS | Native score |
|---|---:|---:|---:|---:|---|
| s044 | 5/5 | 1 | 1.000000 | 1.000000 | [case](../../artifacts/compute/pip02-shard-teds-20261030/paddle-watch/epochs/s044/df426e627327e1f3d1fb4b2f92416b3e5b7cecfb565eaa6dc9b3aeed65e47d13/s044.json) |
| s045 | 5/5 | 3 | 0.951240 | 1.000000 | [case](../../artifacts/compute/pip02-shard-teds-20261030/paddle-watch/epochs/s045/fe4cf9daf2cf012dfb5d55b8c992c82e85d8c053b370064379bbf1b90558ebf1/s045.json) |
| s046 | 5/5 | 0 | — | — | [case](../../artifacts/compute/pip02-shard-teds-20261030/paddle-watch/epochs/s046/d42d08f38d8573fd248239bab7a7dd28cd5ea7b8440212f683295f6edbb1988c/s046.json) |
| s105 | 5/5 | 0 | — | — | [case](../../artifacts/compute/pip02-shard-teds-20261030/paddle-watch/epochs/s105/f8c50b4963e8367751cab661018557839054d926a5df0a21808208a4828ef792/s105.json) |
| s106 | 5/5 | 0 | — | — | [case](../../artifacts/compute/pip02-shard-teds-20261030/paddle-watch/epochs/s106/d12a280efc1778d807567d40e9cc574ff28979e25b3f9c1026e61d5c51fdbf63/s106.json) |


- [x] **PIP02-INCREMENTAL-FILING-20261031-0105** — original Phase C English scorer/GT and existing strict receipt reader verified newly completed Paddle r22 shards s116, s117 and s118 (5/5 pages each, zero GT tables each). Current selected generations cover **309 unique completed pages / 82 GT tables**, up from 294/82; no repeated epoch denominator is summed. Zero-table shards have no TEDS or structure-only mean; the existing 82-table means are unchanged. [Running table](../../artifacts/compute/codex3-ready-checkpoint-20261031-0105/pip/paddle-running-table.md) and [native-receipt delta](../../artifacts/compute/codex3-ready-checkpoint-20261031-0105/pip/DELTA.json) preserve prior refusal/generation history. Full 755-page and paired-parser gates remain open. ✅ 2026-10-31 [belief: cc]
