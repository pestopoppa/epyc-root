# PF1-EXPAND r7 row packet

This packet prepares the existing `PF1-EXPAND` handoff row only. It does not publish a row, book a grant, run a measured cell, or authorize a production/serving conclusion.

- `spec-initial.json` is the forward shorter-L frame: five interleaved blocks, lengths 128/256/512/1024/2048, A0/A1/A2/A1-disabled, GPU ubatches 512/2048/4096, and the existing seed-34 10,000-resample launch-level median CI analysis. The full denominator is 250 invocations.
- `spec-holdout.json` is a separate later reversed-order session. It requires the complete initial self-hashed receipt, the same frozen manifest, a distinct session, and at least 14,400 seconds after initial completion. Its lengths are derived from the initial bracket; if no forward L* exists, they are the existing P3-3 8192/32768 conditional frame.
- `launch-initial.sh` and `launch-holdout.sh` are phase-specific entrypoints. `launch.sh` aliases the initial phase for compatibility.
- A real native first-progress smoke uses the allocated CPU affinity (normally four CPUs), one A1 L=128/ub=512 invocation, and writes `FILLER_DRYRUN_RESULT_PATH` only after native output, owned-child cleanup, placement evidence, and in-window GPU evidence pass. It is outside the 250-cell denominator.
- The only external build input is `/mnt/raid0/llm/tmp/pf1-loadthreads-build-20261104/loadthreads-build/BUILD-RECEIPT.json`. Before row publication, the owner must bind the produced receipt and actual output binary/library hashes through `prepare_manifest.py`; this packet must not be represented as publish-ready until that receipt exists and validates.

The existing 2026-11-03 GPU-skew amendment remains in force: A0 requires <=40% maximum NUMA node share; GPU arms require valid in-window placement evidence and >=90% RSS coverage, with maximum node share recorded as a covariate. C6 is an authorized diagnostic candidate, not the current champion or production.

Cell records carry the existing `VB-PREFILL-XOVER` source/family tuple at write time. They do not invent a grade or protocol ID. The initial and reversed holdout comparison remains descriptive; no final crossover/serving conclusion is emitted by the driver. The planning-context canary specified in the active belief-substrate program is a separate prerequisite before anyone reports the source as wired or communicates a final decision. P-GPU-1 fresh-server evidence is not established by this llama-bench packet.
