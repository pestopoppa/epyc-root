# 2026-11-07 — Research intake: harness/inference batch + session-bus id fix

**Session**: intake-harness-inference-20261106 · **Branch**: `wrapup/intake-20261107` · **Plan**: `research/intake-stage3-plan-2026-11-06-harness-inference.md`

## Ingested and dived

Three submitted sources — `pingdotgg/t3code`, `microsoft/foundry-local`, arXiv 2610.32813
(HarnessMM) — plus nine expansion entries, ingested as intake-2650…2661. All twelve were dived
across exactly four operator-authorised waves. 100 claim anchors recorded; every quote re-found
verbatim in its source and re-hashed after a second-reader pass removed several paraphrased or
spliced quotes before they shipped.

## Findings that changed the plan

- **Harness savings are over-attributed almost everywhere.** HarnessMM's headline reproduces but
  64–88% of the saving is per-call context shrink, not callback removal; output tokens rise.
  ActionEngine's 3.20× is a single-attempt mean against a hosted API, and its v1 reports 2×.
  HARBOR ties the manual peak inside a corrected ±5.9-pass interval with no grid/random control.
  CORTEX cuts rule evaluations 63–70% while median latency gets 0.14 ms slower. vCache's error
  budget is on the cache, not the skip (per-hit error ≈ δ/hit-rate, ~2.2% in its own table).
- **The soundness gap is interpreter identity.** `prepared_action.py` rechecks catalog and read-set
  fingerprints but not which handler will execute a stored call; the schema-epoch paper demonstrates
  descriptor-stable handler changes. Three fields plus a serving-identity digest close it.
- **t3code's transferable part is the contract**, not the product: budgeted handoff with
  omitted-item pointers, and a transfer record resolved lazily at first dispatch.
- **Foundry's AMDGPU path is buildable**: ORT-GenAI 0.19 exposes an AMDGPU/MIGraphX umbrella EP that
  Foundry enumerates but never ships or registers. Converted from a decline to a probe after
  operator steering.

## Filed (Stage 4, operator-approved after one revision)

17 tasks, 0 flips at filing time, across four owners: harness-program (UFH-TE-1…4, HIL-RE-1…4),
context-and-token-economy (CTX-HO-1, CTX-HO-3), coordination-and-churn-pipeline (CTX-HO-2,
BUS-ID-1…3), routing-program (RTG-EP-1, RTG-VAR-1/2). Five monitor triggers, eight explicit declines
(ten reviewed; two converted to work after the operator flagged the platform-mismatch pattern), two
knowledge rows.

## BUS-ID-1 landed (this wrap-up)

`cmd_append` used `setdefault`, honouring a caller-supplied id verbatim with no uniqueness check,
while every consumer dedupes by id (BUS_PROTOCOL rule 3) — a collision silently lost the second
message. Now refused at the author with a regression test
(`tests/test_session_bus.py::test_append_refuses_a_duplicate_caller_supplied_id`). `-k append`
suite: 8 passed. One unrelated pre-existing failure in the same file
(`test_audit_shadow_preserves_source_done_and_synthesizes_one_targeted_audit`) fails identically with
the change stashed.

## Gates

- `validate_intake.sh`: 0 errors (2657 entries); `--plan-file/--session-file`: 0.
- `index_state.py --check`: 0 problems.
- Anchor integrity: 100/100 verbatim + hash match against on-disk sources.
- Wiki: 12 dive files + digest visible to `compile_sources.py`; scoped compile/touch this wrap-up.
- Upstream repair: two kernel-champion fold tracks lost in the archive refactor were restored as
  compatibility pointers; 56 index cross-refs that failed validation now resolve.

## Follow-ups

- RTG-EP-1 (gfx90a EP probe) is the only filed task that spends hardware time.
- The other 16 are zero-inference; BUS-ID-2/3 and the HIL-RE rules are the cheapest next.
- Deferred, with named blocker: none.
