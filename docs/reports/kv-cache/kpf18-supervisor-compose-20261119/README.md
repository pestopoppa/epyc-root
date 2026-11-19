# KPF-18 disabled outer supervisor

The new supervisor invokes the bound full driver's main through an outer
subreaper boundary. Before enabling the subreaper it refuses preexisting
children and multiple native threads. Its finally block drains captured/adopted
children after entry finalizers, including on ordinary exceptions and
SystemExit. Cleanup failure prevents a successful return. Direct supervisor,
driver and shell entry points remain disabled with rc78. Callable test entry
points do not establish admission authority.

Twelve tests PASS. Real child cases preserve return value or original exception,
require the child to be present during entry finalization and absent after
supervisor return, and exercise TERM-ignore escalation through the pinned
cleanup helper. Preexisting-child refusal leaves that child untouched; thread,
preloaded binding, source drift, incomplete install and existing-destination
controls fail closed. The source-bound earlier fixture is transformed only in
memory to route actual imported item3/controller/gate calls through the outer
wrapper: all eleven embedded checks PASS. Its drift control now changes the
new launcher's bytes instead of the immutable driver symlink. The first draft
of this test temporarily changed and restored the inherited driver via that
symlink; the final fixture avoids that write. All eleven checks also PASS on
the persistent installation.

The original predecessor has missing references under the reclaimed h-kvu lane.
Installation explicitly relocates those fourteen references to this lane only
after digest equality with their original seals. Negative control refuses a
relocation digest mismatch. Two small import-binding modules receive private
manifests in scratch; the driver is an immutable symlink and all other inputs
remain referenced. No source tree is copied. The original predecessor manifest
is retained and pinned. The installer never edits it.

Installed successor:
`/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf18-supervisor-successor-20261119`.
Exact manifest, supervisor and test identities are in `qualification.json`.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 \
  -p test_supervisor.py -v
```

The real-child controls use a synthetic paused Python child; full-driver cell
controls use synthetic seed/server/identity peers. These are software tests,
not native server cancellation/release, actual native driver main execution,
continuous supervision, output-reserve enforcement, current execution custody,
rowflow admission or GPU qualification. No model or GPU was loaded. KPF-18.0d
remains open. Next: bind current execution dependencies and official rowflow
admission in this disabled supervisor before publishing an owned-native
lifecycle qualification. The historical flock identity remains insufficient.

GitNexus has no index in this sparse lane, so upstream graph impact is unavailable.
Changes are confined to this package and its owning handoff/progress record.

## 2026-11-19 — preloaded native dependency refusal

The callable `run_driver()` previously refused only `composition` and its own
private driver alias. A preloaded `guard`, `controller`, or other sealed native
peer could therefore bypass on-disk custody: importing it returns its existing
Python object. The new gate derives peer names from the sealed Python source
inventory and refuses any already-loaded match (including dotted aliases)
before the first driver import. Matching `__file__` is insufficient because
module globals can be modified after import. Unrelated modules remain allowed.
The gate uses the same inventory as source verification; new sealed peers are
covered without maintaining a second dependency list.

Four focused tests PASS, including eight injected peer/alias cases, a matching
origin with untrusted globals, a newly added inventory peer and an unrelated
module control. The import control asserts that driver loading is never reached.
These tests run without the native runtime or model bytes:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 \
  -p test_supervisor.py -k DependencyBinding -v
```

Current supervisor SHA-256: `e14bc45590ca7eabf95146298fe68f488bed70c3b265705ab6fae2be851f8bed`.
`qualification.json` describes the earlier implementation and is historical;
the persistent disabled installation still contains that earlier version.
This change does not update or enable it.

The complete inherited suite currently fails in installer setup because three
original R9 source paths are missing: `evidence_view.py`, `normalize_bridge.py`
and `test_real_grid.py` below
`/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-format-r9/`. Their required digests
remain in the pinned predecessor manifest; no pin was changed or inferred.
An exact retained `evidence_view.py` was located but a temporary recovery
symlink was removed after the other two dependencies remained unavailable.
No whole-suite or installed-successor regression PASS is claimed for this change.
Next: recover all three files at their sealed digests, then bind current
execution dependencies and official rowflow admission before installing and
publishing a native lifecycle successor. Direct entries remain disabled (rc78);
no GPU/native or execution-admission qualification follows from these tests.
