# mscale-neutral YaRN A/B (correctness + MTP acceptance ONLY; -t 24 on cores 24-47, tok/s NOT a speed claim)

| arm | short prompts | byte-identical vs N | MTP accepted/drafted (short) | MTP (34k) | tok/s short (info) |
|---|---|---|---|---|---|
| N | 20 | 20/20 | 1225/1739 = 0.704 | 171/333 = 0.514 | 30.42 |
| Y | 20 | 13/20 | 1267/1793 = 0.707 | 168/343 = 0.490 | 30.01 |
| YM | 20 | 13/20 | 1261/1718 = 0.734 | 166/355 = 0.468 | 30.71 |

## First differing char vs N (short prompts)
### Y
- gsm8k_00115: first diff at char 47 (N len 482, Y len 459)
- ifeval_1481: first diff at char 43 (N len 774, Y len 819)
- gsm8k_00452: first diff at char 113 (N len 547, Y len 502)
- gsm8k_00363: first diff at char 39 (N len 441, Y len 521)
- gsm8k_00538: first diff at char 483 (N len 508, Y len 505)
- gsm8k_01156: first diff at char 56 (N len 562, Y len 526)
- gsm8k_00016: first diff at char 79 (N len 227, Y len 474)
### YM
- leetcode_the-number-of-the-smallest-unoccupied-chair: first diff at char 627 (N len 664, YM len 665)
- gsm8k_00115: first diff at char 47 (N len 482, YM len 459)
- ifeval_1481: first diff at char 128 (N len 774, YM len 794)
- gsm8k_00452: first diff at char 113 (N len 547, YM len 502)
- gsm8k_00363: first diff at char 23 (N len 441, YM len 512)
- gsm8k_00294: first diff at char 3 (N len 287, YM len 536)
- gsm8k_00016: first diff at char 155 (N len 227, YM len 195)

## 34k-depth probe (256 forced tokens, greedy)
- N: depth 34248, accept 0.5135135135135135, tok/s 13.424067444192849 (info)
- Y: depth 34248, accept 0.4897959183673469, tok/s 13.01425630439044 (info), vs N: first diff char 44
- YM: depth 34248, accept 0.4676056338028169, tok/s 12.502988385163349 (info), vs N: first diff char 115
