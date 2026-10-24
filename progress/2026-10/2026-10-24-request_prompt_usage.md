# 2026-10-24 — request_prompt_usage (EVL-37 S4-T2.PROMPT)

## Objective

Add exact, request-local generation prompt-token telemetry to `/chat` responses and carry that value into the seeding result without relabeling decoded/output tokens.

## Root cause

`LLMPrimitives` shared one mutable `total_prompt_tokens_reported` counter across requests, while API initialization reset it on shared instances. The per-call `get_last_inference_meta()` context already held exact prompt counts, but only for the latest call. In addition, preprocessing input formalization used an external `llama-cli` generation subprocess before the request collector was opened and exposed no exact usage. The seeding builder preferred `tokens_used` over `prompt_tokens`, losing exact zero and storing decoded usage as prompt usage. The newer builder also omitted the existing separate `RoleResult.tokens_used` field, unlike the legacy builder.

## Changes

| Repo | Change | Source commit |
|---|---|---|
| epyc-orchestrator | Add a request-context prompt usage accumulator; include finalized structured-chat usage; return explicit `ChatResponse.prompt_tokens` as null when unavailable; propagate context into parallel REPL delegation; invalidate totals when input formalization runs; keep existing shared serving counters intact. | `df8e89fa76a7ff5d0ca112b7a73dbcd9ff4e5d5f` |
| epyc-orchestrator | In `seeding_eval._build_role_result`, copy exact `resp.prompt_tokens` only into `RoleResult.prompt_tokens`, and preserve `resp.tokens_used` separately in its existing field. `RoleResult.prompt_tokens` is nullable; no historical checkpoint rewrite. | `6e6d85ade9c29f86a58ca5bfaeff4132a2dd39b0` |

The source metric is exact generation prompt usage reported through `LLMPrimitives`; embedding-only work is excluded. An input-formalizer attempt forces null because its separate generation subprocess reports no exact count. `tokens_generated` and `tokens_used` retain their legacy shared/reset and approximate behavior; no full-cost or exact decoded-output claim is made.

## Verification

Calendar-managed focused validation passed on source pin `6e6d85ade9c29f86a58ca5bfaeff4132a2dd39b0`: **24 passed, 2 warnings, 4.31 s**. Evidence: `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/request-usage-v2/test.log` and `status.json`. The warnings were an OpenTelemetry deprecation and a Pydantic serialization warning from the existing test mock.

The prior failed attempt is retained at `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/request-usage/test.log` and `status.json`: earlier pin `df8e89fa76a7ff5d0ca112b7a73dbcd9ff4e5d5f`, 18 passed / 6 failed. The failures exposed an unconfigured prompt-usage mock and the missing separate `tokens_used` copy in the newer seeding builder; both were corrected in the later pin. No historical results were backfilled.

## Publication and integration

The feature branch was published with an explicit refspec under the canonical push lock, then promoted through an isolated merge under the wrap-up and push leases. Fresh orchestrator integration started at `origin/main` `3329083dc37a693953eea7878f32037695d851f6`, then cherry-picked only the two prompt telemetry commits:

- `0a44d698` — prompt telemetry source, fresh-main cherry-pick of `df8e89fa`.
- `68c71f67` — seeding output/prompt separation, fresh-main cherry-pick of `6e6d85ad`.

Feature branch: `codex/ni-20261024-request-prompt-usage-integration`, published at `68c71f677b00e2bcd7e24a84e6a779354d2bb752`. Isolated promotion merge: `8c7470470325bf832601da7f95ccae380779b203`. Verified remote `main` points to that merge and contains the published feature commit. The source branch's stable patch ID matched the approved patch (`d80b20737c11a29a470c90a5a8c957fcdccd8cef`).

Integration worktree: `/mnt/raid0/llm/worktrees/codex-ni-20261024-request-usage-integration`. No output-only changes, live inference, API reload, or service/config/registry changes were made.

Root progress and hand-off documentation were published on root `main` in commit `d3adf499ea3660dfa7657bade2ecfa63052443b5`. The orchestrator source was already integrated on `main` by merge `8c7470470325bf832601da7f95ccae380779b203`.

## Handoff

The bounded `S4-T2.PROMPT` child checkbox is checked in the root docs candidate after the source was verified on remote main. The S4-T2 parent and live A/B gates remain open. The source response field does not claim full cost, exact decoded output, historical backfill, or live A/B results. No API reload or live inference was run.
