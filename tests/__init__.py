"""Marks `tests/` as a real package. Do not delete — see below (C16, 2026-07-28).

This is NOT cosmetic and NOT optional. Without it, `tests` is a namespace
package, and namespace packages lose to regular packages ANYWHERE on sys.path
regardless of order: `import tests.compliance` resolved to
`/mnt/raid0/llm/epyc-orchestrator/tests/__init__.py` — the orchestrator's suite,
reached through this venv — and failed with `ModuleNotFoundError: No module named
'tests.compliance'`. That single unimportable module aborted even a bare
`pytest tests/`, and it broke the documented
`python -m tests.compliance.agent_file.runner` CLI the same way.

Putting `/workspace` first on sys.path (`pythonpath = .` in pytest.ini) is not
sufficient on its own for exactly the precedence reason above; this file is the
other half of the fix.
"""
