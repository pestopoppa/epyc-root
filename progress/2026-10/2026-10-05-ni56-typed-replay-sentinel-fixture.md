# NI56 — typed replay live-database refusal sentinel

Main reviewed and accepted the bounded source/receipt scope on 2026-10-05. The candidate APP branch is `codex/ni54-fixture-20261005` at `6bb8d860d410217895efb7806e9ef907a62a4350`, based on `64843e13642930895bb2e52694cd444de5892903`; the reviewed fixture changes are in `tests/unit/test_typed_decisions_routing_replay.py` only.

The original off-host receipt in CI run `37361602330` reports 24/24 cases passed, with zero failures, errors, or skips. The live-path refusal test substitutes an owned temporary sentinel as the resolver module’s `LIVE_DB_PATH` and traps database timestamp reads, proving refusal before reading bytes. Main independently reopened the receipt and declared source readset; the existing CI verifier and shared grade produce `Judged/Located`. The earlier fullscan outcome (23/24) remains unchanged.

The run used Python 3.11.14, uv 0.8.15 and frozen lock SHA-256 `7eae6b0447832155673e18f0e9f849fd4a65e3eb5839bf85f4165b13a4b06ca3`. Workflow ROOT commit is `6793d952fa502094b09b5b34bfbf32c5988446a1`; root producer is `ff8a6baa7e4bc86fc7318055d3fe1050f31422c7`. Private originals and the external hash manifest are recorded at `/mnt/raid0/llm/tmp/codex-ni54-56-custody-37361602330/` and `/mnt/raid0/llm/tmp/codex-ni54-56-custody-37361602330.SHA256SUMS.json`.

This establishes only the selected typed replay module’s offline refusal fixture. No live database was read or changed; no inference, performance, serving, or production-promotion claim is made. Main will integrate the exact APP candidate and finish shared documentation and push before counting NI56 as COMPLETED.
