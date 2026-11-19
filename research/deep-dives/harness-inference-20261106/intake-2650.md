# T3 Code — provider-agnostic agent harness control surface (server + web/desktop/mobile clients over installed agent CLIs)

**Intake**: intake-2650 · **Verification**: dive-verified · **Read depth**: FULL · **Source**: https://github.com/pingdotgg/t3code

## What the dive found

2026-11-06 Stage-2 dive (read_depth FULL; clone at b90e554e0a942605c4de2d4ff5d4654caf998e27). All seven examined claims resolved: five confirmed, two narrowed. Narrowed: (a) the orchestration is command-idempotent with an outbox, but the event log is a ~1-day buffer whose projections cannot be rebuilt, so it is not an audit-trail or replay guarantee; (b) the 240-character rule applies to delta/merge-back summaries, not to portable handoff selection, which keeps full item text. Also recorded: the implemented strategy set has a fifth value (fork_delta_context); evals are excluded from EXECUTION in CI, not from the build; and on an external OpenCode server the adapter skips MCP registration and its scoped token, so orchestration tools disappear in the one mode that attaches to a pre-existing server. No tmux integration exists anywhere in the tree, and no llama.cpp/vLLM/MLX/local-endpoint path exists; the managed Codex runtime actively deletes OPENAI_BASE_URL.

## Claims and corrections

- claim 0: **unaffected** — Confirmed in README and docs/internals/overview.md at b90e554.

- claim 1: **unaffected** — Confirmed: execution stays in the workspace-owning environment; remote clients cannot substitute their own filesystem, credentials or machine state.

- claim 2: **narrowed** — Single-transaction commit of events+projections+receipt+outbox is real, but 'event-sourced' overstates durability: the docs say the event log is kept about a day and ProjectionMaintenance deletes events the projections cover, so projections cannot be rebuilt from the log; effects bound to a lost provider process are retired rather than replayed. Treat as command-idempotency + outbox, not an append-only audit ledger.

- claim 3: **unaffected** — Durable record + lazy resolution confirmed. The implemented strategy set has five values, adding fork_delta_context (contracts/orchestrationV2.ts:189-212), which merge-back uses; the architecture page lists four.

- claim 4: **narrowed** — 16,000-token default cap clamped 1,024-64,000, one-byte-per-token accounting, and 'never shortens your request' are confirmed. The 240-character rule is NOT a portable-selection rule: compactText()/summarizeDeltaItem() apply it to delta, merge-back and side-chat summaries; portable selection keeps full item text. Stage 1 merged the two artefacts.

- claim 5: **unaffected** — Hidden refs refs/t3/orchestration-v2/checkpoints confirmed in production code; rollback is capability-gated to fail before filesystem work.


## Anchors

intake-2650 carries 7 verbatim claim anchors; see `research/intake_index.yaml` for quotes, locators and hashes.


## Actionables

Stage-3 plan: `research/intake-stage3-plan-2026-11-06-harness-inference.md`.
