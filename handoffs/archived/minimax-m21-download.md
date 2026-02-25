# MiniMax M2.1 Download + Model Cleanup Handoff

**Date Created:** 2026-01-18
**Purpose:** Download MiniMax M2.1 Q4_K_M + Q6_K after cleaning up existing models
**Status:** Ready for execution
**Save to:** `/mnt/raid0/llm/claude/handoffs/active/minimax-m21-download.md`

---

## Target Model: MiniMax M2.1

| Attribute | Value |
|-----------|-------|
| **Size** | 138 GB (Q4_K_M) |
| **Architecture** | MoE: 230B total, 10B active (8/256 experts) |
| **Vocab** | 200,064 (unique - no compatible draft) |
| **Context** | 196K tokens |
| **Spec Decode** | NOT VIABLE (no smaller MiniMax model) |
| **Best Acceleration** | MoE expert reduction, Prompt Lookup |

### Download Commands (after cleanup)

```bash
# Q4_K_M (138 GB) - faster, slightly lower quality
huggingface-cli download unsloth/MiniMax-M2.1-GGUF \
  MiniMax-M2.1-Q4_K_M.gguf \
  --local-dir /mnt/raid0/llm/lmstudio/models/unsloth/MiniMax-M2.1-GGUF/

# Q6_K (188 GB) - slower, higher quality
huggingface-cli download unsloth/MiniMax-M2.1-GGUF \
  MiniMax-M2.1-Q6_K.gguf \
  --local-dir /mnt/raid0/llm/lmstudio/models/unsloth/MiniMax-M2.1-GGUF/
```

**Total download: 326 GB** (both quants)

---

## Current Disk Status

| Location | Size | Content |
|----------|------|---------|
| `/mnt/raid0/llm/lmstudio/` | 1.4 TB | Main GGUF models |
| `/mnt/raid0/llm/models/` | 77 GB | Secondary GGUF models |
| `/mnt/raid0/llm/hf/` | 26 GB | HuggingFace cache |
| **Free Space** | **655 GB** | Sufficient for 138GB download |

---

## Models in Production (DO NOT DELETE)

These are actively used by the orchestrator (`model_registry.yaml`):

| Role | Model | Size | Port |
|------|-------|------|------|
| **frontdoor + coder_primary** | Qwen3-Coder-30B-A3B-Instruct-Q4_K_M | 18 GB | 8080 |
| **coder_escalation** | Qwen2.5-Coder-32B-Instruct-Q4_K_M | 19 GB | 8081 |
| **coder_escalation draft** | Qwen2.5-Coder-0.5B-Instruct-Q8_0 | ~500 MB | 8081 |
| **worker** | Qwen2.5-7B-Instruct-Q4_K_M | 4.2 GB | 8082 |
| **worker draft** | Qwen2.5-0.5B-Instruct-Q8_0 | ~500 MB | 8082 |
| **architect_general** | Qwen3-235B-A22B-Q4_K_M (4 parts) | 136 GB | 8083 |
| **architect_coding** | Qwen3-Coder-480B-A35B-Instruct-Q4_K_M (8 parts) | 280 GB | 8084 |
| **ingest_long_context** | Qwen3-Next-80B-A3B-Instruct-Q4_K_M | 46 GB | 8085 |

**Total Production:** ~504 GB

### Production Model Validation Against Blind Rescore

| Role | Current Model | Blind Score | Alternatives Considered | Verdict |
|------|---------------|-------------|------------------------|---------|
| **frontdoor** | Qwen3-Coder-30B-A3B | 89.5% | None faster with higher score | ✅ KEEP |
| **coder_primary** | Qwen3-Coder-30B-A3B | 89.0% | None faster with higher score | ✅ KEEP |
| **coder_escalation** | Qwen2.5-Coder-32B | 85.2% | Must differ from frontdoor | ✅ KEEP |
| **worker** | Qwen2.5-7B | 90% (summary.csv) | gemma-3-12b (80%), Llama-3-8B (75%) | ✅ KEEP |
| **architect_general** | Qwen3-235B-A22B | **87.1%** | Llama-3.1-70B (86.3%), Qwen2.5-72B (77.8%) | ✅ KEEP |
| **architect_coding** | Qwen3-Coder-480B | **77.1%** | ⚠️ See analysis below | 🔶 REVIEW |
| **ingest_long_context** | Qwen3-Next-80B | 85.8% | Only SSM for long context | ✅ KEEP |

#### architect_coding Analysis (77.1% - Lowest Production Score)

**Concern:** Qwen3-Coder-480B scored 77.1% in blind rescore - lower than other production models.

