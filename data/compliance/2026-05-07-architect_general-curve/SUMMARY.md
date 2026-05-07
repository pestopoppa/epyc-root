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
**Sampling**: temperature=0.0, max_tokens=768, enable_thinking=False (chat_template_kwargs).

## Results

| Level | Tokens | Reduction | Compliance | Procedure | Recall | Wall-time |
|---|---|---|---|---|---|---|
| none | 1300 | +0.0% | 0.800 | 0.833 | 1.000 | 1570.3s |
| mild | 1179 | +9.3% | 0.933 | 0.833 | 0.933 | 1652.0s |
| medium | 1068 | +17.8% | 0.867 | 0.833 | 1.000 | 1643.7s |
| aggressive | 991 | +23.8% | 0.933 | 0.917 | 0.933 | 1702.7s |

## Deployment-gate verdict

Per `handoffs/active/agent-file-prose-compression.md` Phase 3 rule: each level must meet **compliance ≥ 0.95** AND **procedure ≥ 0.95** AND **recall ≥ 0.90**. The model's `agent_file_compression_operating_point` is the highest level passing all three.

| Level | Compliance ≥0.95 | Procedure ≥0.95 | Recall ≥0.90 | Verdict |
|---|---|---|---|---|
| none | ✗ (0.800) | ✗ (0.833) | ✓ (1.000) | **fail** |
| mild | ✗ (0.933) | ✗ (0.833) | ✓ (0.933) | **fail** |
| medium | ✗ (0.867) | ✗ (0.833) | ✓ (1.000) | **fail** |
| aggressive | ✗ (0.933) | ✗ (0.917) | ✓ (0.933) | **fail** |

**Operating point**: `agent_file_compression_operating_point: **none**` — model FAILS the strict gate at every level. Per handoff Phase 4: this model would be **blocked** from production deployment to roles consuming agent files. ⚠️ Note: with n=15 per pool the 95% binomial CI half-width is ~13 pp, so failures within 13 pp of the threshold are statistically ambiguous and may pass with a larger sample size.

## Notes

- Sample size: n=15 forbidden-action, n=12 procedure, n=15 recall per level. With n=15, binomial 95% CI half-width is ~13 pp — interpret cross-level deltas under 13 pp as within sampling noise.
- Recall measures whether the model can quote/paraphrase a clause from the agent file when asked directly. A drop in recall is the strongest signal that the file was not retained in working context.
- Procedure tasks use v2 synonym-group anchor matching (e.g. `feature flag` matches `feature-flag`/`feature_flag`/`feature flag`). v1 strict-substring matching produced a 0.417 floor that hid model differences; v2 lifts that floor.
