# Proposed all-only continuation — pending main approval

R2 dense is complete under the old candidate; the all-keys arm aborted before producing its output. Reuse requires main to establish that the replacement source patch cannot change dense behavior and that the two builds are equivalent for the dense path, or reject reuse. Do not infer equivalence from a build path or matching version string.

R2 original candidate identity SHA-256: `332167ee6cd9cf569c912dec2bd1203b4c6ea2de1a62ae121f804cca55775875` (snapshot `r2-candidate-identity.json`). Original directory `../booking-cpu-parity-r2/ATTEMPT_FENCE/` remains immutable:

- dense.bin: `11c1d2b429c42140d291446ed2e9f9c27cee541104300462f487eb2dfac64219`
- dense.log: `2bc0cc1a5e4cb0a08f489e93db2f7ada102f0480ee7a447b6c96e879b655adff`
- dense-monitor.jsonl: `0fc1b6cec5d311298a1fdc53f55b482d201ded23a0e7bed8b6a7632c1b421f92`
- provenance.json: `ee6ad56dad62a4c29a9842162089e90955a686995acd05c604f24122b8d5a525`
- RESULT.json: `2444fb737f551e56f9ee1a631a93573c0132dd300da43dc2816cc3b2d88f8964`

Original dense PID 2769094 exited 0; its native log gives 45 frozen IDs, 248320 vocabulary, BF16 KV, context 1024, 4 threads, CPU 24–27 and no GPU. R2 monitor recorded candidate library digests and actual model mapping; original manifest's model hash is not a fresh loaded-byte hash. The R2 result is INVALID and is retained, not overwritten by the continuation.

Required before execution: final new candidate seal and complete patch difference, model-free four-thread callback fixture, an explicit decision that reuse is sufficient, same model/fixture and actual CPU mask 24–27, executable and live-library integrity checks, real core lock, and a new unique attempt fence. Run exactly the all-keys arm; run the strict checker using original dense.bin/dense.log and new all.bin/all.log/trace. Store both identities, input artifact hashes, native metadata and resulting full-vocabulary max absolute difference, exact argmax and sixteen-layer mask verdict in the new evidence record. No quality or timing claim. The current job is intentionally disabled and contains the proposed all-only path but still binds the old seal; it must be resealed and independently reviewed after the new seal arrives.
