# Retrain Routing Models

**Status**: BLOCKED
**Blocked on**: Accumulate ~500+ routing memories via seeding
**Created**: 2026-05-25

## Context
Episodic memory was reset. The routing classifier weights, GraphRouter GAT
weights, and SkillBank skills were all invalidated. Normal FAISS retrieval
is active as fallback. Once enough new episodic memories are collected
(~500+ routing memories), retrain routing models and re-distill skills.

## Steps

### 1. Verify memory count
```bash
python3 -c "from orchestration.repl_memory.episodic_store import EpisodicStore; s = EpisodicStore(); print(s.count('routing'))"
```

### 2. Retrain routing classifier (MLP)
```bash
python3 scripts/graph_router/extract_training_data.py
python3 scripts/graph_router/train_routing_classifier.py
```

### 3. Retrain GraphRouter (GAT)
```bash
python3 scripts/graph_router/train_graph_router.py --epochs 100
python3 scripts/graph_router/onboard_model.py \
    --role test_new_model \
    --description "Validation model" \
    --port 9999 --tps 60.0 --memory-tier HOT --memory-gb 10
```

### 4. Re-distill SkillBank
```bash
# Dry-run to check trajectory volume
python3 -m orchestration.repl_memory.distillation.pipeline --days 25 --teacher mock --dry-run

# Real distillation (needs ~500 trajectories)
python3 -m orchestration.repl_memory.distillation.pipeline --days 25 --teacher claude

# Verify
sqlite3 /mnt/raid0/llm/tmp/skills.db "SELECT skill_type, COUNT(*) FROM skills GROUP BY skill_type;"
```

### 5. Enable features
Set in `orchestrator_stack.py` or environment:
```bash
export ORCHESTRATOR_ROUTING_CLASSIFIER=1
export ORCHESTRATOR_GRAPH_ROUTER=1
export ORCHESTRATOR_SKILLBANK=1
```

## Research Intake Update — 2026-06-10

### New Related Research
- **[intake-687] "LOLLMS Smart Router Dataset"** (huggingface.co/datasets/ParisNeo/lollms_smart_router_dataset)
  - Relevance: this handoff is data-starved (gated on accumulating ~500+ routing examples). The lollms dataset is **464 labeled query→model-index examples with natural-language rationales** (Apache-2.0) — usable as bootstrap/eval data or a schema/format reference for a generative-router surface.
  - Key technique: synthetic routing-label generation via multi-LLM prompting (TTT Dataset Builder); two reference routers fine-tuned on it (Llama-3.2-1B/3B). Schema is `task_prompt` (task + enumerated candidate-model list with capability descriptions) → `task_solution` (selected index + justification).
  - Delta from current approach: **taxonomy mismatch** — lollms labels are generic public models (GPT-4/Claude-2/CodeLlama/DALL-E/Whisper), NOT our 5-role EPYC taxonomy (frontdoor/architect_general/architect_coding/coder_escalation/worker_explore). Requires a relabel/translation step before training use; the transferable value is the difficulty-tier signal, the prompt-with-candidate-list format, and the rationale field. Verdict worth_investigating — cold-start/reference data, not a drop-in.

### Deep-Dive Refinement (2026-06-12) — correction: lollms is NOT the unblock
**This retrain is NOT short on labels.** The live `episodic.db` already holds **52K+ labeled routing memories**; the real blocker is **missing BGE embeddings** (FAISS was reset; `reembedded.npz` is a frozen 2026-04-15 snapshot). The lollms dataset cannot fix an embedding gap, and it's the wrong surface: it's generative-router SFT *text* (per-row candidate-list → index+rationale), while our controller is a discriminative **BGE-embedding MLP** (1031-d feature → 8 roles). Its "relabel to 5 roles" is structurally infeasible — the label is a *prompt-relative index into a per-row candidate list*, with no stable model→role map — and synthetic labels would pollute the Q-grounded store. **Unblock path = operator BGE re-embed** (`repair_episodic_embeddings.py --repair` → `extract_training_data.py` → `train_routing_classifier.py`), not lollms. Keep lollms parked only as a TTT-synthesis / generative-router reference. Full: `research/deep-dives/2026-06-12-lollms-smart-router-dataset.md`.

### 6. Delete this handoff
