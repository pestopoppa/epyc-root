# KVU-16b replay kvu_off_b512 (2026-10-04T05:50:12Z): **CAPPED** (fixed predicate)

- -b 512 -ub 512; prompts [79867, 79473, 79429, 79841]; budgets [27893, 19924, 12618, 5977]; wall 1206.5 s (cap 1200, capped=True)
- request -> slot/task: [{'req': 0, 'server_slot': 2, 'task': 34, 'log_slot': 2, 'log_task': 34, 'agree': True}, {'req': 1, 'server_slot': 1, 'task': 264, 'log_slot': 1, 'log_task': 264, 'agree': True}, {'req': 2, 'server_slot': 0, 'task': 550, 'log_slot': 0, 'log_task': 550, 'agree': True}, {'req': 3, 'server_slot': 3, 'task': 875, 'log_slot': 3, 'log_task': 875, 'agree': True}]
- TTFT own-send s [208.3, 340.6, 569.9, None]; first token since t0 [208.3, 548.9, 1118.7, None]
- max requests decoding at once 3; max resident 252162; max resident while all 4 decoding 0
- KFD peak 48.565 GiB (budget 62.0); bad lines {'failed to find a memory slot': 0, 'Context size has been exceeded': 0}; failed []
- decode tok/s per request with all decoding: {}
