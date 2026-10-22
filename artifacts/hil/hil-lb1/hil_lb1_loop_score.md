# HIL-LB1 loop-detector scoring

Tokenizer: `/mnt/raid0/llm/hf-models/Qwen3-4B-Instruct-2507/tokenizer.json` sha256 `aeb13307a71acd8f`. Zero inference, deterministic.

## Who&When Pro text split — injected behaviour, not natural frequency; positives = mode A.4 (all in alfagent)

Loop N=53; frameworks: {'alfagent': 311, 'macnet': 261, 'metagpt': 81, 'smolagents': 3276, 'magentic-one': 811, 'debate': 445, 'dylan': 152, 'mathchat': 920}.

### population: all

| detector | N | pos | TP | FP | FN | TN | precision | recall | F1 | FP rate on neg |
|---|---|---|---|---|---|---|---|---|---|---|
| prevalence_baseline (flag all) | 6257 | 53 | 53 | 6204 | 0 | 0 | 0.0085 | 1.0 | 0.0168 | 1.0 |
| l2_loop_existing | 6257 | 53 | 33 | 92 | 20 | 6112 | 0.264 | 0.6226 | 0.3708 | 0.0148 |
| l2_loop_existing_exempt | 6257 | 53 | 32 | 87 | 21 | 6117 | 0.2689 | 0.6038 | 0.3721 | 0.014 |
| repeated_call_2395_ge1 | 6257 | 53 | 53 | 416 | 0 | 5788 | 0.113 | 1.0 | 0.2031 | 0.0671 |
| repeated_call_2395_ge1_exempt | 6257 | 53 | 53 | 415 | 0 | 5789 | 0.1132 | 1.0 | 0.2035 | 0.0669 |
| token_period_stream | 6257 | 53 | 7 | 15 | 46 | 6189 | 0.3182 | 0.1321 | 0.1867 | 0.0024 |
| token_period_stream_exempt | 6257 | 53 | 6 | 13 | 47 | 6191 | 0.3158 | 0.1132 | 0.1667 | 0.0021 |
| paraphrase_stream_exempt | 6257 | 53 | 0 | 0 | 53 | 6204 | None | 0.0 | 0.0 | 0.0 |
| paraphrase_norm_stream_exempt | 6257 | 53 | 4 | 4 | 49 | 6200 | 0.5 | 0.0755 | 0.1311 | 0.0006 |
| locals_tools_guard_stream_exempt | 6257 | 53 | 6 | 13 | 47 | 6191 | 0.3158 | 0.1132 | 0.1667 | 0.0021 |
| in_grammar_stream_exempt | 6257 | 53 | 0 | 0 | 53 | 6204 | None | 0.0 | 0.0 | 0.0 |
| no_tools_stream_exempt | 6257 | 53 | 0 | 0 | 53 | 6204 | None | 0.0 | 0.0 | 0.0 |
| token_period_reply | 6257 | 53 | 0 | 7 | 53 | 6197 | 0.0 | 0.0 | 0.0 | 0.0011 |
| paraphrase_reply | 6257 | 53 | 0 | 2 | 53 | 6202 | 0.0 | 0.0 | 0.0 | 0.0003 |
| in_grammar_reply | 6257 | 53 | 0 | 0 | 53 | 6204 | None | 0.0 | 0.0 | 0.0 |
| repeated_call_2395_ge2_exempt (descriptive sweep) | 6257 | 53 | 53 | 254 | 0 | 5950 | 0.1726 | 1.0 | 0.2944 | 0.0409 |
| repeated_call_2395_ge3_exempt (descriptive sweep) | 6257 | 53 | 48 | 218 | 5 | 5986 | 0.1805 | 0.9057 | 0.3009 | 0.0351 |
| repeated_call_2395_ge5_exempt (descriptive sweep) | 6257 | 53 | 35 | 167 | 18 | 6037 | 0.1733 | 0.6604 | 0.2745 | 0.0269 |

### population: alfagent

