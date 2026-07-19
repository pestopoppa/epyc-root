# GLM-5.2 Accept-Control Signoff Packet

Date: 2026-07-18
Scope: superseded operator-facing input for `GC-shadow-repair4b.2b` before
`P-REV-1`.
This packet was prepared from existing artifacts only; no inference, build, or
benchmark run was performed.

## Supersession Notice

Status update, 2026-07-19: this packet is historical. The operator-approved
executable-oracle / `multi_oracle` path converted enough C-CRAB accept controls
to decision grade without manual row labeling. `GC-shadow-repair4b.2c` and
`P-REV-1` then ran on the decision-grade slice, and GLM-5.2-IQ2 failed
patch-review admission (`FA=41.7%`, `FR=25.0%`, `AUC=0.509`). The current
blocker is reviewer/control-plane route selection or a repaired-GLM admission
run, not this signoff packet.

## Historical Decision Needed

Before `P-REV-1`, an operator/oracle must convert the current C-CRAB/Python
full-candidate accept-control packet from observation-only to decision-grade.

Required decision:

1. Review every row in
   `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_n24_audit_packet_20260718.json`
   using the row's task and full candidate patch.
2. For each row, set `signoff.status` to `reviewed`, set `signoff.reviewer`,
   set `signoff.reviewed_at`, and set `signoff.notes` with the rationale.
3. Set `signoff.decision` to:
   - `hard_accept` only if the patch is a complete plausible fix for the
     reported task.
   - `reject_or_ambiguous` if the patch is incomplete, unrelated,
     under-tested, or requires execution to know.
4. Run the inference-free signoff summarizer without `--allow-unreviewed`.
   `P-REV-1` should not proceed on this accept-control slice unless the report
   has `decision_grade: true`, `hard_accept_n >= 24`, and `unreviewed_n == 0`.

If any of the 24 rows are `reject_or_ambiguous`, the accept-control blocker is
not closed by this packet. Select/sign off replacement full-candidate accept
controls or provide executable oracle evidence until there are at least 24
reviewed hard accepts.

## Historical Evidence State

GLM patch-review still has an accept-control gate, not a serving/build gate.
The targeted old-false-accept confirmation rejected all six curated hard
negatives, but it false-rejected one observation-grade clean accept control. That
row is not valid as a hard model error until audited, because the corpus marks
merged PR accepts as `gold_confidence=observation`.

Historical deterministic accept-control filter output:

- Matching C-CRAB/Python clean accept pool: `151`
- Hard accept-control pool before manual/oracle signoff: `0`
- Selected rows: `24`
- Selected rows that are observation-only: `24`
- Decision-grade: `false`

Machine review recommends `24/24` rows as hard-accept candidates, but it is
explicitly non-authoritative. It did not modify `signoff` fields, did not claim
operator signoff, and wrote no official signoff outputs. It flags five rows with
redacted long digit runs and one submodule-update format concern for manual
attention.

## Exact Artifacts

Primary signoff input:

- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_n24_audit_packet_20260718.json`

Selection/filter evidence:

- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_n24_filter_20260718.md`
- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_n24_filter_20260718.json`
- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_n24_row_ids_20260718.txt`
- Source corpus: `/mnt/raid0/llm/datasets/nearmiss-corpus-v1/rows.jsonl`

Machine recommendation inputs, non-authoritative:

- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_machine_recommendations_20260718.md`
- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_machine_recommendations_20260718.json`

Inference-free signoff summarizer:

- `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/glm52_ccrab_accept_control_signoff.py`
- Expected validation mode:
  `python3 scripts/benchmark/glm52_ccrab_accept_control_signoff.py docs/data/glm52_ccrab_accept_control_n24_audit_packet_20260718.json --min-hard-accepts 24`

Prior GLM evidence that motivates this gate:

- Targeted old-FA n=12 row list:
  `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_rowid_n12_confirm_20260718.txt`
- Curated oracle notes for six reject controls:
  `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_oracle_notes_n12_confirm_20260718.json`
- Targeted n=12 run summary:
  `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_corpus_direct/glm52-ccrab-patch-review-rowid-v5-notes-n12-20260718Tcodex/summary.json`
- Targeted n=12 decisions:
  `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_corpus_direct/glm52-ccrab-patch-review-rowid-v5-notes-n12-20260718Tcodex/decisions.jsonl`
- Earlier negative-evidence n=4 smoke:
  `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_corpus_direct/glm52-ccrab-patchdiff-negative-evidence-v3c-n4-20260718Tcodex/summary.json`

Governance context:

- `/mnt/raid0/llm/epyc-root/handoffs/active/glm52-reviewer-capability-gates.md`
- `/mnt/raid0/llm/epyc-root/handoffs/active/v7-promotion.md`

## Historical Blocker

`GC-shadow-repair4b.2b` was open because the accept-control slice had no
decision-grade full-candidate accepts yet. That condition has since been closed
through executable oracle evidence.

Do not use this packet as the current GLM reviewer blocker. The current evidence
state is post-`P-REV-1`: GLM failed admission, and RM-2.fast did not produce a
clean replacement reviewer. Future work should either repair/retest GLM under a
new gate or make an explicit reviewer route decision.
