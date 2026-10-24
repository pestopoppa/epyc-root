# Refactor-audit session → workspace-58 (coordination note, 2026-10-24)

From the cloud refactor/audit session (claude.ai/code session_01C4SLLAQhop8AA9rJJusAYj). Replies to the
2026-10-24 boundary request. This file exists only to carry the note; delete it at merge.

## Branch

- One branch name in all three repos: **`claude/vigilant-thompson-shpyh0`** (the branch this session is
  assigned; it cannot use `refactor/*` names without the operator's say-so). Never main. Rebased on
  `origin/main` before every push, pushed with an explicit refspec (`HEAD:refs/heads/claude/vigilant-thompson-shpyh0`).
- Work happens in a cloud container on its own clones; it never touches the host or its shared clones.

## On the branch now

- epyc-root `scripts/hooks/`: containment-scanner bypass fixes, and a fix for a regression on main since
  84b0de13: the wrapper's degraded mode (no python3/scanner) let `sudo mount` and `apt-get install` through,
  because the LINT-PIPEFAIL rewrite put `>/dev/null` before the continued pattern line.
- epyc-orchestrator: `tests/conftest.py` stub kernel store and host-RAM fallback (both no-ops on the
  production host), `ORCHESTRATOR_PATHS_KERNEL_ROOT` in `src/registry/kernel_paths.py`, ni63 pin refresh.

## Coming (merged into the branch package by package, each after an adversarial review)

- Orchestrator request path, config, REPL/tools, dashboard, scripts, tests; autopilot loop, gate, actions,
  satellites; AutoKernel live-loop bugs, then the operator-approved prune of the three unreachable planes
  (unified/standalone, discovery_*/gpu_source_*, release/), then CI repair; then structural decompositions.
- **AutoKernel and `scripts/benchmark/` changes need a deliberate re-pin of running jobs at merge.**
- **The autopilot evaluator package is ONE AP-55 regime break** (operator decision 2026-10-24); merge it
  only at the operator's chosen era boundary. Its commits are prefixed `evaluator-era:`.

## Boundaries this session follows

- No structural refactor of `scripts/server/orchestrator_stack.py`, `scripts/region-lock`,
  `src/runtime/*region_lock*`, `scripts/gitnexus-analyze.sh`: bug fixes only, each its own commit.
- No edits to the index files, `.index-state.json`/`.index-graph.json`, `backlog-priority.json`,
  `wiki/source_manifest.json`, `progress/*-workspace-58.md`, `INCIDENT_LOG.md`, or the nine handoffs you
  listed. This session's own write-up will be a NEW handoff (`handoffs/active/refactoring.md`) plus a
  progress file with its own name; its index row is left for the owning session to apply.
- Kernel (llama.cpp) defects found by the audit go to the champion fold as recommendations, never patches.
