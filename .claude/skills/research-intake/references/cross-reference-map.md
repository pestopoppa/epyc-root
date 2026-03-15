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
- **Handoffs**: (none active)
- **Search terms**: KV cache, paged attention, prefix caching, radix attention, cache eviction, vAttention

### quantization
- **Chapters**: (none)
- **Handoffs**: (none active)
- **Search terms**: quantization, GPTQ, AWQ, GGUF, Q4_K_M, mixed precision, calibration

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
- **Handoffs**: `orchestrator-stack-audit.md`, `rlm-orchestrator-roadmap.md`
- **Search terms**: agent architecture, tool use, REPL, code generation, orchestration

### context_extension
- **Chapters**: (none)
- **Handoffs**: `yarn-context-extension-research.md`
- **Search terms**: YaRN, RoPE scaling, context extension, long context, sliding window

### inference_serving
- **Chapters**: (none)
- **Handoffs**: (none active)
- **Search terms**: continuous batching, disaggregated serving, vLLM, TensorRT-LLM, llama.cpp server

### routing_intelligence
- **Chapters**: (none)
- **Handoffs**: `routing-intelligence.md`
- **Search terms**: routing classifier, difficulty estimation, factual risk, delegation policy

### hardware_optimization
- **Chapters**: (none)
- **Handoffs**: `tree-speculation-numa-drafting.md`
- **Search terms**: NUMA, GPU kernel, flash attention, operator fusion, CUDA graph

### ssm_hybrid
- **Chapters**: (none)
- **Handoffs**: (none active)
- **Search terms**: Mamba, state space model, SSM, hybrid architecture, linear attention, Jamba

### multimodal
- **Chapters**: (none)
- **Handoffs**: `multimodal-pipeline.md`
- **Search terms**: vision-language, multimodal, image understanding, VLM

### training_distillation
- **Chapters**: (none)
- **Handoffs**: `08-doc-to-lora-prototype.md`
- **Search terms**: distillation, LoRA, fine-tuning, RLHF, DPO

### autonomous_research
- **Chapters**: (none)
- **Handoffs**: `autopilot-continuous-optimization.md`
- **Search terms**: autonomous research, automated experimentation, self-improving

### swarm_techniques
- **Chapters**: (none)
- **Handoffs**: (none active)
- **Search terms**: swarm, multi-agent coordination, parallel exploration

### memory_augmented
- **Chapters**: (none)
- **Handoffs**: (none active)
- **Search terms**: episodic memory, working memory, external memory, memory-augmented

## File Locations

All paths are relative to the respective repo root:

- **Chapters**: `epyc-inference-research/docs/chapters/`
- **Active handoffs**: `epyc-root/handoffs/active/`
- **Completed handoffs**: `epyc-root/handoffs/completed/`
- **Experiments**: `epyc-inference-research/docs/experiments/`
- **Research notes**: `epyc-root/research/`
- **Intake index**: `epyc-root/research/intake_index.yaml`
