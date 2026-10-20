(q0 reps discarded for overlapping the contamination windows: 26)
### qwen-tts, final claim (candidate = build2, total ms/frame, lower is better)
| leg | variant | n | median | min-max | vs prod | neighbour tok/s in window (median) |
|---|---|---|---|---|---|---|
| quiet_1T | prod | 5 | 89.5 | 85.5-91.4 |  |  |
| quiet_1T | exp_ctl | 5 | 86.8 | 85.8-90.1 | x1.03 |  |
| quiet_1T | exp_pool | 5 | 92.6 | 90.4-97.1 | x0.97 |  |
| quiet_1T | exp_default | 5 | 93.3 | 89.7-95.6 | x0.96 |  |
| quiet_8T_free | prod | 5 | 25.8 | 24.4-27.4 |  |  |
| quiet_8T_free | exp_ctl | 5 | 24.6 | 23.4-24.9 | x1.05 |  |
| quiet_8T_free | exp_pool | 5 | 23.0 | 22.8-23.9 | x1.12 |  |
| quiet_8T_free | exp_default | 5 | 23.6 | 23.2-27.4 | x1.09 |  |
| quiet_8T_pinned | prod | 5 | 40.1 | 36.4-50.4 |  |  |
| quiet_8T_pinned | exp_ctl | 5 | 38.9 | 36.6-43.3 | x1.03 |  |
| quiet_8T_pinned | exp_pool | 5 | 35.5 | 35.1-36.1 | x1.13 |  |
| quiet_8T_pinned | exp_default | 5 | 35.5 | 35.3-38.4 | x1.13 |  |
| quiet_1T | prod/AA | 5 | 97.6 | 94.8-100.1 |  |  |
| quiet_8T_free | prod/AA | 5 | 24.6 | 23.8-27.2 |  |  |
| quiet_8T_pinned | prod/AA | 5 | 40.0 | 35.6-45.1 |  |  |
| cont_1T_1spin | prod | 5 | 197.0 | 191.4-203.9 |  |  |
| cont_1T_1spin | exp_pool | 5 | 196.5 | 183.0-202.8 | x1.00 |  |
| cont_1T_1spin | exp_default | 7 | 185.9 | 178.7-201.0 | x1.06 |  |
| nb_8T | prod | 2 | 13379.5 | 13337.7-13421.2 |  | 0.35 |
| nb_8T | exp_default | 3 | 423.6 | 416.5-425.3 | x31.59 | 9.91 |
| cont_8T_8spin | exp_default | 3 | 495.2 | 478.7-513.0 |  |  |
| cont_8T_8spin | prod | 3 | 9984.2 | 9666.3-11254.9 |  |  |
| cont_8T_1spin | prod | 5 | 715.6 | 613.7-777.6 |  |  |
| cont_8T_1spin | exp_pool | 5 | 580.3 | 480.0-757.5 | x1.23 |  |
| cont_8T_1spin | exp_default | 5 | 63.6 | 60.2-65.1 | x11.25 |  |
| nb_1T | prod | 3 (TO=1) | 189.5 | 189.4-194.1 |  | 5.96 |
| nb_1T | exp_default | 3 | 179.0 | 178.9-180.9 | x1.06 | 6.17 |
neighbour alone nb_1T: median 13.38 tok/s over 39 reps (llama-bench internal avg 13.40)
neighbour alone nb_8T: median 17.00 tok/s over 39 reps (llama-bench internal avg 16.61)
neighbour alone nb_1T: median 14.24 tok/s over 39 reps (llama-bench internal avg 14.22)
neighbour alone nb_8T: median 27.85 tok/s over 39 reps (llama-bench internal avg 27.50)
neighbour alone nb_1T: median 14.60 tok/s over 39 reps (llama-bench internal avg 14.59)
neighbour alone nb_8T: median 27.80 tok/s over 39 reps (llama-bench internal avg 26.34)
neighbour alone nb_1T: median 14.37 tok/s over 39 reps (llama-bench internal avg 14.33)
neighbour alone nb_8T: median 27.50 tok/s over 39 reps (llama-bench internal avg 27.19)

