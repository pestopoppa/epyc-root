# CF-3c task-level diagnostic

Seal and verify the packet offline from the lane with:

```bash
python3 -B scripts/experiments/cf3c-task-level/prepare.py
```

The returned path, `/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-task/packet/spec.json`,
is the row publisher input. Preparation pins a detached orchestrator source
tree and reuses the prior verified model receipt. A repeat validates the
existing packet without changing cases or seeds.

Run the tests against the sealed packet with:

```bash
R=/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-task
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
PYTHONPATH="$R/packet:/usr/lib/python3/dist-packages" PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  "$PY" -B -m pytest -p no:cacheprovider --basetemp "$R/offline-tests" -q \
  --import-mode=importlib scripts/experiments/cf3c-task-level/test_task_level.py
```

Publisher smoke checks native rendering and tokenization for all six arms of
the reasoning-only case and requires a successful A0 workflow in the separate
old-head case. The official schedule covers all 18 case/arm combinations.
Each task starts from a seeded archive. The model chooses live tools and
arguments, receives their results and produces a terminal response. The
runner retains native evidence under `native/`. See the
[prospective protocol](../../../docs/design/cf3c-task-level-protocol-20261118.md).
