# Operator decisions for the refactoring program (2026-10-24 ~19:55 UTC, via AskUserQuestion)

1. Evaluator regime: BATCH INTO ONE ERA EVENT. Land all evaluator fixes (eval_tower.py, rubric_scoring.py,
   src/autopilot_core/tier_specs.py, orchestration/eval_registry.yaml) plus an AST-normalized evaluator
   fingerprint, on the branch. Merging/deploying is the single AP-55 regime break; the operator picks the time.
2. AutoKernel prune: DELETE ALL THREE unreachable planes (unified/standalone control plane; discovery_*/gpu_source_*
   stack; release/ plane), "but make sure that you're current with main": rebase onto the latest origin/main
   before starting and again before review, and re-prove unreachability from the live entry points at that HEAD.
3. CI: ADD ORCHESTRATOR CI (pull_request + workflow_dispatch only) + REPAIR the AutoKernel guards workflow
   (operator re-enables it in GitHub).
4. Scope: FULL PROGRAM, PACED (decompositions included, behind behavioural tests; ~2 concurrent agents;
   no overage credits on the account, so work spans several 5-hour usage windows).

Earlier standing inputs: hermetic tests approved (2026-10-07); keep an eye on code-size bloat (2026-10-07);
peer-relayed operator rule (2026-10-24): kernel (llama.cpp) defects go to the champion fold (CH-xx in
epyc-root handoffs/active/autokernel-champion-aggregate.md), not production patches.
