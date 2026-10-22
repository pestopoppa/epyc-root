# 2026-10-22 YaRN gate: RULER suite in the belief-kernel schema (3c4ca599)

Gap: `yarn_gate_agg.py` (`epyc.yarn_gate_decision.v1`) had no `ruler` suite, so research `decision_records.py` excluded every RULER item (NIAH mk_2/mk_3/mv at 32K/64K/124K, most of the 185-item native plan).

- Root: `ruler` added to `SUITES`; `source_pins` = {ruler_repo, ruler_pin (7-40 hex, `ab17b78` checkout), essay_sha256, words_source `essay_vocab_hyphen_pairs`, deviations (non-empty)}. `comparable_to_published:false` unchanged, no new grading rule, observations keep an empty protocol_id. Tests: `tests/vidya/test_yarn_gate_agg.py` (14 pass).
- Research: see report below (filled at close).
- No inference was started, killed or armed.
