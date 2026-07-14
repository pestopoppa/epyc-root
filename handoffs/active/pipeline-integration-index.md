# Pipeline Integration — Coordination Index

**Status**: active
**Updated**: 2026-07-14 backlog ROI audit — vision row retired to baseline, quiet-window probe row folded into ODL row, DS-E1-gated idle-teardown closed by decision, KB-RAG dispatch entries added
**Purpose**: dispatch surface for new capability pipelines being added to the EPYC stack. Production routing, stack, and evidence-plane behavior route through [routing-and-optimization-index.md](routing-and-optimization-index.md).
**History**: pre-compaction detail lives in [../archived/pipeline-integration-index-history-through-2026-06-19.md](../archived/pipeline-integration-index-history-through-2026-06-19.md).

## Start Here

1. Read [master-handoff-index.md](master-handoff-index.md) for global priority and live inference-lane constraints.
2. Check the owning handoff before editing a pipeline; this index is only the dispatch layer.
3. Coordinate any model server load, reload, or benchmark with [bulk-inference-campaign.md](bulk-inference-campaign.md) and the current RAM/NUMA state.
4. Use `/workspace/MEASUREMENT.md` for benchmark claims, cache-state labels, and acceptance evidence.
5. Update this index only when priority, gate, or ownership changes; put chronology in the owning handoff or progress log.

## Active Queue

