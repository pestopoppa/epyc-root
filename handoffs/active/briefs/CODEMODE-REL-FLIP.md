---
schema: epyc.brief.v1
id: CODEMODE-REL-FLIP
box_text_sha: 92539571d4a71874
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/features.py::repl_explicit_final_strict
- epyc-orchestrator:src/features.py::codemode_prompt_v2
- epyc-orchestrator:src/features.py::codemode_stubs
- epyc-orchestrator:src/features.py::repl_turn_memory
approach: 'Operator-approved flip. Make each C3 flag (repl_explicit_final_strict, codemode_prompt_v2, codemode_stubs, hardened
  picker, repl_turn_memory=4, repl_tool_name_repair) default ON in its FeatureSpec and env_on, keep kill switches and the
  autopilot manipulation surface, run the REPL and security suites with flags on and off, then one API-only reload. Branch
  feat/codemode-rel-flip already exists in the orchestrator (worktree orch-codemode-flip): first step is rebase and rerun.
  Gate: 35B CPU r2 latency gate and 27B GPU r2 stage 1 passed with picker p95 in budget. Acceptance is the flag-default test.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_codemode_prompt_v2.py tests/unit/test_codemode_stubs.py
  tests/unit/test_codemode_explicit_final.py tests/unit/test_codemode_turn_memory.py
non_goals:
- do not stop autopilot
- no full-stack reload
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/features.py: 7410fd35cca156e436d981664d5304d6bf2ad3b2
---
