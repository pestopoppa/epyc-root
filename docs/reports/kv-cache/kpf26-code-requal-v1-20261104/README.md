# KPF-26 same-ID diagnostic requalification packet

Prepared for the existing `rtg58-kpf26-code-off-diag-20261102` and
`rtg58-kpf26-code-on-diag-20261102` IDs, owner `rtg58-codex` and existing
handoff task KPF-26. No READY manifest or original launcher was edited.
The two specs share `/mnt/raid0/llm/tmp/kv-prefix-fork/kpf26-code-requal-20261104`
but retain separate result paths, STOP markers, completion markers and ports.

The original helpers, cohort and three-file source-input snapshot were copied,
not a Git checkout. The retained binary directory uses hardlinks plus original
relative library symlinks; all contents remain checked against the copied
BINARIES.sha256. The clean orchestrator source at
`868275acb64ef3d490ecac6952518ae187fe74d3` is referenced in place, with no edits.
Before spawn the job checks the exact source HEAD, cleanliness, every retained
ELF digest and the real ggml library tree. This establishes pinned identities;
it does not invent source-to-binary build provenance or a decision-grade gate.

The full three-scout diagnostic and keyword-only interpretation remain unchanged.
Its smoke branch completes one native target-model call and verifies the socket
belongs to the captured PID/birth before and after the HTTP200 response. The
isolated qualification result requires a positive native generated-token count;
it cannot satisfy the full fan-out, outcome or timing gate. The launcher enables
cross-role disjoint placement and lets the engine restrict smoke CPU affinity.

Static `bash -n` and Python compilation pass. `test_native_smoke.py` tests real
listener ownership and refusal of incomplete native progress without inference.
Main must publish each same-ID spec with ROWFLOW_REPO set to the lane so the
current handoff resolves. No smoke, model inference, qualification or publication
was run during preparation.

Owner outcome: both original IDs passed reduced native smoke, then ended full execution INCONCLUSIVE. This generation is preserved historical evidence; use the fresh CODE r2 successors in kpf26_code_requal_v3, not these terminal IDs.

Archived row inputs only: no service imports or installs this packet. Published rows execute their pinned scratch launchers. This archive is not a deployment of fleet coordination code.
