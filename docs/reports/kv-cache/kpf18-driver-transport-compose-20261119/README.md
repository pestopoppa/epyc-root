# KPF-18 disabled full-driver transport composition

The composed full driver imports the corrected transport and all six of its
pinned dependencies before importing the actual retained controller and gate.
This fixes a composition defect found by the negative control: the receipt-backed
predecessor's vendor directory contains an older `native_task_log.py` that accepts
release before cancellation. Letting that directory win import resolution lost
the already-qualified ordering check. Explicit dependency binding preserves it.

The installer writes only a changed driver, the binding helper, a manifest and a
disabled launcher. All other inputs remain at their original paths, bound by
SHA-256; no tree, native binary, model or log is copied. Driver `BASE` still names
the inherited candidate so its recipe/protocol paths retain their meaning. Its
import output goes to an explicitly supplied existing scratch directory rather
than creating attempts in the predecessor. Both direct entries return 78.

Installed successor: `/mnt/raid0/llm/tmp/kvu/driver-transport-successor-20261119`.
`qualification.json` binds its manifest and changed driver by SHA-256.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s docs/reports/kv-cache/kpf18-driver-transport-compose-20261119 \
  -p test_composition.py -v
```

Five harness checks and fifteen child-process checks passed. The child imports
the entire installed driver, actual controller and gate. Eight consumer controls
execute the class captured by the actual controller, including ordered success,
release-before-cancel rejection, typed STOP and cleanup failure. Slots, SSE and
native log peers are synthetic. Main-function controls execute the full imported
driver with fake guard, preload, GPU witness and gate, testing normal ordering
and refusal. Other checks cover actual callable/module binding, changed-source
refusal, preloaded-module refusal, incomplete installation, destination refusal
and disabled direct entries. The controller's full construction loop and real
server lifecycle are not executed.

The old inventory also names OS utilities and native binaries. An attempted
whole-inventory check found `/usr/bin/flock` no longer matches its historical
digest. This package verifies the pinned Python import inputs and transport
dependencies, and retains the old inventory hash as provenance; it does not
assert current native execution custody. Refreshing execution dependencies under
current rowflow authority is still required before a scheduled native entry.

KPF-18.0d remains open. This closes full-driver import/transport composition only.
The original driver's broad exception handling, actual native cancellation and
release, owned server/descendant drain, current admission and GPU qualification
remain required before publication. No model, benchmark or GPU ran, and no
layout or historical-equivalence verdict follows. GitNexus reports no indexed
repository for this lane; graph blast radius is unavailable. All repository
changes are confined to this qualification package and the owning handoff note.
