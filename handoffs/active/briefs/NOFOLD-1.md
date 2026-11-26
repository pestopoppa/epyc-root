---
schema: epyc.brief.v1
id: NOFOLD-1
box_text_sha: t:3f033531d18aa7b3
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:docs/reference/kernel-manifests/README.md
- epyc-root:.claude/skills/kernel-promotion/SKILL.md
- epyc-root:docs/reference/kernel-manifests/llama-v11-manifest.md
approach: >-
  In docs/reference/kernel-manifests/README.md, add a section '## NO-FOLD list' directly after '## Rules
  (operator directive 2026-10-20)' (before the 'Production trees stay frozen' line is fine) with two bullets
  copied from the box: (a) feature/tree-draft-v6 must not fold, because the champion carries a later
  contradicting decision; (b) inf70/sync17-fix2 @ 2516c9807 and inf70/retest1-fix1 must not fold as-is:
  GGML_SCALE_SPLIT and GGML_SOLO_YIELD_ROWCOL default ON is the -2.136% regression, so flip both OFF first;
  retest1-fix1 is a measurement instrument, not a lever.

  In .claude/skills/kernel-promotion/SKILL.md, in the 'Presence gates first' paragraph (~L196-199), add one
  sentence: no branch on the NO-FOLD list may enter the candidate, linking ../../../docs/reference/kernel-
  manifests/README.md#no-fold-list.

  Preserve the existing README text, including its final production-freeze paragraph. Insert the new section
  once and retain exactly one existing Rules heading and its five rules.
acceptance: grep -q '^## NO-FOLD list' docs/reference/kernel-manifests/README.md && grep -q 'GGML_SOLO_YIELD_ROWCOL' docs/reference/kernel-manifests/README.md
  && grep -q 'feature/tree-draft-v6' docs/reference/kernel-manifests/README.md && grep -q 'kernel-manifests/README.md#no-fold-list'
  .claude/skills/kernel-promotion/SKILL.md && grep -Fq 'Production trees stay frozen; the manifests are read-only analysis documents and never authorize a build or a branch switch in a frozen tree.' docs/reference/kernel-manifests/README.md && grep -c '^## Rules (operator directive 2026-10-20)' docs/reference/kernel-manifests/README.md | grep -qx '1'
non_goals:
- do not touch any kernel branch, build or the frozen llama.cpp tree
- do not edit manifest table rows in llama-v11-manifest.md
- do not reword other promotion steps
- do not remove existing README text or duplicate its Rules section
tier: local
grounded:
  at: '2026-11-26'
  blobs:
    epyc-root:docs/reference/kernel-manifests/README.md: 01373c382dba86c6935e30477fbd51c84880d58c
    epyc-root:.claude/skills/kernel-promotion/SKILL.md: f49ef6dd9938ef2bb03627d797aebcd79d2cc8ce
    epyc-root:docs/reference/kernel-manifests/llama-v11-manifest.md: e41a47bc6bb79ed499fba085549b233ac9385b7f
---
