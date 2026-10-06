# R-25 current reference-resolution matrix (private draft)

Source basis: ROOT `f5a316b64ac4078df0afc7d6e67a62645564037c`; no canonical edits applied. Stable alias decision: first event table (`F-33`…`F-36`, handoff `:117-120`) becomes `(a)`; second delivery-plane table (`:999-1002`) becomes `(b)`. Do not renumber or alter historical evidence snapshots. The dated alias note in the proposed active handoff maps old bare IDs by cited row/description.

| Current source consumer | Resolution | Draft action |
|---|---|---|
| Active coordinator ledger, rows `:117-120`, `:999-1002` | Row identities themselves | Label the two series `(a)` / `(b)`; preserve each row body and stable number. |
| Active coordinator ledger `:859`, `:1084`, `:1087`, `:1130`, `:1141`, `:1170`, `:1178` | Delivery mechanisms / composer reporting | Qualify F-33/34/35/36 as `(b)` by local context; patch includes explicit mapped instances. |
| Active coordinator ledger `:122-145`, `:561` | Original-row evidence and task | Existing evidence cites `(a)`; revise R-25 scope to include current cross-consumers, dated alias map, and no-history-rewrite rule. |
| `docs/design/loop-owned-fleet.html:339,414` | Correct-refusal / delivery-plane family | F-34 is `(b)`; family beginning F-33 is explicitly `(b)`; not a bare individual citation after mapping. |
| `scripts/coordination/tmux_adapter.py:825` | F-34 refusal loop | `(b)` (delivery-plane defect). |
| `scripts/coordination/worker_runner.py:28` | C51–C56 / F-33–F-43 delivery class | F-33 start is `(b)`; revise to `F-33(b)–F-43`. |
| `tests/test_tmux_adapter.py:272,298,2339` | F-34 refusal loop | `(b)`. |
| `tests/coordination/test_mech_column_audit.py:22,502,507,525` | Historical doorbell/C55 MECH-UC evidence | F-35 is `(a)`; The mixed pair is `F-33(b)` (bare Enter/wake character) plus `F-35(a)` (original doorbell failure); do not infer suffix from pair proximity. |
| `handoffs/active/session-bus-thin-dispatcher.md:3165` | Lost-track evidence note | Already uses F-33(a); no change. |
| `wiki/agent-architecture.md:1090,1199` | Lost-track evidence note | Already uses F-33(a); no change. |
| `research/intake_index.yaml:129893` (`intake-1325` relevance) | Doorbell failure at old `:119` | Exact narrow change to F-35(a); separate patch file. |
| `research/intake_index.yaml:132631+` current collision direction | Four collision pairs | Name both `(a)/(b)` members explicitly; patch in `R25-intake-current.patch`. |
| `docs/reviews/rtg48-mech-column-audit-2026-08-23.md:32,34` | Dated audit snapshot; F-33 pane-drain caveat, F-35 doorbell | Historical snapshot retained unchanged; alias mapping lets readers resolve F-33(a), F-35(a). |
| `progress/2026-08/2026-08-13-coordinator-agent.md:106` | Historical filing of original first series | Immutable progress snapshot retained unchanged; resolves to `(a)` by first-table chronology. |
| `progress/2026-09/2026-09-07-research-intake-wave.md:33` | Reports collision as a set | Historical progress snapshot retained unchanged; no individual bare citation. |

Source grep also surfaced `research/intake_index.yaml` historical analysis passages that describe collisions or prior citations. They are preserved as record text; current R-25 direction and active intake relevance are corrected, and the active handoff alias map supplies retrospective resolution. Generic collision-set references may name both versions explicitly; individual current citations may not remain bare.

The current YAML intake aliasing sites included in the separate intake patch are: `intake-1325` relevance (`F-35(a)`), `intake-1331` collision pair definition (`F-33(a)/F-33(b)` through `F-36(a)/F-36(b)`), its detailed row comparison (`F-33(a)` vs `(b)`, likewise F-34–36), the number-collision finding/action (explicit four pairs), the dive-note dispatch attribution (both F-33 series named), and the stage-1 actionable cross-link (`F-33(a)`). Older dated progress/audit snapshots are not edited; the live handoff alias table resolves them by row semantics.
