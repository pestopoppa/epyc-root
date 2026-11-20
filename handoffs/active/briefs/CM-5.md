---
schema: epyc.brief.v1
id: CM-5
box_text_sha: 779e5d524a1b25fe
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/repl_environment/environment.py
- epyc-orchestrator:src/repl_environment/codemode_tools.py
- epyc-orchestrator:tests/unit/test_codemode_cm45.py
approach: 'Handle store landed flag-gated (ORCHESTRATOR_REPL_HANDLES). Remaining: confirm handles survive a real branch checkpoint
  and restore in the live session store (unit-tested at REPL level only) and run the live handle-reference vs peek re-read
  comparison (tokens, success) via the prepared cm probe rows after S4. First step: an integration test of handle survival
  through GraphHarness checkpoint/restore.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_codemode_handles_checkpoint_restore.py
new_tests:
- tests/unit/test_codemode_handles_checkpoint_restore.py
non_goals:
- no default-on
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/repl_environment/environment.py: cd93f9e4825452efdf31e0f2e81efa7b8142aecc
    epyc-orchestrator:src/repl_environment/codemode_tools.py: cfaae2f92b9ccbc95cefa49fdcb66c24017955aa
    epyc-orchestrator:tests/unit/test_codemode_cm45.py: 12412b307efe50f6be4a79ef18c1a02cd9975107
---
