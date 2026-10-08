# AUD10: narrow forced-clean Bash hook — pending operator choice

Decision only a human can make: authorize the shared coordination hook setting under D9 and name its live steward. No authorization is recorded here. Recommendation: authorize only the reviewed clean-only hook with codex-ni-main as explicit temporary steward; default while undecided is no installation. Preparation, proposed source preservation and fake-only validation are complete. Existing four pending choices are not reasked.

The removed historical guard contained a clean-untracked refusal, but its installation/invocation at the historical destructive command was not proved and the actor remains unknown. The old task’s 149 untracked rows support only a code counterfactual. The new proposal scans agent-typed Bash, validates payload cwd, uses existing shell_scan framing, distinguishes untracked/ignored/directory/dry-run cases and fails closed on ambiguous wrappers/composed/control-prefix cases. Its Git probes are read-only; it never executes git clean.

Options:

1. Approve one clean-only Bash hook entry and name codex-ni-main temporary steward (recommended). Gives a bounded preventive guard with a named owner; carries conservative false-positive refusals and explicitly limited shell coverage.
2. Approve the same scope with another named live steward. Separates ownership but needs that named steward before shared installation.
3. Decline installation. Retains historical correction and operational watch without adding this forced-clean hook.

Concrete AUD10-three-path-PROPOSED.patch adds the exact hosted-tested scanner and tests at scripts/hooks and one PreToolUse Bash command in .claude/settings.json; no other hook changes. Shared settings preimage is public ROOT567d, byte-identical to original59c5. Existing shell_scan candidate is unchanged and pinned. Exact source pins and patch hashes are in manifest.json; copied source is preserved in proposed/aud10 at OWN46305499, not activated at canonical hook paths.

Original offhost run37775175542, push attempt1/source46305499, passed26/26 with zero errors/failures/skips; preceding original run37774637646 also passed26 and is retained independently. Fake subprocess runners reject any git clean invocation; no real cleanup or live owner inspection is executed. Original stdout/stderr/exits/JUnit/Python/pytest/env/argv and source verifier are retained. The earlier local26 taskset record overlapped an existing owner and is not accepted as isolated validation; it remains historical and unchanged. Hosted fixtures establish these bounded controls, not full Bash grammar correctness or universal cleanup protection. Executed scripts, aliases, other shells, daemons, cron and human terminals remain outside the claimed surface. Source preservation is not D9 approval; canonical source/settings materialization and live hook activation require explicit human trust authorization and normal MAIN review.


MAIN accepted and published the exact proposed copies through ROOT `e6f6c0048ed79d77524b542c91501ef37d4ba660`; the original fixture source remains `46305499`, not relabelled as an execution at the merge. Canonical metric and hook paths are unchanged. Original hosted outcomes are copied alongside this package and GitHub runs [M12f63](https://github.com/pestopoppa/epyc-root/actions/runs/37775175390), [AUD10 26](https://github.com/pestopoppa/epyc-root/actions/runs/37775175542).
