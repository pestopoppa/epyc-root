# AutoPilot multi-tier incumbent baseline — v10 evidence

Collected 2026-08-09 through 2026-08-10 under execution instrument
`resource_lanes_v10_history_scoped_quiescence` and production kernel
`production-consolidated-v8`.

| Lane | Scored rows | Quality (0–3) | Reliability | Artifact SHA-256 |
|---|---:|---:|---:|---|
| T1 frontier | 100 | 1.500 | 1.000 | `2293f55a6ab7ea442bc3d32093b0e3c3df7f0e842a0ba726af872eb8191c9e2f` |
| T2 comprehensive | 500 | 1.356 | 1.000 | `8d18534b3bbb520bc097957093ec2ecb11f6eae6be018c6f4cc86a27c369c3ad` |
| T3 expert/workflow | 160 | 1.275 | 1.000 | `012f2d99de64efa2439aa76550c73b17011eb2386de5def1838f99d0eec4fac7` |

All three artifacts report zero error rows, scorer errors, backend-drain failures, contamination,
or duplicate question identities. T1 preserves 90 clean source rows byte-for-byte and replaces only
the 10 poisoned ordinals through the targeted recovery batch. T2 and T3 are deterministic evidence
recodes from the clean v9 artifacts: only execution-instrument identity/profile fields and the
explicit recode receipt changed; answers, scores, timings, and routing did not.

These files are `CANDIDATE` baseline evidence until the consolidated operator transaction applies
them. AutoPilot remained stopped after collection.
