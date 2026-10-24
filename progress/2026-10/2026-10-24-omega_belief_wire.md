# S4 Omega ROOT belief adapter — 2026-10-24

Promoted the reviewed ROOT S4 Omega Vidya adapter to `main` through the approved isolated promotion flow. Implementation commit `7ff9c7e49c725fdc4523f4f3683aec07c1436d0d` and replay-report fixture correction `9389682e8020470cb1ad85c30a047b051466da5f` landed in merge `16c0fa1ba2b45466a9324df0333987386d71e38b`. The integration changed only the adapter, LOW source registry entry, CLI source choice, fixture builder, and dedicated adapter tests. Shared ingest behavior, `ClaimTuple`, and grading rules were not changed.

Granted validation recorded 10 tests passed in 1.14 seconds, no skips, and a carrier audit of 199 tuples with 0 violations. The first grant's earlier fixture failure remains preserved separately; replay semantics are 30 native rows projected, 0 frames emitted, 90 frames skipped, with unchanged ledger length. No repeat was run after integration because the accepted source patches were byte-identical by patch ID.

The orchestrator producer is published at `be208213775a032aefde26a3c1df4ac4ca2d445e`; its original acceptance covered 9 tests and 6 synthetic records. No real S4 A/B capture or model/API call has occurred. Projected records remain Judged/Located; protocol and model/server identities remain unknown. Legacy output-token counts do not establish exact cost; no paired delta or promotion claim is available.

Next: after the outer S4 experiment's serving owner obtains the required calendar grant and produces real native captures, ingest those artifacts using the existing reader. This is ingestion work only; do not launch a duplicate quality experiment or duplicate TD21 parser work. Main reviewed and applied source-table enrollment and handoff completion in this closeout.

Evidence: `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/omega-root-v2/test.log`; status `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/omega-root-v2/status.json`.
