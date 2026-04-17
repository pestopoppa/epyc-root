# Lean 4 Proving Pipeline — Leanstral + Goedel-Code-Prover

**Status**: ⚠️ QUEUED FOR BLOCKED MOVE (2026-04-17 audit — 20d stale; stub with no progress; no owner; cross-repo coordination unassigned). **Gate to reactivate**: assign S1 owner (Goedel-CP-8B GGUF convert, lowest-effort entry). Move `active/` → `blocked/` pending directory permissions fix.
**Created**: 2026-03-28 (via research intake deep dive)
**Categories**: specialist_models, formal_verification, moe_optimization
**Depends on**: hermes-agent-index.md (OpenGauss context), kv-cache-quantization.md (REAP infrastructure)

## Objective

Deploy a two-tier Lean 4 proving pipeline on EPYC hardware using local models:
- **Tier 1 (Planner)**: Leanstral (119B MoE, 6.5B active) — repo-scale proof strategy, context selection, proof decomposition at architectural level
- **Tier 2 (Executor)**: Goedel-Code-Prover-8B (8B dense) — function-level tactic generation, leaf-goal proving via hierarchical search

Analogous to the OCR pipeline pattern: large model plans, small model executes at volume.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-233 | Goedel-Code-Prover: Hierarchical Proof Search for Code Verification | high | worth_investigating |
| intake-235 | Leanstral: Open-Source Foundation for Trustworthy Vibe-Coding | high | worth_investigating |

## Architecture

```
User / OpenGauss Agent Harness
        │
        ▼
┌──────────────────────┐
│ Leanstral (Tier 1)   │  119B MoE → REAP-pruned to ~20 GB
│ - Repo-scale context │  MCP: lean-lsp-mcp for LSP integration
│ - Proof strategy     │  Output: subgoal decomposition, context windows
│ - Which files matter │
└──────┬───────────────┘
       │ subgoals
       ▼
┌──────────────────────┐
│ Goedel-CP-8B (Tier 2)│  ~4.5 GB Q4_K_M
│ - Tactic generation  │  Hierarchical proof search
│ - Leaf-goal proving  │  Compiler feedback loop
│ - pass@k attempts    │  OpenAI-compat API
└──────┬───────────────┘
       │ proofs
       ▼
┌──────────────────────┐
│ Lean 4 Verifier      │  lean-ray-server (Ray-based)
│ - Type checking      │  QuickCheck counterexample search
│ - Proof validation   │
└──────────────────────┘
```

## Model Details

### Goedel-Code-Prover-8B
- **Base**: Qwen3-8B (vanilla, no modifications)
- **Architecture**: `qwen3` in llama.cpp — fully supported
- **Source**: https://huggingface.co/Goedel-LM/Goedel-Code-Prover-8B (safetensors, BF16)
- **License**: MIT
- **Results**: 62.0% prove success on 427 tasks (Verina/Clever/AlgoVeri), 2.6× over strongest baseline
- **Q4_K_M**: ~4.5 GB, expected 25-40 t/s on EPYC 9655
- **Q8_0**: ~8.5 GB, expected 15-25 t/s
- **Deep dive**: `research/deep-dives/goedel-code-prover-analysis.md`

### Leanstral
- **Base**: Mistral Small 4 (DeepSeek V3-style MoE + MLA)
- **Architecture**: `deepseek2` in llama.cpp — fully supported
- **Params**: 119B total, 6.5B active. 128 routed experts (2048 FFN each), 4 active/token, 1 shared expert (12288 FFN)
- **Source**: https://huggingface.co/mistralai/Leanstral-2603 (official), `jackcloudman/Leanstral-2603-GGUF` (community GGUFs)
- **License**: Apache 2.0
- **Results**: 26.3 pass@2 on FLTEval, beats Sonnet by 2.6 points at 15× lower cost
- **Q4_K_M**: ~68 GB (full), ~20 GB (REAP-32 pruned)
- **REAP candidate**: 95% of params are routed experts. Lean 4 is narrow domain → likely high expert clustering
- **Deep dive**: `research/deep-dives/leanstral-architecture-analysis.md`

## Work Items

### S1: Convert Goedel-CP-8B to GGUF [Priority: P0]
- Download safetensors from HuggingFace
- Convert: `python convert_hf_to_gguf.py Goedel-LM/Goedel-Code-Prover-8B --outtype f16`
- Quantize: Q4_K_M and Q8_0
- Validate: run a simple Lean proof generation test via llama-server
- Add to model registry as specialist (`role: lean_prover`)

### S2: Profile Leanstral Expert Activation [Priority: P1]
- Download `jackcloudman/Leanstral-2603-GGUF` Q4_K_M (~68 GB)
- Run with `--moe-expert-stats` on representative Lean 4 proof workloads
- Analyze: how many experts cover 90% / 95% / 99% of activations?
- If ≤32 experts cover 95%: proceed with REAP pruning
- If spread is uniform: REAP pruning risky, defer

### S3: REAP-Prune Leanstral [Priority: P1, depends on S2]
- Apply REAP pruning to top-32 experts (or top-N based on S2 profiling)
- Quantize pruned model: Q4_K_M (~20 GB target)
- Benchmark: quality on FLTEval subset, speed on EPYC 9655
- Compare: REAP-pruned vs full model quality/speed tradeoff

### S4: End-to-End Pipeline Test [Priority: P2, depends on S1]
- Set up Goedel-CP decomposition pipeline against local llama-server (2-4 slots)
- Run on FormalQualBench subset (start with 5 of the 23 theorems)
- Measure: prove success rate, wall-clock time per problem, tokens generated
- Compare: Goedel-CP-8B via llama-server vs OpenGauss baseline (8/23)
- Adjust concurrency settings for local deployment (512 → 2-4 workers)

### S5: Two-Tier Integration [Priority: P3, depends on S3 + S4]
- Design routing: Leanstral for planning/decomposition, Goedel-CP for execution
- Implement: adapter between Leanstral's MCP-based output and Goedel-CP's input format
- Test on full FormalQualBench (23 theorems)
- Measure improvement over single-model approaches

## Infrastructure Requirements

- **Lean 4 toolchain**: Required for both models' verification loop
- **Mathlib4**: Required by Goedel-CP pipeline
- **lean-ray-server**: Ray-based Lean REPL management (bundled with Goedel-CP repo)
- **lean-lsp-mcp**: MCP server for Lean LSP (used by Leanstral)
- **Memory budget**: ~25 GB for both models simultaneously (REAP-pruned Leanstral + Goedel-CP Q4_K_M)

## Open Questions

- Does Leanstral's planning output format align with Goedel-CP's input expectations, or is significant adapter work needed?
- Can the lean-ray-server and lean-lsp-mcp coexist, or do they need separate Lean toolchain instances?
- Is FormalQualBench (23 math theorems) the right eval for code verification? May need Verina subset instead.
- What's the minimum viable concurrency for Goedel-CP's pipeline before wall-clock becomes impractical?
- Should Leanstral's Pixtral vision encoder be stripped to save ~1B params of dead weight?

## Notes

- Both models are open-weight with permissive licenses (MIT + Apache 2.0)
- Combined memory footprint (~25 GB) leaves massive headroom on EPYC 9655
- The pipeline pattern mirrors OCR: large model (Leanstral) plans, small model (Goedel-CP) executes at volume
- OpenGauss agent harness (intake analysis in `research/deep-dives/opengauss-architecture-analysis.md`) could serve as the orchestration layer
