# CF-3c active-evidence diagnostic

Run `python3 -B scripts/experiments/cf3c-active-evidence/prepare.py` from the
lane. Preparation seals a fixed 18-cell schedule, paired seeds, source-pinned
orchestrator worktree, serving recipe and retained weight receipt under
`/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-active/`. It verifies
model identity using the prior receipt and file stat. Repeating preparation
with the same inputs returns the existing sealed spec.

The returned `packet/spec.json` is the standard row publisher input. Publisher
smoke renders and tokenizes all six arms of the reasoning-only fixture and
requests one A0 continuation. Smoke records which native renders expose the
target and verifies the private listener exits. The official run records
each started cell and its raw native exchanges under `native/`.

Run the offline checks after preparation with

```bash
PYTHONPATH=/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-active/packet:/usr/lib/python3/dist-packages \
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -B -m pytest \
  -q --import-mode=importlib scripts/experiments/cf3c-active-evidence/test_cf3c.py
```

[Prospective protocol](../../../docs/design/cf3c-active-evidence-protocol-20261118.md)
