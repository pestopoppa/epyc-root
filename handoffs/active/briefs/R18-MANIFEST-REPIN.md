---
schema: epyc.brief.v1
id: R18-MANIFEST-REPIN
box_text_sha: 0c1f422bf248977e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/producers/r18_inputs/comparator-dependencies.json
approach: 'Review the drift in comparator-dependencies.json (schemas.py changed 11-06; /usr/bin/perl differs; /usr/bin/python3.13
  absent here) and re-pin deliberately before the next R18 capture: for each pinned path, recompute the digest, decide per
  item whether the drift is benign (then repin) or invalidates earlier captures (then record era boundary). No blind repin.

  '
acceptance: python3 -c "import json;json.load(open('scripts/vidya/producers/r18_inputs/comparator-dependencies.json'))"
non_goals:
- no blind digest bump
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/producers/r18_inputs/comparator-dependencies.json: 9744d49aa546f3c130998fe6953db1d20cafc2cd
---