### qwen-tts, first claim (older fixed-budget builds; fixed-spin futex/yield variants), total ms/frame
| leg | variant | n | median | min-max | vs prod | neighbour tok/s in window (median) |
|---|---|---|---|---|---|---|
| quiet_1T | prod | 5 | 88.0 | 87.1-90.1 |  |  |
| quiet_1T | exp_ctl | 5 | 87.0 | 84.3-87.6 | x1.01 |  |
| quiet_1T | exp_pool | 5 | 85.8 | 83.9-88.3 | x1.03 |  |
| quiet_1T | exp_yield | 5 | 87.1 | 85.5-90.5 | x1.01 |  |
| quiet_1T | exp_futex | 5 | 88.5 | 85.7-88.7 | x1.00 |  |
| quiet_8T_free | prod | 5 | 23.5 | 22.9-24.0 |  |  |
| quiet_8T_free | exp_ctl | 5 | 23.0 | 22.9-23.4 | x1.02 |  |
| quiet_8T_free | exp_pool | 5 | 23.2 | 22.9-26.8 | x1.01 |  |
| quiet_8T_free | exp_yield | 5 | 23.9 | 23.1-26.0 | x0.98 |  |
| quiet_8T_free | exp_futex | 5 | 24.0 | 23.1-26.9 | x0.98 |  |
| quiet_8T_pinned | prod | 5 | 37.6 | 37.0-43.4 |  |  |
| quiet_8T_pinned | exp_ctl | 5 | 37.4 | 36.5-41.9 | x1.01 |  |
| quiet_8T_pinned | exp_pool | 5 | 35.7 | 35.5-38.4 | x1.06 |  |
| quiet_8T_pinned | exp_yield | 5 | 35.5 | 35.2-35.7 | x1.06 |  |
| quiet_8T_pinned | exp_futex | 5 | 35.8 | 35.5-38.4 | x1.05 |  |
| cont_1T_1spin | prod | 5 | 192.0 | 190.9-197.3 |  |  |
| cont_1T_1spin | exp_ctl | 5 | 179.0 | 175.2-185.4 | x1.07 |  |
| cont_1T_1spin | exp_pool | 5 | 178.6 | 175.3-179.1 | x1.08 |  |
| cont_1T_1spin | exp_yield | 5 | 176.1 | 175.0-180.6 | x1.09 |  |
| cont_1T_1spin | exp_futex | 5 | 174.8 | 173.4-177.5 | x1.10 |  |
| cont_8T_1spin | prod | 5 | 791.1 | 620.0-1318.9 |  |  |
| cont_8T_1spin | exp_ctl | 5 | 1040.5 | 898.3-1128.5 | x0.76 |  |
| cont_8T_1spin | exp_pool | 5 | 398.1 | 157.8-855.0 | x1.99 |  |
| cont_8T_1spin | exp_yield | 5 | 223.0 | 202.2-231.6 | x3.55 |  |
| cont_8T_1spin | exp_futex | 5 | 204.0 | 203.6-205.3 | x3.88 |  |
| quiet_1T | prod/AA | 5 | 96.3 | 94.4-97.5 |  |  |
| quiet_8T_free | prod/AA | 5 | 24.6 | 24.2-27.1 |  |  |
| quiet_8T_pinned | prod/AA | 5 | 38.1 | 36.1-43.4 |  |  |
| nb_1T | prod | 5 | 194.7 | 188.4-199.5 |  |  |
| nb_1T | exp_ctl | 5 | 184.2 | 182.2-187.3 | x1.06 |  |
| nb_1T | exp_pool | 5 | 186.9 | 184.9-191.8 | x1.04 |  |
| nb_1T | exp_yield | 5 | 184.8 | 183.1-190.2 | x1.05 |  |
| nb_1T | exp_futex | 5 | 182.8 | 179.9-190.9 | x1.06 |  |
| nb_8T | prod | 5 | 11851.1 | 11344.1-12591.1 |  |  |
| nb_8T | exp_ctl | 1 | 12372.4 | 12372.4-12372.4 | x0.96 |  |

### whisper-cli large-v3-turbo, 13/30 s window, total ms (lower is better)
| leg | variant | n | median | min-max | vs prod | neighbour tok/s in window (median) |
|---|---|---|---|---|---|---|
| quiet_8T_free | prod | 3 | 4623.2 | 4590.2-5129.5 |  |  |
| quiet_8T_free | exp_pool | 3 | 4683.5 | 4625.1-4710.1 | x0.99 |  |
| quiet_8T_free | exp_yield | 3 | 4675.4 | 4519.6-4764.4 | x0.99 |  |
| quiet_8T_free | exp_futex | 3 | 4371.5 | 4353.8-4441.1 | x1.06 |  |
| cont_8T_1spin | prod | 3 | 13842.1 | 13535.5-15130.8 |  |  |
| cont_8T_1spin | exp_pool | 3 | 12646.8 | 12195.1-13796.0 | x1.09 |  |
| cont_8T_1spin | exp_yield | 3 | 9285.4 | 9207.7-9353.8 | x1.49 |  |
| cont_8T_1spin | exp_futex | 3 | 5665.7 | 5630.0-5751.2 | x2.44 |  |
| nb_8T | prod | 3 | 32179.6 | 30708.2-32262.9 |  | 0.08 |
| nb_8T | exp_pool | 3 | 30451.1 | 28213.3-31959.3 | x1.06 | 0.78 |
| nb_8T | exp_yield | 3 | 16359.0 | 16166.9-17617.0 | x1.97 | 1.68 |
| nb_8T | exp_futex | 3 | 12899.7 | 12463.3-13690.8 | x2.49 | 2.04 |
| cont_8T_8spin | prod | 2 | 30072.7 | 29736.4-30409.0 |  |  |
| cont_8T_8spin | exp_pool | 2 | 24238.2 | 23871.6-24604.7 | x1.24 |  |
| cont_8T_8spin | exp_yield | 2 | 18962.9 | 18809.9-19115.9 | x1.59 |  |
| cont_8T_8spin | exp_futex | 2 | 12710.1 | 12548.2-12872.1 | x2.37 |  |
neighbour alone nb_1T: median 14.69 tok/s over 39 reps (llama-bench internal avg 14.66)
neighbour alone nb_8T: median 27.47 tok/s over 39 reps (llama-bench internal avg 27.28)