| Priority | Pipeline | Owner handoff | Current gate / next action |
|----------|----------|---------------|----------------------------|
| P0.5 | Local image generation | [ernie-image-turbo-evaluation.md](ernie-image-turbo-evaluation.md) | CPU backend is deployed; remaining work is prompt-enhancer heuristic, content-filter audit, typography spot-check, and the **GPU rebench — now UNBLOCKED (MI210 landed 2026-07-02)**: build sd-server on the ROCm/HIP path and measure the DiT on gfx90a (operator-approved; no published gfx90a numbers). |
| P1 | PDF extraction / OpenDataLoader / LiteParse | [opendataloader-pipeline-integration.md](opendataloader-pipeline-integration.md) | ODL structured context now feeds chunking and per-figure VL prompts, local PDF processing can produce it under explicit `PDF_EXTRACTOR=opendataloader` + `ORCHESTRATOR_ODL_STRUCTURED=1` gates, ODL structured figure bboxes replace PyMuPDF image enumeration in that mode, unsafe ODL structured metadata is suppressed when `INJECTION_SCANNING` is enabled, ODL tables now flow through preprocessing/cache/TaskIR output, a default-inert `ORCHESTRATOR_ODL_TABLE_BACKEND` seam exists, and `ORCHESTRATOR_DOCUMENT_BODY_INJECTION_POLICY=warn` provides default-off primary body warnings. `scripts/benchmark/pdf_fastpath_probe.py` now supports no-inference backend evidence with corpus labels, manifests, per-backend structural totals, structural-signal PDF coverage/fraction, an opt-in `--require-structural-signal` guard, and a sidecar-aware `opendataloader_hybrid` backend that reports missing SDK/sidecar dependencies explicitly. Router outputs now stamp the effective producer (`opendataloader_structured` vs `opendataloader_hybrid`) so hybrid evidence is attributable without enabling hybrid by default. `scripts/benchmark/build_pdf_probe_manifest.py` now builds repeatable structural/table-heavy candidate manifests for quiet-window ODL/LiteParse/hybrid batches. The 2026-07-04 filtered 8-PDF local corpus probe shows pdftotext/ODL/LiteParse all succeed on `7/8` valid PDFs, with ODL higher median quality but much slower; the structural-metadata rerun reports `0` ODL headings/tables/figures and `0` LiteParse bboxes/page images despite `1195` table-like text lines. 2026-07-06 manifest/probe checkpoint: a 27-PDF structural manifest was built from `epyc/claude` + `hy-mt2-1.8b/base-metadata`, and the quiet-window probe on that manifest showed structural signal on `27/27` PDFs, `table_like_lines=19725`, pdftotext median `121.591 ms / 0.928`, ODL structured `2877.039 ms / 1.000`, and LiteParse `91.897 ms / 0.959`. 2026-07-06 live sidecar checkpoint: `opendataloader-pdf-hybrid` is now running on `127.0.0.1:5002` and the same 27-PDF manifest returned `27/27` successful hybrid parses with median `1510.743 ms / 1.000`. 2026-07-07 quiet-window hybrid all-local probe (retired row, folded here): hybrid succeeded `27/27` and quality ties ODL structured; artifacts `pdf_fastpath_probe_hybrid_alllocal_20260707T004440Z`. The surviving gap is a benchmark-backed table-selection/routing-policy comparison — the sidecar IS live on `127.0.0.1:5002`, so viability is no longer in question. |
| P2 | Lean 4 proving | Completed Lean baseline plus this index | Goedel-CP GGUF exists as a candidate; next active work is Leanstral expert profiling, then REAP prune and end-to-end proof-pipeline validation if profiling supports it. |
| P3 | Multimodal TTS | [multimodal-pipeline.md](multimodal-pipeline.md) | Benchmark the first viable path among Qwen3 TTS, MiniCPM-O, Qwen3-TTS sidecar, or ZipVoice-Distill; promote only with RTF/latency/WER/memory evidence. |
| P4 | Doc-to-LoRA | [08-doc-to-lora-prototype.md](../completed/08-doc-to-lora-prototype.md) | Archived/low priority; AND-gate: GPU availability ✅ (MI210 landed 2026-07-02, though LoRA-training viability on gfx90a is [unverified]) but the second conjunct — a demonstrated need not solved by REPL tooling — remains ✗ (recorded as covered by REPL). **Net: stays closed** — one gate opened, the load-bearing gate did not. (See also the cross-model-LoRA-transfer intake cluster intake-764..771 — a lightweight watch, same reopen trigger.) |
| P5 | Internal KB-RAG | [internal-kb-rag.md](internal-kb-rag.md), [colbert-reranker-web-research.md](colbert-reranker-web-research.md) | K7 certification is complete; default-signal decision stays on the owning handoff; deferred K8 wikilink scorer waits on a measured wiki cross-link gap. Open dispatch (2026-07-14): (a) AutoWiki model-backed page writer — the only remaining core gap [inference-window gated]; (b) `recency_w0.3_s90` default-retrieval-weight promotion decision (decision-only from existing sweep evidence; inference-window only if re-measurement is required); (c) K11 FTS5 lexical signal — landed default-off (orchestrator `74120be`), measure-first before any default-weight promotion [inference-window gated]. Checklist items below. |
| GATED (GPU + REPL-need reopen-trigger) | Code2LoRA evolution variant | [08-doc-to-lora-prototype.md](../completed/08-doc-to-lora-prototype.md) | (added 2026-06-20 via research-intake batch deep-dive) intake-707; logged against the 08-doc-to-lora-prototype reopen-trigger (GPU + REPL-uncovered need). New bits are Evo/GRU-per-diff + RepoPeftBench. Hot-swap is DONE (Finding 1); the gap is orchestrator LoRA wiring (Finding 7). |
| CONDITIONAL (no live consumer) | neural-txt 135M doc-NLP specialist | [opendataloader-pipeline-integration.md](opendataloader-pipeline-integration.md) | (added 2026-06-20 via research-intake batch deep-dive) intake-718; watch-item. Re-surface only if ODL pipeline grows a cheap structured-NLP-extraction stage (bullets/Q&A/KG-triplets). document_formalizer today is a 1B OCR VLM. |
| GPU-training-viability-GATED (MI210 present; training-on-gfx90a [unverified]) | UniRL diffusion/LLM RL | [gpu-acceleration-path.md](gpu-acceleration-path.md) | (added 2026-06-20; re-triaged 2026-07-03) intake-709. The "no training GPU" blocker is STALE — the MI210 landed 2026-07-02 (it was a DGX Spark being *considered*, never bought). Remaining blocker downgraded to: gfx90a training-viability is [unverified] + fit-of-a-diffusion-RL-loop on one 64 GB card unassessed. Runs behind the gfx90a training smoke that also gates F3-W3. A CPU image-gen role (sd_server/ERNIE-Image-Turbo) IS deployed. |

## Closed / Baseline (retired 2026-07-14)

Rows retired from the Active Queue by the 2026-07-14 backlog ROI audit. Reopen only on the stated condition; otherwise treat as live baseline.

| Pipeline | Owner handoff | Closure |
|----------|---------------|---------|
| Multimodal vision validation (was P0) | [multimodal-pipeline.md](multimodal-pipeline.md) | CLOSED 2026-07-14 — work complete, baseline live: direct analyzer smokes passed on `8086/8087`; `vision_analyze`/`vision_search`/`vision_face_identify` are in `tool_registry.yaml`; reloaded API passed `/v1/vision/analyze` smoke 2026-07-03; orchestrator `9833a5b8` bridged OpenAI-compatible multipart `image_url` data URLs into the chat vision handler. Owning handoff is Priority: LOW with no active blocker. Remote-image fetching or multi-image support = new scoped feature if wanted, not a reopen of this row. MiniCPM-O Phase 1 testing remains pending in the owning handoff — dispatched via the progress checklist below so it isn't lost. |
| Proactive cold-role idle-teardown (was GATED DS-E1) | [dynamic-stack-concurrency.md](dynamic-stack-concurrency.md) | CLOSED-BY-DECISION 2026-07-14 — the DS-E1 gate is RESOLVED, not pending: `ds_e1_evidence_packet_20260705T094913Z` reported `ready_for_profile_decision=true`, and the DS-7 decision (2026-07-04) = retain static-prewarm, park DS-6. Reopen condition: new evidence that static pre-warm leaves throughput/latency on the table. History: intake-701 (2026-06-20), drove-style RAM-reclaim for cold/rare roles; ASR-facade half already shipped via whisper_server.py `/v1/audio/transcriptions`. |

