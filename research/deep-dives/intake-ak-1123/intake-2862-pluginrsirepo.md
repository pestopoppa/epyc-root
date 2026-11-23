# Dive — pluginrsirepo — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://raw.githubusercontent.com/syr-cn/PluginRSI/main/README.md", retrieved: "2026-11-23", sha256: "ae163ec09e7b"}
> SOURCE-QUARANTINE: {url: "https://github.com/syr-cn/PluginRSI @ bafab39e4c62b7f0aa252f2ffd891886b45c82f8 (clone, reading material)", retrieved: "2026-11-23", sha256: "n/a"}

Bearing: intake-2859 ledger PR2 (manifest, AP-DGM-PROV) and PR4 (status split). Reuses the wave-1 admission reading.

## 1. Stage-1 fields
PluginRSI code release; Yaorui Shi, Yuchun Miao, Yuxin Chen, Jiayuan Zhang, Yueqing Sun, Xierui Song, Xiang Wang, An Zhang; MIT, last push 2026-10-18. Categories: autonomous_research, agent_architecture, tool_implementation. Novelty low; relevance medium. Credibility 1 = within 12 months +1. Verdict: adopt_patterns (field list and status split as schema text only).

## 2. Key claims
0. **Manifest. CONFIRMED, PR2 narrowed.** `PluginManifest` (`schemas.py:19-30`, `extra="forbid"`): `schema_version` (Literal 1), `kind` in {role, tool, skill, memory}, `name`, `version` (`^v[a-zA-Z0-9_]+$`), `entrypoint` (`module:Class`), `description`, `provenance` (free dict), `config_schema`; `ref` = `kind/name/version`. A harness binds alias to `{ref, config}` (`schemas.py:33-47`). Seed `coder/v0001` provenance: `label, sources, upstream_assets, adaptation`. `parent_refs` is not a schema field: the controller writes `[source_ref]` (`proposer.py:38`) and validation requires label, sources, upstream_assets, adaptation and every parent in the frozen library (`proposer.py:117-125`). No digest field: identity is the ref string. Anchors 0-1.
1. **Versioning. CONFIRMED.** Controller assigns `v_<candidate id>` (`loop.py:343`); a mutation creates exactly one plugin with it (`proposer.py:101-102`), cannot reuse a published ref (:103-104), must be referenced (:114); the published library is checked unchanged after each proposal (`loop.py:457-458`). Local mutation keeps kind/name and changes only the assigned alias ref; workflow, alias, instance config compare equal (`mutation.py:45-59`). Anchor 2.
2. **Status split. CONFIRMED, PR4 narrowed.** Row: `completed` and `solver_limit` are usable, `infra_error` unusable, anything else a candidate error (`selection.py:21-23`). Record: `candidate_error`, `completed` (valid ratio >= threshold, no candidate error) or `infra_error`; `mean_score` null unless accepted (:24-28), so a shortfall is "no measurement", not zero. `paired` compares tasks both valid and needs `ceil(n(2r-1))` matched tasks (20 tasks, r=0.95: 18; `mutation.py:28-42`). Thresholds: default 1.0 (`schemas.py:130`); swe 0.95 for batches, 0.975 for selection and held-out (`configs/swe.yaml:31,50`; `runner.py:29-32`). Retry is infra-only (`runner.py:19-20`), `infra_retry_attempts` default 0 (`schemas.py:132`). Wave-1 "fails a candidate only on candidate errors" is PARTIAL: an infra shortfall also yields no score. Anchor 3.
3. **Cached-parent admission re-confirmed. CONFIRMED.** `branch_feedback` reuses the incumbent's rollouts (`loop.py:280-288`). Anchor 4.

## 3. Reported results
README repeats paper numbers (Kimi-K3 SWE-bench held-out 69.0 vs Meta-Harness 63.0); none new. Confound analysis is in intake-2859.

## 4. Performance-principles table
| Mechanism | MI210 | Zen 5 |
|---|---|---|
| YAML manifest, alias binding, status record | n/a (host files) | YES |
| Rollouts feeding the status split | solver served on MI210; counts only | n/a |

## 5. In-house state
AP-DGM-PROV (options A and C default-off) and BSV-2 (`autopilot-program.md` L123, L935-L946 @ d785b6d). Life-Harness implements the same "budget exhaustion is a measurement, not an outage" convention (`ContextLimit`, `life_optimizer/context.py:23`): design agreement, not replication. Upstream-present: n/a.

## 6. Derived-actionables ledger
| # | Task | Owner | Compute | Rule |
|---|---|---|---|---|
| PR2a | Refines PR2: journal fields `schema_version, kind, name, version, entrypoint, description, provenance{label, sources, upstream_assets, adaptation, parent_refs}, config_schema`, plus what PluginRSI lacks: a content digest and the producing evaluation id. | `autopilot-program.md` AP-DGM-PROV | doc-only | Done when the note carries the list and a digest decision. |
| PR4a | Refines PR4: row statuses `completed, solver_limit, infra_error, candidate_error`; record statuses `completed, candidate_error, infra_error` with null mean; batch and full thresholds; infra-only retry; budget exhaustion is scored, not infra. | `autopilot-program.md` BSV-2; `harness-program.md` HIL-2 | doc-only | Done when the schema names them. |
| PR6 | DECLINE: vendor the `pluginrsi` package. Schema and status rules transfer as text; the package carries a SWE-bench and Docker runner nothing here uses. | n/a | n/a | n/a |

## 7. Dive-surfaced sources
None. Project page and `.claude/skills/pluginrsi-*` change no row.

## 8. Contradiction pass
Wave-1 PR2 implied manifest-level parent references; code enforces them only for new plugins at proposal time. Hashing is forbidden in proposed plugin code (`proposer.py:17-24`), so no digest exists to adopt. No independent replication.

## 9. Read depth
PARTIAL: schemas, selection, proposer validation, runner thresholds, one seed manifest; graders, adapters, prompts not read; nothing run. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e.

## Anchors (verbatim substrings of page.txt, verified)
0. `| Plugin schema `H(W, P)` | [`schemas.py`](src/pluginrsi/schemas.py), [`loader.py`](src/pluginrsi/loader.py), [`contracts.py`](src/pluginrsi/contracts.py) |`
1. `Each plugin records its sources in its provenance metadata.`
2. `a variant is added to the library only if it beats its parent on the same minibatch`
3. `The new harness must improve full held-in accuracy to replace the incumbent.`
4. `| Memory | Incremental evidence retrieval | 10/19 → 14/19 |`
Claims 1-3 rest on repo code.

## 10. Artifact audit
artifact audit: clean
