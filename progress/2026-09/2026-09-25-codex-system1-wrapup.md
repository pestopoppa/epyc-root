# System One and Evolution Research Intake Wrap-Up — 2026-09-25

## Problem

Turn a long, multi-stage research intake into durable EPYC work without losing actionables across LensVLM, Jev and open typed-decision models, DGM-family systems, long-horizon program evolution, open-ended evolution, and autonomous-science evaluation.

The final Stage 4 application also had to coexist with a concurrent EXL3 intake that occupied the originally reserved `intake-1528..1575` range.

## Resolution

- Rebased the intake lane onto the concurrent work and remapped this wave's 132 new records from `intake-1528..1659` to `intake-1576..1707`. Existing records `intake-772`, `intake-779`, and `intake-780` retained identity.
- Applied the operator-approved Stage 3 plan to all 135 scoped records: 120 `integrated`, 12 `knowledge_only`, two `monitor`, and one `declined`.
- Added 53 open implementation and evaluation tasks plus three completed factual findings across the existing handoff owners.
- Created `handoffs/active/formal-artifact-reproducibility.md` and routed it through EVL-51.
- Added seven prospective source rows to `scripts/vidya/adapters/README.md` for LensVLM, external typed-decision bundles, DGM replay, long-horizon/adversarial search, OEE/QD, autonomous science, and formal-proof rebuild receipts.
- Persisted all twelve Stage 1–3 steering messages, the Stage 3 approval hash, the nine-group source closeout, and final Stage 4 validation in `.research-session.json`.
- Corrected DGM task-generation attribution, preserved the original `S3-INF03-01` obligation while filing the new AIDE comparison separately, fixed LensVLM task-ID collisions, placed TD-22..27 after TD-21, expanded an abbreviated DGM pin, and repaired intake citations.

## Durable Files

| Area | Files | Result |
|---|---|---|
| Intake ledger | `research/intake_index.yaml`, `.research-session.json` | 1,703 unique validated records; complete disposition and steering metadata |
| Decision models | `typed-decision-plane.md`, `canonical-judge-suite-revamp.md`, `decision-aware-routing.md`, `harness-selection-and-integration.md` | robustness, calibration, provenance, judge-cascade, and harness-boundary tasks filed |
| Evolution systems | AutoPilot, AutoKernel, agentic-kernel, sequential-allocation, Eval Tower, and collaboration handoffs | matched controls, replay packages, provenance, adversarial panels, QD/OEE diagnostics, and long-horizon evaluation tasks filed |
| Multimodal | `multimodal-pipeline.md` | LensVLM provenance and isolated BF16 MI210 pilot filed as `MM-LENS-1/2` |
| Autonomous science | reviewer artifacts/calibration, AutoPilot, and Vidya handoffs | execution, artifact, adjudication, and validity outcomes separated |
| Formal artifacts | `formal-artifact-reproducibility.md`, `research-evaluation-index.md` | FAR-1/2 created and indexed as EVL-51 |
| Measurement capture | `vidya-belief-substrate-program.md`, `scripts/vidya/adapters/README.md` | prospective write-side requirements filed before governed runs |

## Verification

- `python3 scripts/handoffs/index_state.py --check`: passed after regeneration; the new formal-artifact handoff has exactly one owner.
- `python3 .claude/skills/research-intake/scripts/validate_intake.py`: 1,703 records validated.
- `bash scripts/validate/validate_intake.sh`: 1,703 records validated.
- Vidya citation check over 17 changed documents: 625 citations, zero problems.
- Strict JSON parse, task-definition uniqueness, and `git diff --check`: passed.
- Final Stage 4 commit `304e663b6e559cd5185cce842ef13b1036c4fb65` was serialized, pushed to `origin/main`, and verified with an empty `git cherry origin/main` result.
- The intake worktree, local branch, and autostash were removed after publication. Stale shared-checkout intake files were backed up before restoring the published versions.

## Remaining Work

No session-derived actionable remains only in conversation prose. The 53 open tasks are owned by their active handoffs and retain their experiment gates, dependency monitors, and explicit evidence requirements. No production kernel, service, model registry, or application code changed during this intake.

## Full Wrap-Up

- Compiled the research into seven durable wiki categories: agent architecture, autonomous research, benchmark methodology, routing intelligence, multimodal systems, formal verification, and knowledge management.
- Added measured writer-review evidence for each page. All seven review validations passed, and project-wiki lint reported zero errors.
- Advanced the wiki source manifest only for the 17 Stage 4 sources, this wrap-up report, and the new AutoPilot history ledger. Six later or concurrent source changes remain visible for their owning compilation pass: agent-loop design, two AutoKernel handoffs, DeepSeek-V4.1 evaluation, the later Vidya update, and the main-ak-seat progress report.
- Compacted `autopilot-continuous-optimization.md` from 3,603 to roughly 840 lines. The exact prior file is preserved in a reciprocal history sibling, and all 101 open checkbox items remain in the active handoff.
- Refreshed RTG-02, EVL-04, EVL-13, EVL-14, REV-02, REV-03, REV-09, and UFH-01 to current runnable next actions. No active handoff or index row qualified for pruning.
- Kept the README unchanged after its freshness check passed.

### Wrap-Up Verification

- `python3 scripts/handoffs/index_state.py --check`: passed after regeneration; citation check clean across 558 citations in the changed documentation set.
- Both intake validators passed against the current branch state with 1,713 unique records; the Stage 4 commit itself remains the 1,703-record checkpoint described above.
- Project-wiki lint: passed with zero errors; 91 pre-existing warnings remain informational.
- Seven `wiki_writer_review.py validate` runs: all accepted with zero errors.
- Scoped source-manifest check: zero additions, six intentionally pending changed sources, zero removals.
- README freshness and `git diff --check`: passed.
