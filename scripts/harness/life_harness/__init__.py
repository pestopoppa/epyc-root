"""Glue around the upstream Life-Harness evolve-from-scratch run (AP-POSTREBOOT-LH-RIGOR).

Nothing here edits the upstream clone. The modules split into three layers:

* ``rigor`` / ``plan`` / ``rounds``: pure, dependency-free R1-R5 accept enforcement
  (AP-BSV2-ACCEPT-RIGOR) and the per-round controller, testable with fakes.
* ``proxy`` / ``conformance``: loopback OpenAI-compatible proxies and the improver
  conformance replay (LH4a / LH4c).
* ``run_alfworld`` / ``cli``: the only modules that import upstream code, lazily.
"""
