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

Preloaded-refusal revision SHA-256: `e14bc45590ca7eabf95146298fe68f488bed70c3b265705ab6fae2be851f8bed`.
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

## 2026-11-19 — callable supervisor self-binding regression

A normally imported `supervisor` registers itself in `sys.modules`. The
preloaded-dependency check consequently rejected its own executing module,
preventing `run_driver()` from reaching the driver. A new isolated-process
test reproduced this failure through the actual `run_driver()` and real
cleanup helper, using a minimal sealed synthetic driver without R9 inputs.

The refusal gate now exempts only the module whose dictionary is this
executing supervisor's exact globals object. A separate object registered as
`foreign.supervisor`, including one with the same `__file__`, remains refused
before driver entry. File names and origin matches grant no exemption.

All six focused binding tests PASS: the four existing dependency controls
and two new callable controls. The successful callable returns the synthetic
driver's value and writes its entry marker; the refusal control requires
that marker to remain absent. Before the fix, the positive callable control
failed with `preloaded driver binding or dependency: supervisor`.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 \
  -p test_supervisor.py -k Binding -v
```

Supervisor SHA-256: `83dac150737f8cd4b04d25bbb5dd64e3f44b26e9ecadb6a6e6f967a321144710`.
Test SHA-256: `84dc695dfaacecb913ad51d12013bc5ad9eaea8378f59f9a1563e6102316d32b`.

The exact R9 `evidence_view.py` bytes are retained in
`/mnt/raid0/llm/tmp/kvu/g3-preload-integrated-20261105/candidate/evidence_view.py`
at SHA-256 `434f97561317bd0a5f75f2bcee2c7ea56b362278958ff77959c7008085422212`.
The scoped temporary/worktree/reachable-file-history search did not locate
`normalize_bridge.py` at `d3fed4a89230f5b18e9ec38787175c4fee9112c3dfa9e364923e0fa4d8cf8f0c`
or `test_real_grid.py` at `bcbb114cf72f5cc86b0672def2e805213c0910257670b9fcaa5bfe68d44e256e`.
No original R9 path or seal was changed. The inherited suite still cannot
initialize; it was not repeated. The persistent installation and historical
`qualification.json` remain unchanged. These tests qualify the callable
binding correction only, with no model, GPU, native lifecycle or current
execution-admission claim. Current custody/admission integration can proceed
independently with focused synthetic controls before the missing inputs are
required for full inherited integration.

## 2026-11-19 — current execution custody and official full-run entry gate

`run_driver()` now loads a sealed `execution_admission.py` before importing the
driver, captures admission, then rechecks it after import and before `main()`.
Missing execution configuration fails closed. The installer optionally accepts
explicit reviewed identities; it never learns native identities at execution
and refuses conflicting inherited pins. Existing installations are unchanged.

The execution manifest requires eight artifact roles (`python`, `shell`,
`flock`, `server`, `ggml`, `ggml_base`, `ggml_cpu`, `ggml_hip`), the provider
module, and its exact provider-source inventory. All require sealed file
identities. The running interpreter path must match. The whole source inventory
is checked again before driver main; GGUF entries are refused before reading
weights. Supervisor helper, admission, driver and provider source are compiled
from their verified source bytes rather than accepting cached bytecode.

The read-only gate checks the canonical flags/grants namespace, exact sealed
row/STOP identity, active declared window, the current keeper grant schema
(including mandatory `holds=`), GPU token, grant-derived CPU/thread/deadline
fields and process affinity. STOP, terminal receipts, active exact-name HOLDs,
symlinked namespaces/grants and malformed/duplicate/unknown grant fields refuse
entry. Renamed historical HOLD files do not block. Smoke, dry-run and direct
contexts are deliberately refused by this full-run-only gate.

The bound provider must supply its complete source inventory. Its existing
`capture` contract requires an exclusive canonical GPU lock held by a captured,
same-UID ancestor attributed to the current row, with birth identity and inode
retained; `recheck` must succeed again before main. Preloaded `src` provider
peers are refused. The gate acquires no grant or lock. Historical flock or
provider identity alone grants no authority.

Fifteen new focused tests and six existing binding tests PASS (21 total).
All new grant/provider tests use a private flags namespace and synthetic
provider/artifact bytes, with no official host lock or native artifact executed.
A positive test traverses actual supervisor capture/import/recheck/main with
only namespace/provider fixtures; another mutates a sealed artifact during
driver import and proves main remains unentered. A separate canonical-namespace
refusal traverses real `run_driver()` and proves driver import remains unentered.
The binding-only fixture explicitly seals an inert synthetic admission module;
its two real cleanup-boundary controls remain binding tests only.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 \
  -p test_execution_admission.py -v
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 \
  -p test_supervisor.py -k Binding -v
```

