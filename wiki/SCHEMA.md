# Wiki Schema — Living Taxonomy

> Authoritative taxonomy for epyc-root. Extends `research/taxonomy.yaml` with
> new categories and aliases. Updated: 2026-04-07.
>
> The Aliases section maps informal/variant category names used in intake entries
> to canonical categories, allowing `validate_intake.py` to accept both forms
> without requiring bulk edits to `intake_index.yaml`.

## Categories

### Core Inference Optimization

| Key | Label | Description | Related Chapters |
|-----|-------|-------------|------------------|
| `speculative_decoding` | Speculative Decoding | Draft-verify paradigms including tree, linear, self-speculation, and hierarchical approaches | 01, 03, 05, 10 |
| `moe_optimization` | MoE Optimization | Mixture-of-Experts inference optimization including expert pruning, routing, and offloading | 02 |
| `kv_cache` | KV Cache Optimization | KV cache compression, quantization, eviction, shared prefix caching, paged attention | 04 |
| `quantization` | Quantization | Weight and activation quantization, mixed-precision, calibration methods | — |
| `hardware_optimization` | Hardware Optimization | GPU/CPU kernel optimization, NUMA-aware scheduling, operator fusion, flash attention | — |

### Serving & Systems

| Key | Label | Description | Related Chapters |
|-----|-------|-------------|------------------|
| `inference_serving` | Inference Serving | Serving infrastructure, batching, scheduling, continuous batching, disaggregated serving | — |
| `local_inference` | Local Inference | On-device inference with GGUF, llama.cpp, node-llama-cpp, and local model serving | — |

### Routing & Evaluation

| Key | Label | Description | Related Chapters |
|-----|-------|-------------|------------------|
| `cost_aware_routing` | Cost-Aware Routing | Request routing based on cost, latency, quality tradeoffs across model tiers | 08 |
| `routing_intelligence` | Routing Intelligence | Classifier-based routing, difficulty estimation, factual risk scoring, delegation policy | — |
| `benchmark_methodology` | Benchmark Methodology | Evaluation frameworks, scoring methods, dataset construction, statistical rigor | 06, 07 |

### Agent & Architecture

| Key | Label | Description | Related Chapters |
|-----|-------|-------------|------------------|
| `agent_architecture` | Agent Architecture | Multi-agent systems, tool use, REPL-driven code generation, orchestration patterns | 09 |
| `autonomous_research` | Autonomous Research | AI-driven research workflows, automated experimentation, self-improving systems | — |
| `swarm_techniques` | Swarm Techniques | Multi-agent swarm coordination, parallel exploration, ensemble methods | — |
| `memory_augmented` | Memory-Augmented Models | External memory, episodic memory, working memory integration for LLMs | — |

### Context & Compression

| Key | Label | Description | Related Chapters |
|-----|-------|-------------|------------------|
| `context_extension` | Context Extension | Long-context methods including YaRN, RoPE scaling, sliding window, and sparse attention | — |
| `context_management` | Context Management | Context compaction, session folding, token compression, tool output filtering | — |
| `ssm_hybrid` | SSM & Hybrid Architectures | State-space models (Mamba), SSM-attention hybrids, linear attention variants | — |

### Training & Distillation

| Key | Label | Description | Related Chapters |
|-----|-------|-------------|------------------|
| `training_distillation` | Training & Distillation | Knowledge distillation, fine-tuning, LoRA, RLHF, DPO, and training optimization | — |
| `reinforcement_learning` | Reinforcement Learning | RL training, PPO, GRPO, reward modeling, bandit methods for LLM optimization | — |

### Multimodal & Domain

| Key | Label | Description | Related Chapters |
|-----|-------|-------------|------------------|
| `multimodal` | Multimodal | Vision-language models, image understanding, multimodal reasoning, TTS, ASR | — |
| `document_processing` | Document Processing | PDF parsing, OCR, document extraction, table recognition, reading order analysis | — |
| `formal_verification` | Formal Verification | Theorem proving, Lean 4, formal methods for code and mathematical correctness | — |

### Knowledge & Retrieval

| Key | Label | Description | Related Chapters |
|-----|-------|-------------|------------------|
| `knowledge_management` | Knowledge Management | LLM-compiled knowledge bases, persistent wikis, research intake, cross-referencing | — |
| `rag_alternatives` | RAG Alternatives | Non-retrieval approaches to knowledge integration — compilation, persistent synthesis | — |
| `retrieval_augmented_decoding` | Retrieval-Augmented Decoding | RAG, retrieval-augmented generation, and grounded decoding techniques | — |
| `search_retrieval` | Search & Retrieval | Hybrid search, BM25, vector search, re-ranking, and retrieval pipelines | — |

### Tools & Interfaces

