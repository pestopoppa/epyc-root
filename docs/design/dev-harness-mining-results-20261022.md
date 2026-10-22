# Dev-harness mining results: full run 20261022T1310Z

Aggregate-only write-up (counts, rates, CIs). Per-session and per-item data stays private under the
dev-harness private root. Source of every number: `data/dev_harness/mining-full-20261022T1310Z.aggregate.json` (reduced by
`scripts/dev_harness/publish_mining_results.py`, validated by `dh_privacy.validate_aggregate`, preflighted by
`raw_trace_publish_preflight`; cluster `top_terms` dropped because hashed-TF-IDF terms are transcript-derived).

Caveats: would-fire is today's predicate over historical calls (not a claim that the call was wrong); DHM-5
"always-on" is a file-size estimate (identical 8,326 for every non-Claude-main row), not a usage-field
measurement; opencode `write_*_outside_allowlist` counts are inflated by that harness working outside the
Claude allowlist roots and are not violations by themselves; OAB-LB1 reads vault rollout copies, UFH14-LB8
read-only snapshots.

Run `full-20261022T1310Z`: 42,420 units, 863 interrupt candidates, 13,989 cluster docs, 80 clusters, planted 3/5, would-fire total 21,924.

## DHM-1 interrupts per 1000 turns (any marker, Wilson 95% CI)

| harness | role | k/turns | per 1000 | 95% CI |
|---|---|---|---|---|
| claude_code | all | 394/219,268 | 1.797 | 1.628-1.983 |
| claude_code | main | 380/60,294 | 6.303 | 5.702-6.966 |
| claude_code | subagent | 14/158,974 | 0.088 | 0.052-0.148 |
| codex | all | 294/97,559 | 3.014 | 2.689-3.378 |
| codex | main | 116/16,987 | 6.829 | 5.697-8.184 |
| codex | subagent | 178/80,572 | 2.209 | 1.908-2.558 |
| opencode | all | 82/89,463 | 0.917 | 0.739-1.137 |
| opencode | main | 56/78,445 | 0.714 | 0.550-0.927 |
| opencode | subagent | 26/11,018 | 2.360 | 1.611-3.455 |

## DHM-2 would-fire per 1000 tool calls (by harness)

| class | claude_code | codex | opencode |
|---|---|---|---|
| bare_gitnexus_analyze | 0.0667 | 0.0808 | - |
| edit_running_script | 1.4516 | 0.085 | 0.6673 |
| git_clean | 0.025 | 0.0043 | 0.0212 |
| git_reset_hard | 0.292 | 0.0298 | 0.0318 |
| git_stash | 1.1555 | 0.0043 | 0.4025 |
| git_worktree_prune_or_force | 1.1263 | 0.9396 | 0.2224 |
| glob_rm | 0.7508 | 0.0064 | 0.4978 |
| hooks_path_null | 0.0501 | 0.1892 | - |
| llama_cli_unbounded | 0.1627 | 0.1552 | 0.2648 |
| no_verify | 0.0959 | 0.0064 | 0.0106 |
| pattern_kill | 0.5339 | 0.0531 | 0.1377 |
| pgrep_pattern | 3.5874 | 2.0153 | 17.573 |
| piped_gate_push | 0.1877 | 0.0021 | 0.0318 |
| run_benchmark_invocation | 0.2461 | 0.3359 | 0.1695 |
| test_deleted | 0.3629 | 0.0213 | 0.053 |
| test_deselect | 0.1961 | 0.102 | 0.0424 |
| test_skip_added | 0.1377 | 0.0149 | 0.0318 |
| wholesale_git_add | 1.0428 | 0.0638 | 0.6356 |
| write_outside_allowlist | 8.8891 | 2.7828 | 47.6665 |
| write_tool_outside_allowlist | 0.3587 | 0.2424 | 75.6096 |

## DHM-2 would-fire counts per class and harness (all sources)

