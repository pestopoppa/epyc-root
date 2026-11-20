---
schema: epyc.brief.v1
id: ROWLINT-DECLARED-THREADS-IGNORED
box_text_sha: ace70528331182f4
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/coordination/rowflow/rowflow.py::launcher_threads
- epyc-root:scripts/coordination/rowflow/publish_row.py
- epyc-root:scripts/coordination/tests/test_rowflow.py
approach: 'Take the second option in the box: keep launcher_threads as the only width evidence (rowflow.py L1722 says declared/measured
  threads are never width evidence) and change the refusal text to ''declared_threads is not evidence; put -t N / OMP_NUM_THREADS=N
  in launch.sh''. Do not honour declared_threads. Add a test in test_rowflow.py for a runtime-computed -t launcher. Box has
  no done-when; acceptance is the closest check.

  '
acceptance: grep -q 'declared_threads is not evidence' scripts/coordination/rowflow/rowflow.py && python3 -m pytest -q scripts/coordination/tests/test_rowflow.py
non_goals:
- do not loosen the thread-evidence rule for timing rows
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/rowflow/rowflow.py: 5e76c90af8cfa49c863684663c3ca56084adfa8d
    epyc-root:scripts/coordination/rowflow/publish_row.py: f71787bda4ff97f509d88afd008069379d1d6500
    epyc-root:scripts/coordination/tests/test_rowflow.py: 78e91e9f387bc36c68c48333f25760dabd0e9c2c
---
