# 2026-10-24 — NI wave one granted source validation and native ingest

## S4-T1.SRC private-snapshot test

The calendar owner granted q1 for CPU correctness from 13:07 to 13:17Z. The focused suite ran from `/mnt/raid0/llm/worktrees/codex-ni-20261024-s4-orch` with HEAD exactly `7c0f2929ebef839fdf87edf6c20adc47a564035c`; the captured `pwd` and HEAD match the accepted private snapshot. `pytest tests/unit/test_seeding_eval.py -q` passed 22 tests, with one OpenTelemetry deprecation warning, in 1.85 seconds (rc 0, 13:08:13Z). This run provides new valid verification for S4-T1.SRC; the earlier 22+1 results remain documented but retracted because the launcher had tested the canonical shared checkout. The S4-T1 parent stays open for inference-owner live seeding proof; no live run was performed.

## DS41 original-five native ingest

Under the same q1 correctness grant, the existing strict adapter preflight matched one unit and projected the original five native rows into 15 frames, with zero refused, missing, or declined rows. Source sidecar: `/workspace/repos/epyc-inference-research/data/ds41-1017-w5-20261021/belief_measurements.jsonl`, SHA-256 `483b67f595467877f1b12c241f266677666b4cd5e7b3d71d76165e8661cacbc0`. Its five source measurements and row digests were checked against the scored artifacts:

- `ds41w:357e9cc1ad30d28fdfeb4f6e` — `e92099ccce5022473da1cc6d2c2e83eb31e9ef6bbddb12c742c9967330a74c53`
- `ds41w:3a2d5c4b211a6603688231c2` — `b24874bb12e7fff18d4442a299e811940c38a52080b492924bed8855f0d89850`
- `ds41w:d7498256d58ca7fd8bd1cc76` — `69fdc8be64eea186fca5c8b69994bf057451d2def647a9cd14f12af6a89b09d5`
- `ds41w:1eefde8760bfde0c4a687fbd` — `ca9b182aebc70ce3173153c9c9a317fcdb009f2706736f980306870226aecc14`
- `ds41w:206a767290019163fde3f8aa` — `bc6e8ed433cdc679d72ff584356f736d21d7ca1314823f3949a515f7140a68b2`

The canonical append used the existing `cli.py ingest ds41-1017-validation --only-new` path at `2026-10-24T13:08:04Z`, emitted 15 frames, and completed rc 0 at 13:08:13Z. The idempotency dry-run then emitted zero and skipped all 15. The canonical ledger tail contains sequences 37956–37970: five `source_observed` frames, five corresponding `claim_proposed` frames, and five `evidence_supports_claim` frames. All five tuples grade `Judged/Located`; their protocol citation is empty, so they remain observations and cannot gate decisions. No historical ABA data was reconstructed, and no Sept-Q4 quant was inferred. The AKSCOPE parent remains open for the separate historical ABA source audit.

## Other wave one status at checkpoint

These are bounded status observations, not accepted completion claims: request-usage validation reported six failing tests at 13:09:04Z; the Omega validator returned rc 1 at 13:10:28Z. Both remain unaccepted and await their source owners' fixes. This coordinator did not edit their files, rerun their tests, launch inference, or touch a production kernel.
