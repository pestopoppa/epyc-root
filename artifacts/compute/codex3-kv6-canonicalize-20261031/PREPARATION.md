# INF05 KV-6 — native synthetic timing, indicative only

Actual native `src/inference/prefix_cache.py` at orchestrator HEAD `84f6f6f15f713d21098dbad2b153d32f8cc13624`, file SHA256 `8f075d9dd5716abb7838be75779c57c4031663a58eebbfd080efff0f39e929cb`. `measure.py` SHA256 `d063020ca782ff9edb1648b1239c16283e2d07720cbdb5b7ebf75bb196beedfb` imported and timed the actual function, without modifying production. R6 sampled supervisor and no-delete, CPUs 30,31, 9 batches per synthetic shape, `measurement.log` SHA256 `3ab41722ad15fab20a5c4ebacbc07134b2b74a974e6e3d729ac9929393e2ba8d`; 4.0 s, sampled peak 44,621,824 B. Timing is shared-host indicative, not isolated throughput or production request latency.

| Characters | Plain median ms | Date/UUID/newline mixed median ms |
|---:|---:|---:|
| 256 | 0.008 | 0.007 |
| 10,000 | 0.279 | 0.242 |
| 100,000 | 2.830 | 2.411 |
| 1,000,000 | 31.053 | 24.266 |

The present `CachingBackend.infer` implementation returns before the router if `ORCHESTRATOR_PREFIX_ROUTER_PIN_SLOTS` is disabled; its default is off. Therefore these microbench figures do not imply a production default-path cost. No representative production prompt distribution, cross-process RSS, network, GPU inference, or end-to-end routing contribution was measured. Do not mark a live-path optimization or selection decision from synthetic data.

Belief wiring proposal sent to owner: native source identity, synthetic shape/length, raw batch times, CPU affinity, interpreter and R6 context as an OBSERVATION through existing shared grading; no new grading ladder. This is a measurement, not an inference launcher or a READY row.
