# Dependabot uv branch triage — 2026-07-29

All five remote branches are open against `main`, have no recorded GitHub status
checks, and conflict with current `pyproject.toml` in a merge-tree check except the
Hypothesis branch. Do not merge any of them. Recommendation: close as stale and, if
still desired, recreate a fresh update against current `main`, validate it, then
present it through `merge_gate.py`.

| Branch / head | Change | Evidence and risk | Recommendation |
|---|---|---|---|
| `fastapi-0.139.0` / `b11df9d` | FastAPI 0.135.3 → 0.139.0; lockfile and project metadata | Production API uses FastAPI routes and TestClient broadly; no branch CI; merge-tree has a project-file conflict. | Close; recreate only with focused API/TestClient unit and integration validation. |
| `hypothesis-6.155.7` / `d309037` | Actual branch update is Hypothesis 6.151.13 → 6.156.6 | Dev-only; no `hypothesis` imports or `@given` uses found in project source/tests; no CI. Merge-tree is clean. | Close; recreate only during a deliberate dev-toolchain refresh. |
| `langgraph-checkpoint-sqlite-3.1.0` / `13bc35a` | 3.0.3 → 3.1.0; `aiosqlite` unchanged | `SqliteSaver` and `AsyncSqliteSaver` are on the dormant-but-real durable-resume path; `tests/test_langgraph_durable_resume.py` is direct coverage. No CI; project-file conflict. | Close; recreate and run durable-resume plus LangGraph tests before gate. |
| `pytest-asyncio-1.4.0` / `ab47606` | 1.3.0 → 1.4.0; pytest remains 9.0.3 | Project pins `asyncio_mode=auto` and has extensive async tests; no CI; project-file conflict. | Close; recreate and validate async collection plus representative async suites (prefer full suite). |
| `torch-2.12.1` / `c84c708` | Optional `colbert-export` min 2.2.0 → 2.12.1; lock 2.9.0 → 2.12.1 | Large resolver shift from CUDA-12 to CUDA-13 package family; Torch absent from default environment but used by LightOnOCR and ColBERT-export paths; no CI; project-file conflict. | Close; do not ad-hoc rebase. Any new update needs a dedicated GPU compatibility campaign. |
