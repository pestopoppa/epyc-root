# Research Taxonomy

The taxonomy (`research/taxonomy.yaml`) defines 24 categories for classifying research material.

## Categories

| Category | Description |
|----------|-------------|
| `speculative_decoding` | Draft-verify paradigms: tree, linear, self-spec, hierarchical |
| `moe_optimization` | Expert pruning, routing, offloading for MoE models |
| `retrieval_augmented_decoding` | RAG, retrieval-augmented generation |
| `kv_cache` | Cache compression, quantization, eviction, paged attention |
| `quantization` | Weight/activation quantization, mixed-precision |
| `benchmark_methodology` | Evaluation frameworks, scoring, dataset construction |
| `cost_aware_routing` | Cost/latency/quality tradeoff routing |
| `agent_architecture` | Multi-agent systems, tool use, orchestration |
| `context_extension` | YaRN, RoPE scaling, sliding window, sparse attention |
| `inference_serving` | Batching, scheduling, continuous batching, disaggregated serving |
| `memory_augmented` | External/episodic/working memory for LLMs |
| `training_distillation` | Distillation, LoRA, RLHF, DPO |
| `multimodal` | Vision-language, image understanding |
| `routing_intelligence` | Classifier routing, difficulty estimation, delegation |
| `hardware_optimization` | Kernel optimization, NUMA, operator fusion |
| `ssm_hybrid` | Mamba, SSM-attention hybrids, linear attention |
| `autonomous_research` | AI-driven research workflows |
| `swarm_techniques` | Multi-agent swarm coordination |
| `document_processing` | PDF parsing, OCR, table recognition, reading order for LLM pipelines |
| `knowledge_management` | LLM-compiled knowledge bases, persistent wikis, research intake, knowledge hygiene |
| `rag_alternatives` | Non-retrieval approaches to knowledge integration — compilation, persistent synthesis |
| `tool_implementation` | CLI tools, plugins, developer tooling for LLM workflows and agent systems |
| `local_inference` | On-device inference with GGUF, llama.cpp, node-llama-cpp, local model serving |
| `search_retrieval` | Hybrid search, BM25, vector search, re-ranking, retrieval pipelines |

## Usage

Each intake entry has a `categories` list (1 or more values from the keys above). The taxonomy drives cross-referencing: each category maps to related chapters in `related_chapters`.

## Adding Categories

Add new entries to `research/taxonomy.yaml`. Run `scripts/validate_intake.py` to verify integrity.
