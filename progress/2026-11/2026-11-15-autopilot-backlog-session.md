# 2026-11-15 autopilot-backlog-session

## AGG-1.13 out-of-sample validation filed (POST-DATA)

- 10 unseen 10-Ks, 76 cells, 30 questions. PREDECLARED `a8b71525`; amendments `279645ad` (fy_end) and `67d65270` (split-header pairing + real-text preflight).
- M1: v2 71/76 vs v1 61/76, paired 10-0, z 3.16, p 0.002, 0 regressions; canonical 67 vs 56.
- P-large: arm C (v2 + agg110 planner) 25/30 vs A (v1) 15/30, p 0.002; arm B 18/30.
- M3: prefill ratio v2 0.22 vs v1 0.40; LLM calls 305 vs 491. May-year-end filers 13/15 vs 9/15. No gates tripped.
- Rows: agg113-ingest-v1-cpu-20261114-r2, agg113-ingest-v2-cpu-20261114-r2, agg113-arms-gpu-20261114-r2 (smoke fix: job.sh empty grep count skipped the audit phase; fixed with default 0).
- Result: the in-sample AGG-1.12 gain replicates out of sample. Open: AGG-1.7, AGG-1.9, AGG-1.11 step 2; Phase 2 decision is the operator's.
