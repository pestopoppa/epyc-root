# KPF-31 impact run — retained native evidence

Row `kvfork31-p3-impact-20261102` ended rc1 on 2026-11-02 at 22:59:04Z. Bound source HEAD: `c72ec82f5417bb2937310326120f149b665e8400`.

Verdict: **INCONCLUSIVE**. The decision requires resolved-risk native upstream impact output for `find_slot`, `apply_ubatch`, and `llama_kv_cells`. `results.jsonl` contains only the explicitly partial preliminary source-reference scan; no impact outputs are present. The source scan cannot satisfy the rule.

`analyze.stderr` shows repeated parser idle timeouts, exhausted cumulative timeout budgets (210 s next total over the 150 s cap), dropped worker slot after its respawn budget, and a terminating native `Napi::Error`. `analyze.stdout` also warns that the default `master` branch is not the primary index and reports large files skipped. The immediate failing stage is analyzer termination before the impact queries; branch/index identity and parse completeness need correction or explicit handling before a continuation. These logs do not prove a source-code risk class, correctness, or benchmark result.

All original files from `out/` and `identity.json` were copied here before filing/reaping; `SHA256SUMS.json` binds them. No frozen production tree was changed.
