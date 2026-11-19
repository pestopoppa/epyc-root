# CF-PB-1 native cache pricing

`python3 -B -m unittest discover -s scripts/experiments/cf-plan-boundary -p test_pricing.py`
checks break-even arithmetic, invalidation/reuse refusal controls, native
accounting and fixture prefix relations without inference.

`prepare.py` creates one detached source worktree and a sealed packet under
`/mnt/raid0/llm/tmp/delegation-context-preassembly/cf-plan-boundary`.
It reuses the prior verified model receipt and checks model stat and small
build/template identities. It does not hash weights. The packet pins shared
serving helpers by a root-repo git object; no external source is copied.
Preparation is refused over an existing packet to preserve attempts.

Publish the packet's `spec.json` using `publish_row.py --smoke-now`; the
publisher's four-core native smoke is the only direct inference run.
The official six pairs run only under row admission. Keep partial outcomes;
never retry or substitute a pair. Read the native RESULT and apply
`completed == 6 and cache_witness_valid == 1` when filing. The handoff's
adoption question stays open after this diagnostic.

See [protocol](../../../docs/design/cf-plan-boundary-protocol-20261118.md)
for the prospective schedule, native cache witnesses, stop rules and limits.
