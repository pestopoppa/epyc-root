# RTG-36 / SCG-PRIORS-WARM source-only proposal

Base: `epyc-orchestrator origin/main` at `2e45e6a46a1d03099051b52be8165369f915aeb2`.
Patch: `proposed.patch` (SHA-256 `7c00a58774bccd28776f857a0a3051540a60d36aa910d0f41a08f61d05a3ff66`).

## Finding and scoped change

The compiler still marks every role in `stack_roles` as `live_stack`, and its serving record has no
`default_launch` field. Seeding's `_read_stack_prior_default_roles` and
`_read_stack_prior_active_roles` then read every live role. The WARM vision roles are declared and
routable once started, but the default `start` launches only HOT servers. The Oct 4 package audit
found many consumers that need WARM roles to remain `live_stack`.

The patch changes only three files:

- `src/registry/stack_priors.py`: derive `default_launch` for each role from its ports intersecting
  the numa-mode-filtered HOT launch ports; project that boolean into `serving`; add a helper that
  filters live records by that flag. A pre-flag artifact falls back to `tier != "warm"`.
- `scripts/benchmark/seeding_types.py`: use the helper in default role and active role discovery.
- `tests/unit/test_stack_priors_default_launch.py`: preserve live-stack membership while checking
  the new filter, old-artifact fallback, explicit-flag precedence, compiler's HOT-port derivation,
  and serving-record projection.

This preserves all `live_stack` consumers, including explicit `start --only`, routing, URLs and lock
sets. It does not change runtime classification, stack configuration, generated priors, reloads, or
human-only approvals.

## Impact and governance

`gitnexus impact compile_stack_priors --repo epyc-orchestrator --direction upstream --summary-only`
reported HIGH risk, 65 impacted symbols (4 direct, 6 depth-2, 55 depth-3; Registry, Autopilot and
Unit modules). `gitnexus context compile_stack_priors --repo epyc-orchestrator` enumerated its direct
tests, `write_stack_priors`, `main`, renderer, and stack-change checker. The upstream impact is broad
because the compiler is central; this patch keeps the live classification stable and changes only
an additive serving field plus two seeding readers.

The prepared `STACKCHG-HYGIENE-20261003` package says “PREPARED (phases 0–5). The operator signs next
(phase 6)” and explicitly records that nothing was applied. That is a gate for ratifying/applying the
multi-repo stack-change package, not a bar on preparing this isolated source-only patch. The old
package also bundles KVU-16a and DRAFT-SEL-2 and has an older base; do not apply it as a whole.

## Validation

- `patch --dry-run -p1 -d apply-check < proposed.patch` against files freshly read from `origin/main`:
  applies cleanly.
- Applied the proposal to a private source-only scratch copy of `origin/main`, then ran:
  `PYTHONPATH=<scratch>/run-check:/workspace/repos/epyc-orchestrator PYTHONDONTWRITEBYTECODE=1 pytest -q <scratch>/run-check/tests/unit/test_stack_priors_default_launch.py`
  Result: `4 passed in 0.51s`.
- `ruff check --line-length 100 --select E,F,W tests/test_default_launch.py`: passed.
- The test consumes the candidate compiler and seeding module from the scratch copy. Its stack-manifest,
  NUMA-mode, topology and HOT/WARM inputs were separately compared byte-for-byte with `origin/main`.
- No changes were made to the shared orchestrator checkout or handoff/index rows.

Before integration, refresh the shared source safely and re-run the focused test plus the canonical
stack-change pipeline checks. Generated `stack_priors.yaml` remains unchanged until an owning session
applies an approved stack-change package.
