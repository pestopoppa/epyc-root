# KVU-16b replay kvu_on_b512 (2026-10-04T06:20:01Z): **PASS** (fixed predicate)

- -b 512 -ub 512; prompts [79867, 79473, 79429, 79841]; budgets [27893, 19924, 12618, 5977]; wall 926.1 s (cap 1200, capped=False)
- request -> slot/task: [{'req': 0, 'server_slot': 2, 'task': 34, 'log_slot': 2, 'log_task': 34, 'agree': True}, {'req': 1, 'server_slot': 1, 'task': 259, 'log_slot': 1, 'log_task': 259, 'agree': True}, {'req': 2, 'server_slot': 0, 'task': 494, 'log_slot': 0, 'log_task': 494, 'agree': True}, {'req': 3, 'server_slot': 3, 'task': 740, 'log_slot': 3, 'log_task': 740, 'agree': True}]
- TTFT own-send s [163.9, 195.1, 238.0, 232.7]; first token since t0 [163.9, 359.0, 597.0, 829.7]
- max requests decoding at once 4; max resident 325556; max resident while all 4 decoding 325485
- KFD peak 48.585 GiB (budget 62.0); bad lines {'failed to find a memory slot': 0, 'Context size has been exceeded': 0}; failed []
- decode tok/s per request with all decoding: {2: 7.67, 1: 9.66, 0: 10.67, 3: 8.82}
