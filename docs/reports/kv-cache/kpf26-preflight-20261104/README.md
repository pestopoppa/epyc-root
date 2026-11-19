# KPF-26 diagnostic preflight repair proposal

The four existing diagnostic rows are owned by `rtg58-codex`. No qualification failure record is present in the inspected flags tree; this proposal does not diagnose a failed smoke or authorize duplicate publication.

`source-binary-preflight.patch` adds a fail-closed guard before either job starts its server: require the presently clean orchestrator commit, verify every retained binary/library digest against the existing manifest, and prove linked ggml libraries resolve inside the retained binary directory. The same patch applies to the code and API/scout scratch jobs. It does not modify their workloads or decision rules.

The source commit is `868275acb64ef3d490ecac6952518ae187fe74d3`; changing it requires owner review and a new reviewed source pin. A digest manifest proves binary identity, not that a binary was built from that source. Approved build provenance and run-time residency remain separate requirements.

Validation: both transformed scripts pass `bash -n`. No inference, qualification, manifest mutation or launcher mutation occurred. The row owner should review and apply the patch, synchronize any permitted launcher/engine hashes, and requalify the existing IDs through the keeper. Do not create duplicate rows merely to obtain a fresh qualification counter.
