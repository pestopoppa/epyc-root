# Pipeline Integration — Coordination Index

**Status**: active
**Updated**: 2026-07-06 ODL structural manifest builder; vision live-server/tool checkpoint
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
| P0 | Multimodal vision validation | [multimodal-pipeline.md](multimodal-pipeline.md) | Live direct analyzer smokes passed on `8086/8087`, `vision_analyze`/`vision_search`/`vision_face_identify` are in `tool_registry.yaml`, the reloaded API passed `/v1/vision/analyze` smoke on 2026-07-03, and orchestrator `9833a5b8` bridged OpenAI-compatible multipart `image_url` data URLs into the existing chat vision handler. Remaining vision work is no longer a blocker here; any remote-image fetching or multi-image support should be treated as a new scoped feature. |
| P0.5 | Local image generation | [ernie-image-turbo-evaluation.md](ernie-image-turbo-evaluation.md) | CPU backend is deployed; remaining work is prompt-enhancer heuristic, content-filter audit, typography spot-check, and the **GPU rebench — now UNBLOCKED (MI210 landed 2026-07-02)**: build sd-server on the ROCm/HIP path and measure the DiT on gfx90a (operator-approved; no published gfx90a numbers). |
| P1 | PDF extraction / OpenDataLoader / LiteParse | [opendataloader-pipeline-integration.md](opendataloader-pipeline-integration.md) | ODL structured context now feeds chunking and per-figure VL prompts, local PDF processing can produce it under explicit `PDF_EXTRACTOR=opendataloader` + `ORCHESTRATOR_ODL_STRUCTURED=1` gates, ODL structured figure bboxes replace PyMuPDF image enumeration in that mode, unsafe ODL structured metadata is suppressed when `INJECTION_SCANNING` is enabled, ODL tables now flow through preprocessing/cache/TaskIR output, a default-inert `ORCHESTRATOR_ODL_TABLE_BACKEND` seam exists, and `ORCHESTRATOR_DOCUMENT_BODY_INJECTION_POLICY=warn` provides default-off primary body warnings. `scripts/benchmark/pdf_fastpath_probe.py` now supports no-inference backend evidence with corpus labels, manifests, per-backend structural totals, structural-signal PDF coverage/fraction, an opt-in `--require-structural-signal` guard, and a sidecar-aware `opendataloader_hybrid` backend that reports missing SDK/sidecar dependencies explicitly. Router outputs now stamp the effective producer (`opendataloader_structured` vs `opendataloader_hybrid`) so hybrid evidence is attributable without enabling hybrid by default. `scripts/benchmark/build_pdf_probe_manifest.py` now builds repeatable structural/table-heavy candidate manifests for quiet-window ODL/LiteParse/hybrid batches. The 2026-07-04 filtered 8-PDF local corpus probe shows pdftotext/ODL/LiteParse all succeed on `7/8` valid PDFs, with ODL higher median quality but much slower; the structural-metadata rerun reports `0` ODL headings/tables/figures and `0` LiteParse bboxes/page images despite `1195` table-like text lines. This is fast-path evidence only. Next work is running the generated structural/table-heavy manifest through ODL/LiteParse and, after sidecar health check, `opendataloader_hybrid` before any router policy change. |
| P1 | Quiet-window PDF structural corpus probe | [opendataloader-pipeline-integration.md](opendataloader-pipeline-integration.md) | Use only in an AutoPilot-idle window with a structural/table-heavy corpus and, if available, the hybrid sidecar output; this is the missing evidence step after the fast-path probe. | Can share with other AutoPilot-off doc-analysis work if the ODL stack is isolated; do not co-run with DS-E1 or other full-stack shutdown work. | `pdf_fastpath_probe` JSON/MD with backend attribution, structural-signal totals, and missing-dependency diagnostics if hybrid is absent. |
| P2 | Lean 4 proving | Completed Lean baseline plus this index | Goedel-CP GGUF exists as a candidate; next active work is Leanstral expert profiling, then REAP prune and end-to-end proof-pipeline validation if profiling supports it. |
| P3 | Multimodal TTS | [multimodal-pipeline.md](multimodal-pipeline.md) | Benchmark the first viable path among Qwen3 TTS, MiniCPM-O, Qwen3-TTS sidecar, or ZipVoice-Distill; promote only with RTF/latency/WER/memory evidence. |
| P4 | Doc-to-LoRA | [08-doc-to-lora-prototype.md](../completed/08-doc-to-lora-prototype.md) | Archived/low priority; AND-gate: GPU availability ✅ (MI210 landed 2026-07-02, though LoRA-training viability on gfx90a is [unverified]) but the second conjunct — a demonstrated need not solved by REPL tooling — remains ✗ (recorded as covered by REPL). **Net: stays closed** — one gate opened, the load-bearing gate did not. (See also the cross-model-LoRA-transfer intake cluster intake-764..771 — a lightweight watch, same reopen trigger.) |
| P5 | Internal KB-RAG | [internal-kb-rag.md](internal-kb-rag.md), [colbert-reranker-web-research.md](colbert-reranker-web-research.md) | K7 certification is complete; default-signal decision stays on the owning handoff, and the only concrete no-inference follow-up here is the deferred K8 wikilink scorer once a measured wiki cross-link gap exists. |
| GATED (GPU + REPL-need reopen-trigger) | Code2LoRA evolution variant | [08-doc-to-lora-prototype.md](../completed/08-doc-to-lora-prototype.md) | (added 2026-06-20 via research-intake batch deep-dive) intake-707; logged against the 08-doc-to-lora-prototype reopen-trigger (GPU + REPL-uncovered need). New bits are Evo/GRU-per-diff + RepoPeftBench. Hot-swap is DONE (Finding 1); the gap is orchestrator LoRA wiring (Finding 7). |
| GATED (DS-E1 evidence) | Proactive cold-role idle-teardown | [dynamic-stack-concurrency.md](dynamic-stack-concurrency.md) | (added 2026-06-20 via research-intake batch deep-dive) intake-701; drove-style optional RAM-reclaim for cold/rare roles (DS-7-profile). Distinct from DS-6 quarter-eviction + earlyoom; never for hot pre-warmed roles. ASR-facade half DROPPED — already shipped: whisper_server.py /v1/audio/transcriptions. |
| CONDITIONAL (no live consumer) | neural-txt 135M doc-NLP specialist | [opendataloader-pipeline-integration.md](opendataloader-pipeline-integration.md) | (added 2026-06-20 via research-intake batch deep-dive) intake-718; watch-item. Re-surface only if ODL pipeline grows a cheap structured-NLP-extraction stage (bullets/Q&A/KG-triplets). document_formalizer today is a 1B OCR VLM. |
| GPU-training-viability-GATED (MI210 present; training-on-gfx90a [unverified]) | UniRL diffusion/LLM RL | [gpu-acceleration-path.md](gpu-acceleration-path.md) | (added 2026-06-20; re-triaged 2026-07-03) intake-709. The "no training GPU" blocker is STALE — the MI210 landed 2026-07-02 (it was a DGX Spark being *considered*, never bought). Remaining blocker downgraded to: gfx90a training-viability is [unverified] + fit-of-a-diffusion-RL-loop on one 64 GB card unassessed. Runs behind the gfx90a training smoke that also gates F3-W3. A CPU image-gen role (sd_server/ERNIE-Image-Turbo) IS deployed. |

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
