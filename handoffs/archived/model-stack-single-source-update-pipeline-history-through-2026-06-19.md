# Model Stack Single-Source Update Pipeline - Completed Scope Through 2026-06-19

Historical ledger only; current work lives in `../active/model-stack-single-source-update-pipeline.md`.

## Scope

This file compactly preserves completed N11a/model-stack SSoT work that was pruned from the active handoff during the 2026-06-19 wrap-up. Full chronology and validation detail remain in `progress/2026-06/2026-06-19.md` and commit history.

## Completed Slices

| Area | Completed scope |
|------|-----------------|
| Stack truth contract | Generated model descriptors and `orchestration/derived/stack_priors.yaml` are the source contract for live role/model/serving facts. |
| Gates | Runtime attestation, q_scorer provenance checks, production launch gate, AutoPilot preflight gate, direct benchmark preflight, stack-manifest registry drift gate, and promotion-gate execution are live. |
| Guard inventory | Scanner-rule ownership is enforced through `orchestration/stack_change_surface_manifest.yaml`; current inventory is `consumer_surface_count=13`, `rule_count=27`, and the previous active-code warning baseline is clean. |
| Shared helper API | `src.registry.stack_priors` owns canonical helpers for live role records, serving URLs, endpoint/primary ports, slot limits, config URL projection, and canonical role/live-role lookup. |
| Config/admission | `src.config.models`, `src.config.__init__`, `ChatPipelineConfig`, `TimeoutsConfig`, and `src.api.admission` consume typed stack-prior projections while preserving env override precedence and explicit degraded fallbacks. |
| Health/status/OpenAI/preflight | CLI status, OpenAI `/v1/models` listing/order, AutoPilot preflight, API health probes, dashboard topology/status hints, stack status scanning, and stack runtime attestation derive live targets from stack priors or stack-manifest metadata. A 2026-06-19 read-only preflight audit found no remaining duplicate role/port table in `scripts/autopilot/preflight_audit.py`; the degraded fallback intentionally consumes stack-manifest HOT/WARM and launch-mode metadata. |
| Routing/action surfaces | Routing classifier load/save, role classifier, GraphRouter live action discovery, raw-label action-index lookup, dispatcher TaskIR roles/model hints, proactive delegation actors, REPL delegate targets, and generic alias normalization now resolve through canonical role truth. |
| Prompt/delegation surfaces | Architect investigation prompts, prompt resolver fallbacks, system-card generation, delegation role validation/reporting, chat template role lookup, fast revise, direct-answer prefixes, and planner program guidance were aligned with live stack truth. |
| Benchmark/eval consumers | Seeding default role order, reward priors, escalation chain detection, corpus quality gate fallback order, routing policy analysis, GraphRouter training fleet fallback, bilinear/factual-risk scorer role keys, and direct benchmark runtime checks were migrated or guarded. Seeding reward throughput now degrades through model descriptors before the legacy static table. |
| Swap-CI witnesses | Representative frontdoor, worker, vision, and long-context ingest swaps prove generated descriptors, stack priors, operator summary, system card, q_scorer priors, and selected consumers move together. Orchestrator `7a90924` extends the worker swap witness to seeding reward descriptor degraded fallback. |
| Runtime policy consumers | Inference lock/tap, current contention classes, worker concurrency caps, parallel burst-worker selection, KV compression production-port lookup, config-applicator physical ports, planner slot-query ports, host-health rewarm targets, and chunk-digest worker selection now derive from stack priors/manifest data or explicit degraded paths. |
| Documentation/examples | Operator docs, README/chapter examples, wiki pages, active handoff examples, local-inference notes, hardware/multimodal/quantization summaries, and generated system card wording were moved to canonical live role names while preserving historical notes where labeled. |
| X-MAS | The default-off X-MAS route hook now has complete-table/confidence/forced-role/failure-veto guards, and the measured 5x5 function-axis table was compiled into an enforce-eligible artifact. The 2026-06-18 held-out A/B returned `decision: hold` because hard replacement overrode learned incumbent routes; `epyc-orchestrator` `24baac4` added an incumbent-aware constrained policy. The next gate is a fresh quiet held-out A/B before any enforce flip. |
| PromptForge | Prompt path resolution now preserves fallback precedence while blocking path/symlink escapes. |
| Stack summary renderer | Registry+descriptor fallback rows are compiled before the old dict-only degraded path; broader renderer rewrite remains deferred unless a narrow helper seam appears. |

## Current Residuals

- Continue high-risk P2 consumer migrations from `orchestration/stack_change_surface_manifest.yaml` after focused GitNexus impact checks.
- Broaden W4 swap-CI only when new migrated consumers create useful witness surfaces.
- Keep X-MAS enforce default-off until the incumbent-aware policy passes a fresh quiet held-out A/B and a future operator/evidence gate.
- Keep broad renderer rewrites parked unless there is a specific, testable consumer seam.
