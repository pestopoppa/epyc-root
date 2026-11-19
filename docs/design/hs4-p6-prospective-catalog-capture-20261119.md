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

For an isolated row-owned server, add `--mcp-launch-spec /path/to/arm-launch.json`.
This requires MCP enabled and prospective catalog binding. The launch JSON has
exactly three fields:

```json
{
  "command": ["/absolute/venv/bin/python", "/absolute/row/server.py"],
  "cwd": "/absolute/row",
  "files": {
    "/absolute/venv/bin/python": "<SHA-256 of executable bytes>",
    "/absolute/row/server.py": "<SHA-256 of declared source bytes>"
  }
}
```

The original comparison manifest must also contain `mcp_launch_specs`, mapping
each overridden arm to the SHA-256 of its original launch JSON bytes. Preparation
changes only the existing `mcp.orchestrator.command` and `cwd` fields; provider,
plugin, permissions, prompts and autonomy settings retain their template values.
No server is imported or started during preparation. The executable must be an
absolute executable file, cwd an existing absolute directory, and file pins must
match before preparation. Environment/file interpolation in argv or cwd is
refused. The original launch JSON and its declared file inputs are rechecked by
`check-catalog` before exposure and again during verification. Existing callers
without an override retain their previous config and binding behavior.

These are declared input pins, not proof of the complete import/native dependency
closure, inherited environment, a stable cwd's contents, or mapped process bytes.
The row still needs to capture live tools/list and serving custody. A passing
configuration test supplies no inference or catalog-growth acceptance evidence.

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

## Isolated file-tool adapter

`scripts/harness/hs4_p6_candidate_mcp.py` is an explicit candidate launcher,
not an active-server registration. It loads the declared orchestrator checkout,
then registers `read_range`, `peek`, `grep`, `peek_grep` and `outline` against its
shared `exploration_core`. Supply `--orchestrator-root` and one or more
`--read-root` arguments. Every call must provide an absolute root within those
admitted directories; path resolution and bounded reads remain in the shared
core. The session stamp is accepted but grants no read scope.

This stage is incomplete for the full P6 comparison: `code_search` has not moved
to the shared core. Do not freeze the trial catalogs until root-bound search is
implemented and qualified. Existing actor catalog/config and production MCP
registration remain unchanged. The adapter's structured grep result and
character-page peek are explicit candidate contracts, not proof of actor output
compatibility; actor migration still needs its seat tests. No catalog-growth
acceptance follows from these controls.

The focused tests exercise actual FastMCP tools/list, stamped tool calls,
unknown-argument refusal, read-root admission, traversal and symlink escapes,
4 MiB file limits, bounded grep output, shared read/outline behavior and
unbounded peek refusal. They require FastMCP and the orchestrator checkout via
`HS4_P6_ORCHESTRATOR_ROOT` (default: the canonical local checkout). A missing
checkout or dependency skips the suite and must never be reported as a pass.
The tested core is `epyc-orchestrator` commit
`a6f65249f4ca2190efbca897b2a6d506c7441799`, path
`src/repl_environment/exploration_core.py`, blob
`faecdb52803243a7076c2b3dedfa5e847253f14a`.
