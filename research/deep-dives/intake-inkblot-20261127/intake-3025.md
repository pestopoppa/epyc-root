# Recursive Self-Improving Loopers

**intake-3025 · Sweep 1 · partial source read**

[Primary source](https://github.com/eelbaz/Recursive-Self-Improving-Loopers)

## Evidence

- Confirmed within the stated scope. The released FP-Solve implementation calls the generic linear solver for its regularized update. [rse_looper/fpsolve.py:L61-L70 @ 765453d](https://raw.githubusercontent.com/eelbaz/Recursive-Self-Improving-Loopers/765453d13878804c49876a656f39b57a4384dca4/rse_looper/fpsolve.py)
- Confirmed. The original acceptance function allows a maximum loss of two correct answers per mode and rejects total losses. [rse_looper/gspo.py:L120-L138 @ 765453d](https://raw.githubusercontent.com/eelbaz/Recursive-Self-Improving-Loopers/765453d13878804c49876a656f39b57a4384dca4/rse_looper/gspo.py)
- Confirmed within the stated scope. Running the original GSPO CLI requires externally supplied training and gate JSONL files. [rse_looper/gspo.py:L376-L381,L416-L418 @ 765453d](https://raw.githubusercontent.com/eelbaz/Recursive-Self-Improving-Loopers/765453d13878804c49876a656f39b57a4384dca4/rse_looper/gspo.py)
- Confirmed. The original generation summary records 118 correct for the accepted generation 2 winner, followed by 114 for the accepted generation 3 winner. [results/gspo_results.json:L128-L178 @ 765453d](https://raw.githubusercontent.com/eelbaz/Recursive-Self-Improving-Loopers/765453d13878804c49876a656f39b57a4384dca4/results/gspo_results.json)

## Limits and corrections

Read the pinned implementation, tests, six summary JSONs, README and four-page paper. No training set, gate split or per-item predictions in the tracked release. No training or inference run. The v5.24.0 native Transformers file at eeee110 lacks the cache class the wrapper imports. Items, seeds and evaluation-environment identities would be needed for exact replay.

2026-11-27. Recipe replay is overturned for this release. Five generations marked accepted (0–4) give 111 → 112 → 114 → 118 → 114 → 116 correct across three modes. The 118→114 step violates the public gate. The separately reported merged result is 120/192. The merge helper has no caller in the generation loop. The README describes four generations and Cholesky. The original evaluator uses known answers with a deterministic grader, so teacher-free does not imply label-free GSPO.

## Recommendations

- RI-TRAIN. Gate a training attribution experiment on recoverable lineage and include a simple matched-budget control.

## Sources surfaced

The author paper and independent repair PR were selected for sweep 2. The HF companion was already selected.

Artifact audit clean. External code and model weights were not executed.
