# Host snapshot 2026-11-04 13:05Z (fixture)

## region-lock status
q0  HELD  build  owner=f8     tag=kvu-lb2-arch   since 12:10Z  (grant kvu-lb2-arch end=14:40Z, resumable)
q1  free
q2  free
q3  HELD  build  owner=3c4ca599 tag=kpf19-gpu-fold (GPU job, folded 184-191 claim; grant end=15:30Z)
gpu-quiet  SHARED by kpf19-gpu-fold
MemAvailable 612 GiB. No DS41-1017 shard mapped. rocm-smi: 71% use, 46 GB VRAM.

## Queue rows (abridged from FILLERS.md)
| id | owner | status | ready | class (derived) | resources | min window | duration | peak RAM GiB | launcher pid | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| kvu-lb2-arch | f8 | ARMED | y | block-correctness | q0 (resumable) | 1800 s | ~2.5 h | 45 | 51001 alive | running |
| kpf19-gpu-fold | 3c4ca599 | ARMED | y | block-timing-pairable | mi210_0,184-191 folded | 2400 s | 2.4 h | 48 | 51002 alive | running |
| ds41-w9-floor | 3c4ca599 | ARMED | y | block-timing-quiet | 0-95 + gpu-quiet exclusive | 10800 s | 3.2 h | 739 (DS41-class) | 51003 alive | decision: champion baseline, floor file cited |
| yarn-ext-arms | 3c4ca599 | ARMED | y | block-correctness | mi210_0,184-191 no-fold (resumable) | 7200 s | ~17 GPU-h | 64 | 51004 alive | |
| spec-gram-2 | f8 | ARMED | y | block-correctness | any one quarter | 1800 s | 50 min | 50 | 51005 alive | |
| kpf64-pass3 | 3c4ca599 | ARMED | y | block-correctness | one quarter, ATOMIC | 23800 s | 6.6 h | 42 | 51006 alive | fixed order after pass2 (done) |
| v12-build | 3c4ca599 | ARMED | y | block-correctness | 72-95 | 900 s | 25 min | 16 | 51007 alive | needed by v12-gpu-ab (precond build.ok) |
| v12-gpu-ab | 3c4ca599 | ARMED | y | block-timing-pairable | mi210_0,184-191 folded | 3000 s | 55 min | 33 | 51008 alive | precond: v12-build |
| hil19-replay | f8 | BACKLOG | n | block-correctness | one quarter | 2400 s | 1 h | 40 | - | blocker=missing launcher |
| new14-quant | ws58 | BACKLOG | n | block-correctness | 0-95 | 1800 s | 3 h | 172 | - | blocker=operator decision: reference model P or R |
| dhm-73 | f8 | ARMED | y | block-correctness | one quarter | 1500 s | 40 min | 4 | 51009 DEAD | grants/dhm-73.complete exists |

Fixed points: operator-booked quiet window 2026-11-05 05:00-08:30Z (ds41-w9-floor is the only quiet row). Night ends 06:25Z. The owner session may be rate-limited after 22:00Z.
