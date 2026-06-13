# Frontier F3 — The Data Flywheel: Train on What the Lab Already Generates

**Status**: W1 capture-hygiene current-lineage branch-ready except F2-W3 tuple evidence; W2 builder + reviewed-label capture branch-ready; W2 triage baseline still open (created from the Fable 5 strategic-frontiers review)
**Created**: 2026-06-12
**Priority**: MED — W1/W2 capture+curation now, W3 training HW-GATED with the MI210 portfolio per operator instruction
**Spec**: [fable5-findings-07-strategic-frontiers.md](fable5-findings-07-strategic-frontiers.md) §F3 — read it before claiming any waypoint
**Related**: [frontier-f2-self-running-lab.md](frontier-f2-self-running-lab.md) (W3 tuples are this frontier's gold data); [fable5-findings-01c-sequential-verdict-spec.md](fable5-findings-01c-sequential-verdict-spec.md) (outcome labels); [gpu-drafter-mi200-investigation.md](gpu-drafter-mi200-investigation.md) (drafter training); [retrain-routing-models.md](retrain-routing-models.md) (routing-classifier stack reuse)

## Why

Open-source + CPU-only created a no-training culture, yet the lab sits on
unique corpora it uses for nothing: `logs/planner_archive.jsonl` (every
planner/critic exchange with cost fields), 694 intake entries with verdicts,
the new per-question eval ledger, deep-dive→decision chains, and F2's job
tuples. A local planner alone would eliminate the cloud-dependency incident
class (out-of-credits halt, 300s timeouts, resumed-session contamination).
Capture and curation cost nothing now; training waits for the GPU.

## Waypoints

- [ ] **W1 — capture hygiene, NOW, zero cost** (1–2 days): patch `controller_io.py` so FAILED planner calls archive too (move `_append_planner_archive` before the early return — known gap); log intake-triage decisions as labeled `{source_features, verdict}` rows; confirm the per-question ledger (N2) journals per-trial outcome vectors; confirm F2-W3 tuple capture. Deliverable: `docs/reference/datasets.md` listing each corpus, schema, era-labeling rule, intended model — acceptance: page exists and every corpus has an era-labeling rule. **Current-lineage branch-ready evidence 2026-06-13**: `feat/intake-triage-label-capture` tip `87cfc81` is based on live F5 lineage `a7b87c1` and includes failed Claude planner-call archiving, `docs/reference/datasets.md`, and `scripts/datasets/record_intake_triage_verdict.py` for reviewed `reviewed_intake_triage_verdict.v1` JSONL rows; N2 per-question writer is branch-ready in `feat/paired-question-stats-current` `8dbdba5b`. Remaining W1 work: deploy/merge the current-lineage capture branch, collect real reviewed intake labels, and confirm F2-W3 tuple capture/deployment evidence.
- [ ] **W2 — dataset builders, pre-GPU** (3–4 days): `scripts/datasets/build_planner_sft.py` (planner_archive → (context, action) pairs labeled by measured outcome — keep confirmed/critic-approved, drop contaminated eras) + `build_triage_set.py` (intake index → classification set); train the CPU-feasible triage baseline now (BGE embedding + small MLP, routing-classifier stack reused) — acceptance: triage baseline ≥85% agreement with operator verdicts on a held-out 100. **Builder scaffolds current-lineage branch-ready 2026-06-13**: `feat/intake-triage-label-capture` tip `87cfc81` adds planner-SFT and intake-triage JSONL builders, reviewed-label joins via `--reviewed-labels`, training-grade filtering via `--require-reviewed-labels`, manifests, and direct CLI execution; live smokes emitted 694 intake rows from the current intake index and 1 reviewed-only row from a temporary reviewed label. Remaining W2: train/evaluate the CPU triage baseline and create held-out agreement evidence once at least 100 reviewed labels exist.
- [ ] **W3 — GPU fine-tunes (HW-GATED — do not start before the MI210 card)**: (a) planner-distill — QLoRA a Qwen3.5-9B-class base on W2's SFT set, acceptance: shadow-draft mode with ≥80% cloud-critic approval over 100 trials before any binding use; (b) drafters per the α measurement (FastDraft path, already gated in backlog); (c) judge/rubric model for EV-9 (unblocks rubric-scored suites in F1-W3) — acceptance: each fine-tune gets a MEASUREMENT.md protocol entry before its first reported number.

## Gates & pitfalls

- W3 is HW-GATED with the MI210 portfolio per operator instruction — no training work before the card lands.
- Era-label training corpora per MEASUREMENT.md §5 — never train on pre-scrub narrative text (gate-lock-era strategies etc.).
- Planner SFT must include *failure* cases or it learns only optimism.
- Deployment is always shadow-first behind the same reliability ladder as F2.

## Reporting

On completion of each waypoint: tick here, one-line progress entry, update master index row. W1/W2 can complete and be reported long before W3 ungates — do not hold the handoff open as "blocked" on the GPU; mark W3 gated explicitly.

## Progress

- 2026-06-13: W2 builder scaffolds branch-ready at `feat/data-flywheel-builders` tip `4a81d06`. Validation: `python3 -m py_compile scripts/datasets/_common.py scripts/datasets/build_planner_sft.py scripts/datasets/build_triage_set.py tests/unit/test_dataset_builders.py` passed; `uv run --with pytest --with pyyaml pytest -q tests/unit/test_dataset_builders.py` -> 3 passed, 1 pytest config warning; `uv run --with ruff ruff check scripts/datasets/_common.py scripts/datasets/build_planner_sft.py scripts/datasets/build_triage_set.py tests/unit/test_dataset_builders.py` passed; `git diff --cached --check` passed. Live-source smokes wrote planner and triage outputs/manifests under `/mnt/raid0/llm/tmp/f3-datasets-smoke-20260613`.
- 2026-06-13: Current-lineage F3 capture/build branch-ready at `feat/intake-triage-label-capture` tip `87cfc81` on top of F5 live lineage `a7b87c1`. It carries forward the failed planner-call archive fix and dataset builders, then adds reviewed intake-triage verdict capture plus reviewed-label joins. Validation: `python3 -m py_compile scripts/datasets/_common.py scripts/datasets/build_planner_sft.py scripts/datasets/build_triage_set.py scripts/datasets/record_intake_triage_verdict.py tests/unit/test_dataset_builders.py tests/unit/test_autopilot_controller_io.py` passed; `uv run --with pytest --with pyyaml pytest -q tests/unit/test_dataset_builders.py tests/unit/test_autopilot_controller_io.py` -> 40 passed, 1 pytest config warning; `uv run --with ruff ruff check ...` passed; `uv run --with ruff ruff format --check ...` passed; `git diff --check` passed. Live-source smokes wrote `/mnt/raid0/llm/tmp/f3-intake-label-smoke-20260613/intake_triage.jsonl` with 694 rows and `/mnt/raid0/llm/tmp/f3-intake-label-smoke-20260613/intake_triage_reviewed_only.jsonl` with 1 reviewed-only row; `rg "citation_context|IGNORE PRIOR|notes|source_text"` over emitted classifier outputs returned no hits.
