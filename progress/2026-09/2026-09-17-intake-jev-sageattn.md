# 2026-09-17 — research-intake session `intake-jev-sageattn` (full wrap-up)

## Problem / mandate

Operator submitted two research digests — (1) one-pass typed decisions instead of autoregressive JSON
(Reconstructing Jev-Like Inference) and (2) agentic porting of SageAttention3 from CuTe C++ to CuTeDSL —
plus steering: PAW for agent-loop robustness and a deterministic/fuzzy authoring GUI; Jev techniques into the
orchestrator (JSON schemas / tool use / fast routing / episodic-memory writes); the porting methodology into
autokernel. Nine URLs were supplied; the two digests were inline material.

## Method (four-stage research-intake, full flow)

- **Stage 1** — fresh worktree `intake/jev-sageattn-20260917` off `origin/main` `6f346ea3` (shared `/workspace`
  clone is 529 commits behind with peer work; all writes in the worktree). Unbounded dedup sweep (0 exact
  collisions; `programasweights` = companion artifacts of intake-811, not duplicates). Phase 1+2 fanned out to
  6 subagents; 10 entries persisted (`intake-1460…1469`); Phase 3 expansion (cap 10) added `intake-1470…1479`.
- **Stage 2** — operator selected all 8 ranked dive groups. 16 entries dived against pinned primary sources
  (13 dive-verified, 2 dive-overturned — `intake-1466` "no accuracy numbers on the docs site" false;
  `intake-1471` "no sample sizes" false — 2 remain stage1-unverified because the source threads are
  unfetchable). Per-claim corrections + span anchors + dependency edges recorded; operator essay ingested as
  `intake-1480`; 12 operator-selected dive-surfaced sources ingested as born-verified `intake-1481…1492`.
- **Stage 3** — plan mode: one plan covering 3 new stubs, 10 handoff edits, 3 index rows, 1 operator decision,
  and explicit declines; all five plan-completeness gates passed; operator approved.
- **Stage 4** — plan implemented exactly; OP-43 closed mid-flight by operator ruling.

## Changes made

| File | Change |
|---|---|
| `research/intake_index.yaml` | 33 entries appended/amended (`intake-1460…1492`); intake-811 blocker corrected + `monitor→integrated`; per-claim corrections, anchors, depends_on edges, handoffs_updated/created fills (head bytes preserved on every write; pre-write backups in `/workspace/tmp/intake-jev-sageattn/`) |
| `handoffs/active/typed-decision-plane.md` | **new stub** — TD-1/TD-1a/TD-2/TD-3/TD-4/TD-5 (one-pass typed decisions over llama.cpp; native candidate-scoring fast path; calibration before any gate) |
| `handoffs/active/paw-compiled-specialists.md` | **new stub** — PAW-1…PAW-5 (license scope resolved 2026-09-17; self-hosted compile spike; FuzzyBench eval with vidya wiring first) |
| `handoffs/active/fuzzy-workflow-authoring-gui.md` | **new stub** — FW-1…FW-3 (deterministic/fuzzy process authoring) |
| `handoffs/active/routing-intelligence.md` | +RI-14 (renumbered from RI-11/RI-12 collisions) |
| `handoffs/active/learned-routing-controller.md` | +LRC-TD-1 |
| `handoffs/active/canonical-judge-suite-revamp.md` | +CJ-13, +CJ-14 |
| `handoffs/active/eval-benchmark-cost-reduction.md` | +ECR-TD-1, +ECR-TD-2 |
| `handoffs/active/episodic-memory-integrity.md` | +M-19 (renumbered from M-17 collision) |
| `handoffs/active/tool-use-eval-contract.md` | +TU-TD-1 |
| `handoffs/active/autokernel-research-loop.md` | +AK-PORT-1/2/3 (methodology only; unverified port numbers non-citable) |
| `handoffs/active/agentic-rocm-kernel-authoring.md` | cross-ISA port evidence rider (LuXuxue = RDNA-only, never gfx90a evidence) |
| `handoffs/active/vidya-belief-substrate-program.md` | +VB-TDP-1 (write-side wiring before first measurement run) |
| `handoffs/active/{routing-and-optimization,inference-research,user-facing-harness}-index.md` | rows RTG-56, INF-76, UFH-09 |
| `handoffs/active/master-handoff-index.md` | OP-43 opened then closed (row removed per OP-9 precedent; ruling recorded in PAW stub + intake-811) |
| `research/intake-stage3-plan-2026-09-17-jev-paw-autokernel.md` | **new** — approved Stage-3 plan |
| `.research-session.json` | full four-stage session record incl. two steering-ledger rows, dive results, rulings |

## Verified findings of record (dive-verified)

- **Calibration is the gap, not speed**: candidate-softmax confidence is uncalibrated (65% of a 7B's wrong
  fields scored >0.90) and the local one-pass speedup is 3.4–7.9x vs same-model JSON, not 40–200x (intake-1474);
  a fully local pinned implementation measures 5.21x and 20 decisions/s parallel reuse (intake-1487).
