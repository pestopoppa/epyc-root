# X-MAS Heterogeneous Text-MAS Routing Spike

**Status**: classifier/table scaffold, guarded default-off enforce path, true function-axis 5x5 sweep, enforce-eligible `orchestration/xmas_winner_table.yaml`, default-off config wiring for that table, live A/B harness, machine-readable held-out verdict reporting, no-inference regression diagnostics, and incumbent-aware constrained enforce policy are all landed. The 2026-06-21 quiet constrained-policy A/B carried historical `xmas_policy=incumbent_constrained_v1` and still returned `decision.status=hold`; `epyc-orchestrator` `f517902d` repaired same-cheap-role cheap-first suppression and row-level `xmas_meta`, and `b108f865` now requires repaired-policy evidence as `incumbent_constrained_cheapfirst_v2`. Enforce remains OFF pending a future passing held-out decision for that repaired policy.
**Created**: 2026-05-19 (post-latent-MAS-cluster deep-dive)
**Categories**: agent_architecture, cost_aware_routing, benchmark_methodology, routing_intelligence
**Priority**: HIGH (empirical heterogeneous-routing artifact exists, but promotion is currently blocked by held-out regression evidence)
**Depends on**: `routing-intelligence.md`, `routing-and-optimization-index.md`, `meta-harness-optimization.md`, `hermes-outer-shell.md`
**History**: [x-mas-text-routing-history-through-2026-06-19.md](../archived/x-mas-text-routing-history-through-2026-06-19.md) preserves the completed scaffold/sweep/A-B chronology compacted out of this active handoff.
**Source deep-dive**: [`/workspace/research/deep-dives/2026-05-19-latent-mas-cluster.md`](../../research/deep-dives/2026-05-19-latent-mas-cluster.md)

## Objective

Replicate the X-MAS (intake-557, arxiv:2505.16997, `github.com/MASWorks/X-MAS`) domain x function optimal-model methodology on the EPYC production stack, build a domain/function winner table, and only route live traffic through it if held-out production evidence beats current routing without unacceptable latency or domain regressions.

## Current Evidence

- The deterministic 5-domain x 5-function classifier and winner-table loader are implemented in `epyc-orchestrator/src/classifiers/xmas_routing.py`.
- The production hook is default-off and guarded: enforce requires a complete evidence-backed table, confident classification, no forced role, and downstream guard pass/fail semantics still get final say.
- The true function-axis sweep completed in `epyc-inference-research` from 500 rows and produced the enforce-eligible `epyc-orchestrator/orchestration/xmas_winner_table.yaml`.
- `epyc-orchestrator` `21d96da2` wires that table into `orchestration/classifier_config.yaml` with `mode: off`, `winner_table_path: orchestration/xmas_winner_table.yaml`, and `require_complete_table: true`; this removes the missing-table production-readiness blocker without enabling live route mutation.
- The live A/B harness exists at `epyc-orchestrator/scripts/benchmark/xmas_live_ab.py` and now emits machine-readable `decision` and diagnostics summaries without rerunning inference.
- The 25-prompt held-out rerun (`benchmarks/results/runs/xmas_live_ab/20260618-215637-heldout-resilient-rerun`) returned `decision: hold`: overall score delta `-0.35`, latency ratio `16.18x`, no lift domain, and regressions in `code`, `math`, and `reasoning`.
- `epyc-orchestrator` `209ff62e` surfaces that latest held-out A/B verdict inside `scripts/autopilot/fable5_gate_report.py --strict`, so the aggregate Fable5 pickup check now explains the X-MAS blocker rather than only reporting `mode=off`.
- The refreshed replay diagnostics in `epyc-orchestrator` `96acc5e` identify the dominant mechanism: X-MAS overrode 23/25 prompts, mostly replacing baseline `coder_escalation` with slower `worker_general`; there were 7 baseline-only quality wins, 0 X-MAS-only wins, 20 prompts with at least `3x` latency regression, and 2 X-MAS timeouts.
- The constrained policy landed in `epyc-orchestrator` `24baac4`: enforce now treats the existing route as incumbent and only replaces it when the current cell evidence evaluates both roles and proves quality lift or material speed lift within a 1.10 latency cap. A no-inference replay diagnostic against the failed held-out bundle estimates that the policy would suppress 22/23 prior replacements (`incumbent_role_not_evaluated`) and allow only the one evidence-backed speed lift.
- `epyc-orchestrator` `7f20920` stamps new X-MAS A/B artifacts with `xmas_policy=incumbent_constrained_v1` and makes the aggregate Fable5 gate require that policy id before any held-out `promote_candidate` can count as enforce evidence. Existing 2026-06-18 summaries are therefore explicitly `unknown_legacy`, so the next required run is a fresh quiet-window constrained-policy A/B rather than a replay of old rows.
- `epyc-orchestrator` `91bdf6d` hardens the X-MAS real-run quiet-window preflight: `--host-quiet-confirmed` is still required, and the runner now refuses known competing evidence/benchmark coordinators including AutoPilot, DCP/BEP A/B, DS-E1 KV measurement, seeding, migration, placement, and generic benchmark runners before any orchestrator reload or chat call.
- The 2026-06-21 quiet constrained-policy A/B (`epyc-orchestrator/benchmarks/results/runs/xmas_live_ab/20260621T112005Z-constrained-policy`) wrote 100 rows and restored `xmas_routing.mode=off`. It carried `xmas_policy=incumbent_constrained_v1` / `required_xmas_policy=incumbent_constrained_v1`, but the verdict remained `hold`: score rate regressed from `0.60` baseline to `0.35` X-MAS (`score_delta_xmas_minus_baseline=-0.25`), while latency improved (`latency_ratio_xmas_over_baseline=0.714`). Regressions were `code`, `math`, and `reasoning`; blockers were `overall score delta -0.250 < required 0.050`, `no domain improved by >= 0.050`, and `domain regressions: code, math, reasoning`.
- `epyc-orchestrator` `f517902d` repairs the same-cheap-role failure mode by preserving try-cheap-first when X-MAS enforces the configured cheap role and adds row-level `xmas_meta` capture. `epyc-orchestrator` `b108f865` versions the repaired policy as `incumbent_constrained_cheapfirst_v2` and makes that policy id the new required evidence marker. The next real run must be a repaired-policy quiet-window A/B, not a replay of the historical v1 artifact.
- `epyc-inference-research` `7d05d03` adds this constrained-policy A/B to
  `docs/data/clean_window_measurement_manifest.json` and
  `docs/data/clean_window_measurement_commands.sh` as package `X-MAS`; the
  completed 2026-06-21 orchestrator run is the current evidence for that lane.

