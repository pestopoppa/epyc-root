# Benchmark Results Dashboard

**Status**: active — proposed 2026-07-28, NOT started
**Created**: 2026-07-28
**Priority**: LOW — nice-to-have, operator-requested (2026-07-28). The archival-DB phase is explicitly *not* high priority.
**Owner**: unclaimed
**Parent index**: [master-handoff-index.md](master-handoff-index.md) (§B. ACTIVE)
**Related**: [loops-and-dashboards-audit-2026-07-05.md](loops-and-dashboards-audit-2026-07-05.md) (dashboard-hub infra) · the 2026-07-28 v8 keep/drop decision artifact (a hand-built precursor of the per-model view)

## Objective

A **read-only web dashboard to inspect inference-benchmarking results** for the models on the
system — hosted as a **sibling page on the existing stdlib handoff-dashboard hub (:8100)**, not new
infrastructure. The goal is to be able to see *what benchmark evidence exists per model*, even where
models were not all benchmarked on identical metrics. An archival database is a later, lower-priority
phase.

## Why (motivation)

Benchmark results are scattered across `epyc-inference-research/artifacts/<campaign>/<arm>/`
(`summary.json`, `results.json`, `per_question.jsonl`) with **no single inspection surface**. The
2026-07-28 v8 keep/drop decision (Laguna + the two 27B finetunes) was assembled *by hand* from those
dirs — a dashboard makes that browsable and repeatable, and lets us answer "what do we know about
model X?" without artifact archaeology.

## Context / key facts (read before starting)

- The handoff dashboard is a **stdlib hub on :8100** — supervisor `scripts/dashboard/hub_supervisor.sh`,
  code in `dashboard/` (`server.py`, `static/`, `handoff_parser.py`, `freshness.py`). A benchmark view
  is a **sibling page/route on the same server**; no new process, git-seeded like the handoff board.
- Benchmark artifact layout: `/mnt/raid0/llm/epyc-inference-research/artifacts/<campaign>/<arm>/`
  → `summary.json` (suite accuracy, n, throughput), `results.json` (per-cell / per-row), plus
  `quality_*/summary.json`. Campaigns are dated dirs (e.g. `np_context_study_v8_20260727`,
  `architect-bench-gpu-20260720`, `architect-laguna-iq2-v8-20260726`).
- **MEASUREMENT.md discipline is load-bearing**: every number is either observation-grade or
  decision-grade `(metric, protocol-id, n/reps, date, attestation)`. The dashboard must **display the
  grade + kernel/era on every number** and never let an observation read as a gate. Historical numbers
  era-label via `instrument_eras.yaml`.
- **Index by MODEL / quant, NEVER by role** (standing rule) — a model's benchmark identity is its
  weights + quant, not the role it was serving.
- "Models on the system" comes from the registries: research **master**
  `epyc-inference-research/orchestration/model_registry.yaml` (full record) + orchestrator **lean**
  `epyc-orchestrator/orchestration/model_registry.yaml` (active).

## Phase 1 — read-only inspector (the actual ask)

- [ ] Enumerate models on the system from the registries (master full-record + lean active).
- [ ] Ingest artifact surfaces (`summary.json` / `results.json`) into a **per-model** view: quality
      (suite / n / accuracy), throughput (np×L grid, RAG-at-depth), kernel + era, date.
- [ ] Filterable table + per-model drill-down, served as a sibling page on :8100.
- [ ] Tag every number with its **MEASUREMENT grade** (observation vs decision) and kernel/era, so the
      surface can't launder an observation into a gate.
- [ ] Handle sparse coverage gracefully (models with partial / no benchmarks show what exists, not an
      error) — the operator explicitly wants "at least what we have."

## Phase 2 — archival database (stretch, low priority)

- [ ] Persist ingested results into a queryable store (SQLite) for historical / cross-era queries.
- [ ] Backfill from existing artifacts.

## Non-goals

- **Not a benchmark runner** — inspection only; never launches inference (respects the no-concurrent-
  inference + codified-recipe rules).
- **Does not re-run or re-score** — reads existing artifacts as-is.
- **Does not gate decisions** — the MEASUREMENT trust boundary is human-only; the dashboard surfaces
  evidence, it does not certify it.

## Key file locations

- Hub: `scripts/dashboard/hub_supervisor.sh` · `dashboard/server.py` · `dashboard/static/`
- Artifacts: `/mnt/raid0/llm/epyc-inference-research/artifacts/`
- Registries: research `orchestration/model_registry.yaml` (master) · orchestrator lean equivalent
- Standing rules: `/workspace/MEASUREMENT.md` · `instrument_eras.yaml`
- Precedent per-model view: the 2026-07-28 v8 keep/drop decision artifact (Laguna + 27B finetunes)

## Reporting

Flip the Phase-1/Phase-2 checkboxes as they land; record the :8100 route added and any ingest schema
in `progress/`. Remove the master-index row on completion (rows are deleted on completion, not struck).
