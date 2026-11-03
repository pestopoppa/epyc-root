# R18-B build timing patch

The attached patch records successful build-command completion in the AutoKernel promotion and continuation paths. It does not identify the historical run-18 binary or establish binary freshness. In the continuation path, reused build directories retain `built_at: null`, while the command-completion timestamp is recorded separately.

The patch was applied in a scratch source snapshot of `epyc-inference-research` `origin/main` at `3ab4ffbf1f436ceb4a8918d0ce2984c0567b0095`. The agent reported 46 passing model-free tests for `test_r18b_timestamp_writer.py` and `test_anchor.py`; no inference or kernel build was run. Recheck the source revision and run the relevant checks when integrating.

- Patch SHA-256: `b261084a59ffa3cdb6da8a27a6659c6a35183b37988d1e43cded1a187fb7b94a`
- Target: `scripts/kernel_rnd/autokernel/loop/pool.py`, `run.py`, and tests in the research repository.
- Handoff: [R18-B](../../../handoffs/active/autokernel-loop.md#track-autokernel-rebuild-program). The historical forensic question remains open.