| Key | Label | Description | Related Chapters |
|-----|-------|-------------|------------------|
| `tool_implementation` | Tool Implementation | CLI tools, plugins, and developer tooling for LLM workflows and agent systems | — |

### Research & Analysis

| Key | Label | Description | Related Chapters |
|-----|-------|-------------|------------------|
| `mechanistic_interpretability` | Mechanistic Interpretability | Sparse autoencoders, circuit analysis, feature visualization in neural networks | — |
| `emotion_psychology` | Emotion & Psychology | Emotion/personality in LLMs, cognitive science of language models, user modeling | — |
| `llm_prompting` | LLM Prompting | Prompt engineering, prompt sensitivity, instruction following, brevity constraints | — |
| `safety` | Safety | LLM safety, alignment, jailbreak prevention, adversarial robustness | — |

## Aliases

Maps informal/variant category names to canonical categories above.

| Alias | Maps To |
|-------|---------|
| `kv_cache_optimization` | `kv_cache` |
| `sparse_autoencoders` | `mechanistic_interpretability` |
| `benchmark` | `benchmark_methodology` |
| `eval_methodology` | `benchmark_methodology` |
| `llm_evaluation` | `benchmark_methodology` |
| `evaluation` | `benchmark_methodology` |
| `reasoning_evaluation` | `benchmark_methodology` |
| `architecture_comparison` | `benchmark_methodology` |
| `survey` | `benchmark_methodology` |
| `reasoning` | `cost_aware_routing` |
| `chain_of_thought` | `cost_aware_routing` |
| `rag` | `retrieval_augmented_decoding` |
| `information_retrieval` | `retrieval_augmented_decoding` |
| `finetuning` | `training_distillation` |
| `post_training` | `training_distillation` |
| `prompt_optimization` | `llm_prompting` |
| `prompt_sensitivity` | `llm_prompting` |
| `prompt_manipulation` | `llm_prompting` |
| `prompting` | `llm_prompting` |
| `instruction_following` | `llm_prompting` |
| `cuda_inference` | `hardware_optimization` |
| `gpu_inference` | `hardware_optimization` |
| `inference_speed` | `hardware_optimization` |
| `multi_agent_systems` | `swarm_techniques` |
| `persona` | `emotion_psychology` |
| `nlp_cognitive_science` | `emotion_psychology` |
| `llm_safety` | `safety` |
| `constrained_decoding` | `speculative_decoding` |
| `rl_training` | `reinforcement_learning` |
| `rl_alternative` | `reinforcement_learning` |
| `theorem_proving` | `formal_verification` |
| `small_model_deployment` | `local_inference` |
| `web_systems` | `inference_serving` |

## Conformance (added 2026-06-20 — OKF-inspired, intake-710/711)

This section adopts the two genuinely-new conventions surfaced by the Open
Knowledge Format (OKF v0.1, Google Cloud) deep-dive. The other four OKF
conventions were already satisfied by existing infrastructure (see *Rejected as
already-covered* below).

**Schema version stamp.** This taxonomy is at `schema_version: "1.0"`. The
version is declared here so that parallel agents and cross-repo consumers can
detect schema drift — if the category set, alias map, or conformance contract
changes in a backward-incompatible way, bump this number. Treat it as the
authoritative OKF-style version stamp for the wiki taxonomy and the intake index
schema it backs.

**Permissive-consumption contract (the genuinely-new adoption).** Consumers of
intake entries MUST preserve unknown/extra keys and MUST NOT reject an entry for
carrying fields beyond the required set. New optional fields may be added
forward-compatibly without coordinating a flag-day across parallel agents. This
is already the de-facto behavior of
`.claude/skills/research-intake/scripts/validate_intake.py` — it only flags
MISSING required fields (and invalid enum values), and never rejects an entry for
carrying additional keys. This section CODIFIES that behavior as an intentional
contract so a future validator change does not silently regress it: any change
that would cause the validator to reject entries on the basis of extra/unknown
fields is a conformance break and must be rejected in review.

**Rejected as already-covered.** The following OKF conventions were evaluated and
deliberately NOT adopted because existing infrastructure already provides the
equivalent capability:

- Reserved `index.md` — we already have `wiki/INDEX.md` as a
  progressive-disclosure index.
- Per-bundle `log.md` change history — we use per-file dated "Research Intake
  Update" sections, giving change history at finer (per-file) granularity.
- `#Schema` / `#Examples` / `#Citations` heading renames — our existing
  Summary / Key-Findings / Source-References headings are equivalent in role.
- A bespoke HTML force-directed graph visualizer — GitNexus `wiki` / `cypher`
  already cover graph visualization of symbols and relationships.

Full OKF analysis lives in intake-710/711. This is a conventions-adoption, not a
tooling import: OKF's enrichment agent is BigQuery-coupled and therefore out of
scope for the self-hosted EPYC stack.
