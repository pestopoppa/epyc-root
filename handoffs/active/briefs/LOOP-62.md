---
schema: epyc.brief.v1
id: LOOP-62
box_text_sha: t:30b14a416639d001
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-orchestrator:src/__init__.py::_InferenceLockAliasFinder
- epyc-orchestrator:src/dispatcher.py
- epyc-orchestrator:tests/unit/test_inference_lock_concurrent_import.py@5886e5aeb273fd4a8aaf1447bb3d8bc163d5c082
- epyc-orchestrator:tests/unit/test_inference_lock_concurrent_import.py
approach: >-
  Recreate tests/unit/test_compat_alias_cold_import.py from
  5886e5ae:tests/unit/test_inference_lock_concurrent_import.py (git show), keeping _COMPAT_ALIASES (16 entries),
  test_compat_alias_is_the_unrenamed_target_module and test_all_compat_aliases_concurrent_first_import_is_safe.

  Fix: in src/__init__.py, generalize _InferenceLockAliasFinder/_InferenceLockAliasLoader to one finder keyed on
  that same dict; create_module returns importlib.import_module(target).

  Reduce each shim file (src/dispatcher.py etc., which today set _real.__name__ = __name__ and swap sys.modules
  from their own body) to a docstring only, so the finder is the only path and the target is never renamed.

  Keep the inference_lock behaviour and its two existing tests unchanged.
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_compat_alias_cold_import.py tests/unit/test_inference_lock_concurrent_import.py
new_tests:
- epyc-orchestrator:tests/unit/test_compat_alias_cold_import.py
non_goals:
- do not rename or move any target module under src/runtime, src/orchestration, src/inference or src/registry
- do not edit callers to drop the old alias imports
- do not reduce the stress parameters (24 threads, 20 subprocesses) to make it pass
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/__init__.py: ff893046a8e7d2598657b950e9e41449f358d25f
    epyc-orchestrator:src/dispatcher.py: 4834a7fbdf26d2f57ab39cb8e5d5aa3be58dbc54
    epyc-orchestrator:tests/unit/test_inference_lock_concurrent_import.py@5886e5aeb273fd4a8aaf1447bb3d8bc163d5c082: 047b6a5a9e1937897f42c45ce1ad049a2337ceeb
    epyc-orchestrator:tests/unit/test_inference_lock_concurrent_import.py: 2e5dd9fecafedc6c2ba616be0815f64c64a4b1ad
---
