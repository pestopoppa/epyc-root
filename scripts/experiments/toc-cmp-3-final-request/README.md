# CMP-3 final REPL request candidate

Apply `orchestrator.patch` after both the CMP-3 contract and post-fold runtime patches on orchestrator commit `12afe2858f9dbd4691447926d6cf1864de64348c`. The new `context_compaction_final_request` flag defaults off and requires the compaction contract. It can operate independently of the boundary evaluator. Install the explicit async callback with `configure_final_request_check(state, evaluator, evaluator_id, timeout_s)`. It receives a request-bound case and returns UTF-8 JSON bytes in the seven-field CMP-3 schema.

The REPL checks each supported HTTP generation attempt after the backend assembles its payload. Each permitted attempt has one exact literal contract, seven evidence-validated entailed decisions and a fresh check for that payload. A failed attempt blocks further guarded continuation on that task state. The runner uses a recording HTTP transport for the worker and a private Qwen3-4B evaluator. See the [screen protocol](../../../docs/design/toc-cmp-3-final-request-protocol-20261118.md).

Run the offline integration regressions using the patched orchestrator worktree in `PYTHONPATH`.

```bash
PYTHONPATH=/path/to/patched-orchestrator:/usr/lib/python3/dist-packages \
  /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -B -m pytest -q \
  scripts/experiments/toc-cmp-3-final-request/test_final_request.py
```

Run `prepare.py` once on fresh scratch to seal the spec and source. Preparation reuses the earlier model identity receipt. The prepared spec is `/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3-final-request/packet/spec.json`. The publisher smoke records one intact attempt. The official row records all three fixed attempts and retains partial artifacts if a transport or integration check fails.
