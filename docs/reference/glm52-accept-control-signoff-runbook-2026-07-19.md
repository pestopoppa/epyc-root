# GLM-5.2 Accept-Control Hard-Signoff Runbook

Date: 2026-07-19
Scope: superseded bounded operator runbook for `GC-shadow-repair4b.2b` before
`P-REV-1`.

This runbook is preparation only. It does not perform inference, does not modify
the accept-control packets, and does not claim operator signoff.

Status update, 2026-07-19: this runbook is historical. The operator-approved
executable-oracle / `multi_oracle` path superseded manual labeling for this
slice, `GC-shadow-repair4b.2c` produced decision-grade accept controls, and
`P-REV-1` ran. GLM-5.2-IQ2 failed patch-review admission (`FA=41.7%`,
`FR=25.0%`, `AUC=0.509`). Do not point future agents at this runbook as the
current blocker.

## Decision Boundary

GLM-5.2 remains research-only for patch review because it failed the
decision-grade P-REV-1 run. The current decision boundary is reviewer route
selection or a repaired-GLM admission gate, not manual signoff on the old packet
files.

## Already Machine-Reviewed

The 2026-07-18 packet set has already done the mechanical preparation:

- Deterministic filter selected `24` C-CRAB/Python `merged_pr_accepted` clean
  controls from a matching pool of `151`.
- The selected slice is still observation-only: `hard_accept_control_pool_n=0`,
  `hard_accept_control_n=0`, `observation_only_n=24`,
  `decision_grade=false`.
- The audit packet contains full task and candidate patch text plus explicit
  `signoff` placeholders for all `24` rows.
- Machine recommendation review marked `24/24` rows as
  `hard_accept_candidate`, with `0` reject-or-ambiguous candidates.
- The helper was run in report mode without output paths and found
  `unreviewed_n=24`, `hard_accept_n=0`, `rejected_or_ambiguous_n=0`,
  `decision_grade=false`.
- No authoritative `signoff` fields were modified, no operator signoff was
  claimed, and no official `*_signoff_*.json` outputs were written.

Machine review is advisory only. It may accelerate human review, but it cannot
turn the observation labels into decision-grade controls.

This section is retained to explain the old packet lineage. It is not the
current path for C-CRAB accept-control qualification.

## Files To Review

Primary packet, to review row by row:

- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_n24_audit_packet_20260718.json`

Selection and row-id evidence:

- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_n24_filter_20260718.md`
- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_n24_filter_20260718.json`
- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_n24_row_ids_20260718.txt`
- `/mnt/raid0/llm/datasets/nearmiss-corpus-v1/rows.jsonl`

Machine recommendation sidecars, non-authoritative:

- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_machine_recommendations_20260718.md`
- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_machine_recommendations_20260718.json`

Inference-free signoff summarizer:

- `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/glm52_ccrab_accept_control_signoff.py`

Inference-free review-sheet helper and generated blank worksheet:

