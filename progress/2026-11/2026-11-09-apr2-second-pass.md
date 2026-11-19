# 2026-11-09 apr2 second-pass

Orchestrator branch `apr2/second-pass-20261109` (worktree `/mnt/raid0/llm/worktrees/apr2-second-pass-orch-20261109`), root branch `apr2/second-pass-20261109`.

Done or partial (details in each handoff box): SEQ-4 (done, ticked), M-19 (spec as unwired code, ticked), TD-18, TD-30c, TD-30f, TD-31 (partial), TOC-CMP-4 (pre-registration doc, partial), `scripts/graph_router/reembed_episodic_store.py` now resolves llama-server through `scripts/server/stack_paths.py` (kernel store) and pins LD_LIBRARY_PATH to the store's lib dir.
Re-checked with no code to write: EV-CONF-2 (landed earlier; remaining is the inference probe). Not started: AP-29b (reward mapping unspecified), AP-71, BEP-5, CFI-2 (decision package), DCP-10/10b (ContextBench not staged), DCP-15, M-12c, TD-12, TD-29.M3, TD-30d, UTM-V1..V3, TOC-CMP-3 (compaction code excluded by instruction).
Tests ran with the orchestrator venv python plus system pytest on PYTHONPATH (repo conftest needs fastapi, absent from system python; the venv lacks pytest).
