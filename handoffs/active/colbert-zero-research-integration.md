# ColBERT-Zero Research Integration

**Status**: ACTIVE
**Created**: 2026-02-20
**Priority**: MEDIUM
**Paper**: [ColBERT-Zero (arXiv:2602.16609)](https://arxiv.org/abs/2602.16609) — Chaffin et al., LightOn AI, Feb 2026
**Literature Review**: `research/colbert_zero_review.md`

## Goal

Integrate findings from ColBERT-Zero research into the NextPLAID retrieval stack and MemRL routing pipeline. Two active tracks, two eliminated by investigation.

## Investigation Results (Pre-Plan)

### ELIMINATED: Query/Document Prompt Prefixes

LateOn-Code model card explicitly states **no prefix required** — raw text input only. Adding `search_query:`/`search_document:` prefixes would degrade retrieval. Confirmed at `code_search.py:150`. No action needed unless we switch to a prompt-trained model.

### CONFIRMED ACTIVE: PLAID PQ Compression

Already enabled at `nbits=4` (IVF+PQ hybrid) in `index_codebase.py:79`. Code index 336MB, docs index 31MB. No changes needed.

---

## Track 1: GTE-ModernColBERT-v1 as Docs Model Replacement

**Goal**: Replace `answerai-colbert-small-v1-onnx` (33M, 96-dim) on `:8089` with `GTE-ModernColBERT-v1` (149M, 128-dim).

**Why**:
- BEIR avg 54.67 (answerai unscored)
- LongEmbed SOTA 88.39 (critical for long markdown docs)
- 128-dim output (matches LateOn-Code; current docs model is mismatched at 96-dim)
- ModernBERT backbone (same family as LateOn-Code)

**ONNX Blocker**: RESOLVED. Official ONNX INT8 available on HuggingFace (143MB).

**Discovery**: Model uses `[Q] ` / `[D] ` prefixes (query_prefix_id=50368, document_prefix_id=50369). NextPLAID reads these from `onnx_config.json` automatically. Hidden size 768 projected to 128-dim via Dense layer (bundled in official ONNX).

**Model files**: `/mnt/raid0/llm/models/gte-moderncolbert-v1-onnx/` (downloaded + verified)

### Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1a | ONNX INT8 download | DONE (official, 143MB) |
| 1b | Embedding verification (128-dim, ~21ms/query) | DONE |
| 2 | Update model_registry.yaml | DONE (candidate documented) |
| 3 | Stop docs container, swap model, reindex | DONE (1992 chunks, 246s) |
| 4 | Qualitative A/B on 10 sample queries | DONE (5 better, 4 same, 0 worse) |
| 5 | Latency regression check (<2x) | DONE (28ms → 50ms, +78%) |

### A/B Results (10 Queries)

| Query | Old (answerai) Top Hit | New (GTE) Top Hit | Verdict |
|---|---|---|---|
| escalation policy | ARCHITECTURE.md:721 | ARCHITECTURE.md:73 | Same |
| model routing strategy | model-routing.md:1 | model-routing.md:1 + :648 | Better |
| verification gates | ch10:327 | ch10:386 + SETUP.md | Better |
| speculative decoding | kernel-development.md | **ch05-speculative-decoding.md:1** | **Much better** |
| REPL environment tools | nextplaid handoff | **ch11-repl-environment.md:1** | **Much better** |
| add model to registry | self_management.md | ARCHITECTURE.md:627 | Same |
| session compaction | ch10:428 | **context-window-management.md:1** | Better |
| architect delegation | ch17:211 | rlm-roadmap:444 | Same |
| episodic memory Q-value | model-routing.md:69 | graphiti_memrl.md:315 | Same |
| feature validation battery | **unrelated** | **feature-validation-battery.md:1** | **Much better** |

**Summary**: GTE-ModernColBERT-v1 produces more relevant docs search results, particularly for queries where the old model returned unrelated files. Latency increase is within acceptable bounds (28→50ms, <2x).

### Files to Modify

- `orchestration/model_registry.yaml` — docs retrieval model entry
- `scripts/server/orchestrator_stack.py` — docs container model path/config
- `scripts/nextplaid/index_codebase.py` — `--reindex` for docs with new model

### Validation

1. Health check passes on docs container with new model
2. `python scripts/nextplaid/index_codebase.py --docs-only --reindex` succeeds
3. 10 sample queries: "escalation policy", "model routing strategy", "verification gates", etc.
4. Relevance scores qualitatively improved or equivalent
5. Latency regression <2x
6. Fallback: stop docs container → code_search falls back to :8088

### Resume Commands

```bash
# Check docs container status
python3 scripts/server/orchestrator_stack.py status

# Reindex docs only
python scripts/nextplaid/index_codebase.py --docs-only --reindex

# Test query
python3 -c "
from src.repl_environment.code_search import code_search
results = code_search('escalation policy', index='docs')
for r in results[:5]: print(r['unit'], r['score'])
"
```

---

## Track 2: MemRL Distillation Architecture (Research)

**Goal**: Design architecture for a compressed routing classifier distilled from episodic store Q-values. Follows ColBERT-Zero insight that **supervised fine-tuning before distillation is critical**.

**Deliverable**: `docs/reference/agent-config/MEMRL_DISTILLATION_DESIGN.md`

### Current State (What Exists)

| Component | Location | Role |
|-----------|----------|------|
| Episodic store | `episodic_store.py` | SQLite+FAISS, ~500K entries, 1024-dim BGE embeddings |
| Q-scorer | `q_scorer.py` | 7-dim reward: latency, quality gap, memory tier, regret, speedup |
| FailureGraph | `failure_graph.py` | Kuzu graph DB, symptom→mitigation chains |
| HypothesisGraph | `retriever.py:1101-1119` | (action, task_type) → confidence |
| DistillationPipeline | `distillation/pipeline.py` | Trajectories → skills via teacher model |
| TwoPhaseRetriever | `retriever.py` | FAISS cosine → Q-weighted cost-aware ranking |

### What's Missing

A compressed model that converts these signals into a fast `route(task_context) → action` classifier, bypassing the full retrieval pipeline on high-confidence decisions.

### Proposed 3-Stage Pipeline (Mirrors ColBERT-Zero)

| Stage | ColBERT-Zero Analogy | Our Equivalent | Data Source |
|-------|---------------------|----------------|-------------|
| 1. Unsupervised | Contrastive on 29 datasets | Learn task embeddings from episodic store | `memories` table |
| 2. Supervised | Hard-negative contrastive | Train on (task, best_action) pairs weighted by Q-value | `q_scorer.py` rewards |
| 3. Distillation | KD from BGE-Gemma teacher | Compress HybridRouter decisions into small classifier | `retriever.py` output |

### Key Insight

The supervised stage BEFORE distillation bridges the performance gap. Our current DistillationPipeline goes directly from raw trajectories to skills (skipping supervised fine-tuning). Adding an intermediate supervised stage would improve skill quality.

### Design Doc Contents

- Training data extraction queries (SQL for episodic store)
- Feature engineering (task_type, objective keywords, context_length, has_images → feature vector)
- Model architecture (2-4 layer classifier, ~100-500 params)
- Loss function (cross-entropy + Q-value weighting + cost penalty)
- Integration point in HybridRouter (fast first-pass, fall back to retrieval if confidence < 0.6)
- Evaluation protocol (held-out trajectories, latency measurement)

### Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Architecture design document | PENDING |
| 2 | Training data extraction script | FUTURE |
| 3 | Prototype classifier | FUTURE |
| 4 | A/B test vs HybridRouter | FUTURE |

---

## Documentation Updates

| File | Update |
|------|--------|
| `CHANGELOG.md` | ColBERT-Zero findings entry |
| `orchestration/BLOCKED_TASKS.md` | New entries for both tracks |
| `docs/reference/models/QUIRKS.md` | Retrieval model quirks (LateOn-Code prefixes, dim mismatch, ONNX gap) |
| `docs/reference/benchmarks/RESULTS.md` | Retrieval section with current + candidate benchmarks |
| `research/colbert_zero_review.md` | Literature review (CREATED) |

---

## Execution Order

1. **Handoff + literature review** (this document + `research/colbert_zero_review.md`) — DONE
2. **Documentation updates** (CHANGELOG, BLOCKED_TASKS, QUIRKS, RESULTS)
3. **Track 1** (GTE-ModernColBERT) — ONNX conversion first, then A/B test
4. **Track 2** (MemRL distillation design) — architecture doc, no code yet

## Completion Checklist

- [x] Literature review written (`research/colbert_zero_review.md`)
- [x] Handoff created
- [x] CHANGELOG updated
- [x] BLOCKED_TASKS updated
- [x] QUIRKS.md updated
- [x] RESULTS.md retrieval section added
- [x] ONNX INT8 verified (official export, 143MB)
- [x] Docs container swapped to GTE-ModernColBERT-v1
- [x] 10-query qualitative comparison (5 better, 4 same, 0 worse)
- [x] MemRL distillation design doc written (`docs/reference/agent-config/MEMRL_DISTILLATION_DESIGN.md`)
- [ ] `make gates` passes
- [ ] model_registry.yaml swap finalized (currently old model in launch_command, new in candidate comment)
