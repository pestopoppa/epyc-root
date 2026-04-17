# Pipeline Integration — Coordination Index

**Status**: active
**Created**: 2026-04-04
**Purpose**: Entry point for agents working on new capability pipelines being added to the EPYC stack. Each pipeline adds a new modality or data processing capability.

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
| [opendataloader-pipeline-integration.md](opendataloader-pipeline-integration.md) | PDF extraction | active (magika evaluated + skipped 2026-04-17) | P2 (medium) | 2026-04-17 |
| [lean-proving-pipeline.md](lean-proving-pipeline.md) | Lean 4 theorem proving | stub | unset | 2026-03-28 |
| [08-doc-to-lora-prototype.md](08-doc-to-lora-prototype.md) | Document → LoRA fine-tune | active (reference) | P3 (low) | 2026-03-18 |

---

## Outstanding Tasks (Priority Order)

### P0 — Multimodal Vision (validation)

- [ ] Live validation with model servers (ports 8086/8087) — `--no-display-prompt` bug FIXED 2026-04-08 (removed from `vl_describe.py`). Re-test needed with VL servers.
- [ ] Register vision tools in orchestrator tool surface
- [x] Test OpenAI-compat multimodal API passthrough — ✅ FIXED 2026-04-08. `content: str | list` + `_extract_text()` helper. Re-test with actual multipart content needed.

### P1 — OpenDataLoader PDF

- [ ] **Phase 1**: Replace pdftotext with ODL local; swap extraction call; handle JVM lifecycle; update tests
- [ ] **Phase 2**: Parse ODL JSON for figures/tables; enrich VL model prompts; improve chunker with heading hierarchy
- [ ] **Phase 3**: Deploy hybrid sidecar; benchmark 3-way routing; run comparison suite (200 PDFs)
- [ ] Clone opendataloader-bench; implement NID/TEDS/MHS scoring

### P2 — Lean 4 Proving Pipeline

- [ ] S1: Convert Goedel-CP-8B to GGUF, quantize Q4_K_M/Q8_0, validate
- [ ] S2: Profile Leanstral expert activation on Lean 4 workloads (target 95% coverage)
- [ ] S3: REAP-prune Leanstral to ~20GB (depends on S2)
- [ ] S4: End-to-end pipeline test on FormalQualBench subset (depends on S1)
- [ ] S5: Two-tier integration: Leanstral planning → Goedel-CP execution (depends on S3+S4)

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
```

---

## Cross-Cutting Concerns

1. **RAM budget**: Each pipeline adds model footprint competing with production stack. Current production uses ~80GB across 4 NUMA quarters. Adding vision (7B VL model, ~5GB), Lean proving (Leanstral ~20GB pruned + Goedel-CP ~5GB), or TTS models requires careful NUMA quarter allocation. Coordinate with `dynamic-stack-concurrency.md` DS-6.

2. **NUMA quarter allocation**: Pipeline models should run on the same quarter as the orchestrator role they serve. Vision → frontdoor quarter. Lean proving → architect quarter. TTS → separate quarter or time-shared. See `routing-and-optimization-index.md` for current quarter layout.

3. **Model server ports**: Vision 8086/8087, ASR 9000, TTS 9002 (target). Avoid collisions with production stack (8080-8083). Document port assignments in `orchestrator_stack.py`.

4. **OpenDataLoader JVM**: The ODL PDF pipeline requires Java 11+. JVM startup adds ~2s cold-start latency. Consider persistent sidecar process vs. per-request launch.

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
