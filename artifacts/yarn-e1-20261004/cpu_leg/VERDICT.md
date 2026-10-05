# INF-59 CPU leg (Qwen3.6-35B-A3B, CPU) — results

## CN

| depth | decode tok/s | needles (id, distance k, status) | local |
|---|---|---|---|
| 34210 | 20.365976599492885 | [('C00', 22, 'correct')] | OK |
| 69298 | 10.943105937301818 | [('C00', 57, 'correct'), ('C01', 31, 'correct'), ('C02', 6, 'correct')] | OK |
| 133275 | 6.41593236404301 | [('C00', 121, 'correct'), ('C01', 95, 'correct'), ('C02', 70, 'correct'), ('C03', 44, 'correct'), ('C04', 20, 'correct')] | OK |
| 193488 | 4.678761875328176 | [('C00', 181, 'correct'), ('C02', 130, 'correct'), ('C03', 104, 'correct'), ('C05', 56, 'correct'), ('C06', 29, 'correct')] | OK |
| 252969 | 3.6889615204423802 | [('C01', 215, 'correct'), ('C02', 190, 'correct'), ('C05', 115, 'correct'), ('C07', 65, 'correct'), ('C09', 15, 'correct')] | OK |

turn append cost (depth, s per 8k turn), every 8th: [(0, 19.7), (69298, 136.9), (142587, 241.1), (210655, 371.3)]

## CY2

| depth | decode tok/s | needles (id, distance k, status) | local |
|---|---|---|---|
| 34210 | 19.56441959627292 | [('C00', 22, 'correct')] | OK |
| 133275 | 6.244254249446737 | [('C00', 121, 'correct'), ('C01', 95, 'correct'), ('C02', 70, 'correct'), ('C03', 44, 'correct'), ('C04', 20, 'correct')] | OK |
| 252969 | 3.641904711611792 | [('C01', 215, 'correct'), ('C02', 190, 'correct'), ('C05', 115, 'correct'), ('C07', 65, 'correct'), ('C09', 15, 'correct')] | OK |
| 323527 | 2.938802604164825 | [('C01', 286, 'correct'), ('C03', 234, 'correct'), ('C06', 159, 'correct'), ('C09', 85, 'correct'), ('C11', 36, 'correct')] | OK |

turn append cost (depth, s per 8k turn), every 8th: [(0, 19.7), (69298, 141.4), (142587, 252.8), (210655, 385.3), (279800, 556.8), (350940, 602.5)]

- C1 short CY2 vs CN: {'gate': 'INCOMPLETE', 'regressions': 0, 'identical': 52, 'both_bad': 0, 'needs_review': 13, 'n': 84}
- C3 CY2 beyond native (>= 4/5 and local OK at every depth): {'pass': True, 'per_depth': {323527: 5}}
