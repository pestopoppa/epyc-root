# SkillsBench Methodology Adoption — Skill Transfer Eval Suite

**Status**: COMPLETED (2026-03-03)
**Created**: 2026-03-03
**Priority**: P2 — depends on seeding infrastructure stability
**Effort**: ~1 developer-day (see sizing below)
**Source**: [SkillsBench (arxiv.org/pdf/2602.12670)](https://arxiv.org/pdf/2602.12670)

## Research Review

### SkillsBench: Benchmarking Agent Skills Across Diverse Tasks
**Authors:** Xiangyi Li, Wenbo Chen, Yimin Liu et al. (40+ authors)

**Scope constraint**: Methodology adoption only — SkillsBench's 87 tasks require Docker/Harbor containers with baked-in data files (Excel sheets, CVE repos, video files) and cannot run in our text-based seeding pipeline. No flat dataset or HuggingFace export exists. We adopt SkillsBench's *methodology* (measuring per-skill cross-domain transfer and regression on model swaps) by writing our own `skill_transfer` question suite and post-hoc analysis scripts.

**Orchestrator Relevance: HIGH.** Our orchestrator routes tasks to specialist workers. SkillsBench provides a principled methodology for measuring whether our worker skills (REPL, web research, code review) actually transfer across problem domains. Informs:
- **Seeding validation**: Benchmark worker outputs against skill categories
- **Routing decisions**: Quantify which workers have generalizable vs narrow skills
- **Skill regression testing**: Detect when model updates degrade cross-domain transfer

### Key Insight
SkillsBench reveals that agent skills are NOT uniformly transferable. Some capabilities (basic tool use, file I/O) transfer well, while others (domain-specific reasoning, multi-step planning) are highly task-dependent. This directly impacts our routing strategy — we may be over-routing to "generalist" workers when specialists are needed, or vice versa.

### Domain Coverage

| SkillsBench Domain | Our Coverage | Why |
|---|---|---|
| Software Engineering | Strong | coder, debugbench, livecodebench, REPL worker |
| Mathematics | Strong | math (GSM8K/MATH-500), gpqa |
| Web/Research | Good | web_research suite (50q), worker_explore |
| Text/NLP | Partial | general, instruction_precision |
| Healthcare, Manufacturing, Cyber, Robotics, Energy, OS | None | No workers or tools — skip |

## References

- [SkillsBench paper](https://arxiv.org/pdf/2602.12670)
- [SkillsBench GitHub](https://github.com/THUDM/SkillsBench)
- Local file paths:
  - `dataset_adapters.py`: `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/dataset_adapters.py` (line 50: `YAML_ONLY_SUITES`)
  - `seeding_types.py`: `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/seeding_types.py` (line 62: `DEFAULT_SUITES`)
  - `seeding_checkpoint.py`: `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/seeding_checkpoint.py`
  - `web_research.yaml`: `/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/debug/web_research.yaml`
  - `question_pool.py`: `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/question_pool.py`

## Implementation Steps

### Step 1. Create `skill_transfer` YAML suite

**File**: `/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/debug/skill_transfer.yaml`

Design: 4 skill categories × 3 domains × ~3 questions = ~36 questions. Follow `web_research.yaml` format conventions.

**Skill categories** (mapped to real orchestrator capabilities):
- `structured_extraction` — extract key-value data from: Python traceback (code), prose paragraph (NLP), web page excerpt (web)
- `error_diagnosis` — identify root cause: broken Python (code), wrong derivation (math), contradictory claims (research)
- `multi_step_planning` — decompose into steps: code refactor (code), research synthesis (web), proof sketch (math)
- `format_transformation` — convert between formats: CSV→JSON (code), bullets→table (NLP), URLs→bibliography (web)

Each question MUST have `skill` and `domain` fields for analysis grouping. Scoring: `f1` with threshold `0.5` (matching `web_research` suite).

**Important**: extra YAML fields (`skill`, `domain`) are dropped during pool build (`question_pool.py` lines 92-103 only keeps standard fields: `id`, `prompt`, `expected`, `category`). Analysis scripts must join against the YAML source file by `question_id` to recover `skill`/`domain`.

### Step 2. Register suite in seeding pipeline

Two one-line additions:

1. Add `"skill_transfer"` to `YAML_ONLY_SUITES` in `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/dataset_adapters.py` (line 50):
   ```python
   YAML_ONLY_SUITES = {"agentic", "long_context", "mode_advantage", "mode_advantage_hard", "skill_transfer", "web_research"}
   ```

2. Add `"skill_transfer"` to `DEFAULT_SUITES` in `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/seeding_types.py` (line 62, medium tier after `"agentic"`):
   ```python
   # Medium difficulty
   "hotpotqa", "simpleqa", "agentic", "skill_transfer", "coder",
   ```

3. Rebuild pool: `cd /mnt/raid0/llm/epyc-inference-research/scripts/benchmark && python question_pool.py --build`

### Step 3. Post-hoc skill transfer analysis script

**File**: `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/analyze_skill_transfer.py`

Structure:
- Reads checkpoint JSONL from `benchmarks/results/eval/`
- Joins against `skill_transfer.yaml` by `question_id` to recover `skill`/`domain` (since pool drops these fields)
- Outputs: skill × domain pass-rate matrix, one table per action (`SELF:direct`, `SELF:repl`, `ARCHITECT`)
- CLI: `python analyze_skill_transfer.py [--checkpoint-dir PATH] [--yaml PATH]`
- Must handle empty/partial data gracefully ("no skill_transfer data found")

### Step 4. Model swap regression script

**File**: `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/skill_transfer_regression.py`

Structure:
- CLI: `--before DIR --after DIR [--threshold 0.10]`
- Compares two checkpoint sets, flags per-skill cells where pass rate drops > threshold
- Output: diff table with `REGRESSED` markers
- Ties into handoffs #02 (Nanbeige) and #04 (MiroThinker) — their model swap checkpoints provide before/after data

## Out of Scope

- Running SkillsBench Docker tasks (requires Harbor framework + containerized data)
- Covering Healthcare, Manufacturing, Cyber, Robotics, Energy, OS domains (no workers/tools)
- Building a runtime skill scoring module (analysis is post-hoc only)
- Full SkillsBench-scale evaluation (87 tasks × 3 conditions × 5 trials)

## Acceptance Criteria

- [x] **AC1**: YAML file exists at `benchmarks/prompts/debug/skill_transfer.yaml`, 36 questions (4 skills × 3 domains × 3 each), all have `skill`/`domain` fields, pool rebuild succeeds (53,231 questions)
- [x] **AC2**: Suite registered in `YAML_ONLY_SUITES` (both research + orchestrator repos) and `DEFAULT_SUITES`
- [x] **AC3**: `analyze_skill_transfer.py` runs end-to-end, handles 0-result gracefully (prints "No skill_transfer data found." and exits 0)
- [x] **AC4**: `skill_transfer_regression.py` runs end-to-end with two checkpoint dirs, exits 0 even if no data
- [ ] **AC5**: After one seeding run with `--suites skill_transfer`, analysis script produces non-empty skill × domain matrix (requires live orchestrator)

### Test Plan

1. Create YAML → `python -c "import yaml; d=yaml.safe_load(open('skill_transfer.yaml')); assert len(d['questions'])>=36; assert all('skill' in q and 'domain' in q for q in d['questions'])"`
2. Pool rebuild → `python question_pool.py --build` exits 0 and includes `skill_transfer` in output
3. Analysis empty case → `python analyze_skill_transfer.py --checkpoint-dir /tmp/empty` exits 0
4. Regression empty case → `python skill_transfer_regression.py --before /tmp/empty --after /tmp/empty` exits 0
5. End-to-end → run seeding with `--suites skill_transfer -n 5`, then run analysis script

## Effort Sizing

| Task | Estimate |
|---|---|
| YAML creation (36 questions with cross-domain skill parallelism) | ~2-3 hours |
| Registration (two one-liners + pool rebuild) | 5 minutes |
| Analysis script | 2-3 hours |
| Regression script | 1-2 hours |
| **Total** | **~1 developer-day** |

Seeding populates results automatically as part of normal runs once registered.

## Future Work: Native SkillsBench Docker Evaluation

When the orchestrator reaches production readiness (stable tool dispatch, reliable containerized execution), revisit running SkillsBench's native 87 Docker-containerized tasks via the Harbor framework. These are interactive agent workflows — reading Excel files, fixing CVEs, processing videos — that test real-world tool orchestration in ways our text-based suites cannot. This would require:
- Harbor framework integration or equivalent Docker task runner
- Mapping SkillsBench's agent API to our orchestrator's tool dispatch
- Subset selection (focus on Software Engineering + Data Analysis domains first)

Track as a separate handoff when the time comes.

## Implementation Notes (2026-03-03)

### Bonus fix: Pool builder scoring propagation
The pool builder (`question_pool.py`) had a latent bug: per-question `scoring_method` defaulted to `"exact_match"` even when the YAML top-level specified `scoring_method: f1`. Fixed by reading top-level defaults and using them as per-question fallbacks. This also fixed `web_research.yaml` scoring (50 questions were silently using `exact_match` instead of `f1`).

### Orchestrator repo registration
The handoff only mentioned adding `skill_transfer` to the research repo's `dataset_adapters.py`. The orchestrator repo has its own copy — added `skill_transfer` to both.

### Files Modified

| File | Repo | Changes |
|------|------|---------|
| `scripts/benchmark/question_pool.py` | research | Top-level `scoring_method`/`scoring_config` propagation |
| `benchmarks/prompts/debug/skill_transfer.yaml` | research | **NEW** — 36 questions, 4 skills × 3 domains |
| `scripts/benchmark/dataset_adapters.py` | research | `"skill_transfer"` added to `YAML_ONLY_SUITES` |
| `scripts/benchmark/dataset_adapters.py` | orchestrator | `"skill_transfer"` added to `YAML_ONLY_SUITES` |
| `scripts/benchmark/seeding_types.py` | orchestrator | `"skill_transfer"` added to `DEFAULT_SUITES` |
| `scripts/benchmark/analyze_skill_transfer.py` | orchestrator | **NEW** — skill × domain pass-rate analysis |
| `scripts/benchmark/skill_transfer_regression.py` | orchestrator | **NEW** — before/after regression detection |

## Reset Compatibility

All deliverables (YAML suite, analysis scripts, suite registration) are permanent infrastructure. Episodic memory resets only clear MemRL Q-values. Checkpoint files survive resets and can be compared across any pair (pre/post reset, model A vs B). Fully compatible with the current "fix bugs → reset → reseed" cycle.
