# ACP Registry — machine-readable registry of agents implementing the Agent Client Protocol

**Intake**: intake-2654 · **Verification**: dive-verified · **Read depth**: PARTIAL · **Source**: https://github.com/agentclientprotocol/registry

## What the dive found

2026-11-06 Stage-2 dive (read_depth PARTIAL; registry cloned at 7402d128935361c0f7c32842f5b98469b66f8d77 with full history, ACP spec at 7ec5185c). The claim that the registry tells a client what an agent can do is OVERTURNED: the shipped agent schema carries no authMethods, no protocolVersion, no capability block and no MCP field, so only 1 of 5 client questions is answerable from the published index; a nightly capability matrix exists but is repo-internal. Confirmed: 46 manifests, hourly bot bumps (89.8% of last-30d commits), per-agent auth handshake check, quarantine list. But quarantine gates checks, not publication (6 agents ship unmarked), the auth check only proves advertisement, binary automation is GitHub-only with four manual agents, and the matrix probes a method renamed in March 2026 (session/stop -> session/close). Verdict for EPYC: no adoption - the lane's ACP arm was closed on layer grounds (north-facing editor protocol vs EPYC's south-facing injection point) and the registry removes no existing work; borrow only the pin source discipline (archive + sha256 + platform keys, refusing the 7/22 entries without sha256) and the nightly-capability-diff pattern.

## Claims and corrections

- claim 0: **narrowed** — All 12 named ids exist, but the roster is 46 manifests, not 12. github-copilot is present in the repo but EXCLUDED from the default published registry.json (build_registry.py:820); kimi is archived by its vendor and superseded by kimi-code (added 2026-11-06).

- claim 1: **narrowed** — Hourly automation confirmed (cron 17 * * * *), but binary automation covers only GitHub-hosted repos; cursor, devin, kiro and grok-build are manual and three agents need bespoke sources. Per-platform targets are a manifest property, not automation output. quarantine.json gates update checks and auth verification only: build_registry.py never reads it, so quarantined entries ship unmarked. The separate auth gate launches each agent and requires >=1 method of type agent|terminal (client.py:102-112), but proves advertisement only, covers neither quarantined nor preview agents, and leaves the exempt set unmarked in the index.

- claim 1: **narrowed** — The matrix exists (39 agents, 239 nightly snapshots) but does not track stable v1: it probes session/stop (renamed to session/close on 2026-03-09; 0/39 support), probes session/fork (unstable schema only), never records mcpCapabilities or promptCapabilities although both are in the initialize response it parses, and omits the current stable delete/close capabilities. It is a repo artifact, not in dist/ and not referenced by README.


## Anchors

intake-2654 carries 6 verbatim claim anchors; see `research/intake_index.yaml` for quotes, locators and hashes.


## Actionables

Stage-3 plan: `research/intake-stage3-plan-2026-11-06-harness-inference.md`.
