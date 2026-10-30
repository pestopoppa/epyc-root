# Document Parser Table-Extraction Benchmark — PaddleOCR-VL-1.6 pipeline vs ODL

**Scratch**: `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/pip02-current-provenance-source-20261007`, `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/pip02-selected-library-native-root-20261007`, `/mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/pip02-current-original-run-37602237437`

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
