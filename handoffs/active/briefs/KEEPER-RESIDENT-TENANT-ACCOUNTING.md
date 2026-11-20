---
schema: epyc.brief.v1
id: KEEPER-RESIDENT-TENANT-ACCOUNTING
box_text_sha: 373321a99eed998b
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/coordination/rowflow/rowflow.py::vram_used_bytes
- epyc-root:scripts/coordination/rowflow/run_direct.py
- epyc-root:scripts/coordination/tests/test_rowflow.py
approach: 'Rows may declare resident_after (tenants left resident, e.g. embedder_gpu). Keeper keeps a resident-tenant table
  with declared VRAM; GPU admission budget = total VRAM minus declared residents; GPU rows run while a resident exists get
  a measured_with_resident tag copied to their result so timing rows are labelled. Needs D9-ack (keeper side). Box has no
  done-when; acceptance is the closest check.

  '
acceptance: grep -q resident_after scripts/coordination/rowflow/rowflow.py && python3 -m pytest -q scripts/coordination/tests/test_rowflow.py
non_goals:
- do not evict residents automatically
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/rowflow/rowflow.py: 5e76c90af8cfa49c863684663c3ca56084adfa8d
    epyc-root:scripts/coordination/rowflow/run_direct.py: 1201d4213f6e106f6ccf172c6c95f3f7d68366bc
    epyc-root:scripts/coordination/tests/test_rowflow.py: 78e91e9f387bc36c68c48333f25760dabd0e9c2c
---
