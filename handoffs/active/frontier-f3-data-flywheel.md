# Frontier F3 — The Data Flywheel: Train on What the Lab Already Generates

**Status**: W1 capture-hygiene partially branch-ready; W1 inventory/labels + W2 still open (created from the Fable 5 strategic-frontiers review)
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

- [ ] **W1 — capture hygiene, NOW, zero cost** (1–2 days): patch `controller_io.py` so FAILED planner calls archive too (move `_append_planner_archive` before the early return — known gap); log intake-triage decisions as labeled `{source_features, verdict}` rows; confirm the per-question ledger (N2) journals per-trial outcome vectors; confirm F2-W3 tuple capture. Deliverable: `docs/reference/datasets.md` listing each corpus, schema, era-labeling rule, intended model — acceptance: page exists and every corpus has an era-labeling rule. **Partial branch-ready evidence**: failed Claude planner calls are archived in `feat/planner-session-hygiene` `69a41f7`; N2 per-question writer is branch-ready in `feat/paired-question-stats-current` `8dbdba5b`. Remaining W1 work: labeled intake-triage capture, F2-W3 tuple confirmation, and `docs/reference/datasets.md`.
- [ ] **W2 — dataset builders, pre-GPU** (3–4 days): `scripts/datasets/build_planner_sft.py` (planner_archive → (context, action) pairs labeled by measured outcome — keep confirmed/critic-approved, drop contaminated eras) + `build_triage_set.py` (intake index → classification set); train the CPU-feasible triage baseline now (BGE embedding + small MLP, routing-classifier stack reused) — acceptance: triage baseline ≥85% agreement with operator verdicts on a held-out 100.
- [ ] **W3 — GPU fine-tunes (HW-GATED — do not start before the MI210 card)**: (a) planner-distill — QLoRA a Qwen3.5-9B-class base on W2's SFT set, acceptance: shadow-draft mode with ≥80% cloud-critic approval over 100 trials before any binding use; (b) drafters per the α measurement (FastDraft path, already gated in backlog); (c) judge/rubric model for EV-9 (unblocks rubric-scored suites in F1-W3) — acceptance: each fine-tune gets a MEASUREMENT.md protocol entry before its first reported number.

## Gates & pitfalls

- W3 is HW-GATED with the MI210 portfolio per operator instruction — no training work before the card lands.
- Era-label training corpora per MEASUREMENT.md §5 — never train on pre-scrub narrative text (gate-lock-era strategies etc.).
- Planner SFT must include *failure* cases or it learns only optimism.
- Deployment is always shadow-first behind the same reliability ladder as F2.

## Reporting

On completion of each waypoint: tick here, one-line progress entry, update master index row. W1/W2 can complete and be reported long before W3 ungates — do not hold the handoff open as "blocked" on the GPU; mark W3 gated explicitly.
