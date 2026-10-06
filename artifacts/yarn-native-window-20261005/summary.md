# Q3.6-35B-A3B CPU decode at depth: production recipe vs the leg's hand-built launch

## HEADLINE: P vs P-YaRN (YaRN x2 inside the native window, MTP on, -c 262144)

| depth | P tok/s (accept) | P-YaRN tok/s (accept) | PY / P | PK (kvu) | PKY (kvu+YaRN) | PKY / PK |
|---|---|---|---|---|---|---|
| 0 | 39.13 (42%) | 38.62 (41%) | 0.987 | n/a | n/a | n/a |
| 34k | 24.59 (53%) | 22.72 (48%) | 0.924 | n/a | n/a | n/a |
| 128k | n/a | n/a | n/a | n/a | n/a | n/a |

Greedy quality probe at depth 0 (20 short prompts, <=160 tokens): byte-identical P vs P-YaRN 13/20 = 65%; degenerate P 0, P-YaRN 0.
- gsm8k_00115: identical=False first diff at char 47; degenerate P=None PY=None
- ifeval_1481: identical=False first diff at char 43; degenerate P=None PY=None
- gsm8k_00452: identical=False first diff at char 113; degenerate P=None PY=None
- gsm8k_00363: identical=False first diff at char 39; degenerate P=None PY=None
- gsm8k_00538: identical=False first diff at char 483; degenerate P=None PY=None
- gsm8k_01156: identical=False first diff at char 56; degenerate P=None PY=None
- gsm8k_00016: identical=False first diff at char 79; degenerate P=None PY=None

Generated 2026-10-05T12:10:54Z. 256 forced tokens x 2 reps per cell; tok/s = timings.predicted_per_second (mean of reps); acceptance = draft_n_accepted / draft_n (MTP arms only).

## Decode tok/s (acceptance)

| arm | 0 | 34k | 128k |
|---|---|---|---|
| P | 39.13 (42%) | 24.59 (53%) | n/a |
| PY | 38.62 (41%) | 22.72 (48%) | n/a |

Leg reference (CN arm, cpu_leg/results/VERDICT.md): 34k 20.366, 133k 6.416, 253k 3.689 tok/s (128 tokens, 1 rep, --verbosity 4).

## Launch-setup ratios (same depth)

| ratio | 0 | 34k | 128k |
|---|---|---|---|
| PY / P (YaRN cost, headline) | 0.987 | 0.924 | n/a |
| P / L (production vs leg launch) | n/a | n/a | n/a |
| PK / L (production, 128k-capable, vs leg) | n/a | n/a | n/a |
| P-noMTP / L (launch flags without MTP) | n/a | n/a | n/a |
| P / P-noMTP (MTP gain) | n/a | n/a | n/a |
| PKY / PK (YaRN cost, 128k-capable) | n/a | n/a | n/a |
| PK / P (does --kv-unified move speed) | n/a | n/a | n/a |
| PK@128k / leg-reported CN@133k (external ref) | n/a | n/a | n/a |

## Depth falloff per arm (tok/s at depth / tok/s at the shallower depth)

| arm | 34k / 0 | 128k / 0 | 128k / 34k |
|---|---|---|---|
| P | 0.628 | n/a | n/a |
| PY | 0.588 | n/a | n/a |

## Per-arm facts

- **P**: n_ctx_slot=65536 slots=4 numa_share={'N0': 0.25, 'N1': 0.25, 'N2': 0.25, 'N3': 0.25}; reps={'0': [38.95, 39.319], '34k': [24.682, 24.499]}
- **PY**: n_ctx_slot=65536 slots=4 numa_share={'N0': 0.25, 'N1': 0.25, 'N2': 0.25, 'N3': 0.25}; reps={'0': [38.231, 39.004], '34k': [22.873, 22.56]}

Reading the table: a P/L (or P-noMTP/L) ratio near 1.0 at depth 0 and 34k means the leg's hand-built launch cost nothing and the 20.4 -> 6.4 tok/s drop is the CPU flash-attention depth falloff; a ratio that differs identically at every depth is launch-setup cost; MTP gain is P / P-noMTP.