**Why it's still the right choice:**

1. **Role is "ultimate escalation"** - used ONLY when 30B fails twice
   - Lower score on general benchmarks acceptable
   - Should excel on HARDEST problems (selection bias)

2. **Blind rescore tested baseline config** - MoE optimization may differ:
   ```
   baseline: 77.1%
   MoE4:     94% (from summary.csv)
   MoE6:     79%
   MoE8:     100% (limited questions)
   ```

3. **No better alternative for this role:**
   - TOTAL-RECALL (97% MoE6) - Fragile, baseline 22%
   - Qwen3-Coder-30B (89%) - Already frontdoor
   - Must be LARGER than escalation source

4. **Speed-quality tradeoff:**
   - 480B @ 6.6 t/s (MoE4) for hardest problems
   - No faster model with comparable capacity exists

**Action:** Keep current assignment but monitor MiniMax M2.1 as potential alternative.

#### Why MiniMax M2.1 Could Change This

| Metric | Qwen3-235B-A22B | Qwen3-Coder-480B | MiniMax M2.1 (expected) |
|--------|-----------------|------------------|-------------------------|
| Score | 87.1% | 77.1%-94% | TBD (need benchmark) |
| Speed | 7.2 t/s (MoE4) | 6.6 t/s (MoE4) | ~18-22 t/s (Q4) |
| Active Params | ~8B (MoE4) | ~13B (MoE4) | 10B (fixed) |
| Memory | 136 GB | 280 GB | 138 GB |

**If MiniMax M2.1 scores ≥85%:**
- Could replace architect_general (3x faster, similar quality)
- Could replace architect_coding (2x faster, potentially higher quality)

**This is why we're downloading it - to test this hypothesis.**

---

## Candidates for Deletion

### Category A: Duplicate/Redundant (Safe to Delete)

| Model | Size | Reason |
|-------|------|--------|
| Qwen3-Coder-30B-A3B-Instruct (lmstudio-community) | 18 GB | Duplicate - have unsloth version |
| Qwen3-Next-80B-A3B-Instruct-Q2_K | 28 GB | Lower quality - have Q4_K_M |
| DeepSeek-R1-Distill-Qwen-32B-Q4_K_M | 19 GB | Duplicate in models/ dir |
| DeepSeek-R1-Distill-Qwen-32B-Q2_K | 12 GB | Lower quality quant |

**Subtotal A:** ~77 GB

### Category B: Benchmarked, Not in Production (BLIND RESCORE 2026-01-16)

| Model | Size | Blind Score | t/s | Recommendation |
|-------|------|-------------|-----|----------------|
| Meta-Llama-3.1-70B-Instruct-Q4_K_M | 40 GB | **86.3%** | 2.1 | **KEEP** - best Llama 70B |
| Hermes-4-70B-Q4_K_M | 40 GB | 85.2% | 2.7 | DELETE - Llama 3.1 slightly better |
| DeepSeek-R1-Distill-Llama-70B-Q4_K_M | 40 GB | **67%** | 1.0 | **DELETE** - truncation issues, slow |
| Meta-Llama-3-70B-Instruct-Q4_K_M | 40 GB | ~36% | 1.5 | **DELETE** - very poor |
| Qwen2.5-72B-Instruct-Q4_K_M | 45 GB | 77.8% | 1.9 | KEEP - decent general 72B |
| Qwen2.5-72B (base) | 45 GB | — | 2.2 | DELETE - not instruct |
| Qwen2.5-Math-72B-Instruct-Q6_K (2 parts) | 61 GB | — | 0.0 | DELETE - Q4_K_M version exists |
| gemma-3-27B-it-QAT-Q4_0 | 15 GB | 77% | 2.2 | DELETE - SWA breaks spec decode |

**Critical Finding from Blind Rescore:**
- **Meta-Llama-3.1-8B.Q4_K_S: ~6%** - BROKEN MODEL, severe repetition issues, DO NOT USE

**Recommended deletes from B:** ~241 GB
**Keep from B:** Meta-Llama-3.1-70B (40 GB), Qwen2.5-72B-Instruct (45 GB)

### Category C: Experimental/Testing (Review)

#### Qwen3-Coder-53B-A3B-TOTAL-RECALL Analysis

**Size:** 30 GB

**Performance by Expert Count (from summary.csv):**
| Config | Score | Speed | Quality |
|--------|-------|-------|---------|
| Baseline (8 experts) | **22%** | 10.3 t/s | GARBAGE |
| MoE2 (2 experts) | 55% | 15.8 t/s | Poor |
| MoE4 (4 experts) | 64% | 14.0 t/s | Moderate |
| MoE6 (6 experts) | **97%** | 12.7 t/s | EXCELLENT |

