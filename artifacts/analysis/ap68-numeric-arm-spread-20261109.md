# Numeric trial arms: planner vs sampler

Planner trials: 188; sampler: 336 trials in 107 studies. Cells with both arms (n>=3): 30; planner narrower spread in 16, smaller step in 21.

| surface | param | planner n/spread/step | sampler n/spread/step |
|---|---|---|---|
| chat_long_context | chat.long_context_threshold_chars | 4/0.239784/0.24052 | 3/0.248935/None |
| chat_pipeline | chat.try_cheap_first_q_threshold | 5/0.170668/0.154152 | 5/0.170668/0.112042 |
| chat_review_skip | chat.review_skip_q_threshold | 4/0.117634/0.239349 | 2/0.084148/None |
| chat_summarization | chat.summarization_threshold_tokens | 4/0.221885/0.425531 | 3/0.251654/0.576222 |
| escalation | escalation.max_escalations | 7/0.338815/0.333333 | 70/0.353914/0.432927 |
| escalation | escalation.max_retries | 8/0.195156/0.321429 | 70/0.297974/0.518293 |
| gpu_placement_policy | placement_policy.lease_batch_weight | 3/0.177473/0.216809 | 3/0.177473/0.243586 |
| gpu_placement_policy | placement_policy.lease_eval_weight | 3/0.221052/0.437856 | 3/0.221052/0.340954 |
| gpu_placement_policy | placement_policy.lease_interactive_weight | 3/0.202368/0.240427 | 3/0.202368/0.13616 |
| gpu_placement_policy | placement_policy.long_running_trigger_tokens | 3/0.005854/0.011597 | 3/0.005854/0.01416 |
| gpu_placement_policy | placement_policy.min_resident_remaining_tokens | 3/0.04807/0.057812 | 3/0.04807/0.038542 |
| gpu_placement_policy | placement_policy.min_speedup | 3/0.105593/0.1769 | 3/0.105593/0.097569 |
| gpu_placement_policy | placement_policy.rate_window_tokens | 3/0.243325/0.494048 | 3/0.243325/0.407738 |
| kv_compaction | kv.keep_first | 1/0.0/None | 4/0.307226/0.357143 |
| kv_compaction | kv.keep_ratio | 4/0.296813/0.228487 | 4/0.091868/0.105447 |
| kv_compaction | kv.n_future | 2/0.085938/0.171875 | 4/0.141652/0.225 |
| memrl_retrieval | memrl_retrieval.confidence_threshold | 63/0.248319/0.238335 | 85/0.253268/0.306181 |
| memrl_retrieval | memrl_retrieval.min_q_value | 63/0.270326/0.24222 | 85/0.29294/0.368081 |
| memrl_retrieval | memrl_retrieval.min_similarity | 66/0.305945/0.25401 | 85/0.323398/0.357989 |
| memrl_retrieval | memrl_retrieval.prior_strength | 63/0.2601/0.259243 | 85/0.298253/0.384614 |
| memrl_retrieval | memrl_retrieval.q_weight | 63/0.305478/0.192503 | 85/0.290877/0.327292 |
| memrl_retrieval | memrl_retrieval.semantic_k | 69/0.300221/0.25719 | 85/0.301215/0.343791 |
| monitor | monitor.entropy_spike_threshold | 7/0.227262/0.256555 | 58/0.288331/0.422452 |
| monitor | monitor.entropy_threshold | 6/0.297844/0.287482 | 58/0.246673/0.370595 |
| monitor | monitor.repetition_threshold | 7/0.341959/0.497644 | 58/0.361607/0.503422 |
| repl_budget | repl.task_token_budget_cap | 7/0.344531/0.550696 | 11/0.335855/0.466855 |
| repl_budget | repl.worker_call_budget_cap | 8/0.124319/0.121805 | 11/0.186065/0.205263 |
| repl_executor | repl.frontdoor_non_tool_token_cap | 19/0.253271/0.261878 | 18/0.282051/0.297361 |
| repl_executor | repl.turn_token_cap | 20/0.251954/0.287226 | 18/0.247086/0.41599 |
| think_harder | think_harder.cot_roi_threshold | 7/0.23198/0.249043 | 63/0.235261/0.308548 |
| think_harder | think_harder.min_expected_roi | 19/0.165062/0.088649 | 63/0.220286/0.297398 |
| think_harder | think_harder.token_budget_max | 7/0.350986/0.398655 | 63/0.31195/0.440962 |
| think_harder | think_harder.token_budget_min | 6/0.151963/0.091462 | 63/0.304766/0.448216 |

planner arm = explicit params on the journaled action; sampler arm = Optuna study trials (journal rows store params={} for sampler trials). Values are normalized to parameter bounds, linear scale. Exact-repeat rate is AP-53's.
