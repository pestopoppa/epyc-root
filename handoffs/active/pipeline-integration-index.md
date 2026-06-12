# Pipeline Integration — Coordination Index

**Status**: active
**Created**: 2026-04-04
**Purpose**: Entry point for agents working on new capability pipelines being added to the EPYC stack. Each pipeline adds a new modality or data processing capability.

> **2026-06-12**: Fable 5 architecture review complete — verdicts + new owning handoffs in [master-handoff-index.md](master-handoff-index.md); standing reference [fable5-findings-00-executive-summary.md](fable5-findings-00-executive-summary.md). Measurement claims now follow /workspace/MEASUREMENT.md.

---

## Agent Operating Instructions

1. Read **Outstanding Tasks** to find work items
2. All pipelines compete for NUMA quarters and RAM — check **Cross-Cutting Concerns** before provisioning models
3. After completing work: update checkbox here, update handoff document, update `progress/YYYY-MM/YYYY-MM-DD.md`

---

## Subsystem Status

| Handoff | Domain | Status | Priority | Last Updated |
|---------|--------|--------|----------|-------------|
| [multimodal-pipeline.md](multimodal-pipeline.md) | Vision + TTS + ASR | mixed (vision done, **TTS Path D candidate surfaced 2026-04-17** — LuxTTS/ZipVoice-Distill CPU benchmark) | LOW | 2026-04-17 |
| [ernie-image-turbo-evaluation.md](ernie-image-turbo-evaluation.md) | Self-hosted text-to-image / Hermes `image_generate` replacement | Refreshed 2026-05-28: production on CPU via sd-server Q8 + conv-direct (~3 min/image @ 1024²); remaining work is prompt-enhancer/content-filter/typography spot-check + GPU/Spark rebench | MEDIUM | 2026-05-28 |
| [opendataloader-pipeline-integration.md](opendataloader-pipeline-integration.md) | PDF extraction | active (magika evaluated + skipped 2026-04-17; **LiteParse born-digital fast-path candidate added 2026-05-29 → P1b**) | P2 (medium) | 2026-05-29 |
| ~~[lean-proving-pipeline.md](../completed/lean-proving-pipeline.md)~~ | Lean 4 theorem proving | merged into § P2 below (2026-04-21) | P2 (medium) | 2026-04-21 |
| [08-doc-to-lora-prototype.md](../completed/08-doc-to-lora-prototype.md) | Document → LoRA fine-tune | ARCHIVED 2026-06-12 (solved-by-REPL; Findings 1-8 preserved in file; Phase B reopen = training GPU + demonstrated need) | P3 (low) | 2026-06-12 |
| [internal-kb-rag.md](internal-kb-rag.md) | Internal markdown KB retrieval pipeline | STUB 2026-04-25 — sibling consumer of colbert-reranker-web-research's ONNX/MaxSim plumbing; no AR-3 gate | P5 (medium) | 2026-04-25 |

---

## Outstanding Tasks (Priority Order)

### P0 — Multimodal Vision (validation)

- [ ] Live validation with model servers (ports 8086/8087) — `--no-display-prompt` bug FIXED 2026-04-08 (removed from `vl_describe.py`). Re-test needed with VL servers.
- [ ] Register vision tools in orchestrator tool surface
- [x] Test OpenAI-compat multimodal API passthrough — ✅ FIXED 2026-04-08. `content: str | list` + `_extract_text()` helper. Re-test with actual multipart content needed.

### P0.5 — Local Image Generation

- [x] ERNIE-Image-Turbo Q8 local backend deployed through sd-server; Hermes `image_generate` plugin overrides disabled FAL path.
- [ ] Prompt-enhancer heuristic, content-filter audit, LongTextBench spot-check, and Spark performance reality check remain in [ernie-image-turbo-evaluation.md](ernie-image-turbo-evaluation.md).

### P1 — OpenDataLoader PDF (+ LiteParse born-digital fast path)

