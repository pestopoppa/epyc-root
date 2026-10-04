# CPU window 2 (2026-10-04) — structural-seed falsifiers and the EXL3 full-model window (durable copy)

Run by ak-ds41-main under `region-lock run --cpu-list 0-95 --role bench --tag cpu-window2-20261004` (q0–q3 held
04:40:39Z–05:00:11Z). Source: `/mnt/raid0/llm/tmp/cpu-window2-20261004/` (not durable).

| Step | Result |
|---|---|
| step 0, structural falsifiers (`step0_struct_falsifiers/REPORT.txt`) | `bench_readbw` 2×2: local/4K ×1.000, local/THP ×1.018 vs interleave/4K → **NUMA lever and seed 4(A) KILLED** (≤ 1.05×). Q38FN `GGML_CPU_PROF` census (shares, not speed): seeds 2 (solo rows, 7.6%), 5 (norm→matmul, 5.0%), 6 (sibling gemv pack, 3.5%) **KEPT**; seeds 1 (hc fused ops, 5.4% < 12%) and 3 (routed‖shared groups, 0%) **DROPPED**. Dense mul_mat runs at ~195 GB/s on wall vs a ~407 GB/s gemv read ceiling. |
| step 1, EXL3 3.05 bpw full model (`step1_exl3_full/REPORT.txt`) | vs UD-IQ4_XS: PPL **−3.4%** (2.8909 vs 2.9925, wiki c512, 40 chunks); pp5 **−31%** (slower 3/3); pp256 −17% and tg128 −7% inconclusive. Uniform IQ4_XS vs UD: pp5 **+24%**, pp256 **+34%** (faster 3/3), tg128 +11% inconclusive, at PPL **+17.8%** (3.5244). Greedy: p1 identical, p2 differs at token 45, p3 at token 22. n = 3 launches per arm. |
| steps 2–4 (EXL3 microbench, MXFP4 vs Q4_K, Q38FN anchor) | **Refused** by the load preflight (rc 3, `step{3,4}_*/load-preflight.json`): host at ~2,400% of one CPU from unlocked subagent CPU work. See INC-20261004-subagent-unlocked-cpu-in-held-window in `docs/reference/agent-config/INCIDENT_LOG.md`. |

PPL caveat (from the report): wikitext overlaps the Q38FN memorised n-gram set and the public Q8_0 KLD floor is
0.022–0.027, so small PPL gaps between 4-bit-class files are not resolvable as quality. The project gate is a paired
per-item task eval.

Consumers: `handoffs/active/deepseek-v41-flash-evaluation.md` (DS41-C107-s00a/s00b and seeds),
`handoffs/active/exl3-cpu-mi210-implementation.md` (EXL3-6c5/6c6), `handoffs/active/cpu-decode-roofline-program.md`
(XFER-3), Q38FN lane inbox note 62 (`/mnt/raid0/llm/autokernel/campaigns/ak-q38fn-cpu-decode-20261003/store/inbox/`).
