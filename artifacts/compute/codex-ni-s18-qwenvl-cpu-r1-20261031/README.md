# S18 Qwen3-VL-30B CPU r1 — accepted READY and runtime qualification (2026-10-31)

Publication `codex-ni-s18-qwenvl-cpu-r1-20261031` completed at 2026-10-31T08:13:04.986327Z. Exact approved READY manifest SHA-256: `b15927014bdd7eb366985cce390cf834a23b6f327a3f6c3f436f88474de9b0ea`. The READY packet requests the native CPU MMMU measurement on the pinned 60-item cohort using the preserved 512-token, temperature 0.2, seed 42 recipe and 48-core NUMA_HALF_A placement. It is diagnostic admission only; actual t48/60-item measurement and VB-SERVING-DF2 projection/canary remain open.

## Completed runtime-only outcomes

- Public normal launch: rc0, one of one runtime rows, 221.4304 s including drain; max_tokens=4, request handling succeeded. Output parsing did not produce a complete MMMU result. This is runtime admission evidence only and contributes no quality score.
- Active-request cutoff: rc75, partial=true, one of two runtime rows after 233.1852 s including drain; captured process group drained. This verifies cutoff handling under real active grants, not a result for the 60-item cohort.
- Both records use canonical model/MMProj SHA pins and CPU-only server closure. The exact 60-item MI210 baseline remains 36/60; historical 159/250 remains a distinct cohort/result. They must not be combined. No S18 scientific checkbox is complete.

## Custody and source records

The exact READY/row/publication and compact terminal, retention and scan proofs are included. Full runtime records remain under `/mnt/raid0/llm/tmp/codex-ni-next-ranked-cpu-prep-20261031/`; `SOURCES.sha256` records source and native-record hashes without copying response logs, runtime samples, model weights or binaries. The 162-file bounded-packet retention check found zero unretained existing or future paths. Frozen kernels and serving stack were not changed.
