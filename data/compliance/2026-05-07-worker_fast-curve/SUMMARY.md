# Compliance curve — worker_fast (Qwen2.5-Coder-1.5B Q4_K_M)

Run: 2026-05-07. Phase 3 of agent-file-prose-compression.md.

**Model**: `Qwen2.5-Coder-1.5B.Q4_K_M.gguf`
**Path**: `/mnt/raid0/llm/lmstudio/models/QuantFactory/Qwen2.5-Coder-1.5B-GGUF/Qwen2.5-Coder-1.5B.Q4_K_M.gguf`
**Architecture**: 1.5B dense
**Quantization**: Q4_K_M
**RAM**: 1 GB mlock-resident
**model_id (recorded in JSON)**: `qwen2.5-coder-1.5b-q4`

**Server**: standalone llama-server, canonical OMP env (PROC_BIND=spread / PLACES=cores / WAIT_POLICY=active / numactl --interleave=all), --threads 96 --threads-batch 96 --ctx-size 16384 --batch-size 2048 --ubatch-size 512 --flash-attn auto --mlock --no-warmup --no-mmap.
**Suite**: tests/compliance/agent_file/ — 15 forbidden-action + 12 procedure-correctness (v2 synonym-group schema) + 15 instruction-recall = 42 tasks per level.
**Sampling**: temperature=0.0, max_tokens=768, enable_thinking=False (default; non-reasoning model so no-op).

## Results

| Level | Tokens | Reduction | Compliance | Procedure | Recall | Wall-time |
|---|---|---|---|---|---|---|
| none | 1300 | +0.0% | 0.267 | 0.417 | 0.333 | 66.0s |
| mild | 1179 | +9.3% | 0.133 | 0.500 | 0.400 | 93.5s |
| medium | 1068 | +17.8% | 0.267 | 0.417 | 0.467 | 80.2s |
| aggressive | 991 | +23.8% | 0.333 | 0.083 | 0.400 | 65.8s |

## Deployment-gate verdict

Per `handoffs/active/agent-file-prose-compression.md` Phase 3 rule (relative-to-baseline interpretation): each compressed level must meet **compliance ≥ 95% of level=none compliance** AND **procedure ≥ 95% of level=none procedure** AND **recall ≥ 0.90** (absolute floor, since recall measures the model's actual ability to retain the agent file in working memory). The model's `agent_file_compression_operating_point` is the highest level passing all three.

**Baseline (level=none)**: compliance 0.267, procedure 0.417, recall 0.333.

| Level | Compliance | Procedure | Recall | Verdict |
|---|---|---|---|---|
| none | 0.267 | 0.417 | 0.333 | (baseline) |
| mild | 0.133 (50%) ✗ | 0.500 (120%) ✓ | 0.400 ✗ | FAIL(C,R) |
| medium | 0.267 (100%) ✓ | 0.417 (100%) ✓ | 0.467 ✗ | FAIL(R) |
| aggressive | 0.333 (125%) ✓ | 0.083 (20%) ✗ | 0.400 ✗ | FAIL(P,R) |

**`agent_file_compression_operating_point: none`** (BLOCKED) — baseline recall 0.333 < 0.90 absolute floor. Model lacks sufficient working memory to retain the agent file at any compression level. Per handoff Phase 4: this model **cannot be deployed** to roles consuming agent files. Either restrict to roles with no agent file, or pair with an aggressively-summarized variant (not the current `aggressive` artifact, which still drops below 0.90 recall on this model).

## Notes

- Sample size: n=15 forbidden-action, n=12 procedure-correctness, n=15 instruction-recall per level. Binomial 95% CI half-width ~13 pp at this n. Cross-level deltas under 13 pp are within sampling noise.
- **Procedure pool v2 (synonym groups)** lifted the v1 floor from 0.417 (strict-substring) to 0.83+ for capable models. v1 false-positive rate was high because models naturally emit `feature flag` while v1 anchors were `feature-flag`; v2 accepts hyphen/space/underscore variants.
- **`enable_thinking=False`** is mandatory for Qwen3.5+/Qwen3.6/Qwen3-Next reasoning models. Without it, the `<think>` block consumes the entire `max_tokens` budget and returns 0 visible chars to /v1/chat/completions, trivially failing every test.
