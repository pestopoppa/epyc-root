# LightOn DenseOn + LateOn: Retrieval Upgrade Deep Dive

**Status**: deep-dive (proposal)
**Category**: `search_retrieval`
**Created**: 2026-04-22
**Intakes**: [intake-428](../intake_index.yaml) (blog), [intake-430](../intake_index.yaml) (LateOn), [intake-431](../intake_index.yaml) (DenseOn); historical context [intake-174](../intake_index.yaml) (Reason-ModernColBERT, eliminated)
**Related handoffs**:
- [`handoffs/active/colbert-reranker-web-research.md`](/workspace/handoffs/active/colbert-reranker-web-research.md) (primary candidate for amendment)
- [`handoffs/active/searxng-search-backend.md`](/workspace/handoffs/active/searxng-search-backend.md) (upstream composer)
- [`handoffs/completed/colbert-zero-research-integration.md`](/workspace/handoffs/completed/colbert-zero-research-integration.md) (prior upgrade cycle)
- [`wiki/search-retrieval.md`](/workspace/wiki/search-retrieval.md) (synthesis page, must be updated after any adoption decision)

## 1. Abstract

LightOn's 2026-04 release ships two Apache-2.0 retrieval models trained on a fully-open data pipeline: **LateOn** (149M, multi-vector ColBERT, BEIR 57.22 / decontaminated 60.36) and **DenseOn** (149M, single-vector dense, BEIR 56.20 / decontaminated 57.71). Both sit on the same ModernBERT-base backbone as EPYC's deployed GTE-ModernColBERT-v1 (BEIR 54.67) and the previously surveyed ColBERT-Zero (55.39). LateOn is the first sub-150M ColBERT to exceed BEIR 57, and DenseOn is the first sub-150M dense model past 56. The release also introduces a **decontamination evaluation protocol** (exact-hash + 13-gram containment) that cleanly distinguishes genuine generalization from benchmark leakage, plus a reusable 665M-pair curated pre-training corpus. For EPYC this is a near-zero-risk, same-architecture drop-in replacement for the reranker stage of the web_research pipeline and a credible challenger for the BGE-small probe-first pool. The binding constraint is ONNX INT8 export, which is not yet published by LightOn; a short benchmark+export workstream is proposed.

## 2. What's New

### 2.1 Architectural Lineage

```
ModernBERT-base (AnswerDotAI, 149M, 8192-ctx)
  ├─ GTE-ModernColBERT-v1        (LightOn 2025-09)  BEIR 54.67     deployed :8089
  ├─ Reason-ModernColBERT        (LightOn 2025-10)  BRIGHT 22.62   eliminated (CC-BY-NC-4.0)
  ├─ ColBERT-Zero                (LightOn 2026-02)  BEIR 55.39     candidate, Apache-2.0
  ├─ LateOn                      (LightOn 2026-04)  BEIR 57.22     <-- NEW, primary candidate
  └─ DenseOn                     (LightOn 2026-04)  BEIR 56.20     <-- NEW, secondary (dense)
```

Both new models share the **ModernBERT-base 149M** backbone (identical parameter count and context window to existing artifacts). LateOn emits **128-dim per-token** multi-vector representations with MaxSim scoring — byte-compatible with GTE-ModernColBERT-v1 and the on-disk `model_int8.onnx` format in the orchestrator venv. DenseOn emits **768-dim CLS-pooled** single vectors with cosine similarity, and requires asymmetric `query:` / `document:` prompt prefixes (handled by `SentenceTransformer.encode(..., prompt_name=...)`).

### 2.2 Headline Numbers

| Model | Params | Vector type | Dim | BEIR | Decon. BEIR | ΔDecon | License |
|-------|-------:|-------------|----:|-----:|------------:|------:|---------|
| GTE-ModernColBERT-v1 | 149M | multi | 128 | 54.67 | n/a | n/a | Apache-2.0 |
| ColBERT-Zero | 149M | multi | 128 | 55.39 | 59.33 | +3.94 | Apache-2.0 |
| **LateOn** | **149M** | **multi** | **128** | **57.22** | **60.36** | **+3.14** | **Apache-2.0** |
| GTE-ModernBERT (dense) | 149M | dense | 768 | 55.19 | n/a | n/a | Apache-2.0 |
| **DenseOn** | **149M** | **dense** | **768** | **56.20** | **57.71** | **+1.51** | **Apache-2.0** |
| Reason-ModernColBERT | 149M | multi | 128 | ~51 / 22.62 BRIGHT | n/a | n/a | CC-BY-NC-4.0 (eliminated) |
| jina-ColBERT-v2 | ~110M | multi | 128/96/64 | ~52 | n/a | n/a | CC-BY-NC-4.0 |
| Snowflake Arctic Embed L v2 | 568M | dense | 1024 | 55.22 | n/a | n/a | Apache-2.0 |
| Qwen3-Embedding-0.6B | 600M | dense | 1024 | 55.52 | n/a | n/a | Apache-2.0 |

