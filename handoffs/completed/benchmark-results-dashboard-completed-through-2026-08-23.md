# Benchmark Results Dashboard

**Status**: active — registry inventory landed 2026-07-29; artifact ingestion and UI remain open
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

- [x] Enumerate models on the system from the registries (master full-record + lean active). ✅ 2026-07-29 — `scripts/dashboard/build_benchmark_model_inventory.py` emits the read-only `data/benchmark_model_inventory.json` contract: 166 deduplicated model/quant records from 179 research roles and 15 orchestrator roles, retaining each source's role references. YAML parsing stays out of the stdlib-only :8100 hub.
- [x] Ingest artifact surfaces (`summary.json` / `results.json`) into a **per-model** view ✅ 2026-07-29: `scripts/dashboard/build_benchmark_artifact_inventory.py` builds an explicit-path-only JSON index; six registry models receive 154 saved artifacts while 1,341 unmatched artifacts remain visible rather than being role/arm-inferred. `GET /api/benchmark_artifacts` serves the offline-built contract.
      (suite / n / accuracy), throughput (np×L grid, RAG-at-depth), kernel + era, date.
- [x] Filterable table + per-model drill-down, served as a sibling page on :8100 ✅ 2026-07-29 — `/benchmarks` filters model/quant rows client-side and exposes each saved artifact path; its data comes exclusively from the offline path-keyed contract at `/api/benchmark_artifacts`.
- [x] Tag every number with its **MEASUREMENT grade** (observation vs decision) and kernel/era, so the
      surface can't launder an observation into a gate. ✅ 2026-07-29 — artifact drill-down displays its saved grade and kernel; era is explicitly `not inferred` unless a future read-only resolver can map it unambiguously from the human-owned registry. No dashboard value is promoted by display.
- [x] Handle sparse coverage gracefully (models with partial / no benchmarks show what exists, not an
      error) ✅ 2026-07-29 — the artifact builder emits all 158 registry records with model paths; 152 have an explicit empty artifact list and remain filterable in `/benchmarks`, while unmatched artifacts remain separately counted rather than guessed onto a model.

## Phase 2 — archival database (stretch, low priority)

- [x] Persist ingested results into a queryable store (SQLite) for historical / cross-era queries. ✅ 2026-07-29 — `scripts/dashboard/export_benchmark_artifact_sqlite.py` exports the read-only artifact contract to `data/benchmark_artifacts.sqlite`; bounded validation returns 154 rows. It stores reported kernel/grade/timestamp without inferring era or certifying evidence.
- [x] Backfill from existing artifacts. ✅ 2026-07-29 — recursive read-only scan covered current saved JSON under research `artifacts/`: 154 explicitly path-matched records loaded into both JSON/SQLite views, with 1,341 unmatched records retained for later provenance work rather than discarded or guessed.

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
