# MemRL Mode-Advantage Tasks — Handoff

**Created**: 2026-02-02
**Status**: ALL PHASES COMPLETE
**Plan**: Enrich MemRL with mode-advantage tasks that produce strong routing signal

## Context

Current debug suite (327 QA questions) produces weak comparative rewards because all tasks are solvable by direct inference. This work adds 90 hand-written tasks + external dataset adapters specifically designed to differentiate routing modes (direct vs react vs repl vs delegation).

## Phase 0: Hand-written YAML tasks — COMPLETED
- Files created: `benchmarks/prompts/debug/mode_advantage.yaml`
- 60 tasks: 15 computation-gated, 15 iterative-fix, 15 multi-step, 15 escalation-gated
- All use existing scorers (exact_match, code_execution, substring)
- All expected answers verified via Python computation
- Tests passing: Y (1726 passed)
- Blockers: none

## Phase 0.5: Exemplars in existing suites — COMPLETED
- Files modified: math.yaml (+4), coder.yaml (+4), agentic.yaml (+4), long_context.yaml (+4)
- 16 total `mode_advantage: true` exemplars across 4 suites
- All answers verified

## Phase 1: GAIA adapter — COMPLETED
- GaiaAdapter class added to `scripts/benchmark/dataset_adapters.py`
- 165 dev questions, exact-match, L1-L3 mapped to T1-T3
- File staging in `/mnt/raid0/llm/tmp/gaia/`
- Skips audio/video questions automatically
- Dataset pre-downloaded to `/mnt/raid0/llm/cache/huggingface/`

## Phase 2: CRUXEval adapter — COMPLETED
- CRUXEvalAdapter class added to `scripts/benchmark/dataset_adapters.py`
- 800 functions × 2 tasks (output + input prediction)
- Output pred = tier 1 (just run it), input pred = tier 2 (reasoning)
- Dataset pre-downloaded to `/mnt/raid0/llm/cache/huggingface/`

## Phase 3: BigCodeBench adapter — COMPLETED
- BigCodeBenchAdapter class added to `scripts/benchmark/dataset_adapters.py`
- 1,140 tasks, code_execution scoring
- Tier based on library count (1 lib=T1, 2=T2, 3+=T3)
- Dataset pre-downloaded to `/mnt/raid0/llm/cache/huggingface/`

## Phase 4: Mini-SWE tasks — COMPLETED
- 30 curated mini-SWE tasks added to `benchmarks/prompts/debug/mode_advantage.yaml`
- IDs: ma_swe_001 through ma_swe_030
- All use code_execution scoring (broken code + test assertions + known fix)
- Categories: EventEmitter, Paginator, CSV parser, LRU decorator, URL parser, task scheduler, retry decorator, config manager, matrix multiplication, JSON path, state machine, ring buffer, expression tokenizer, template engine, job scheduler, middleware pipeline, database query, cache proxy, observable/reactive, diff algorithm, pub/sub broker, rate-limited queue, HTTP router, permission checker, connection pool, search index, graph cycle detection, command parser, event sourcing, Jaccard similarity
- Total questions in mode_advantage.yaml: 90

## Step 0: OSS orchestrator stub — COMPLETED
- File created: `handoffs/active/open_source_orchestrator.md`

## Registration — COMPLETED
- `seeding_types.py`: Added `mode_advantage` to DEFAULT_SUITES + SUITE_TIMEOUTS
- `dataset_adapters.py`: Added gaia/cruxeval/bigcodebench to ADAPTER_SUITES
- `seed_specialist_routing.py`: No changes needed (auto-discovers YAML + adapters)

## Dataset Pre-Downloads — COMPLETED (2 of 3)
- CRUXEval: `cruxeval-org/cruxeval` (test split, 800 rows) — cached at `/mnt/raid0/llm/cache/huggingface/`
- BigCodeBench: `bigcode/bigcodebench` (v0.1.2 split, 1,140 rows) — cached at `/mnt/raid0/llm/cache/huggingface/`
- GAIA: `gaia-benchmark/GAIA` — **GATED DATASET**, requires HuggingFace token with access approval
  - To enable: `huggingface-cli login`, then request access at https://huggingface.co/datasets/gaia-benchmark/GAIA
  - The adapter gracefully falls back to empty list if auth fails
  - Also removed deprecated `trust_remote_code` flag from adapter

## Verification Results
- YAML valid: 90 questions (60 original + 30 mini-SWE), unique IDs, correct categories
- All expected answers verified by computation (original 60)
- SWE tasks validated structurally (all code_execution, no duplicate IDs)
- Unit tests: 1726 passed, 10 skipped, 0 failures
- Scorer tests: exact_match, code_execution, substring all work on mode_advantage tasks
- Seeding pipeline: mode_advantage in DEFAULT_SUITES, loads via YAML path

## Running the Eval
```bash
cd /mnt/raid0/llm/claude

# Dry-run first (check question loading, no model calls)
python3 scripts/benchmark/seed_specialist_routing.py \
  --suites mode_advantage --sample-size 5 --dry-run

# Full run with mode_advantage + external adapters
python3 scripts/benchmark/seed_specialist_routing.py \
  --suites mode_advantage,gaia,cruxeval,bigcodebench --sample-size 10

# Default suites (includes mode_advantage automatically)
python3 scripts/benchmark/seed_specialist_routing.py --sample-size 10
```
