# Historical ledger — superseded index narration (through 2026-08-10)

> **Historical ledger only; current work lives in [`../active/pipeline-integration-index.md`](../active/pipeline-integration-index.md).**
> Extracted 2026-08-10 in the index restructure: rows became thin and machine-parseable (`ID | Track | Handoff | Next action | Deps`), and status moved to generated state (`handoffs/active/.index-state.json` + the rollup block in `master-handoff-index.md`).
>
> Everything below is the index content **verbatim as of 2026-08-10**, preserved for provenance: closed rows, evidence citations, retracted rows, and campaign narration. It is not a task list — do not dispatch from it. Where a row here contradicts the active index, the active index wins.

---

# Pipeline Integration — Coordination Index

**Status**: active
**Updated**: 2026-07-31 — **TTS unblocked** (upstream `qwentts.cpp`: round-trip WER 0.0%, TTFA 67.9 ms, 0.86× RT on CPU); **ASR arm opened** (Qwen3-ASR serves on the MI210 with zero kernel change, WER 72.14% from a config defect with a named suspect); **STT offline hardening closed**. Prior: 2026-07-17 PaddleOCR-VL table post-processing checkpoint surfaced — prompt-only HTML table recovery stayed negative; pipe-table HTML conversion moves table TEDS off zero but is not table-quality-clean. Prior: 2026-07-14 backlog ROI audit retired vision row, folded quiet-window probe into ODL row, closed DS-E1-gated idle-teardown by decision, and added KB-RAG dispatch entries.
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
| P1 | PDF extraction / OpenDataLoader / LiteParse | [opendataloader-pipeline-integration.md](opendataloader-pipeline-integration.md) | ODL is the default extractor (Phase 1 landed 2026-07-17); structured context feeds chunking and per-figure VL prompts under explicit gates, and the `opendataloader-pdf-hybrid` sidecar is live on `127.0.0.1:5002` (`27/27` parses, median `1510.743 ms / 1.000`). **Open**: benchmark-backed table-selection / routing-policy decision. **Table-quality evidence moved to [document-parser-table-bench.md](document-parser-table-bench.md)** — prior `0` ODL headings/tables/figures and PaddleOCR-VL `table.TEDS=0.0` numbers are RETRACTED 2026-07-20 (corpus and invocation artifacts; see that handoff). |
| P1 | Document parser table extraction (benchmark) | [document-parser-table-bench.md](document-parser-table-bench.md) | Full OmniDocBench local (1651 pages / 665 tables) and PaddleOCR env installed. **Next**: Phase B correct-invocation smoke — confirm PaddleOCR-VL-1.6 emits real HTML tables via its 3-stage pipeline (`--vl_rec_backend llama-cpp-server`) before spending a full run. Phases B/C need operator inference approval. |
| P2 | Lean 4 proving | Completed Lean baseline plus this index | Goedel-CP GGUF exists as a candidate; next active work is Leanstral expert profiling, then REAP prune and end-to-end proof-pipeline validation if profiling supports it. |
| P3 | Multimodal TTS — **PATH FOUND 2026-07-31** | [multimodal-pipeline.md](multimodal-pipeline.md) | ~~Benchmark the first viable path among Qwen3 TTS, MiniCPM-O, Qwen3-TTS sidecar, or ZipVoice-Distill~~ — **ANSWERED: upstream `qwentts.cpp` (Path E).** Measured CPU: round-trip **WER 0.0%**, **TTFA 67.9 ms**, **0.86× RT**, 1.19 GB Q8_0 pair; `CodecDecode` is 64% of wall. Our port's noise came from its hand-rolled codec half. **Open**: S-6 GPU bench **IN FLIGHT** (`/mnt/raid0/llm/tmp/tts_bench_results.txt`, no numbers yet) → S-9 wire `start_tts()` into `orchestrator_stack.py` (port 9002) → S-11 register the GGUF pair (MRG-1). Path C (`scripts/voice/tts_server.py`, PyTorch) demoted to fallback — its ~0.9× RT was always an estimate, never measured. |
| P3b | Speech ASR — **Qwen3-ASR on MI210, config-broken** | [multimodal-pipeline.md](multimodal-pipeline.md) | Serves on the GPU with **zero kernel change** (frozen v8 ships `tools/mtmd/models/qwen3a.cpp` + `libmtmd.so.0.0.10107`). **WER 72.14% is a configuration defect, not a model verdict** — utterances >~11 s degenerate to `????????`, short ones are perfect, and 8k→65536 context changed nothing. **Next: S-7, test the bf16 audio projector** (on disk, untested) — the cheapest experiment in this lane. Prize: wall/request median **2.14 s** vs whisper's **4.2 s fixed floor**. Do not trade latency against a 72% WER — resolve the defect first (S-10). |
| — | Speech STT offline hardening | [multimodal-pipeline.md](multimodal-pipeline.md) | **CLOSED ✅ 2026-07-31** — `whisper_server.py` resolved a model NAME through `huggingface_hub` on every cold start and failed **silently** (whisper is in `OPTIONAL_AUXILIARY_ROLES`). Now `local_files_only` + `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE`, escape hatch `WHISPER_ALLOW_DOWNLOAD=1`; loads in 1.42 s with no network. Repo `epyc-inference-research`. |
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

