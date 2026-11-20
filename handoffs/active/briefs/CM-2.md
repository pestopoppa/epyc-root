---
schema: epyc.brief.v1
id: CM-2
box_text_sha: 87355678de2314f4
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/prompt_builders/constants.py
- epyc-orchestrator:src/repl_environment/codemode_tools.py
- epyc-orchestrator:scripts/benchmark/codemode_ab/CM_FOLLOWUP.md
- epyc-orchestrator:tests/unit/test_codemode_repl_tools.py
approach: 'Code landed flag-gated (b5a30286, ORCHESTRATOR_REPL_TOOL_SEARCH). Remaining acceptance: first the zero-inference
  prompt-token vs tool-count measurement on the current prompt (constants.py:11-20,85-87) per CM_FOLLOWUP.md, then the prepared
  live probe rows codemode-cm-{27b,35b}-gpu-20261119 (search-first core_search rung) which wait only on S4. Stop when a prompt-token
  reduction at equal accuracy is shown or refuted. Decision: enable search_tools in default C3.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_codemode_repl_tools.py
non_goals:
- no enabling anywhere real before S4 or operator exception
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/prompt_builders/constants.py: bf4cb73b0ef7e14503ecac188e39dd8c5e27c89a
    epyc-orchestrator:src/repl_environment/codemode_tools.py: cfaae2f92b9ccbc95cefa49fdcb66c24017955aa
    epyc-orchestrator:scripts/benchmark/codemode_ab/CM_FOLLOWUP.md: 9289d4d1ca9be6dc08f149171c9e4a40bc561a65
    epyc-orchestrator:tests/unit/test_codemode_repl_tools.py: c380868c3981feea17c5c84b070a1c3c6103ed45
---
