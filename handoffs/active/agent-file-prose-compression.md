# Per-Model Agent-File Prose Compression

**Status**: compacted 2026-07-30 (wrap-up) — AFC-P6 restructure COMPLETE (22/22 items; audit
D1–D13 all addressed); compliance suite v2 landed (30/30/30, `agent_file_compliance_v2_20260730`);
operator DECIDED: n=30 expansion runs BEFORE any compressed-artifact rollout. The expansion
campaign is fully prepared and **HELD — inference is operator-gated**.
**Created**: 2026-04-30 (intake-509 follow-up) · **Priority**: HIGH
**Completed history**: [`../completed/agent-file-prose-compression-completed-through-2026-07-30.md`](../completed/agent-file-prose-compression-completed-through-2026-07-30.md)

## Executor Start Here (2026-07-30)

Exactly two things remain:

- [ ] **AFC-P5.E3 — run the n=30 compliance campaign.** READY but HELD (operator: "I will tell
  you when you can proceed" with inference). Launch:
  `region-lock run --cpu-list 0-95 -- bash /workspace/tests/compliance/agent_file/run_n30_campaign.sh`
  (queues behind any held bench claim; starts automatically on release). Shape: 4 current-stack
  models {worker_general gemma4-26B-Q4KM, frontdoor Qwen3.6-35B-Q8, ingest Qwen3-Next-80B-Q4KM,
  architect Qwen3.5-122B-UD-Q4KM} × 4 levels × 90 tasks, 8-way concurrent (est. ~2–4h wall),
  per-model fail-fast probe, sequential bench servers on :18099 (v8 binary 10107,
  teardown-verified), incremental JSON per (model,level) →
  `data/compliance/2026-07-30-n30-curve/`. Smoke probe passed 6/6. Notes: worker_fast retired
  (4-model roster); the earlier ingest "registry drift" claim was RETRACTED (depth-capped find);
  the parallel perf re-measurement does NOT gate this (within-instrument baseline,
  deterministic scoring at temp 0).
- [ ] **AFC-P5.E4 — re-take the rollout decision on the n=30 evidence.** Gate per model/level:
  `compliance ≥ 0.95 × level-none baseline`, `procedure ≥ 0.95 × baseline`, `recall ≥ 0.90`
  absolute; baseline recall < 0.90 ⇒ operating point `none`. Decision-fork table below. Factor
  in post-restructure savings (mild 1.6% / medium 20% / aggressive 39% of words) — the
  structural-deletion pass already captured most of the original win.

**Decision forks (for E4)**:

| n=30 result | Action |
|---|---|
| ≥95% baseline compliance at medium/aggressive for Tier-A models | Roll Phase 5 to `agents/shared/*.md` first; role overlays second PR |
| Only mild passes | Adopt mild as conservative default; no aggressive overlay artifacts |
| No level passes | Operating points → `none`; archive artifacts as research; close "abandoned by eval" |
| Failures concentrated in polarity/order | Patch the compression rider; rerun only the failed class |

## Objective (unchanged)

Compress agent-file prose at authoring time (project rider derived from /caveman), measure
per-model compression-tolerance curves, and use the per-model operating point as a deployment
gate — a model that can't follow its agent file at any level is flagged before production.

## Key Files

- Suite v2: `tests/compliance/agent_file/` (`runner.py` `SUITE_VERSION`, pools 30/30/30,
  `live_runner.py --concurrency`, `run_n30_campaign.sh` with SMOKE mode)
- Compressed artifacts (regenerated 2026-07-30, post-restructure source):
  `agents/shared/ENGINEERING_STANDARDS.compressed-{mild,medium,aggressive}.md`
- v1 curve + operating points (superseded instrument, historical evidence):
  `data/compliance/2026-05-07-*`; registry fields `agent_file_compression_operating_point`
- Audit + restructure record: `docs/reference/agent-config/agent-file-audit-2026-07-30.md`
  (defects D1–D13); incident narratives `docs/reference/agent-config/INCIDENT_LOG.md`

## Completed Scope

Everything before E3/E4 is DONE and ledgered in the completed sibling (link in header):
Phases 1–4 + pilot artifacts; v1 per-model curve + registry operating points; the 2026-07-29
lossless structural deletion pass (AFC-P5.0/P5.2); the 2026-07-30 full-stack audit + AFC-P6
restructure (P6.1–P6.22: staleness repair, dedup/extraction into SESSION_LIFECYCLE +
INCIDENT_LOG + docs/guides, enforcement hardening incl. post-edit reference guard + matrix
discovery, MEASUREMENT v2 ratification support, sub-repo fixes, thin overlays, retirements);
suite v2 instrument repair + expansion (AFC-P5.E1/E2); the operator decision (n=30 first,
✅ 2026-07-30).

## Reporting

- E3: per-(model,level) JSONs are the drain points; write the curve table into this handoff
  when complete; flip E3.
- E4: present the rollout decision as an operator decision package citing the n=30 curve; flip
  E4 and either execute the chosen fork or close per the fork table. Update
  `handoffs/active/research-evaluation-index.md` row on close.