- Pipeline models compete with the production NUMA fleet and RAM. Check live stack state before loading vision, Lean, TTS, or PDF sidecars. **⚠ Updated 2026-07-30: quarters are RETIRED** — every quarterable role is now **1 full + 2 halves** (full `0-95`; half A `0-47,96-143` = nodes 0,1, **GPU-disjoint**; half B `48-95,144-191` = nodes 2,3, **GPU co-tenant**), and ports `8280 8380 8282 8382 8385 8485` are freed. Schedule sidecars that must not collide with the GPU lane on **half A**. The vision pair now carries explicit `membind=1` / `membind=3` because the two roles share ONE GGUF and, under shared mmap, only one of them could ever be node-local. See [numa-topology-cutover-resume-20260730.md](numa-topology-cutover-resume-20260730.md).
- Pipeline ports must not collide with production stack ports. Current known targets: vision `8086/8087`, ASR `9000`, TTS `9002` (**reserved but still unwired as of 2026-07-31** — the TTS *capability* now exists via `qwentts.cpp`; `start_tts()` does not).
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
- [x] P3 Multimodal TTS: benchmark first viable path with RTF/WER evidence — **DONE ✅ 2026-07-31**. The viable path is upstream **`qwentts.cpp`** (not the PyTorch sidecar, not ZipVoice, not MiniCPM-O which was struck the same day): CPU round-trip **WER 0.0%**, **TTFA 67.9 ms**, **0.86× RT**, memory 1.19 GB (Q8_0 Talker + tokenizer). RTF/WER/latency/memory evidence all present, which is exactly what this row demanded.
- [x] P3 TTS follow-through: **S-6 GPU bench** ✅ 2026-07-31 — hypothesis confirmed: xRT **0.86× → 5.47×**, TTFA **67.9 → 37.8 ms**, `CodecDecode` **64% → 10.4%**, round-trip WER 1.49%. Required a real gfx90a `ARGSORT` fix (S-6a); HIP graphs were never a separate bug and are now 13.2% faster, bit-identical
- [ ] P3 TTS follow-through: **S-9 wire `start_tts()` into `orchestrator_stack.py`** (port 9002 reserved) — capability exists, service wiring does not
- [ ] P3 TTS follow-through: **S-11 register the Qwen3-TTS GGUF pair + `qwentts.cpp` tree** in the manifest/registry per MRG-1, so the speech stack is discoverable outside progress logs
- [ ] P3 TTS follow-through: **S-13 pin the qwentts.cpp fork as a versioned dependency, do NOT merge it into our llama.cpp** (operator decision 2026-07-31) · **S-14 upstream the argsort fix**
- [x] P3b ASR: **S-7 / S-8** ✅ 2026-07-31 — **superseded**. The bf16 projector was not the cause and it is not a scoring artifact (extended normalization moved WER 29.36% → 28.88%): it is a degenerate repetition loop on 21/100 rows carrying 94.7% of errors, duration-correlated (0% under 3 s, 50% at 7–30 s), clean rows 2.27%
- [x] P3b ASR: **S-10 decide whether Qwen3-ASR augments or replaces whisper** ✅ 2026-07-31 — **neither; Qwen3-ASR DROPPED.** whisper.cpp large-v3-turbo f16 on MI210 gives WER 2.35% (identical to incumbent) at wall median **0.124 s** / max 0.218 s vs 4.240 s — the GPU max is 19× below the incumbent's minimum. The 4.2 s fixed floor is gone, which removes the whole reason Qwen3-ASR was in contention
- [ ] P3c STT: **S-12 register whisper.cpp large-v3-turbo f16 (MI210) as the STT model** and retire the CPU whisper path from the stack definition (MRG-1)
- [x] P0 Vision model selection — **SETTLED ✅ 2026-07-31**: **Qwen3-VL-30B-A3B Q4_K_M** wins MMMU val (250 stratified MCQ, identical rows, temp 0.2/seed 42) at **63.6% vs incumbent 52.4%, +11.2pp, McNemar p=0.0011**, 21.0 GB. The 8B (57.2%, p=0.21) and 4B (54.0%, p=0.72) are NOT separable from the incumbent. The earlier 42q suite **mis-ranked** the field
- [ ] P0 Vision follow-through: **S-15 set `max_tokens ≥ 1024` on the vision role** — a `max_tokens=128` cap produced 3 parse failures for the incumbent vs **41 and 50** for the Qwen3-VL arms. This is a production config change and it **gates** S-16
- [ ] P0 Vision follow-through: **S-16 promote Qwen3-VL-30B-A3B Q4_K_M to the vision role**, retire Qwen2.5-VL-7B (MRG-1) · **S-17 audit the ~51.8/64 GB GPU resident-set budget** before any fifth GPU model lands
- [x] Speech STT offline hardening ✅ 2026-07-31 — `local_files_only` + offline env pins, `WHISPER_ALLOW_DOWNLOAD=1` escape hatch; verified 1.42 s cold load with no network
- [x] P3/multimodal-pipeline: MiniCPM-O Phase 1 testing — **CANCELLED ✅ 2026-07-31**. Phase 1 reached its verdict in the owning handoff and the verdict is a decline: MiniCPM-o scored 31/42 on 42q OCRBench+ChartQA vs the Qwen2.5-VL-7B incumbent's 35/42, so it is a vision downgrade; its speech case is superseded by a dedicated 1.14 GB CPU Qwen3-TTS plus existing whisper/Qwen3-ASR. Weights deleted (22 GB). No further Phase-1 testing will occur.
- [ ] P5 Internal KB-RAG: deferred K8 wikilink scorer once measured cross-link gap exists
- [ ] P5 KB-RAG: AutoWiki model-backed page writer — only remaining core gap [inference-window gated]
- [ ] P5 KB-RAG: recency_w0.3_s90 default-retrieval-weight promotion decision (decision-only unless re-measurement needed)
- [ ] P5 KB-RAG: K11 FTS5 lexical signal — measure-first before default-weight promotion (landed default-off, orchestrator 74120be) [inference-window gated]
