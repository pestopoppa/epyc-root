# KPF-60 blob snapshot binding

This review candidate removes a second open of each blob between the
provenance/alias checks and the fixed-oracle comparison. It compares the exact
immutable bytes read, hashed, and inode-checked during contract validation.
Eight model-free tests pass, including a control that fails if the comparison
reopens either blob. The original prospective verifier is unchanged.

This closes only that intra-verifier reopening gap. It does not make multiple
artifact reads an atomic snapshot, prevent same-UID mutation, authenticate a
producer receipt, prove source/build/device provenance, or create a measurement
warrant. No native blob was captured or compared; this candidate is not wired
to a runner.
