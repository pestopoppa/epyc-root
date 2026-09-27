# 2026-09-27 — narrowed plan applied (workspace-8d, root writer)

The operator adopted a narrowed plan after a Fable audit of workspace-8d's 2026-09-25 to 27 work. The audit found
that the thesis had been named but never measured, while infrastructure grew. The thesis is: the orchestrator must
beat the strongest model plus an off-the-shelf harness.

## Freezes

Each frozen box carries `❄ FROZEN 2026-09-27`, a reason and an unfreeze trigger. The boxes stay open.
- **HS-19b, HS-19c and HS-19d P1–P6.** HS-19d.0, the design, stays done.
- **TD-28**, plus VB-TD-ADVICE. These wait until v11 native scoring exists AND the thesis verdict is in.
- **REPL-EMB-0.3** (the GPU embedder) and **REPL-EMB-1.4** (the saturation-guard B+D policy). The UFH-12 A1 duty sweep
  is cancelled. These wait until the UFH-12 retrieval eval passes.
- **DAR-LAT-3i**, and **DAR-LAT-1/2/3/3a/3g/3b/3c** plus VB-SEL-LOADAB. Only DAR-LAT-3h's G1 proceeds.
- **LRC-1** and **LRC-2**.
- **OD-A F7 and F6** (the KTransformers port).

Index updates:
- UFH-12 and RTG-09 now point at the next live step.
- OP-64 (the HS-19 discussion) is recorded as decided.

## Thesis experiment: UFH-13, TOP priority

A new handoff, `handoffs/active/thesis-experiment-orchestrator-vs-strongest-model.md`, is promoted from REPL-EMB-B.1.
Its arms, all through OpenCode → `/v1`:
- **A0:** Flash-Next alone.
- **A1:** frontdoor alone.
- **A2:** frontdoor with escalation to the consultant. After the role swap, the consultant is `architect_general`
  = Flash-Next.

The suite is the frozen MMLU-Pro 200 + GPQA 195 manifest (sha256 `1532906b…`), which Flash-Next already scores
0.755 / 0.6513 on. The proposed rule is G ≥ 0.75 at d ≤ 0.50, with the lower CI bound of G above d. The operator
confirms it through OP-66.

Blocker found: `/v1` never escalates (orch `openai_compat.py:595-596`). TE-1 adds a default-off escalation flag for
A2. The belief-kernel write side is filed as VB-THESIS-1, with a source-table row.

## UFH-12 kill rule (REPL-EMB-2.1 draft)

- Primary k = 5.
- Hybrid must beat the best lexical arm by M = 0.10 in recall@5, with a paired-bootstrap lower bound above 0, or
  UFH-12 stops at lexical.
- The cheapest arm within X = 0.05 of the best wins.
- n ≥ 120 queries.
- The operator confirms it through OP-66.

## Governance repair

Every ratifier in `scripts/operator/`, plus the unapplied `artifacts/operator/ratify_p_kld_divergence_protocol_20260915.sh`,
now refuses an unset `RATIFY_OPERATOR`, a system account, the login account and agent ids. The shared guard is
`scripts/operator/lib/ratify_operator.sh`, and the rules live once, in `ratification_receipt.py check-operator`. The
receipt tool now returns REFUSED instead of recording `$USER`. The `run_*` wrappers apply the same check.

One exempt script, `ratify_actor_seat_wire_test_20260926.sh` (historical, applied at b3e1bb00), was left untouched:
- Its exemption pins the as-run sha256. Editing the script would lapse the exemption, and the checker would then fail.
- The exemption list is human-only, so the pin cannot be moved by an agent.
- The script's fallback line cannot be reached: the script reports ALREADY RATIFIED and refuses to double-sign.

Countersignature: `artifacts/operator/countersign/COUNTERSIGN-20260927.md` records four ratifications:
P-SERVE-SEL-1, OP-63, TRUST-BOUNDARY-RECEIPTS-FIX (it recorded `operator: node`) and DAR-LAT-3h. Each is
CHAT-CONFIRMED, with its terminal countersignature PENDING. `scripts/operator/countersign_20260927.sh` is for the
operator to run later; it has not been run. Master queue row: OP-67.

Tests: `tests/validate` + `tests/harness` + `tests/test_ratify_v10_episodic_repin.py` pass (see the commit). The
receipt checker is at exit 0 (45 scripts: 16 receipted, 29 exempt, 0 failing), and `index_state.py --check` is at
exit 0.
