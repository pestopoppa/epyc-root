# SSU-F9c — shared promotion lease

The default promotion lease previously derived from the executing script's lane directory.
Two lane worktrees could therefore acquire independent leases for one repository. Promotion
now resolves the target's shared git common directory using the existing serialized-push
resolver; explicit `SERIALIZED_PUSH_LOCK_DIR` and CLI overrides retain precedence.

Source candidate `06b346eb87c76aa2f859ab47e8def7fa3000523c` was validated in combined root
`23298f00096f24b5d665a478467692f2085c09a0` by GitHub Actions run
[37273697465](https://github.com/pestopoppa/epyc-root/actions/runs/37273697465).
All three `DefaultLockDirectoryTests` passed: real cross-worktree lock contention, environment
override, and CLI precedence. The fixture proves unchanged HEAD and mocks the promotion operation.
The parent session accepted SSU-F9c on 2026-10-05 and owns integration/publication.

The broad Vidya job in the same run failed unrelated fixture/source-registration checks; those
failures are recorded separately and do not change the promotion fixture result. Retained
host-region validation remains queued; no claim of local execution or actual promotion is made.

Scratch/evidence: `/mnt/raid0/llm/worktrees/codex-ni-validation-ci-20261005/ni05-run-full.log`
and `ni05-artifacts/`; focused source lane `/mnt/raid0/llm/worktrees/codex-ni-promote-20261005`.
