# Continuation Prompt — AutoPilot Bootstrap + Routing A/B Test

**Date**: 2026-03-29
**Handoff from**: Claude Code sandbox session (35 tasks completed)
**Handoff to**: Agent with production Python environment

---

## Context

A massive implementation session just completed 35 tasks across the orchestration index. All code-only work is done. The remaining tasks need live inference on the production stack.

**Stack status**: 26 llama-servers running with correct models (verified). The orchestrator API (port 8000) needs to be started — all llama-server backends are healthy.

**What was built this session** (don't redo any of this):
- AutoPilot wiring: AP-1–8 (failure context, journal queries, Optuna epochs, etc.)
- Routing Phase 4: RI-0–6 (Q-scorer fix, cheap-first bypass, risk-aware escalation, veto modulation)
- Observability: DS-1–4 (queue depth, escalation rate, slot-save-path, stack state)
- Dynamic Stack: Phases B-D (pre-warm 1×96t + 4×48t, ConcurrencyAwareBackend, KV migration)
- Context Folding: Phase 0 (compaction trigger 0.60 → 0.75)
- Calibration dataset: RI-1 (2000 labeled examples in `orchestration/factual_risk_calibration.jsonl`)
- AutoPilot TUI: `scripts/autopilot/autopilot_tui.py` (--tui flag on autopilot.py)
- AR-2 smoke test: PASSED (dry-run 5 trials, all systems functional)

---

## Your Tasks (in order)

### 1. Start the orchestrator API

```bash
cd /mnt/raid0/llm/epyc-orchestrator
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Verify: `curl http://localhost:8000/health` should return `{"status": "ok"}`.

If it fails on missing deps, install them: `pip install httpx faiss-cpu numpy scikit-learn`.

### 2. AR-1: Establish debug suite baseline (579 questions)

This is the "before" number for autoresearch. CF Phase 0 (compaction trigger raised to 0.75) is deployed, so the baseline reflects the new compaction policy.

```bash
cd /mnt/raid0/llm/epyc-orchestrator
python scripts/benchmark/seed_specialist_routing.py \
    --debug --3way \
    --debug-batch-size 579 \
    --output benchmarks/results/orchestrator/ar1_baseline_$(date +%Y%m%d_%H%M%S).json
```

After completion:
1. Extract the pass rate: `correct / 579`
2. Write to `orchestration/autopilot_baseline.yaml`:
   ```yaml
   quality: <pass_rate as 0-3 scale>
   speed: <median t/s from results>
   cost: <normalized cost>
   reliability: <fraction non-error>
   per_suite_quality:
     simpleqa: <rate>
     gpqa: <rate>
     coder: <rate>
     # ... all suites
   frontdoor_speed: 12.7
   captured_at: "2026-03-29"
   notes: "Post CF-0 (trigger 0.75), pre-autoresearch baseline"
   ```
3. Mark `AR-1` done in `handoffs/active/routing-and-optimization-index.md`
4. Update `progress/2026-03/2026-03-29.md`

### 3. RI-7: A/B test Phase 4 routing enforcement

Two arms, 500+ questions each. Compare `factual_risk_mode=enforce` vs `off`:

**Arm A (control — risk mode off):**
```bash
ORCHESTRATOR_FACTUAL_RISK_MODE=off python scripts/benchmark/seed_specialist_routing.py \
    --3way --sample-size 500 \
    --suites simpleqa gpqa hotpotqa coder math thinking general \
    --output benchmarks/results/orchestrator/ri7_control_$(date +%Y%m%d).json
```

**Arm B (treatment — risk mode enforce):**
```bash
ORCHESTRATOR_FACTUAL_RISK_MODE=enforce python scripts/benchmark/seed_specialist_routing.py \
    --3way --sample-size 500 \
    --suites simpleqa gpqa hotpotqa coder math thinking general \
    --output benchmarks/results/orchestrator/ri7_enforce_$(date +%Y%m%d).json
```

After both complete, compare:
- SimpleQA F1 (primary factual metric)
- Overall pass rate
- Escalation rate (enforce should escalate more on high-risk)
- p95 latency
- Cost proxy

Statistical significance: p < 0.05 via paired bootstrap or McNemar's test on question-level pass/fail.

Mark `RI-7` done in the index with results summary.

### 4. AR-3: First live autoresearch run

Follow `scripts/autopilot/program.md` setup phase. Start with Tier 1 experiments (prompt optimization — hot-swap, fast iteration).

```bash
cd /mnt/raid0/llm/epyc-orchestrator
python scripts/autopilot/autopilot.py start \
    --tui \
    --max-trials 50 \
    --no-controller
```

The `--tui` flag gives you the live inference monitoring panel. The `--no-controller` flag uses autonomous species selection (no Claude CLI needed).

Monitor for:
- Hangs (inference stream stops for >60s)
- Safety gate violations (auto-rollback after 3 consecutive failures)
- Pareto frontier improvements (new "frontier" entries in journal)

After the run:
1. Check `orchestration/autopilot_journal.jsonl` for trial outcomes
2. Run `python scripts/autopilot/autopilot.py report` for summary
3. Run `python scripts/autopilot/autopilot.py plot` for visualizations
4. If any trial achieved pareto="frontier", that's a success
5. Mark `AR-3` done in the index

### 5. Update documentation

After all tasks complete:
1. Update `handoffs/active/routing-and-optimization-index.md` — mark checkboxes
2. Update `progress/2026-03/2026-03-29.md` — add results sections
3. Update `logs/agent_audit.log` — log task outcomes
4. Commit all changes to both `epyc-orchestrator` and `epyc-root`

---

## Key File Locations

| What | Where |
|------|-------|
| Routing index (task list) | `epyc-root/handoffs/active/routing-and-optimization-index.md` |
| AutoPilot handoff | `epyc-root/handoffs/active/autopilot-continuous-optimization.md` |
| Program strategy | `epyc-orchestrator/scripts/autopilot/program.md` |
| Baseline output | `epyc-orchestrator/orchestration/autopilot_baseline.yaml` |
| Calibration dataset | `epyc-orchestrator/orchestration/factual_risk_calibration.jsonl` |
| Seeding script | `epyc-orchestrator/scripts/benchmark/seed_specialist_routing.py` |
| AutoPilot script | `epyc-orchestrator/scripts/autopilot/autopilot.py` |
| TUI monitor | `epyc-orchestrator/scripts/autopilot/autopilot_tui.py` |
| Progress report | `epyc-root/progress/2026-03/2026-03-29.md` |
| Audit log | `epyc-root/logs/agent_audit.log` |
| Stack launcher | `epyc-orchestrator/scripts/server/orchestrator_stack.py` |

## Important Notes

- **Do NOT relaunch the llama-servers** — they're already running (26 processes). Only the orchestrator API (uvicorn) needs starting.
- **matplotlib** may not be installed — `autopilot.py plot` will fail without it. Install with `pip install matplotlib` if needed.
- The **calibration dataset** (RI-1) is already built. Don't rebuild it.
- The **AR-2 smoke test** already passed. Don't rerun it.
- All code changes from this session are committed. Check `git log --oneline -15` in both repos to see recent work.
- The stack uses **pre-warm config**: frontdoor/coder/worker each have 1×96t + 4×48t instances. The `ConcurrencyAwareBackend` handles routing automatically.
