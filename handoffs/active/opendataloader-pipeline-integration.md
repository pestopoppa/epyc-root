# OpenDataLoader PDF — Pipeline Integration

**Status**: Active. The default ODL extractor and structured-context substrate are landed; parser-quality, routing, intrinsic-metric, LiteParse, and model-backed comparison gates remain open.
**Created**: 2026-03-17 (via research-intake deep dive)
**Priority**: P2 — medium effort, high document-quality payoff
**Categories**: document_processing, multimodal

## Executor Start Here

1. Implement ODL-011's non-coreference Ekimetrics and contradictory HOPE arms against one digest-pinned fixture and downstream RAG endpoint.
2. Acquire or construct the immutable GT-page-to-source-PDF bridge needed for the full OmniDocBench rebaseline.
3. ~~Run the ODL-013 observation~~ ✅ **DONE 2026-08-13** (inference-granted window and LiteParse-aware scoring). The result does not authorize adoption or a routing-default change; make the evidence durable and protocol-admissible before using it for either.
4. Do not promote a parser or flip a routing default from the existing July artifacts: they are scaffolding/observations, not representative decision evidence.

The domain router is [PIP-05](pipeline-integration-index.md). The full completed implementation and evidence ledger is in [the completed-through-2026-08-13 sibling](../completed/opendataloader-pipeline-integration-completed-through-2026-08-13.md).

## Objective

Use OpenDataLoader PDF as the structured document path, preserve a cheap born-digital fast path, and route scanned or structurally difficult pages to model-backed parsing. Any parser choice must report reading order, table fidelity, structure, speed, deploy footprint, and a workload-relevant downstream endpoint under the project measurement constitution.

## Current Decision Gates

| Gate | Current state | What closes it |
|---|---|---|
| ODL-011 chunk metrics | **SC/BI/ICC/DCC registered + first real run 2026-08-13** | Contradictory HOPE scores and common RAG correctness on the digest-pinned Phase-2 fixture (HOPE arm row below). |
| ODL-013 LiteParse comparison | **Observation complete 2026-08-13; decision gate open** | Preserve or rerun it as durable, protocol-admissible evidence with a precommitted decision rule. LiteParse leads the aggregate point estimates, but the current scratch artifact cannot authorize adoption or routing. |
| Full ODL baseline | Input blocked | Immutable source-PDF manifest or explicit page/document scoring bridge for the 1,651-page / 665-table corpus. |
| PaddleOCR-VL | Prior arm void | Official pipeline or official cropped-element prompts; never reuse the off-label full-page numbers. |
| Unlimited-OCR | **18-page observation complete (18/18 pages, 0 errors; median 5857 ms/page, ~392 t/s decode; text_block edit_dist 0.3624, table TEDS 0.0117, reading_order 0.2165 — run detail in `progress/2026-08/2026-08-13-mainD.md`); evidence correction open** | Correct the causal claim and mutex receipt, then run the canonical-profile A/B after the operator lifts the all-inference-stop order. |
| Routing policy | Default unchanged | Matched quality + latency evidence for local ODL, hybrid ODL, LiteParse/pdftotext, and model-backed arms. |

## Outstanding Tasks

### Routing and representative parser evidence