| detector | N | pos | TP | FP | FN | TN | precision | recall | F1 | FP rate on neg |
|---|---|---|---|---|---|---|---|---|---|---|
| prevalence_baseline (flag all) | 311 | 53 | 53 | 258 | 0 | 0 | 0.1704 | 1.0 | 0.2912 | 1.0 |
| l2_loop_existing | 311 | 53 | 33 | 80 | 20 | 178 | 0.292 | 0.6226 | 0.3976 | 0.3101 |
| l2_loop_existing_exempt | 311 | 53 | 32 | 75 | 21 | 183 | 0.2991 | 0.6038 | 0.4 | 0.2907 |
| repeated_call_2395_ge1 | 311 | 53 | 53 | 244 | 0 | 14 | 0.1785 | 1.0 | 0.3029 | 0.9457 |
| repeated_call_2395_ge1_exempt | 311 | 53 | 53 | 243 | 0 | 15 | 0.1791 | 1.0 | 0.3037 | 0.9419 |
| token_period_stream | 311 | 53 | 7 | 14 | 46 | 244 | 0.3333 | 0.1321 | 0.1892 | 0.0543 |
| token_period_stream_exempt | 311 | 53 | 6 | 12 | 47 | 246 | 0.3333 | 0.1132 | 0.169 | 0.0465 |
| paraphrase_stream_exempt | 311 | 53 | 0 | 0 | 53 | 258 | None | 0.0 | 0.0 | 0.0 |
| paraphrase_norm_stream_exempt | 311 | 53 | 4 | 4 | 49 | 254 | 0.5 | 0.0755 | 0.1311 | 0.0155 |
| locals_tools_guard_stream_exempt | 311 | 53 | 6 | 12 | 47 | 246 | 0.3333 | 0.1132 | 0.169 | 0.0465 |
| in_grammar_stream_exempt | 311 | 53 | 0 | 0 | 53 | 258 | None | 0.0 | 0.0 | 0.0 |
| no_tools_stream_exempt | 311 | 53 | 0 | 0 | 53 | 258 | None | 0.0 | 0.0 | 0.0 |
| token_period_reply | 311 | 53 | 0 | 0 | 53 | 258 | None | 0.0 | 0.0 | 0.0 |
| paraphrase_reply | 311 | 53 | 0 | 0 | 53 | 258 | None | 0.0 | 0.0 | 0.0 |
| in_grammar_reply | 311 | 53 | 0 | 0 | 53 | 258 | None | 0.0 | 0.0 | 0.0 |
| repeated_call_2395_ge2_exempt (descriptive sweep) | 311 | 53 | 53 | 222 | 0 | 36 | 0.1927 | 1.0 | 0.3232 | 0.8605 |
| repeated_call_2395_ge3_exempt (descriptive sweep) | 311 | 53 | 48 | 206 | 5 | 52 | 0.189 | 0.9057 | 0.3127 | 0.7984 |
| repeated_call_2395_ge5_exempt (descriptive sweep) | 311 | 53 | 35 | 160 | 18 | 98 | 0.1795 | 0.6604 | 0.2823 | 0.6202 |

### fire timing on positives (vs injected step)

| detector | timing |
|---|---|
| l2_loop_existing | {'no_fire': 20, 'at_or_after_injected_step': 31, 'before_injected_step': 2} |
| l2_loop_existing_exempt | {'no_fire': 21, 'at_or_after_injected_step': 30, 'before_injected_step': 2} |
| repeated_call_2395_ge1 | {'at_or_after_injected_step': 47, 'before_injected_step': 6} |
| repeated_call_2395_ge1_exempt | {'at_or_after_injected_step': 48, 'before_injected_step': 5} |
| token_period_stream | {'no_fire': 46, 'at_or_after_injected_step': 7} |
| token_period_stream_exempt | {'no_fire': 47, 'at_or_after_injected_step': 6} |
| paraphrase_stream_exempt | {'no_fire': 53} |
| paraphrase_norm_stream_exempt | {'no_fire': 49, 'at_or_after_injected_step': 4} |
| locals_tools_guard_stream_exempt | {'no_fire': 47, 'at_or_after_injected_step': 6} |
| in_grammar_stream_exempt | {'no_fire': 53} |
| no_tools_stream_exempt | {'no_fire': 53} |
| token_period_reply | {'no_fire': 53} |
| paraphrase_reply | {'no_fire': 53} |
| in_grammar_reply | {'no_fire': 53} |