### whisper-cli, encode ms
| leg | variant | n | median | min-max | vs prod | neighbour tok/s in window (median) |
|---|---|---|---|---|---|---|
| quiet_8T_free | prod | 3 | 4281.9 | 4248.9-4758.9 |  |  |
| quiet_8T_free | exp_pool | 3 | 4341.4 | 4275.6-4356.9 | x0.99 |  |
| quiet_8T_free | exp_yield | 3 | 4341.5 | 4176.6-4422.9 | x0.99 |  |
| quiet_8T_free | exp_futex | 3 | 4039.4 | 4017.5-4107.9 | x1.06 |  |
| cont_8T_1spin | prod | 3 | 6732.0 | 6531.4-7309.2 |  |  |
| cont_8T_1spin | exp_pool | 3 | 6373.0 | 6315.4-7099.6 | x1.06 |  |
| cont_8T_1spin | exp_yield | 3 | 8687.5 | 8657.5-8838.7 | x0.77 |  |
| cont_8T_1spin | exp_futex | 3 | 5237.0 | 5223.2-5337.8 | x1.29 |  |
| nb_8T | prod | 3 | 12668.8 | 12343.8-12726.6 |  | 0.08 |
| nb_8T | exp_pool | 3 | 14041.5 | 13843.8-14325.6 | x0.90 | 0.78 |
| nb_8T | exp_yield | 3 | 13065.2 | 12884.6-13243.2 | x0.97 | 1.68 |
| nb_8T | exp_futex | 3 | 11039.5 | 10990.8-11498.8 | x1.15 | 2.04 |
| cont_8T_8spin | prod | 2 | 13920.7 | 13906.2-13935.3 |  |  |
| cont_8T_8spin | exp_pool | 2 | 14252.0 | 14116.8-14387.3 | x0.98 |  |
| cont_8T_8spin | exp_yield | 2 | 12512.5 | 12509.3-12515.7 | x1.11 |  |
| cont_8T_8spin | exp_futex | 2 | 11148.1 | 10957.8-11338.4 | x1.25 |  |
neighbour alone nb_1T: median 14.69 tok/s over 39 reps (llama-bench internal avg 14.66)
neighbour alone nb_8T: median 27.47 tok/s over 39 reps (llama-bench internal avg 27.28)

### whisper-cli, batched-decode ms (the barrier-heavy phase)
| leg | variant | n | median | min-max | vs prod | neighbour tok/s in window (median) |
|---|---|---|---|---|---|---|
| quiet_8T_free | prod | 3 | 143.2 | 141.8-143.7 |  |  |
| quiet_8T_free | exp_pool | 3 | 138.4 | 138.2-140.0 | x1.03 |  |
| quiet_8T_free | exp_yield | 3 | 140.3 | 133.7-141.4 | x1.02 |  |
| quiet_8T_free | exp_futex | 3 | 136.5 | 136.1-138.8 | x1.05 |  |
| cont_8T_1spin | prod | 3 | 6914.8 | 6800.7-7622.6 |  |  |
| cont_8T_1spin | exp_pool | 3 | 6122.1 | 4892.6-7218.5 | x1.13 |  |
| cont_8T_1spin | exp_yield | 3 | 315.8 | 310.9-422.8 | x21.90 |  |
| cont_8T_1spin | exp_futex | 3 | 206.3 | 203.8-212.7 | x33.52 |  |
| nb_8T | prod | 3 | 14031.9 | 13539.6-14272.8 |  | 0.08 |
| nb_8T | exp_pool | 3 | 13755.9 | 13733.7-14346.8 | x1.02 | 0.78 |
| nb_8T | exp_yield | 3 | 2885.6 | 2846.5-3027.4 | x4.86 | 1.68 |
| nb_8T | exp_futex | 3 | 1080.4 | 1057.2-1227.4 | x12.99 | 2.04 |
| cont_8T_8spin | prod | 2 | 14461.2 | 14340.9-14581.6 |  |  |
| cont_8T_8spin | exp_pool | 2 | 9463.0 | 8968.1-9957.8 | x1.53 |  |
| cont_8T_8spin | exp_yield | 2 | 5870.4 | 5655.2-6085.6 | x2.46 |  |
| cont_8T_8spin | exp_futex | 2 | 1061.0 | 1036.0-1086.0 | x13.63 |  |
neighbour alone nb_1T: median 14.69 tok/s over 39 reps (llama-bench internal avg 14.66)
neighbour alone nb_8T: median 27.47 tok/s over 39 reps (llama-bench internal avg 27.28)

