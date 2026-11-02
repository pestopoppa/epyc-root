# UFH14 B4c/B4d A/B preparation (2026-11-01)

This reconstructs the lost B4bcd runbook as preparation only. It is not a run record, a production change, or evidence of an outcome. Prepare a defined A/B workload and coordinate the live serving window before enabling the flag.

## Common measurement contract

- Keep prefix-cache evidence separate by port and role. For B4c the handoff calls for `missed_prefill_share` / `hit_tok` on REPL roles; design §4.3 identifies `missed_prefill_share` as the later-step headline and `cold_large_share` as continuity context. Also record decode `predicted_per_second` and error rate as separately sourced regression guards.
- Use `/workspace/repos/epyc-orchestrator/scripts/analysis/prefix_cache_report.py` on `logs/serving_calls/serving_calls.jsonl` plus its rotated shards. The design's invocation is `python3 scripts/analysis/prefix_cache_report.py --split-at <ISO-UTC> [--port PORT] --json OUT`; this is a before/after split, not an A/B arm selector. For randomized/alternated arms, retain exact UTC boundaries and run/report the arms as separate windows (or use a split boundary only when it actually separates the intended windows). Report per-port and per-port/role rows from JSON.
- B4c compares the same A/B protocol as B4b: eval-tower quality and the B4 cache metrics for REPL roles (design names `hit_tok` on :8070). Freeze comparable traffic, model/server shape and scoring rubric; retain raw outputs and per-case quality judgments. Keep B4c separate from B4b and B4d so attribution is clear.
- Record actual call counts/windows and `fp_coverage`. Records without `prefix_fp` cannot support `missed_prefill_share`; missing serving records make cache metrics inconclusive. The report's per-port/per-role fields are exactly `hit_tok`, `cold_large_share`, `missed_prefill_share`, `prefill_s`, and related counts; decode rate and errors are separately sourced guards, not fields in this report. Require no quality regression before considering rollout.

## B4c — `prefix_stable_order`

### Feasibility

The source has a default-off `prefix_stable_order` feature consumed by `src/prompt_builders/builder.py` for `RootLMPrompt`; enabling it changes model input order. `/config` updates the current worker without reload and writes shared runtime overrides; `/config/attest` reports that worker's state. The current code does not give this flag a general six-hour default expiry, so specify an explicit short `ttl_s` for an enable and verify its expiry/source and enabled state. This flag only affects prompts rendered through that builder; report the eligible REPL/root-LM subset. This source inspection does not establish current deployed code or worker topology.

### Arm sequence

1. Save baseline configuration attestation and confirm `prefix_stable_order=false` on every serving API worker. Capture the comparison start UTC and serving-call log boundary. If workers cannot be individually attested, do not claim a fleet-wide arm.
2. Run the frozen eval-tower cases with the feature off; save per-case quality outputs and serving-call records.
3. Enable only `prefix_stable_order` with an explicit bounded expiry, verify all workers through `/config/attest`, and run the same cases and traffic schedule. The route writes a shared override, but the attestation endpoint reports the answering worker; check each worker explicitly.
4. Disable the flag, verify all workers report false, and preserve each arm's records and report JSON. If the enabled arm fails or expires, still explicitly set false and attest closure.

Manual local API examples (not executed here):

```bash
curl -fsS http://127.0.0.1:8000/config/attest
curl -fsS -X POST http://127.0.0.1:8000/config \
  -H 'Content-Type: application/json' \
  -d '{"prefix_stable_order":true,"ttl_s":3600}'
curl -fsS http://127.0.0.1:8000/config/attest
# After the arm (including failure/expiry), explicitly restore and attest:
curl -fsS -X POST http://127.0.0.1:8000/config \
  -H 'Content-Type: application/json' -d '{"prefix_stable_order":false,"ttl_s":3600}'
curl -fsS http://127.0.0.1:8000/config/attest
```

The route filters recognized flags from the POST body and writes a shared runtime override; send only the target flag plus its expiry. A `false` override has no expiry in current code, so explicit restore and attestation are necessary. The API accepts localhost requests only. These examples are preparation only; coordinate any live serving window with its owner.

## B4d — CoT prefix and worker RAG placement

### Feasibility

Not launch-ready: there is no `per_query_material_at_tail` flag in the current orchestrator feature registry, so a live arm cannot yet isolate this behavior. Code locations also differ from the old handoff anchors. Current CoT prefix concatenation sites include `src/graph/helpers.py` (think-harder) and `src/api/routes/chat.py` plus `src/api/routes/chat_pipeline/stream_adapter.py` (error escalation). `src/services/corpus_retrieval.py::format_for_rag` currently emits the reference-code block before `## Task`; the builder also uses `format_for_prompt` for worker context. The handoff says the RAG half is abandoned (`rag_enabled` ABANDONED); it does not authorize restoring it. Record the CoT and RAG results separately; do not claim coverage of an inactive RAG path, and identify exact live caller paths before evaluating it.

### Required implementation before an A/B

- Add a default-off `per_query_material_at_tail` feature spec and dataclass field; use it to gate all applicable CoT-prefix sites listed above. Preserve byte-identical behavior when off. These implementation items and the tests below are recommendations for making the proposed behavior reviewable, not existing handoff acceptance criteria.
- For any RAG arm, enumerate the live caller paths of both `format_for_rag` and `format_for_prompt`, define exactly which worker prompts change, and gate only those paths. Do not claim the RAG portion based on the currently abandoned path.
- Add focused tests for off-mode byte identity, on-mode exact placement, streaming and non-streaming escalation paths, and the eligible RAG path if re-enabled. Then use the B4c common measurement contract with a separate B4d arm and separate quality/serving report.
- Only after those changes land should the runtime-flag arm sequence be prepared. Rollback is explicit flag=false plus `/config/attest` across all workers; code rollback is not a substitute for restoring runtime state.

## Current evidence anchors

- Design/protocol: `docs/design/ufh14-b4-prefix-cache-policy-20261003.md`, especially §§4.2–4.3.
- B4 source state: `/workspace/repos/epyc-orchestrator/src/features.py`, `src/prompt_builders/builder.py`, `src/graph/helpers.py`, `src/api/routes/chat.py`, `src/api/routes/chat_pipeline/stream_adapter.py`, `src/services/corpus_retrieval.py`, and `src/api/routes/config.py`.
- Offline metric: `/workspace/repos/epyc-orchestrator/scripts/analysis/prefix_cache_report.py`.
- Historical runbook named by the handoff (`/mnt/raid0/llm/tmp/ufh14-b4-20261005/B4bcd-RUNBOOK.md`) is absent; this file replaces it as a preparation artifact.
