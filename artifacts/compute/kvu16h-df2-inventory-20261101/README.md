# KVU-16h DF2 E2E source inventory, 2026-11-01

These exact source snapshots came from `/mnt/raid0/llm/tmp/v11-fa-ab-20261004/df29/`. Hashes were independently rechecked against the inventory and review before copying. They are historical evidence; do not execute them as a new row.

In the inspected `df2_e2e.sh` lines 60–74, the no-draft batched benchmark is a separate process and omits `-md`. Lines 80–109 choose DFlash2 or target-only server mode, using `-md` only for DFlash2. On arm M fallback, a server-stop helper is called before target-only launch; source inspection does not establish that the stop completed. `df29_client.py` lines 87–95 builds a request without request-level speculative parameters, and lines 159–169 send that body in concurrent mode. No `n_max: 0` mixing is apparent in this one inspected source path.

This is not a runtime proof, a global inventory, a general guard, or a matched no-draft versus drafted server comparison. The original search had inaccessible-path uncertainty. No compute was run.
