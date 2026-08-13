# mainC — resume RTE-Prefix (prefix-cache audit, live A/B measurement)

## 1. Drain first

```
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python scripts/coordination/session_bus.py drain --agent mainC
```

Act on MUST-ACT items. Refresh your heartbeat after draining.

## 2. Assigned row

**Task text (the identity):** `repl-turn-efficiency--Prefix-L107`
**Row ref (a hint only):** `handoffs/active/repl-turn-efficiency.md:107`

Your prior session already completed the static audit and landed two instrumentation fixes and a
flag-gated prefix-stable order:
- `epyc-orchestrator d977454e` — fix(llama-server): read v9 KV-cache fields for cache stats.
- `epyc-orchestrator 2c4087b7` — feat(rte-prefix): flag-gated prefix-stable prompt order + A/B harness.

Remaining: the **live A/B measurement** on `bench_repl_prefix_stability.py --order both` — per-turn
hit ratios for legacy vs stable order, then decide whether to flip `prefix_stable_order` to
default-on.

This needs a compute window: send a `compute-request` to `inference` (BUS_PROTOCOL rule 11,
`llama-server -np 1`, CPU region, est 0.75h) and wait for the grant. Do not self-claim compute.

## 3. Wrap-up at checkpoints

Run the wrap-up skill at every checkpoint boundary. Write your own progress file at
`progress/2026-08/2026-08-13-mainC.md` (update the one from this morning).

## 4. Compute

Compute windows are granted by `inference` at its discretion. Do not self-claim CPU regions or the
MI210 (operator directive 2026-08-13, BUS_PROTOCOL rule 11).
