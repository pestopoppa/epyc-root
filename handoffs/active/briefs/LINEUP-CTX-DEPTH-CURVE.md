---
schema: epyc.brief.v1
id: LINEUP-CTX-DEPTH-CURVE
box_text_sha: 4b1881199c232c5d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/engineering-hygiene-backlog.md
approach: 'Question: decode tok/s versus context depth for Qwen3.6-35B-A3B Q8_0, Qwen3.8-Flash-Next UD-IQ4_XS and Qwen3-VL-30B-A3B
  Q4_K_M (best-case tg128 at depth 0: 57.01, 25.59, 84.42). Run P-BENCH-1 with -d depths about 0, 4k, 16k, 32k, n=10, quiet
  host, after the v11 promotion (not on v10). Stop at all depths x models filed. Prep now: row spec with recipe, launcher
  and contention label; publish after v11. Decision: serving throughput budget per role.

  '
acceptance: grep -q 'LINEUP-CTX-DEPTH-CURVE.*RESULT' handoffs/active/engineering-hygiene-backlog.md
non_goals:
- do not run on v10
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/engineering-hygiene-backlog.md: 5cd40ac89a5ee1197b2d1ebb5d3d4aab8e39919c
---
