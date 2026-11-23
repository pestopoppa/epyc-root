---
schema: epyc.brief.v1
id: TU-GR-1
box_text_sha: t:7ed41a4520d860f6
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-orchestrator:scripts/autopilot/evals/dtap/harness/runner.py::JudgeApplication
- epyc-orchestrator:scripts/autopilot/evals/dtap/tests/conftest.py
- epyc-orchestrator:scripts/autopilot/evals/dtap/judges
- epyc-root:docs/design/tu-grader-isolation-boundary.md
approach: 'Add epyc-orchestrator scripts/autopilot/evals/dtap/harness/isolation.py with probe_grader_access(sentinel: Path,
  launcher: list[str]) -> dict. It launches a child via the launcher argv; the child tries open(sentinel) and os.listdir(sentinel.parent)
  and reports ok/errno, uid, and /proc/self/mountinfo hash as JSON on stdout. Add assert_grader_unreachable(result), which
  raises GraderReachable on any successful read.

  Use a tmp_path sentinel holding a random token, outside any git worktree.

  New test test_grader_isolation.py has two cases. (1) test_reachable_grader_is_flagged: launcher=[] (plain subprocess), and
  assert_grader_unreachable must raise. This is the ''fails on a deliberately reachable grader'' control. (2) test_isolated_launch_denies:
  launcher=[''unshare'',''--user'',''--map-root-user'',''--mount'',''sh'',''-c'',''mount -t tmpfs none <dir> && exec "$@"'',''--'']
  must yield ENOENT/EACCES; if unshare is not permitted, pytest.skip with the errno. Never pass vacuously (bwrap is not installed
  on this host). Empty child stdout is an error, never a denial: raise or return launcher_error, and assert a real errno (ENOENT/EACCES)
  in the isolation test.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q scripts/autopilot/evals/dtap/tests/test_grader_isolation.py
new_tests:
- epyc-orchestrator:scripts/autopilot/evals/dtap/tests/test_grader_isolation.py
non_goals:
- no isolation or security claim from this test; it proves the check, not a production sandbox
- do not wire the launcher into runner.py or change judges, cases.json or denominators
- do not touch code_exec_scorer.py (eval-tower 2a-iv owns it)
tier: terra
grounded:
  at: '2026-11-23'
  blobs:
    epyc-orchestrator:scripts/autopilot/evals/dtap/harness/runner.py: 6a53438e66722922565d1df650424ec779d5606a
    epyc-orchestrator:scripts/autopilot/evals/dtap/tests/conftest.py: 19bd13c42448227ad93a37918044172af829476f
    epyc-orchestrator:scripts/autopilot/evals/dtap/judges: tree:90a364691792c3f646540e80cea024a19334ba02
    epyc-root:docs/design/tu-grader-isolation-boundary.md: 7d86967f8cd2e3dad46c9b58bd650f7414dd247f
---
