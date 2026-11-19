# NG5 provenance audit — 2026-11-02

This is a scoped source inventory, not a measurement or an NG5 completion. NG5 requires corpus and repeated-5-gram fraction beside every ngram observation in the handoff, research master registry and any quoting index row, plus the live-server replication and non-context-control rules. Do not transfer a fraction between different prompt sets or substitute a repeated-5-gram **count** for a fraction.

## Evidence boundaries

The research retraction at `epyc-inference-research/data/numa_placement/20260730-P-BENCH-PLACEMENT-1/RETRACTION-ngram-20260730.md` reports 6–17% repeated 5-grams for the screened real repository source/docs prompts in its retracted run, and 99.7% for the separately discarded synthetic-filler attempt. Neither range applies by default to another run. It attributes the warm-repeat artifact to a prior generated answer retained in context; prompt screening did not detect that contamination. Sample count and per-prompt numerator/denominator were not found in this retraction. The handoff's current replication rule calls for distinct prompts on a live server and a non-context-reading control; perfect acceptance triggers investigation rather than an automatic contamination finding.

The following observations are as recorded in the handoff; “not recorded” means in that handoff, not a finding that the original run lacked the information.

| Handoff observation | Corpus recorded there | Repeated-5-gram fraction recorded there |
| --- | --- | --- |
| NG1 / NG2 corrected and retracted observations; NG4 GPU sweep | Not recorded for those specific numbers | Not recorded |
| SR-3 composed recipe; SR-6 historical three-prompt width sweep; SR-7 122B observation | Not recorded for those specific numbers | Not recorded |
| T3 / T3c combined arm | `default+expanded` deterministic tasks | Not recorded |
| T5 512- and 1024-token runs | Not recorded | Not recorded |
| COPYSPEC-P1 | Code edits, RAG and general MCQ; MCQ is not a valid prose control | Not recorded by class |
| COPYSPEC-WIDTH | Code edits and reported 65-item set | Not recorded |
| COPYSPEC-SWEEP | Code edits, RAG and real prose | Not recorded by class |

## Research master registry working-copy inventory

Read-only snapshot: research HEAD `99301fa149af86a6f9743d2b0405c9234ba39586`, `orchestration/model_registry.yaml` modified in its own working tree, SHA-256 `af6c3308fa2b21c1ec0527d5e09a902914a73b629d7af81b3929abdaec74c765`. This is not an assertion about the committed version or permission to modify the shared working copy. The following fields contain numerical ngram observations without an adjacent corpus-specific repeated-5-gram fraction and need source-by-source provenance review:

- `speculative_decoding_policy.evidence_for_reversal`: `long_context_coding_35b`, `long_context_coding_gemma`, `ordinary_text`, and `retracted_positive`; `where_ngram_does_win` also describes multiple distinct fixtures.
- `task_class_spec_observation`, `historical_candidate`, `mi210_ngram_mtp_repetition_observation`, `mi210_ngram_mtp_prompt_diverse_observation`, `expanded_task_quality_observation`, `quiet_mi210_broader_task_ab`, and `ngram_gpu_smoke_observation`.

The gemma prompt-diverse native `compact_summary.json` under `data/k11_gemma4_determinism/k11_gemma4_mi210_prompt_diverse_20260719T004626Z/` records `repeated_5grams: 0` for the coding-explanation task in each of three arms. That field is a count, and this check did not establish its denominator or whether it measures prompt or generated output; it does not establish a prompt fraction. The registry's prose similarly reports that count, not a complete corpus fraction.

A text search of `handoffs/active/*index*.md` and `CURRENT-CAMPAIGN.md` for `ngram` found only the unrelated word “engram”; this is a limited same-text search, not proof that every index quote or alias is covered.

## Remaining work

Trace each registry observation and each handoff “not recorded” marker to its exact original corpus and rendered prompt evidence. Where recoverable, record sample count, repeated-5-gram numerator/denominator, fraction and range adjacent to the specific observation; otherwise retain explicit “not recorded”. Inspect all index references by task identity as well as spelling. Apply any master-registry edits through its owning source workflow, taking care of the existing uncommitted changes. Recheck the full NG5 scope and replication/control wording before considering its checkbox complete. Historical retractions and distinct recipes remain distinct; these records alone do not warrant a performance or deployment claim.
