# D9 decision: R-25 citations and OBS-11 registry applicability

Only the operator can acknowledge this protected-path merge. The exact proposed commit is `145540334907d399354adbd74a5b51c35c982a1e`, based on ROOT `f5a316b64ac4078df0afc7d6e67a62645564037c`. [Exact three-file patch](proposed.patch), [MAIN independent static review](MAIN-static-review.json).

The existing D9 ruling in [loop-owned fleet, operator decisions](../../../../handoffs/active/loop-owned-fleet-implementation.md) says: “merging any change under `scripts/coordination/**` requires operator ack.” It applies to metadata and docstrings as well as executable code. This is why approval is required.

| Option | Effect | Tradeoff |
|---|---|---|
| **A — approve this exact proposal (recommended)** | Fix two ambiguous source citations to F-34(b) and F-33(b); classify fleet_watch as exempt from the process/session-liveness battery because current D8/P3-3 source monitors hardware and queue aging only. | Corrects stale governance with a protected merge. It changes two docstrings and one registry row; runtime remains untouched. |
| B — retain current protected files | Keep the ambiguous citations and obsolete fleet-watch liveness assignment. | Avoids the merge, but leaves R-25 and OBS-11 open on known stale premises. |

MAIN compared the full patch: exactly observer_registry.json, tmux_adapter.py and worker_runner.py. Executable ASTs are identical after removing docstrings; actual docstrings intentionally differ. All 18 unrelated registry rows and fleet-watch runtime/owner/task-marker fields are unchanged. Registry shape and exempt reason are valid by static inspection. No fixtures or runtime actions were performed for this metadata/docstring correction.

Recommendation: **A**, confined to this exact commit. MAIN will recheck preimages, preserve peer changes and apply the corresponding task closures after acknowledgement. This approval does not cover OBS-1 implementation, bus activation, hook installation, cron changes, reloads or inference.
