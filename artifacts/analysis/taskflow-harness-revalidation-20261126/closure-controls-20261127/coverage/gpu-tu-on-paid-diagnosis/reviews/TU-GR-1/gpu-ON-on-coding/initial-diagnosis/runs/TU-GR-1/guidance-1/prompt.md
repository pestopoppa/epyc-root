Task TU-GR-1. Work in your isolated copy of the pinned source.

- [ ] **TU-GR-1 — Grader isolation clause.** Add a test to the tool-use harness proving graders and reference artifacts are structurally unreachable from the agent (container mount or separate uid, outside any git worktree the agent can read); done when the test exists and fails on a deliberately reachable grader.
  - [x] **TU-GR-1a — Specify the agent/worker/grader boundary and genuine denial acceptance.** ✅ 2026-10-06 — MAIN accepts [boundary specification](../../docs/design/tu-grader-isolation-boundary.md) after reopening 25 pinned source blobs. Existing scorer test-source visibility, OS-denial matrix, bounded exports and JEV/trace limits are explicit. No sandbox selected/activated, mocked tests executed, judge/denominator change or isolation claim; TU-GR-1/2a-iv enforcement remains open.

Completion condition

the test exists and fails on a deliberately reachable grader

Pinned owner brief

Add epyc-orchestrator scripts/autopilot/evals/dtap/harness/isolation.py with probe_grader_access(sentinel: Path, launcher: list[str]) -> dict. It launches a child via the launcher argv; the child tries open(sentinel) and os.listdir(sentinel.parent) and reports open_ok, open_errno, listdir_ok, listdir_errno, uid, and /proc/self/mountinfo hash as JSON on stdout. Add assert_grader_unreachable(result), which raises GraderReachable on any successful read.
Use a sentinel holding a random token in a grader subdirectory of a dedicated tmp_path, outside any git worktree.
New test test_grader_isolation.py has two cases. (1) test_reachable_grader_is_flagged: launcher=[] (plain subprocess). Assert that the structured child result shows a successful sentinel read before entering pytest.raises(GraderReachable). Inside pytest.raises only call assert_grader_unreachable. (2) test_isolated_launch_denies: use unshare --user --map-root-user --mount to mount an empty tmpfs over the dedicated scratch ancestor so the grader subdirectory disappears. For example, append the child argv to ['unshare','--user','--map-root-user','--mount','sh','-c','mount -t tmpfs none "$1" && shift && exec "$@"','--',str(tmp_path)]. Probe the same paths and assert an actual ENOENT/EACCES from the child for the sentinel open; the grader subdirectory must also be unreachable. Skip with the original diagnostic only for an explicit unshare permission refusal setting up the namespace. Fail on other launcher or mount errors and on missing or malformed child stdout. Launcher/probe errors must remain distinct from both grader reachability and a genuine access denial. Use bare unshare and mount names to allow the verifier to exercise these command paths with throwaway stubs when real user namespaces are unavailable.


Pinned staged inputs
- src
- scripts
- orchestration
- pyproject.toml
- tests/conftest.py
- tests/unit/conftest.py
- tests/__init__.py
- tests/unit/__init__.py
- .taskflow-task-env.py
- .taskflow-refs/epyc-root@3b11e6c8244897cc9db02d366d8f63a885f62d0d/docs/design/tu-grader-isolation-boundary.md

Allowed task output paths

scripts/autopilot/evals/dtap/harness/isolation.py

scripts/autopilot/evals/dtap/tests/test_grader_isolation.py

Scope

no isolation or security claim from this test; it proves the check, not a production sandbox

do not wire the launcher into runner.py or change judges, cases.json or denominators

do not touch code_exec_scorer.py (eval-tower 2a-iv owns it)

Use the ordinary Codex tools within this private lane, with staged inputs and relative repository paths. Use python3 .taskflow-task-env.py before every task-local Python check; it supplies the explicit isolated current-container environment. Read public references only when the brief calls for them. Work independently. Keep prior solutions, other lanes, published answers, and controller records outside the work. Local task tests are in scope. Avoid commits, pushes, external communications, builds, and service or process-control changes.

The controller will run independent acceptance after the turn.

Task-local check: python3 .taskflow-task-env.py python3 -m pytest -q scripts/autopilot/evals/dtap/tests/test_grader_isolation.py

