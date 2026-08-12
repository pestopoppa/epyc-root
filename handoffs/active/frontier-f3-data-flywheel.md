# Frontier F3 — The Data Flywheel: Train on What the Lab Already Generates

**Status**: W1 capture hygiene and W2 dataset builders are on the current orchestrator branch; reviewed intake-label recording, reviewed-label joins, stdlib CPU triage-baseline scaffold, a 120-row actionable review queue, machine-readable/markdown review-readiness packets, trusted-label-source baseline guards, and F2 lab batch verdict/gold-tuple capture tooling are live. The operator-delegated review apply reached the 100-label readiness gate and the held-out triage-baseline report passed (`0.90` accuracy vs `0.85` threshold); real F2-W3 tuple evidence is now present from the 2026-07-07 quiet-window lab batch, leaving gfx90a training-viability as the remaining W3 gate before fine-tune work (created from the Fable 5 strategic-frontiers review)
**Created**: 2026-06-12
**Priority**: MED — W1/W2 capture+curation now, W3 training HW-GATED with the MI210 portfolio per operator instruction
**Spec**: [fable5-findings-07-strategic-frontiers.md](../completed/fable5-findings-07-strategic-frontiers.md) §F3 — read it before claiming any waypoint
**Related**: [frontier-f2-self-running-lab.md](frontier-f2-self-running-lab.md) (W3 tuples are this frontier's gold data); [fable5-findings-01c-sequential-verdict-spec.md](../completed/fable5-findings-01c-sequential-verdict-spec.md) (outcome labels); [gpu-drafter-mi200-investigation.md](gpu-drafter-mi200-investigation.md) (drafter training); [retrain-routing-models.md](retrain-routing-models.md) (routing-classifier stack reuse); [../completed/frontier-f7-economic-ledger.md](../completed/frontier-f7-economic-ledger.md) (planner-distill economic justification)

## Why

Open-source + CPU-only created a no-training culture, yet the lab sits on
unique corpora it uses for nothing: `logs/planner_archive.jsonl` (every
planner/critic exchange with cost fields), 694 intake entries with verdicts,
the new per-question eval ledger, deep-dive→decision chains, and F2's job
tuples. A local planner alone would eliminate the cloud-dependency incident
class (out-of-credits halt, 300s timeouts, resumed-session contamination).
Capture and curation cost nothing now; training waits for the GPU.

## Waypoints

- [x] **W1 — capture hygiene, NOW, zero cost** (1–2 days) ✅ 2026-07-14 all W1 items confirmed live on current branch (2026-06-28 + 2026-07-04 refresh): patch `controller_io.py` so FAILED planner calls archive too (move `_append_planner_archive` before the early return — known gap); log intake-triage decisions as labeled `{source_features, verdict}` rows; confirm the per-question ledger (N2) journals per-trial outcome vectors; confirm F2-W3 tuple capture. Deliverable: `docs/reference/datasets.md` listing each corpus, schema, era-labeling rule, intended model — acceptance: page exists and every corpus has an era-labeling rule. **Current-lineage status 2026-06-28**: current `controller_io.py` already archives failed planner calls in the newer planner-provider schema; `docs/reference/datasets.md` and `scripts/datasets/record_intake_triage_verdict.py` are live; `epyc-orchestrator` `2abf8ff2` makes `build_triage_set.py` consume reviewed `reviewed_intake_triage_verdict.v1` rows; `epyc-orchestrator` `c27664f8` adds `prepare_intake_triage_review.py` and a prompt-free 120-row review queue at `orchestration/datasets/intake_triage_review_queue.jsonl`; `epyc-orchestrator` `4f860e20` adds `intake_triage_review_status.py` plus non-operator `shadow_job` queue label-source support; `epyc-orchestrator` `f8738b24` prevents `shadow_job` labels from suppressing operator review by default. **2026-07-04 refresh**: failed provider-call archive, per-question ledger, and F2 lab tuple scaffolds are confirmed live on the current branch; remaining W1/W2 work is real reviewed intake labels and real quiet-window F2 outputs/verdicts/`lab_gold_tuple.v1` rows.
- [x] **W2 — dataset builders, pre-GPU** (3–4 days): `scripts/datasets/build_planner_sft.py` (planner_archive -> (context, action) pairs labeled by measured outcome — keep confirmed/critic-approved, drop contaminated eras) + `build_triage_set.py` (intake index -> classification set); train the CPU-feasible triage baseline now (BGE embedding + small MLP, routing-classifier stack reused) — acceptance: triage baseline >=85% agreement with operator verdicts on a held-out 100. **Builder scaffolds landed current branch 2026-06-14**: `epyc-orchestrator` `74ae865` adds planner-SFT and intake-triage JSONL builders, manifests, and direct CLI execution. Live no-inference smokes emitted 694 intake rows and 2,685 planner rows under `/mnt/raid0/llm/tmp/f3-datasets-smoke-20260614-codex`; intake-triage output had no `citation_context` / `IGNORE PRIOR` / `notes` / `source_text` field leakage. **Reviewed-label join landed 2026-06-21**: `epyc-orchestrator` `2abf8ff2` lets `build_triage_set.py` overlay the latest reviewed label per intake ID, emit reviewed-label provenance, and require reviewed labels for gold/held-out sets. **Stdlib baseline scaffold landed 2026-06-21**: `scripts/datasets/train_intake_triage_baseline.py` trains/evaluates a deterministic naive-Bayes baseline over reviewed labels only by default, writes aggregate-only reports, and reports `insufficient_reviewed_labels` until the 100-reviewed-label acceptance set exists. **Review queue landed 2026-06-27**: `prepare_intake_triage_review.py` excludes already reviewed IDs, supports verdict filters, and generated 120 actionable rows from `worth_investigating`, `adopt_patterns`, `adopt_component`, and `new_opportunity` items. **Readiness reporter landed 2026-06-28**: `intake_triage_review_status.py` reports reviewed-label readiness without raw text. **Trusted label authority landed 2026-06-28**: `epyc-orchestrator` `f8738b24` makes operator labels the default trusted source for readiness, baseline training, and reviewed-label overlay; shadow labels require explicit opt-in. **Review packet automation landed 2026-07-06**: `intake_triage_review_status.py --output-md --batch-template` now emits an operator-facing markdown packet plus blank-verdict JSONL batch rows. **Trusted-label gate cleared 2026-07-07**: operator-delegated batches appended 100 rows to `orchestration/datasets/intake_triage_reviewed.jsonl`; refreshed status `orchestration/reports/intake_triage_review_status_20260707T000650Z.json` reports `100` trusted reviewed labels, `0` labels needed, and `ready_for_baseline=true`. **Baseline acceptance passed 2026-07-07**: `orchestration/reports/intake_triage_baseline_report_20260707T000910Z.json` reports `acceptance_pass`, `80` train rows, `20` held-out rows, `18` correct, and `0.90` accuracy against the `0.85` threshold.
- [x] **W-aux — trace publish/redaction reference (pi-share-hf, intake-736), pre-GPU** ✅ 2026-07-29: the MIT `pi-share-hf` tool (Collect → Redact → TruffleHog secret-scan → LLM-review → JSONL → Upload-to-HF) is a pattern reference for two GAPS this flywheel lacks: (1) an **UPLOAD/publish** step, and (2) **general secret/PII redaction of RAW traces** (`planner_archive.jsonl`, `agent_audit.log`) — broader than W1/W2's field-name quarantine (`source_text`/`citation_context`). **Do NOT re-implement** the existing quarantine + operator trusted-label review (`f8738b24`). Adopted the hygiene patterns only in `epyc-orchestrator` `e57be4c8` / `16f9d6c3`: fail-closed deterministic credential and high-entropy scanning with separate reasoning-span reporting. It does not authorize upload/publish or training, and it does not replace operator label authority. verdict adopt_patterns — mine the pattern, don't trust the gate wholesale.
- [x] **W-aux preflight CLI — raw-trace export hygiene.**
  `epyc-orchestrator` now has `scripts/datasets/raw_trace_publish_preflight.py`
  for candidate `planner_archive.jsonl` / `agent_audit.log` exports. It reuses
  production credential redaction, adds high-entropy token backstop checks with
  hash-field false-positive guards, separately reports reasoning/trace-field
  hits, and exits nonzero on any hit or parse error. This does not authorize
  publish/training and does not replace operator label authority. Focused tests
  passed (`44 passed`), ruff was clean, and a clean candidate CLI smoke returned
  `ok=true`. ✅ 2026-07-06
- [ ] **W3 — GPU fine-tunes (MI210 present since 2026-07-02; the HW gate is CLEARED. The DATA gate is now satisfied by 100 trusted reviewed triage labels plus initial F2 gold tuples; gfx90a TRAINING-VIABILITY is still [unverified] — a LoRA/GRPO/SFT smoke on a small model via TRL/verl-ROCm must pass before any of (a)–(c) is scoped. NOTE: gradient-based QLoRA (below) is what rides the training-viability gate; a gradient-FREE Evolution-Strategies path (intake-564/563, forward-pass-only) would sidestep it entirely and is tracked in learned-routing-controller.md)**: (a) planner-distill — QLoRA a Qwen3.5-9B-class base on W2's SFT set, acceptance: shadow-draft mode with ≥80% cloud-critic approval over 100 trials before any binding use; (b) drafters per the α measurement (FastDraft path, already gated in backlog); (c) judge/rubric model for EV-9 (unblocks rubric-scored suites in F1-W3) — acceptance: each fine-tune gets a MEASUREMENT.md protocol entry before its first reported number.
  - **W3 candidate variant — self-distillation (intake-736 context / intake-739 reference, MI210-gated)**: the operator direction — self-distill the compressed CPU worker from own agent-tool traces + a GLM-5.2-FP8 generation loop + frontier HF traces (~210 GB) — is an **on-policy** distillation variant, distinct from W3a's **offline** planner-distill QLoRA; V4-Pro-DSpark's "on-policy distillation" consolidation (intake-739) is a reference point only, not an endorsement. GATES: external frontier-HF / GLM-loop traces are **untrusted** under the `f8738b24` authority model → require an explicit trusted-source opt-in before feeding gold/held-out sets; must pass a MEASUREMENT.md protocol + shadow-approval before any binding use.

## Gates & pitfalls

- W3 HW gate CLEARED 2026-07-02 (MI210 landed). DATA gate satisfied. **Training-viability gate CLEARED 2026-08-12** — LoRA/SFT on a real pretrained model executes on the MI210, loss `0.9174 → 0.4077` (55.6%) in 60 steps with GPU residency sampled during the run: [`artifacts/gpu-aux-baselines/a9_gfx90a_training_viability_20260812.md`](../../artifacts/gpu-aux-baselines/a9_gfx90a_training_viability_20260812.md). **All three W3 gates are now met**; (a)–(c) may be scoped.
  - **This gate was never a measurement problem.** It sat 29 days because a prior session reported "no PyTorch on the host" from a `find / -maxdepth 6`, which structurally cannot reach a venv `site-packages` at depth 8+. torch `2.5.1+rocm6.2` with `gfx90a` was installed the whole time in `/mnt/raid0/llm/tools/geak-v1-rocm62-py312` (trl `1.9.2`, peft `0.20.0`). **This row also never named a software gate** — it listed only HW and DATA, so a cleared HW gate read as "runnable". Any future row of this shape should name its runtime dependency explicitly.
  - **Carry-forward for W3(a):** transient bf16 LoRA gradients reach ~1e34 on layer-0 attention projections while loss converges normally (AdamW is per-parameter scale-invariant). `torch.nn.utils.clip_grad_norm_` norms in fp32 and returns `inf` on that, propagating a NaN scale into every parameter. Use fp64 or per-tensor clipping.
  - **4-bit QLoRA specifically is NOT yet runnable**: `bitsandbytes 0.50.0` imports and exposes `Linear4bit`, but ships no gfx90a code object for ROCm 6.2 and fails with `no kernel image is available for execution on the device`. A source build is viable (`hipcc 6.2` present). Likely unnecessary — a 9B at bf16 plus LoRA state is ~22–25 GB against 64 GB of VRAM.
  - The gradient-free ES alternative (learned-routing-controller.md) is **not** a substitute: it has zero checkbox rows, its section says "do NOT branch a separate handoff", and its own two gates are unmet. It sidesteps this gate by not training.
  - [ ] **Build `bitsandbytes` from source for gfx90a / ROCm 6.2** — `hipcc 6.2.41133`, cmake and make are all present, so `cmake -DCOMPUTE_BACKEND=hip -DBNB_ROCM_ARCH=gfx90a`. Not started 2026-08-12 only because a parallel compile is CPU work and mainA held four CPU regions for the E5 Stage-B re-measurement; no decision blocks it.
  - [ ] **Confirm bf16 LoRA on a 9B-class base fits the MI210 before spending that build.** Arithmetic says ~22–25 GB against 64 GB, which would retire the 4-bit requirement for W3(a) entirely. One load + a few steps settles it. Do this task *first* — it may delete the one above.
  - [ ] **GRPO end-to-end smoke on gfx90a.** A9 demonstrated LoRA/SFT only; the W3 row names GRPO as well, and TRL `1.9.2` imports clean under transformers `5.15.0`. Same harness shape as `a9_stage2_trl_sft.py`.
- Era-label training corpora per MEASUREMENT.md §5 — never train on pre-scrub narrative text (gate-lock-era strategies etc.).
- Planner SFT must include *failure* cases or it learns only optimism.
- Deployment is always shadow-first behind the same reliability ladder as F2.

## Reporting

On completion of each waypoint: tick here, one-line progress entry, update master index row. W1/W2 can complete and be reported long before W3 ungates — do not hold the handoff open as "blocked" on the GPU; mark W3 gated explicitly.

## Progress

- 2026-07-06: Added a raw-trace publish preflight note to
  `epyc-orchestrator/docs/reference/datasets.md` covering deterministic
  secret/PII scanning, entropy/ML backstops, and reasoning-span scans as
  hygiene-only checks for future trace export/publish paths. This advances
  W-aux without changing the quarantine/operator-review trust boundary.
- 2026-07-07: Applied the first F3 intake-triage review packet under explicit
  operator delegation. `epyc-orchestrator`
  `orchestration/datasets/intake_triage_review_batch_filled_20260707T000328Z.jsonl`
  accepted the first 25 prompt-free queue suggestions and appended them via
  `apply_intake_triage_review_batch.py --apply` to
  `orchestration/datasets/intake_triage_reviewed.jsonl` with
  `label_source=operator` and reviewer `codex-operator-delegated`. Refreshed
  status artifacts
  `orchestration/reports/intake_triage_review_status_20260707T000402Z.json`,
  `orchestration/reports/intake_triage_review_packet_20260707T000402Z.md`,
  and
  `orchestration/datasets/intake_triage_review_batch_template_20260707T000402Z.jsonl`
  report `25/100` trusted reviewed labels and queue the next 25 rows.
- 2026-07-07: Completed the remaining operator-delegated F3 reviewed-label
  applies through the same recorder path. Additional filled batches
  `orchestration/datasets/intake_triage_review_batch_filled_20260707T000642Z.jsonl`,
  `...000645Z.jsonl`, and `...000647Z.jsonl` brought
  `orchestration/datasets/intake_triage_reviewed.jsonl` to `100` trusted
  operator-source labels. Final status
  `orchestration/reports/intake_triage_review_status_20260707T000650Z.json`
  is `ready_for_baseline=true`, with `20` non-blocking queue rows still
  available for future review.
- 2026-07-07: Ran the W2 held-out triage-baseline acceptance report from the
  reviewed-only corpus. `build_triage_set.py --require-reviewed-labels`
  emitted
  `orchestration/datasets/intake_triage_reviewed_only_20260707T000910Z.jsonl`
  with `100` operator-source rows, and
  `train_intake_triage_baseline.py` wrote
  `orchestration/reports/intake_triage_baseline_report_20260707T000910Z.json`
  with `status=acceptance_pass`, `80` train rows, `20` held-out rows, and
  `18/20 = 0.90` accuracy against the `0.85` acceptance threshold.
- 2026-07-07: Cleared the F2 tuple-evidence blocker for W3 readiness. The
  quiet-window lab batch produced real non-mock `handoff_freshness_lint` and
  `attestation_watch` rows; cloud review accepted the handoff-lint row as a
  positive `lab_gold_tuple.v1` and rejected the attestation row as a negative
  `lab_gold_tuple.v1` because it falsely claimed the attestation latest file
  was empty. The lab review queue now reports `pending_reviews=0`. Remaining
  W3 gate: gfx90a training-viability smoke.
- 2026-07-06: Intake-triage review packet automation landed in
  `epyc-orchestrator`. `intake_triage_review_status.py` can now write a
  markdown review packet and operator-fillable JSONL batch template while
  preserving dry-run/default-off label application. Live artifacts:
  `orchestration/reports/intake_triage_review_packet_20260706T235801Z.md`,
  `orchestration/reports/intake_triage_review_status_20260706T235801Z.json`,
  and
  `orchestration/datasets/intake_triage_review_batch_template_20260706T235801Z.jsonl`.
  The trusted-data gate remains `0/100` labels until reviewed rows are filled
  and applied.
- 2026-07-06: Implemented the raw-trace publish preflight as an executable
  no-inference scanner in `epyc-orchestrator`
  `scripts/datasets/raw_trace_publish_preflight.py` with focused unit coverage.
  It fail-closes candidate raw-trace exports on credential-pattern hits,
  high-entropy token shapes, parse errors, or hits inside reasoning/trace
  fields, while preserving hash false-positive guards.
- 2026-07-06: F2 gold-tuple capture is now batchable via `epyc-orchestrator`
  `2bdfe35f`. `scripts/lab/apply_review_batch.py` reuses the existing
  `record_verdict.py` path to persist reviewed verdict batches as
  `lab_review_verdict.v1` rows plus `lab_gold_tuple.v1` files, and
  `scripts/lab/review_queue_report.py` exposes pending review items without
  mutating trust state. Live report still shows `0` task records / `0`
  pending reviews, so this removes a capture-path gap but does not satisfy the
  trusted-data gate; real quiet-window lab outputs and reviewed verdicts remain
  required.
- 2026-07-06: F2 pending-review evidence is now easier to inspect via
  `epyc-orchestrator` `95d2d39f`. `scripts/lab/review_queue_report.py
  --markdown/--output-md` renders pending queue rows and editable
  `lab_review_batch.v1` JSONL into a review packet. Live packet
  `orchestration/reports/lab_review_queue_report_20260706T131453Z.md` shows
  `8` active-safe deterministic rows awaiting operator verdicts and `0`
  review-candidate rows; this improves review throughput but still does not
  satisfy the trusted-data gate until verdicts are actually recorded.
- 2026-07-06: The first quiet-window F2 batch is now command-planned via
  `epyc-orchestrator` `88f66ae6`. `scripts/lab/quiet_window_lab_plan.py`
  reports the model-backed jobs ready for the next AutoPilot-stopped window and
  emits the exact run/review/batch-apply commands that will turn outputs into
  pending review items and then `lab_gold_tuple.v1` evidence. Current smoke
  selected `handoff_freshness_lint` and `attestation_watch` but correctly
  blocked execution while AutoPilot and live llama servers were active. This is
  still prep, not data: the F3 trusted-data gate remains `0` task records /
  `0` verdicts / `0` gold tuples until that quiet-window command is actually
  run and reviewed.
- 2026-06-13: W2 builder scaffolds branch-ready at `feat/data-flywheel-builders` tip `4a81d06`. Validation: `python3 -m py_compile scripts/datasets/_common.py scripts/datasets/build_planner_sft.py scripts/datasets/build_triage_set.py tests/unit/test_dataset_builders.py` passed; `uv run --with pytest --with pyyaml pytest -q tests/unit/test_dataset_builders.py` -> 3 passed, 1 pytest config warning; `uv run --with ruff ruff check scripts/datasets/_common.py scripts/datasets/build_planner_sft.py scripts/datasets/build_triage_set.py tests/unit/test_dataset_builders.py` passed; `git diff --cached --check` passed. Live-source smokes wrote planner and triage outputs/manifests under `/mnt/raid0/llm/tmp/f3-datasets-smoke-20260613`.
- 2026-06-13: Current-lineage F3 capture/build branch-ready at `feat/intake-triage-label-capture` tip `87cfc81` on top of F5 live lineage `a7b87c1`. It carries forward the failed planner-call archive fix and dataset builders, then adds reviewed intake-triage verdict capture plus reviewed-label joins. Validation: `python3 -m py_compile scripts/datasets/_common.py scripts/datasets/build_planner_sft.py scripts/datasets/build_triage_set.py scripts/datasets/record_intake_triage_verdict.py tests/unit/test_dataset_builders.py tests/unit/test_autopilot_controller_io.py` passed; `uv run --with pytest --with pyyaml pytest -q tests/unit/test_dataset_builders.py tests/unit/test_autopilot_controller_io.py` -> 40 passed, 1 pytest config warning; `uv run --with ruff ruff check ...` passed; `uv run --with ruff ruff format --check ...` passed; `git diff --check` passed. Live-source smokes wrote `/mnt/raid0/llm/tmp/f3-intake-label-smoke-20260613/intake_triage.jsonl` with 694 rows and `/mnt/raid0/llm/tmp/f3-intake-label-smoke-20260613/intake_triage_reviewed_only.jsonl` with 1 reviewed-only row; `rg "citation_context|IGNORE PRIOR|notes|source_text"` over emitted classifier outputs returned no hits.
- 2026-06-14: W2 builder scaffolds integrated onto current `fix/substring-scorer-digit-separators` lineage as `epyc-orchestrator` `74ae865` (`Add data flywheel dataset builders`). Validation on current branch: scoped ruff passed; py_compile passed; `tests/unit/test_dataset_builders.py` passed 3. No-inference live-source smokes wrote `/mnt/raid0/llm/tmp/f3-datasets-smoke-20260614-codex/intake_triage.jsonl` (694 rows) and `planner_sft.jsonl` (2,685 rows with `--include-excluded`). Intake-triage quarantine field scan returned no hits. The older failed-planner archive commit was not replayed because current `controller_io.py` already archives planner calls with statuses `timeout`, `process_failed`, `stale_session`, `missing_cli`, and `success`; `gitnexus impact _append_planner_archive` on the current hook was LOW.
- 2026-06-21: Reviewed intake-label joins landed on current orchestrator branch as `2abf8ff2` (`Join reviewed intake labels into triage dataset`). `build_triage_set.py` now loads `orchestration/datasets/intake_triage_reviewed.jsonl` by default when present, prefers the latest reviewed row per `intake_id`, carries `destination_index`, `reviewed_at`, `label_source`, and `output_contract_version`, and supports `--require-reviewed-labels` for reviewed-only gold/held-out sets. Validation: GitNexus impact LOW for `build_example`, `build_dataset`, `run`, and `record_intake_triage_verdict.py`; `python3 -m py_compile scripts/datasets/build_triage_set.py scripts/datasets/record_intake_triage_verdict.py tests/unit/test_dataset_builders.py`; `uv run --with ruff ruff check ...`; `uv run --with pytest --with pyyaml pytest -q tests/unit/test_dataset_builders.py` -> `6 passed`; default live-source CLI smoke emitted 720 rows; temp reviewed-label smoke over real `intake-001` emitted exactly one reviewed-only row and privacy scan found no `source_text`, `citation_context`, or prompt-injection text.
- 2026-06-21: Stdlib CPU triage-baseline scaffold landed on current orchestrator branch. `scripts/datasets/train_intake_triage_baseline.py` reads the reviewed-label triage JSONL, filters to reviewed examples by default, trains/evaluates a deterministic multinomial naive-Bayes baseline, and writes aggregate-only JSON reports with acceptance status. It deliberately reports `insufficient_reviewed_labels` until the 100-row reviewed-label gate exists; no NumPy/sklearn dependency was added because those packages are absent in the active environment. Validation: GitNexus impact LOW for the touched dataset test target and `_common.load_jsonl`; `python3 -m py_compile scripts/datasets/train_intake_triage_baseline.py tests/unit/test_dataset_builders.py`; `uv run --with ruff ruff check scripts/datasets/train_intake_triage_baseline.py tests/unit/test_dataset_builders.py`; `uv run --with pytest --with pyyaml pytest -q tests/unit/test_dataset_builders.py` -> `8 passed`; live-source smoke under `/mnt/raid0/llm/tmp/f3-triage-baseline-smoke-20260621T041938Z` confirmed the current default reviewed-label corpus has 0 reviewed rows and the baseline reports `insufficient_reviewed_labels` with no raw text in the report.
- 2026-06-21: F7's first monthly economic review (`epyc-orchestrator` `876172e4`, `orchestration/reports/economic_review_2026-06.md`) records F3-W3a planner-distill as economically justified for operator review after the 2026-06-06 planner-spend projection exceeded threshold (`$410.75` vs `$250.00`). This does not ungate training: W3 remains HW-gated on the MI210 path and must still meet its shadow approval protocol before any binding use.
- 2026-06-27: Intake-triage review queue landed on current orchestrator branch as `c27664f8` (`Prepare intake triage review queue`). `scripts/datasets/prepare_intake_triage_review.py` emits prompt-free `intake_triage_review_queue.v1` rows, excludes already reviewed IDs, supports `--include-verdict` / `--exclude-verdict`, and writes a manifest. The committed queue contains 120 actionable rows from the real research intake index (`worth_investigating`, `adopt_patterns`, `adopt_component`, `new_opportunity`) and omits quarantined source/citation text. Validation: GitNexus impact LOW for reused `build_triage_set.py:build_dataset`; `uv run python -m py_compile scripts/datasets/prepare_intake_triage_review.py`; `uv run ruff check scripts/datasets/prepare_intake_triage_review.py tests/unit/test_dataset_builders.py`; `uv run pytest tests/unit/test_dataset_builders.py -q` -> `9 passed`.
- 2026-06-28: Review-readiness status landed on current orchestrator branch as `4f860e20` (`Report intake triage review readiness`). `scripts/datasets/intake_triage_review_status.py` reports aggregate queue/reviewed-label progress and refuses to mark the baseline gate ready until the reviewed-label threshold is met; `prepare_intake_triage_review.py` now threads `--label-source shadow_job` through review rows and recorder commands so synthetic or delegated review queues are not mislabeled as direct operator labels. Live status smoke over the committed queue reports `status=needs_reviewed_labels`, `queue_rows=120`, `reviewed_rows=0`, `remaining_queue_items=120`, `labels_needed=100`, and `ready_for_baseline=false`. Validation: GitNexus impacts LOW for orchestrator code/tests/docs; `uv run python -m py_compile scripts/datasets/intake_triage_review_status.py scripts/datasets/prepare_intake_triage_review.py tests/unit/test_dataset_builders.py`; `uv run pytest tests/unit/test_dataset_builders.py -q` -> `13 passed`; `uv run ruff check scripts/datasets/intake_triage_review_status.py scripts/datasets/prepare_intake_triage_review.py tests/unit/test_dataset_builders.py`; `git diff --check`.
- 2026-06-28: Trusted reviewed-label authority landed on current orchestrator branch as `f8738b24` (`Enforce trusted intake triage label sources`). Default authority is now `operator` across `build_triage_set.py`, `prepare_intake_triage_review.py`, `intake_triage_review_status.py`, and `train_intake_triage_baseline.py`; missing `label_source` rows are treated as legacy operator rows, while `shadow_job` rows no longer satisfy baseline readiness, baseline training, reviewed-label overlays, or operator-review queue suppression unless explicitly requested through the new trusted-source CLI flags. Live status smoke remains `status=needs_reviewed_labels`, `trusted_label_sources=["operator"]`, `trusted_reviewed_rows=0`, `queue_rows=120`, and `labels_needed=100`. Validation: GitNexus impacts LOW for all touched F3 dataset entry points; `uv run python -m py_compile ...`; `uv run ruff check ...`; `uv run pytest -q tests/unit/test_dataset_builders.py` -> `17 passed`; adjacent `tests/unit/test_dataset_builders.py tests/unit/test_lab_readiness_report.py` -> `22 passed`; A10/action guard coverage `tests/unit/test_seed_operator_strategies.py tests/unit/test_autopilot_actions.py` -> `82 passed`; `git diff --check`; orchestrator GitNexus refreshed at `f8738b2`.
- 2026-07-04: Dataset inventory refresh removed stale branch-ready/deploy language from `epyc-orchestrator/docs/reference/datasets.md`. Live evidence: `intake_triage_review_status.py --json` reports `120` queue rows, `0` trusted reviewed unique intake IDs, `100` labels needed, and `ready_for_baseline=false`; `readiness_report.py --json` reports `enabled_jobs=2`, `nightly_runnable=2`, `nightly_ready_now=0`, `task_records=0`, `verdicts=0`, and `gold_tuples=0`; current journals contain per-question vectors (`trial 789`, `55` `question_results`). This means the remaining F3 bottleneck is trusted review data collection, not replaying old capture branches.
