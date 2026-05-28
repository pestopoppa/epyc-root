# Integration Test Coverage - Remaining Gaps

**Status**: COMPACTED 2026-05-28 - active coverage backlog only; Phases 1-4 are preserved in the completed ledger.
**Created**: 2026-04-13
**Updated**: 2026-05-28
**Priority**: MEDIUM
**Primary repo**: `/mnt/raid0/llm/epyc-orchestrator`
**Parent index**: [master-handoff-index.md](master-handoff-index.md)
**Completed ledger**: [integration-test-coverage-phases-1-4-completed-through-2026-05-28.md](../completed/integration-test-coverage-phases-1-4-completed-through-2026-05-28.md)

## Executor Start Here

The integration scaffolding and earlier coverage tranches are historical. Do not chase blanket 100% coverage. Pick one focused slice that closes a real production risk, add or update tests, then record the command, test count, and coverage delta here.

## Outstanding Task Queue

| Work item | When to pick | Validation |
|---|---|---|
| Focused seeding/orchestrator coverage tranche | Non-inference code session | Run the exact focused pytest target or coverage command for the touched package. |
| Real LLM parsing paths | User-approved inference window | Add integration cases using production model outputs; mark as integration/inference-gated. |
| Backend health, KV migration, and slot paths | llama-server test fixture available | Use isolated dev ports with startup, teardown, and stale-process checks. |
| API route regressions | No inference needed if dependency overrides suffice | Use FastAPI/httpx test client with dependency overrides. |

## Rules For New Tests

- [ ] Keep mocked integration tests separate from real inference tests.
- [ ] Label inference-backed tests so normal CI can skip them.
- [ ] Include port selection, startup, teardown, and stale-process checks for live-server fixtures.
- [ ] Avoid broad fixture rewrites unless a current failing test proves the fixture contract is wrong.
- [ ] Before adding code, run `git -C /mnt/raid0/llm/epyc-orchestrator status --short` and inspect the current test layout.

## Dependency Forks

| Finding | Next action |
|---|---|
| Existing unit tests already cover the branch | Do not add duplicate coverage; record the existing test target and close that slice. |
| Branch requires real model output | Move it to the inference-gated slice and do not block normal CI. |
| Live server dependency is required | Create or reuse an isolated fixture; never touch production ports. |
| Coverage gain is small but branch is high-risk | Keep the test if it captures a production failure mode; record risk rationale, not just percentage delta. |

## Completed Scope

| Scope | Result | Ledger |
|---|---|---|
| Orchestrator refactoring coverage Phases 1-4 | Historical coverage tranches completed and preserved; extracted module unit coverage averaged 88% after the refactor audit. | [completed ledger](../completed/integration-test-coverage-phases-1-4-completed-through-2026-05-28.md) |
| Historical module/gap tables | Preserved for provenance, but not the active queue. | [completed ledger](../completed/integration-test-coverage-phases-1-4-completed-through-2026-05-28.md) |

## Key Files

- `/mnt/raid0/llm/epyc-orchestrator/tests/`
- `/mnt/raid0/llm/epyc-orchestrator/src/`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py`
- `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/`

## Reporting Instructions

After each coverage slice, update this file with the changed test files, command output summary, test count, coverage delta if measured, and any skipped inference gates. Update [master-handoff-index.md](master-handoff-index.md) only when priority, blocker state, or active scope changes.
