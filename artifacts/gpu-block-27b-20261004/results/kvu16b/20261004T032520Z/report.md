# KVU-16b — concurrent residency on the 393216 pool (2026-10-04T03:53:36Z): **PASS**

- prompts [79877, 79487, 79443, 79836] (sum 318643); budgets [27861, 19901, 12604, 5970]; residual before 68508
- first token at +s [181.4, 525.1, 1069.7, None]
- max slots decoding at once 4; max resident 310461; max resident while all 4 decoding 308416 (threshold 300000)
- bad lines {'failed to find a memory slot': 0, 'Context size has been exceeded': 0}; KFD peak 58.879 GiB (budget 62.0); failed requests []
- decode tok/s per slot with all 4 decoding: {0: 0.0, 1: 0.16, 2: 0.22, 3: 0.14} (sum 0.52)
- idle-purge evidence (production flags): {"residual_before": 68508, "per_slot_before": {"0": 17128, "1": 17132, "2": 17127, "3": 17121}, "probe_http": 200, "per_slot_after": {"0": 44, "1": 0, "2": 0, "3": 0}, "idle_saves_logged": 0, "clear_nonzero_logged": 0, "clear_nonzero_tokens": 0, "purged": false, "residual_used_for_budget": 44}
- server log bytes 27474003-27525049 of /mnt/raid0/llm/epyc-orchestrator/logs/llama-server-8083.log
