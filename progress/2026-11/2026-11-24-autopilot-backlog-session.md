# 2026-11-24 autopilot backlog session

## Wrap-up (operator /wrap-up)

- Landed overnight (details in `2026-11-23-autopilot-backlog-session.md`): AP-LH-WHOLE-TRAJECTORY-CAPTURE (orch `4c07ffd5`, ticked) and the AP-ALFWORLD-SUITE adapter (orch `2a04aaf7`, rebased over the capture commit with both flags kept; box open until the live 5-episode slice after AP-POSTREBOOT-ALF-SMOKE).
- STACK-UP-RELOAD-QUEUE (`harness-program.md`): sub-bullet lists every orchestrator commit since 2026-11-20 that the next API-only reload ships (sampler tap, BSV-2 gate, distill, capture, ALFWorld suite). The capture flag needs the API side on too.
- Checks: index --check rc=0; belief ledger fresh (lag 0); no prune candidates. Research README still 60 days stale: waiting on the operator's manual fix of the broken `../../MEASUREMENT.md` link (Edit hook 20 refuses every edit to that README while that link is broken).
- Open operator choice: ALFWorld slice inside or outside autopilot's keep/revert aggregate (built outside).

## Session wrap-up (late)

Orchestrator commits (all new runtime behaviour default OFF, queued for the next API reload in `handoffs/active/harness-program.md`):

- `ffa410f1`, `dba27980`, `d319438a`: compaction ledger, replayed on 62 real traces.
- `87ac9115`: context_fold_digest.
- `18e2100d`: scorer_fuzz + judge_fpr_audit.
- `4110ed1c`: scorer v2 `strict_finals_v2_20261124`. P-PAIRED McNemar flips v1 p=0.855 to v2 p=0.0129 (a_better), n=1583.
- `a8c49312`: launder lint.
- `5b7e2100`: reviewer flips.
- `286fd797`: chat_finish_reason, truncation_narrowing_hint, http_post_guard.
- `9079993b`: drops manifest + token_span_ratio.
- `353cb5e0`, `ceb93ff3`: usage_root_capture.
- `60edb5d4`, `46f2fc46`: delegation_untrusted_data_field.
- `ec0ba432`: EV-CONF-2 sample_manifest_v2 (0 exact_match flips).
- `42196fe2`: serving_calls_json_schema_capture.

Root commits: `15200074d` (Agents_intro intake-2907..2941), `d0c3a6a4a`, `7d4771fb9`, `747ced337`.

Pending operator, in order:

1. `scripts/operator/ratify_scorer_semantics_v2_era_20261124.sh` (E21 scorer-era ratify).
2. `/mnt/raid0/llm/tmp/rerun-arm-amendment/ratify_aei_rerun_arm_20261124.sh`.
3. `/mnt/raid0/llm/tmp/ppaired-v2-amendment/ratify_ppaired_v2_20261124.sh`.
4. Remove rehearsal worktrees `ppaired-dry`, `-a`, `-b`, `-c`, `-d` and branch `ppaired-dry-d`.

Open issue: v1 AUROC 0.4373 versus the recorded 0.4013 is unexplained.

Post-stack-up items: judge FPR live run, token span ratios, KV-EVICT-COST-1/2, API reload.

Next: operator (ratify scripts above); autopilot-backlog-session owns the post-stack-up items.