## Dependency Graph

```text
Vision live validation
  -> orchestrator tool registration
  -> quiet-window API restart + endpoint smoke

LiteParse/ODL extraction evidence
  -> PDF router fast-path decision
  -> structural sidecar or chunking changes
  -> gated local ODL structured producer path
  -> ODL table integration
  -> ODL table backend seam
  -> primary document-body safety policy
  -> ODL hybrid sidecar/client evidence

Leanstral profile
  -> REAP prune decision
  -> Lean two-tier integration

K-RAG / ColBERT shared encoder
  -> internal KB-RAG default retrieval decision
  -> search/web reranker reuse
```

## Cross-Cutting Concerns

- Pipeline models compete with production NUMA quarters and RAM. Check live stack state before loading vision, Lean, TTS, or PDF sidecars.
- Pipeline ports must not collide with production stack ports. Current known targets: vision `8086/8087`, ASR `9000`, TTS `9002`.
- PDF work splits into born-digital fast-path extraction and structural extraction. Do not let LiteParse evidence erase ODL's table/heading/figure role without a structural benchmark.
- KB-RAG and ColBERT web reranking should share encoder plumbing where practical; keep archive content out of the default corpus unless an explicit historical-retrieval mode exists.
- Hermes or orchestrator tool-surface changes must be reflected in the relevant owning handoff and, if API behavior changes, [routing-and-optimization-index.md](routing-and-optimization-index.md).

## Key Files

| Resource | Path |
|----------|------|
| Vision pipeline | `/mnt/raid0/llm/epyc-orchestrator/src/vision/` |
| PDF router | `/mnt/raid0/llm/epyc-orchestrator/src/services/pdf_router.py` |
| PDF fast-path probe | `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/pdf_fastpath_probe.py` |
| PDF structural manifest builder | `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/build_pdf_probe_manifest.py` |
| Document chunker | `/mnt/raid0/llm/epyc-orchestrator/src/services/document_chunker.py` |
| Stack launcher | `/mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py` |
| Full model registry | `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml` |
| Lean proving deep dives | `research/deep-dives/goedel-code-prover-analysis.md`, `research/deep-dives/leanstral-architecture-analysis.md` |
| Internal KB-RAG | `/mnt/raid0/llm/epyc-orchestrator/src/retrieval/` |

## Reporting

After completing a row:

1. Update the owning handoff first.
2. Update this index only if active priority, gate, ownership, or dependency order changes.
3. Append `progress/YYYY-MM/YYYY-MM-DD.md` with artifacts, command lines, runtime state, and validation evidence.
4. If RAM/NUMA allocation or API behavior changes, update [routing-and-optimization-index.md](routing-and-optimization-index.md) and the relevant stack or Hermes handoff.

## Progress checklist

- [x] P0 Multimodal vision: remaining remote-image/multi-image treated as new scoped feature (live smokes passed) ✅ 2026-07-14 row retired to Closed/Baseline
- [ ] P0.5 Local image gen: prompt-enhancer, content-filter audit, typography check, GPU DiT rebench on gfx90a (unblocked)
- [ ] P1 ODL/PDF: benchmark-backed hybrid-vs-baseline comparison + routing policy (sidecar viable on :5002)
- [x] P1 Quiet-window PDF structural corpus probe (AutoPilot-idle evidence step) ✅ 2026-07-07
- [ ] P2 Lean 4: Leanstral expert profiling -> REAP prune -> end-to-end proof pipeline
- [ ] P3 Multimodal TTS: benchmark first viable path (Qwen3-TTS/MiniCPM-O/ZipVoice) with RTF/WER evidence
- [ ] P3/multimodal-pipeline: MiniCPM-O Phase 1 testing (pending in owning handoff; carried from retired P0 vision row)
- [ ] P5 Internal KB-RAG: deferred K8 wikilink scorer once measured cross-link gap exists
- [ ] P5 KB-RAG: AutoWiki model-backed page writer — only remaining core gap [inference-window gated]
- [ ] P5 KB-RAG: recency_w0.3_s90 default-retrieval-weight promotion decision (decision-only unless re-measurement needed)
- [ ] P5 KB-RAG: K11 FTS5 lexical signal — measure-first before default-weight promotion (landed default-off, orchestrator 74120be) [inference-window gated]
