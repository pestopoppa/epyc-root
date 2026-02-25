# SkillBank: Experience Distillation for Orchestration Memory

**Status**: SPEC COMPLETE — ready for review and refinement
**Created**: 2026-02-14
**Priority**: HIGH — addresses core memory quality bottleneck
**Depends on**: replay-evaluation-harness (complete), episodic store (production)

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Literature & References](#2-literature--references)
3. [Architecture Overview](#3-architecture-overview)
4. [SkillBank Schema](#4-skillbank-schema)
5. [Distillation Pipeline](#5-distillation-pipeline)
6. [Teacher Model Selection](#6-teacher-model-selection)
7. [Retrieval Integration](#7-retrieval-integration)
8. [Failure Lesson Formalization](#8-failure-lesson-formalization)
9. [Recursive Evolution](#9-recursive-evolution)
10. [Replay Harness Integration](#10-replay-harness-integration)
11. [ClaudeDebugger Integration](#11-claudedebugger-integration)
12. [Migration Strategy](#12-migration-strategy)
13. [Implementation Phases](#13-implementation-phases)
14. [Testing Strategy](#14-testing-strategy)
15. [Risk Assessment](#15-risk-assessment)
16. [Documentation Plan](#16-documentation-plan)
17. [Open Questions](#17-open-questions)

---

## 1. Problem Statement

### Current State

The EpisodicStore holds ~102 MB of raw task trajectories in `episodic.db` (SQLite) with FAISS vector search. Each `MemoryEntry` stores the full action, context dict, outcome, and Q-value. The `TwoPhaseRetriever` ranks these by `0.7 * q_value + 0.3 * similarity`, with optional graph-based adjustments from FailureGraph (risk penalty) and HypothesisGraph (confidence multiplier).

**The problem**: Raw trajectories are redundant, noisy, and scale poorly. SkillRL's ablation data quantifies this: replacing structured skills with raw trajectories causes **-28.2%** (ALFWorld) and **-22.5%** (WebShop) performance drops. Our retriever returns raw context blobs that waste prompt tokens and dilute signal.

### What SkillBank Adds

A **derived, compressed knowledge layer** sitting above the episodic store:

```
EpisodicStore (raw trajectories)   ← replay harness reads these (unchanged)
       ↓ periodic distillation
SkillBank (structured skills)      ← inference-time retrieval injects these into prompts
       ↓ recursive evolution
Refined SkillBank                  ← per-category accuracy monitoring triggers updates
```

**Key insight**: The episodic store remains the ground-truth log. SkillBank is a **materialized view** — a lossy compression optimized for inference-time prompt injection. Raw trajectories stay intact for replay evaluation, Q-learning, and audit.

### Expected Impact

- **10-20x token compression** per retrieved memory (structured principle vs raw trajectory)
- **Monotonic escalation reduction**: skills learned from architect-solved tasks propagate to workers
- **Multiplicative gain with replay harness**: replay optimizes retrieval params, SkillBank improves data quality — orthogonal axes

### Relevance to Our Stack

Qwen2.5-7B is our C-tier worker at port 8082 (44 t/s with spec+lookup). SkillRL demonstrates that a 7B model with skill augmentation outperforms GPT-4o (48.0%) and Gemini-2.5-Pro (60.3%) on ALFWorld (89.9%). This validates investing in the memory quality layer over model size — directly relevant since our escalation pipeline routes from 7B workers up to 235B/480B architects.

---

## 2. Literature & References

### Primary Reference

**[SkillRL]** Xia, P., Chen, J., Wang, H., Liu, J., Zeng, K., Wang, Y., Han, S., Zhou, Y., Zhao, X., Chen, H., Zheng, Z., Xie, C., & Yao, H. (2026). *SkillRL: Evolving Agents via Recursive Skill-Augmented Reinforcement Learning.* arXiv:2602.08234. https://arxiv.org/abs/2602.08234

- **Core contribution**: Automated discovery and organization of reusable behavioral patterns (skills) from raw agent trajectories via experience-based distillation, adaptive retrieval, and recursive evolution.
- **Key results**: +12.3% ALFWorld, +25.8% WebShop, +4.0% Search QA over best baselines. 7B model beats GPT-4o.
- **Ablation data**: Removing skill library → -28.2% ALFWorld, -22.5% WebShop. Removing cold-start SFT → -24.7%, -26.2%. Removing hierarchical structure → -13.1%, -11.3%.
- **Repo**: https://github.com/aiming-lab/SkillRL (MIT license, code not yet released as of 2026-02-14)

### Already Integrated

**[ALMA]** Xiong, W. et al. (2026). *ALMA: Adaptive Learning for Memory Architectures.* Referenced in our replay evaluation harness (`orchestration/repl_memory/replay/`). ALMA demonstrated that meta-learned memory configs outperform hand-crafted ones — our replay harness implements this principle.

### Related Work (Context)

**[EvolveR]** Competitive baseline in SkillRL paper. Iterative self-refinement of agent behaviors. SkillRL outperforms by +4% on Search QA through structured abstraction rather than raw trajectory refinement.

**[GRPO]** Shao, Z. et al. (2024). *DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models.* Group Relative Policy Optimization — the RL algorithm used by SkillRL. Relevant context: our system uses TD-learning (Q-value updates) rather than policy gradient RL, so we adapt the skill distillation mechanism without the RL training loop.

**[xRouter]** Referenced in our QScorer cost-penalty design (`cost_penalty_lambda`). Cost-aware routing with quality-gated cost penalties. SkillBank's escalation skills complement xRouter-style cost optimization by reducing the need for expensive model tiers.

**[SimpleMem]** Simple memory baseline in SkillRL. Stores raw trajectories and retrieves by similarity. Equivalent to our current EpisodicStore + TwoPhaseRetriever. SkillRL's SkillBank outperforms SimpleMem+GRPO by +25.8% on WebShop — validates our upgrade path.

### How This Spec Adapts SkillRL

| SkillRL Design | Our Adaptation | Rationale |
|----------------|----------------|-----------|
| RL training (GRPO) | No RL — offline distillation only | We use pre-trained models via llama.cpp, not fine-tuning |
| Single teacher (o3) | Multi-teacher (Opus 4.6 + Codex 5.2 + local Qwen3-235B) | Leverage installed models; teacher diversity |
| Per-epoch evolution | Per-accuracy-threshold evolution | Our system is continuous, not epoch-based |
| SFT cold-start | Skill seeding (bootstrap SkillBank from existing trajectories) | Analogous warm-start without weight updates |
| SkillBank as prompt injection | Same | Direct adoption |
| Failure lessons | Same, formalized with FailureGraph cross-reference | Builds on existing Kuzu graph |

---

## 3. Architecture Overview

### Component Topology

```
                        ┌─────────────────────────┐
                        │   Teacher Models         │
                        │  ┌───────────────────┐   │
                        │  │ Claude Opus 4.6    │   │
                        │  │ Codex 5.2          │   │
                        │  │ Qwen3-235B (local) │   │
                        │  └───────────────────┘   │
                        └──────────┬──────────────┘
                                   │ distillation
                                   ▼
┌──────────────┐    read     ┌──────────────┐    embed     ┌──────────────┐
│ EpisodicStore│────────────▶│ Distiller    │─────────────▶│ SkillBank    │
│  (episodic.db│             │  Pipeline    │              │  (skills.db  │
│   + FAISS)   │             └──────────────┘              │   + FAISS)   │
└──────┬───────┘                                           └──────┬───────┘
       │                                                          │
       │  replay harness reads                  retriever reads   │
       ▼                                                          ▼
┌──────────────┐                               ┌──────────────────┐
│ ReplayEngine │                               │ SkillRetriever   │
│ (offline     │                               │ (runtime, injects│
│  evaluation) │                               │  into prompts)   │
└──────────────┘                               └────────┬─────────┘
                                                        │
                                               ┌────────▼─────────┐
                                               │ TwoPhaseRetriever│
                                               │ (existing, now   │
                                               │  skill-enhanced) │
                                               └──────────────────┘
```

### Separation of Concerns

| Component | Reads | Writes | Frequency |
|-----------|-------|--------|-----------|
| EpisodicStore | — | Raw trajectories | Every task (real-time) |
| Distiller | EpisodicStore, FailureGraph | SkillBank | Periodic batch (daily/weekly) |
| SkillBank | — | Skills (from Distiller) | Batch only |
| SkillRetriever | SkillBank FAISS index | — | Every inference request |
| ReplayEngine | EpisodicStore (raw) | DesignArchive | On-demand (meta-agent) |
| Recursive Evolution | SkillBank, QScorer accuracy | SkillBank (new skills) | Triggered by accuracy drop |

---

## 4. SkillBank Schema

### 4.1 Skill Record Format

Adapted from SkillRL §3.1 (SkillBank structure) with additions for our provenance and effectiveness tracking:

```python
@dataclass
class Skill:
    id: str                          # e.g., "gen_001", "route_012", "fail_003"
    title: str                       # 3-7 words: "Prefer Coder for Refactoring"
    skill_type: str                  # "general" | "routing" | "escalation" | "failure_lesson"
    principle: str                   # 1-3 sentences: actionable strategy
    when_to_apply: str               # Applicability conditions
    task_types: List[str]            # ["code_generation", "debugging", ...] or ["*"] for general
    source_trajectory_ids: List[str] # Provenance: which raw trajectories produced this
    source_outcome: str              # "success" | "failure" | "mixed"
    confidence: float                # 0.0-1.0, updated by recursive evolution
    retrieval_count: int             # How often this skill has been retrieved
    effectiveness_score: float       # Post-retrieval outcome correlation
    embedding: Optional[np.ndarray]  # 1024-dim BGE-large embedding of principle text
    created_at: datetime
    updated_at: datetime
    revision: int                    # Incremented on evolution updates
    deprecated: bool                 # Soft-delete for skills that degrade
    parent_id: Optional[str]         # Lineage: which skill this was evolved from
    teacher_model: str               # Which teacher produced this ("claude-opus-4-6", etc.)
```

SkillRL uses 4 fields (ID, title, principle, when_to_apply). We add provenance (`source_trajectory_ids`, `teacher_model`), lifecycle (`confidence`, `effectiveness_score`, `deprecated`, `revision`), and lineage (`parent_id`). These additions support recursive evolution and effectiveness tracking that SkillRL handles implicitly through RL — since we skip RL, we need explicit tracking.

### 4.2 SQLite Table (in `skills.db`, separate from `episodic.db`)

```sql
CREATE TABLE skills (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    skill_type TEXT NOT NULL CHECK(skill_type IN ('general', 'routing', 'escalation', 'failure_lesson')),
    principle TEXT NOT NULL,
    when_to_apply TEXT NOT NULL,
    task_types TEXT NOT NULL,              -- JSON array
    source_trajectory_ids TEXT NOT NULL,   -- JSON array (provenance)
    source_outcome TEXT NOT NULL,
    confidence REAL DEFAULT 0.5,
    retrieval_count INTEGER DEFAULT 0,
    effectiveness_score REAL DEFAULT 0.5,
    embedding_idx INTEGER,                -- FAISS index position
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    revision INTEGER DEFAULT 1,
    deprecated INTEGER DEFAULT 0,
    parent_id TEXT,
    teacher_model TEXT NOT NULL,
    FOREIGN KEY (parent_id) REFERENCES skills(id)
);

CREATE INDEX idx_skill_type ON skills(skill_type);
CREATE INDEX idx_task_types ON skills(task_types);  -- JSON containment via json_each()
CREATE INDEX idx_confidence_desc ON skills(confidence DESC);
CREATE INDEX idx_deprecated ON skills(deprecated);
CREATE INDEX idx_effectiveness ON skills(effectiveness_score DESC);
```

### 4.3 FAISS Index (separate from episodic FAISS)

- **File**: `orchestration/repl_memory/sessions/skill_embeddings.faiss` + `skill_id_map.npy`
- **Dimensionality**: 1024 (BGE-large-en-v1.5, same as episodic)
- **Index type**: `IndexFlatIP` (same as episodic — corpus will be small, <1000 skills)
- **Embedding source**: Embed `"{title}: {principle}"` via ParallelEmbedder

### 4.4 Why Separate from `episodic.db`

1. **Different lifecycles**: Episodic entries are write-heavy (every task), skills are batch-updated (daily)
2. **Different FAISS indices**: Skill embeddings represent compressed knowledge, not raw task contexts — mixing them would degrade retrieval quality for both
3. **Independent backup/restore**: Can rebuild SkillBank from episodic store at any time (it's derived)
4. **Replay harness isolation**: Replay reads only episodic.db — SkillBank changes don't affect counterfactual evaluation

---

## 5. Distillation Pipeline

### 5.1 Overview

Adapted from SkillRL §3.1 (Experience-based Skill Distillation). SkillRL uses a single teacher (o3) to analyze both success and failure trajectories. We extend this with multi-teacher support and FailureGraph cross-referencing.

```
TrajectoryExtractor.extract_complete(days=25)     # Reuses existing replay infra
    │
    ├── success trajectories ──▶ Success Distillation Prompt ──▶ strategic_skills[]
    │
    ├── failure trajectories ──▶ Failure Lesson Prompt ──────▶ failure_lessons[]
    │
    └── escalation chains ─────▶ Escalation Pattern Prompt ──▶ escalation_skills[]
    │
    ▼
Deduplicate + Merge with existing SkillBank
    │
    ▼
Embed all new/updated skills via ParallelEmbedder
    │
    ▼
Persist to skills.db + skill_embeddings.faiss
```

### 5.2 Distillation Prompts

#### 5.2.1 Success Distillation Prompt

```markdown
# Task: Distill Routing Skills from Successful Trajectories

You are analyzing successful task trajectories from an LLM orchestration system.
Extract reusable strategic patterns that explain WHY these routing decisions worked.

## Trajectories

{trajectories_json}

## Instructions

For each cluster of similar successful patterns, produce a skill record:

```json
{
  "title": "3-7 word imperative title",
  "skill_type": "routing",
  "principle": "1-3 sentence actionable strategy. Be specific about model tiers, task types, and conditions.",
  "when_to_apply": "Precise applicability conditions. Reference task_type, complexity indicators, or context fields.",
  "task_types": ["list", "of", "applicable", "task_types"],
  "source_outcome": "success"
}
```

## Rules

1. Each skill must be ACTIONABLE — a routing decision the system can directly apply
2. Merge similar trajectories into ONE skill (compress, don't enumerate)
3. Preserve specific model names, tier names, and port numbers from the trajectories
4. Reference concrete thresholds from Q-values when available
5. Produce 3-8 skills per batch (fewer, more general is better than many narrow ones)
6. Do NOT produce skills for trivially obvious patterns (e.g., "use the system" is too vague)
```

#### 5.2.2 Failure Lesson Prompt

Adapted from SkillRL §3.1's failure synthesis. SkillRL identifies "the failure point, flawed reasoning, correct alternative, and prevention principles." We add FailureGraph cross-referencing to avoid duplicating known mitigations.

```markdown
# Task: Extract Failure Lessons from Failed Trajectories

Analyze these failed task trajectories and extract structured failure lessons.

## Trajectories

{trajectories_json}

## Existing FailureGraph Context

{failure_graph_summary}

## Instructions

For each failure pattern, produce a failure lesson:

```json
{
  "title": "3-7 word title describing the anti-pattern",
  "skill_type": "failure_lesson",
  "principle": "Structure as: FAILURE POINT: [what went wrong]. FLAWED REASONING: [why the system made this choice]. CORRECT ALTERNATIVE: [what should have happened]. PREVENTION: [actionable rule to avoid recurrence].",
  "when_to_apply": "Conditions that indicate this failure pattern is about to recur",
  "task_types": ["applicable", "types"],
  "source_outcome": "failure"
}
```

## Rules

1. Each lesson must identify the ROOT CAUSE, not just the symptom
2. The PREVENTION field must be a concrete, testable rule
3. Cross-reference with the FailureGraph summary — avoid duplicating known mitigations
4. If a failure has an existing mitigation with success_rate > 0.8, skip it
5. Produce 2-5 lessons per batch
```

#### 5.2.3 Escalation Pattern Prompt

This is our novel extension beyond SkillRL. SkillRL doesn't have a multi-tier model hierarchy, so escalation skill extraction is specific to our architecture.

```markdown
# Task: Extract Escalation Patterns

Analyze trajectories where tasks were escalated from a lower tier to a higher tier.
Identify patterns that could allow the lower tier to handle these tasks directly.

## Escalated Trajectories

{trajectories_json}

## Instructions

For each escalation pattern, produce a skill:

```json
{
  "title": "Imperative title for avoiding this escalation",
  "skill_type": "escalation",
  "principle": "What the lower-tier model should do differently to handle this without escalation. Reference specific reasoning strategies the architect used.",
  "when_to_apply": "Task characteristics that currently trigger escalation but could be handled locally",
  "task_types": ["applicable", "types"],
  "source_outcome": "success"
}
```

## Rules

1. Focus on TRANSFERABLE reasoning — strategies the 7B/30B model can actually execute
2. Don't suggest escalation avoidance for genuinely complex tasks (architecture, novel design)
3. Prioritize high-frequency escalation patterns (most impact from preventing common escalations)
4. Produce 1-4 skills per batch
```

### 5.3 Trajectory Batching

The distiller groups trajectories before sending to the teacher:

```python
@dataclass
class DistillationBatch:
    batch_id: str
    skill_type: str                    # "routing" | "failure_lesson" | "escalation"
    trajectories: List[Trajectory]     # 10-30 trajectories per batch
    task_type_filter: Optional[str]    # None = mixed, or specific type
    existing_skills: List[Skill]       # Already-distilled skills for dedup context

class DistillationPipeline:
    def __init__(
        self,
        teacher: TeacherModel,         # Abstract: Claude, Codex, or local
        store: EpisodicStore,
        skill_bank: SkillBank,
        failure_graph: Optional[FailureGraph] = None,
        batch_size: int = 20,
    ): ...

    def run_full_distillation(
        self,
        days: int = 25,
        max_trajectories: int = 1000,
    ) -> DistillationReport: ...

    def distill_successes(self, trajectories: List[Trajectory]) -> List[Skill]: ...
    def distill_failures(self, trajectories: List[Trajectory]) -> List[Skill]: ...
    def distill_escalations(self, trajectories: List[Trajectory]) -> List[Skill]: ...
    def deduplicate(self, new_skills: List[Skill], existing: List[Skill]) -> List[Skill]: ...
```

### 5.4 Deduplication Strategy

Before inserting new skills, check for semantic overlap with existing ones:

1. Embed new skill principle → search SkillBank FAISS index
2. If `similarity > 0.85` with an existing skill:
   - If same skill_type and overlapping task_types → **merge** (append source_trajectory_ids, update principle if teacher provides better wording, increment revision)
   - If different skill_type → **keep both** (a routing skill and failure lesson can coexist for the same pattern)
3. If `similarity < 0.85` → **insert** as new skill

---

## 6. Teacher Model Selection

### 6.1 Available Teachers

| Teacher | Interface | Strengths | Cost | Latency |
|---------|-----------|-----------|------|---------|
| Claude Opus 4.6 | Anthropic API | Best reasoning, nuanced abstraction | API cost | ~5s/batch |
| Codex 5.2 | Local (installed on machine) | Code-focused reasoning, fast | Free (local) | TBD |
| Qwen3-235B-A22B | Local (:8083) | General reasoning, no API cost | Free (local), 6.75 t/s | ~30s/batch |

### 6.2 Multi-Teacher Strategy

Use different teachers for different skill types:

| Skill Type | Primary Teacher | Rationale |
|------------|-----------------|-----------|
| `routing` | Claude Opus 4.6 | Requires meta-reasoning about model capabilities |
| `failure_lesson` | Claude Opus 4.6 | Root cause analysis needs strong reasoning |
| `escalation` | Codex 5.2 or Qwen3-235B | Understanding what reasoning transfers to smaller models |

### 6.3 TeacherModel Interface

```python
class TeacherModel(Protocol):
    """Abstract interface for distillation teachers."""

    async def distill(
        self,
        prompt: str,
        trajectories: List[Dict[str, Any]],
        max_tokens: int = 4096,
    ) -> str:
        """Send distillation prompt + trajectories, return structured response."""
        ...

    @property
    def model_id(self) -> str: ...

class ClaudeTeacher(TeacherModel):
    """Uses Anthropic API (Opus 4.6)."""
    def __init__(self, api_key: str, model: str = "claude-opus-4-6"): ...

class CodexTeacher(TeacherModel):
    """Uses locally installed Codex 5.2."""
    def __init__(self, binary_path: Path, model_path: Path): ...

class LocalLlamaTeacher(TeacherModel):
    """Uses local llama.cpp server (e.g., Qwen3-235B at :8083)."""
    def __init__(self, base_url: str = "http://localhost:8083"): ...
```

### 6.4 Codex 5.2 Integration Notes

Codex 5.2 is installed but has no existing integration in the codebase. Required:

- [ ] Locate binary and model paths on the machine
- [ ] Determine API interface (OpenAI-compatible? CLI? Python binding?)
- [ ] Write `CodexTeacher` adapter
- [ ] Benchmark distillation quality vs Claude Opus on a calibration set

---

## 7. Retrieval Integration

### 7.1 SkillRetriever Class

Adapted from SkillRL §3.2 (Adaptive Retrieval Strategy). SkillRL uses `sim(e_d, e_s) > 0.4, top-K=6` for task-specific retrieval. We adopt these defaults with the addition of confidence filtering and token budget enforcement.

```python
@dataclass
class SkillRetrievalConfig:
    general_skills_max: int = 6        # Always-included general skills [SkillRL default]
    task_specific_k: int = 6           # Top-K task-specific skills per query [SkillRL default]
    min_similarity: float = 0.4        # Cosine floor for task-specific retrieval [SkillRL default]
    min_confidence: float = 0.3        # Skip deprecated/low-confidence skills [our addition]
    max_prompt_tokens: int = 1500      # Token budget for injected skills [our addition]

@dataclass
class SkillRetrievalResult:
    skill: Skill
    similarity: float
    source: str                        # "general" | "task_specific"

class SkillRetriever:
    def __init__(
        self,
        skill_bank: SkillBank,
        config: SkillRetrievalConfig = SkillRetrievalConfig(),
    ): ...

    def retrieve_for_task(
        self,
        task_embedding: np.ndarray,
        task_type: str,
    ) -> List[SkillRetrievalResult]:
        """
        Two-level retrieval (per SkillRL §3.2):
        1. Load all general skills (skill_type='general', not deprecated)
           sorted by confidence DESC, capped at general_skills_max
        2. FAISS search for task-specific skills (skill_type != 'general')
           filtered by min_similarity, min_confidence, not deprecated
           capped at task_specific_k
        3. Combine, deduplicate, truncate to max_prompt_tokens
        """
        ...

    def format_for_prompt(self, results: List[SkillRetrievalResult]) -> str:
        """Format skills as a markdown section for prompt injection."""
        ...

    def record_retrieval(self, skill_ids: List[str]) -> None:
        """Increment retrieval_count for tracking."""
        ...
```

### 7.2 Prompt Injection Format

Skills are injected into the system prompt as a structured section:

```markdown
## Learned Routing Skills

### General Principles
- **Prefer Coder for Refactoring**: Route refactoring tasks directly to coder_primary (port 8081) unless the task spans >3 files, in which case escalate to architect_coding.
  *Apply when*: task_type is "refactoring" or "code_review"

- **SSM Models Cannot Speculate**: NEVER route Qwen3-Next tasks through speculative decoding. SSM requires consecutive token positions.
  *Apply when*: routing involves ingest_long_context role

### Task-Specific Skills
- **Debug Single-File Bugs Locally**: For debugging tasks affecting a single file with a clear error message, use worker_explore (port 8082) with REPL mode. Escalation to coder is unnecessary for stack-trace-guided fixes.
  *Apply when*: task_type is "debugging", context contains single file path and error trace

### Failure Lessons
- **Avoid Prompt Lookup on Novel Code**: FAILURE: Prompt lookup returns 0 tokens on code generation from scratch (no existing context to match). CORRECT: Use speculative decoding (K=24) for novel generation. PREVENTION: Check if task has existing code context before enabling prompt lookup.
  *Apply when*: task_type is "code_generation", context lacks source file
```

### 7.3 Integration with TwoPhaseRetriever

The SkillRetriever does NOT replace TwoPhaseRetriever. They serve different purposes:

| Component | Returns | Used For |
|-----------|---------|----------|
| TwoPhaseRetriever | Raw memories + Q-values | HybridRouter routing decisions |
| SkillRetriever | Compressed skill principles | Prompt augmentation for model generation |

Integration point: `HybridRouter.route()` continues to use `TwoPhaseRetriever` for the routing decision. The `SkillRetriever` is called separately to augment the prompt sent to whichever model is selected:

```python
class SkillAugmentedRouter:
    """Wraps HybridRouter + SkillRetriever."""

    def __init__(self, router: HybridRouter, skill_retriever: SkillRetriever): ...

    def route_with_skills(self, task_ir: Dict) -> Tuple[List[str], str, str]:
        """
        1. Route via HybridRouter (uses TwoPhaseRetriever internally)
        2. Retrieve skills via SkillRetriever (for prompt injection)
        3. Return (routing, strategy, skill_prompt_section)
        """
        routing, strategy = self.router.route(task_ir)
        embedding = self.router.retriever.embedder.embed(task_ir)
        skills = self.skill_retriever.retrieve_for_task(embedding, task_ir.get("task_type"))
        skill_section = self.skill_retriever.format_for_prompt(skills)
        return routing, strategy, skill_section
```

---

## 8. Failure Lesson Formalization

### 8.1 Current FailureGraph Limitations

The FailureGraph (Ch16) stores:
- `FailureMode` nodes with severity, timestamps
- `Symptom` nodes with regex patterns
- `Mitigation` nodes with success rates
- Relationships: `HAS_SYMPTOM`, `MITIGATED_BY`, `PRECEDED_BY`, `RECURRED_AFTER`

**What it captures**: WHAT failed and WHAT was tried.
**What it lacks**:
- WHY the system made the wrong choice (flawed reasoning)
- WHAT the correct reasoning should have been (correct alternative)
- HOW to prevent recurrence proactively (prevention principle)

### 8.2 Failure Lesson Skill Format

SkillRL's failure lesson format (§3.1) fills these gaps:

```
FAILURE POINT:       What went wrong (maps to FailureMode.description)
FLAWED REASONING:    Why the system chose this path (NEW — not in FailureGraph)
CORRECT ALTERNATIVE: What should have been done (maps to Mitigation.action)
PREVENTION:          Actionable rule to avoid recurrence (NEW — proactive, not reactive)
```

### 8.3 FailureGraph ↔ SkillBank Cross-Reference

When distilling failure lessons, the pipeline queries FailureGraph for context:

```python
def build_failure_context(self, failure_graph: FailureGraph, symptoms: List[str]) -> Dict:
    """Gather FailureGraph context for the distillation prompt."""
    matching = failure_graph.find_matching_failures(symptoms)
    mitigations = failure_graph.get_effective_mitigations(symptoms)
    return {
        "known_failures": [
            {"description": f.description, "severity": f.severity, "recurrence": f.last_seen}
            for f in matching
        ],
        "known_mitigations": [
            {"action": m["action"], "success_rate": m["success_rate"]}
            for m in mitigations
        ],
    }
```

New failure lessons are then stored as skills AND optionally back-propagated to FailureGraph as new Mitigation nodes (with the prevention principle as the action).

### 8.4 Migration Path

- **Phase 1**: Failure lessons stored only in SkillBank (read by SkillRetriever for prompt injection)
- **Phase 2**: Back-propagate to FailureGraph (create Mitigation nodes from prevention principles)
- **Phase 3**: Unify retrieval — GraphEnhancedRetriever considers both FailureGraph risk AND SkillBank failure lessons

---

## 9. Recursive Evolution

### 9.1 Concept

Adapted from SkillRL §3.3 (Recursive Evolution Mechanism). SkillRL monitors per-category success rates during RL training and proposes new skills when accuracy drops. Since we don't do RL training, we trigger evolution from QScorer's per-category accuracy data.

**The escalation reduction dynamic**: Hard tasks escalate → architect solves → success trajectory distilled into escalation skill → skill injected into worker prompts → worker handles similar tasks next time → escalation rate monotonically decreases for recurring task categories.

### 9.2 Trigger Mechanism

```python
@dataclass
class CategoryAccuracy:
    task_type: str
    accuracy: float                # Success rate over sliding window
    sample_count: int
    trend: str                     # "improving" | "stable" | "degrading"

class EvolutionMonitor:
    def __init__(
        self,
        store: EpisodicStore,
        skill_bank: SkillBank,
        accuracy_threshold: float = 0.6,   # Trigger below this
        window_days: int = 7,
        min_samples: int = 10,
    ): ...

    def check_categories(self) -> List[CategoryAccuracy]:
        """Query EpisodicStore for per-task_type success rates over the window."""
        ...

    def identify_degraded_categories(self) -> List[str]:
        """Return task_types where accuracy < threshold and sample_count >= min_samples."""
        ...

    def collect_failure_trajectories(
        self,
        task_types: List[str],
        max_per_type: int = 20,
    ) -> List[Trajectory]:
        """
        Diversity-aware stratified sampling of recent failures.
        (Per SkillRL §3.3: diversity-aware stratified sampling)
        """
        ...
```

### 9.3 Evolution Workflow

```
EvolutionMonitor.identify_degraded_categories()
    │
    ├── No degraded categories → skip (everything healthy)
    │
    └── Degraded categories found
        │
        ▼
    collect_failure_trajectories(degraded_types)
        │
        ▼
    Teacher analyzes gaps:
        - What skills exist for this category?
        - What failures are NOT covered by existing skills?
        - What NEW skills would address these gaps?
        │
        ▼
    Teacher proposes new/revised skills
        │
        ▼
    Deduplicate against existing SkillBank
        │
        ▼
    Insert new skills (confidence = 0.5, initial)
    Update existing skills (increment revision, update principle)
        │
        ▼
    Log evolution event to DesignArchive (audit trail)
```

### 9.4 Frequency and Guards

- **Check frequency**: After every replay evaluation, or on a daily cron
- **Max skills per evolution**: 10 (prevent runaway growth)
- **Cooldown**: No evolution for the same category within 3 days of the last one
- **Total skill cap**: 500 skills (warn at 400). If exceeded, deprecate lowest-confidence skills
- **Human approval**: Evolution runs automatically for skill proposals, but promotion to "general" type requires human sign-off

---

## 10. Replay Harness Integration

### 10.1 No Interference — Complementary Layers

The replay harness and SkillBank operate on different axes:

| Replay Harness | SkillBank |
|----------------|-----------|
| Evaluates `RetrievalConfig` + `ScoringConfig` | Evaluates distilled knowledge quality |
| Reads raw trajectories from EpisodicStore | Reads compressed skills from SkillBank |
| Output: optimal retrieval params | Output: optimal skill library |
| Meta-agent proposes config mutations | Teacher proposes new skills |
| DesignArchive stores config lineage | SkillBank stores skill lineage (parent_id) |

### 10.2 Extended DesignCandidate

Add SkillBank parameters to the design space the meta-agent can mutate:

```python
@dataclass
class SkillBankConfig:
    general_skills_max: int = 6
    task_specific_k: int = 6
    min_similarity: float = 0.4
    min_confidence: float = 0.3
    max_prompt_tokens: int = 1500
    enable_failure_lessons: bool = True
    enable_escalation_skills: bool = True

@dataclass
class DesignCandidate:
    candidate_id: str
    parent_id: Optional[str]
    retrieval_config: RetrievalConfig       # Existing
    scoring_config: ScoringConfig           # Existing
    staged_config: Optional[StagedConfig]   # Existing
    skill_bank_config: Optional[SkillBankConfig] = None  # NEW
    role_overrides: Optional[Dict[str, Dict[str, Any]]] = None
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
```

### 10.3 Replay Engine Extension

The replay engine can optionally simulate skill-augmented routing:

```python
class SkillAwareReplayEngine(ReplayEngine):
    """Extension that injects skills into replay steps."""

    def __init__(self, skill_bank: SkillBank, **kwargs):
        super().__init__(**kwargs)
        self.skill_bank = skill_bank

    def _replay_step(self, trajectory, store, retriever, scorer, skill_config=None):
        step = super()._replay_step(trajectory, store, retriever, scorer)
        if skill_config:
            skills = self.skill_bank.retrieve(trajectory.embedding, trajectory.task_type)
            step.skill_match = any(
                s.principle contains trajectory.routing_decision for s in skills
            )
        return step
```

### 10.4 Extended ReplayMetrics

```python
@dataclass
class ReplayMetrics:
    # ... existing fields ...

    # NEW: Skill-related metrics
    skill_coverage: float = 0.0          # % of trajectories matched by a skill
    skill_routing_agreement: float = 0.0 # % where skill advice aligned with actual routing
    escalation_preventable: float = 0.0  # % of escalations that skills could have prevented
```

### 10.5 Meta-Agent Prompt Extension

Add to `meta_agent_reflect.md`:

```markdown
## SkillBank Statistics

{skill_stats}

## SkillBank Config Ranges

| Parameter | Min | Max | Notes |
|-----------|-----|-----|-------|
| general_skills_max | 2 | 12 | Always-included skills |
| task_specific_k | 2 | 12 | Per-query skill retrieval |
| min_similarity | 0.2 | 0.7 | Skill retrieval cosine floor |
| min_confidence | 0.1 | 0.7 | Minimum skill confidence |
| max_prompt_tokens | 500 | 3000 | Token budget for skills |

You may also propose SkillBankConfig mutations alongside RetrievalConfig and ScoringConfig.
```

---

## 11. ClaudeDebugger Integration

### 11.1 Current State

Commit `6140c64` wired `replay_context` into the debugger as a lazy-loaded 14-day replay summary. Extending for SkillBank:

### 11.2 Skill Diagnostics for Debugger

```python
def build_skill_debug_context(skill_bank: SkillBank) -> str:
    """Build diagnostic summary for ClaudeDebugger."""
    stats = skill_bank.get_stats()
    low_confidence = skill_bank.get_skills(max_confidence=0.3, deprecated=False)
    high_retrieval_low_effect = skill_bank.get_skills(
        min_retrieval_count=10, max_effectiveness=0.3
    )
    unused = skill_bank.get_skills(max_retrieval_count=0, min_age_days=7)

    return f"""
## SkillBank Status
- Total skills: {stats['total']} (general: {stats['general']}, routing: {stats['routing']},
  failure: {stats['failure']}, escalation: {stats['escalation']})
- Deprecated: {stats['deprecated']}
- Avg confidence: {stats['avg_confidence']:.2f}
- Last distillation: {stats['last_distillation']}

## Attention Required
- Low-confidence skills (< 0.3): {len(low_confidence)}
- Frequently retrieved but ineffective: {len(high_retrieval_low_effect)}
- Unused skills (>7 days, 0 retrievals): {len(unused)}
"""
```

### 11.3 Debugger Recommendations

The debugger could surface:
- "Skill `route_012` retrieved 47 times but effectiveness 0.18 — consider deprecating or revising"
- "Category `code_generation` has no failure lessons — distillation coverage gap"
- "3 escalation skills have confidence > 0.8 — test if workers can handle these tasks without escalation"

---

## 12. Migration Strategy

### 12.1 Additive, Not Destructive

SkillBank is a new layer. No existing code is modified in Phase 1:

```
BEFORE:
  Request → HybridRouter(TwoPhaseRetriever) → routing decision → model prompt

AFTER:
  Request → HybridRouter(TwoPhaseRetriever) → routing decision
          → SkillRetriever                   → skill prompt section
          → model prompt + skill section
```

### 12.2 Feature Flag

```python
SKILLBANK_ENABLED = os.environ.get("SKILLBANK_ENABLED", "0") == "1"
```

All SkillBank paths gated behind this flag. Allows A/B comparison.

### 12.3 Rollback Plan

1. Set `SKILLBANK_ENABLED=0` → immediately disables skill injection
2. SkillBank data persists in `skills.db` but is not read
3. No changes to episodic.db, FAISS index, FailureGraph, or HypothesisGraph
4. Replay harness continues to function identically (reads only episodic.db)

---

## 13. Implementation Phases

### Phase 1: SkillBank Core (Foundation)

**Files to create**:
- `orchestration/repl_memory/skill_bank.py` — Skill dataclass, SkillBank class (SQLite + FAISS CRUD)
- `orchestration/repl_memory/skill_retriever.py` — SkillRetriever, SkillRetrievalConfig, format_for_prompt()

**Tests**:
- Schema creation, CRUD operations, FAISS search
- Deduplication logic (similarity threshold)
- Prompt formatting (token budget enforcement)

**Deliverable**: Can store and retrieve skills, format for prompt injection. No distillation yet — skills created manually for testing.

### Phase 2: Distillation Pipeline

**Files to create**:
- `orchestration/repl_memory/distillation/pipeline.py` — DistillationPipeline
- `orchestration/repl_memory/distillation/teachers.py` — TeacherModel protocol, ClaudeTeacher, LocalLlamaTeacher
- `orchestration/repl_memory/distillation/prompts.py` — Prompt templates (success, failure, escalation)
- `orchestration/prompts/skill_distill_success.md` — Success distillation prompt
- `orchestration/prompts/skill_distill_failure.md` — Failure lesson prompt
- `orchestration/prompts/skill_distill_escalation.md` — Escalation pattern prompt

**Tests**:
- Prompt template rendering with mock trajectories
- Teacher response parsing (JSON extraction, validation)
- Deduplication against existing skills
- Batch processing (correct grouping by type)

**Deliverable**: Can distill raw trajectories into skills via teacher model. CLI: `python3 -m orchestration.repl_memory.distillation.pipeline --days 25 --teacher claude`

### Phase 3: Retrieval Integration

**Files to modify**:
- `orchestration/repl_memory/retriever.py` — Add `SkillAugmentedRouter` wrapper
- `src/api/services/memrl.py` — Lazy-load SkillBank + SkillRetriever
- Graph node that builds model prompts — inject skill section

**Tests**:
- End-to-end: store skill → retrieve by embedding → format into prompt
- Token budget enforcement (truncation at max_prompt_tokens)
- Feature flag gating (disabled = no change to prompts)

**Deliverable**: Live inference augmented with skill injection. A/B testable.

### Phase 4: Failure Lesson Formalization

**Files to modify**:
- `orchestration/repl_memory/failure_graph.py` — Add `export_for_distillation()` method
- `orchestration/repl_memory/skill_bank.py` — Add failure lesson specific queries

**Files to create**:
- `orchestration/repl_memory/distillation/failure_bridge.py` — FailureGraph ↔ SkillBank sync

**Deliverable**: Failure lessons flow from trajectories through FailureGraph context into structured skills.

### Phase 5: Recursive Evolution

**Files to create**:
- `orchestration/repl_memory/evolution.py` — EvolutionMonitor, CategoryAccuracy, evolution workflow

**Files to modify**:
- `orchestration/repl_memory/replay/meta_agent.py` — Extended prompt template with skill stats

**Deliverable**: Automated skill library evolution triggered by accuracy degradation.

### Phase 6: Replay Harness Extension

**Files to modify**:
- `orchestration/repl_memory/replay/candidates.py` — Add SkillBankConfig to DesignCandidate
- `orchestration/repl_memory/replay/engine.py` — Optional skill-aware replay
- `orchestration/repl_memory/replay/metrics.py` — Add skill_coverage, skill_routing_agreement, escalation_preventable

**Deliverable**: Replay harness can evaluate SkillBankConfig mutations alongside RetrievalConfig.

### Phase 7: Codex 5.2 Teacher + Multi-Teacher

**Files to create**:
- `orchestration/repl_memory/distillation/codex_teacher.py` — CodexTeacher adapter

**Prerequisite**: Codex 5.2 interface discovery (binary path, API format).

**Deliverable**: Multi-teacher distillation with teacher selection per skill type.

### Phase 8: Effectiveness Tracking + Debugger

**Files to modify**:
- `orchestration/repl_memory/skill_bank.py` — Add effectiveness tracking (post-retrieval outcome correlation)
- ClaudeDebugger integration — `build_skill_debug_context()`

**Deliverable**: Full observability. Skill effectiveness measured, surfaced in debugger.

---

## 14. Testing Strategy

### 14.1 Unit Tests

```
tests/repl_memory/test_skill_bank.py          # CRUD, schema, FAISS, dedup
tests/repl_memory/test_skill_retriever.py      # Retrieval, formatting, token budget
tests/repl_memory/test_distillation.py         # Prompt rendering, response parsing
tests/repl_memory/test_evolution.py            # Monitor, trigger, cooldown
tests/repl_memory/test_failure_bridge.py       # FailureGraph ↔ SkillBank sync
```

### 14.2 Integration Tests

- Full pipeline: extract trajectories → distill → store → retrieve → format
- Replay harness with SkillBankConfig mutations
- Feature flag enable/disable toggles

### 14.3 Calibration Set

Before production distillation, create a calibration set:
1. Manually select 50 representative trajectories (25 success, 15 failure, 10 escalation)
2. Distill with each teacher model
3. Human review of resulting skills (quality, actionability, accuracy)
4. Establish baseline skill quality score for teacher comparison

### 14.4 Safety

- All test files on `/mnt/raid0/` (per filesystem constraints)
- `pytest -n 8` (per pyproject.toml default, never `-n auto`)
- Mock mode for teacher models in tests (no live API calls)
- SkillBank in-memory mode for unit tests (`:memory:` SQLite)

---

## 15. Risk Assessment

### 15.1 Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Skill drift: outdated skills injected into prompts | HIGH | Effectiveness tracking + automatic deprecation below threshold |
| Prompt bloat: too many skills waste context | MEDIUM | Token budget cap (1500 default), priority by confidence |
| Distillation hallucination: teacher invents non-existent patterns | MEDIUM | Source trajectory ID provenance — validate skills against raw data |
| Dedup failure: near-duplicate skills dilute retrieval | LOW | 0.85 cosine threshold + manual review in evolution |
| SkillBank ↔ replay harness coupling | LOW | Separate DBs, separate FAISS indices, feature-flagged |
| Teacher API cost (Claude) | LOW | Batch distillation (daily), not per-request. ~20 batches/day max |
| Skill library growth beyond usefulness | MEDIUM | 500 cap with LRU deprecation, confidence decay |

### 15.2 Failure Modes

1. **Teacher produces invalid JSON** → Parser retries with relaxed regex, falls back to skip batch
2. **FAISS index corruption** → Rebuild from skills.db (embedding_idx is recoverable)
3. **Skill effectiveness negative** → Auto-deprecate after 20 retrievals with effectiveness < 0.2
4. **Evolution runaway** → Max 10 skills/evolution, 3-day cooldown per category, 500 total cap

---

## 16. Documentation Plan

SkillBank is a significant enhancement to the episodic memory architecture and must be documented across multiple chapters and references.

### 16.1 New Chapter: Ch27 — SkillBank & Experience Distillation

**File**: `docs/chapters/27-skillbank-experience-distillation.md`

Full chapter covering:
- Motivation (raw trajectory limitations, SkillRL evidence)
- SkillBank schema and storage design
- Distillation pipeline (teacher selection, prompt design, batching)
- Retrieval integration (SkillRetriever, prompt injection)
- Recursive evolution mechanism
- Interaction with replay harness (complementary, not conflicting)
- Performance metrics and expected impact
- Literature references (SkillRL, ALMA, GRPO, xRouter, SimpleMem)

### 16.2 Chapter Updates

| Chapter | Section to Add/Update | Content |
|---------|----------------------|---------|
| **Ch15 (MemRL System)** | New section: "SkillBank Layer" | Brief overview of SkillBank as a derived knowledge layer above episodic store. Cross-ref to Ch27. Update architecture diagram to show `EpisodicStore → SkillBank` flow. Update "Episodic Memory Architecture" section to note that raw trajectories remain as ground truth while SkillBank provides compressed view. |
| **Ch16 (Graph-Based Reasoning)** | New section: "Failure Lesson Formalization" | How SkillBank failure lessons extend FailureGraph with flawed-reasoning and prevention-principle fields. Cross-reference pipeline from §8.3 of this spec. Update graph schema diagram to show SkillBank back-propagation path. |
| **Ch17 (Memory Seeding)** | New section: "Skill Seeding" | Initial SkillBank bootstrap from existing trajectories as an extension of the seeding philosophy. Relationship between canonical seed examples and initial skill distillation. |
| **Ch18 (Escalation & Routing)** | New section: "Escalation Reduction via Skill Propagation" | The knowledge pipeline dynamic: architect-solved tasks → distilled escalation skills → worker prompt injection → reduced escalation rate. Expected monotonic decrease in escalation for recurring categories. Interaction with THINK_HARDER action. |
| **Ch25 (Cost-Aware Rewards)** | New section: "Skill Effectiveness Scoring" | How skill retrieval outcomes feed into effectiveness tracking. Relationship between QScorer cost penalties and skill-augmented routing cost reduction. |
| **Ch26 (Claude Debugger)** | New section: "Skill Diagnostics" | `build_skill_debug_context()` integration. Debugger recommendations for skill health (low confidence, high retrieval + low effectiveness, unused skills). |

### 16.3 INDEX.md Update

Update the reading paths:

**Agents / Daily Reference table**:
```
| Memory/learning system | [Ch15] + [Ch16] + [Ch17] + [Ch25] + [Ch27] |
```

**Part IV: Intelligence & Learning table** — add row:
```
| 27 | [SkillBank & Experience Distillation](27-skillbank-experience-distillation.md) | Structured skill library, teacher distillation, recursive evolution |
```

**Researchers / Public Showcase** — add entry:
```
7. [Ch27](27-skillbank-experience-distillation.md) SkillBank: experience distillation for routing skill transfer
```

### 16.4 Reference Document Updates

| Document | Update |
|----------|--------|
| `docs/reference/benchmarks/RESULTS.md` | Add SkillBank metrics section when A/B data available |
| `orchestration/model_registry.yaml` | No change (SkillBank doesn't add models) |
| `CLAUDE.md` Component Flow | Update to include `SkillBank(SQLite+FAISS) → SkillRetriever → prompt injection` |
| `CHANGELOG.md` | Entry per implementation phase |

### 16.5 Literature References Section

All chapters touching SkillBank must include or cross-reference:

```markdown
## References

- **[SkillRL]** Xia et al. (2026). "SkillRL: Evolving Agents via Recursive Skill-Augmented
  Reinforcement Learning." arXiv:2602.08234. https://arxiv.org/abs/2602.08234
- **[ALMA]** Xiong et al. (2026). "ALMA: Adaptive Learning for Memory Architectures."
  (Referenced in replay evaluation harness.)
- **[GRPO]** Shao et al. (2024). "DeepSeekMath: Pushing the Limits of Mathematical Reasoning
  in Open Language Models." (RL algorithm used by SkillRL; our system uses TD-learning instead.)
- **[xRouter]** (Referenced in QScorer cost-penalty design.)
- **[SimpleMem]** SkillRL baseline equivalent to raw trajectory retrieval.
  SkillBank outperforms SimpleMem+GRPO by +25.8% on WebShop.
```

Ch27 should contain the full references section. Other chapters should cross-reference Ch27 for the complete bibliography.

---

## 17. Open Questions

1. **Codex 5.2 interface**: What's the API format? OpenAI-compatible? CLI? Need to locate binary and determine integration path before Phase 7.

2. **Optimal distillation frequency**: Daily? Weekly? After every N tasks? SkillRL uses per-epoch during RL training, but our system is continuous. Proposal: daily batch + triggered on accuracy degradation.

3. **Skill confidence initialization**: Should new skills start at 0.5 (neutral) or inherit from source trajectory Q-values? Argument for 0.5: no prior about skill quality. Argument for inherited: if source trajectories had high Q, skill is likely good.

4. **Effectiveness measurement**: How to attribute outcome improvement to a specific skill? Proposal: compare routing accuracy for tasks where a skill was retrieved vs not. Requires sufficient sample size per skill.

5. **Prompt injection position**: Where in the model prompt should skills appear? Before task description? After? In a system prompt section? Position affects attention. Needs A/B testing.

6. **General skill promotion**: When should a task-specific skill be promoted to general? Threshold proposal: retrieved across >= 3 task_types with effectiveness > 0.7.

7. **Multi-teacher consensus**: If Claude and Codex produce different skills from the same trajectories, which wins? Proposal: keep both, let effectiveness tracking decide.

8. **Warm-start interaction**: When `WarmStartProtocol` resets Q-values for a model swap, should skills be recalibrated too? Skills are model-agnostic in principle, but some may reference specific model capabilities (e.g., "route to Qwen2.5-Coder-32B for..."). May need a skill audit on model swap.

---

## Resume Commands

```bash
# Phase 1: Create SkillBank core
cd /mnt/raid0/llm/claude
# Start with skill_bank.py and skill_retriever.py

# Phase 2: Distillation pipeline
# After Phase 1 tests pass
python3 -m orchestration.repl_memory.distillation.pipeline --days 25 --teacher claude --dry-run

# Phase 3: Integration
SKILLBANK_ENABLED=1 python3 scripts/server/orchestrator_stack.py start --dev

# Full test suite
pytest tests/repl_memory/ -n 8 -v
make gates
```

---

## Completion Checklist

- [ ] Phase 1: SkillBank core (schema, CRUD, FAISS, retriever)
- [ ] Phase 2: Distillation pipeline (teachers, prompts, batching)
- [ ] Phase 3: Retrieval integration (prompt injection, feature flag)
- [ ] Phase 4: Failure lesson formalization (FailureGraph bridge)
- [ ] Phase 5: Recursive evolution (monitor, trigger, cooldown)
- [ ] Phase 6: Replay harness extension (SkillBankConfig in candidates)
- [ ] Phase 7: Codex 5.2 teacher + multi-teacher
- [ ] Phase 8: Effectiveness tracking + debugger integration
- [ ] Calibration set evaluated
- [ ] A/B test: skill-augmented vs baseline routing accuracy
- [ ] **Ch27 written**: `docs/chapters/27-skillbank-experience-distillation.md`
- [ ] **Ch15 updated**: SkillBank layer section added
- [ ] **Ch16 updated**: Failure lesson formalization section added
- [ ] **Ch17 updated**: Skill seeding section added
- [ ] **Ch18 updated**: Escalation reduction via skill propagation section added
- [ ] **Ch25 updated**: Skill effectiveness scoring section added
- [ ] **Ch26 updated**: Skill diagnostics section added
- [ ] **INDEX.md updated**: Reading paths, Part IV table, researcher showcase
- [ ] **CLAUDE.md updated**: Component Flow line
- [ ] **CHANGELOG.md**: Entry per phase
- [ ] Literature references included in all updated docs
- [ ] `make gates` passing
