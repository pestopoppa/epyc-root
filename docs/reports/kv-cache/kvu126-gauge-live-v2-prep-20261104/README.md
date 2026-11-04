# KVU-12.6 live gauge v2 preparation packet

This packet is an archival snapshot of the v2 scratch inputs for `kvu126-live-gauge-r2-20261104`. The runnable launcher remains `/mnt/raid0/llm/tmp/kvu126-gauge-live-v2-20261104/launch.sh`; the copied launcher and spec intentionally retain those absolute scratch paths. Do not treat this packet as a self-contained runnable job.

The v2 job reuses the v1 experimental CPU build sealed after the prior grant-path failure. `v1-build-custody.json` records the reused binary inventory, hashes, original build evidence hashes, source pin, and explicit limitation that no independent build-time binary attestation was written. `reuse_guard.py` verifies that custody at job start. `INPUTS.sha256` is the launcher's input manifest; it binds the job, model digest, tests, reuse guard, custody record, and linkage verifier input. The reused `build-reused/` binaries remain in scratch and are represented here by the custody manifest rather than duplicated in this report packet.

The preparation record reports eight offline tests passed, shell syntax and input-manifest checks passed, and publisher smoke and model inference not run. No full target inference is established by this packet. The decision rule is limited to one loaded-endpoint capability witness for this specific verified server and model; it makes no population, performance, promotion, or generalization claim.

Known contract discrepancy retained for review: the runtime's request-window predicate accepts equality at dispatch or response boundaries, while the spec says the mapped-library sample must fall strictly between them. Runtime code and the published row were not changed as part of packet reconciliation.

`SHA256SUMS.json` contains the SHA-256 digest of each packet file except itself. Regenerate it after any packet edit.
