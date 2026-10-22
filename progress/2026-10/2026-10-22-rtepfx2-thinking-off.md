# 2026-10-22 RTE-PFX-2 filler: Qwen3.6 thinking-off source fix

Coordinator session 3c4ca599. No inference run.

- Orchestrator branch `lane/qb2-rtepfx2-20261021`, commit `c91f3a781`: `rte_pfx2_role_recipe.py` adds `--reasoning off` to the server argv for Qwen3.x (same rule as `qwen_thinking_lib.sh`: GGUF name or arch qwen35/qwen3moe), runs a 16-token "Reply with OK." preflight after the own-PID port proof and before the linkage check and probe (rc 9 on non-empty reasoning_content or empty content, rc 8 on transport failure), and records the delta plus the preflight result in RUN_HEADER.json. The registry-derived argv is otherwise unchanged.
- Tests: `tests/unit/test_rte_pfx2_role_recipe.py` 13 passed (argv, header-arch detection, stubbed-HTTP preflight).
- Job `rte_pfx2_job.sh` runs from the worktree and does not check a sha, so no repin is needed. Poller 2209910 had only a `sleep` child (idle) when the edit was made.
- See docs/guides/agent-workflows/compute-fillers.md item 15.
