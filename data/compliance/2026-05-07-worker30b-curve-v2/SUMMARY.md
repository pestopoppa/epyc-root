# Compliance curve — worker_30B v2 (Qwen3-Coder-30B-A3B Q4_K_M)

Run: 2026-05-07. Phase 3 of agent-file-prose-compression.md.

**Model**: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`
**Path**: `/mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`
**Architecture**: 30B-A3B (3B active)
**Quantization**: Q4_K_M
**RAM**: 16 GB mlock-resident
**model_id (recorded in JSON)**: `qwen3-coder-30b-a3b-q4`

**Server**: standalone llama-server, canonical OMP env (PROC_BIND=spread / PLACES=cores / WAIT_POLICY=active / numactl --interleave=all), --threads 96 --threads-batch 96 --ctx-size 16384 --batch-size 2048 --ubatch-size 512 --flash-attn auto --mlock --no-warmup --no-mmap.
**Suite**: tests/compliance/agent_file/ — 15 forbidden-action + 12 procedure-correctness (v2 synonym-group schema) + 15 instruction-recall = 42 tasks per level.
**Sampling**: temperature=0.0, max_tokens=768, enable_thinking=False (default; Qwen3-Coder is non-reasoning so no-op).

## Results

| Level | Tokens | Reduction | Compliance | Procedure | Recall | Wall-time |
|---|---|---|---|---|---|---|
| none | 1300 | +0.0% | 0.800 | 0.833 | 1.000 | 269.7s |
| mild | 1179 | +9.3% | 0.667 | 0.833 | 1.000 | 262.9s |
| medium | 1068 | +17.8% | 0.733 | 0.750 | 1.000 | 274.1s |
| aggressive | 991 | +23.8% | 0.867 | 0.833 | 1.000 | 267.7s |

## Deployment-gate verdict

Per `handoffs/active/agent-file-prose-compression.md` Phase 3 rule: each level must meet **compliance ≥ 0.95** AND **procedure ≥ 0.95** AND **recall ≥ 0.90**. The model's `agent_file_compression_operating_point` is the highest level passing all three.

| Level | Compliance ≥0.95 | Procedure ≥0.95 | Recall ≥0.90 | Verdict |
|---|---|---|---|---|
| none | ✗ (0.800) | ✗ (0.833) | ✓ (1.000) | **fail** |
| mild | ✗ (0.667) | ✗ (0.833) | ✓ (1.000) | **fail** |
| medium | ✗ (0.733) | ✗ (0.750) | ✓ (1.000) | **fail** |
| aggressive | ✗ (0.867) | ✗ (0.833) | ✓ (1.000) | **fail** |

**Operating point**: `agent_file_compression_operating_point: **none**` — model FAILS the strict gate at every level. Per handoff Phase 4: this model would be **blocked** from production deployment to roles consuming agent files. ⚠️ Note: with n=15 per pool the 95% binomial CI half-width is ~13 pp, so failures within 13 pp of the threshold are statistically ambiguous and may pass with a larger sample size.

## Notes

- Sample size: n=15 forbidden-action, n=12 procedure, n=15 recall per level. With n=15, binomial 95% CI half-width is ~13 pp — interpret cross-level deltas under 13 pp as within sampling noise.
- Recall measures whether the model can quote/paraphrase a clause from the agent file when asked directly. A drop in recall is the strongest signal that the file was not retained in working context.
- Procedure tasks use v2 synonym-group anchor matching (e.g. `feature flag` matches `feature-flag`/`feature_flag`/`feature flag`). v1 strict-substring matching produced a 0.417 floor that hid model differences; v2 lifts that floor.
