# 2026-09-16 — closure-audit follow-up (sub-closure-fix)

This is a zero-inference follow-up to `progress/2026-09/2026-09-16-sub-closure-audit.md`. The work was done
in worktree `/mnt/raid0/llm/worktrees/sub-closure-fix` on branch `sub/closure-fix-20260916`, which is not
pushed.

## 1. False closures reopened (checkbox discipline, `SESSION_LIFECYCLE.md` → *Two axioms*)

Each box below is unticked, keeps its original text (with the old tick struck through), and has a dated
reopen note that gives the checked ref, "exists on no ref", and the audit file.

| box | phantom | checked against | ticked by |
|---|---|---|---|
| `reviewer-calibration-accounting.md` RC-9 | `review_ledger.v2`, `rubric_json`, `per_item_grades_json` | orch `88a2902d` + all branch tips + `log --all -S` in all 3 repos | root `4762625d` |
| `rlm-contested-claims-self-evaluation.md` E1a | `scripts/benchmark/niah_scorer.py` | research `cfbfa448`, orch, root; `log --all`; disk | root `4762625d` |
| `completed/benchmark-results-dashboard-…` Phase-2 "Persist … (SQLite)" | `scripts/dashboard/export_benchmark_artifact_sqlite.py`, `data/benchmark_artifacts.sqlite` | root `6e85d3b5`, orch, research; `log --all`; disk | root `4762625d` |
| `tool-output-compression.md` "Instrument TOTAL tokens" (**new**, found by the strict sweep) | session-log `input_tokens`/`total_*`/`token_observed_turns` | orch `88a2902d` `src/graph/session_log.py`; `log --all -G` | root `08e9d60d` |

- The **completed** handoff's Backfill box stays ticked. Its JSON half is real
  (`build_benchmark_artifact_inventory.py`), so it got a correction note instead. The handoff was not
  moved.
- **"The two other class-(b) boxes in `4762625d`".** The audit's confirmed class-(b) set from that
  commit was RC-9, E1a, the exporter, and UTM-M7/M8. UTM-M7/M8 are no longer false (task 2). The other
  two cohort-sweep leftovers were checked and are **not** phantoms:
  - UTM-M4 (`google-research/reasoning-bank`, `induce_memory.py`, `SUCCESSFUL_SI`…) cites an external
    repo.
  - The TTS guardrail box (`worker_tts`, `voice_id`) is a default-deny design.
  - RC-3's `rationale_vs_gold_cause` is a corpus-row schema field in data, and its tick came from
    `c736992c`, not `4762625d`.
  - This row is flagged for the caller in case another pair was meant.

## 2. UTM-M7/M8

No change was needed. On root `origin/main`, both boxes already cite orchestrator `74418b3c` and merge
`d748b4c7`, and say that the 2026-07-29 tick was false.

## 3. DAR-6.3 / DAR-6.4 / DAR-6.5

- DAR-6.3 and DAR-6.4 stay ticked, because the work was really built (orch `5f5fd8f6`). Both are now
  labelled **SUPERSEDED/REMOVED 2026-06-16**, with a removal note: `771348c8` deleted `src/swarm_fanout.py`
  and its symbols, and `src/bradley_terry.py` survives.
- DAR-6.5 has a dependency note: its dependency is gone. The `swarm_fanout` FeatureSpec
  (`src/features.py:211,563`, `runtime_flags.spec.yaml:117`) is read by no code, so it controls nothing.

## 4. Annotations only (no box state changed)

- **C6 anchor `a4cb04ca8`, on no ref.** Annotated boxes: RVP-C6-1, C6-1a, C6-2 and C6-8
  (`rocm-verify-profile-backend.md`), R24-1 (`autokernel-rebuild-program.md`), and the two
  `autokernel-research-loop.md` boxes (IQK proposal-v4 and "Bind the hardened instrument").
  - The equivalent work is llama.cpp `974b5fcb3` (sole parent `0db32c06`).
  - **Correction to the brief:** `974b5fcb3` is the tip of
    `fork/experimental-v9-autokernel-t1-hardening-final`. The branch
    `fork/experimental-v9-autokernel-t1-hardening` points at a different one-parent commit,
    `0492c2319`.
  - Six files in `/mnt/raid0/llm/autokernel/iqk-*.json` still pin `a4cb04ca8`.
- **AK-V27-RCV and AK-V27-CMP:** branch-only notes (`codex/autokernel-v27-*`).
- **Hermes F:** preservation-risk note. `532a49f1` exists only on local `main` of
  `/mnt/raid0/llm/hermes-agent`, whose only remote is NousResearch `origin`.
- **K28.5a:** the doc is staged but not committed, and `gated_delta_net.cu` has uncommitted edits, in
  `llama.cpp-k28-prototype-20260720` (branch `k28/prototype-20260720`).
