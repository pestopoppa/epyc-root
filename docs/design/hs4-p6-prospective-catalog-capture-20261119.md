# P6 prospective catalog capture

The P0.4 runner can now bind the existing catalog comparator's identities before
execution and emit its native per-trial input at verification. This is software
support for the two-rerun gate; it does not establish live P6 acceptance.

Use the existing comparator manifest with task `calc-add-fix`,
`previously_passing: true`, and fixture equal to the runner's
`task_suite_fingerprint()`. Both arms share `identity`: `model` is the exact
`--model-role` declaration, `server` the exact `--build-info` declaration,
`plugin` the runner's `plugin_sha256()`, and `base_catalog` the baseline catalog
digest. Each arm's catalog identity is the SHA-256 of the original catalog
snapshot bytes. Distinct arm catalog identities are required.

Prepare each of baseline/candidate × trials 1/2 in its own fresh scratch directory:

```bash
python3 scripts/harness/hs4_p04_acceptance.py prepare \
  --out /mnt/raid0/llm/tmp/harness-selection-and/p6/baseline-1 \
  --enable-mcp --catalog-manifest /path/to/frozen-manifest.json \
  --catalog-arm baseline --catalog-trial 1 \
  --catalog-snapshot /path/to/baseline-tools-list.json
```

Preparation performs no inference. `catalog-binding.json` pins the original
manifest, catalog snapshot, generated config, prompt, fixture, plugin and runner
source. Its digest is recorded in `prepared.json`. The generated launcher checks
these pins and declared serving identity before OpenCode starts. An exposed trial
cannot be rerun in place. Long runs require a keeper row and publisher smoke;
this command does not authorize running its generated `run.sh` outside a grant.

Verification consumes the prepared binding; it has no catalog identity override.
Unbound historical records cannot gain catalog identities at verification.
`catalog-record.json` is created exclusively, preserving its first finalization.
Collect the four original record objects into a JSON array for the existing
`hs4_p6_catalog_gate.py` comparator. Reverification cannot replace a trial record.

Functional P0.4 failures are `fail`; transport, provenance, parity, missing usage
or other infrastructure failures are `infra_error`, with token cost unknown.
Known token cost is prompt plus completion over the full session, including
cache-read/write prompt tokens, conditional on A5 parity. SC86 receives the actual
arm and the nested prospective comparison identity in the attempt record.

Snapshots and serving declarations do not prove the active tools or mapped
binaries. A qualified row must separately capture live tools/list, content-based
serving custody and matched MCP-enabled configurations, retaining all four native
trials and failures. No MCP tools are activated by this change. P6's shared-tool
integration and live catalog acceptance remain open. Existing SC86 projection is
reused; the source extension is registered under VB-PARK-HARNESS-EVAL, with the
planning-context canary still required before calling the loop wired.
