---
schema: epyc.brief.v1
id: SKILL-PAIR-COMPAT-REPLAY
box_text_sha: t:ffd84af23b10ba50
author: intake
written: '2026-11-27'
accepted: auto
where:
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3017.md
- epyc-orchestrator:orchestration/repl_memory/replay/skill_replay.py
approach: 'Local skills are text/tool bundles, whereas the source trains continuous prompts. The existing null replay records
  single-task effects. Freeze model, executor, evidence and cost ceiling. Compare both orders, shuffled partners, constituent
  controls and explicit two-step intermediate on held-out tasks. Record stale skills, tool failures, invalid completions,
  abstentions and additional compute. Reopen admission policy only for effects surviving shuffled labels and cost-matched
  controls.

  '
acceptance: Freeze model, executor, evidence and cost ceiling. Compare both orders, shuffled partners, constituent controls
  and explicit two-step intermediate on held-out tasks. Record stale skills, tool failures, invalid completions, abstentions
  and additional compute. Reopen admission policy only for effects surviving shuffled labels and cost-matched controls.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3017.md: d836e5a9d0baff93f35ac37acfe6eb26a30e6550
    epyc-orchestrator:orchestration/repl_memory/replay/skill_replay.py: 9cdcfa0b26666793d2d905bfeb31c740f633c290
---