- **Z12:** `docs/gdn2-low-rank-static-analysis-2026-08-25.md` is untracked (`??`) in research.
- **INF-70** (`cpu-decode-roofline-program.md`, under "Tasks filed from the 2026-09-08 findings"): the
  research clone is 3 commits ahead of origin: `1780fa7b` (on main as `56ef1404`), merge `6ab403ed`, and `ae8e5ef9`, whose
  twin `ccbfe1b8` is on main.
  - **Correction:** `1780fa7b` *is* on the pushed branches `origin/inf70/evidence-2026-09-08` and
    `origin/lane/autokernel-status-bounding-20260914`. It is unmerged, not unpushed.
  - Nothing was pushed.

## 5. Tool promoted

- `scripts/handoffs/closure_audit.py` accepts `--root/--orch/--research/--rev/--handoff-dir`,
  `--no-external`, `--triage`, `--tsv` and `--git-timeout`. `--strict-idents` is kept.
  - Word search was rewritten as a single tokenizing pass over `cat-file --batch`. The old
    `git grep -w -F -f` with about 2,200 patterns ran for more than 20 minutes on the root tree, and the
    first strict run timed out.
  - Branch tips are now scanned only over the files each tip changed since its merge-base.
  - An identifier that matches a file stem (a test-module name) now counts as present.
- `scripts/handoffs/closure_audit_triage.json` holds 407 override keys, all line-free. It was seeded
  from the audit's 265-row triage and this sweep.
- `tests/test_closure_audit.py` is a fixture repo with real, phantom, branch-only and file-stem
  references, plus strict and triage cases. Result: 3 tests OK.
- New guide `docs/guides/agent-workflows/handoff-closure-audit.md`, linked from `INDEX.md` and
  `handoff-index-authoring.md`.

## 6. `--strict-idents` sweep over `handoffs/active`

The run took 63 minutes and exited 0, against root `4018e411`, orch `88a2902d` and research `be6bbad9`.

- 3,374 checked boxes, 2,542 with references; 270 flagged.
- Identifiers: ok 2,832, a 50, b 117, c 13, d 82.
- 97 of the class-b identifiers were **new and untriaged**. Every one was triaged, as follows:

| outcome | count / examples |
|---|---|
| **confirmed phantom → reopened** | 1: `tool-output-compression.md` `token_observed_turns` (see §1) |
| file-stem names (test modules exist) | 5: `test_autopilot_phase_status`, `test_autopilot_startup_attestation`, `test_e8_quality_baseline_reseed`, `test_model_descriptors_schema`, `test_autokernel_serving_feedback`. The tool now resolves these. |
| memory-file names | 9: `feedback_*` / `project_*` |
| external or upstream symbols | about 40: fla `chunk_*`, rocprofiler, PaddleOCR kwargs, RISC-V `v_*` ops, llama.cpp experimental-branch symbols (`skip_barrier`, `build_qsa_top_k`, `model_shared`, …), SkyRL `parent_rid`, dsh `PiAiModelProfile` |
| design, spec or recommendation text | S3-AKU-17 schema fields (a design item), `trimmed_window_empty` (a recommendation), P3-1 `recent_failure_history` (spec bullet), and `protected_action` (the box itself says the grep returns nothing) |
| spec event names, implemented under other names | P2-6/P2-7 `consult_denied` / `review_advisory`: `ConsultationDenied` and `consult_events` dicts exist on orch main |
| run ids, config keys, prose | the rest (`sample_135`, `vl_ocr_0124`, `xrt_overall`, …) |

Other new untriaged rows:

- **dflash2** (`:64`, `:132`, `:356`): research `sub/gpu-runner-20260916` is unmerged, from today's GPU
  runner, so this is for its owner.
- `869effe5` is a binary digest, and `ap53_reproposal.py` is a declared scratch script; both are false
  positives.
- The 40 class-a identifiers are vendored llama.cpp symbols on research branches, or tests and code
  deleted later; none is a phantom.

## 7. Gates

- `index_state.py` was regenerated, and `--check` reported 0 problems.
- `cite-check` over the edited handoffs was clean: no refuted, conflicted or dangling citations.

## Items for other owners

- **AutoKernel:** re-point the `a4cb04ca8` pins (handoff boxes and six `iqk-*.json` manifests) to the
  `974b5fcb3` / `-final` lineage. `caa22f42` and `cffb98d3` are branch-only.
- **Hermes:** push `532a49f1` to a fork.
- **K28 prototype:** commit the staged scaffold.
- **Research:**
  - commit the Z12 doc;
  - land `1780fa7b` (on main as `56ef1404`) on main;
  - merge `sub/gpu-runner-20260916` (dflash2 SL1/SL5 evidence).
- **Reviewer-calibration and RLM owners:** RC-9 and E1a are open work again.
- **Dashboard owner:** decide whether to file a successor for the SQLite archival store.
- **Tool-output-compression owner:** the total-token telemetry is not built.