- `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/glm52_ccrab_accept_control_review_sheet.py`
- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_n24_review_sheet_20260719.csv`
- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_n24_review_packet_20260719.md`
- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_n24_review_sheet_status_20260719.json`

Governance context:

- `/mnt/raid0/llm/epyc-root/handoffs/active/glm52-reviewer-capability-gates.md`
- `/mnt/raid0/llm/epyc-root/docs/reference/glm52-accept-control-signoff-packet-2026-07-18.md`
- `/mnt/raid0/llm/epyc-root/handoffs/active/v7-promotion.md`
- `/mnt/raid0/llm/epyc-root/handoffs/active/tree-draft-forward-port-plan.md`
- `/mnt/raid0/llm/epyc-root/docs/reference/glm-mtp-contract-generalization-audit-2026-07-19.md`

## Manual Attention Flags

Review every row from the primary packet, not only these flagged rows. These six
rows need explicit attention because the machine recommendation sidecar found
format concerns:

| Row id | Manual concern |
|---|---|
| `nearmiss-v1:c-crab:04b3b67ccf17ffe1` | Candidate includes a submodule commit update; confirm the packet preserves the intended transition. |
| `nearmiss-v1:c-crab:08cafcb6483d8389` | Candidate has redacted long digit runs; confirm redaction is metadata-only. |
| `nearmiss-v1:c-crab:09584d0209952576` | Candidate has redacted long digit runs; confirm redaction is metadata-only. |
| `nearmiss-v1:c-crab:10070430d41b73e9` | Candidate has redacted long digit runs; confirm no significant expected-expression literal is hidden. |
| `nearmiss-v1:c-crab:1600ca8239e2f6e0` | Candidate has redacted long digit runs; manually check path or fixture literals before signoff. |
| `nearmiss-v1:c-crab:200003ca11cb7699` | Candidate has redacted long digit runs; manually check the Dockerfile fixture before signoff. |

No selected candidate patch was truncated. No task text had redacted long digit
runs.

## Historical Signoff Rules

For each of the 24 rows, review the `task` and full `candidate` patch.

Set:

- `signoff.status`: `reviewed`
- `signoff.reviewer`: non-empty human/operator or executable-oracle identity
- `signoff.reviewed_at`: non-empty UTC timestamp
- `signoff.decision`: one of:
  - `hard_accept` only when the patch is a complete plausible fix for the
    reported task.
  - `reject_or_ambiguous` when the patch is incomplete, unrelated,
    under-tested, format-damaged, or requires execution to know.
- `signoff.notes`: rationale. For `hard_accept`, include why the task is
  covered. For `reject_or_ambiguous`, include the blocker.

Do not mark a row hard-accept solely because it was a merged PR or because the
machine recommendation says `hard_accept_candidate`.

## Historical Optional Review-Sheet Workflow

The generated worksheet and Markdown packet are convenience layers over the
JSON packet. They do not replace row-by-row review of the packet's full `task`
and `candidate` fields, and the helper never turns machine recommendations into
decisions.

To regenerate the blank worksheet and bounded Markdown review packet:

```bash
cd /mnt/raid0/llm/epyc-inference-research
python3 scripts/benchmark/glm52_ccrab_accept_control_review_sheet.py \
  docs/data/glm52_ccrab_accept_control_n24_audit_packet_20260718.json \
  --machine-recommendations docs/data/glm52_ccrab_accept_control_machine_recommendations_20260718.json \
  --review-csv-out docs/data/glm52_ccrab_accept_control_n24_review_sheet_20260719.csv \
  --review-md-out docs/data/glm52_ccrab_accept_control_n24_review_packet_20260719.md \
  --summary-out docs/data/glm52_ccrab_accept_control_n24_review_sheet_status_20260719.json
```

After review, fill the worksheet's `decision`, `reviewer`, `reviewed_at`, and
`notes` columns for every row. Valid `decision` values are `hard_accept` and
`reject_or_ambiguous`; a blank decision remains `unreviewed` and blocks
decision-grade signoff.

To apply the completed worksheet into the official signed packet:

```bash
cd /mnt/raid0/llm/epyc-inference-research
python3 scripts/benchmark/glm52_ccrab_accept_control_review_sheet.py \
  docs/data/glm52_ccrab_accept_control_n24_audit_packet_20260718.json \
  --apply-review-csv docs/data/glm52_ccrab_accept_control_n24_review_sheet_20260719.csv \
  --signed-packet-out docs/data/glm52_ccrab_accept_control_n24_signoff_packet_20260719.json \
  --summary-out docs/data/glm52_ccrab_accept_control_n24_review_sheet_apply_20260719.json
```

The apply step refuses duplicate, missing, extra, or reordered row ids. It also
requires reviewer identity, review timestamp, and notes for every reviewed row.
It is still not the final gate; run the signoff summarizer below afterward.

## Historical Official Outputs Needed

Create a signed copy of the packet. Do not overwrite the unreviewed 2026-07-18
input packet.

Required signed packet:

- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_n24_signoff_packet_20260719.json`

Then run the inference-free summarizer from the inference-research repo:

```bash
cd /mnt/raid0/llm/epyc-inference-research
python3 scripts/benchmark/glm52_ccrab_accept_control_signoff.py \
  docs/data/glm52_ccrab_accept_control_n24_signoff_packet_20260719.json \
  --min-hard-accepts 24 \
  --expected-row-ids docs/data/glm52_ccrab_accept_control_n24_row_ids_20260718.txt \
  --json-out docs/data/glm52_ccrab_accept_control_n24_signoff_report_20260719.json \
  --row-ids-out docs/data/glm52_ccrab_accept_control_n24_hard_accept_row_ids_20260719.txt \
  --oracle-notes-out docs/data/glm52_ccrab_accept_control_n24_oracle_notes_20260719.json
```

Required acceptance outputs:

- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_n24_signoff_packet_20260719.json`
- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_n24_signoff_report_20260719.json`
- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_n24_hard_accept_row_ids_20260719.txt`
- `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_accept_control_n24_oracle_notes_20260719.json`

Historical acceptance condition:

- `signoff_report.schema == "glm52_ccrab_accept_control_signoff.v1"`
- `selected_n == 24`
- `min_hard_accepts == 24`
- `allow_unreviewed == false`
- `hard_accept_n == 24`
- `rejected_or_ambiguous_n == 0`
- `unreviewed_n == 0`
- `decision_grade == true`
- `accepted_row_ids_match_expected == true`
- `hard_accept_row_ids_20260719.txt` contains exactly the same 24 row ids as
  `glm52_ccrab_accept_control_n24_row_ids_20260718.txt`, one per line. This
  exact-match guard is enforced by `--expected-row-ids`.
- `oracle_notes_20260719.json` contains a note entry for every accepted row id,
  each with reviewer identity and review timestamp.
  `glm52_reviewer_corpus_direct_runner.py` accepts this structured signoff-helper
  output directly and extracts the `notes` field as the prompt hint.

Historical rejection or incomplete-signoff condition:

- Any `reject_or_ambiguous` row, any remaining `unreviewed` row, or
  `hard_accept_n < 24` keeps `GC-shadow-repair4b.2b` open.
- The report may still be useful as rejection evidence, but it is not an
  accepted hard-control packet for `P-REV-1`.
- To recover, select replacement full-candidate accept controls from the
  C-CRAB/SWE-CARE patch-review pool or attach executable oracle evidence until
  there are at least `24` reviewed `hard_accept` rows.

## Historical After-Signoff Flow

This flow was superseded by the executable-oracle path, then by the completed
P-REV-1 failure result. It is retained only as context for artifact provenance.
The historical flow was:

1. Update `GC-shadow-repair4b.2b` in
   `/mnt/raid0/llm/epyc-root/handoffs/active/glm52-reviewer-capability-gates.md`
   with the signed packet/report paths and checkbox date.
2. Run the matched `n>=24` GLM patch-review confirmation or the approved
   `P-REV-1` reviewer protocol using the signed hard-accept row ids and oracle
   notes.
   For `P-REV-1`, the direct runner must be launched with
   `--measurement-protocol p_rev1`, `--protocol-attestation <attest-id>`, and
   `--accept-control-signoff-report docs/data/glm52_ccrab_accept_control_n24_signoff_report_20260719.json`.
   Without those explicit inputs it remains observation-only or refuses
   execution.
3. Keep the known GLM serving constraints in the run record: chat channel,
   JSON schema where applicable, no raw `/completion` role claim, explicit
   prompt-token count, and the next-power-of-two `glm-dsa.attention.indexer.top_k`
   schedule (`2048`, `4096`, `16384` for the tested prompt bands).
4. Treat all pre-`P-REV-1` FA/FR/ECE/AUC values as observation-grade unless the
   approved protocol and signed controls make them decision-gating.

`P-REV-1` did not clear GLM reviewer quality. Synthetic GC-1/2/3 repair smokes
and exact-answer CruxEval evidence still do not substitute for patch-review
admission.

## Subsequent Native-GLM-MTP Gates

Native GLM-MTP is no longer the reason GLM is blocked for reviewer admission.
It is repaired enough to provide acceleration evidence, but reviewer routing
still depends on patch-review quality:

- Already closed: source/tensor contract scoping for GLM-5.2 `blk.78` NextN
  tail tensors, single-NextN `glm-dsa` MTP graph scaffold, build/test smoke, and
  bounded same-model draft-MTP smoke. These are scaffold feasibility, not alpha,
  quality, or throughput evidence.
- Still open for production use: numerical/coherence gate on real
  generated-token volume with live speculative counters.
- Still open for production use: native-GLM-MTP A/B for alpha, acceptance, task
  quality, and throughput with enough generated tokens to measure honestly.
- Do not claim multi-head/general GLM-MTP support from the current scaffold; the
  2026-07-19 contract audit only supports a single-NextN implementation.

For v7 promotion, the old coupled gate order was:

```text
GC-shadow-repair4b.2b hard accept-control signoff
  -> P-REV-1 reviewer quality
  -> native GLM-MTP alpha/quality/throughput
  -> v7 READY FOR OPERATOR PROMOTION
  -> STOP for operator-authorized cutover
```

That order is superseded. No agent should promote GLM to production reviewer
status, sign as operator, or cut over the production kernel from this runbook
alone.