Exemption: {'traces_with_any_exempt_call': 177, 'exempt_calls_total': 403, 'alfagent_traces_with_any_exempt_call': 177}

## Constrained-output fixtures

| fixture | degenerate | tokens | current guard (chunk) | tools (tok) | in_grammar (tok) | no_tools (tok) |
|---|---|---|---|---|---|---|
| td1_24q_varying | False | 1155 | 900 | None | None | None |
| td1_24q_identical | False | 1113 | 150 | 144 | None | None |
| grid_64_identical_rows | False | 1602 | 250 | 76 | 1425 | 1325 |
| identical_obj_x40_then_close | False | 1842 | None | 139 | 1761 | 1577 |
| runaway_identical_obj_to_limit | True | 4096 | None | 133 | 1729 | 1553 |
| legit_prefix_then_runaway | True | 4096 | 1000 | 693 | 2198 | 2050 |

Legitimate identical-row sweep (closed arrays; any fire here cuts a legitimate reply):

| shape | tokens | in_grammar (tok) | no_tools (tok) |
|---|---|---|---|
| grid_row_x16 | 402 | None | None |
| compact_obj_x16 | 562 | None | None |
| grid_row_x32 | 802 | None | None |
| compact_obj_x32 | 1122 | None | None |
| grid_row_x48 | 1202 | None | None |
| compact_obj_x48 | 1682 | 1585 | 1445 |
| grid_row_x64 | 1602 | 1425 | 1325 |
| compact_obj_x64 | 2242 | 1585 | 1445 |
| grid_row_x96 | 2402 | 1425 | 1325 |
| compact_obj_x96 | 3362 | 1585 | 1445 |
| grid_row_x128 | 3202 | 1425 | 1325 |
| compact_obj_x128 | 4482 | 1585 | 1445 |

## Recorded EPYC replies (inference tap, unlabelled)

```
{
 "files": [
  "inference_tap_events.jsonl",
  "inference_tap_events.jsonl"
 ],
 "label": "none (natural recorded replies; firing counts only)",
 "json_shaped_is_a_proxy": "reply text starts with { or [ (request grammar flag is not recorded in the tap)",
 "counts": {
  "all": {
   "n": 3576,
   "current_guard": 26,
   "tools_token_period": 0,
   "paraphrase": 2,
   "in_grammar": 0,
   "no_tools": 0,
   "periodic_tail_at_end_in_grammar": 0,
   "reply_tokens_ge_4096": 60,
   "current_guard_fire_is_last_chunk (cut live)": 16,
   "current_guard_fire_reply_continued (guard inactive)": 10,
   "current_guard_fire_reply_is_valid_json": 8
  },
  "json_shaped": {
   "n": 649,
   "current_guard": 26,
   "tools_token_period": 0,
   "paraphrase": 2,
   "in_grammar": 0,
   "no_tools": 0,
   "periodic_tail_at_end_in_grammar": 0,
   "reply_tokens_ge_4096": 0,
   "current_guard_fire_is_last_chunk (cut live)": 16,
   "current_guard_fire_reply_continued (guard inactive)": 10,
   "current_guard_fire_reply_is_valid_json": 8
  }
 },
 "reply_tokens_p50_p90_p99_max": [
  19,
  746,
  5487,
  8196
 ]
}
```

## Natural coding sessions (unlabelled) — test-after-edit exemption effect

```
{
 "n_files": 150,
 "label": "none (natural sessions; firing counts only)",
 "counts": {
  "calls": 11376,
  "exempt_calls": 2,
  "l2_loop_existing|fires_exempt": 0,
  "l2_loop_existing|fires_raw": 0,
  "l2_loop_existing|flipped_by_exemption": 0,
  "mutating_calls": 584,
  "repeated_call_ge1|fires_exempt": 44,
  "repeated_call_ge1|fires_raw": 44,
  "repeated_call_ge1|flipped_by_exemption": 0,
  "sessions_with_calls": 150,
  "sessions_with_exempt_call": 1,
  "token_period_stream|fires_exempt": 6,
  "token_period_stream|fires_raw": 6,
  "token_period_stream|flipped_by_exemption": 0,
  "verifying_calls": 398
 }
}
```