SHA-256 identities:

| File | SHA-256 |
| --- | --- |
| `execution_admission.py` | `24185aaba431336fff57765aaa6e3bd44016bf7920f0e5da7e99f129d4fb0b75` |
| `test_execution_admission.py` | `c5527efadc563c2211380a5046d809a5c7706d7c29624d893362bde03d90befb` |
| `supervisor.py` | `f0b08f5842d6c8dab8b96ebcf0acc1c26f62d839a02efb9f919766f01a46359d` |
| `install.py` | `044155bd634844b30bb9cd2cab35edf2cb6ff0c7f26713279baf76b4692422ad` |
| `test_supervisor.py` | `2ab1ef29461f4d9d45c58adacc9aa2a100456a0da7f4a52abb9a7fe9d2f997a0` |

These are model-free entry-gate regressions, not live official admission,
installed inherited integration, native cancellation/release or GPU results.
File custody does not prove which native DSOs a future server maps. The gate
checks entry and pre-main boundaries only, without continuous supervision or
output-reserve enforcement. Direct entries still return rc78. No persistent
installation, original R9 source path, historical pin or qualification record
was changed. The inherited suite was not rerun: its two missing exact R9 inputs
remain prerequisite to full installation. Next: recover those identities and
qualify the composed installation; separately qualify a publisher-smoke path
before publishing any native lifecycle successor. The retained driver's own
historical guards have not been bypassed or represented as current authority.


## 2026-11-19 — explicitly sealed publisher-smoke admission

The disabled supervisor now supports `execution.mode = "publisher-smoke"`.
The default remains `official`; environment flags cannot select the sealed
mode. Both modes retain identical artifact custody, provider capture and
pre-main provider/source rechecks. No launcher or persistent installation was
enabled or updated.

Smoke admission reads only the current row's canonical
`compute-flags/dryrun/<row>/grants/<row>.grant`, requiring the publisher's
`epyc.rowflow.dryrun-grant.v1` schema, matching `id`, and `kind=rowflow-dryrun`.
It checks the actual inherited publisher dry-run/state/grants directories,
exactly four assigned CPUs and equal process affinity, the sealed grant window,
STOP identity, deadline and GPU declaration. Direct, preflight and historical
`KPF_SMOKE` contexts fail closed. Both publisher flags must equal `1`.
The optional `ROWFLOW_FLAGS` alias, when present, must remain canonical.

The result path must name `native-attempts/attempt-*/native-result.json` under
that same row's dry-run directory. Symlinked result leaves or directory
components refuse entry. The grant bytes and selected result path are retained
and compared before main; STOP, terminal receipts and active HOLDs are rechecked.
This checks the destination at admission boundaries; it does not redirect the
inherited driver's outputs or prove all its writes use this path. The sealed
`window_s` must match the publisher-generated grant duration; no new window,
grant, lock, result or environment authority is created by admission.

Ten new smoke tests plus fifteen official tests PASS (25 admission tests).
Six binding regressions also PASS (31 total). The smoke controls traverse the
actual supervisor capture/import/recheck/main path with a synthetic driver,
and prove import-time artifact drift prevents main. Refusal controls cover
wrong mode/row/schema, missing or redirected publisher context, two-core or
escaped affinity, expired deadline, output isolation and result-path drift,
STOP/terminal/HOLD, symlinked grant/state/result, provider capture refusal and
loss of the captured provider before main. All use private namespace, clock,
affinity, provider and inert artifact fixtures. The supervisor ordering fixtures
bypass the outer cleanup wrapper, whose binding controls remain separate.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 \
  -p test_execution_admission.py -v
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 \
  -p test_supervisor.py -k Binding -v
