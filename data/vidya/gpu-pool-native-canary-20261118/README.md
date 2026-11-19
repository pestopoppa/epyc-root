The GPU-pool canary accepts `--native-result` only for a complete non-smoke producer receipt matching the original sealed capture, exact row, digest, operator census and residency count. It refuses stale or unchecked reader context, including matching claim IDs from a nonfresh state. The existing shared carrier and candidate-local routing are unchanged.

After the original producer complete check passes, run:

```bash
python3 -BI scripts/vidya/canary/gpu_pool_context_exclusion.py \
  --capture /path/to/native/belief.json \
  --native-result /path/to/native/RESULT.json \
  --research /workspace/repos/epyc-inference-research \
  --scratch /mnt/raid0/llm/tmp/vidya-belief-substrate/pool-canary-native-replay
```

[Readiness controls](readiness.json) are software evidence only. The five already-prepared native captures, actual planning replay and production consumer adoption retain their separate acceptance requirements.
