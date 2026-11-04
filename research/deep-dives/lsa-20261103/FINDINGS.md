# D-LSA intake — approved filing

The operator approved the [Stage 3 plan](PLAN.md) on 2026-11-03. Its exact bytes remain the approval record; the checkpoint binds their SHA-256. Research records are intake-2622#record through intake-2627#record. Filing creates four implementation/evaluation tasks and one intake-validation repair task. No inference, kernel build, reload or production promotion is part of this filing.

## Evidence clarifications from final second-reader review

These clarify source wording and locators without changing the approved recommendations:

- In intake-2622#record, the relevant untested AMD target is MI210/gfx90a. The paper's NVIDIA measurements establish neither its correctness nor its performance. The plan's residual MI50/gfx906 example is not the target hardware.
- HashAttention describes top-k training labels, with 64 as an example, rather than an invariant top-64 rule. Its CPU-resident/ultra-long offload limitation is discussed in [§6](https://arxiv.org/html/2412.14468v2#S6). See intake-2625#record.
- The InfLLM-V2 training/model recipe is located in [§4.1](https://arxiv.org/html/2509.24663v1#S4.SS1), rather than the block-representation subsection. See intake-2626#record.
- MoBA's Llama continuation recipe is in [§3.3](https://arxiv.org/html/2502.13189v1#S3.SS3), and its 10M performance scaling evidence is in [§3.4](https://arxiv.org/html/2502.13189v1#S3.SS4). See intake-2627#record. Performance scaling is not 10M task-accuracy evidence.

All seed numerical claims and the derived KV arithmetic were checked against the raw paper/configuration evidence by a second reader. They remain author-reported results or explicit arithmetic, not local reproductions. The four expansion mechanisms were independently re-read. No independent performance replication was established by this run's bounded contradiction search.

## Execution posture

Qwen3.8-27B has released model-specific PCA/distilled maps. Qwen3.6-35B-A3B needs its own capture adapter and projections. Both transplants preserve Gated DeltaNet layers. Full KV storage remains necessary. The reference Qwen path's BF16-KV and speculation restrictions require separate integration work for our quantized-KV and DFlash2/MTP recipe.

The approved tasks live in the long-context, architecture-readiness, ROCm, belief-substrate and knowledge-pipeline owners. Existing indices already own these handoffs; no new rows or stubs are required. Tree and native-training follow-ons remain conditional prose, not unchecked backlog.

The scoped close-out checks are the exact approved-payload intake validator, handoff index regeneration/check, digest generation/check and wiki scanner discovery. Scanner discovery does not mark the sources compiled.

## Filing validation

The scoped validation repair is complete: 53 regression tests plus 16 subtests passed, and the full exact-plan/checkpoint validator accepts all 2,623 entries. The handoff index check reports zero problems. The six-entry dive digest is current, and the scanner discovers the approved plan, these findings and the digest. Four implementation/evaluation tasks remain open; the validation-repair task is checked complete. No model inference was run.