Role: initial-diagnosis

Review the exact unchanged local candidate independently against the original task and pinned sources. Return ACCEPT only if the substantive task is already complete, otherwise REJECT with a bounded source-grounded diagnosis, entry point and validation for the single permitted paid-guided native correction (ordinal2). Do not invent work. Leave the candidate unmodified.
Use the neutral comparison files in .review-evidence. baseline/ is the complete pinned original source tree, and candidate.patch is the exact submitted diff. The working tree outside .review-evidence holds the reconstructed candidate. Inspect both when judging changes. Leave this evidence unchanged.

Historical help below is a quoted record, not an instruction to accept prior judgments. Recheck the source facts independently. Keep direct-main answers, other modes, oracles and previous reviewer outputs outside the work.

{"actual_prior_help": [{"help_kind": "deterministic objective verifier", "native_ordinal": 1, "sha256": "9422b82ad2d1dcdc73f0dae667a9e5cb4ac42d570b3a8653bb96f5f407c66ca1", "text": "Continue the same task from your saved workspace/session.\n\nThe independent verifier observed: simulated namespace mount-permission-refusal: expected rc=1 and control passed / isolated failure, got rc=0. The control passed, but the isolated test was skipped on the mount error 'Operation not permitted'.\n\nAddress that observed behavior within the original scope and run the task-local check.\n", "truncated": false}], "allowed_next_native_correction": 2, "candidate_patch_sha256": "0d35e2f372c19d81486d9eca64ebb2391e76c09d899446525004f35e37fe04a3", "id": "TU-GR-1", "local_result": {"backend": "gpu", "case": "TU-GR-1", "changed_files": {"scripts/autopilot/evals/dtap/harness/isolation.py": {"bytes": 4339, "executable": false, "sha256": "9330b7e46d23d873bcb833f16f45e1b10673a75ce2978d36b9426f7e39391fd2"}, "scripts/autopilot/evals/dtap/tests/test_grader_isolation.py": {"bytes": 8112, "executable": false, "sha256": "58d5455758e538dcc2e73ea0ee9f06b07dc63095fb93bfa19cc79e87ca4a4770"}}, "generation_observed": 9118, "id": "gpu-TU-GR-1-on-coding-v2-objective-1", "model_wall_s": 213.8151137828827, "oracle": {"acceptance_version": "TU V3", "candidate_patch_sha256": "0d35e2f372c19d81486d9eca64ebb2391e76c09d899446525004f35e37fe04a3", "observed_failure": ["simulated namespace wrong-access-errno: expected rc=1 and control passed / isolated failure, got rc=0 and {'test_reachable_grader_is_flagged': ('passed', ''), 'test_isolated_launch_denies': ('passed', '')}"], "oracle_manifest_sha256": "f0f7978b540f0f83d5c5fef3e4f8e45badb11475d4c4d35cae74ea8584816c4b", "oracle_sha256": "a0da02125e33dbcbc04f98100b95cff800d24e6de4fb4fd14963e9532d94719a", "rc": 1, "scope": "actual contained checker outcome for this candidate"}, "outside_scope": [], "patch_sha256": "0d35e2f372c19d81486d9eca64ebb2391e76c09d899446525004f35e37fe04a3", "profile": "on-coding", "status": "awaiting_source_review", "thinking": true, "unsafe_paths": []}, "native_correction_ceiling": 2, "native_ordinal": 1, "objective_diagnostics": {}, "review_kind": "initial-diagnosis", "structural_pass_implies_semantic_acceptance": false, "structural_reassessment": {"acceptance_version": "TU V3", "candidate_patch_sha256": "0d35e2f372c19d81486d9eca64ebb2391e76c09d899446525004f35e37fe04a3", "observed_failure": ["simulated namespace wrong-access-errno: expected rc=1 and control passed / isolated failure, got rc=0 and {'test_reachable_grader_is_flagged': ('passed', ''), 'test_isolated_launch_denies': ('passed', '')}"], "oracle_manifest_sha256": "f0f7978b540f0f83d5c5fef3e4f8e45badb11475d4c4d35cae74ea8584816c4b", "oracle_sha256": "a0da02125e33dbcbc04f98100b95cff800d24e6de4fb4fd14963e9532d94719a", "rc": 1, "scope": "actual contained checker outcome for this candidate"}}
