# Dive evidence — intake-938..956 (2026-08-03 research-intake batch)

Durable copy of the Stage-1 collection and Stage-2/2b dive reports backing entries
`intake-938` … `intake-956` in `research/intake_index.yaml`.

These files were originally written to a gitignored scratch path. Moved here at operator
instruction so the evidence is durable in git rather than merely present on the filesystem
(`feedback_verify_evidence_in_git_not_filesystem`: untracked looks identical to committed).

Each entry's `dive_corrections` field in the index is the authoritative, dated summary.
These documents are the underlying working evidence, kept so a later reader can check a
correction without re-running a dive.

| file | covers |
|---|---|
| `stage1_results.md` | Stage-1 collection, 9 operator-submitted sources (intake-938..946) |
| `stage1_expansion.md` | Stage-1 Phase-3 expansion, 10 sources (intake-947..956) + schema-normalization record |
| `DIVE-A-inkling.md` | intake-941/942/955 — Inkling, as a worker_general / architect_critic candidate |
| `DIVE-B-escha.md` | intake-945/946 — Escha W2, same framing |
| `DIVE-C-instruments.md` | intake-950/954 — PIE + COFFE, measurement instruments |
| `DIVE-D-benchmarks.md` | intake-951/952/953 — SWE-Perf, EffiBench-X, SWE-fficiency |
| `DIVE-E-fair-rl.md` | intake-939 — FAIR RL for Code Optimization (125pp incl. appendices) |
| `DIVE-F-memharness.md` | intake-938 — MemHarness (dive-overturned) |
| `DIVE-G-frontis.md` | intake-940 — Frontis-MA1, incl. the medal-count reconstruction |
| `DIVE-H-codecrucible-benchmrk.md` | intake-943/948 — CodeCrucible + benchmrk |
| `DIVE-I-consolidated.md` | intake-944/947 — QuixiCore + HipKittens, AMD/NVIDIA kernel gap |
| `DIVE-I-delta-only.md` | the delta report that preceded the consolidation (kept for provenance) |
| `2bA-quixi-forks.md` | Stage-2b — QuixiAI llama.cpp fork + QuixiFlow |

Stage-2b dives were uncapped by operator instruction; further `2b*` files are added as they land.