## Current Gate

- [ ] Keep `xmas_routing.mode=off` in production until a future held-out run passes the verdict gates; the validated winner table is configured default-off and must not be treated as an enforce flip.
- [ ] Run the repaired constrained-policy quiet-window A/B after deploying/reloading the current code/config. Any future real-run artifact must carry `xmas_policy=incumbent_constrained_cheapfirst_v2`, `required_xmas_policy=incumbent_constrained_cheapfirst_v2`, `required_xmas_policy_min_commit=b108f865`, row-level `xmas_meta`, and `decision.status=promote_candidate`.
- [ ] Do not spend effort on RMAS/LatentMAS/Dead Weights hidden-state paths until this text-mediated route has either a passing decision or a documented kill.

## Validation Commands

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run pytest -q tests/unit/test_xmas_live_ab.py tests/unit/test_validate_xmas_winner_table.py tests/classifiers/test_xmas_routing.py tests/unit/test_pipeline_routing.py
uv run python scripts/validate/validate_xmas_winner_table.py --table orchestration/xmas_winner_table.yaml --require-function-axis
python3 scripts/autopilot/fable5_gate_report.py --strict
uv run python scripts/benchmark/xmas_live_ab.py --prompts benchmarks/results/runs/xmas_live_ab/20260618-heldout-resilient/prompts.jsonl --reps 2 --host-quiet-confirmed --output benchmarks/results/runs/xmas_live_ab/$(date -u +%Y%m%dT%H%M%SZ)-constrained-policy
uv run python scripts/benchmark/xmas_live_ab.py --summarize-results benchmarks/results/runs/xmas_live_ab/20260618-215637-heldout-resilient-rerun/results.jsonl --output /tmp/xmas-replay-diagnostics
```

## Non-Goals

- Hidden-state or latent-agent handoff work.
- Cross-tokenizer projection or Dead Weights reproduction.
- Production enforce flips without a passing held-out decision.

## References

- Deep-dive: `/workspace/research/deep-dives/2026-05-19-latent-mas-cluster.md`
- X-MAS paper: `https://arxiv.org/abs/2505.16997`
- X-MAS repo: `https://github.com/MASWorks/X-MAS` (no license — methodology only)
- Related handoffs: `routing-intelligence.md`, `routing-and-optimization-index.md`, `learned-routing-controller.md`, `hermes-outer-shell.md`, `meta-harness-optimization.md`
