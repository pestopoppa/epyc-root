# Citation repair evidence (private, source-only)

Captured from `fff1aee9e3d0c7b4317e0bb68f375802bf356b6a`; SHA-256 pins are in `evidence.json`.

- `intake-408` has five indexed key claims, all about episodic-memory evaluation/benchmark properties. No claim concerns reasoning-model classification or the `ModelFeatures` schema. Its ledger rows map only `_00` through `_04`. The old reference does not support the proposal. Draft withdraws the proposal pending an independently recorded rationale and uses `#record` solely to discuss the index record; it does not make a graded source claim.
- `intake-1333` has five indexed key claims. Claim `#01` explicitly states that all seven regressions occur on the three smaller models and cluster in orchestration-heavy capabilities, and that sub-agent delegation scores 0.42–0.45 on the fast tier. `reported_results[5]` records the Appendix A Qwen 3.6 MCP `.65 -> .50` example. Thus `#01` is the precise in-range key claim matching the risk note; no `#05` exists. The ledger currently has zero rows for `src_intake_1333` / `clm_intake_1333_*`; under `citation_gate.py`, the corrected citation classifies `unknown` (substrate coverage gap), not `ok`. No ledger change is proposed.
- The original scoped cite-check found exactly two dangling references. Other reported unknown citations are untouched.

`decision-aware-routing.citation-repair.patch` is the exact proposed hunk. `decision-aware-routing.prepared.md` is a scratch-only validation copy, not a canonical edit.
