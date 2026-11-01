# Completed NI inference-prep priority retirement

MAIN applied an evidence-reviewed metadata patch that removes exactly four completed synthetic T0 entries from `scripts/handoffs/backlog_priority_curated.json`. The generated priority output was also applied under canonical W. This filing preserves the source patch, completion evidence, comparison, and exact applied SHAs.

The retirement covers only the completed work represented by these prep IDs: Meta private C5 host-view build, HPR fixture environment source proof, HPR golden-original custody publication, and GNX ESRCH source publication. It does not close parent handoffs, claim performance/quality, change HPR native-contract state, or close the separate GNX native-proof task.

## Applied inputs and outputs

- Curated source base SHA-256: `2a253c06cac66e38e0c2fd5a1198eac6993fa327dd788f3a6a4e25bf82bbd258`
- Curated source after MAIN apply SHA-256: `38d2e04f6690dff9fb34941a12e6bbe40e69eb211a7b1ecf51275b18117eb06b`
- Exact four-entry patch SHA-256: `ea9e3429b920627a33c7740a0636b7ae5337f1eda0d27701cc12ca1962325179`
- Generated priority output SHA-256: `77bb32516ea0f884a08d1c40d083b6c01f43d8bdb8556468fb809da2e402c2f3`
- ROOT source HEAD used for regeneration: `c3e89f524bd938fc58646ff9ed6e5b1218033181`
- Same-HEAD baseline document SHA-256: `97279ac429f116b89f7723e27362a7c5e84e5f5f73aa1e6e79fefa991a204bdf`

The regular priority generator ran with `--out` after the curated apply; `--seed-prep` was not used. The comparison confirms T0 66→62; the four IDs are absent; all remaining 62 preserve order and row/kind/score/blocker/owner/why; the separate GNX native-proof ID remains; the 174 row summaries and one preexisting done-pending checkbox remain. Seventeen derived row summaries move because the prep bases/rank positions changed. No row weights, scoring method, tiers, kinds, or parent handoff checkboxes changed.

## Validation and publication

`backlog_priority.py --check` passed at ROOT `c3e89f524` (age 0, tier drift 0/174). After the approved generated-state refresh, `index_state.py --check` passed with 0 problems. The only tracked index change is the generated master summary count for routing-and-optimization (651→650); no domain-index row or handoff box changed. The ignored `.index-state.json` and `.index-graph.json` were refreshed.

Canonical generated priority output and curated metadata are present in the ROOT working tree. This artifact and the per-agent progress shard are being published together in the ROOT metadata commit. The standard append-only agent log is runtime-only and is not part of the Git commit. No FILLERS, grant, queue, source code, handoff row, checkbox, quota, measurement, or quality record was changed.
