# Repo Resilience & Portability

**Status:** COMPLETE (All Phases Done)
**Created:** 2026-02-03
**Updated:** 2026-02-04 (Session 15 - Shell Script Migration Complete)
**Priority:** Maintenance only

## Goal

**Primary:** Disaster recovery — format machine, clone repo, restore working state.
**Secondary:** Future hardware changes, model roster updates.
**Completed:** External API backends, benchmark prompts documentation.

## Completed Work

### Phase 1: Foundation (COMPLETE)
- [x] Wired PathsConfig to env vars via pydantic-settings (`ORCHESTRATOR_PATHS_*` prefix)
- [x] Created `.env.example` with all path variables
- [x] Added `huggingface_id` fields to model_registry.yaml

### Phase 2: Documentation (COMPLETE)
- [x] Created `docs/SETUP.md` — comprehensive setup guide
- [x] Created `docs/MODEL_MANIFEST.md` — role-based model catalog
- [x] Created `docs/guides/model-sizing.md` — hardware assessment guide

### Phase 3: Automation (COMPLETE)
- [x] Created `scripts/setup/download_models.py` — automated model downloads
- [x] Created `scripts/setup/bootstrap.sh` — environment setup script
- [x] Created `scripts/lib/env.sh` — shell environment library
- [x] Added Makefile targets: `setup`, `bootstrap`, `download-models`, `validate-paths`

### Phase 4: Path Migration (COMPLETE)
- [x] Migrated 13 Python files in `src/` to use config-based paths with fallbacks
- [x] Migrated 4 critical shell scripts to source `env.sh`

### Phase 5: Validation & CI (COMPLETE)
- [x] Added path linting to CI (fails if >13 hardcoded paths in src/)
- [x] Updated README.md with Setup section and env-var Quick Start

### Phase 6: External APIs & Documentation (COMPLETE - Session 11)

**Shell Script Migration (4 priority scripts):**
- [x] Fixed critical bug: `agent_log.sh` had wrong log dir `/mnt/raid0/llm/LOGS` → `${LOG_DIR}`
- [x] `scripts/utils/agent_log.sh` — source env.sh, use `${LOG_DIR}`
- [x] `scripts/utils/agent_log_analyze.sh` — source env.sh, use `${LOG_DIR}`
- [x] `scripts/benchmark/bench_zen5.sh` — source env.sh, use `${MODELS_DIR}`, `${LLAMA_CPP_BIN}`
- [x] `scripts/benchmark/run_inference.sh` — source env.sh, use env vars

