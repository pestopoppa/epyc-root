# 2026-11-06 — Research intake: "You don't need long context" (3 dive waves, Stage-4 filed)

**Session**: intake-ydnlc-20261106 · **Branch**: `intake/ydnlc-20261106` · **Plan**: `research/deep-dives/ydnlc-20261106/PLAN.md`

## Ingested and dived

Primary source arXiv 2611.05306v1 (NVIDIA, "You don't need long context"), plus three waves of operator-approved
dives: intake-2628…2640 (13 entries; 10 dived in this run, 2 existing entries deepened, 3 left
`stage1-unverified`). Duplicate re-encounters recorded rather than re-minted (intake-1071 ACE, intake-2397
SWE-chat, intake-2527 TRACE).

## Findings that changed the plan

- Compaction preserves benchmark accuracy only where ground truth lives outside the transcript and only for
  strong models; the source's Appendix D is the local-model counter-result (Qwen 3 Coder Next 53.0 → 3.6 %).
- Governance, not task score, is the project-relevant failure: retained rules violated 2.6× more, soft policies
  decay 8.3× more than hard norms, open-weight compactors retain 6 % of side constraints, presence checks are not
  safety checks.
- **OpenCode compaction laundering is a live provenance hole**: role labels interpolated unescaped and the summary
  re-injected as a user message (paper-measured 87–100 % across five harnesses). Our build is untested; the
  orchestrator path is structurally safer but unguarded by test.
- Local speed evidence for short context already exists: CPU depth alone −55 % decode / −60 % prefill by 128k; MI210
  np8 L64k decode collapse 26.71 → 10.18 tok/s (occupancy confound unresolved).

## Filed (Stage 4, operator-approved)

9 tasks, 0 checkbox flips: UFH-21 (laundering probe/patch), TOC-CMP-1…5 (detector fix, retention+compliance probe,
artifact contract/arms, reliability clause, role-boundary test), REG-ENF-1/2 (rule registry, tool-use hook),
DEPTH-ENV-1 (depth-to-throughput envelope for the launch-flag session). M1 = monitor note only.

## Gates

`validate_intake.sh --plan-file/--session-file`: zero plan/session errors; repo-wide exit 1 is the pre-existing
`fold-list-1a/1b` → `handoffs/completed/mi210-serving-program.md` defect (5,877 errors, also fires on untouched
`cross-reference-map` lines). `index_state.py --check`: 0 problems. `compile_sources.py`: all 10 dive Markdown files
+ plan listed as new sources. Dive digest committed at `research/deep-dives/intake-digests/2026-11-06-ids-2628-2640.md`.

Lane branch pushed to origin; **not merged to main** (serialized-trunk decision left to the operator).
