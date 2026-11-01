# TD-17 source adapter and model-free controls (partial)

APP source candidate `027427c223d53a0b5a95541e5e2e49cd2cf0dc5d` was published on APP main in merge `5cb3f2c9a7d510f498acbd77eaaed587a59d5399`, whose first parent is `f0310d9db781f3dd0a2a4d122cc4efcf7425e929`. The publication adds exactly five TD-17 source/test/fixture/workflow paths; the reviewed source blobs match the candidate.

Hosted run [41287440906](https://github.com/pestopoppa/epyc-orchestrator/actions/runs/41287440906) succeeded with 70 tests, exit 0 (one existing deprecation warning). Original API responses, jobs, ZIP, extracted stdout/JUnit/source hashes, and reviewer note are retained in `ci-41287440906/`; ZIP SHA-256 is `2674dbeaed1964424102692a73e7dbdb8df20baa04ebee737eedad1daadaa0e6`.

The zero-inference adapter pins source commit `914d87ab16517f14e833cff63d73b51235b14bd6`, validation data SHA-256 `763949cdf07f422cbb3c4bd040392944034ae4caf23a07de08fcef04cfd1eb33`, and generator hash. It provides frozen/fresh/tier-ablated and matched forced/unknown fixtures, preserving observed noisy labels separately from clean oracle truth. Seed-0 generation exactly reproduces the pinned 900 rows. These are source and model-free controls only: no model calls, TD-18 metrics, or calibration result.

**TD-17 remains open.** Completion still requires per-model-pin native and JSON TD-18 metric readouts under the champion-sidecar CPU gate, including the amended forced-choice, abstention, eligibility, probability-mass, and invalid-response metrics. No checkbox or quota credit is claimed. `[no-belief: source and deterministic software verification; no measurement]`
