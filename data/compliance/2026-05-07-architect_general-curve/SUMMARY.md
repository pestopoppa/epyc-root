# Compliance curve — architect_general (Qwen3.5-122B-A10B Q4_K_M)

Run: 2026-05-07. Phase 3 of agent-file-prose-compression.md.

**Model**: `Qwen3.5-122B-A10B-Q4_K_M-00001-of-00003.gguf`
**Path**: `/mnt/raid0/llm/lmstudio/models/unsloth/Qwen3.5-122B-A10B-GGUF/Q4_K_M/Qwen3.5-122B-A10B-Q4_K_M-00001-of-00003.gguf`
**Architecture**: 122B-A10B (10B active, hybrid SSM+attention)
**Quantization**: Q4_K_M (multi-part)
**RAM**: 69 GB mlock-resident
**model_id (recorded in JSON)**: `qwen3.5-122b-a10b-q4`

**Server**: standalone llama-server, canonical OMP env (PROC_BIND=spread / PLACES=cores / WAIT_POLICY=active / numactl --interleave=all), --threads 96 --threads-batch 96 --ctx-size 16384 --batch-size 2048 --ubatch-size 512 --flash-attn auto --mlock --no-warmup --no-mmap.
**Suite**: tests/compliance/agent_file/ — 15 forbidden-action + 12 procedure-correctness (v2 synonym-group schema) + 15 instruction-recall = 42 tasks per level.
**Sampling**: temperature=0.0, max_tokens=768, `chat_template_kwargs.enable_thinking=False` (mandatory for this reasoning model).

## Results

| Level | Tokens | Reduction | Compliance | Procedure | Recall | Wall-time |
|---|---|---|---|---|---|---|
| none | 1300 | +0.0% | 0.800 | 0.833 | 1.000 | 1570.3s |
| mild | 1179 | +9.3% | 0.933 | 0.833 | 0.933 | 1652.0s |
| medium | 1068 | +17.8% | 0.867 | 0.833 | 1.000 | 1643.7s |
| aggressive | 991 | +23.8% | 0.933 | 0.917 | 0.933 | 1702.7s |

## Deployment-gate verdict

Per `handoffs/active/agent-file-prose-compression.md` Phase 3 rule (relative-to-baseline interpretation): each compressed level must meet **compliance ≥ 95% of level=none compliance** AND **procedure ≥ 95% of level=none procedure** AND **recall ≥ 0.90** (absolute floor, since recall measures the model's actual ability to retain the agent file in working memory). The model's `agent_file_compression_operating_point` is the highest level passing all three.

**Baseline (level=none)**: compliance 0.800, procedure 0.833, recall 1.000.

| Level | Compliance | Procedure | Recall | Verdict |
|---|---|---|---|---|
| none | 0.800 | 0.833 | 1.000 | (baseline) |
| mild | 0.933 (117%) ✓ | 0.833 (100%) ✓ | 0.933 ✓ | **PASS** |
| medium | 0.867 (108%) ✓ | 0.833 (100%) ✓ | 1.000 ✓ | **PASS** |
| aggressive | 0.933 (117%) ✓ | 0.917 (110%) ✓ | 0.933 ✓ | **PASS** |

**`agent_file_compression_operating_point: aggressive`** ✓.

## Notes

- Sample size: n=15 forbidden-action, n=12 procedure-correctness, n=15 instruction-recall per level. Binomial 95% CI half-width ~13 pp at this n. Cross-level deltas under 13 pp are within sampling noise.
- **Procedure pool v2 (synonym groups)** lifted the v1 floor from 0.417 (strict-substring) to 0.83+ for capable models. v1 false-positive rate was high because models naturally emit `feature flag` while v1 anchors were `feature-flag`; v2 accepts hyphen/space/underscore variants.
- **`enable_thinking=False`** is mandatory for Qwen3.5+/Qwen3.6/Qwen3-Next reasoning models. Without it, the `<think>` block consumes the entire `max_tokens` budget and returns 0 visible chars to /v1/chat/completions, trivially failing every test.
