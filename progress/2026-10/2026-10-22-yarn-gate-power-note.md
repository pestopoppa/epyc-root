# 2026-10-22 YaRN native-window gate: power fields so a NOT-FAIL cannot be over-read (3c4ca599)

The gate (YARN-AGG-1(i)) is a one-sided exact McNemar on native-zone discordant pairs: FAIL iff p <= 0.05. It is harm DETECTION, not equivalence; it needs at least 5 losses with 0 wins to fail. With few discordants it almost always reads NOT-FAIL.

- Research (branch `yarn-native-gate-runner-20261022`, 7e7d5ef7f, pushed while both pollers 3893272 and 1198715 had only a `sleep` child): `agg_scoring.power_fields` feeds `net_paired_mcnemar` (so pooled and per-cell blocks carry it), top-level `decision.json` (INTERIM and FINAL), `claim_tuple.extra` and the per-cell verdict records. Fields: `n_pairs`, `n_discordant`, `b_a0right_a1wrong`, `c_a0wrong_a1right`, `min_losses_to_fail_given_discordant` (smallest b among the current discordants with p <= alpha, null when unreachable; companion `min_losses_to_fail_with_zero_wins` = 5), `power_note`, `interpretation` (FAIL / NOT-FAIL-underpowered when n_discordant < 10 / NOT-FAIL). `verdict` and its rule are untouched.
- Root adapter `yarn_gate_agg.py`: optional `n_discordant` (must equal b + c) and `interpretation` on verdict records, mirrored into row `extra`; grading untouched (`claim_tuple.grade()`).
- Tests: research yarn_gate 88 pass (power fields at n_discordant 0, 3, 10; FAIL boundary; verdicts unchanged across fixtures); root `tests/vidya/test_yarn_gate_agg.py` 16 pass.
- `YG_RESEARCH_SHA` in yarn_gate_lib.sh swapped atomically to 7e7d5ef7f28f0c0ec45c16b7a90a51750006671f.
- Offline recompute of the live interim data (copy under /mnt/raid0/llm/tmp/yarn-power-offline-3c4ca599, live decision.json untouched): 18 pairs, 2 discordant (b=1, c=1), interpretation NOT-FAIL-underpowered.
- No inference was started, killed or armed.
