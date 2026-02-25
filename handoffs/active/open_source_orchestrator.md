# Open-Source Model-Agnostic Local Orchestrator — Future Revisit

**Created**: 2026-02-02
**Status**: STUB (future work)
**Priority**: Low — revisit after MemRL routing is validated

## Concept

Generic model-agnostic local orchestrator with auto-benchmarking + MemRL routing as open-source project. Nothing like this exists — RouteLLM is closest (binary API routing) but doesn't do local multi-model + mode selection + RL.

## Market Gap Analysis

| Existing Tool | What It Does | What It Lacks |
|---------------|-------------|---------------|
| RouteLLM | Binary API routing (strong/weak) | No local inference, no mode selection, no RL |
| LiteLLM | API gateway / load balancer | No quality-aware routing, no benchmarking |
| vLLM | High-throughput serving | Single model, no routing, no RL |
| Ollama | Easy local inference | No multi-model orchestration, no routing |
| LM Studio | GUI local inference | No programmatic routing, no benchmarking |
| Open Interpreter | Code execution agent | Single model, no comparative routing |

**Unique value**: Auto-discovers models → benchmarks them → learns optimal routing via RL → adapts to hardware.

## Core Abstractions to Generalize

### 1. Model Registry (from `orchestration/model_registry.yaml`)
- Abstract: YAML schema for model capabilities, paths, compatible drafts, launch commands
- Generalize: Auto-detect GGUF/HF models, infer capabilities from metadata
- Scale: 64GB Mac (2-3 models) → 1.13TB server (10+ models)

### 2. Benchmark Adapters (from `scripts/benchmark/dataset_adapters.py`)
- Abstract: Pluggable adapters for HuggingFace datasets
- Generalize: Standard interface `BaseAdapter.sample() → list[QuestionDict]`
- Include: Built-in suites (math, code, reasoning, tool-use) + custom YAML

### 3. Reward Computation (from `seed_specialist_routing.py`)
- Abstract: Comparative evaluation framework
- Generalize: Run same question through multiple model+mode combos, compute rewards
- Simplify: Don't need full orchestrator API — can test models directly

### 4. Q-Learning Router (from MemRL system)
- Abstract: State = (task_type, complexity, context_length) → Action = (model, mode)
- Generalize: Hardware-aware cost model (RAM, GPU VRAM, tokens/sec)
- Default: Sensible heuristic routing before RL has enough data

### 5. Mode Selection
- Direct: Send prompt, get response
- React: Tool-augmented generation (calculator, search, code exec)
- REPL: Iterative code execution with feedback
- Delegation: Multi-model pipeline (planner → executor → verifier)

## Architecture Sketch

```
┌─────────────────┐
│  User Request    │
└────────┬────────┘
         ▼
┌─────────────────┐
│  Task Classifier │ ← Lightweight (frontdoor model or rule-based)
└────────┬────────┘
         ▼
┌─────────────────┐
│   RL Router     │ ← Q-table: (task_features) → (model, mode)
│   (or heuristic │    Falls back to heuristic if < N episodes
│    if cold)     │
└────────┬────────┘
         ▼
┌─────────────────┐
│  Execution Layer │ ← llama.cpp / vLLM / Ollama / API backend
│  + Mode Handler  │    Mode: direct / react / repl / delegation
└────────┬────────┘
         ▼
┌─────────────────┐
│  Response + Log  │ ← Log for offline RL training
└─────────────────┘
```

## Hardware Scaling

| Target | RAM | Models | Strategy |
|--------|-----|--------|----------|
| MacBook 32GB | 32GB | 1-2 small | Single model, mode selection only |
| Desktop 64GB | 64GB | 2-3 medium | Frontdoor + specialist |
| Workstation 128GB | 128GB | 3-5 models | Full routing with MoE |
| Server 256GB+ | 256GB+ | 5-10 models | Multi-tier with workers |
| EPYC 1TB+ | 1TB+ | 10+ models | Full orchestration stack |

## What Needs Generalization from Current System

1. Remove hardcoded Qwen model assumptions
2. Abstract llama.cpp launch commands (support vLLM, Ollama, API backends)
3. Make MoE expert reduction configurable per-architecture
4. Generalize speculative decoding compatibility checking
5. Abstract port topology (current 8080-8090 is fixed)
6. Make benchmark suites pluggable without code changes
7. Package as pip-installable CLI tool

## Potential Name Ideas
- `localroute` — local model routing
- `modelswarm` — multi-model orchestration
- `inferflow` — inference workflow
- `routellm-local` — explicit positioning vs RouteLLM

## Next Steps (When Revisiting)
1. Validate MemRL routing produces measurable quality improvement
2. Extract core abstractions into standalone package
3. Write integration tests against Ollama + llama.cpp backends
4. Publish on PyPI with minimal deps
5. Write blog post with benchmarks showing routing > single-model