**External API Backends:**
- [x] Created `src/backends/anthropic.py` — AnthropicBackend class
- [x] Created `src/backends/openai.py` — OpenAIBackend class
- [x] Added `ExternalAPIConfig` and `ExternalBackendsConfig` to `src/config.py`
- [x] Updated `src/backends/__init__.py` exports
- [x] Created 26 unit tests (all passing)
- [x] API keys via env: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`

**Benchmark Prompts Documentation:**
- [x] Created `benchmarks/prompts/MANIFEST.yaml` — 15 HF-backed + 4 YAML-only suites
- [x] Created `scripts/benchmark/reconstruct_suite.py` — regeneration utility
- [x] Documented HuggingFace IDs, splits, licenses, reconstruction commands

### Phase 7: Backend Routing & Script Migration (COMPLETE - Session 12, Committed Session 14)

**Backend Type Routing:**
- [x] Added `BackendConfig` dataclass to `registry_loader.py` (local, anthropic, openai)
- [x] Added `backend_config` field to `RoleConfig`
- [x] Added methods: `get_roles_by_backend()`, `get_local_roles()`, `get_external_roles()`, `get_fallback_role()`
- [x] Updated `route_task()` to support `backend_preference` filtering
- [x] Added external API roles to `model_registry.yaml`: claude-sonnet, claude-opus, gpt-4o, gpt-4o-mini

**Shell Script Migration (12 additional scripts):**
- [x] `scripts/server/launch_production.sh` — source env.sh, removed hardcoded env exports
- [x] `scripts/server/start_servers.sh` — source env.sh, use env vars
- [x] `scripts/benchmark/full_optimization_benchmark.sh` — source env.sh
- [x] `scripts/benchmark/add_model_to_benchmark.sh` — source env.sh
- [x] `scripts/benchmark/compare_results.sh` — source env.sh
- [x] `scripts/benchmark/run_quality_checks.sh` — source env.sh
- [x] `scripts/voice/start_whisper_server.sh` — source env.sh
- [x] `scripts/document/start_lightonocr_server.sh` — source env.sh
- [x] `scripts/session/monitor_storage.sh` — source env.sh, fixed old UTILS paths
- [x] `scripts/session/claude_safe_start.sh` — source env.sh
- [x] `scripts/system/system_audit.sh` — source env.sh
- [x] `scripts/utils/report_update_workflow.sh` — source env.sh

### Phase 8: Complete Shell Script Migration (COMPLETE - Session 15)

**Final Shell Script Migration (19 additional scripts):**
- [x] `scripts/benchmark/bench_formalizers.sh` — source env.sh, FORMALIZER_LOG_DIR
- [x] `scripts/benchmark/bench_tree_speculation.sh` — source env.sh, TREE_LOG_DIR
- [x] `scripts/benchmark/comprehensive_benchmark.sh` — source env.sh, all paths
- [x] `scripts/benchmark/dry_run_all_models.sh` — source env.sh, DRY_RUN_MODEL_BASE
- [x] `scripts/benchmark/process_benchmark_results.sh` — source env.sh
- [x] `scripts/benchmark/prove_paged_attention.sh` — source env.sh, LLAMA_CPP_EXPERIMENTAL
- [x] `scripts/benchmark/record_test.sh` — source env.sh
- [x] `scripts/benchmark/run_all_formalizers.sh` — source env.sh, EVAL_LOG_DIR
- [x] `scripts/benchmark/run_combination_benchmarks.sh` — source env.sh, BENCH_LOG_DIR
- [x] `scripts/benchmark/run_draft_discovery.sh` — source env.sh
- [x] `scripts/benchmark/run_remaining_benchmarks.sh` — source env.sh, BENCH_LOG_DIR
- [x] `scripts/benchmark/run_twyne_figures.sh` — source env.sh
- [x] `scripts/benchmark/systematic_optimization_benchmark.sh` — source env.sh, BENCH_TMP_DIR
- [x] `scripts/benchmark/watch_benchmark.sh` — source env.sh, TMP_DIR
- [x] `scripts/document/start_lightonocr_llama.sh` — source env.sh
- [x] `scripts/session/start_orchestrator_test.sh` — source env.sh
- [x] `scripts/session/yolo_env_setup.sh` — source env.sh
- [x] `scripts/setup/bootstrap.sh` — conditional env.sh sourcing (runs before env.sh exists)
- [x] `scripts/system/reorganize_project.sh` — source env.sh

**Migration complete:** 75 scripts now source env.sh. Only legacy/ scripts (deprecated) and emergency_cleanup.sh (root FS cleanup, doesn't use model paths) remain without sourcing.

## Remaining Work (Low Priority)

### P3: Docker/Nix Containerization (Deferred)

For fully reproducible environment:

**Docker approach:**
```dockerfile
FROM python:3.11
# Install system deps (numactl, etc.)
# Copy project, run uv sync
# Mount models as volume
```

**Nix flake approach:**
- Fully reproducible deps, tools, paths
- Higher complexity

### P4: Model Hosting Decision

Currently using third-party HuggingFace repos (lmstudio-community, unsloth).

**Options:**
1. Keep documenting third-party sources (current approach, less maintenance)
2. Mirror to project HuggingFace org (more control, more maintenance)

**Recommendation:** Keep third-party, document well. Only mirror if sources become unreliable.

### P4: llama.cpp as Submodule

Currently separate clone at `/mnt/raid0/llm/llama.cpp`. Could track as submodule for exact commit tracking.

**Trade-offs:**
- Submodule: Exact reproducibility, harder local development
- Separate: Easier iteration, need to document required branch

**Current approach:** Separate clone, document required branch (`production-consolidated`).

## Files Reference

### Created in Phases 1-5
| File | Purpose |
|------|---------|
| `.env.example` | Environment configuration template |
| `docs/SETUP.md` | Comprehensive setup guide |
| `docs/MODEL_MANIFEST.md` | Role-based model catalog |
| `docs/guides/model-sizing.md` | Hardware assessment guide |
| `scripts/setup/download_models.py` | Automated model downloads |
| `scripts/setup/bootstrap.sh` | Environment setup script |
| `scripts/lib/env.sh` | Shell environment library |

### Created in Phase 6 (Session 11)
| File | Purpose |
|------|---------|
| `src/backends/anthropic.py` | Anthropic Claude API backend |
| `src/backends/openai.py` | OpenAI API backend |
| `tests/unit/test_anthropic_backend.py` | 14 unit tests |
| `tests/unit/test_openai_backend.py` | 16 unit tests |
| `benchmarks/prompts/MANIFEST.yaml` | Machine-readable suite manifest |
| `scripts/benchmark/reconstruct_suite.py` | Suite regeneration utility |

### Modified in Phases 1-5
| File | Changes |
|------|---------|
| `src/config.py` | PathsConfig env var support |
| `orchestration/model_registry.yaml` | Added `huggingface_id` fields |
| `Makefile` | Added setup targets |
| `.github/workflows/test.yml` | Added path linting |
| `README.md` | Setup section, env-var examples |
| 13 Python files in `src/` | Config-based paths with fallbacks |
| 4 shell scripts in `scripts/session/` | Source env.sh |

### Modified in Phase 6 (Session 11)
| File | Changes |
|------|---------|
| `src/config.py` | +ExternalAPIConfig, +ExternalBackendsConfig |
| `src/backends/__init__.py` | Export AnthropicBackend, OpenAIBackend |
| `scripts/utils/agent_log.sh` | Source env.sh, use ${LOG_DIR} |
| `scripts/utils/agent_log_analyze.sh` | Source env.sh, use ${LOG_DIR} |
| `scripts/benchmark/bench_zen5.sh` | Source env.sh, use env vars |
| `scripts/benchmark/run_inference.sh` | Source env.sh, use env vars |

### Modified in Phase 7 (Session 12)
| File | Changes |
|------|---------|
| `src/registry_loader.py` | +BackendConfig, backend routing methods, route_task backend_preference |
| `orchestration/model_registry.yaml` | +backend section for roles, +4 external API roles |
| 12 shell scripts | Source env.sh, use env vars (see Phase 7 list above) |

## Verification Commands

```bash
# Test fresh clone scenario
cd /tmp && git clone <repo> test-clone && cd test-clone
cp .env.example .env
# Edit .env to point to /tmp/test-llm
pip install -e ".[dev]"
make validate-paths  # Should pass
make gates           # Should pass (tests may skip without models)