- **Jev quality is not established**: independent rerank reproduction ties Cohere Pro (nDCG 0.692 vs 0.691, CI
  crosses 0) with 24.7% order sensitivity (intake-1486); the vendor's own evals put Jev behind Sol/Opus
  (intake-1471, corrected); the cited "3–329 s" baseline is not derivable from its cited live page (intake-1492).
- **PAW is artifact-available but not officially self-hostable**: weights (2026-06-07) and FuzzyBench data
  (2026-02-17) predate the 2026-07-11 blocker; an unofficial MIT server compiles locally for the default
  Qwen3 compiler (intake-1481), independent eval shows 94–97% on one adversarial task (intake-1482).
- **Agentic porting**: digest port claims have no fetchable primary source and are non-citable; the harness
  patterns filed are generic standard tooling only; the only real cross-ISA artifact found is an RDNA-only HIP
  port (intake-1491).

## Gates

- `validate_intake.sh` exit 0 (1,488 entries).
- `index_state.py --check` exit 0 (0 problems); cite-check clean after adding per-claim corrections and
  converting the 1492 reference to `#record`.
- 27 new task checkboxes, 1 flip (PAW-1 resolved), 3 index rows, 1 operator decision opened and closed.
- Operator ruling applied: **everything is internal research** → PAW license scope resolved; distribution
  questions are out of scope for all current work.

## Deferred / carried

- Nothing blocked. PAW-2 (self-hosted compile spike) and PAW-3 (FuzzyBench eval) proceed; PAW-1 done.
- Thread-source URLs for the two Maharshi X posts remain unavailable; intake-1461/1480 stay stage1-unverified
  and their numbers non-citable (recorded).
- The full wrap-up's operator-cadence steps (index pruning, wiki compilation sweep) were invoked by the
  operator for this run and are executed below.

## Implementation round — typed-decision plane (operator: "take ownership and implement")

TD-1/TD-1a/TD-2/TD-3/TD-4 implemented in `epyc-orchestrator` on branch `intake/jev-typed-decisions-20260917`
(worktree `/mnt/raid0/llm/worktrees/sub-jev-tdp-orch`): new `src/typed_decisions/` package (types, Draft 2020-12
schema, JSON runner with typed failures + corrective retry, adapter-verified confidence formulas, native
candidate-scoring path, bench harness, contamination/calibration/fanout studies with receipts, closed-set
tool-arg mapping), flag `typed_decisions` default off, 87 unit tests.

Live measurements on the MI210 GPU (frozen-v9 HIP server; small window between autokernel CPU runs; server
launched and killed by this session):
- contamination: 6.25% flip rate (Qwen3.8-27B-Q8_0, 3/48 pairs) vs 37.5% (LFM2.5-2.6B, 18/48).
- calibration: 91.7% acc / ECE 0.0625 / Brier 0.078 (27B) vs 50.0% / 0.267 / 0.313 (LFM).
- fan-out: 1.54x (3 batched vs 12 singleton calls, 100% agreement, LFM).
- native (TD-1a) live validation FAILED CLOSED: 23/24 `native_unknown_candidate` from non-tokenizer-mapped
  candidate strings → new task TD-1b (tokenizer-aware candidates) filed; no speedup claim.

Belief-kernel write side wired first (VB-TDP-1): `scripts/vidya/adapters/typed_decisions_measurement.py` +
source row + CLI ingest; 5 measurement receipts projected → 11 claims / 33 frames (bench report refused as
non-measurement). `metric_direction` write-side gap fixed in the producer.

## Implementation round 2 — TD-1b + TD-5 + worker-model measurements

- TD-1b (tokenizer-aware native candidates) and TD-5 (routing shadow) implemented in `epyc-orchestrator`
  branch `intake/jev-typed-decisions-20260917`; 167 focused tests; commit `53000834`.
- Live round on the production worker (`Qwen_Qwen3.6-35B-A3B-Q8_0.gguf`, MI210, v9 HIP server, 55% VRAM,
  launched/killed by this session): native arm mechanically fixed — 0 unknown-candidate failures, 8/24
  unsupported by tokenization design, 16/24 resolved, **18.9x faster** (1.03 s vs 19.4 s), but agreement
  11/16 and native accuracy 68.8% vs JSON 91.7% on the overlap -> TD-1c filed (semantic parity).
- Long-context fan-out (three 40k-char states): **3.22x** (33.9 s batched vs 109.2 s singleton) vs 1.54x at
  small state; agreement there uninterpretable (content-neutral probe) -> TD-3b filed.
- TD-5 shadow smoke passed (one JSONL record, bounded daemon, fail-open); enablement for a labeled window is next.
- Operator steerings this round: "lets do this" (TD-1b), "agreed" (TD-5 shadow), and the reminder that Jev's
  advantage is speed/reliability, not correctness — now stated in the plan framing.
- 6 measurement receipts projected into the belief kernel (16 claims / 48 frames cumulative); bench reports
  correctly refused as non-measurements.
