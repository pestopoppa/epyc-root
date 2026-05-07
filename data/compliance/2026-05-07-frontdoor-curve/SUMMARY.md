# Compliance curve — frontdoor (Qwen3.6-35B-A3B Q8_0)

Run: 2026-05-07. Phase 3 of agent-file-prose-compression.md.

**Model**: `Qwen_Qwen3.6-35B-A3B-Q8_0.gguf`
**Path**: `/mnt/raid0/llm/models/Qwen_Qwen3.6-35B-A3B-Q8_0.gguf`
**Architecture**: 35B-A3B (3B active, MoE)
**Quantization**: Q8_0
**RAM**: 37 GB mlock-resident
**model_id (recorded in JSON)**: `qwen3.6-35b-a3b-q8`

**Server**: standalone llama-server, canonical OMP env (PROC_BIND=spread / PLACES=cores / WAIT_POLICY=active / numactl --interleave=all), --threads 96 --threads-batch 96 --ctx-size 16384 --batch-size 2048 --ubatch-size 512 --flash-attn auto --mlock --no-warmup --no-mmap.
**Suite**: tests/compliance/agent_file/ — 15 forbidden-action + 12 procedure-correctness (v2 synonym-group schema) + 15 instruction-recall = 42 tasks per level.
**Sampling**: temperature=0.0, max_tokens=768, `chat_template_kwargs.enable_thinking=False` (mandatory for this reasoning model).

## Results

| Level | Tokens | Reduction | Compliance | Procedure | Recall | Wall-time |
|---|---|---|---|---|---|---|
| none | 1300 | +0.0% | 0.800 | 1.000 | 1.000 | 715.1s |
| mild | 1179 | +9.3% | 0.733 | 0.917 | 1.000 | 698.2s |
| medium | 1068 | +17.8% | 0.867 | 1.000 | 1.000 | 712.0s |
| aggressive | 991 | +23.8% | 0.933 | 0.917 | 1.000 | 731.8s |

## Deployment-gate verdict

Per `handoffs/active/agent-file-prose-compression.md` Phase 3 rule (relative-to-baseline interpretation): each compressed level must meet **compliance ≥ 95% of level=none compliance** AND **procedure ≥ 95% of level=none procedure** AND **recall ≥ 0.90** (absolute floor, since recall measures the model's actual ability to retain the agent file in working memory). The model's `agent_file_compression_operating_point` is the highest level passing all three.

**Baseline (level=none)**: compliance 0.800, procedure 1.000, recall 1.000.

| Level | Compliance | Procedure | Recall | Verdict |
|---|---|---|---|---|
| none | 0.800 | 1.000 | 1.000 | (baseline) |
| mild | 0.733 (92%) ✗ | 0.917 (92%) ✗ | 1.000 ✓ | FAIL(C,P) |
| medium | 0.867 (108%) ✓ | 1.000 (100%) ✓ | 1.000 ✓ | **PASS** |
| aggressive | 0.933 (117%) ✓ | 0.917 (92%) ✗ | 1.000 ✓ | FAIL(P) |

**`agent_file_compression_operating_point: medium`** ✓. Note: non-monotonic curve — `mild` fails the gate but `medium` passes. Orchestrator should route this model directly to `medium` (skipping intermediate levels). Per user direction 2026-05-07: skip is the correct policy.

Failure detail at higher levels: mild: FAIL (compliance, procedure); aggressive: FAIL (procedure)

## Notes

- Sample size: n=15 forbidden-action, n=12 procedure-correctness, n=15 instruction-recall per level. Binomial 95% CI half-width ~13 pp at this n. Cross-level deltas under 13 pp are within sampling noise.
- **Procedure pool v2 (synonym groups)** lifted the v1 floor from 0.417 (strict-substring) to 0.83+ for capable models. v1 false-positive rate was high because models naturally emit `feature flag` while v1 anchors were `feature-flag`; v2 accepts hyphen/space/underscore variants.
- **`enable_thinking=False`** is mandatory for Qwen3.5+/Qwen3.6/Qwen3-Next reasoning models. Without it, the `<think>` block consumes the entire `max_tokens` budget and returns 0 visible chars to /v1/chat/completions, trivially failing every test.
