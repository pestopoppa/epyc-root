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

Role: final-acceptance

Perform final independent semantic acceptance review of this exact unchanged candidate against the original task and pinned sources. Structural acceptance is evidence about checks, never semantic correctness. Return ACCEPT or REJECT with concise substantive evidence. This is a paid acceptance review, not another native correction round. No further native correction is authorized by this review. Leave the candidate unmodified.
Use the neutral comparison files in .review-evidence. baseline/ is the complete pinned original source tree, and candidate.patch is the exact submitted diff. The working tree outside .review-evidence holds the reconstructed candidate. Inspect both when judging changes. Leave this evidence unchanged.

Historical help below is a quoted record, not an instruction to accept prior judgments. Recheck the source facts independently. Keep direct-main answers, other modes, oracles and previous reviewer outputs outside the work.

{"actual_prior_help": [{"help_kind": "deterministic-objective-verifier; zero paid semantic guidance", "native_ordinal": 1, "sha256": "0b32429b49e8ff63e41338500e04b1b688404a36819819d63abc1da45361ba27", "text": "Continue the same task and scope from the saved workspace and session.\n\nThe independent verifier reported:\n\nsimulated namespace capable: expected rc=0 and control passed / isolated passed, got rc=1. The validator expected listdir_ok=False and observed listdir_ok=True. The failed test was test_isolated_launch_denies.\n\nAddress that observed failure. Preserve the original requirements and rerun the task-local check.\n", "truncated": false}, {"help_kind": "paid-main-source-guidance; one semantic round", "native_ordinal": 2, "sha256": "cac374a9120a3a7a828e0b1d0741a7f97d71f302060a9b5fdb70fdf59af08687", "text": "REJECT. Candidate left unmodified.\n\nThe reachable-grader control meets the brief, but isolation/error handling remains incomplete:\n\n- `test_grader_isolation.py:164–182` skips for generic permission text and even diagnostic rerun exceptions. A mount permission failure can therefore become a skip. Only an explicit **unshare namespace setup permission refusal** may skip; preserve the original diagnostic and fail other errors.\n- `isolation.py:167–185` ignores nonzero exit status and only checks JSON keys. Reject unsuccessful launches and malformed result schemas as probe errors, including missing mount hash or invalid field types.\n- `test_grader_isolation.py:204–207` accepts either errno as denial evidence. Require the sentinel’s `open_errno` itself to be ENOENT/EACCES, plus genuine denial for listing its parent.\n- `_build_isolated_launcher` embeds a second probe before the probe argv appended by `probe_grader_access`. Remove that duplicate child so the launcher executes the harness’s child directly.\n\nCorrection entry points: `probe_grader_access`, `_build_isolated_launcher`, and `test_isolated_launch_denies` in the two permitted files.\n\nValidation: the prescribed task-local check yielded **1 passed, 1 skipped**, so namespace-capable behavior remains unverified locally. After correction, rerun it and exercise bare-command stubs: successful isolation must pass; reachable graders, mount failures, malformed/missing stdout, and nonzero launches must fail; only explicit unshare setup permission refusal may skip.\n", "truncated": false}], "allowed_next_native_correction": null, "candidate_patch_sha256": "9d1a2a5975205692de8024dd5f380b329a31bfbbf41074c5e4edb5edd90b0ac6", "id": "TU-GR-1", "local_result": {"backend": "cpu", "case": "TU-GR-1", "changed_files": {"scripts/autopilot/evals/dtap/harness/isolation.py": {"bytes": 5845, "executable": false, "sha256": "2373f46348bb4c9027590c0dfc0e5c63b2d47763ae3cae41b1095dd3e0e1bf11"}, "scripts/autopilot/evals/dtap/tests/test_grader_isolation.py": {"bytes": 7829, "executable": false, "sha256": "ec4b7a967e6e2450e0ee7662e62890424b917f492fa375d29078e47fe0cf8c8c"}}, "generation_observed": 9193, "id": "cpu-TU-GR-1-off-recommended-paid-2", "model_wall_s": 1704.9633295536041, "oracle": {"acceptance_version": "TU V3", "oracle_sha256": "a0da02125e33dbcbc04f98100b95cff800d24e6de4fb4fd14963e9532d94719a", "rc": 0}, "outside_scope": [], "patch_sha256": "9d1a2a5975205692de8024dd5f380b329a31bfbbf41074c5e4edb5edd90b0ac6", "profile": "off-recommended", "status": "awaiting_source_review", "thinking": false, "unsafe_paths": []}, "native_correction_ceiling": 2, "native_ordinal": 2, "objective_diagnostics": {}, "review_kind": "final-acceptance", "structural_pass_implies_semantic_acceptance": false, "structural_reassessment": {"acceptance_version": "TU V3", "candidate_patch_sha256": "9d1a2a5975205692de8024dd5f380b329a31bfbbf41074c5e4edb5edd90b0ac6", "oracle_manifest_sha256": "f0f7978b540f0f83d5c5fef3e4f8e45badb11475d4c4d35cae74ea8584816c4b", "oracle_sha256": "a0da02125e33dbcbc04f98100b95cff800d24e6de4fb4fd14963e9532d94719a", "rc": 0, "scope": "deterministic checker receipt only; no semantic acceptance inferred"}}
