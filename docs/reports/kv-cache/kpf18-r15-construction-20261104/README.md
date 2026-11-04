KPF-18 group-3 native construction qualification (2026-11-04)

R15 inspection
- Preserved original result: /mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-native-control-r15/out/conformance/VERDICT.json remains INVALID (3 attempts, 0 accepted, 1 load, 0 same-load controls, no program closure).
- The retained C1 seed event records 016/024/032-C1-attempt{1,2,3}-full32512-seed.event.json each show `AttributeError: module 'kpf18_gate' has no attribute 'pid_owns_port'`. This was the immediate cause of bounded construction exhaustion before the full-prefix request reached HTTP/native work. Since C1 never completed, C2/C3 and the declared arm sequence were absent; no layout verdict can be derived.

Repair/qualification
- Private successor implementation: /mnt/raid0/llm/tmp/kpf18-g3-repair-successor-20261029/candidate/vendor/cancel_seed_transport.py. `SeedControl` now calls its local `pid_owns_port()` listener/PID verifier instead of the missing helper on `kpf18_gate`.
- Focused test: `PYTHONDONTWRITEBYTECODE=1 python3 -B -I /mnt/raid0/llm/tmp/kpf18-g3-repair-successor-20261029/candidate/test_ownership.py`
- Result: PASS — exact loopback listener accepted; wrong PID and bound-only listener rejected; actual seed entry advanced to the slot precondition; foreign address and dead process rejected. This was a CPU-only local-socket test; no model/server/GPU/claim was started and no files were created by the test.
- SHA256 transport source: 95ea82faece95847abceb3eab1c36b52bcd244faa4db5477ec6983f0bf4f513f
- SHA256 focused test: 4153be840f0f48224a533c6ca14906bd98dcd974b504a7c4d58dbbefd2394175

Handoff update
- Added this limited diagnosis and qualification to handoffs/active/kv-cache-program.md under the R15 results, explicitly preserving R15 INVALID and the still-open group-3 control.

Scope boundary
- This only qualifies the local server-ownership check. It does not validate cancellation, C1 construction, arm ordering, raw-data custody, a native control, GPU admission, a layout comparison, or KPF-18 item-3 closure. The private candidate launcher/job remains fail-closed per its PREPARATION.md; no native/GPU execution is ready or asserted.
