# RTG-39 experience-data contract

This inert field contract keeps recorded experience separate from generated teacher targets. It defines types and provenance only; it contains no records, examples, synthetic values, inference outputs, or training instructions.

Source: [Experience Distillation, arXiv v1](https://arxiv.org/html/2607.21051v1). Owning scope: [RTG-39 blocked handoff](../../handoffs/blocked/swarm-dataset-distillation.md).

## Source-grounded construction levers

- **Hindsight-conditioned history:** retain the ordered attempt lineage and a reference to the preprocessed history supplied as teacher context, with its preprocessing implementation/version.
- **Enhanced teacher reasoning:** pin the prompt template/version used for target generation. The teacher remains frozen while generating targets; the student is separately identified as trainable for SFT.
- **Branch packing:** retain the packing group and ordered member lineage. A later target may condition on prior generated targets, while each subsequent observation remains the actual recorded observation after the original action.

## Record shape

One record represents one teacher target at a recorded decision branch point. Keep the original state/action/observation provenance separate from the generated target.

| Field | Type | Meaning |
|---|---|---|
| `source_ref` | required object | Source dataset or experience reference, source/license identifier, immutable source revision, and source record key. |
| `attempt_lineage` | required array of objects | Ordered attempt identifiers and references to the actual recorded context/experience used by the teacher. |
| `verifier_outcomes` | required array of objects | Verifier identity/version and observed outcome attached to a corresponding recorded attempt; empty is distinct from pass. |
| `preprocessed_history_ref` | required object | Immutable reference plus preprocessing implementation/version for the teacher context. |
| `teacher` | required object | Checkpoint reference, `parameter_state: frozen` during target generation, and prompt-template/version reference. |
| `branch_point` | required object | Reference to the recorded state/context at which the teacher decision is generated. |
| `recorded_action` | required object | Action actually taken in the source experience, with source event reference. |
| `recorded_observation` | nullable object | Observation actually recorded after that source action, with source event reference. Null means the source contains no such observation; do not synthesize one from a teacher target. |
| `generated_target` | required object | Teacher-generated decision/target and generation provenance. Keep its environment-verification status explicitly `unverified` until an actual verifier observes an outcome; generated text alone is not an observed result. |
| `student` | required object | Initialization checkpoint reference and `parameter_state: trainable` during SFT; its input contract excludes the experience context used to generate the target. |
| `loss_mask_ref` | required object | Immutable reference to the mask selecting target tokens for the training loss. |
| `packing` | required object | Packing group/reference and ordered member references; preserves the distinction between source observations and prior generated targets used as later context. |
| `split_group` | required string | Stable task/repository grouping key used to keep related examples in the same evaluation split. |

## Invariants

- Teacher and student roles are distinct: teacher parameters are frozen for target generation; student parameters are trainable during SFT.
- Teacher context may include preprocessed prior experience; student input does not include that experience context.
- Recorded source action and any recorded following observation retain their original provenance. A missing observation remains null; generated targets never create observations.
- A one-step branch ending at a teacher decision has no environment observation unless one is actually recorded by the source or a verifier.
- Packed sequences identify prior generated targets separately from recorded subsequent observations; packing is an approximation and must not rewrite source history.
- Missing source/license, verifier, prompt, split, mask, or lineage information remains absent/unknown, not inferred from generated text.
- This contract adds no protocol, acceptance threshold, source grade, ClaimTuple, or change to the Strand Phase-B/P1–P5 gate.

## Prospective producer wiring

This document produces no dataset or measurement. Before implementing a teacher-target or dataset producer, enroll its native output source in `scripts/vidya/adapters/README.md` and its write-side hook in the Vidya handoff. Retain actual source, teacher/student, prompt, split, verifier and output identities at write time; reuse the existing ClaimTuple projection and shared grade.
