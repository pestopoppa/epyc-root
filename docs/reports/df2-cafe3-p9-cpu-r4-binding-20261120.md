# CAFE-3 CPU P9 retained R4 build binding — 2026-11-20

The parked CPU P9 row referenced reclaimed R3 full-build scratch. Rebound only
its build receipt to the qualified, retained R4 full CPU build:
`/mnt/raid0/llm/tmp/df2/cafe3-cpu-build-r4-20261120/RESULT.json`, SHA-256
`6ed842ac55bb2df09834888214cf1a72f160b14876b046e99b7c3f0c6cf896cb`.
The executable is bound by content SHA-256
`e87b6b11d8d41221da3501f0962c78d8e792afe82b585ece1192a0f711f68115`;
its server implementation SHA-256 is
`7d2b12da8294e199fb5d5c3b4ff9853a271e579b26b1286c8a9121fa9c0296e6`.
R4 was filed with `--no-reclaim` to preserve these dependent inputs.

Resealed inventory, all three launcher commands and publisher predicate to the
same new inventory digest. The existing publication binding checker and sealed
input validator PASS; the latter reuses the trusted full-build validator and
retains model/corpus full identity and runtime checks. No model hashing or
preparation occurs in the grant. Prepared inputs, runtime sources, five-arm
schedule and P9 decision rule are unchanged. Original pre-R4 inventory remains
in place as `inputs-before-r4-build.json`; no source, binary or log copied.

`df2-cafe3-p9-cpu-20261119` republished with **smoke PASS** on **116–119**,
rc0 at **11:16:22Z**. Initial standard publication queued the smoke; the
publisher's `--smoke-now` path then qualified it on available cores. Post-smoke
sealed input validation also PASS, covering the prior cleanup/corpus drift
boundary. Smoke executes compiled server `--help` without loading models;
it establishes no native inference or P9 verdict.

P9 still requires 100% token identity versus static-0, adaptive request-wall
throughput >=1.01 times the fastest static width 0..3 (higher is better), and
same-request post-exploration zero-to-positive recovery within 128 rounds.
Missing recovery remains inconclusive; late recovery or identity/speed failure
fails. Parent CAFE-3 stays open. Consume its scheduled result when delivered.

Original evidence in place, SHA-256:

- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/inputs.json`: `5620affde630549cb80c013711e00c5988d5c78138df3d92ea75eae51d8d3452`.
- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/launch.sh`: `a4931711ab140b4390125c32f2ce3f3acb4db204df937993617598400598f49e`.
- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/spec.json`: `0146d3b6cb0aada26644640c6296493e968803f4e1741c54edd54c9b7db2908c`.
- `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe3-p9-cpu-20261119/PASS.json`: `81ead6677c64cdfbe080794ccac7c3cdef74b8e2a673b2bc099a9afc03693fd5`.

[no-belief: publisher smoke qualification only; no native P9 verdict]
