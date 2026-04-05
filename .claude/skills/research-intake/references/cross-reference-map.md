# Cross-Reference Map

Maps taxonomy categories to specific files and search terms for cross-referencing.

## Category → File Mapping

### speculative_decoding
- **Chapters**: `01-speculative-decoding.md`, `03-prompt-lookup.md`, `05-deprecated-approaches.md`, `10-advanced-speculative-decoding.md`
- **Handoffs**: `tree-speculation-numa-drafting.md`, `hsd-hierarchical-self-speculation.md`
- **Experiments**: `specexec-verification-profile.md`, `bench_self_speculation.sh`
- **Search terms**: speculative decoding, draft model, tree speculation, Sequoia, SpecInfer, Medusa, EAGLE, self-speculation, hierarchical speculation

### moe_optimization
- **Chapters**: `02-moe-optimization.md`
- **Handoffs**: (none active)
- **Search terms**: mixture of experts, expert pruning, expert offloading, MoE routing

### kv_cache
- **Chapters**: `04-radix-attention.md`
- **Handoffs**: `kv-cache-quantization.md`, `tq3-quantization-evaluation.md` (monitoring upstream PRs)
- **Search terms**: KV cache, paged attention, prefix caching, radix attention, cache eviction, vAttention, ChunkKV, TurboQuant, Hadamard rotation

### quantization
- **Chapters**: (none)
- **Handoffs**: `kv-cache-quantization.md`, `tq3-quantization-evaluation.md`
- **Search terms**: quantization, GPTQ, AWQ, GGUF, Q4_K_M, mixed precision, calibration, TQ3_1S, Walsh-Hadamard, TurboQuant

### benchmark_methodology
- **Chapters**: `06-benchmarking-framework.md`, `07-benchmark-suite-construction.md`
- **Handoffs**: `qwen35-frontdoor-benchmark.md`
- **Search terms**: benchmark, evaluation, scoring, dataset construction, question pool

### cost_aware_routing
- **Chapters**: `08-cost-aware-rewards.md`
- **Handoffs**: `routing-intelligence.md`
- **Search terms**: cost-aware, reward model, routing cost, latency-quality tradeoff

### agent_architecture
- **Chapters**: `09-claude-debugger.md`
- **Handoffs**: `orchestrator-stack-audit.md`, `rlm-orchestrator-roadmap.md`, `orchestrator-conversation-management.md`, `meta-harness-optimization.md`
- **Search terms**: agent architecture, tool use, REPL, code generation, orchestration, harness optimization, subagent, tool-level constraints

### context_extension
- **Chapters**: (none)
- **Handoffs**: `yarn-context-extension-research.md`, `long-context-eval-datasets.md`
- **Search terms**: YaRN, RoPE scaling, context extension, long context, sliding window

### context_management
- **Chapters**: (none)
- **Handoffs**: `context-folding-progressive.md`, `orchestrator-conversation-management.md`, `tool-output-compression.md`
- **Search terms**: context compaction, session compaction, context folding, prompt cache boundary, HISTORY_SNIP, CONTEXT_COLLAPSE, micro-compaction, token compression, tool output filtering, RTK, segment dedup, helpfulness scoring, free-zone threshold, role-aware compaction, AgentOCR, Skill0, ICRL, optical self-compression

### inference_serving
- **Chapters**: (none)
- **Handoffs**: `dynamic-stack-concurrency.md`
- **Search terms**: continuous batching, disaggregated serving, vLLM, TensorRT-LLM, llama.cpp server

### routing_intelligence
- **Chapters**: (none)
- **Handoffs**: `routing-intelligence.md`, `routing-and-optimization-index.md`
- **Search terms**: routing classifier, difficulty estimation, factual risk, delegation policy

### hardware_optimization
- **Chapters**: (none)
- **Handoffs**: `tree-speculation-numa-drafting.md`
- **Search terms**: NUMA, GPU kernel, flash attention, operator fusion, CUDA graph, Neural Engine, ANE

### ssm_hybrid
- **Chapters**: (none)
- **Handoffs**: `multiscreen-attention-evaluation.md` (screening as alternative to softmax/Delta Net)
- **Search terms**: Mamba, state space model, SSM, hybrid architecture, linear attention, Jamba, Delta Net, Multiscreen, screening mechanism, absolute relevance

### multimodal
- **Chapters**: (none)
- **Handoffs**: `multimodal-pipeline.md`
- **Search terms**: vision-language, multimodal, image understanding, VLM, TTS, Gemma 4, any-to-any, MedGemma

### training_distillation
- **Chapters**: (none)
- **Handoffs**: `08-doc-to-lora-prototype.md`
- **Search terms**: distillation, LoRA, fine-tuning, RLHF, DPO

### autonomous_research
- **Chapters**: (none)
- **Handoffs**: `autopilot-continuous-optimization.md`, `meta-harness-optimization.md`
- **Search terms**: autonomous research, automated experimentation, self-improving, Meta-Harness, harness search

### swarm_techniques
- **Chapters**: (none)
- **Handoffs**: `autopilot-continuous-optimization.md` (SiliconSwarm-inspired cross-species patterns)
- **Search terms**: swarm, multi-agent coordination, parallel exploration, collective intelligence, SiliconSwarm, Ensue, shared memory

### memory_augmented
- **Chapters**: (none)
- **Handoffs**: `orchestrator-conversation-management.md` (B1: User Modeling)
- **Search terms**: episodic memory, working memory, external memory, memory-augmented, user modeling

## File Locations

All paths are relative to the respective repo root:

- **Chapters**: `epyc-inference-research/docs/chapters/`
- **Active handoffs**: `epyc-root/handoffs/active/`
- **Completed handoffs**: `epyc-root/handoffs/completed/`
- **Experiments**: `epyc-inference-research/docs/experiments/`
- **Research notes**: `epyc-root/research/`
- **Intake index**: `epyc-root/research/intake_index.yaml`