```

| File | SHA-256 |
| --- | --- |
| `execution_admission.py` | `bb34f0ebcc8c476a60b1f63093050e3196ab8b4dfb06ec19897122fc350c3a1f` |
| `test_execution_admission.py` | `35cd7261e878c638d50037e3138afc15c7b7f3a73ec0689459e33ff57011dc7f` |

This is model-free code qualification. No publisher invocation, native smoke
PASS, real provider admission, mapped-DSO custody, inherited installation or GPU
qualification is claimed. The original R9 seals and historical qualification
record remain intact. The retained candidate `normalize_bridge.py` has SHA-256
`a68c3a1e0986bcf4c8a058965bbaa78bc6592ce1172aac6e4d1831eadd9e1ad4`,
which cannot satisfy the missing R9 identity above; its candidate has no
`test_real_grid.py`. To avoid repeated recovery-only turns, the next integration
step is an explicitly versioned successor using retained inputs and independent
integration controls, preserving rather than weakening the historical seals.
Then qualify the installed driver and output routing before native publication.


## 2026-11-19 — explicitly versioned retained bindings v2

`install(..., binding_revision="retained-bindings-v2")` creates a disabled
`kpf18.disabled-supervisor.v2` inventory. The default installer still requires
all original R9 identities. V2 retains the three superseded path/digest pairs
in `historical_sources`, binds the retained exact evidence reader and the
explicitly different retained normalizer, and seals independent controls in
place of claiming the missing `test_real_grid.py` suite passed. Unknown
revisions, replacement drift and inherited-identity conflicts fail closed.
Original predecessor manifests, paths, seals and qualification records are
unchanged. All inputs stay referenced; only the existing small binding modules
are materialized, and the full driver remains an immutable symlink.

Twelve independent tests PASS. Fresh interpreters import the installed full
driver and verify controller/transport/terminal/normalizer bindings. Actual
`driver.main()` is exercised with inert source/witness/gate peers and dry-run
arguments; no native source-authority check is claimed. The actual
`item3_smoke` closure, using inert server/request/resource peers, writes only
through its imported `OUT`, and exclusive creation refuses overwrite. Missing,
relative, outside-scratch and symlink output roots fail before main. Direct
entries remain rc78 and missing execution custody refuses admission. Twenty-five
execution-admission and six binding regressions also PASS: **43 tests total**.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 \
  -p test_successor.py -v
```

The persistent disabled installation is
`/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf18-supervisor-retained-v2-20261119`.
Three isolated installed controls (main, smoke-output, rebind) returned rc0.
[Source and installed-manifest SHA-256 identities](qualification-v2.json)
bind this result separately from historical `qualification.json`.

This qualifies model-free installed binding and legacy private-scratch output
routing only. The driver's retained `guard.sources()` still checks historical
manifests, and `guard.attempt_root()` still expects the candidate's legacy
namespace. Neither was bypassed for native execution or changed by this result.
Next: implement and qualify an explicitly versioned guard/output integration
with current execution custody and the publisher's isolated output namespace,
then qualify real publisher smoke before native publication. No model, GPU,
native lifecycle or KPF-18 parent verdict follows from these controls.


## 2026-11-19 — current source guard and admitted output integration v3

The opt-in installer argument `guard_revision="current-guard-v3"` requires
`binding_revision="retained-bindings-v2"` and explicit execution identities.
It produces a disabled `kpf18.disabled-supervisor.v3` inventory. Before driver
import, the supervisor captures current admission and prepares a source-sealed
binding module; the installed composition obtains its output directory from
that binding. After driver import, current admission is rechecked and the
binding replaces `guard.sources()` with the current custody/provider/grant
recheck, `guard.attempt_root()` with the admitted directory, and `guard.BIN`
with the explicitly sealed server artifact. It refuses an unsealed guard,
repeated binding, mismatched driver OUT, redirected output aliases and missing,
duplicate or mismatched `--out` arguments.

In publisher mode the directory comes from the captured isolated native-result
path, not a new environment authority. Official mode requires an explicit,
existing private directory in sealed `execution.output_root`. Every output-root
access rechecks admission and directory components; symlinks refuse access.
This redirects the driver's imported OUT and its reserve-accounting root. It
does not prove every inherited gate/helper write is contained there.

Eleven new model-free tests PASS, alongside 25 execution-admission tests,
six supervisor binding regressions and twelve retained-successor regressions:
**54 tests total**. The new isolated child installs v3 in temporary task scratch
and traverses actual supervisor capture/import/bind/recheck/main and outer
cleanup. Only canonical FLAGS is redirected to a private fixture, and the gate,
witness installer and server/request peers are inert. Actual driver.main runs
its current guard.sources without a source-check mock. The real item3_smoke
closure writes SMOKE-REQUEST.json into the publisher attempt directory and
refuses overwrite. Refusal controls cover artifact drift, provider loss,
STOP/grant/result drift, output aliases/argv, symlinks, unknown revisions and
missing explicit execution. Official private output is also tested.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 \
  -p test_execution_binding.py -v
