---
schema: epyc.brief.v1
id: CF-AB-A7-SURFACE
box_text_sha: 14315a4ebdac6dc0
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/context-and-token-economy.md
approach: 'Edit the A7 bullet of the CF-AB-1 addendum in place: name grep_history plus peek over session.verbatim.md as the
  tool surface (log format, 10/page up to 30, 6K response, 300-char clip), add a generic bare-search control arm, and an inline-versus-pointer
  delivery check as precondition to any pass-rate claim. Text edit only.

  '
acceptance: grep -Eq '^ +- \*\*A7, .*grep_history.*bare-search' handoffs/active/context-and-token-economy.md
non_goals:
- No arm is run; UTM-B2-GREP-HISTORY code is separate
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/context-and-token-economy.md: 55a59d4e87cf3920d424f3fb6d879a3b4d8a3801
---
