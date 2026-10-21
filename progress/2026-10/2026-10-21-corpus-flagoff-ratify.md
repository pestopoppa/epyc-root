# 2026-10-21 — corpus-flagoff-ratify

- Prepared the operator ratification package that switches corpus retrieval OFF in the frozen registry (index deleted 2026-07-04, CPL-4/5; operator approved the fix 2026-10-21).
- Finding: the orchestrator `orchestration/model_registry.yaml` is a COMPILED copy of the research master (`epyc-inference-research/orchestration/model_registry.yaml`), and descriptors / stack_priors / the summary are derived too. A lean-only edit would be reverted at the next `orchestrator_stack.py start`. So the change is two lane commits: master (research) + regenerated derived layer (orchestrator, via `stack_change_pipeline.py update`).
- Master carries 7 role blocks with `corpus_retrieval: true` (5 live in the lean view), not 4; all flipped.
- Two `test_registry_loader.py` assertions pinned the old ON state; updated to OFF.
- Lanes: research `lane/corpus-flagoff-research-20261021`, orchestrator `lane/corpus-flagoff-orch-20261021`, root `lane/corpus-flagoff-root-20261021`. Nothing pushed to any main by the agent except the root ratifier+note.
- Ratifier: `scripts/operator/ratify_corpus_retrieval_off_20261021.sh` (`--dry-run` / `--apply --attest RATIFY-CORPUS-RETRIEVAL-OFF-20261021` / `--verify`). Inert until the operator runs it.
- Handoff note filed under CPL-5 in `handoffs/completed/corpus-augmented-prompt-lookup-revalidation.md`.