```

No persistent installation was updated. Original R9 seals and historical
qualification records stay intact; direct entry points remain disabled (rc78).
The native `guard.boundary`, ContextBoundary resource checks, enrollment and
legacy smoke selection are deliberately not replaced by this integration.
Next implement current grant/provider boundary and admitted smoke selection,
then qualify real publisher smoke. No model/GPU execution, native lifecycle,
mapped-DSO custody or KPF-18 parent verdict follows from these software tests.
[no-belief: model-free software regression tests]


## 2026-11-19 — current per-work boundary and sealed smoke selection

The opt-in v3 binding now replaces retained `guard.boundary()` with captured
current admission/provider recheck and the existing sampled output-reserve
policy on the admitted output filesystem. The retained `ContextBoundary`
resolves this new boundary through its module globals; its underlying context
checks, conservative own-process HWM limit and output accounting remain active.
Historical lock/grant checks no longer supply authority at this boundary.
In sealed publisher-smoke mode the driver’s existing `item3` binding points to
its existing `item3_smoke` before main selects the gate item. Official mode
retains the full item. No environment switch or driver source rewrite is used.

Thirteen binding tests, 25 admission tests, six supervisor binding regressions
and twelve retained-successor tests PASS (56 total). The installed-driver child
traverses actual supervisor capture/import/bind/main/cleanup, checks main’s smoke
selection, calls the real retained ContextBoundary, verifies underlying context
checks and HWM refusal, runs the real smoke request closure, and checks context
STOP refusal. Added boundary controls cover provider loss and reserve refusal;
official selection remains unchanged. The fixture uses private grant/provider
inputs, inert server/request peers and controlled disk-free readings.

Commands: the preceding four unittest discovery commands, using patterns
`test_execution_binding.py`, `test_execution_admission.py`, `test_supervisor.py`
with `-k Binding`, and `test_successor.py`. No model, GPU, actual publisher smoke,
mapped-DSO custody or native lifecycle verdict is established. Direct entry
remains disabled; no persistent installation or historical seal was changed.
KPF-18 remains open. Full-run driver RowflowContext still carries its historical
rowflow adapter and needs current-admission integration before native full-run
qualification; gate-level admission/output containment also needs review before
real publisher smoke. Next: inspect and qualify the real publisher-smoke gate
entry and output routing using explicit current execution identities.

Revision identities (SHA-256):
- `execution_binding.py`: `62dc983a38fcb28c0ec0be9cc11f6e5429c550d29b7e67ec5e67a35b7c56042e`
- `test_execution_binding.py`: `b2c869ebfb01e2ddbef86e249ee649c0cc80c204613ad1227468235e96f8dff5`
- `install.py`: `2684eed635727f9ccfa03ccad6a02932bfb1d5c15c74a6bdfa9dac767445c6a4`


## 2026-11-19 — publisher smoke gate entry restriction and routing regression

Current v3 smoke binding now wraps the retained gate entry before its parser
can dispatch another command. It admits only item3 and an explicit option set;
preparation, argv output, resume, CPU mode, duplicate/abbreviated/equals-form
options and other gate commands refuse entry. The server must match explicit
execution custody; argv and prompt-set inputs must already exist in the source
inventory. Entry rechecks current admission, reserve and output routing. Full
mode retains its original gate entry. This narrows command dispatch, not every
possible server-side write or launch-prefix behavior.

The installed-driver child now traverses the real retained gate parser and
execution loop, with private prepared-input identities, inert server/request
peers and a fixture context builder. The real smoke action writes its request
record; the real loop writes run_meta.json and two completion markers under
the admitted publisher directory. Device acquisition, native preflight and
process launch are fixture substitutes; this is not actual publisher smoke.
Negative controls cover alternate commands, write options, changed inputs and
STOP before entry.

15 binding tests, 25 admission tests, 12 successor tests and six supervisor
Binding tests PASS (58 total), using unittest discover with their respective
patterns and `-k Binding` for test_supervisor.py. Unrestricted discovery also
attempts the historical Supervisor class and errors at setup because original
R9 evidence_view.py is unavailable; the successor does not claim that suite.
GitNexus reports this lane unindexed; its required indexing wrapper refused
CPU admission. Manual impact inspection confines the change to the opt-in
smoke binding and its model-free fixture.

Next: integrate current admission into non-dry driver enrollment/preload entry
before attempting actual publisher smoke. Historical guard.tests_and_enrollment
and retained preload custody still execute before gate.main on a native smoke
run; full-run RowflowContext also remains historical. Direct launch remains
disabled, no persistent installation changed, no native/GPU verdict or parent
KPF-18 completion is claimed. [no-belief: model-free software regression tests]

Source identities (SHA-256):
- `execution_binding.py`: `e7224011cde45fa46f737b5d10b0a973dbaef96045472ad84f695fde1d4f1a16`
- `test_execution_binding.py`: `1ad96938cf3c2af7d70923bfc48f6c23524790ec2cba7ee80f729bcc0fe3e0c2`
