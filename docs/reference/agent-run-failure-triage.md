# Agent-run failure triage labels

Adopted 2026-10-06 from intake-1332#03, with non-exclusive descriptive labels:

| Label | Observed symptom |
| --- | --- |
| `contract_format` | Output or action violates the required contract or format. |
| `tool_recovery` | Tool use or recovery fails to progress after an observed error. |
| `evidence_grounding` | Conclusion or action lacks the evidence required by the task. |
| `artifact_commitment` | Required artifact is absent, uncommitted or not preserved at the task boundary. |
| `state_continuation` | Task state or continuation is lost or incorrectly resumed. |

The closed metadata contract is `execution_alignment_labels: list[enum]` with the five values above, unique entries, and `classification_status: classified | unknown`. A classified empty list means a reviewer found none applicable. An unknown record carries an empty list and means insufficient evidence or no review; it must never be counted as a classified failure with no symptoms. More than one label may apply. Preserve the supporting native record reference and reviewer provenance when records support labeling. This adoption adds no automatic transcript classifier, scores, thresholds or measurement warrant.

The runtime `ErrorCategory` enum in APP `src/orchestration/escalation.py` at `be8d46f61edcf5cb795d485b1a8171c562ee4971` remains distinct: CODE, LOGIC, TIMEOUT, SCHEMA, FORMAT, EARLY_ABORT, INFRASTRUCTURE, UNKNOWN. It governs escalation/retry behavior; these triage labels do not replace it.

[MHS-5](../../handoffs/active/promptforge-mutation-safety-contract.md) supplies a held-out contrastive failure-trajectory corpus that can consume this vocabulary as descriptive metadata. Label membership does not establish patch safety or a corpus outcome grade. No source rates or efficacy claims are adopted. Future writer implementation must enroll its native source and preserve unknowns before capture.
