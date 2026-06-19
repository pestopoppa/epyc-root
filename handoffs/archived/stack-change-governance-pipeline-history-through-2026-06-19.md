# Stack Change Governance Pipeline - Completed Scope Through 2026-06-19

Historical ledger only; current work lives in `../active/stack-change-governance-pipeline.md`.

## Scope

This file compactly preserves completed stack-change governance work that was pruned from the active handoff during the 2026-06-19 wrap-up. Full chronology and validation detail remain in `progress/2026-06/2026-06-19.md`, the earlier `*-history-2026-06-15.md` files, and `epyc-orchestrator` commit history.

## Completed Slices

| Waypoint | Completed scope |
|----------|-----------------|
| W1 truth precedence | `docs/reference/stack-truth-precedence.md` defines stack-manifest/server-mode precedence over narrative registry fields, shared-runtime alias handling, retired-role handling, and generated-consumer source evidence. |
| W2 derived priors | `compile_stack_priors.py` produces the generated live stack-prior contract from registry/descriptors, including role/model/serving/TPS/quality/memory/acceleration/source evidence. |
| W3 validator foundation | Guard and pipeline checks cover descriptor/stack-prior freshness, stack-manifest registry drift, procedure role enums, structural stack-prior contract versions, runtime launch requirements, runtime flag witnesses, scanner-rule ownership, waiver metadata/expiry, surface summaries, and machine-readable rule inventory. |
| W3 evidence projection | Architect/REAP quality, GGUF context metadata, thinking-control evidence, shared-runtime alias provenance, VL projector requirements, effective launch context, exact launch port sets, and runtime binary/KV/flag witnesses are generated/guarded. |
| W4 consumer migrations | q_scorer, planner signatures, seeding/reward priors, bilinear/factual-risk scorer roles, GraphRouter, health/status/preflight, admission/config, prompt/delegation surfaces, runtime lock/tap/concurrency, KV compression/config-applicator, launcher helper parity, and dashboard/status consumers have representative stack-prior or manifest-backed paths. |
| W5 swap-CI | Simulated data-only fixtures cover shared-runtime swaps, retired-role removal, runtime requirement drift, generated operator/system-card/q_scorer changes, health/dashboard/routing/API/long-context/vision witnesses, and promotion-gate execution. |
| W6 launch hook | Production start, AutoPilot preflight, direct benchmark preflight, and promotion-gate command wiring fail closed unless generated contracts and runtime evidence are fresh, with explicit diagnostic bypasses only where documented. |
| Recurrence guards | Active-code retired-role/string surfaces are guarded; remaining legacy-test and historical-doc mentions are exact allowances or explicitly historical. |

## Current Residuals

- Keep the canonical command `uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate` green before launch, AutoPilot resume, or stack-sensitive benchmark interpretation.
- Continue high-risk consumer migrations through the owning N11/N11a handoffs.
- Keep waiver/exception entries intentional, owned, and expiring.
- Treat broad shared-helper changes with HIGH/CRITICAL GitNexus impact as main-thread work.
