---
schema: epyc.brief.v1
id: RTG100-HS-C6-DROP
box_text_sha: 2289290143de44b1
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/handoffs/stale_next_action.py::compare_generated
- epyc-root:scripts/handoffs/index_state.py
approach: 'Time/data-gated: stale_next_action.py --compare-generated records a daily sample to the C6 ledger; criterion C6_DAYS=7
  days at C6_AGREE>=0.90 (first sample 86.7%, not met). When it reports the drop verdict (exit 0), delete the hand-written
  index rows via the owning session (rows are applied by the owner, never a subagent). Acceptance is the box''s own command;
  it exits non-zero until the criterion holds, and running it appends one ledger sample.

  '
acceptance: python3 scripts/handoffs/stale_next_action.py --compare-generated --quiet
non_goals:
- do not lower C6_AGREE or C6_DAYS
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/handoffs/stale_next_action.py: 246b76e65c5c165abcd3c8c54584a1ff806f3f8b
    epyc-root:scripts/handoffs/index_state.py: 9c92d0e6739b383fc78a4a1ca38728303f202a46
---