| class | claude_code | codex | opencode |
|---|---|---|---|
| bare_gitnexus_analyze | 16 (blocked 0, slipped 16) | 38 (blocked 0, slipped 34) | 0 (blocked 0, slipped 0) |
| edit_running_script | 348 (blocked 3, slipped 328) | 40 (blocked 0, slipped 40) | 63 (blocked 0, slipped 63) |
| git_clean | 6 (blocked 3, slipped 3) | 2 (blocked 0, slipped 2) | 2 (blocked 0, slipped 2) |
| git_reset_hard | 70 (blocked 6, slipped 61) | 14 (blocked 0, slipped 14) | 3 (blocked 0, slipped 3) |
| git_stash | 277 (blocked 96, slipped 175) | 2 (blocked 0, slipped 2) | 38 (blocked 0, slipped 38) |
| git_worktree_prune_or_force | 270 (blocked 11, slipped 247) | 442 (blocked 0, slipped 432) | 21 (blocked 0, slipped 21) |
| glob_rm | 180 (blocked 12, slipped 149) | 3 (blocked 0, slipped 2) | 47 (blocked 0, slipped 47) |
| hooks_path_null | 12 (blocked 1, slipped 11) | 89 (blocked 0, slipped 88) | 0 (blocked 0, slipped 0) |
| llama_cli_unbounded | 39 (blocked 5, slipped 27) | 73 (blocked 0, slipped 65) | 25 (blocked 1, slipped 24) |
| no_verify | 23 (blocked 5, slipped 16) | 3 (blocked 0, slipped 3) | 1 (blocked 0, slipped 1) |
| pattern_kill | 128 (blocked 9, slipped 10) | 25 (blocked 0, slipped 5) | 13 (blocked 0, slipped 12) |
| pgrep_pattern | 860 (blocked 6, slipped 769) | 948 (blocked 0, slipped 889) | 1659 (blocked 0, slipped 1658) |
| piped_gate_push | 45 (blocked 4, slipped 40) | 1 (blocked 0, slipped 1) | 3 (blocked 0, slipped 3) |
| run_benchmark_invocation | 59 (blocked 0, slipped 59) | 158 (blocked 0, slipped 150) | 16 (blocked 0, slipped 16) |
| test_deleted | 87 (blocked 11, slipped 74) | 10 (blocked 0, slipped 10) | 5 (blocked 0, slipped 5) |
| test_deselect | 47 (blocked 0, slipped 45) | 48 (blocked 0, slipped 46) | 4 (blocked 0, slipped 4) |
| test_skip_added | 33 (blocked 0, slipped 32) | 7 (blocked 0, slipped 7) | 3 (blocked 0, slipped 3) |
| wholesale_git_add | 250 (blocked 51, slipped 198) | 30 (blocked 0, slipped 16) | 60 (blocked 0, slipped 60) |
| write_outside_allowlist | 2131 (blocked 1168, slipped 897) | 1309 (blocked 2, slipped 1155) | 4500 (blocked 2, slipped 4371) |
| write_tool_outside_allowlist | 86 (blocked 0, slipped 81) | 114 (blocked 0, slipped 105) | 7138 (blocked 0, slipped 7082) |

## DHM-3 violations per 1000 tool calls, pre vs post lesson (rate [k])

| lesson | harness | segments |
|---|---|---|
| glob_rm | claude_code | post_lesson_prose_only: 1.2999 [56] ; pre_lesson: 0.6195 [116] |
| glob_rm | codex | post_lesson_prose_only: 0.0 [0] ; pre_lesson: 0.0073 [3] |
| glob_rm | opencode | post_lesson_prose_only: 0.0 [0] ; pre_lesson: 0.5012 [47] |
| llama_cli_unbounded | claude_code | post_hook: 0.0317 [5] ; post_lesson_prose_only: 0.0 [0] ; pre_lesson: 0.453 [33] |
| llama_cli_unbounded | codex | post_hook_harness_uncovered: 0.0061 [1] ; post_lesson_prose_only: 0.0 [0] ; pre_lesson: 0.2619 [72] |
| llama_cli_unbounded | opencode | post_hook_harness_uncovered: 0.0 [0] ; post_lesson_prose_only: 0.0 [0] ; pre_lesson: 1.4311 [22] |
| pattern_kill | claude_code | post_hook: 0.0891 [15] ; post_lesson_prose_only: 0.0 [0] ; pre_lesson: 1.7109 [113] |
| pattern_kill | codex | post_hook_harness_uncovered: 0.0 [0] ; post_lesson_prose_only: 0.0 [0] ; pre_lesson: 0.1512 [25] |
| pattern_kill | opencode | post_hook_harness_uncovered: 0.1193 [11] ; pre_lesson: 0.9112 [2] |
| piped_gate_push | claude_code | post_lesson_prose_only: 0.0 [0] ; pre_lesson: 0.2626 [45] |
| piped_gate_push | codex | post_lesson_prose_only: 0.0 [0] ; pre_lesson: 0.0024 [1] |
| piped_gate_push | opencode | post_lesson_prose_only: 0.0 [0] ; pre_lesson: 0.0336 [3] |
| wholesale_git_add | claude_code | post_hook: 1.2208 [224] ; post_lesson_prose_only: 0.5576 [19] ; pre_lesson: 0.3557 [7] |
| wholesale_git_add | codex | post_hook_harness_uncovered: 0.0373 [12] ; post_lesson_prose_only: 0.0381 [5] ; pre_lesson: 0.8102 [12] |
| wholesale_git_add | opencode | post_hook_harness_uncovered: 0.629 [58] ; post_lesson_prose_only: 0.8818 [1] ; pre_lesson: 0.9425 [1] |

