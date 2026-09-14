# Follow-ups discovered — noninf-20260914 (§7 of every folded fragment)

Deduplicated, grouped by the handoff that would own the work. `[id]` = the fragment that raised it.
Nothing here was fixed; none is in any dispatched scope.

## cpu-decode-roofline-program.md (INF-70)

- `/mnt/raid0/llm/tmp/inf70/agents/retest1/CHAMPION-FINAL.md:45` — **WRAP-12 record defect**: the run
  record names its champion arm `bin-r1 (10303)` while its header says "baseline `ef81196d5`"; every
  downstream quotation of 43.281 t/s / 2.1857× / ≥117% / ≥81% inherits an unstated two-commit
  instrumentation delta whose knobs default ON for a measured −2.136%. Sweep handoff + wiki +
  `progress/2026-09/`. `[wrap10]`
- `/mnt/raid0/llm/tmp/inf70/agents/retest1/bin-r1` + `/mnt/raid0/llm/tmp/inf70/retest1wt` — the only
  copies of the binary behind the campaign headline live in scratch; digests are in git, the artifact is
  not, so a re-measurement to close `CHAMPION_PIN_RESOLVED` would have nothing to compare against.
  Preserve or push `inf70/retest1-fix1` (one of WRAP-11's 21 unique-work branches). `[wrap10]`
- `epyc-inference-research` `Makefile:19-102` — `scripts/lib/test_canonical_recipe.py` is not in
  `PYTEST_SMOKE` and cannot be added as-is (`scripts/lib/__init__.py` imports `requests`, so collection
  fails); it has evidently never run in CI. A guard outside the Makefile's set fails silently. `[wrap10]`
- `scripts/lib/qwen38_flash_next_recipe.py` — `assert_artifact_digests()` reads ~95 GB and has no guard
  against being called from `preflight()`. Not wired in today; one edit away. `[wrap10]`

## promptforge-mutation-safety-contract.md (RTG-55)

- `scripts/autopilot/species/prompt_forge.py:~1440` — `apply_code_mutation` writes the live tree directly
  (git-checkpointed). `apply_code_mutation_in_context` is the isolated path and exists, but nothing forces
  its use. `[mhs]`
- Same file, apply gate — only `MutationEffect.UNSAFE` is refused, so `UNKNOWN` (the default on a
  hand-constructed `CodeMutation`) still applies. Tightening to "only screened effects apply" needs an
  audit of every construction site. `[mhs]`
- `scripts/autopilot/species/prompt_forge.py:~1478` — `revert_code_mutation` uses `git add -A <path>` for
  the new-file revert; narrow with a pathspec, but it is the idiom the project's hygiene rules warn about.
  `[mhs]`
- `scripts/autopilot/species/prompt_forge.py` is **format-dirty on `origin/main`** (`ruff format --check`
  fails on a pristine clone). A standalone formatting commit would keep future diffs readable. `[mhs]`
- `docs/guides/meta-harness-operator-guide.md` cites `prompt_forge.py` **line numbers** throughout
  (`line 575`, `line 594`, `line 509`, …), already stale by hundreds of lines. Symbol names would not rot.
  `[mhs]`
- `handoffs/completed/meta-harness-optimization.md:3` points at a non-existent file (housekeeping rider,
  owned elsewhere). `[mhs]`

## eval-tower-loop-robustness-audit-2026-07-20.md (EVL-13)

- `scripts/autopilot/eval_tower.py:1413` — `_compact_question_result` reads `r.rubric_threshold_source`
  unguarded, breaking the documented duck-typed-row contract; one-line `getattr` fix, and a real defect
  for any legacy/foreign row. `[etr]`
- `scripts/autopilot/safety_gate.py` — `SafetyVerdict` has a first-class `reliability_blocked` field but
  ETR-2's state is exposed only as the `quality_not_measured` category string; a downstream consumer that
  needs to branch on it wants a field. Deliberately not added to keep the diff clear of the parallel
  `safety_gate.py` edit. `[etr]`
- `src/api/routes/chat_pipeline/stages.py:115` — mock-mode `ChatResponse` omits `tokens_generated`
  entirely while `vision_stage.py:194` sets it to `0`, so two "no decode" cases serialize differently.
  Harmless today (ETR-3 excludes mock mode explicitly); an inconsistent wire contract for any future
  structural check. `[etr]`

## eval-tower-verification.md (EVL-14)

- `scripts/autopilot/eval_tower.py` — `EvalResult.n_questions` (set from `total_count` at `:5580` on
  origin/main) has no companion completed count, so the EV-14d requested/completed split stops at the four
  per-role mode reports. Whether the pair belongs on `EvalResult` (and therefore in `eval_details`, the
  journal, and `tier_specs._task_rate_inputs_from_row`) is open. `[ev14]`
- `scripts/autopilot/safety_gate.py:1949` still emits the `"vs baseline {q:.3f}"` prose — now redundant
  with `baseline_pin` for machine reads, but still the human-facing line, and deleting it would change
  `has_legacy_scale_failure_analysis` behaviour. Deliberately left. `[ev14]`

## objective-task-rate-goodput.md (RTG-23)

- `handoffs/active/objective-task-rate-goodput.md` has **TWO boxes named W3d** (`:73` the hold record,
  `:188` panel activation verified 2026-07-27), both ticked — a naming collision worth fixing when the
  file is next edited. (W3d itself confirmed done and documentation-only: `/workspace` `d28466df` touched
  only the handoff and `progress/2026-08/2026-08-12.md`, no code.) `[rtg23]`
- `src/autopilot_core/tier_specs.py` — `task_rate_qph_from{,_row}` still return `0.0` for "unavailable".
  Kept deliberately (they feed archived `eval_details.goodput_qph` history; rescaling would rewrite
  recorded history) but the sentinel is the same defect class and will bite whoever next reads them as
  measurements. `[rtg23]`
- `src/autopilot_core/planner_evidence.py:521` — `_float()` returns `0.0` for absence and is used for
  other journal fields; same class, left as a follow-up by coordinator ruling. `[rtg23]`
- No quality floor / admission gate exists anywhere in `src/autopilot_core/` (`quality_floor` /
  `min_quality` grep returns only the replay report's local `QUALITY_FLOOR = 1.0`). Option (b) of the
  operator decision would have to create one — that is the decision, not a defect. `[rtg23]`
- `orchestration/autopilot_state.json` — the live `pareto_archive` is **empty** (`state["pareto_archive"]`
  has no keys), so the live frontier could not be inspected directly and every count in RTG-23's table is
  journal replay. Either expected post-flip epoch fencing or a silent loss; worth a look by whoever owns
  autopilot state. `[rtg23]`

## learned-routing-controller.md (RTG-15)

- `scripts/benchmark/deprecated/seed_specialist_routing_v1.py:1501` — the same hard-coded
  `type:chat | objective:{task_description[:200]}`. Deprecated tree, but it is the copy a future author
  would grep and cargo-cult. `[epd3]`
- `orchestration/repl_memory/seed_loader.py:~495` — the seed write loop catches every `Exception` and only
  prints, so a total embed failure reports `loaded: 0, failed: N` and still exits 0. Tests now assert
  `failed == 0`, but the tool does not fail closed. `[epd3]`
- `scripts/benchmark/seeding_injection.py:189,287` — the objective is truncated to 200 chars at the
  payload level, i.e. the 2026-07-27 audit's defect #2 (12.6% of rows at the cap, 96.9% objective
  collision) still live on the eval-injection path. Changing it changes what is *stored*, not just what is
  embedded. `[epd3]`
- `orchestration/repl_memory/embedder.py` — `_serialize_failure_context:279`,
  `_serialize_exploration:299`, `_serialize_classification_prompt:305` are unguarded convention builders.
  Single-writer today, so no drift yet; same shape. `[epd3]`

## colbert-reranker-web-research.md (PIP-01)

- `scripts/benchmark/colbert/export_lateon_onnx_int8.py:465-494` — the banked ONNX↔PyLate parity figures
  compared **unlike inputs**: `_encode_onnx` feeds raw text (no `[D]`, hardcoded two-input feed, no
  `do_lower_case`) while `_encode_pylate` calls `model.encode(is_query=False)`, which inserts `[D]`. Mean
  pooling (`_pooled_vec:462`) + reference truncation (`:519`) were forgiving enough that it passed, so
  S3b's 8.24e-03 and S3c's 2.72e-03 are prefix-free-vs-prefixed, not like-for-like. Re-run through
  `colbert_encoder.encode(role=ROLE_DOCUMENT)` before either is cited again (needs the ONNX encoder, so
  not a zero-inference task). `[colbert]`
- `src/retrieval/kb_rag.py:66-67` — hardcodes `_QUERY_MAX_TOKENS = 48` / `_DOC_MAX_TOKENS = 256`; 48 is
  again GTE's number while LateOn declares 32. Deliberately NOT changed: both are stamped into
  `index_meta` (`:236-237`), so a change alters retrieval against every stored index and belongs with the
  OP-24 re-embed decision, where the stamp makes it detectable. `[colbert]`
- `src/retrieval/colbert_encoder.py` — `_MODEL_DIR` is import-time state that `kb_rag` stamps into
  `index_meta`, and the module is an unlocked singleton: a KB query in flight during a
  `refresh_model_dir()` re-point would see `_session is None` and return an ordinary miss. Pre-existing
  shape; worth a row if the reranker is ever enabled concurrently with KB-RAG. `[colbert]`
- **No defect**: `src/retrieval/cross_encoder.py:188-189` handles `token_type_ids` correctly and is a
  cross-encoder, so `[Q]`/`[D]` roles do not apply. Recorded so it is not re-investigated. `[colbert]`

## autopilot-sequential-allocation.md (EVL-04)

- `scripts/analysis/readjudicate_sequential_candidates.py:85-89` — `_axis_refuted_factory` now has no
  caller in `main()`; kept because the existing test module may bind it. A later sweep can delete it with
  its test. `[seqb2]`
- `scripts/autopilot/safety_gate.py:1780` — the refutation record uses the QUALITY axis's `k` for both
  axes (matching the journal's single `k` and the reader), but the rate axis carries its own `k_rate`,
  which can differ when the rate axis was skipped on earlier trials. Not wrong under today's policy;
  worth an explicit decision if `k_rate` ever diverges materially. `[seqb2]`
- `handoffs/active/autopilot-sequential-allocation.md:265` — the rate-axis comparator still has no era
  fence of its own (pre-existing). `[seqb2]`
- The sequential path remains default-off (`AUTOPILOT_SEQ_VERDICT=0`), so no live journal row will carry a
  `refutation` record until the gate is re-armed (`:249`, an operator decision). `[seqb2]`

## episodic-memory-integrity.md (EVL-10)

- `scripts/benchmark/tulving_episodic_adapter.py:325` `compute_chronological_awareness_score` — **CAS
  construction, not a scorer bug**: 30 of the 45 `chronological` questions in the 20ch set have fewer than
  two ground-truth items (15 have zero), so ordering is undefined and two thirds of the tau leg is
  structurally 0.0. Decide whether the paper's Chronological Order score excludes them before CAS is ever
  a headline. `[tulving]`
- `scripts/benchmark/tulving_episodic_adapter.py` `compute_simple_recall_score` — bin `6+` is empty in the
  20ch set, so the 20ch SRS averages over four bins while the 200ch figure averages over five.
  Cross-book-size SRS comparisons are not like-for-like. `[tulving]`
- `scripts/benchmark/tulving_episodic_adapter.py:685-710` — `_llm_judge_fallback_hook` is dead in the
  deterministic path, but `compute_f1_for_result` still branches on it and returns `matched_gt_items: []`
  when a judge fires, which would silently give every judged question zero tau coverage. Harmless today
  (no judge wired); a trap if one ever is. `[tulving]`
- The 2026-09-14 re-score artifact **is not itself an admissible claim** and deliberately emits no belief
  rows, so the corrected SRS/CAS are in git but gate nothing. If a decision ever needs to cite them, the
  path is a codified protocol for offline re-scoring, not a back-filled tuple. `[tulving]`
- Neither repo's `.venv` has `pandas`/`pyarrow` even though `epyc-inference-research/pyproject.toml` pins
  both, so `score_tulving_run.py` cannot run out of the repo venv as checked out. Either the venv needs a
  sync or the dependency claim is stale. `[tulving]`

## autopilot-continuous-optimization.md (RTG-02)

- `scripts/autopilot/autopilot.py:10365-10375` — `_append_baseline_promotion_event()` returns early for
  `updated=False`, so a speed-axis reseed (a real state write) is journaled nowhere. **This is option B of
  RTG-02's prepared decision package** (recommended). `[erastamp]`
- `scripts/autopilot/safety_gate.py` — the same unreachability shape survives on the other early-return
  paths (`seq_inputs_unavailable`, `seq_not_confirmed`, the monotonic skip, and etr's new
  `quality_not_measured`): if quality never improves again after a speed-era boundary, the speed fence
  stays open. Not a mutual latch (any better candidate clears it), so left alone deliberately; a general
  "reseed the speed axis on any eligible in-era frontier measurement" is a design decision, not a defect
  fix. `[erastamp]`
- `handoffs/active/autopilot-continuous-optimization.md:1714` — the E8 quality-baseline reseed row is
  superseded by `ruling_op19_e8_chain_20260827.json`, not by RTG-02's work; it is the owning session's
  call whether it closes as **superseded** (the ruling's own word) rather than done. `[erastamp]`
- `orchestration/repl_memory/q_scorer.py:52` — `Q_TD_WRITE = os.environ.get(...)` is read at **import
  time**, so the branch production actually runs is `False` under pytest unless a test monkeypatches the
  module attribute. This is a standing test-coverage hazard for that whole write path, not only for
  `assigned_role`/`work`: it is why the pre-existing create-only tests passed for the bug's entire
  lifetime. A fixture or a config-object read would remove the trap. `[invlog]`
- `src/api/routes/openai_compat.py:285` also reads `repl._invoked_tools` (correct), but sits outside the
  five modules covered by invlog's new `ast` guard. The guard's module list is **hand-maintained**, so it
  will not notice a *new* route file that reads the shared `get_invocation_log()`. `[invlog]`
- `src/registry/tool_registry.py` — `invoke()` appends to the now-bounded shared ring from whatever
  thread is dispatching. `deque.append` is atomic under CPython so the bound holds, but the ring has no
  documented synchronisation contract for a future non-CPython or free-threaded build. `[invlog]`

## speculative-decoding-mtp-refresh.md (INF-50)

- **The lean registry is auto-generated and its line numbers are quoted as if authoritative.** The sw4
  dispatch pointed a *prose* edit at `epyc-orchestrator/orchestration/model_registry.yaml:1461/:2341`;
  that file's own banner (lines 1-16) says it is compiled from the research master at every stack start.
  A documentation edit aimed at the generated view writes into sand. Worth a one-line note wherever the
  registry is cited for editing. `[sw4]`
- `src/registry/registry_compiler.py:303-320` — `_format_header_banner` embeds `--master` verbatim, so
  compiling from a worktree or temp copy produces an artifact advertising that throwaway path as the
  source of truth (corrected by hand in `a1d36daf`). Canonicalize the path, or refuse a non-canonical one.
  `[sw4]`
- **A fresh `epyc-inference-research` worktree cannot pass its own pre-commit.**
  `scripts/validate/check_evidence_durability.py` reported **12 MISSING** citations in a clean worktree vs
  **0** in the main clone, purely because the cited `data/`/`artifacts/` trees are gitignored and absent
  from any new worktree. Every agent editing the master registry in a worktree hits this and will be
  tempted to reach for `EPYC_ALLOW_COMMIT_HYGIENE_BYPASS`. The checker should resolve gitignored citations
  against the repo's git common-dir worktree root, or say so. `[sw4]`
- `scripts/registry/stack_change_pipeline.py check` **fails with 57 errors on `main` today**, independent
  of any of this work — port vs launch-manifest mismatches on frontdoor/ingest/toolrunner/worker_*, plus
  three `source_artifacts` hash mismatches driven by **uncommitted** edits in the shared
  `/mnt/raid0/llm/epyc-orchestrator` clone. Any session that runs this gate will read it as their own
  breakage. Worth a baseline note or a row. `[sw4]`

## moe-spec-cpu-spec-dec-integration.md (INF-40)

- `wiki/INDEX.md:3` repeats the "paired `tg128` row is uninformative by construction" framing without the
  `pp512` half; it becomes stale now that the four downstream corrections have landed. `[inf40]`
- **Neither MoE-Spec record carries a protocol-id**, so no MoE-Spec number is a claim under
  `MEASUREMENT.md` — and there is **no belief-kernel write-side hook** on either
  `data/moe-spec-bsweep-2026-08-25/` or `artifacts-df25/champion_anchor_*/`, exactly the
  `benchmarks/results` failure mode `CLAUDE.md` names. Candidate source row for
  `scripts/vidya/adapters/README.md` **plus** a task in `vidya-belief-substrate-program.md` (preparation
  only; the owning session applies). `[inf40]`
- `data/moe-spec-bsweep-2026-08-25/plan.json` records that the "live verification batches" were
  **reconstructed substitutes** (the 2026-07-03 prompts were never persisted). Documented honestly in the
  artifact, absent from every downstream quotation of the +10.7%, including the handoff table. `[inf40]`

## autokernel-rebuild-program.md (INF-66) / autokernel-unified-surface-program.md (INF-73)

- **R23-61a is now the binding successor, and it is a live blocker.** Every serving floor on disk
  predates R23-55, so **every one of them loads as `legacy` and refuses to gate** —
  `FloorReading.gate_floor` fails closed by design. The next serving gate cannot run until the floor is
  recalibrated through `recal_serving_floor --apply` (which now stamps `unit` and `n`) at n ≥ 24 with an
  interval under the recipe in force. Needs the GPU, ~30 min. `[floorunit]`
- `scripts/kernel_rnd/autokernel/loop/bench.py:44` — `FLOOR_UNIT` repeats the `"process"` literal because
  `serving` → `loop` → `bench` is a real import cycle (hence `bench.py`'s lazy in-function `serving`
  imports). A leaf module owning the unit vocabulary would remove the duplication; a test pins the two
  together for now. `[floorunit]`
- `artifacts/autokernel-aa-noise-floor/aa-noise-floor.json` — the D8 instrument-characterisation artifact
  behind `MEASURED_FLOOR_PCT` carries **no `unit`**. The built-in table is now labelled in code
  (`bench.FLOOR_UNIT`, `MEASURED_FLOOR_N = 20`) but the artifact itself was deliberately not rewritten,
  so the field is derivable from its single-writer schema rather than stated. `[floorunit]`

## Cross-cutting / tooling (no single owning handoff)

- `scripts/hooks/check_commit_hygiene.py:282-310` — **`positional_and_flags()` misreads shell redirection
  tokens as pathspecs**, so `git commit --file=<msg> 2>&1 | tail` is blocked as a "pathspec commit"
  (`positionals[0] == "2>&1"`). Same family as the quoted-`-m` false positive its own docstring documents.
  Strip `>` / `>>` / `2>&1` / `|` before computing positionals. Cost every one of four agents a retry, and
  a guard that fires spuriously is how a real block eventually gets bypassed.
  Raised independently by `[wrap10]`, `[colbert]`, `[erastamp]`, `[sw4]` (and hit by `[mhs]`, `[ev14]`,
  `[epd3]`). `git commit -F -` / `-F <file>` is refused for the same reason; `--file=<path>` passes.
- **`origin/main` pre-existing test failures on `epyc-orchestrator` are a shared baseline, not per-task
  breakage.** `pytest tests/unit` at `35b05fde`: **29 failed / 12,667 passed** `[etr]`. The
  time-dependent `tests/unit/test_autopilot_actions.py:1332`
  (`test_recent_eval_qids_excludes_only_rows_inside_recency_window`) fails with the calendar — its
  hardcoded `2026-07-01T00:00:00Z` row is 75 days old against the test's own 60-day window — and needs a
  frozen/relative clock; raised by `[mhs]`, `[ev14]`, `[etr]`, `[rtg23]`.
  Also pre-existing: `test_infra_failed_disposition.py::test_compact_row_and_aggregate_accept_duck_typed_rows`,
  `test_offline_reward_pairwise_holdout_expansion_plan.py::test_pairwise_holdout_writes_guarded_collection_manifest_and_script`
  `[etr]`; 9 in `test_e8_quality_baseline_reseed.py` `[epd3]`; 20 in the
  `safety_gate|era|baseline|calibrat` selection `[erastamp]`; 5 in the wider dashboard/journal/planner
  sweep `[rtg23]`. Two more named individually, both reproduced on a **clean `origin/main` detached
  worktree**: `test_e8_quality_baseline_reseed.py::test_legacy_source_change_after_preflight_blocks_scorer_replay`
  and `test_e8_quality_baseline_v5.py::test_generation_tail_replaces_only_target_response_and_sidecar_bytes`
  — they fall inside etr's e8-quality-baseline block of 16 but were **not** among the three pre-existing
  failures the invlog dispatch named, so they are unowned red tests as far as that dispatch knew. `[invlog]`
- **`epyc-inference-research` autokernel-loop baseline**: `pytest scripts/kernel_rnd/autokernel/loop -q`
  at `origin/main` `7ea556f4` reads **176 failed / 201 errors / 2509 passed**; the remainder are
  environmental on this host (HTTP-child fixtures, live-store and port-bound tests) and include the
  `test_campaign_footprint.py` / `test_program_md.py` set. `test_matched_serving.py`'s
  `test_actual_matched_keep_validation_reuse_and_other_target_compare` and
  `test_post_keep_refresh_failure_preserves_keep_and_starts_no_candidate_compare` fail identically on
  `origin/main` and are unrelated to floors. Also: `/tmp` is blocked on this host, so pytest needs
  `TMPDIR` pointed inside `/mnt/raid0/llm/tmp` or its basetemp mass-fails. `[floorunit]`
- `scripts/autopilot/eval_tower.py:1142` (and `scripts/benchmark/seeding_scoring.py:133`) — pre-existing
  `ruff F401`: `INBAND_ERROR_PREFIX` imported and unused; re-export intent unclear. One-line delete.
  Raised by `[etr]`, `[ev14]`, `[erastamp]`.
- `epyc-inference-research` `scripts/lib/__init__.py` imports `requests`, so a bare
  `python3 -m pytest scripts/lib/...` fails at **collection**, not in any test. `make test` / `uv run` is
  the contract. `[wrap10]`
