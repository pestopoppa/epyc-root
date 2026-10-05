# NI05-15 — prospective CI fixture conformance capture

Owning campaign: NI05 non-inference work, 2026-10-05. MAIN accepted the leaf source and its CLI enrollment after actual off-host validation.

The producer authors a bounded boolean `fixture_execution_conformant` and exact result-bearing proposition at original execution. It persists an exclusive pre-execution request, tested repository SHAs, selected command/fixtures, UTC, explicit runner fact allowlist and digest-pinned source readset before launching the fixture command. It seals original log/JUnit and source sidecars before upload. Counts remain descriptive. Missing, malformed, inconsistent, interrupted, zero-case and all-skipped results stay null diagnostics with zero projected tuples. Recorded false outcomes assert the false finding explicitly.

The strict verifier reader reopens original artifacts, preserves the producer's proposition, and projects through shared `ClaimTuple.grade()` only. `cli.py ingest ci-fixture-conformance --path <receipt.json> --as-of <UTC>` now reaches the existing dispatcher and real ledger. No scientific protocol, attestation, replicate count, inference, performance or promotion authority is invented; the receipt is an observation at Judged/Located. Original source snapshots and immutable output identities are retained; environment secrets are not dumped.

Source commits: `a1001ca0b2f692249c066dea43a897de0f050649` (producer/adapter/fixtures) and `c35f35ce2ad825b5f49efc8391d41d9766fde593` (CLI source enrollment and actual CLI-to-ledger regression). The isolated fixture-only workflow is reviewable separately and may be excluded from main publication.

Validation: [run 37277543999](https://github.com/pestopoppa/epyc-root/actions/runs/37277543999) passed 24/24 fixtures. Enrollment [run 37278646239](https://github.com/pestopoppa/epyc-root/actions/runs/37278646239) passed 25/25, with zero failures or skips. Both runs captured their original request, receipt, log, JUnit and source readset prospectively. The first two NI05 campaign runs, 37273697465 and 37275807626, remain plain validation and were not backfilled.

Evidence retained under `/mnt/raid0/llm/worktrees/codex-ni-ci-capture-20261005/native-capture{,-enrollment}-artifacts/` and corresponding full GitHub logs. No local tests, builds, inference or reloads executed.