Key deltas for EPYC:
- **LateOn vs deployed GTE-ModernColBERT-v1**: **+2.55 pp BEIR** (54.67 → 57.22).
- **LateOn vs previously-proposed ColBERT-Zero**: **+1.83 pp BEIR**, **+1.03 pp decontaminated**.
- **DenseOn vs 4× larger dense models**: outperforms Snowflake Arctic Embed L (568M) and Qwen3-Embedding-0.6B (600M) while using ≤150M params.
- **Multi-vector decontamination delta is 2.1× the dense delta** (+3.14 vs +1.51), corroborating LightOn's "ColBERT generalizes better under leakage control" claim.

### 2.3 Training & Evaluation Methodology

**Two-stage contrastive training.**

Stage 1 — Pre-training contrastive objective:
- **Raw pool**: 1.4B query/document pairs, 34 sources.
- **Filtering pipeline** (30+ composable filters, three semantic passes):
  1. *Structural quality* — HTML/boilerplate strip, non-printable character removal, FastText language ID + unicode-range consistency, unigram probability + repeated-token + special-character statistical heuristics.
  2. *Semantic relevance* — cross-encoder scoring via `mxbai-rerank-large-v2`; standard sources kept at similarity ≥3.0, FineWeb-Edu kept at top ~35% percentile.
  3. *Deduplication* — MD5 hash over normalised (query, document) pairs.
- **Retention**: 665M pairs (48% of raw pool).
- **Non-destructive design**: every filter signal is written back as a metadata column rather than dropping rows. This enables downstream mixture re-curation without re-running expensive scoring passes — directly reusable if EPYC ever wants to re-weight by domain (e.g., up-weight code-retrieval pairs).
- **Multinomial source sampling** during pre-training ensures large sources (Common Crawl dumps, MS MARCO) don't dominate gradients, unlocking higher learning rates than uniform sampling.

