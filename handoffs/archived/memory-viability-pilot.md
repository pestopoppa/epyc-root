# Handoff: Adaptive Memory Viability Pilot

## Status

Implemented and runnable. Work paused by request after completing a reduced Stage 0 run.

## Goal

Test whether graph-derived episodic memory (from audit logs) can improve strategic task quality for small models, before investing in latency optimization.

## Scope Delivered

- Standalone runner independent from seeding pipeline.
- Fixed controls + adaptive variants.
- Graph/motif memory injection from `logs/audit_graph`.
- Deterministic scoring and machine-readable decision output.

## Files Added/Updated

- `scripts/experiments/memory_viability_runner.py`
- `scripts/experiments/memory_variant_registry.py`
- `scripts/experiments/memory_variant_generator.py`
- `scripts/experiments/memory_viability_report.py`
- `configs/memory_viability/arms.yaml`
- `configs/memory_viability/search_space.yaml`
- `docs/experiments/memory_viability.md`

## Run Artifacts (This Session)

### Final completed run

- Directory: `logs/memory_viability/20260210_155200`
- Command:
  ```bash
  python scripts/experiments/memory_viability_runner.py \
    --stage stage0 \
    --use-llm-generator \
    --force-role frontdoor \
    --timeout-s 10 \
    --sample-per-suite 2 \
    --suites coder \
    --adaptive-per-round 1
  ```
- Outcome:
  - `decision.md`: **stop**
  - best uplift: `0.00pp`
  - threshold: `+2.00pp`

### Partial/aborted runs (timeout/hang pressure)

- `logs/memory_viability/20260210_152811`
- `logs/memory_viability/20260210_152135`
- `logs/memory_viability/20260210_151957`
- `logs/memory_viability/20260210_151718`

## Operational Findings

1. `worker_fast` (`:8102`) health check failed during session; force role switched to `frontdoor`.
2. LLM generator proposals can timeout (`ReadTimeout`) and delay run start.
3. Very low timeout values speed failure detection but can flatten all-incorrect outcomes.

## Resume Instructions

1. Validate backend availability first:
   ```bash
   curl -sS http://localhost:8000/health | jq '.status, .backend_probes'
   curl -sS http://localhost:8102/health
   ```
2. Resume with larger coder-only Stage 0 sample:
   ```bash
   python scripts/experiments/memory_viability_runner.py \
     --stage stage0 \
     --use-llm-generator \
     --suites coder \
     --sample-per-suite 5 \
     --force-role frontdoor \
     --timeout-s 10
   ```
3. If stage0 uplift >= `+2pp`, run stage1:
   ```bash
   python scripts/experiments/memory_viability_runner.py \
     --stage stage1 \
     --use-llm-generator \
     --suites coder \
     --sample-per-suite 10 \
     --max-rounds 3 \
     --adaptive-per-round 4 \
     --seeds 7 17 29 \
     --force-role frontdoor \
     --timeout-s 10
   ```

## Decision Point for Next Session

Decide whether to prioritize:
- restoring `worker_fast` for truer 1.5B-targeted measurement, or
- continuing with `frontdoor` as a methodological rehearsal before moving back to 1.5B.
