# 2026-11-09 apr2 approved-routing

Orchestrator branch `apr2/approved-routing-20261109` @ `d19d44cd` (worktree `/mnt/raid0/llm/worktrees/apr2-approved-routing-orch-20261109`).

- TD-29.M3: `EXACTNESS_CRITICAL_TOOLS` frozen set + registry-name test; receipt seam fields (`joint_*`) with byte-identity test; caller merges `shadow_receipt_fields` only when a joint proposal is supplied. Box open (mi210-window).
- AP-29b: replay script (tau 0.906, top-10 overlap 8/10, one era, cost axis constant); `per_role_tokens`/`per_role_elapsed_s`/`baseline_tps` capture with `METRIC_SCHEMA_VERSION` 2.
- TOC-CMP-4: runner + 30 frozen points (sha256 9de7e3ba...2655a); no inference.
- Tests: ran under the 3.11 venv interpreter with `--` system pytest on PYTHONPATH because the repo conftest cannot load (no fastapi in any venv here); 12 teardown errors (`get_config.cache_clear`) are conftest-env artefacts, all tests pass.
