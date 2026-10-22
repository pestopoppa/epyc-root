# 2026-10-22 YaRN gate: RULER suite in the belief-kernel schema (3c4ca599)

Gap: `yarn_gate_agg.py` (`epyc.yarn_gate_decision.v1`) had no `ruler` suite, so research `decision_records.py` excluded every RULER item (NIAH mk_2/mk_3/mv at 32K/64K/124K, most of the 185-item native plan).

- Root: `ruler` added to `SUITES`; `source_pins` = {ruler_repo, ruler_pin (7-40 hex, `ab17b78` checkout), essay_sha256, words_source `essay_vocab_hyphen_pairs`, deviations (non-empty)}. `comparable_to_published:false` unchanged, no new grading rule, observations keep an empty protocol_id. Tests: `tests/vidya/test_yarn_gate_agg.py` (14 pass).
- Research: `decision_records.py` stops excluding ruler (`SUITES` + `source_pins('ruler')` from item pins `ruler_sha`, `essay_sha256`, `words_source`, `deviations`), tests updated (ruler cells+verdict now emit; yarn_gate suite 86 pass with EPYC_ROOT at the new root). Branch `yarn-native-gate-runner-20261022` 46d26f626 -> d5a953b2a pushed while both pollers (1039426, 1198715) had only a `sleep` child; `YG_RESEARCH_SHA` in yarn_gate_lib.sh swapped atomically (cp, sed, `bash -n`, mv) to d5a953b2a5beb493750ff45e4505558af70cc107.
- Root adapter commit 0626276f3 on origin/main. Note: `/mnt/raid0/llm/views/epyc-root-main` must be at or past 0626276f3 (or EPYC_ROOT set) at decision time, else ruler records are rejected by the older adapter and listed in `belief_emit.excluded`.
- Fallback root `root-pbe-3c4ca599` fast-forwarded 4345b973c -> 0626276f3 (clean tree, ff-only). Orch `tests/unit/test_epyc_root_resolution.py` (hil6-b-orch worktree, orch venv): 6 passed.
- No inference was started, killed or armed.
