# KVU-16b replay kvu_off_b2048 (2026-10-04T05:28:40Z): **CAPPED** (fixed predicate)

- -b 2048 -ub 2048; prompts [79867, 79473, 79429, 79841]; budgets [27893, 19924, 12618, 5977]; wall 1222.7 s (cap 1200, capped=True)
- request -> slot/task: [{'req': 0, 'server_slot': 2, 'task': 34, 'log_slot': 2, 'log_task': 34, 'agree': True}, {'req': 1, 'server_slot': 1, 'task': 115, 'log_slot': 1, 'log_task': 115, 'agree': True}, {'req': 2, 'server_slot': 0, 'task': 197, 'log_slot': 0, 'log_task': 197, 'agree': True}, {'req': 3, 'server_slot': 3, 'task': 280, 'log_slot': 3, 'log_task': 280, 'agree': True}]
- TTFT own-send s [154.2, 316.0, 526.7, None]; first token since t0 [154.2, 470.2, 997.0, None]
- max requests decoding at once 3; max resident 267643; max resident while all 4 decoding 0
- KFD peak 51.692 GiB (budget 62.0); bad lines {'failed to find a memory slot': 0, 'Context size has been exceeded': 0}; failed []
- decode tok/s per request with all decoding: {}
