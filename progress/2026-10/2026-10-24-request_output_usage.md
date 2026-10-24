# 2026-10-24 — request_output_usage (EVL-37 S4-T2.OUTPUT)

## Objective

Expose a request-local count of decoded output tokens only when the serving path reports a native count, while retaining legacy output counters and their consumers unchanged.

## Root cause

`tokens_generated` / `tokens_used` are legacy shared or approximate counters. Some backend paths derive them from text/chunk lengths, and shared-state counters can be reset or interleave across requests. They cannot establish exact decoded-token usage for one request. Native output counts exist at finalized completion and chat-usage parser sites, but were not carried to the API response or seeding result.

## Changes

| Repo | Change | Source commit |
|---|---|---|
| epyc-orchestrator | Add `InferenceResult.output_tokens_reported` and parser provenance at native `/completion`, chat `usage.completion_tokens`, and terminal stream-count sites. Never substitute text/chunk estimates; interrupted, failed, missing-terminal, or missing-count results remain unknown. | `7301e041` (fresh-main cherry-pick of `19f14a1d`) |
| epyc-orchestrator | Add a locked, request-local output collector with pending attempts and source provenance; propagate the nullable count/status/sources to `ChatResponse` and `RoleResult`; invalidate completeness for unmetered input formalization and text-only WorkerPool generation. Keep legacy counters and scoring gates unchanged. | `7301e041` |
| epyc-orchestrator | Require nonempty, all-valid provenance at API/seeding boundaries; preserve observed native source IDs when aggregate completeness is unknown. | `fc957b62` (fresh-main cherry-pick of `fbc9ed32`) |
| epyc-orchestrator | Correct the transport-failure fixture to include structural `failure_reason="connect_error"`; no classifier change. | `d6d5f268` (fresh-main cherry-pick of `50fcf0f9`) |

The value counts whatever decoded output the server natively reports, including reasoning/tool-call output when included by that server. Tool-return text is not decoded output. Missing, failed, partial, pending, or unmetered generation prevents a complete request aggregate; explicit native zero is valid. Provenance can truthfully remain present for native calls observed before another call makes the aggregate unknown. Embedding tokens are outside this generation metric. No full-host/full-request monetary-cost claim is made.

## Verification

The approved v3 calendar run first executed the formerly failing seeding test as a preflight: 1 passed in 0.72 s. The focused set then passed: **31 passed, 161 deselected, 1 warning, 5.61 s**. Evidence: `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/request-output-v3/test.log`, `status.json`, and `launcher-v3.log`; source pin `50fcf0f9ea1401257c1e637699c8829d45885f15`.

Earlier failures remain preserved. V1: 23 passed / 8 failed; five seeding cases exposed the prompt candidate’s omitted separate legacy `tokens_used` copy, and three cases had stale expectations that unknown aggregate status must erase valid observed native provenance. V2: 30 passed / 1 failed; the fixture said `"transport failed"` but omitted structural failure metadata, so the correct classifier returned `task_failure`. The fixture now supplies the accepted `connect_error` reason; no classifier or metric semantics changed. Logs: `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/request-output/test.log` and `request-output-v2/test.log`.

No live inference, model/API call, service reload, or production/runtime counter mutation was performed.

## Fresh-main integration and promotion

Fresh orchestrator `origin/main` was `8c7470470325bf832601da7f95ccae380779b203`, already containing the separately accepted prompt-usage source (`68c71f67`) and root closeout (`d3adf499`). Output-only feature branch `codex/ni-20261024-request-output-integration` was published at `d6d5f268ee27a642d393eded53756028b374921b` using the registered `push` lease and explicit full-SHA refspec. Isolated promotion under the registered `wrapup` lease produced merge `d2ce754d571c1ca2648e036175d77f2beb9f4e25`; remote `main` was fetched and independently verified at that SHA, and the remote feature ref was verified at `d6d5f268`. `git diff origin/main..HEAD` before promotion contained only the 13 output source/test files; the candidate worktree remains clean.

`git range-diff` matched the provenance and fixture-only follow-ups. The first patch has a different stable patch ID only because fresh main added the `UFH14-LB6.2` serving-call comment/wrapper in the same streaming parser; the native output-count hunk remains after that added context and no semantic conflict occurred. The feature push and isolated promotion are complete; no prompt commits were duplicated. This root closeout records the bounded OUTPUT child and source evidence on root main; no new grader/source-class row or index row was proposed. Adoption by a live API process belongs to the serving owner at its scheduled reload boundary; this session performed no reload. Keep the Omega A/B live run inference-gated and the parent S4-T2 item open.
