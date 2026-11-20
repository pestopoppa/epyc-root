---
schema: epyc.brief.v1
id: JEV-3
box_text_sha: e33a6290dc6da729
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/coordination/rowflow/publish_row.py::_UNIT_RE
- epyc-root:scripts/coordination/handoff_sessions.py::ADV_RX
- epyc-root:scripts/coordination/handoff_sessions.py::work_state
- epyc-root:scripts/coordination/churn/typed_classify.py
- epyc-orchestrator:src/typed_decisions/__init__.py
approach: 'typed_classify.py already wraps the native path with a regex fallback (7b2b40b42 kept, uncalled for work_state).
  First re-run the replay of saved dryrun/*/FAIL-*.json with the SERVED worker model (1.5B replay was unusable), then wire
  work_state to the typed label and delete _UNIT_RE/ADV_RX/OWN_TASK_RX and the UNKNOWN-FAILURE-CLASS fall-through. Done-when
  has no runnable form in the box; acceptance is the closest check: regexes gone + typed tests green.

  '
acceptance: '! grep -nE ''^(_UNIT_RE|ADV_RX|OWN_TASK_RX) *='' scripts/coordination/rowflow/publish_row.py scripts/coordination/handoff_sessions.py
  && python3 -m pytest -q scripts/coordination/tests/test_churn_typed_classify.py'
non_goals:
- no new accuracy study; replay is a regression check only
- do not call the 1.5B model
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/rowflow/publish_row.py: f71787bda4ff97f509d88afd008069379d1d6500
    epyc-root:scripts/coordination/handoff_sessions.py: 579fe838cd5550a673e74a62509c4421a636f1fd
    epyc-root:scripts/coordination/churn/typed_classify.py: 8f430cb8457279d943bd713b9510ef145353db8f
    epyc-orchestrator:src/typed_decisions/__init__.py: fa8ab740e33e481341d1c514804f54c932a81855
---