- [ ] Parser-quality comparison: evaluate LightOnOCR-2-1B only as a structural/table/reading-order parser candidate against docling-fast; speed is secondary and not a standalone reopen reason.
- [ ] Measure LightOnOCR latency only inside the parser-quality comparison above, after structural/table/reading-order scoring says the swap is useful.
- [ ] Implement three-way routing: ODL local (simple) → ODL hybrid (tables) → LightOnOCR (scanned).
- [ ] Run comparison on 200 PDFs: our pipeline vs ODL local vs ODL hybrid vs docling vs marker.
- [ ] Publish results in the dated progress log with immutable artifacts and metric directions.
- [ ] **Make ODL-013 decision-capable before any adoption or routing-default change**: preserve the corpus/evaluator/engine hashes and raw outputs in durable in-repo evidence; use an existing or operator-ratified document-parser protocol with the full claim tuple and a precommitted decision rule. Keep the current default unchanged until that gate closes.
- [x] **Harden the ODL three-way harness and timing record** ✅ 2026-08-25 (mainA PIP-05): fail closed on non-zero pdftotext return codes, missing ODL candidates, and empty liteparse/phase predictions (failed docs leave no prediction file, `failed_stems` recorded, exit 2); ODL engine pinned (`opendataloader-pdf==2.5.0`, `liteparse==2.12.0`) via `importlib.metadata` with fail-closed exit 2 on mismatch/unresolvable, recorded in summary.json; raw per-document latencies persisted (`per_doc_latency_ms`) so median/p90 are independently reproducible, report gains a p90 column; score phase exits 3 on missing/empty predictions or missing evaluation.json. Research `run_three_way_bench.py` + 13 new tests; suite 69 passed/1 skipped.
- [x] **Resolve the dataset name collision explicitly** ✅ 2026-08-25 (mainA PIP-05): the OmniDocBench clone was renamed `/mnt/raid0/llm/opendataloader-bench` → `/mnt/raid0/llm/omnidocbench` (no live processes; venv activate scripts + console shebangs migrated); every in-repo path reference repointed (research odl_bench + document_extraction_adapter + validate_pool, orchestrator corpus_v1/common.py, root handoffs/wiki/op-bundle/backlog-queue/amend_e8 script); bare-name references now fail loudly. `/mnt/raid0/llm/opendataloader-bench-upstream` remains the 200-PDF OpenDataLoader benchmark. Historical progress records left as dated.
- [ ] Run baseline: our current pipeline (pdftotext + LightOnOCR) on the 200 PDFs.
- [ ] Cite W-RAC as Phase-2 hybrid-routing prior art if measured cost becomes a bottleneck.

### ODL-011 — chunk-quality instruments

- [ ] During Phase 3 benchmark integration, add intrinsic chunk-quality scores beside the committed `odl_bench` structural text edit distance, table TEDS, reading-order edit distance, and speed rows; explicitly bridge/co-report sibling NID/MHS if those names remain in the parent contract.
- [x] **ODL-011 integrate and test the non-coref Ekimetrics arm ✅ 2026-08-13**: registered SC/BI/ICC/DCC in `odl_bench` (`intrinsic.py`, research `f24b8aa9` + `cd329746`); upstream MIT provenance pinned (intake-580, FMRE/RC excluded per license + contract); 30 intrinsic tests cover metric direction + degenerate inputs; unavailable-embedder evidence preserved (`value=None` + reason). First real run complete: sentence-transformers 5.7.0 installed under inference grant (msg-84), all-MiniLM-L6-v2 over the ODL-013 dirs (200 docs/engine) — pdftotext ICC 0.651/DCC 0.672, opendataloader ICC 0.643/DCC 0.654, liteparse ICC 0.552/DCC 0.654. Evidence: `/mnt/raid0/llm/tmp/odl013-bench-20260813T1336Z/intrinsic/intrinsic-*-embed.json`. HOPE arm + common RAG endpoint remain open (row below).
- [ ] **ODL-011 add the contradictory HOPE arm and common endpoint**: score both intrinsic families on the digest-pinned Phase-2 fixture and report the same downstream RAG answer-correctness endpoint before either family informs routing.

### ODL-013 — LiteParse fast path

