# Planning-context canary drafts

These scripts replay the 2026-10-25 harness documented in
[the original report](../../../docs/reference/loop-canary-2026-10-25.md).
The unchanged historical scripts remain in its accompanying harness directory.
They execute no inference: B uses the strategy store hash fallback, which changes
semantic rankings. B therefore reports UNKNOWN even if its visible checks pass;
it cannot certify full-fidelity wiring. A reports FAIL if either its exact
belief-section conclusion or the actual formation-guard refusal is absent.

Set `CANARY_SCRATCH` to a new private path under /mnt/raid0/llm/tmp and run
`python3 setup_scratch.py` under the site's resource admission supervisor. Set
`CANARY_ROOT` to the explicit root checkout, and `CANARY_ORCH_SOURCE` to
the explicit orchestrator source checkout. Set `CANARY_STATE=$CANARY_SCRATCH/state/A`
and `CANARY_INDEX=$CANARY_ROOT/research/intake_index.yaml`. Put the research
checkout and its `scripts/kernel_rnd` on PYTHONPATH for A. Run, under the
same admission supervisor:

```text
python3 run.py a gate /absolute/root/checkout
python3 run.py b
```

B requires the orchestrator's installed dependencies and historical host data
under /mnt/raid0/llm/epyc-orchestrator. It reads the live baseline and journal,
and copies the strategy store and state; the cooperative Python audit guard denies network access,
non-scratch writes and unguarded children. It is not kernel-enforced isolation against hostile native code. Ledger mutations are confined to the
private copy. Output includes hashes and blocked operations. Unavailable imports,
missing inputs or a crash produce UNKNOWN through `run.py` (exit 2); FAIL exits 1
and PASS exits 0. Inspect the full summary and provenance before treating a
replay as evidence. The historical replays do not reproduce live profile/launch
sections and no planner or model is invoked.