**Analysis:**
- The 90.7% in blind rescore was likely from MoE6 config
- **Inverted quality curve**: Default 8-expert config produces garbage (22%)
- Must use `--override-kv` with exactly 6 experts to work
- Community finetune broke the default expert routing

**Verdict: DELETE**
- Baseline unusable (22%)
- Quality depends on fragile MoE configuration
- Not production-ready - requires specific override to function
- Production already has Qwen3-Coder-30B-A3B (100% @ 12 t/s baseline)
| Qwen3-VL-235B-A22B-Thinking (3 parts + mmproj) | 128 GB | Vision, not in production |
| Qwen3-Next-80B-A3B-Thinking-Q4_K_S | 43 GB | Thinking variant, have Instruct |
| MathSmith-Hard-Problem-Synthesizer | 4.7 GB + 8.2 GB | Specialized, rarely used |
| Co-rewarding-II-Qwen3-1.7B-Base-MATH | 2.1 GB | Draft testing, not selected |
| Qwen3-30B-A3B-Thinking-2507 (Q4_K_S + Q8_0) | 48 GB | Thinking variant |
| Phi-4-reasoning-plus (Q4_K_M + Q8_0) | 23.5 GB | New, needs benchmarking |

**Subtotal C:** ~287 GB

### Category D: Draft Models (Keep All)

| Model | Size | Used By |
|-------|------|---------|
| Qwen2.5-Coder-0.5B-Instruct-* | ~1 GB | coder_escalation |
| Qwen2.5-0.5B-Instruct-* | ~1 GB | worker |
| DeepSeek-R1-Distill-Qwen-1.5B-* | ~2 GB | thinking models |
| PARD-DeepSeek-R1-Distill-Qwen-1.5B | ~2 GB | PARD draft |
| Qwen3-0.6B-* | ~1 GB | Qwen3 draft |
| Qwen3-1.7B-* | ~2 GB | Qwen3 draft |

**Keep all drafts** - small and essential for spec decode

---

## Recommended Cleanup Actions

### Deletion Script (APPROVED)

```bash
#!/bin/bash
set -euo pipefail

# Phase 1: Duplicates (77 GB)
rm -v /mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/*.gguf
rm -v /mnt/raid0/llm/models/Qwen3-Next-80B-A3B-Instruct-Q2_K.gguf
rm -v /mnt/raid0/llm/models/DeepSeek-R1-Distill-Qwen-32B-*.gguf

# Phase 2: 70B consolidation (120 GB) - keep only Llama 3.1
rm -rv /mnt/raid0/llm/lmstudio/models/lmstudio-community/Meta-Llama-3-70B-Instruct-GGUF/
rm -rv /mnt/raid0/llm/lmstudio/models/lmstudio-community/Hermes-4-70B-GGUF/
rm -rv /mnt/raid0/llm/lmstudio/models/unsloth/DeepSeek-R1-Distill-Llama-70B-GGUF/

# Phase 3: Low performers & duplicates (151 GB)
rm -rv /mnt/raid0/llm/lmstudio/models/mradermacher/Qwen2.5-72B-GGUF/  # base, not instruct
rm -rv /mnt/raid0/llm/lmstudio/models/tensorblock/Qwen2.5-Math-72B-Instruct-GGUF/  # Q6_K dup
rm -rv /mnt/raid0/llm/lmstudio/models/lmstudio-community/gemma-3-27B-it-qat-GGUF/  # SWA broken
rm -rv /mnt/raid0/llm/lmstudio/models/mradermacher/Qwen3-Coder-53B-A3B-Instruct-TOTAL-RECALL-v2-MASTER-CODER-L-i1-GGUF/

echo "Freed ~348 GB"
df -h /mnt/raid0/
```

### Update Model Registry

After deletion, update `/mnt/raid0/llm/claude/orchestration/model_registry.yaml`:

1. **Remove deleted models from `compatible_drafts` sections** (if referenced)
2. **Add to `deprecated_models` section:**