## DHM-5 always-on prefix

| harness | role | always-on est tok/turn (file-size estimate) | first-turn prompt p50 | share of first turn p50 | cache-read share | turns |
|---|---|---|---|---|---|---|
| claude_code | main | 17157.8 | 38056.0 | 0.4509 | 0.9775 | 60,294 |
| claude_code | subagent | 8326.4 | 43402.0 | 0.1918 | 0.9641 | 158,974 |
| codex | main | 8326.4 | 41971.0 | 0.1984 | 0.9125 | 16,987 |
| codex | subagent | 8326.4 | 24105.5 | 0.3454 | 0.9762 | 80,572 |
| opencode | main | 8326.4 | 2595.0 | 3.2086 | 0.9697 | 78,445 |
| opencode | subagent | 8326.4 | 13844.0 | 0.6014 | 0.9843 | 11,018 |

## DHM-7.2 TF-IDF baseline

13,989 docs, k=80, 80 reported, planted 3/5.

| planted class | recovered | best purity |
|---|---|---|
| fs_containment | 1 | 0.141 |
| git_stash | 1 | 0.128 |
| pattern_kill | 0 | 0.375 |
| pytest_workers | 0 | 0.375 |
| wholesale_add | 1 | 0.255 |

## OAB-LB1

15,144 threads, 15,115/15,144 turns completed, 60,718 tool calls, exec wall 9,651.1 s. Turn failures: `{"aborted_interrupted": {"ci95_hi": 0.0679, "ci95_lo": 0.0103, "k": 4, "n": 15144, "per_100": 0.0264}, "no_terminal_event": {"ci95_hi": 0.2436, "ci95_lo": 0.1118, "k": 25, "n": 15144, "per_100": 0.1651}, "not_completed": {"ci95_hi": 0.2749, "ci95_lo": 0.1334, "k": 29, "n": 15144, "per_100": 0.1915}}`.

## UFH14-LB8

202 sessions, 8 days. Prefix hit token-weighted 0.9149 (0.9397 excl. first step); per-step p50 0.988, p10 0.124, n=4,093. Gap p50 human 48.113 s vs tool 3.755 s. Append-length bimodality coefficient (log2) 0.5132.
## Reading
- Operator interrupts concentrate in MAIN sessions (Claude 6.3, Codex 6.8 per 1000 turns); Claude subagents are
  near zero (0.088), Codex/opencode subagent interrupts are not (2.2 / 2.4).
- Hooks work where present: `pattern_kill` 1.71 -> 0.089 and `llama_cli_unbounded` 0.45 -> 0.032 per 1000 tool calls
  on Claude after the hook; prose-only `glob_rm` ROSE 0.62 -> 1.30, so that lesson is not holding.
- `wholesale_git_add` on Claude is 0.36 pre, 0.56 prose-only, 1.22 post-hook (k=224): a hook era with MORE hits.
  Unattributed: harness mix, campaign sessions, or a hook gap (task DHM-9).
- Codex and opencode have no hook coverage (`harness_uncovered`): nearly every would-fire there slipped through.
- DHM-7.2 TF-IDF baseline recovers 3/5 planted classes (`pattern_kill`, `pytest_workers` missed); 7.2a pending.