- [ ] **Phase 1**: Replace pdftotext with ODL local; swap extraction call; handle JVM lifecycle; update tests
- [ ] **Phase 1b (NEW 2026-05-29, via intake-646/647)**: Evaluate **LiteParse** (run-llama, Apache-2.0, JVM-free Rust, ~13 MB manylinux wheel) as the **born-digital fast-path** text+bbox+screenshot backend — a `pdftotext` competitor, NOT an ODL replacement (LiteParse has no heading/table/figure structure). Bench LiteParse-local vs ODL-local vs pdftotext with a LiteParse-output-aware harness. See [opendataloader-pipeline-integration.md](opendataloader-pipeline-integration.md) 2026-05-29 update + `research/deep-dives/liteparse-document-parser-deep-dive.md`.
- [ ] **Phase 2**: Parse ODL JSON for figures/tables; enrich VL model prompts; improve chunker with heading hierarchy
- [ ] **Phase 3**: Deploy hybrid sidecar; benchmark 3-way routing; run comparison suite (200 PDFs)
- [ ] Clone opendataloader-bench; implement NID/TEDS/MHS scoring
- **Future consideration (DD8, intake-436 W-RAC)**: if Phase 2+ introduces LLM-guided chunking for hard document classes (scanned PDFs, complex multi-column layouts), W-RAC's ID-addressable-unit pattern (decouple extraction from grouping; LLM for grouping decisions only, not content generation) is the preferred design. Trigger condition documented in `/workspace/research/deep-dives/intake-trio-202604-references.md`.

### P2 — Lean 4 Proving Pipeline (merged 2026-04-21 from `lean-proving-pipeline.md`)

**Architecture**: Two-tier proof pipeline analogous to OCR pattern (large model plans, small model executes at volume).

- **Tier 1 Planner**: Leanstral (119B MoE, 6.5B active; DeepSeek V3-style MoE + MLA; `deepseek2` in llama.cpp; Apache 2.0) — repo-scale context, proof strategy, subgoal decomposition. REAP-prune candidate (~20GB pruned vs ~68GB full Q4_K_M). 26.3 pass@2 on FLTEval.
- **Tier 2 Executor**: Goedel-Code-Prover-8B (Qwen3-8B base, no modifications; `qwen3` in llama.cpp; MIT) — tactic generation, leaf-goal proving, hierarchical search. 62.0% prove success on 427 tasks. Q4_K_M ~4.5GB, expected 25-40 t/s on EPYC 9655.
- **Verifier**: Lean 4 + Mathlib4 via lean-ray-server; lean-lsp-mcp for Leanstral integration.
- **Memory budget**: ~25GB combined (REAP-pruned Leanstral + Goedel-CP Q4_K_M) — massive headroom.

**Deep dives**: `research/deep-dives/goedel-code-prover-analysis.md`, `research/deep-dives/leanstral-architecture-analysis.md`.

- [ ] **S1: Convert Goedel-CP-8B to GGUF** — Download safetensors, `python convert_hf_to_gguf.py Goedel-LM/Goedel-Code-Prover-8B --outtype f16`, quantize Q4_K_M + Q8_0, validate proof generation via llama-server, add to model registry as `role: lean_prover`. Tracked as NIB2-15 (format conversion is non-inference; proof validation is inference-gated).
- [ ] **S2: Profile Leanstral expert activation** — Download `jackcloudman/Leanstral-2603-GGUF` Q4_K_M (~68GB), run with `--moe-expert-stats` on Lean 4 proof workloads. If ≤32 experts cover 95%: proceed with REAP. If spread is uniform: defer.
- [ ] **S3: REAP-prune Leanstral** (depends on S2) — Top-N experts (from S2), quantize Q4_K_M (~20GB target), benchmark quality on FLTEval subset.
- [ ] **S4: End-to-end pipeline test** (depends on S1) — Goedel-CP decomposition against local llama-server, FormalQualBench subset (5/23). Compare vs OpenGauss baseline (8/23).
- [ ] **S5: Two-tier integration** (depends on S3+S4) — Routing: Leanstral planning → Goedel-CP execution. Adapter between MCP output and Goedel-CP input. Full FormalQualBench (23 theorems).