```yaml
deprecated_models:
  # Deleted 2026-01-18 - MiniMax M2.1 cleanup
  - model: Meta-Llama-3-70B-Instruct-Q4_K_M
    reason: "36% benchmark score, superseded by Llama 3.1-70B (93%)"
    deleted: 2026-01-18
  - model: Hermes-4-70B-Q4_K_M
    reason: "89% score, superseded by Llama 3.1-70B (93%)"
    deleted: 2026-01-18
  - model: DeepSeek-R1-Distill-Llama-70B-Q4_K_M
    reason: "82% score, 1.0 t/s - slow and lower quality"
    deleted: 2026-01-18
  - model: Qwen2.5-72B.Q4_K_M
    reason: "Base model (not instruct), 87% - keep Instruct version"
    deleted: 2026-01-18
  - model: Qwen2.5-Math-72B-Instruct-Q6_K
    reason: "77% score anomaly, Q4_K_M version scores 92%"
    deleted: 2026-01-18
  - model: gemma-3-27B-it-QAT-Q4_0
    reason: "95% quality but SWA breaks speculative decoding"
    deleted: 2026-01-18
  - model: Qwen3-Coder-53B-A3B-TOTAL-RECALL
    reason: "Inconsistent scores (22-97%), unreliable community finetune"
    deleted: 2026-01-18
```

3. **Verify no production roles reference deleted models**

---

## Post-Cleanup: MiniMax M2.1 Integration

### 1. Download
```bash
huggingface-cli download unsloth/MiniMax-M2.1-GGUF \
  MiniMax-M2.1-Q4_K_M.gguf \
  --local-dir /mnt/raid0/llm/lmstudio/models/unsloth/MiniMax-M2.1-GGUF/
```

### 2. Verify llama.cpp Support
```bash
# Check if minimax_m2 architecture is supported
/mnt/raid0/llm/llama.cpp/build/bin/llama-cli \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/MiniMax-M2.1-GGUF/MiniMax-M2.1-Q4_K_M.gguf \
  -p "Hello" -n 10
```

### 3. Benchmark & Add to Registry
- Run quality rubric
- Test MoE expert reduction (try 4 experts: `--override-kv minimax_m2.expert_used_count=int:4`)
- Add to `model_registry.yaml` if performance warrants

### 4. Potential Role Assignment (Based on Benchmarks)

**Current architect tier performance:**
| Role | Model | Score | Speed |
|------|-------|-------|-------|
| architect_general | Qwen3-235B-A22B | 94% | 5.8 t/s (baseline), 7.2 t/s (MoE4) |
| architect_coding | Qwen3-Coder-480B | 83-94% | 6.0-6.6 t/s (MoE4) |

**MiniMax M2.1 ACTUAL (2026-01-19):**
- Baseline (8 experts): 9.52 t/s generation, 40.51 t/s prompt
- **Optimized (4 experts): 13.64 t/s generation (+43%), 59.94 t/s prompt (+48%)**

**Potential roles:**
- **architect_general_alt**: If score ≥90% - **1.9x faster** than Qwen3-235B (7.2 t/s) at 13.64 t/s
- **architect_coding_alt**: If coding score ≥85% - **2x faster** than Qwen3-Coder-480B (6.6 t/s)
- **coder_primary**: Unlikely - no spec decode means can't beat Qwen2.5-Coder-32B (21.3 t/s w/spec)

**Key comparison point (UPDATED):**
- MiniMax M2.1 Q4_K_M optimized: **13.64 t/s** at ~5B active (4 of 10B)
- Qwen3-235B-A22B MoE4: 7.2 t/s at ~8B active (4 of 22B)
- **MiniMax is 1.9x faster** for architect tasks (if quality is similar)

---

## Execution Checklist

- [x] Run deletion script (348 GB freed) - **DONE 2026-01-18** (~335 GB freed, 990 GB now available)
- [x] Update `model_registry.yaml` with deprecated_models section - **DONE 2026-01-18**
- [x] Verify `df -h /mnt/raid0/` shows 326+ GB free - **DONE** (990 GB available)
- [x] Download MiniMax M2.1 Q4_K_M (138 GB) - **DONE** (3 parts, 129 GB)
- [x] Download MiniMax M2.1 Q6_K (188 GB) - **DONE** (4 parts, 175 GB)
- [x] Test llama.cpp architecture support - **DONE 2026-01-19**
  - **Works on production-consolidated (build 7711)**
  - Requires `--jinja` flag for chat template
  - Generation: **9.49 t/s** (lower than expected 18-22 t/s)
  - Prompt: **40.73 t/s**
  - Memory: ~180 GB (model 130 GB + KV cache 48 GB)
  - Uses `<think>` tags (reasoning model style)
  - Command: `llama-completion -m MiniMax-M2.1-Q4_K_M-00001-of-00003.gguf -p "prompt" -n 30 -t 96 --jinja`
