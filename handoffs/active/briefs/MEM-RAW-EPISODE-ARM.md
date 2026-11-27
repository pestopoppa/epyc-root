---
schema: epyc.brief.v1
id: MEM-RAW-EPISODE-ARM
box_text_sha: t:08972e20cbec85a9
author: intake
written: '2026-11-27'
accepted: auto
where:
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3018.md
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3024.md
- epyc-orchestrator:src/graph/compaction.py
approach: 'Current externalization and BEAM reader controls permit adding a raw-episode retriever without changing live memory
  writes. Use identical conversations, raw turns, parser version and token cap. Compare lexical/hybrid, exact mentions, released
  first-mention heuristic and dependency/alias gated edges. Record raw episode IDs, all-gold recall, time/order failures,
  build and query wall time measured externally. Promote only if held-out evidence recall or answer quality improves without
  exceeding the cost ceiling.

  '
acceptance: Use identical conversations, raw turns, parser version and token cap. Compare lexical/hybrid, exact mentions,
  released first-mention heuristic and dependency/alias gated edges. Record raw episode IDs, all-gold recall, time/order failures,
  build and query wall time measured externally. Promote only if held-out evidence recall or answer quality improves without
  exceeding the cost ceiling.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3018.md: 5f6124efc39b635e807aa3aec0d52bd7dfaeae64
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3024.md: 1a606c2fb4582ea74c5090bde7ebc65f33193ae6
    epyc-orchestrator:src/graph/compaction.py: ccecf4da2a308dadd6ec5dd262135dff40bb0bd4
---