**Open questions**:
- Leanstral planning output format alignment with Goedel-CP input expectations
- lean-ray-server and lean-lsp-mcp coexistence (single vs separate Lean toolchains)
- FormalQualBench appropriateness for code verification (vs Verina subset)
- Minimum viable concurrency for Goedel-CP
- Stripping Leanstral's Pixtral vision encoder (~1B dead params)

### P3 — Multimodal TTS (candidate Path D surfaced 2026-04-17)

- [ ] Path A (Qwen3 TTS): Debug codec token generation, compare C++ vs PyTorch reference
- [ ] Path B (MiniCPM-O): Phase 1 test of built-in CosyVoice2 TTS
- [ ] Path C (Qwen3-TTS PyTorch sidecar): FastAPI wrapper on port 8110; VRAM/latency benchmark on EPYC
- [ ] **Path D (NEW, 2026-04-17)**: CPU benchmark upstream `k2-fsa/ZipVoice-Distill` (ASRU 2025, arxiv:2506.13053) on EPYC 9655 — 6-config sweep per `research/deep-dives/luxtts-cpu-tts-candidate.md` §8 (1-thread baseline, PyTorch FP32 16/32-thread, ONNX FP32/INT8 16-thread, LuxTTS 48kHz variant). Metrics: RTF, first-packet latency, WER (whisper-large-v3 on LibriSpeech test-clean), SIM-o (WavLM-SV), UTMOS, memory peak. Promote if RTF<0.35, first-packet<400ms, WER<2.5, memory<2GB. Park if RTF>0.8 or WER>3.0 or memory>4GB. **1-week sidecar integration, NOT a llama.cpp port** (avoid Path A fate).
- [ ] Whichever path unblocks first → register TTS endpoint on port 9002

### P4 — Doc-to-LoRA (low priority)

- [ ] Validate Qwen3-4B checkpoint accessibility
- [ ] Implement D2L→GGUF format conversion for LoRA adapters
- [ ] (Note: core use case largely solved by existing REPL tooling — this is exploratory)

### P5 — Internal Knowledge-Base RAG (added 2026-04-25 from local-RAG architecture review)

Pointer — full plan tracked in [`internal-kb-rag.md`](internal-kb-rag.md). ColBERT-based retrieval over `wiki/`, `handoffs/active/`, `handoffs/completed/`, `research/`, `progress/`, `docs/chapters/` so Explore subagents stop grep/finding blind. Reuses the ONNX/MaxSim encoder being built for [`colbert-reranker-web-research.md`](colbert-reranker-web-research.md) — extract a shared encoder module (K1) so both consumers import the same path. **Not** AR-3-gated; can ship independently of S5/S6. Index-on-commit hook generalizes the existing GitNexus PostToolUse-on-commit pattern from code to markdown.

- [ ] **P5 rollup**: see `internal-kb-rag.md` K1..K7 — entry points for the next pass are K7 runtime/index/harness prep: restore/bless ONNX runtime, refresh the KB index, and add the HotpotQA/LoCoMo-style query/evidence set.
- [x] **P5 hybrid-signal follow-up (added 2026-05-27, from intake-611 agentmemory deep-dive)** — CODE LANDED 2026-05-27: K9 cross-encoder rerank (`src/retrieval/cross_encoder.py` + `kb_rag.query(rerank=…)`, ms-marco-MiniLM ONNX on disk) + K10 temporal Gaussian recency (`kb_rag.query(recency_weight=…)`, env-swept); 21 retrieval tests pass. K11 FTS5 still optional/measure-first. Graph/importance/activation explicitly NOT adopted. **Win-validation gated on K7 → bulk-inference-campaign Package K (K-RAG-1)**. 2026-06-12 diagnostic kept K9 worth testing (+4.17pp recall@10 on 8 stale-index cases) but did not justify default promotion; K10 recency was neutral. See `internal-kb-rag.md` § "Diagnostic Update — 2026-06-12" + `research/deep-dives/2026-05-27-agent-memory-cluster.md`.