- [x] Bench LiteParse-local vs OpenDataLoader-local vs pdftotext on a representative born-digital corpus: reading order, table fidelity, speed, and JVM-free deploy footprint. Use LiteParse-aware scoring and decide `adopt_component` vs ODL-only. ✅ **EXECUTION COMPLETE 2026-08-13; OBSERVATION ONLY** — the same 200 PDFs and prediction stems were scored with the upstream NID/TEDS/MHS evaluator, and all 600 stored outputs reproduce exactly. LiteParse leads the aggregate point estimates (overall 0.8804 vs ODL 0.8419 and pdftotext 0.5705), but NID and MHS paired exploratory intervals cross zero and no decision rule was precommitted. The scratch-only artifact lacks a document-parser protocol/category/attestation and cannot gate adoption, routing, promotion, or closure. Harness: `odl_bench/run_three_way_bench.py` (research `a16aa0d9`); local artifact `/mnt/raid0/llm/tmp/odl013-bench-20260813T1336Z/`.
- [x] **ODL-013 execute and record the representative comparison** under an inference-owned CPU window, with an explicit page/document scoring bridge, pinned transient dependencies, and a fast-path policy verdict. ✅ **EXECUTION COMPLETE 2026-08-13; REQUESTED VERDICT NOT LICENSED** — completed 13:36–13:38Z under the recorded inference grant using the upstream GT/evaluator and pinned LiteParse/OpenDataLoader/poppler dependencies. The independent audit accepts the quality output as reproducible comparative evidence, but rejects `ADOPT` because the record is scratch-only and has no applicable measurement protocol or precommitted selection rule. Timing remains summary-only, ODL's version is `?`, and prospective failure accounting is not fail closed.
- [x] **Independent ODL-013 and matched-parser audit.** ✅ 2026-08-13 — accepted both stored comparisons with follow-ups as sound observations, corrected the comparison report's `matched, decision-grade fixture` phrase by explicit supersession here, and kept all parser/routing defaults unchanged. The audit found 200 non-empty predictions per engine with exact upstream-evaluator replay; it did not find decision-grade warrant.
- [ ] Route complex, dense-table, and scanned documents away from LiteParse; it is a born-digital fast-path backend only.

### Model-backed parser arms and full rebaseline

- [x] **PaddleOCR-VL stronger parser / LightOnOCR comparison ✅ 2026-08-13**: a matched 200-PDF scored fixture was obtained for LiteParse, ODL, and pdftotext. The point estimates are useful comparative observations, not a promotion or routing decision: the local comparison report's `matched, decision-grade fixture` wording is superseded by the independent audit above. PaddleOCR-VL remains retracted off-label; LightOnOCR remains scanned-document scope; the n=665 rebaseline and a protocol-admissible decision record remain open.
- [ ] **Re-baseline ODL end-to-end on the full set**: acquire the missing source PDFs/immutable manifest, then report table TEDS at n=665 with all-language and English-only splits.
- [ ] **Void and re-run the PaddleOCR-VL arm** through the real `PaddleOCRVL` pipeline with `vl_rec_backend="llama-cpp-server"`, or restrict llama.cpp-only testing to cropped elements with the official six prompts. Do not cite the prior `0.0`/`0.058` TEDS numbers.
- [ ] **P1 — evaluate MinerU2.5-Pro (1.2B) and GLM-OCR (0.9B)**: check single-pass vs pipeline architecture and llama.cpp/GGUF availability first; create one intake entry per candidate before measurement.
- [ ] **P2 — Unlimited-OCR as a single-pass arm**: preserve the stock full-MHA path, Q5_K_M-or-better body, `lm_head >= Q8_0`, and conservative loop guard; do not take draft R-SWA PR #24975 into the production kernel.
- [x] **Correct the P2 observation record before using it** ✅ 2026-08-25 (mainA PIP-05): `progress/2026-08/2026-08-13-mainD.md` carries a supersession note — 18-page run retained as an observation; "root cause" → demonstrated prompt/profile mismatch (bare-passthrough GGUF chat template verified; "coordinate output regardless of prompt" NOT — llama.cpp canonical `tools/mtmd/tests/test-deepseek-ocr.py` records prompt-dependent behavior). Timing narrative corrected: stored receipt reports only `held_s=1.002881998` (pre-`aca459d9` ~1s post-health snapshot), not full-interval proof, and the run dir artifact is no longer on disk (`aca459d9` fixes future runs only). Remaining: canonical-profile A/B (row below), gated on inference-stop order lifting.
- [ ] **Run the canonical Unlimited-OCR profile as a fresh matched A/B after inference resumes**: use `document parsing.`, `n_predict=4096`, `n_ctx=16384`, DRY, and grounding-strip exactly as `tools/mtmd/tests/test-deepseek-ocr.py` specifies; preserve both profiles, score the stripped output, and require a new inference-window receipt spanning server launch through termination. This is blocked only on the operator's all-inference-stop order being lifted and a new Inference grant.
- [ ] **Make the default Unlimited-OCR artifact quant-compliant**: replace/requantize the default model so `output.weight`/`lm_head` is at least Q8_0, record immutable SHA-256 plus tensor audit, and update `DEFAULT_MODEL`. *(2026-08-13 lane/mainD `a08b24dc`: a requantized `Unlimited-OCR-Q5_K_M-outq8.gguf` (2.26 GB, `output.weight` → q8_0 via `llama-quantize --allow-requantize --output-tensor-type q8_0`, other 154 tensors byte-copied, verified via `llama-gguf`) exists under `/mnt/raid0/llm/models/Unlimited-OCR-GGUF/` and `DEFAULT_MODEL` was repointed — research `c733e1ee`; the 22:18Z demo ran on it. Still missing: the immutable SHA-256 + tensor-audit record this row requires.)*
- [ ] **Run and score the 18-page OmniDocBench demo** only after the artifact gate and an inference grant: capture binary/model/mmproj digests, server argv, linkage/residency during the window, responses, CER/TEDS/reading-order/latency, failures, manifest contract, and cleanup proof.

