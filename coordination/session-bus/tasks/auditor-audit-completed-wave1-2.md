# auditor — Audit batch: completed mainA/B/C/D work (wave 1+2)

**You are auditor** (roster id `auditor`, reviewer). Bootstrap: `drain --agent auditor --triage`, then execute. These are completed-work packets from `mainA`–`mainD`, in priority order. For each, issue the verdict first, then evidence. Verdicts: `accept` / `accept-with-followups` / `needs-rework` / `blocked-evidence`.

## 1. mainD — compute-request schema kinds (delivery-plane contract) — HIGHEST

- Commit `5aae0c35` (workspace main, LOCAL). Files: `coordination/session-bus/session_bus.schema.json` (+ any BUS_PROTOCOL.md change). Source: `msg-20260813T175934Z-35-mainD`.
- **Question:** does adding `compute-request`/`compute-grant`/`compute-deny` to the `msg.kind` enum correctly satisfy rule 11, with fail-closed validation (no silent acceptance), and do the per-kind payload shapes match rule 11's mechanism (request: task/window/device_region/est_h/release_condition; grant: window boundaries; deny: reason + next step)? Confirm the relay validates them and tests cover authoring + relay.

## 2. mainB — A14 GateDecision-echo merge (orchestrator main)

- Cherry-pick `a7d7bdb6` onto orchestrator main → `c61b8184` (6 files, +299/-0), LOCAL. Source: `msg-20260813T175900Z-29-mainB`.
- **Question:** is the cherry-pick correct (right commit, clean application) and was the `merge_gate.py` AUTONOMOUS (non-gated) verdict the correct call?

## 3. mainA — ODL PaddleOCR parser comparison (measurement claim)

- Source: `msg-20260813T183838Z-77-mainA`. Claim: LiteParse beats ODL on every metric (TEDS 0.780 vs 0.483, NID 0.919 vs 0.912, …), done from existing evidence (ODL-013 fixture, 200-PDF corpus, upstream NID/TEDS/MHS evaluator).
- **Question:** is the comparison sound and decision-grade (correct fixture, same evaluator, no cherry-picked split), or should it carry the "evidence-only, not decision-gating" caveat?

## 4. mainB — ODL-013 three-way bench (measurement)

- Artifact `/mnt/raid0/llm/tmp/odl013-bench-20260813T1336Z/`. Source: `msg-20260813T175844Z-28-mainB`.
- **Question:** is the bench sound (0 failed/0 missing predictions per engine, upstream evaluator)? Verdict first.

## 5. Spot-checks (only if time permits)

- mainA paddleocr default-binary fix: research commit `81abdb1c` (`paddleocr_vl.py:29` build-hip → build-v9-hip, 52 tests pass). Source: `msg-20260813T180235Z-70-mainA`.
- mainC counter reconciliation: `index_state.py` Open column authoritative; `msg-20260813T181621Z-52-mainC`.

## Constraints

- lanes `[none]`; reviewer. Read-only on trust-boundary files; you never tick a checkbox, never sign.
- **Push policy (operator 2026-08-13): docs/handoffs pushes PERMITTED** — push your verdict/handoff/progress notes at wrap-up. Hold kernel/orchestrator code pushes.
- **Wrap-up at the audit boundary (REQUIRED):** run `agents/commands/wrap-up.md` on completing this pass — persist verdicts + evidence, flip `- [ ]`→`- [x]` checkboxes, commit, push handoff edits.