Stage 2 — Supervised fine-tuning with NV-Retriever hard negatives:
- **Seed pool**: 1.88M contrastive pairs from 7 QA/IR sources (FiQA, Natural Questions, HotpotQA, MS MARCO, FEVER, SQuAD v2, TriviaQA).
- **NV-Retriever mining** ([arXiv:2407.15831](https://arxiv.org/abs/2407.15831)):
  1. For each (q, pos), retrieve top-2048 nearest passages via GTE-ModernBERT.
  2. Compute `threshold = 0.99 × similarity(q, pos)`.
  3. Keep negatives with `similarity(q, d) < threshold` (filters false negatives too similar to pos).
  4. Drop the example entirely if <50 eligible negatives remain — this is a **quality gate on query-positive pairing** (a weak positive produces too many near-positives).
  5. Sample 7 hard negatives per example, combine with in-batch negatives.
- **Retention**: 1.69M examples (89.9% after quality gate).
- **Released corpus**: `lightonai/embeddings-fine-tuning` ships the full 2048 mined candidates per example, not just the 7 used — enabling downstream re-mining at different thresholds.

**DenseOn-specific training choices** (the "largest gain" ablation):
- CLS pooling over mean pooling.
- Asymmetric `query:` / `document:` prompt prefixes (SentenceTransformers `prompt_name` mechanism).
- Cosine similarity as the scoring function.
- Combined effect: "one of our largest gains" per the blog — consistent with the broader literature on asymmetric prompting (E5, BGE-m3) but notable that the effect is so large at this parameter class.

**Decontamination protocol** (novel evaluation contribution, reusable):

The methodology is explicitly two-pass, designed to catch both verbatim copies and near-duplicates:

Pass 1 — Exact-hash matching:
```
for (query, document) in BEIR_split:
    normalised = lowercase(NFKD_normalize(concat(query, document)))
    h = xxhash64(normalised)
    if h in mgte_training_hashes:
        mark_contaminated(sample)
```

Pass 2 — 13-gram containment (GPT-3 style, arXiv:2005.14165 protocol):
```
for sample in remaining_BEIR:
    ngrams_beir = extract_13grams(sample.text)
    ngrams_train = extract_13grams_from(mgte_training_data)
    containment = |ngrams_beir ∩ ngrams_train| / |ngrams_beir|
    if containment >= 0.5:
        mark_near_duplicate(sample)
```

Empirical removal rates per BEIR subset:
- ArguAna: 1.5% (clean)
- ... typical subsets: 10–40%
- NQ: 88.6% (heavily leaked in mGTE's original training mix)

BEIR 13.0 nominally has 14 subsets; LightOn's decontaminated leaderboard drops 2 (DBPedia, NQ) where the remaining signal is too small to be statistically meaningful, reporting a **12-subset decontaminated BEIR**. This asymmetry (raw=14, decon=12) must be remembered when comparing numbers.

Key empirical finding: ColBERT models' average NDCG@10 **improves by +3.30** under decontamination; dense models improve by +1.44. The interpretation — token-level late interaction is harder to overfit than single-vector compression — is consistent with prior work on interpretability of multi-vector retrievers, but this is the first controlled same-backbone same-data demonstration we have seen.

**Released artifacts** (all Apache-2.0):
- `lightonai/LateOn` — supervised multi-vector checkpoint (the primary model)
- `lightonai/DenseOn` — supervised dense checkpoint
- `lightonai/LateOn-unsupervised` — pre-training-only checkpoint
- `lightonai/DenseOn-unsupervised` — pre-training-only checkpoint
- `lightonai/embeddings-pre-training` — raw 1.4B pairs with filter metadata
- `lightonai/embeddings-pre-training-curated` — 665M best-mixture pairs
- `lightonai/embeddings-fine-tuning` — 1.88M pairs × 2048 mined candidates

This corpus + code release is materially more open than any prior retrieval SOTA release — notably more reproducible than ColBERT-Zero (which shipped weights and a training description but not the exact data mixture).

## 3. Existing EPYC Position

### 3.1 Currently Deployed

| Slot | Model | Port / Path | Role | Status |
|------|-------|-------------|------|--------|
| Code search | LateOn-Code (NextPLAID) | :8088 | Multi-vector codebase retrieval | deployed, 336MB index |
| Docs search | **GTE-ModernColBERT-v1** | :8089 | Multi-vector docs retrieval | deployed, 31MB index, 128-dim |
| Routing memory | BGE-large 1024-dim | FAISS in-proc | MemRL episodic store | deployed, 0.5–3ms latency |
| Probe-first pool | **BGE-small 384-dim** | in-proc | First-pass dense probe over snippets | deployed |
| Web reranker | none / flag-gated | — | `web_research_rerank` OFF pending AR-3 | S1–S4 done, S5 gated |

On-disk ONNX artifact used by the (gated) reranker: `/mnt/raid0/llm/models/gte-moderncolbert-v1-onnx/model_int8.onnx` (144MB INT8). ONNX Runtime 1.24.4 is installed in the orchestrator cp314 venv. PyLate is **not** installable in that venv because `fast-plaid` and `voyager` lack cp314 wheels.

### 3.2 What the ColBERT-Reranker Handoff Currently Plans

`handoffs/active/colbert-reranker-web-research.md` selected **ColBERT-Zero** as primary (strongest general-purpose BEIR at the time, Apache-2.0) with **GTE-ModernColBERT-v1** de-facto used since it was already on disk and achieves 54.67 vs ColBERT-Zero 55.39 (<1 pp gap). Mxbai-edge-colbert 17M remained the license-clean fallback. S4 measured **180ms median** for 1 query + 10 snippets through the full 150M-param model on EPYC; MaxSim <1ms; perfect test-set separation (relevant 0.93–0.96 vs irrelevant 0.91–0.92). S5 (implementation) is **gated on AR-3 Package D** confirming >20% irrelevant page rate.

### 3.3 BGE-small Probe-First Pool Status

BGE-small (384-dim dense, ~33M) is used in the orchestrator for cheap first-pass snippet probing before multi-vector reranking. Current pool is small and latency-bound: retention decisions are implicit (no explicit eviction metric). DenseOn at 149M / 768-dim is ~4× larger than BGE-small but produces a materially stronger BEIR result (56.20 vs ~53 for BGE-small on comparable subsets). DenseOn is therefore only interesting for the probe slot if CPU encoding time per snippet stays within the probe-stage budget (target <30ms per batch of 10).

## 4. Amend / Expand / Confirm

### 4.1 Confirm

These LightOn findings reinforce standing EPYC decisions:

1. **Multi-vector > dense for reasoning retrieval.** LateOn's +3.14 decontaminated-BEIR gain vs DenseOn's +1.51 (both trained on identical data with identical filtering) is the cleanest head-to-head we have seen. This validates the EPYC choice to route reranking through ColBERT and route only the cheap probe stage through dense vectors. Prior indirect evidence (XTR vs ColBERT in intake-405/407) already pointed this way; LateOn/DenseOn makes it a same-lab, same-data, same-backbone controlled comparison.
2. **ModernBERT backbone choice is durable.** Every new LightOn retrieval release (and AnswerAI's own mxbai-edge-colbert) targets ModernBERT-base. Our `[Q]` / `[D]` ONNX tokenizer config and 128-dim output plumbing will stay reusable across generations.
3. **≤150M parameters is the sweet spot.** LateOn at 149M beats jina-ColBERT-v2 (~110M, +6.5% over ColBERTv2) and DenseOn at 149M beats Snowflake Arctic L at 568M and Qwen3-Embedding at 600M. The 180ms reranking budget in S4 is a function of this parameter class; any temptation to scale to 300M+ should be re-checked against the ROI equation (180ms reranking vs 45s synthesis saved per irrelevant page).
4. **Apache-2.0 open-data retrieval is now achievable at SOTA.** This extinguishes any lingering temptation to re-evaluate CC-BY-NC-4.0 models (Reason-ModernColBERT, jina-ColBERT-v2). No commercial-use exception is required.
5. **180ms ONNX encoding budget on EPYC is architecture-bound, not model-specific.** LateOn has the same layer count and hidden size as GTE-ModernColBERT-v1, so S4's 180ms number should transfer within ±10% once ONNX INT8 weights exist.

### 4.2 Amend

These decisions should be revised:

1. **Replace ColBERT-Zero as the primary reranker candidate with LateOn** in `colbert-reranker-web-research.md`.
   - Rationale: same license (Apache-2.0), same backbone, same parameter count, same output dimension, **+1.83 pp BEIR** over ColBERT-Zero and **+2.55 pp** over the currently-used GTE-ModernColBERT-v1. Zero integration cost once ONNX INT8 weights are available — same tokenizer config, same MaxSim code path, same ONNX session.
   - Action item: add an S3b sub-task to the handoff to download or export LateOn ONNX, then re-run S4 as a 1-hour latency+ranking A/B benchmark.
2. **Adopt LightOn's decontamination protocol as the EPYC-internal eval protocol for retrieval models.**
   - Rationale: our current web_research sentinel suite (50 questions embedded in AR-3 Package D) is small but could be decontaminated against the LightOn-released training data hashes before any A/B result is declared a win. This avoids the cheaper-and-dangerous failure mode where "new model wins" is actually "new model saw the test set."
   - Action item: add a `scripts/benchmark/decontaminate_against_embeddings_training.py` utility that xxhash64-normalises our sentinel queries and emits a contamination report against `embeddings-pre-training` and `embeddings-fine-tuning`.
3. **Reframe the "BEIR 54.67 is fine" position in the handoff.** S3 currently argues that the <1 pp gap between GTE-ModernColBERT-v1 and ColBERT-Zero justifies the on-disk default. LateOn moves the delta to **+2.55 pp** — large enough that, absent a latency regression, the default should flip once ONNX INT8 is validated.
4. **Update `wiki/search-retrieval.md` once adoption is decided.** Add LateOn/DenseOn source references, update the ColBERT family table, retire the ColBERT-Zero "primary" labelling, and add a "Decontaminated BEIR" column.
5. **Add asymmetric-prompt handling to the dense-probe code path** if DenseOn is adopted. BGE-small uses no prompts; DenseOn requires `query:` / `document:` prefixes. Any swap is NOT a drop-in — the tokenizer config must be updated or retrieval quality silently degrades.

### 4.3 Expand

New questions and workstreams this release opens:

1. **Probe-first pool migration to DenseOn.** Is the 149M / 768-dim / prompted DenseOn viable in the BGE-small (33M / 384-dim) slot? Latency budget: probe-stage target <30ms for a batch of 10 snippets. DenseOn at 4.5× BGE-small params will likely need ONNX INT8 + batched encoding to fit. Worth a scoped 2-hour benchmark before committing.
2. **Local fine-tuning for code search and REPL-specific queries.** LightOn released the full 665M-pair curated pre-training mixture and the 1.69M-pair fine-tuning dataset under Apache-2.0. This unlocks a previously-blocked experiment: fine-tune a LateOn variant on repl_executor traces + our sentinel web_research queries, producing an EPYC-domain-specialised reranker. NV-Retriever-style hard-negative mining against our orchestrator logs is straightforward with `fast-plaid` outside the cp314 venv (e.g., in `/workspace/venvs/training/`).
3. **Decontaminated BEIR as a cross-cutting retrieval benchmark.** The LightOn-released hashes and 13-gram sets make reproducing the decontamination protocol a script-sized project. Can we run LateOn, GTE-ModernColBERT-v1, BGE-small, and (future) local fine-tune all through a single EPYC benchmark harness and publish internal deltas?
4. **LateOn-unsupervised as a seed for MemRL distillation.** The MemRL distillation classifier (Track 2 in the completed `colbert-zero-research-integration.md`) was inspired by ColBERT-Zero's 3-stage training. LateOn-unsupervised may be a cleaner unsupervised seed than ColBERT-Zero's own intermediate checkpoint, particularly because the filtering pipeline is documented and reproducible.
5. **DenseOn as fallback reranker** when ONNX concurrency limits are hit. If the orchestrator ever needs to run reranking in parallel with an already-loaded multi-vector model (e.g., LateOn-Code on :8088), a dense 768-dim DenseOn pass over 10 snippets is cheaper per-snippet than MaxSim over 128-dim × 300 tokens. Not a near-term priority but worth noting.
6. **Multilingual requirements?** LateOn/DenseOn are English-first. If EPYC's web_research pipeline ever needs non-English search (SearXNG supports multilingual), the SauerkrautLM-Multi-Reason fork or jina-ColBERT-v2 pattern may still be relevant. Currently out of scope.
7. **PyLate-free ONNX export.** LightOn ships PyTorch weights. The orchestrator cp314 venv cannot run PyLate. We need an export path: either use `optimum` in a separate Python 3.12 venv, or track any community ONNX upload on HF Hub (`onnx-community/LateOn-int8` pattern). This is a 1-hour task at most but is the single gating item.

## 5. Adoption Feasibility on EPYC

### 5.1 ONNX INT8 Availability

**LightOn does not publish ONNX or INT8 variants.** The model cards list `safetensors` only. The blog makes no mention of ONNX. This is the single binding constraint.

Mitigation paths (ranked by effort):
1. **Check HF Hub for community ONNX exports** — search for `onnx-community/LateOn*` or `lightonai/LateOn-onnx`. If present, validate tokenizer parity with GTE-ModernColBERT-v1 (both use `[Q]` / `[D]` token IDs via `onnx_config.json`; confirm LateOn ships the same config).
2. **Export via `optimum.exporters.onnx` in a separate venv.**  Requires Python 3.12, `transformers`, `optimum[onnxruntime]`. Command sketch: `optimum-cli export onnx --model lightonai/LateOn --task feature-extraction --framework pt --dtype int8 ./lateon-onnx-int8`. Output size target: ~145MB INT8 (GTE-ModernColBERT-v1 INT8 is 144MB; LateOn has the same architecture). Validate with a reference fixture (5 query/doc pairs) against PyLate PyTorch outputs — tolerance <1e-3 on embeddings.
3. **Fallback: use PyLate in a separate Python 3.12 venv and expose via localhost HTTP**, then have the orchestrator call it. Adds a second process and ~5ms HTTP overhead but unblocks immediate evaluation.

### 5.2 CPU Latency Budget

Expected numbers on EPYC (192-thread, 1.1TB RAM) by extrapolation from S4:
- **Encoding 1 query (32 tok) + 10 snippets (300 tok each)** via INT8 ONNX: **~180ms ±20ms** (same model architecture as S4).
- **MaxSim 1×300 × 128-dim over 10 docs**: **<1ms** (numpy matmul on EPYC).
- **Total per reranking call**: ~180–200ms.
- **Budget vs synthesis cost**: 180ms << 45s per irrelevant page saved ⇒ break-even at <1% irrelevant rate, actual target >20%. ROI unchanged from S4.

### 5.3 Memory Footprint

- INT8 weights: **~145MB** (same class as GTE-ModernColBERT-v1).
- Session overhead (ORT arena): **~50–80MB** once warm.
- No mlock required (single reranker call is fast; session stays in page cache).
- Fits comfortably in the orchestrator process footprint even alongside BGE-small + MemRL embeddings.

### 5.4 Orchestrator Integration Hooks

All hooks exist today — this would be a literal one-line model-path change if ONNX is available:

| Hook | Current | Post-LateOn |
|------|---------|-------------|
| `src/tools/web/colbert_reranker.py` (planned in S5) | loads `gte-moderncolbert-v1-onnx/model_int8.onnx` | loads `lateon-onnx-int8/model_int8.onnx` |
| `src/features.py` FeatureSpec | `web_research_rerank` | unchanged |
| Tokenizer config | `onnx_config.json` with `[Q]`/`[D]` token IDs | verify parity; may require regenerating `onnx_config.json` |
| Telemetry | `pages_irrelevant`, `irrelevant_rate` via `repl_executor.py` | unchanged |
| Model path anchor | `/mnt/raid0/llm/models/gte-moderncolbert-v1-onnx/` | `/mnt/raid0/llm/models/lateon-onnx-int8/` (new directory) |
| Research registry | `epyc-inference-research/orchestration/model_registry.yaml` | add LateOn entry with BEIR 57.22 / decontaminated 60.36 |

No changes required to `orchestrator_stack.py`, no new Docker container, no new port. The orchestrator registry (lean) stays unchanged until web_research_rerank is default-on.

### 5.5 Tokenizer & Prefix Convention Check

LateOn's model card uses `is_query=True/False` through PyLate rather than explicit `[Q]` / `[D]` tokens. Under the hood PyLate's `ColBERT` class prepends special tokens during tokenization. We need to verify at export time that:

1. The tokenizer config (`tokenizer.json`) preserves the `[Q]` and `[D]` special token IDs.
2. The `onnx_config.json` we ship alongside the ONNX file flags these IDs so the orchestrator's reranker code (which handles prefix injection outside the ONNX graph) stays compatible with the current GTE-ModernColBERT-v1 plumbing.
3. Sequence-length limits match: LateOn documents the canonical `query_length=32`, `document_length=300` — these are the PyLate-side truncation limits, not the ModernBERT-base model ceiling (8192). For EPYC's web-snippet reranking these limits are already comfortable (DDG/SearXNG snippets are typically 150–250 chars ≈ 40–80 tokens).

If the special-token IDs differ from GTE-ModernColBERT-v1, the `onnx_config.json` consumed by the orchestrator reranker must be regenerated from LateOn's tokenizer rather than copy-pasted from the current deployment. This is a 5-minute fix but will silently degrade retrieval if missed. A regression test should assert that the first and last tokens of every encoded query match the declared query-prefix ID.

### 5.6 Dependency & Version Surface

- **No new pip packages** in the orchestrator venv. ONNX Runtime 1.24.4 (already installed) handles INT8 inference.
- **Separate export venv** (Python 3.12, `optimum[onnxruntime]`, `torch>=2.3`, `transformers>=4.42`): one-off, ~1.5GB install, isolated under `/workspace/venvs/export312/` so it doesn't pollute the runtime venv.
- **PyLate parity test** (optional but recommended): same export venv can host PyLate for generating reference embeddings.

No changes to llama.cpp, no orchestrator server restart required beyond the normal reranker lazy-load.

## 6. Proposed Experiment Plan

### 6.1 E1 — ONNX Export & Fixture Validation (1h)

**Goal**: produce `lateon-onnx-int8/model_int8.onnx` with parity to the PyLate reference.

Steps:
1. In a Python 3.12 venv (`/workspace/venvs/export312/`): `pip install -U optimum[onnxruntime] transformers torch`.
2. Export: `optimum-cli export onnx --model lightonai/LateOn --task feature-extraction --dtype int8 /mnt/raid0/llm/models/lateon-onnx-int8/`.
3. Validate against PyLate reference: encode 5 fixture query/doc pairs with PyLate (PyTorch), then with the new ONNX INT8. Assert L2 distance <1e-2 per-token across all layers. Script path: `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/validate_lateon_onnx_parity.py`.
4. Confirm `onnx_config.json` carries `[Q]` / `[D]` token IDs (LateOn uses `is_query=True/False` in PyLate; confirm the exporter preserves the special tokens).

**Pass/fail**: parity <1e-2 L2. If fail, escalate to LightOn GitHub discussion or fall back to PyLate-in-side-venv (path 3 above).

### 6.2 E2 — EPYC Latency Benchmark (30min)

**Goal**: confirm ≤200ms per reranking call on EPYC with ONNX INT8.

Steps:
1. Reuse S4 benchmark script (`scripts/benchmark/bench_colbert_rerank.py`), swap model path.
2. Run 100 trials of (1 query × 10 snippets) at 192 threads, 48 threads, 16 threads.
3. Report median, p95, p99 per thread count.
4. Compare head-to-head with GTE-ModernColBERT-v1 on the same inputs.

**Pass/fail**: median ≤200ms at 48 threads (typical concurrent load); p99 ≤500ms.

### 6.3 E3 — Ranking-Quality A/B on Sentinel Suite (1h inference)

**Goal**: confirm +2.55 pp BEIR translates into observable improvement on EPYC's web_research sentinel queries.

Steps:
1. Use AR-3 Package D's 50-question web_research sentinel suite once it has run (gated on AR-3).
2. For each question: run SearXNG search → get top-10 snippets → rerank with {GTE-ModernColBERT-v1, LateOn} → take top-3.
3. Compute overlap between rerankers' top-3, and recompute `irrelevant_rate` for each ranking.
4. Compute NDCG@3 using `_is_irrelevant_synthesis()` heuristic as relevance label.

**Pass/fail**: LateOn irrelevant_rate < GTE baseline by ≥1 pp across the 50 sentinel queries; top-3 overlap <0.8 (otherwise no meaningful difference).

### 6.4 E4 — Decontamination Sanity Check (1h)

**Goal**: confirm none of the sentinel queries are in the `embeddings-pre-training` or `embeddings-fine-tuning` hashes.

Steps:
1. Stream hash columns from `lightonai/embeddings-*` datasets (HF streaming mode, no full download).
2. xxhash64 each sentinel query+expected-snippet pair after NFKD+lowercase normalisation.
3. Report any matches.

**Pass/fail**: zero exact matches; <5% 13-gram containment per sentinel. If fail, replace matched questions.

### 6.5 E5 — DenseOn Probe-Pool Feasibility (2h)

**Goal**: test whether DenseOn can replace BGE-small in the probe-first pool.

Steps:
1. Export DenseOn to ONNX INT8 (same procedure as E1).
2. Benchmark batch-of-10 snippet encoding with `query:` / `document:` prompts at 48 threads.
3. Compare to BGE-small baseline on a 100-query subset of the sentinel suite (NDCG@10 with heuristic labels).

**Pass/fail**: batch-10 encoding ≤60ms AND NDCG@10 improves by ≥3 pp. Otherwise park DenseOn as future work.

### 6.6 Decision Gates

```
E1 pass ──► E2 pass ──► E3 pass + E4 clean ──► AMEND handoff: LateOn primary
            │                                       │
            │                                       └─► Update wiki/search-retrieval.md
            │
            └── E2 fail ──► diagnose ORT INT8 regression, escalate
E5 pass ──► handoff stub: "DenseOn probe-first migration"
E5 fail ──► keep BGE-small, revisit if LateOn wins E3 by large margin
```

### 6.7 Ordering Within AR-3 Gate

The web_research_rerank S5 item is itself gated on AR-3 Package D producing >20% irrelevant-page rate. The experiment plan here is orthogonal: E1/E2/E4 can run **before AR-3 completes** because they do not depend on sentinel-suite data. E3 explicitly requires AR-3 Package D output. Recommended ordering:

1. Run E1 (export) and E2 (latency) immediately — these unblock an S3b sub-task in the reranker handoff regardless of the AR-3 go/no-go.
2. Run E4 (decontamination check) before E3, once sentinel suite is frozen — avoids wasting an A/B run on contaminated questions.
3. Run E3 after AR-3 Package D completes. Same infrastructure, same sentinel suite, two model configurations.
4. Run E5 only if E3 shows meaningful LateOn gains — no point optimising the probe-pool if the reranker itself is marginal.

This ordering lets us make the primary AMEND decision (LateOn replaces ColBERT-Zero as documented primary) the moment E1/E2 pass, even before web_research_rerank is default-on.

## 7. Risks & Open Questions

### 7.1 Tier 2b Contradicting-Evidence Notes

1. **LightOn commercial bias.** LightOn is a commercial vendor of retrieval services; the blog comparison table is authored by them, and the decontamination protocol is of their design. Independent reproduction on BEIR 13.0 has not yet appeared. **Mitigation**: re-run BEIR subset (minimum: NFCorpus, FiQA, SciFact) locally on the released checkpoints and publish internal numbers.
2. **Decontamination methodology rigor.** The 13-gram threshold of 0.5 containment is inherited from GPT-3 but has known false-positive and false-negative modes (short queries can exceed 0.5 on stylistic overlap; long documents can hide copy-paste in low-containment fractions). **Mitigation**: cross-check decontamination results against at least one independent method, e.g. MinHash LSH.
3. **MaxSim latency at large snippet counts.** EPYC S4 measured 180ms for 10 snippets. What about 50, 100? MaxSim itself is `O(q_tokens × d_tokens × docs)` — a 5× snippet count increase is a 5× MaxSim cost (still <5ms) BUT a 5× encoding cost (~900ms). If we ever scale the reranker to a larger candidate pool, the linear encoding growth becomes the dominant term. **Mitigation**: pre-encode snippets asynchronously during SearXNG page fetch; cache by URL.
4. **BEIR 57.22 is in-domain for LightOn's filtering pipeline.** The fine-tuning mix (FiQA, NQ, HotpotQA, MS MARCO, FEVER, SQuAD v2, TriviaQA) overlaps substantially with BEIR. Even after decontamination passes, distribution-shift risk to our web-research domain (open-web snippets, often non-English noise, often paywalled previews) is non-zero. **Mitigation**: E3 sentinel A/B is the authoritative EPYC-domain test.
5. **DenseOn asymmetric prompts may silently break tokenization.** `query:` and `document:` prefixes consume ~2 tokens each. If input truncation collides with prefix insertion, the last tokens of the document can be dropped. **Mitigation**: explicitly increase max_seq_length by 8 tokens when using prompts.
6. **PyLate is not on our critical path but is the canonical reference.** Any divergence between ONNX-exported LateOn and PyLate inference is our bug to find, not LightOn's. **Mitigation**: E1 fixture validation.
7. **Concurrency semantics of ORT sessions.** S4 measured single-call latency. web_research_rerank runs per request and we have concurrent REPL sessions. If two sessions enter the rerank path simultaneously, ORT's intra-op and inter-op thread pools may contend. **Mitigation**: verify `ort.SessionOptions(intra_op_num_threads=16, inter_op_num_threads=1)` and size-test at 4 concurrent calls.
8. **DenseOn vs BGE-small is not an apples-to-apples comparison.** DenseOn uses ModernBERT-base (8192 context); BGE-small uses BERT-base (512 context). If the probe pool ever operates on longer snippets (e.g., concatenated page prefix), BGE-small silently truncates whereas DenseOn processes fully. Conversely, BGE-small is faster per-token and may win on the actual probe workload despite losing on BEIR.

### 7.2 Open Questions (unresolved, need data)

- Will LateOn's +2.55 pp BEIR translate to ≥1 pp irrelevant_rate reduction on EPYC's web-research sentinels?
- Is ONNX INT8 quantization loss-free on LateOn's embeddings? GTE-ModernColBERT-v1 tolerated INT8 well; no reason to expect otherwise, but no published LateOn INT8 evaluation exists.
- Does DenseOn's asymmetric-prompt convention affect MemRL distillation quality if we ever seed from DenseOn-unsupervised?
- What is the right threshold to decide "LateOn wins" vs "delta is within noise"? Suggested rule: E3 must show ≥1 pp absolute irrelevant_rate reduction with 95% bootstrap CI excluding zero.
- Can we publish a reproducible "EPYC-decontaminated BEIR" alongside LightOn's numbers?

## 8. Cross-References

### 8.1 Intake Entries

- **intake-428** — [`DenseOn with the LateOn: Open State-of-the-Art Single and Multi-Vector Models`](https://huggingface.co/blog/lightonai/denseon-lateon) (blog, LightOn, 2026-04) — primary source
- **intake-430** — [`LateOn`](https://huggingface.co/lightonai/LateOn) (model card) — multi-vector checkpoint
- **intake-431** — [`DenseOn`](https://huggingface.co/lightonai/DenseOn) (model card) — dense checkpoint
- **intake-174** — [`Reason-ModernColBERT`](https://huggingface.co/lightonai/Reason-ModernColBERT) (model, eliminated: CC-BY-NC-4.0) — historical context
- **intake-175** — PyLate library evaluation — training/inference framework (MIT, not installable in cp314 venv)
- **intake-405/406/407** — XTR / WARP / Witchcraft — architectural alternatives (validate ColBERT choice; not overridden by this release)

### 8.2 Handoffs

- [`handoffs/active/colbert-reranker-web-research.md`](/workspace/handoffs/active/colbert-reranker-web-research.md) — **target of the Amend section**; add S3b (ONNX export + parity), swap primary candidate from ColBERT-Zero to LateOn, update model comparison table.
- [`handoffs/active/searxng-search-backend.md`](/workspace/handoffs/active/searxng-search-backend.md) — composes upstream; no change required, LateOn still receives SearXNG snippets via the same contract.
- [`handoffs/completed/colbert-zero-research-integration.md`](/workspace/handoffs/completed/colbert-zero-research-integration.md) — historical context for the GTE-ModernColBERT-v1 → future-LateOn progression.

### 8.3 Wiki

- [`wiki/search-retrieval.md`](/workspace/wiki/search-retrieval.md) — update after E1/E2/E3 decision: add LateOn/DenseOn rows to the ColBERT family table, update the "GTE-ModernColBERT-v1 is deployed" actionable, add decontaminated-BEIR column, add a "Training-Data Transparency" sub-section referencing the 665M-pair curated dataset.
- [`wiki/training-distillation.md`](/workspace/wiki/training-distillation.md) — add a pointer to `embeddings-pre-training-curated` and NV-Retriever hard-negative methodology, both reusable for MemRL distillation and any future local retrieval fine-tune.

### 8.4 Datasets (Apache-2.0, released with the models)

- `lightonai/embeddings-pre-training` — 1.4B raw pairs, 34 sources, non-destructive filtering metadata
- `lightonai/embeddings-pre-training-curated` — 665M curated pairs (the best-mixture recipe)
- `lightonai/embeddings-fine-tuning` — 1.88M pairs + query, positive, 2048 mined candidates with scores (useful for reproducing NV-Retriever hard-negative mining)

### 8.5 Related Research Papers

- [NV-Retriever (arXiv:2407.15831)](https://arxiv.org/abs/2407.15831) — hard-negative mining method used in LightOn's SFT stage
- [PyLate (arXiv:2508.03555)](https://arxiv.org/abs/2508.03555) — CIKM 2025, the training+inference framework for ColBERT-family models at LightOn
- [ColBERT-Zero (arXiv:2602.16609)](https://arxiv.org/abs/2602.16609) — Chaffin et al., the immediate predecessor in the LateOn lineage
- [ModernBERT (arXiv:2412.13663)](https://arxiv.org/abs/2412.13663) — the shared backbone
- [BEIR benchmark (arXiv:2104.08663)](https://arxiv.org/abs/2104.08663) — the evaluation target

## 9. Summary Recommendation

LateOn is a **same-architecture, same-license, higher-accuracy drop-in** for the web_research reranker and should be adopted pending ONNX export and a short latency+ranking validation. DenseOn is a **secondary candidate** for probe-first-pool migration and warrants a ~2-hour feasibility benchmark but not immediate adoption. The decontamination protocol and released training data open a high-value **local fine-tuning workstream** that was previously blocked by license constraints on Reason-ModernColBERT. Net effort to primary-recommendation adoption: ~3 hours of experiment time (E1–E4), gated only on ONNX INT8 export availability.

### 9.1 Concrete Next Actions (in priority order)

1. **Immediately** — add an S3b sub-task to `handoffs/active/colbert-reranker-web-research.md`: "Export LateOn to ONNX INT8 and validate parity against PyLate reference." Estimated effort: 1 hour. No infrastructure dependency.
2. **Immediately after S3b** — add an S4b sub-task: "Re-run S4 latency benchmark with LateOn INT8." Estimated effort: 30 minutes. Unblocks the primary AMEND decision.
3. **Before AR-3 completes** — add an S4c sub-task: "Decontaminate web_research sentinel suite against `embeddings-pre-training` hashes." Estimated effort: 1 hour. Guards E3's validity.
4. **Concurrent with AR-3** — prepare an E3 A/B harness that swaps reranker model via flag. Estimated effort: 30 minutes.
5. **Post-AR-3, if E3 passes** — open a DenseOn probe-pool feasibility handoff stub; run E5. Estimated effort: 2 hours.
6. **Post-adoption** — update `wiki/search-retrieval.md` and `wiki/training-distillation.md` with new primary-source references, decontaminated-BEIR column, and NV-Retriever hard-negative pointer. Estimated effort: 30 minutes.

### 9.2 What This Deep-Dive Does Not Commit To

Explicitly out of scope of this document, left for future deep-dives or handoffs:
- A full local fine-tune of LateOn on EPYC-domain data (Expand item #2; separate handoff if the ROI is ever demonstrated).
- Multilingual retrieval requirements (Expand item #6; no current trigger).
- Replacing LateOn-Code on port 8088 with a fresh LateOn fine-tune for code search (interesting but non-urgent; LateOn-Code is already a same-family model with acceptable performance).
- DenseOn as a MemRL-distillation seed (Expand item #4; depends on Track 2 reactivation).
- Re-evaluating jina-ColBERT-v2 or SauerkrautLM forks (blocked on multilingual trigger).

Any of these may be promoted to an active handoff once adoption of LateOn as primary reranker is confirmed and stable.

---

**Document metadata**:
- Author: EPYC research deep-dive pipeline
- Confidence: high (primary sources re-fetched, numbers cross-verified against blog + both model cards)
- Next review: after E1–E4 completion or 2026-05-01, whichever comes first
- Tier 2b contradicting-evidence flag: **run before adoption** (LightOn commercial bias, decontamination methodology, EPYC-domain MaxSim scaling)
