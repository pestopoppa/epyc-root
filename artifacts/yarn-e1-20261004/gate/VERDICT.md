# INF-59 E1 verdict (pre-registered criteria, RUNBOOK.md section 6)

**Overall: FAIL** (C2 + C3 + C4 decide; C1 is recorded, informational).

## C1 short context (A1 vs A0, n=84)

- coherence_gate **FAIL**: 3 REGRESSION, 0 improvement(s), 53 byte-identical, 3 BOTH_BAD, 10 NEEDS_REVIEW (no judge).
- graded accuracy: A0 59/70, A1 58/70.
  - gsm8k_01180: degeneracy OK -> DEGENERATE ['uniq+stuck']
  - gsm8k_01118: degeneracy OK -> DEGENERATE ['uniq+stuck']
  - gsm8k_00552: answer correct -> unanswered (expected '450', got None)

## C2 within native (128k + 240k, paired): A0 10/10, A1 10/10 -> **PASS**

## C3 beyond native (A1)
- 400k: 5/5 (abstained 0) depths {'N10': {'depth': 0.1, 'distance_k': 358, 'status': 'correct'}, 'N11': {'depth': 0.3, 'distance_k': 279, 'status': 'correct'}, 'N12': {'depth': 0.5, 'distance_k': 199, 'status': 'correct'}, 'N13': {'depth': 0.7, 'distance_k': 119, 'status': 'correct'}, 'N14': {'depth': 0.9, 'distance_k': 40, 'status': 'correct'}}
- 500k: 5/5 (abstained 0) depths {'N15': {'depth': 0.1, 'distance_k': 448, 'status': 'correct'}, 'N16': {'depth': 0.3, 'distance_k': 349, 'status': 'correct'}, 'N17': {'depth': 0.5, 'distance_k': 249, 'status': 'correct'}, 'N18': {'depth': 0.7, 'distance_k': 149, 'status': 'correct'}, 'N19': {'depth': 0.9, 'distance_k': 50, 'status': 'correct'}}

## Diagnostics
- local-coherence probes: {'A0:128k': 'OK', 'A0:240k': 'OK', 'A1:128k': 'OK', 'A1:240k': 'OK', 'A1:400k': 'OK', 'A1:500k': 'OK', 'paired:128k': 'NEEDS_REVIEW', 'paired:240k': 'NEEDS_REVIEW'}
- empty needle answers (instant-EOS signature, llama.cpp #27756): {'A0:128k': 0, 'A0:240k': 0, 'A1:128k': 0, 'A1:240k': 0, 'A1:400k': 0, 'A1:500k': 0}

## C4 memory: {'A0:kfd_A0.jsonl.summary.json': 52.716, 'A0:kfd_A1.jsonl.summary.json': 63.926, 'A1:kfd_A0.jsonl.summary.json': 52.716, 'A1:kfd_A1.jsonl.summary.json': 63.926, 'kfd_A0.jsonl.summary.json': 52.716, 'kfd_A1.jsonl.summary.json': 63.926}