# Test env override
ORCHESTRATOR_PATHS_LLM_ROOT=/tmp/test python3 -c "
from src.config import get_config
print(get_config().paths.llm_root)  # /tmp/test
"
```

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-04 | Mark shell script migration complete | 75/~80 scripts migrated, only legacy/emergency scripts remain |
| 2026-02-04 | Commit Phase 7 as `f554bca` | Backend routing + 12 shell scripts complete |
| 2026-02-03 | Use fallback defaults in helper functions | Robustness — system works even if config fails |
| 2026-02-03 | CI path count threshold of 13 | One fallback per migrated file, catches new hardcoded paths |
| 2026-02-03 | Keep llama.cpp separate (not submodule) | Easier local development |
| 2026-02-03 | Document third-party model sources | Less maintenance than mirroring |
| 2026-02-03 | Implement external backends as protocol-based classes | No inheritance needed, matches existing LLMBackend protocol pattern |
| 2026-02-03 | Store API keys in env vars not config | Security — no secrets in code or config files |
| 2026-02-03 | Create MANIFEST.yaml for benchmark suites | Machine-readable enables automated reconstruction |

## Handoff Checklist

For future work on remaining items:

- [x] ~~Add anthropic/openai backend implementations~~ (Session 11)
- [x] ~~Document benchmark prompt reconstruction~~ (Session 11 - MANIFEST.yaml)
- [x] ~~Migrate priority shell scripts (agent_log.sh, bench_zen5.sh)~~ (Session 11)
- [x] ~~Add `backend_type` field to model_registry.yaml role assignments~~ (Session 12)
- [x] ~~Update registry_loader.py to route based on backend type~~ (Session 12)
- [x] ~~Migrate 12 additional shell scripts~~ (Session 12)
- [x] ~~Migrate remaining ~20 benchmark/utility scripts to source env.sh~~ (Session 15 - 75 scripts total)
- [ ] Evaluate Docker vs Nix for containerization (deferred)
- [ ] Review model hosting if third-party sources become unreliable (monitoring)
