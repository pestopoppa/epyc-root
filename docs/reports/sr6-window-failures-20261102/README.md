# SR-6 first two windows: launch failures, 2026-11-02

Rows `sr6-qwen36-width-w1-20261102` and `sr6-qwen36-width-w2-20261102` both ended rc 1 before their worker ran. The retained native launcher logs show the pinned `region_lock_cli.py` integrity check failed. Their declared result files were absent, so both outcomes were filed **inconclusive** under their window rules; SR-6 remains open. No throughput, acceptance, or registry claim follows.

The sealed input list expected `region_lock_cli.py` SHA-256 `58c2ea675db751f7403222ebbb3d6e52a4ce151ade86035e00fddda411b69940`; the live shared working file at diagnosis hashed to `2414c8bce6722026ab48e0794b213b7e38f9d4c92a1339bce78f03d8f3639882`. Its tracked working diff added a smoke/dry-run-only bypass. The checksum guard correctly refused the changed input. A successor must seal the actual input again and still fail closed if it changes; a smoke pass is not a native measurement.

Native terminal evidence: [W1 launcher](w1-launch.log), [W1 end](w1.ended), [W2 launcher](w2-launch.log), [W2 end](w2.ended). The shared output root and all retained exposures must be consulted before any retry; absence of a result alone is not proof that prompts were untouched.
