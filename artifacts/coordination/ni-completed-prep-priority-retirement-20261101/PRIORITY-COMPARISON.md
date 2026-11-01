# Priority preview comparison

Source is fresh ROOT `c3e89f524bd938fc58646ff9ed6e5b1218033181`; baseline was generated in memory from the same source/index tree with the original `HEAD:scripts/handoffs/backlog_priority_curated.json`, and preview is the regular generator `--out` result with MAIN-applied curated SHA `38d2e04f6690dff9fb34941a12e6bbe40e69eb211a7b1ecf51275b18117eb06b`.

- T0 snapshot: 66 → 62. Exactly the four reviewed completed IDs disappear.
- Remaining 62 entries retain identical order and identical row/kind/score/blocker/owner/why fields. `codex-ni-gnx-r2-nativeproof-20261026` remains present.
- Output has 174 rows and 1 done-pending checkbox in both baseline and preview. No open parent handoff boxes were edited; no new tick or native-proof closure.
- The synthetic prep removal changes row priority summaries for: INF-65, RTG-58, RTG-57, INF-22, INF-81, INF-50, INF-75, UFH-12, INF-23, INF-62, INF-79, UFH-08, UFH-01, RTG-61, INF-44, INF-70, INF-60. These are derived summaries for rows mapped to retired prep items or displaced by rank changes. No scoring weights or ordering algorithm changed.

Preview file SHA-256: `77bb32516ea0f884a08d1c40d083b6c01f43d8bdb8556468fb809da2e402c2f3`.

The preview remains scratch-only; MAIN owns applying the generated output.