**Cross-cutting note**: K1 explicitly coordinates with `colbert-reranker-web-research.md` S5 — both should land the same shared module. `archived/` is deliberately excluded from the corpus to keep retrieval signal clean; archived state is misleading by design.

---

## Dependency Graph

```
P0 (vision validation)     ──independent (model servers required)──
P1 (OpenDataLoader)        ──independent (Java 11+ required)──
P2.S1 (Goedel-CP GGUF)    ──independent──
P2.S2 (Leanstral profile) ──independent──
P2.S3 (Leanstral prune)   ──depends on S2──
P2.S4 (pipeline test)     ──depends on S1──
P2.S5 (2-tier integration)──depends on S3 + S4──
P3 (TTS)                  ──blocked on codec debugging──
P4 (doc-to-LoRA)          ──independent (low priority)──
P5 (internal KB-RAG)      ──independent (reuses colbert-reranker S3/S4 encoder); K1 coordinates with colbert-reranker S5──
```

---

## Cross-Cutting Concerns

1. **RAM budget**: Each pipeline adds model footprint competing with production stack. Current production uses ~80GB across 4 NUMA quarters. Adding vision (7B VL model, ~5GB), Lean proving (Leanstral ~20GB pruned + Goedel-CP ~5GB), or TTS models requires careful NUMA quarter allocation. Coordinate with `dynamic-stack-concurrency.md` DS-E1/DS-7-live; DS-6 scheduler work should only resume if the evidence gate triggers.

2. **NUMA quarter allocation**: Pipeline models should run on the same quarter as the orchestrator role they serve. Vision → frontdoor quarter. Lean proving → architect quarter. TTS → separate quarter or time-shared. See `routing-and-optimization-index.md` for current quarter layout.

3. **Model server ports**: Vision 8086/8087, ASR 9000, TTS 9002 (target). Avoid collisions with production stack (8080-8083). Document port assignments in `orchestrator_stack.py`.

4. **OpenDataLoader JVM**: The ODL PDF pipeline requires Java 11+. JVM startup adds ~2s cold-start latency. Consider persistent sidecar process vs. per-request launch. **Note (2026-05-29)**: the **LiteParse** born-digital fast path (P1b) is **JVM-free** — a self-contained ~13 MB manylinux wheel (PDFium + tesseract-rs compiled in, no system build) — so for born-digital PDFs it sidesteps this JVM concern entirely. ODL stays required for the structural path (heading hierarchy, table DOM, figure semantic-type).

---

## Reporting Instructions

After completing any task:
1. Check the task checkbox in this index
2. Update the relevant handoff document
3. Add entry to `progress/YYYY-MM/YYYY-MM-DD.md`
4. If RAM/NUMA allocation changes, update `routing-and-optimization-index.md` cross-cutting concern

---

## Key File Locations

| Resource | Path |
|----------|------|
| Vision pipeline | `epyc-orchestrator/src/vision/pipeline.py` (385 lines) |
| Vision analyzers | `epyc-orchestrator/src/vision/analyzers/` (6 modules) |
| PDF router | `epyc-orchestrator/src/services/pdf_router.py` |
| Document chunker | `epyc-orchestrator/src/services/document_chunker.py` |
| Stack launcher | `epyc-orchestrator/scripts/server/orchestrator_stack.py` |
| Model registry (full) | `epyc-inference-research/orchestration/model_registry.yaml` |
| TTS models | `/mnt/raid0/llm/models/Qwen3-TTS-12Hz-*.gguf` |
| Lean proving deep dives | `epyc-root/research/deep-dives/goedel-code-prover-analysis.md`, `leanstral-architecture-analysis.md` |
