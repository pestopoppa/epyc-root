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
approach: >-
  Add epyc-orchestrator scripts/autopilot/evals/dtap/harness/isolation.py with probe_grader_access(sentinel:
  Path, launcher: list[str]) -> dict. It launches a child via the launcher argv; the child tries open(sentinel)
  and os.listdir(sentinel.parent) and reports open_ok, open_errno, listdir_ok, listdir_errno, uid, and
  /proc/self/mountinfo hash as JSON on stdout. Add assert_grader_unreachable(result), which raises
  GraderReachable on any successful read. Use a sentinel holding a random token in a grader subdirectory of a
  dedicated tmp_path, outside any git worktree. New test test_grader_isolation.py has two cases. (1)
  test_reachable_grader_is_flagged: launcher=[] (plain subprocess). Assert that the structured child result
  shows a successful sentinel read before entering pytest.raises(GraderReachable). Inside pytest.raises only
  call assert_grader_unreachable. (2) test_isolated_launch_denies: use unshare --user --map-root-user --mount to
  mount an empty tmpfs over the dedicated scratch ancestor so the grader subdirectory disappears. For example,
  append the child argv to ['unshare','--user','--map-root-user','--mount','sh','-c','mount -t tmpfs none "$1"
  && shift && exec "$@"','--',str(tmp_path)]. Probe the same paths and assert an actual ENOENT/EACCES from the
  child for the sentinel open; the grader subdirectory must also be unreachable. Skip with the original
  diagnostic only for an explicit unshare permission refusal setting up the namespace. Fail on other launcher or
  mount errors and on missing or malformed child stdout. Launcher/probe errors must remain distinct from both
  grader reachability and a genuine access denial. Use bare unshare and mount names so the verifier can simulate
  the launch and filesystem denial with throwaway stubs. UID and mountinfo hashes are diagnostics.
control_tests:
- 'test_reachable_grader_is_flagged: assert the plain child read the sentinel, then assert GraderReachable is raised by assert_grader_unreachable'
sanctioned_skips:
- 'test_isolated_launch_denies: pytest.skip only for an explicit namespace setup permission refusal from unshare (e.g. "unshare: write failed /proc/self/uid_map: Operation not permitted"), carrying the original diagnostic'
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