## Completed Scope

| Scope | Durable outcome |
|---|---|
| Phase 1 extractor | ODL is the availability-aware default with pdftotext fallback, quality checks, batch support, and attribution. |
| Phase 2 structured substrate | Headings, figures, tables, cache/TaskIR carriers, injection scanning, and hybrid SDK routing are wired behind explicit gates. |
| Fast-path scaffolding | Local ODL/LiteParse/pdftotext/hybrid probe and July observations exist; they do not close policy. |
| Benchmark scaffolding | `odl_bench`, sibling NID/TEDS/MHS scorer, model-producer interface, and representative manifests are committed. |
| 2026-08-13 audits | ODL-013 is a reproducible full-corpus observation, not a decision record: no parser protocol/category/attestation, no precommitted selection rule, scratch-only durability, and summary-only timing. A14's exact patch was accepted. Unlimited-OCR's 18-page run is mechanically real, but its causal claim and mutex evidence need correction before a canonical rerun. |

See [completed implementation/evidence ledger](../completed/opendataloader-pipeline-integration-completed-through-2026-08-13.md) for commits, historical measurements, corrections, and closed checkpoints.

## Dependencies and Constraints

- Production orchestrator: `/workspace/repos/epyc-orchestrator`; benchmark code: `/workspace/repos/epyc-inference-research/scripts/benchmark/odl_bench/`.
- OpenDataLoader benchmark: `/mnt/raid0/llm/opendataloader-bench-upstream` (200 PDFs). OmniDocBench checkout: `/mnt/raid0/llm/omnidocbench` (renamed 2026-08-25 from the colliding `/mnt/raid0/llm/opendataloader-bench`) and page dataset `/mnt/raid0/llm/datasets/omnidocbench/`.
- Full-corpus ODL replay needs source PDFs or a deliberate document/page bridge; annotations and page images alone cannot reproduce PDF extraction.
- Live model-backed comparisons require an inference-owned window. Non-compute implementation, dependency pinning, artifact audits, and scoring-bridge work do not.
- Production llama.cpp v9 is frozen. Experimental kernel work must follow the version-past-production workflow; the current Unlimited-OCR scaffold needs no kernel patch.
- The ten-document Phase-2 chunk fixture and downstream RAG answer-correctness endpoint are mandatory. Ekimetrics/HOPE intrinsic scores cannot gate alone; RC/FMRE stay excluded until independently verified/licensed.

## Key Files

- Orchestrator: `src/services/pdf_router.py`, `src/services/document_preprocessor.py`, `src/services/document_chunker.py`, `src/services/figure_analyzer.py`, `src/models/odl_structured.py`.
- Research: `scripts/benchmark/odl_bench/`, `scripts/benchmark/document_extraction_adapter.py`.
- Related handoff: [Document Parser Table Bench](document-parser-table-bench.md).
- Evidence review: [2026-08-13 auditor progress](../../progress/2026-08/2026-08-13-auditor.md).

## Reporting Contract

For every run, record corpus/manifest digest, exact engine/dependencies/model/binary, metric direction and denominator, per-document failures, latency distribution, environment/residency proof during the observation window, and cleanup. Treat vendor numbers and unmatched historical artifacts as context, never as promotion evidence.
