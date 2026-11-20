# CPU P9 output-path preflight repair — 2026-11-20

The scheduled CPU P9 row `df2-cafe3-p9-cpu-20261119` exited rc1 before
model launch. Its retained poller stderr ends at `multi_arm.prepare`'s
`output must be new canonical path outside inputs` guard. The runtime constructs
`capture_path = work / 'schedule-capture.jsonl'` as a `pathlib.Path` and passes
it directly to `multi_arm.execute`. The guard compared `str(output) == value`;
for the first output, `value` was still a Path, so this was always false.

`scripts/diagnostics/cafe3-adaptive/multi_arm.py` now applies `os.fspath` to
the result argument at its API boundary. It preserves the original spelling;
it does not resolve away traversal or symlinks. Declared schedule outputs and
all canonical, exclusive, collision and input-overwrite checks remain enforced.
Both CPU and HIP callers use this shared boundary.

Validation: **13 model-free schedule tests PASS**, including Path-valued
successful execution with mocked model processes, input/collision refusals,
and existing-file/dangling-symlink refusals for Path-valued results. Command:
`python3 -m unittest discover -s scripts/diagnostics/cafe3-adaptive -p test_multi_arm.py -v`.

An offline replay of the retained five-arm `native-6vdhxryh` schedule also
passes `prepare` with the actual Path-valued capture argument. The expired,
reaped grant is reconstructed only in memory, with lifecycle/time/affinity
mocked; source/build/input/request validation runs normally. This replay
neither writes a grant nor launches a model. It establishes API compatibility,
not admission under a future live grant or a native P9 verdict.

Evidence is retained in place (SHA-256):

| File | SHA-256 |
| --- | --- |
| `scripts/diagnostics/cafe3-adaptive/multi_arm.py` | `b7d9a87f87cbe1dfdd7a014a412c10983e41eab687dcdc4af4ececa3c357e962` |
| `scripts/diagnostics/cafe3-adaptive/test_multi_arm.py` | `72f2b513a814e607287d49179ad4ed1f896ae33159aeaa1e6d27de49da5e1c91` |
| `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe3-p9-cpu-20261119/poller.out` | `5aed55f7e2b9ddd482fa9b1ca96143a346a2539d93c1dd273453d09d63920f67` |
| `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/runtime.py` | `86301fd05cd714fab84fdc942127b42f9021662c86b7fcb46d490059a48e0261` |
| `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/runs/native-6vdhxryh/schedule.json` | `a1d28aba08ad30bb2c61237b38ae552e1f4b24a244310a183347a5cb96aa8521` |
| `/mnt/raid0/llm/tmp/df2/preflight-repair-20261120/replay.py` | `78f6d11b7deaef2d0f61432c9cfcb5f1aa48c70fd94a0242519eccb5d401bfb4` |

GitNexus status/impact could not run analysis: this lane has no index. Direct
caller inspection bounds this change to the shared CAFE3 scheduler output
preflight; no kernel/build/measurement policy changes. The previously sealed
CPU packet remains unchanged. Next: copy the repaired runtime source into that
packet, reseal inventory/publication bindings, and republish through the normal
smoke gate. Native identity, speed and recovery remain unassessed.
