---
schema: epyc.brief.v1
id: EV-DATE-PIN-1
box_text_sha: t:cb341cb1fcc3d06c
author: intake
written: '2026-11-25'
accepted: owner
where:
- epyc-orchestrator:scripts/validate/template_provenance.py
- epyc-orchestrator:tests/unit/test_template_provenance_bytes.py
approach: 'Scan the effective template bytes that build_row already hashes for the three tokens; emit the boolean in the plan
  row so apply_registry_integrity_pins.py carries it. The warning lives in the registry validator. Today''s served templates
  read no date (dive M1 checked the pinned 27B/A3B, Q38FN, deepseek-v41 and Gemma templates), so the expected first result
  is all false; the guard stops a future template from reintroducing a wall-clock variable silently.

  '
acceptance: .venv/bin/python -m pytest -q tests/unit/test_template_provenance_bytes.py
non_goals:
- No eval rerun; no change to served templates.
tier: local
grounded:
  at: '2026-11-25'
  blobs:
    epyc-orchestrator:scripts/validate/template_provenance.py: a27b454474533ae5975c773c3ef76e9d8a3bc914
    epyc-orchestrator:tests/unit/test_template_provenance_bytes.py: c89af19f77ec432871334e2532c271e36f8eef08
---
