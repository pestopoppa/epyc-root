# CF-3c deterministic policy continuation pilot

Run `python3 -B scripts/experiments/cf3c-live/prepare.py` from the lane. It
seals the cases, fixed recipe, harness, verified weight receipt and prospective
protocol under `/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c/packet`.
Preparation is offline and does not read model weight bytes. An identical
preparation returns the same packet. A changed checkout requires a new packet.

The returned `spec.json` is an input to the standard row publisher. Its smoke
runs six native template/tokenizer checks and one native A0 completion, then
waits for its private listener to exit. Smoke writes under the allocator's
dry-run directory. The official row makes one bounded 18-cell attempt. Its
complete result or partial record retains each started cell and its individual
raw HTTP streams and trajectory receipt.

Run the focused offline suite after preparation with
`PYTHONPATH=/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c/packet:/usr/lib/python3/dist-packages PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -B -m pytest -q --import-mode=importlib scripts/experiments/cf3c-live/test_cf3c.py`.

[Prospective pilot protocol](../../../docs/design/cf3c-pilot-protocol-20261118.md)