- [x] Test MoE expert reduction - **DONE 2026-01-19**
  - **Override key uses hyphens**: `--override-kv minimax-m2.expert_used_count=int:4`
  - 8 experts (default): 9.52 t/s generation, 40.51 t/s prompt
  - 4 experts: **13.64 t/s generation (+43%)**, **59.94 t/s prompt (+48%)**
- [x] Add to model_registry.yaml - **DONE 2026-01-19**
  - Added `minimax_m21_q4` and `minimax_m21_q6` entries
  - Added runtime quirks section for MiniMax M2.1
  - Server mode tested and working (port 8090)
- [ ] Run quality rubric benchmark
- [ ] Create handoff at `handoffs/active/minimax-m21-integration.md` for production integration

---

## Runtime Quirks (2026-01-19)

| Quirk | Description | Workaround |
|-------|-------------|------------|
| **Jinja required** | Chat template fails without `--jinja` | Always use `--jinja` flag |
| **Interactive mode** | `llama-cli` enters conversation mode by default | Use `llama-completion` instead |
| **Thinking tags** | Model outputs `<think>` blocks (reasoning model) | Parse/strip for non-reasoning use |
| **256 experts** | Large expert count may cause sparse memory access | May explain lower-than-expected speed |
| **3-part split** | Model split across 3 GGUF files | Use first part, others auto-loaded |

---

## Decisions Made

| Item | Decision | Reason | Space |
|------|----------|--------|-------|
| 70B Models | Keep only Meta-Llama-3.1-70B | Best 70B (86.3%) | Free 120 GB |
| Qwen3-VL-235B-Thinking | **KEEP** | Potential vision work | 0 GB |
| Qwen3-Coder-53B-TOTAL-RECALL | **DELETE** | Baseline 22%, fragile MoE dependency | Free 30 GB |
| Phi-4-reasoning-plus | Keep (benchmark first) | 75% thinking score | 0 GB |

### Data Sources Used
- `/workspace/benchmarks/results/reviews/BLIND_RESCORE_2026-01-16.md` - Main reference
- `/workspace/benchmarks/results/reviews/summary.csv` - MoE variant breakdown
- `/workspace/benchmarks/results/reviews/thinking_models_summary.csv` - Thinking scores

---

## Reasoning: Why Blind Rescore Didn't Change Production Models

### 1. Production Selection Criteria Were Multi-Dimensional

Production models were selected based on:
- **Quality** (benchmark scores)
- **Speed** (tokens/second)
- **Memory footprint** (fits in tier budget)
- **Role fit** (specialization)
- **Acceleration compatibility** (spec decode, MoE reduction)

Blind rescore only re-evaluates quality. A model with 5% higher score but 3x slower may not be a better choice.

### 2. Blind Rescore Confirmed Rather Than Contradicted

| Role | Previous Score | Blind Rescore | Change |
|------|----------------|---------------|--------|
| frontdoor | ~95% | 89.5% | -5.5% (stricter scoring) |
| architect_general | 94% | 87.1% | -6.9% (stricter scoring) |
| architect_coding | 83-94% | 77.1%-94% | Consistent range |

The scores dropped uniformly due to stricter blind scoring methodology. **Relative rankings were preserved.**

### 3. Models Recommended for Deletion Have Clear Disqualifiers

| Deleted Model | Blind Score | Why Not Production |
|---------------|-------------|-------------------|
| DeepSeek-R1-Distill-Llama-70B | 67% | Severe truncation issues |
| Meta-Llama-3-70B | ~36% | Very poor quality |
| TOTAL-RECALL | 22% baseline | Fragile MoE dependency |
| Hermes-4-70B | 85.2% | Llama 3.1 is slightly better |

### 4. The Gap MiniMax M2.1 Could Fill

Current weakness: **architect_coding at 77.1%** is the lowest production score.

If MiniMax M2.1 achieves:
- **≥85% quality** at **~20 t/s**
- It would be:
  - **3x faster** than Qwen3-Coder-480B (6.6 t/s)
  - **~10% higher quality** than current architect_coding
  - **Same memory** (138 GB vs 136 GB for architect_general)

This is the hypothesis we're testing with this download.

## Final Space Summary

| Action | Space Freed |
|--------|-------------|
| Category A (duplicates) | 77 GB |
| 70B consolidation | 120 GB |
| Qwen3-Coder-53B-TOTAL-RECALL | 30 GB |
| Other Category B (base models, Q6_K dups) | 106 GB |
| gemma-3-27B-QAT | 15 GB |
| **Total to Delete** | **348 GB** |
| **Required for MiniMax** | **326 GB** (Q4 + Q6) |
| **Buffer after download** | **677 GB** |
