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

## 2026-11-19 — current enrollment and preload prerequisites

The opt-in current-guard-v3 binding now checks current admission, provider,
source custody, output routing and reserve before and after enrollment/preload
entry. This changes the disabled successor only; retained driver/guard/verifier
bytes and installed historical manifests remain unchanged.

`execution.enrollment` explicitly supplies `framing_result` and
`canonical_export`. Every file must be in the source inventory, and the framing
result and three projection files must retain the exact SHA-256 identities from
retained guard.tests_and_enrollment. Framing still requires framing_pass=true
and the same raw_sha256. The returned scope remains diagnostic with no new
enrollment receipt; this is no new enrollment authority or grading rule. There
is no fallback to vanished historical directories. The original R14 framing
result and R15 canonical-export paths are absent on this host. Explicit paths
permit recovery of identical bytes without weakening the identity requirements;
the R16 export identities already present in the inherited manifest agree with
the original three projection pins.

`execution.preload_receipt` supplies the receipt path, which the binding assigns
to driver.RETAINED_PRELOAD_RECEIPT. Both it and the driver's BASE/ORIGINAL-MODELS.json
must be sealed inputs. Redirected arguments refuse before verifier entry. The
original load_preload_models callable still checks the fixed receipt digest,
metadata, model paths, draft shape and stat tuples. No model weight hashing or
preparation is added to runtime. STOP/provider/custody changes during verifier
execution refuse before returning models. The driver still controls its original
identity output and subsequent unchanged_models check.

Eight focused prerequisite controls PASS, covering explicit-location enrollment,
original expected digest requirements, framing failure despite a sealed input,
missing configuration, preload delegation and post-call STOP, unsealed/redirected
inputs, provider/source drift and retained verifier errors. Fixtures substitute
synthetic framing/projection pins and an inert preload callable; they do not
qualify the actual retained verifier or native non-dry main. The previous 58
scoped tests also PASS (66 total). Commands:

```bash
python3 -B -m unittest discover -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 -p test_execution_prerequisites.py
python3 -B -m unittest discover -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 -p test_execution_binding.py
python3 -B -m unittest discover -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 -p test_execution_admission.py
python3 -B -m unittest discover -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 -p test_successor.py
python3 -B -m unittest discover -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 -p test_supervisor.py -k Binding
```

GitNexus status/impact unavailable in the unindexed lane. Manual call-site
inspection confines edits to the opt-in binding and its tests. git diff --check
PASS. No new source/measurement producer, GPU/native result, publisher smoke,
full-run RowflowContext qualification or KPF-18 completion is claimed.

Next: exercise actual installed non-dry main through current prerequisites with
private model-free controls and the retained preload verifier, including refusals
before gate entry. Recover/explicitly seal exact framing/projection inputs before
actual publisher smoke; full-run RowflowContext remains historical.

Source identities (SHA-256):
- `execution_binding.py`: `cd9e271c64cea01da7c4ba5c66ccb0051050e73dbfaa33b69daa45b7f887957a`
- `test_execution_binding.py`: `a83b9702f9a8c3f628073929847e59e4164dc47e5163a79ac48e42b4125bc98c`
- `test_execution_prerequisites.py`: `98402f795ef652b9574a9fe90d77e6dac7c60ba0f4045c316a10ae6776ef7ffe`

### 2026-11-19 — Installed non-dry entry and retained preload verifier

`test_nondry_entry.py` adds four isolated-process controls through the installed
supervisor's `run_driver`, current admission and enrollment bindings, unchanged
non-dry driver main, retained `load_preload_models`/`verify`, and both retained
stat checks. The valid case writes the driver's identity output under the admitted
private output and reaches witness/gate entry in order. Receipt digest mismatch,
drafter metadata mismatch, and changed target stat each refuse before identity
output, witness installation or gate entry. All four controls PASS. The prior
66 scoped regressions PASS (70 total); `git diff --check` PASS.

Run the new controls with:

```bash
python3 -B -m unittest discover -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 -p test_nondry_entry.py -v
```

The private fixtures replace framing/projection and receipt pins explicitly in
memory, redirect the admission flags root to private grant/provider fixtures,
and supply tiny stat files. The disk reserve is synthetic; witness and gate are
inert. The tests do not hash model contents, execute a native runtime or touch
production grants. Original source bytes and historical seals are unchanged.
This qualifies software routing and refusal behavior only, not the original
receipt/framing, current official admission, publisher smoke, native lifecycle,
GPU inference or the historical full-run RowflowContext adapter. KPF-18 stays open.

Evidence SHA-256:

- `test_nondry_entry.py`: `4b3f0a27e173ae49f320a7b6430743eca8cb6bd2700a502cee6e74cb87023159`
- `/mnt/raid0/llm/tmp/kvu/g3-preload-integrated-20261105/candidate/verify_receipt.py`: `2f820a5a215a36aa822dee4fb43cec4eb8fddb57b94b2434a85dfa63857eb506`
- `/mnt/raid0/llm/tmp/kvu/g3-preload-integrated-20261105/candidate/preload_integration.py`: `a7958fc86664381b287c589e14f21972473336cd3df58b4f3087e375e4a4b88d`

Next: recover exact framing-result bytes matching
`9c782023a139941349fb664e79c666df5ea894a231395761053bae2dd03a3225`
and explicitly seal their location plus the three pinned projection inputs for
publisher smoke. Full-run RowflowContext remains historical. GitNexus
status/impact unavailable because this sparse lane has no index; this revision
changes only independent qualification tests and this report. No new native
source or measurement producer was introduced. Bus drain rejected the handoff
slug because it has no roster id; no other session's outbox was used.


### 2026-11-19 — Smoke launch prefix preserves admitted affinity

Found a real launch-path defect while preparing publisher smoke: the retained
parser defaults to `numactl --membind=3 -- taskset -c 184-191` and Server.full_cmd
prepends the parsed prefix to the server argv. Omitting --launch-prefix could
expand a four-CPU smoke's inherited affinity. An arbitrary supplied prefix could
also execute a different program before the sealed server. Source: retained
`/mnt/raid0/llm/tmp/kvu/g3-preload-integrated-20261105/candidate/vendor/kpf18_gate.native.py`,
DEFAULT_PREFIX, build_ctx and Server.full_cmd (source seal retained by installer).

The opt-in current publisher-smoke wrapper now refuses every nonempty launch
prefix before gate entry and explicitly supplies an empty prefix when omitted.
The child inherits the admitted process affinity; no extra wrapper executable is
introduced. Caller sys.argv is restored on success and failure. Official entry
is unchanged. Three new regressions reproduced the defect before the fix; the
installed real-driver/parser control now also asserts the parsed prefix is empty.

PASS: 18 binding tests, 25 admission tests, 8 prerequisite tests, 4 non-dry entry
tests, 12 successor tests and 6 supervisor Binding tests (73 total). Commands are
the preceding documented unittest commands, with the same file selection.
`git diff --check` PASS. This is model-free software qualification, with inert
native/context peers in the installed integration. No actual CPU-affinity or
GPU measurement, publisher smoke, native lifecycle, or full-run RowflowContext
qualification is claimed. Persistent installation was not updated.

Evidence SHA-256:
- execution_binding.py: `275066df227c2a99110fe540b14f53975bcba895f5711dd646e3c0ae71dd2789`
- test_execution_binding.py: `22264015037f1805fff9a391904b2cb2a2cc01b6aa2536b561c2de03d759f9e3`

Input recovery: no matching framing bytes in 8 framing-containing small JSON
candidates under the targeted KPF18 roots, or 19,984 small result-name JSON files
under /mnt/raid0/llm/tmp. This search does not prove the bytes are absent from
other stores or git object databases. No historical pins or acceptance receipts
were changed. Actual publisher smoke remains dependent on exact framing recovery.
Next independent work: qualify the full-run RowflowContext adapter against current
official grant/output admission with model-free controls. GitNexus status and
prepare impact unavailable because this sparse lane is unindexed; manual upstream
inspection limits the change to current publisher-smoke entry and its tests.


### 2026-11-19 — Current official full-run work context

The opt-in current-guard-v3 binding now subclasses the retained RowflowContext
for official execution. Each work boundary rechecks the captured current
admission/provider, source custody, output directory and reserve, requires the
underlying context output to equal the admitted output, then calls the unchanged
ContextBoundary (including its own context and HWM checks). Missing retained
context refuses binding. The inherited delegation, EntryRefused type, controller
wrapper and abort/refusal-record path remain intact. A latched terminal refusal
cannot resume work if STOP subsequently disappears. The historical rowflow
adapter is not invoked by this bound context; its original bytes are unchanged.
Publisher-smoke selection and the retained standalone wrapper are unchanged.

The new isolated-process regression installs a private successor and traverses
real supervisor capture/import/bind/main, retained full-run item3 cell,
run_with_rowflow_boundary and abort_terminal_refusal. Eleven controls PASS:
valid two-boundary execution; STOP; grant-byte mutation; captured provider loss;
reserve failure; context output redirection; underlying context failure; HWM
limit; source drift; deadline; and sticky STOP refusal. Each negative control
requires the second work marker to remain absent and checks its specific reason
in the retained diagnostic-refusal path. The historical adapter is replaced
with a raising sentinel in these tests, proving it is not consulted.

Model-free fixtures use private official-format grants, synthetic artifact and
provider inputs, controlled time/affinity/disk readings, inert setup/controller/
server/witness peers and an in-memory refusal ledger. Real driver main runs its
--dry-run branch; non-dry prerequisites are covered separately by existing tests.
This does not qualify actual official grants, gate CLI/output/launch-prefix
routing, native execution, GPU residency, controller numerics or publisher smoke.
Persistent installation and all historical pins remain unchanged; KPF-18 stays
open. No parent gate box is ticked by this software-only result.

PASS: 19 binding, 25 admission, 8 prerequisite, 4 non-dry entry, 12 successor,
6 supervisor Binding, and 1 new full-run test with 11 isolated cases: 75 unittest
tests total. Run the new controls with:

```bash
python3 -B -m unittest discover -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 -p test_fullrun_context.py -v
```

Git diff --check PASS. GitNexus status/impact unavailable in this unindexed sparse
lane; manual caller inspection confines the change to opt-in official binding
and its tests. Bus drain refuses the handoff slug because it is not a roster id;
no other session's outbox was used. [no-belief: model-free software regression tests]

Next: qualify full-run gate command/output/launch-prefix routing under current
official admission before any native full-run publication. Exact historical
framing-result recovery remains necessary before actual publisher smoke.

Evidence SHA-256:
- `execution_binding.py`: `bfee63924c5675536bf8a9d9874386f8daf6f17494ff9ce26dfda29875905810`
- `test_execution_binding.py`: `1bd9cb6aa8f4348dbe9a0b9616a992ceb9d987fd5f33af922e07ce9d34e98f8d`
- `test_fullrun_context.py`: `115e8fa1486dac03da99f724ae41e0d8d925b375166907090428cd4a4964335f`


### 2026-11-19 — Current official gate command and launch routing

Extended the opt-in current-guard-v3 gate-entry wrapper to official execution.
Previously official entry left the retained parser unrestricted, including its
fixed CPU 184-191 launch prefix and alternate commands/write targets. Both
modes now require item3, the admitted output, the sealed server and sealed
prepared argv/prompt inputs; duplicate, unknown and write-producing options
refuse before parser entry. Every nonempty launch prefix refuses; omission
becomes an explicit empty prefix so server children inherit admitted affinity.
Official gate entry also refuses KPF_SMOKE=1 rather than silently selecting the
smoke item. The real full-run item3 selection remains intact. Caller sys.argv
is restored on success and failure. No historical driver or gate bytes changed.

PASS: one new isolated-process test with 13 cases: valid, explicit empty prefix,
nonempty prefix, alternate command, alternate write, redirected output, duplicate
output, foreign server, unsealed prompt input, prepared-input drift, STOP,
smoke-selection override, and inert execution failure. The installed real
supervisor capture/import/bind/main path reaches the real retained parser and
execution loop. Positive controls require item3 selection, empty parsed prefix,
admitted run_meta.json and expected completion markers; negative controls
require no parser-context entry, work or output. Execution failure requires rc4
and no completion marker. Every case checks caller argv restoration.

The other 75 scoped regressions also PASS: 19 binding, 25 admission,
8 prerequisites, 4 non-dry entry, 12 successor, 6 supervisor Binding and
1 full-run context test (11 isolated cases), for 76 unittest tests total.
An initial aggregate command used nonexistent test_supervisor.Binding and
reported a loader error alongside 69 passing tests; corrected discovery with
-k Binding passes all six intended supervisor cases. Git diff --check PASS.

```bash
python3 -B -m unittest discover -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 -p test_fullrun_gate.py -v
python3 -B -m unittest discover -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 -p test_supervisor.py -k Binding -v
```

Scope: private official-format grant/provider/artifact fixtures; inert item3,
context and witness. Driver main intentionally takes its dry prerequisite
branch, then the fixture removes --dry-run only at gate entry to exercise the
real execution loop. No native work, real device claim, actual official grant,
measured affinity, GPU, publisher smoke or full non-dry integration is claimed.
Persistent installation and historical input pins remain unchanged. KPF-18
remains open. Exact historical framing recovery still blocks real publication;
next qualify combined non-dry main/prerequisite/gate routing with private
retained-verifier controls. GitNexus status/impact unavailable: no sparse-lane
index. Bus drain refuses the slug because no matching roster id exists.

Evidence SHA-256:
- execution_binding.py: `fd48e1424391f44421899b4c8d80fa7ffbd04e1b33a848e3dc86e73daf38d023`
- test_fullrun_gate.py: `0d3f0f9d2ab0c7de6e7823bf877d12f398befdf8c684738bd269f4c9666b7355`

[no-belief: model-free software regression tests]


### 2026-11-19 — Combined installed non-dry prerequisites and gate loop

PASS: one combined integration test with 10 isolated-process cases. The installed
supervisor reaches unchanged non-dry driver main, current enrollment checks,
retained preload receipt verifier and both model-stat checks, identity output,
and the real official gate wrapper/parser/execution loop in the same invocation.
The successful control requires item3, dry_run=false, the admitted output/server,
empty launch prefix, run metadata and one completion marker. Inert execution
failure returns rc4 with no completion marker. Digest, stat, metadata and false
framing controls refuse before identity output, witness or parser context. A
nonempty prefix, foreign server, STOP introduced at witness installation and
prepared-input drift introduced there refuse before parser context or work;
these preserve only the earlier preload identity output. No gate.main replacement
is used in the combined controls. The existing non-dry worker supplies shared
fixtures via an opt-in combined argument; its four original controls still pass.

Validation: 52 admission/binding/prerequisite tests, 4 original non-dry tests,
2 full-run context/routing tests and 1 combined test PASS (59 unittest tests;
the combined test contains 10 subprocess cases). git diff --check PASS.

```bash
python3 -B -m unittest discover -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 -p test_combined_entry.py -v
```

Scope remains private model-free software qualification: scientific input pins
are explicitly replaced in memory, the grant/provider/artifact fixtures are
private, and context construction, item3 work and witness installation are inert.
The full RowflowContext and native controller/server/GPU lifecycle are not
exercised by this combined test. Historical pins and persistent installation are
unchanged. KPF-18 remains open; no parent checkbox is completed. Next recover the
exact historical framing result required for real publication, without replacing
its digest with a newly generated result. GitNexus status and impact unavailable
in the unindexed sparse lane; manual inspection limits changes to test harnesses.
Bus drain refuses this slug because it is not a roster id; no foreign outbox used.

Evidence SHA-256:
- test_combined_entry.py: `2536ab02df17d134d316f4e1e20c341bc3ea57d6ce7adb0a1ee60ef50cc3a2b8`
- test_nondry_entry.py: `0928e918418320fb9ce8e2f12a6467da03c4489ec03330833efe0e4ebfe64ee3`

[no-belief: model-free software regression tests]


### 2026-11-19 — Combined non-dry entry through actual item3 boundaries

PASS: 10 isolated subprocess cases connect installed supervisor capture/import/
bind, non-dry enrollment and retained preload checks, identity output, actual
official gate wrapper/parser/execution loop, real item3 step construction and
retained/current RowflowContext abort handling. Unlike the earlier combined
entry test, this test does not replace item3. Native server lifecycle/setup,
controller work, publication and witness installation remain inert peers; parser
context construction is a private fixture. The old rowflow_entry is replaced by
a raising sentinel, so any use of that historical adapter fails the test.

Valid execution requires two underlying boundary checks, both work markers,
publication and four step completion markers with rc0. STOP, grant mutation,
context-output mutation, native-source drift, deadline exhaustion, underlying
context failure, sticky STOP after its file is removed, reserve exhaustion and
HWM excess each require rc3, a reason-specific DIAGNOSTIC-REFUSAL record, only
the first work marker, no publication and only the setup completion marker.
This tests refusal propagation through the actual parser loop rather than calling
step functions directly. Model metadata/digest/stat prerequisites remain real
retained verifier calls over explicitly synthetic, in-memory-pinned fixtures.

Validation: the new combined-context test (10 subprocess cases) PASS; four
original non-dry entry tests, the prior combined-entry test (10 cases), and the
prior full-run-context test (11 cases) PASS. Seven unittest tests total.
git diff --check PASS. Run the new test with:

```bash
python3 -B -m unittest discover -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 -p test_combined_context.py -v
```

No native/GPU execution, actual official grant, publisher smoke, historical
scientific-input recovery or parent-gate completion is claimed. Production and
persistent installed runtime bytes are unchanged. Test-only blast radius was
manually inspected; GitNexus status/impact unavailable in the unindexed lane.
Bus drain refuses the unregistered slug; no other outbox used.

Recovery attempt before this independent result: no exact R14 framing match in
984 small reachable KPF18-named git blobs; targeted archive inventories revealed
no R14 result, and a deterministic reconstruction from retained receipts/writer
and a further 151 retained digest candidates failed its pinned SHA-256. These
attempts were discarded; no replacement bytes were written or accepted and no
pin was changed. This bounded search does not prove absence from all stores.
Retained acceptance-record SHA-256 is
`08300255d31647b0d99c352284058fd33eaeb6a598bc2e94f2dbdbbd37293f86`
at `/mnt/raid0/llm/tmp/kvu/g3-preload-integrated-20261105/candidate/INTEGRATION-REPLAY-ACCEPTED.json`;
retained replay-writer SHA-256 is
`4c2d9ed3763fb0dae651eb697c03afdfd2530435ae31b599c69a3995165ef1a1`
at the same candidate's `integration_replay.py`. Historical acceptance remains
recorded in `progress/2026-10/2026-10-27-codex-ni-checkpoint-0945.md`.
Rather than repeat this unsuccessful recovery, next assess an explicit successor
prerequisite bound to the already accepted retained R7 framing result/source/input
identities. Preserve the R14 contract and distinguish successor acceptance from
recovery; no fresh replay of already accepted recorded-X1 framing is needed.

Evidence SHA-256:
- test_combined_context.py: `4872d50785452bc3520a86a27d1564d498dee670efa1b61b169a678a6eead2b4`
- test_nondry_entry.py: `78602c4986e8503cef19f7a770f75d5b6205804e13c0f83230c22a5dd25f9313`

[no-belief: model-free software regression tests]


### 2026-11-19 — Explicit retained-R7 successor framing enrollment

The disabled current-guard-v3 entry now accepts sealed enrollment
`framing_mode: retained-r7-v1`. Omitted mode retains historical-r14 and its
original result/raw digest requirements; unknown modes refuse without fallback.
R7 mode requires `framing_result`, `complete_marker`, `source_manifest` and
`root_source_manifest` absolute locations in the current source inventory. Their
code-owned pins are the identities accepted in
`artifacts/compute/results-filing-20261030-1752.json` (git blob
52472ec228019aca93e58ddb02065e9b8e363aca).
The retained result/marker/manifests were read at their original paths under
`/mnt/raid0/llm/tmp/codex-ni-kpf18-native-segfault-r7-20261030/`; nothing was
copied or replayed. The completion marker must still name the exact result path.

The entry independently checks bytes against those pins, then checks completed,
nonpartial rc0/child-rc0 execution, captured-child cleanup, original source/raw/
ledger/layout/fork identities, all four stages, 1,128 grids and eight events.
The marker must bind that result identity. Original R6 INVALID remains explicit.
Projection pins, current admission/provider/STOP/reserve checks and post-entry
boundary checks remain required. Returned metadata names the R7 mode/result digest
and retains the diagnostic scope with no new enrollment receipt.

Validation: seven new tests PASS (including the actual retained metadata and
15 synthetic result-field mutations plus four completion-marker mutations),
52 execution admission/binding/prerequisite regressions PASS, and both combined
installed non-dry entry/context tests PASS (61 unittest tests total).
`git diff --check` PASS. Tests use private admission, tiny synthetic projection
files and inert native peers. R7 source-manifest bytes establish historical
source identities; this does not revalidate every historical transitive source
or the absent Micron payloads. No native-control/model/GPU equivalence, runtime
publication, persistent installation or parent completion is claimed.

Manual blast radius is the disabled enrollment branch and its tests; no graph
index exists in this sparse lane, so GitNexus status/impact cannot establish a
graph radius. Source-table wiring is unchanged: this consumes accepted metadata
and introduces no measurement producer. Next qualify the R7 mode through the
installed non-dry entry with unchanged retained preload/projection checks before
preparing a publisher-smoke seal. Bus drain rejected the unregistered session
slug; no other session outbox was used.

Evidence SHA-256:
- execution_binding.py: `def1b67113f5920e5271431068d173f3c342f28f9a63f7613be37162fc5757f2`
- test_retained_r7.py: `fbe46eb6f9a4087a4d0bfd447e6c09ca857947309f0e720e15a6ac952dd9efc8`

[no-belief: model-free software regression tests]

## 2026-11-19 — Installed retained R7 non-dry enrollment

`test_retained_r7_entry.py` passes eight isolated installed-supervisor/real-driver non-dry controls. The positive control consumes the original accepted R7 result, completion marker and two source manifests at the paths in `test_retained_r7.PATHS`, with unchanged `execution_binding.R7_PINS` and framing raw identity. It invokes the real retained preload verifier and stat checks, writes the expected preload identity output, and reaches inert witness/gate peers. Seven negative controls (receipt digest, model stat, metadata, missing completion seal, wrong R7 result, unknown enrollment mode, wrong projection pin) refuse before identity output, witness and gate. No retained input file is modified or copied.

Projection bytes/pins, tiny model stat files, receipt identity and current admission/provider remain explicit private fixtures; this proves enforcement and installed composition, not original projection recovery or native/GPU qualification. Historical R14 seals and persistent installations are unchanged. No model execution, X1 replay, actual publisher smoke or parent gate completion is claimed.

Validation: `python3 -B -m unittest discover -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 -p test_retained_r7_entry.py -v` (one unittest, eight isolated controls); discovery for `test_nondry_entry.py` (4), `test_retained_r7.py` (7), and `test_combined*.py` (2) also PASS. Next: qualify sealed R7 enrollment with real parser/gate routing under publisher-smoke admission, then prepare publication using actual prerequisite locations.

### 2026-11-19 — Installed retained R7 enrollment through the smoke recipe

`test_retained_r7_smoke.py` connects the installed supervisor and current
publisher-smoke admission with the real non-dry driver main, retained R7
enrollment, retained preload verifier, parser/execution loop and unchanged
`item3_smoke` recipe. Fifteen isolated cases cover the valid control, HTTP
failure, empty tokens, missing sampled residency, receipt/stat/metadata
refusals, missing completion seal, wrong framing input, unknown enrollment,
projection refusal, foreign prefix/server, late STOP and prepared-input drift.
Only the valid control writes `SMOKE-REQUEST.json` and both done markers;
runtime failures return rc4 without a smoke record, and entry refusals never
reach context construction or requests. Every case asserts absence of a
publisher native-result or group verdict.

The valid control consumes the original accepted R7 metadata at the paths in
`test_retained_r7.PATHS` without changing R7 pins. Projection identities, model
stat/receipt inputs, admission namespace/provider, context, HTTP client, server
and residency sampler are private fixtures. This qualifies installed software
composition only. It does not run `publish_row.py`, load models, sample a real
GPU, establish mapped-DSO custody, qualify native cancellation/drain, or complete
KPF-18. Production, historical pins and persistent installations are unchanged.

Reproduce the 15 controls with:
`python3 -B -m unittest discover -s docs/reports/kv-cache/kpf18-supervisor-compose-20261119 -p test_retained_r7_smoke.py -v`.
Source SHA-256: `test_retained_r7_smoke.py`
`aafb48e169733937b438770d36cd4c462f28f52893006e97e0f7183b7fc8f5f3`;
shared harness `test_nondry_entry.py`
`3163cfaba13ace97944aa1b5f26380af40006cff77b550db69f41e6840fb5f05`.

Full discovery still refuses the historical `test_supervisor.Supervisor`
setup because the sealed R9 `evidence_view.py` is absent. That default R9
inventory remains unchanged; its prior qualification is not claimed here.
All other `test_*.py` modules in this directory PASS (81 unittest tests,
including the 15 isolated smoke controls). The exclusion is by module name
`test_supervisor`, not by individual failing assertion.
Next prepare the actual prerequisite locations and explicit current artifact/
provider inventory for a sealed successor, then publish the lifecycle row
through official rowflow; this test supplies no smoke-PASS receipt for that row.

SHA-256 identities:

- `test_nondry_entry.py`: `0899f19d7a3f72430e1a665ebf7767007919338d1620dd639a7080791987f5b6`
- `test_retained_r7_entry.py`: `225141d5e79e6a3a016affba09385fe18c9cd16f217f13592c2de24aeec0c0bb`


## 2026-11-19 — delegate device claim to the captured keeper writer

Publication preparation exposed a real integration defect: the retained gate
acquires its own `autokernel.resource.device_claim` whenever parsed
`no_device_claim` is `None`. Current admission already captures the keeper's
exclusive GPU writer, but the restricted gate wrapper prohibited that option
without supplying it. The earlier fixtures hid the omission by assigning the
parsed field themselves. Removing that assignment reproduced three failures
(valid, explicit empty prefix and work-error official controls).

The current wrapper now adds a fixed `--no-device-claim` explanation only after
current boundary/admission/provider recheck, inside the temporary argv scope.
Caller-supplied bypass options remain refused. This applies to both explicitly
sealed official and publisher-smoke modes. The retained gate and historical
manifests are unchanged. The ordinary gate still acquires its device claim;
only the current admitted wrapper delegates to its captured keeper writer.

Official installed routing now covers fifteen isolated cases, including caller
claim override and provider loss. The fifteen retained-R7 smoke cases and both
combined non-dry execution suites now assert the actual parser-produced claim
field instead of filling it in. Publisher-mode controls also require provider
loss to refuse before parser entry and argv restoration on gate failure.
Native work, context construction and provider admission remain private fixtures;
no real lock, GPU execution, publisher smoke or mapped-DSO qualification follows.

Source identities (SHA-256):

- `execution_binding.py`: `5a75fabddb421d57772b4c56881531e35adedc70a07429642a0f4ab3b637a042`
- `test_fullrun_gate.py`: `2eafd7105d0180e7f232cbea9c4dbff4efed041253698cc6343961bb53a80ef6`
- `test_execution_binding.py`: `e03c7e6d20485925e269c75d2864e05aaae68d39fceeee332e01c721db6a8a36`
- `test_retained_r7_smoke.py`: `6a88fe259b118edd8d8b3bb0462fe0f2b3db55705b5827b485acad1d19734c27`
- Retained gate `/mnt/raid0/llm/tmp/kvu/g3-preload-integrated-20261105/candidate/vendor/kpf18_gate.native.py`:
  `76bc6e18c9b58d4270d091c2b9f42358e2225aa6481585fbf4bbb9970424f4c9`.

Actual input locations resolved during this task, without copying or changing them:

- Canonical export: `/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-native-control-r15/canonical-export-root`.
  All three files equal `execution_binding.PROJECTION` pins.
- Preload receipt: that retained R15 directory's `out/PRELOAD-MODEL-IDENTITY.json`.
  The unchanged retained `load_preload_models()` accepts it with
  `/mnt/raid0/llm/tmp/kvu/g3-preload-integrated-20261105/candidate/ORIGINAL-MODELS.json`,
  including both live model stat checks. Model contents were not hashed.
- Prepared argv and prompts named by retained `config.sh`:
  `/mnt/raid0/llm/tmp/overnight-20261020/argv.8083-gate.txt` and
  `/mnt/raid0/llm/tmp/overnight-20261020/kpf18-run/prompt_set.jsonl`.
  These are resolved references, not freshly verified content identities.
- Current provider implementation: `docs/reports/kv-cache/kpf18-g3-current-lock-20261104/current_lock.py`;
  its five `SOURCES` must be freshly pinned from its declared orchestrator tree.

Next: use these actual prerequisites in an explicit retained-R7 successor seal,
complete current artifact/provider custody and retained native launch integration,
then publish the owned-native lifecycle row. No row was published this turn.
GitNexus status and upstream impact both refuse because this lane has no index;
manual inspection limits the change to current binding argv and its regression
fixtures. No persistent installation, production tree or historical seal changed.

Validation: all 82 unittest tests outside historical `test_supervisor.py` PASS
(`python3 -B` unittest discovery per `test_*.py`, excluding that one module).
That historical suite was not rerun; its previously documented unavailable R9
inputs remain outside this successor's qualification. `git diff --check` PASS.


## 2026-11-19 — HSA affinity preservation with inherited placement

The retained `Server.build_env()` calls `apply_pinned_launch_env()` with its
launch prefix. That helper sets `HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0` only when
the prefix contains `taskset`. The current admitted entry requires an empty
prefix to inherit the publisher/keeper CPU placement. Consequently an absent
or conflicting ambient HSA value was preserved, permitting ROCr to widen the
server's CPU affinity; the required launch metadata also omitted the HSA value.
The new real-Server construction control reproduced the absent case before
this fix (`AssertionError: (None, None)`). Earlier controls mocked Server.

After current boundary/provider recheck, the admitted gate wrapper now supplies
HSA0 as fixed `PROD_ENV` recipe data. The unchanged retained Server overrides
ambient values and records HSA0 in `env_note["set"]`. No caller environment,
launch prefix, native lifecycle method or historical source is modified.

Both installed official routing and installed non-dry retained-R7 smoke routing
now construct the actual Server with an empty prefix. Each checks ambient HSA
unset, zero and one, requiring effective/recorded HSA0, retained grids3 debug,
binary-local LD_LIBRARY_PATH, prefix-free command and unchanged caller env.
Construction performs no Popen, model load, request or native GPU work.
The official suite passes 15 isolated cases; the smoke suite passes 15 isolated
cases. The broader 82-test successor suite excludes the historical
`test_supervisor.py` module with previously documented unavailable R9 inputs.

Reproduce with unittest discovery for `test_fullrun_gate.py` and
`test_retained_r7_smoke.py` in this directory. Source SHA-256 identities:

- `execution_binding.py`: `a63c1e6fadf17392f325bfeade23bf6630e8af778ac018853fbc23f718de1c4e`
- `test_fullrun_gate.py`: `b42af1cf2b3c75c0a2999b99b0469d2cbab5dc6a18849cb4572e9f70d75fa287`
- `test_retained_r7_smoke.py`: `afe5676efb173def96ea27ef497dae9a40697d973afba130241a1696b2d25cef`
- `test_execution_binding.py`: `a826392a633dd0491c4235bdab2fe194a7e692f05cd7c0701182031d8aa4ec65`

This is model-free software qualification. Actual post-launch thread affinity,
provider admission, mapped DSOs, cancellation/release and GPU residency remain
for the scheduled native row; no publisher invocation or smoke-PASS receipt is
claimed. Persistent installations, production and historical manifests remain
unchanged. Next seal the successor using the actual inputs above and current
artifact/provider identities, then publish its owned-native lifecycle row.
GitNexus status/impact are unavailable in this unindexed sparse lane; manual
review limits the runtime change to the admitted gate's recipe environment.
Bus drain refuses the unregistered kvu slug; no other outbox was used.
[no-belief: model-free software regression tests]


## 2026-11-19 — current admission at retained recipe step boundaries

The current wrapper previously rechecked before gate parser entry. The retained
execution loop then called each Step directly. Its startup steps did not call
current admission; the smoke request checked it later and converted a late
STOP into generic rc4. Thus admission could change during context construction
and native startup would still be attempted before the later request refused.

Both official and smoke item3 recipes now wrap every step action with the
current boundary. A refusal becomes the retained gate Abort (rc3), before the
action or its done marker. Empty steps are checked too. The gate retains its
existing finally cleanup and partial-record finalizers, and the outer supervisor
still drains owned children. This checks between steps; it does not interrupt an
already executing action or establish a native cancellation/release result.

The installed non-dry retained-R7 test now includes an inert startup step and
three late mutations injected by context construction: STOP, prepared-input drift
and grant change. All refuse before startup/request, produce rc3, and leave no
smoke request or successful done marker. Its 18 isolated cases PASS. Eight
additional direct controls exercise official/smoke recipe selection with valid
ordering or STOP/provider/reserve refusal between actions, including empty steps.
Two older inert fixtures now return actual empty Step objects instead of None,
as required by the real gate's step contract.

Validation: 83 scoped unittest tests PASS (all test_*.py modules here except
historical test_supervisor.py, whose unavailable R9 sources remain outside this
successor's scope). Reproduce with python3 -B unittest discovery per module.
Git diff whitespace validation PASS. Source SHA-256 identities:

- execution_binding.py: `c763ee7db16b13a5f42de820a43645b01599553fdc4a75589a517e7d74ed8306`
- test_execution_binding.py: `4f85eed65097a54bedcf5a5a7807ed03583c3e36e89cdfcf01577df0c309446f`
- test_retained_r7_smoke.py: `78ee118629c0fd99becbffaae4d238e1b38c19cb02b16200e7de8c9afe1e5931`
- test_fullrun_context.py: `70cb97a65e45b733d0a73a77e130d6aa78f0d3bf58d40330782f13e2f143b8d9`

This is model-free software qualification with private admission and inert native
peers. No publisher invocation, native launch, GPU residency, cancellation,
release or parent completion is claimed. Persistent installations, production
and historical seals are unchanged. Next seal retained-R7 with the actual input
locations above and current artifact/provider identities; qualify real native
context integration and publish the owned-native lifecycle row.
GitNexus status/impact refuse in this unindexed sparse lane. Manual inspection
bounds the change to current recipe action wrappers and regression fixtures.
The session bus refuses the unregistered kvu slug; no other outbox was used.
[no-belief: model-free software regression tests]


## 2026-11-19 — current admission in the real native context

The installed retained context reproduced a distinct admission gap: after a
successful boundary call, creating STOP did not make its next check refuse
(`Abort not raised`). The existing per-step and controller wrappers did not
change the native `Ctx` returned by `build_ctx`. Earlier tests supplied an inert
context, so they could not expose this gap.

The explicitly opted-in binding now subclasses that real native context in both
official and publisher-smoke modes. Each existing context boundary rechecks
current custody, grant, provider, STOP/deadline, output identity and reserve,
then runs the retained child-death, sampler, preemption and budget checks.
Refusal latches per instance and raises the existing gate Abort; removing STOP
does not reauthorize a refused context. The native preemption flag is preserved.
The retained context implementation, historical seals and production trees are
unchanged. This does not add checks inside an operation that does not already
call the context boundary; in particular the native startup health loop remains
unchanged. Native interruption and cleanup still need scheduled qualification.

`test_native_context.py` passes 24 isolated installed controls: valid, STOP,
provider loss, grant change, deadline, output mismatch, reserve exhaustion,
sticky refusal, dead child, sampler abort, budget and preemption, in each mode.
The child and sampler peers are synthetic; no server is launched.

A separate installed control passes the actual retained `build_ctx` and
`preflight`, real parser, prompt-set loader, argv validation, binary knob check,
GPU witness installation and native-context check. It uses the actual server,
argv, prompts, R7 records, canonical projection and preload receipt at the
locations recorded above. Enrollment and the unchanged preload verifier check
the accepted metadata and both live model stat tuples before the dry plan.
The witness pins the actual ELF/HIP backend and discovers topology read-only.
`Popen` is forbidden; no model bytes are hashed or loaded and no request is sent.
Admission, provider, grant, clock and affinity are private test fixtures, so this
is not actual keeper admission or complete current artifact/provider custody.
The gate dry plan is not publication and produces no native result.

Validation: two new unittest tests PASS (24 boundary controls and one actual-input
preflight); the existing scoped 83-test suite also PASS. Historical
`test_supervisor.py` remains excluded for its previously documented missing R9
inputs. Reproduce with `python3 -B -m unittest discover -s
docs/reports/kv-cache/kpf18-supervisor-compose-20261119 -p test_native_context.py`.
Git diff whitespace validation PASS. Source SHA-256 identities:

- `execution_binding.py`: `7774351fed859945cf25c129a2a59e799aa2a983285c153df24f38e430e680ef`
- `test_native_context.py`: `8c4cfe63dd82be90729b0bffa780cf29ef890dca1240a5875873f5141d25429c`
- `test_execution_binding.py`: `e0c6e6875859d25bbb9e9daa310a25e90b45ca76dfbac672e9d08cce6930b5bc`

No persistent successor, publisher smoke, native/GPU run, cancellation/release
or layout verdict is claimed. The result-bearing task this turn is the
reproduced native-context defect and qualified fix; publication remains next.
Seal actual artifact/provider custody in the retained-R7 successor, then create
the lifecycle launcher and publish its GPU row using the publisher's smoke.
GitNexus status/impact refuse in the unindexed sparse lane; manual review bounds
the change to the opt-in native context and its tests. Session-bus drain refuses
unregistered kvu; no other session's outbox was used.
[no-belief: model-free software regression tests]


## 2026-11-19 — interrupt admission loss during retained native startup

The retained `Server.start()` health loop never checked its current context.
An isolated negative control invoked that unchanged method with inert native
peers and created STOP in a successful health response: it returned without
Abort. The corrected opt-in binding installs a Server subclass alongside the
current native Ctx. It preserves the startup recipe and checks the context
before launch, after linkage and prelaunch sampling, on each health iteration,
after the HTTP response, around read-back and after residency sampling. Refusal
uses the existing sticky native Abort. It does not retry or signal a process.
Captured children remain in `ctx.own_children` for existing gate/supervisor
cleanup. Before a child exists, refusal stops the prelaunch sampler; a secondary
sampler-stop exception cannot replace the original refusal.

`test_native_context.py` passes 16 installed startup controls (eight in each
admission mode): valid startup, STOP during linkage, prelaunch sampling, false
and true health responses, read-back and residency, plus provider loss during
health. No real child, sampler, HTTP call, sleep or model/GPU work is used.
Controls assert launch suppression, absence of later stages, retained child
registration, sampler ownership, prelaunch sampler stop and sticky refusal.
The existing 24 native-context controls and actual-input read-only preflight
also pass. Reproduce with `python3 -B -m unittest discover -s
docs/reports/kv-cache/kpf18-supervisor-compose-20261119 -p test_native_context.py -v`.
The startup method itself performs the real retained orchestration with inert
peers; this is software qualification, not actual native cleanup or admission.

SHA-256 identities:

- `execution_binding.py`: `19d2063ad8bdaba0e90fcd132f603c11d26ec89b83c0c0b55bf9521e4c52608a`
- `test_native_context.py`: `07d4d2715490334899efa22a15463becb915a9dd49576070d36efcf95824c8cb`

Checks occur around bounded operations; they do not interrupt the retained
120-second linkage subprocess or five-second health request mid-call. Existing
bounded sleeps remain. No persistent installation, historical seal or production
source is changed. Current artifact/provider sealing and publisher smoke remain
required before scheduling native lifecycle qualification; no GPU row or parent
completion is claimed. GitNexus status/upstream impact are unavailable because
the sparse lane has no index. Manual review bounds the change to the opt-in
Server binding and its tests. No new measurement producer is introduced.
[no-belief: model-free software regression tests]

Broader validation: all 86 unittest tests outside historical `test_supervisor.py`
PASS; its previously documented unavailable R9 inputs remain excluded.
`git diff --check` PASS. Session-bus drain refuses the unregistered kvu slug;
no other session outbox was used.


### 2026-11-19 — seal and check the native application DSO closure

Actual ELF inspection exposed a publication prerequisite defect: the accepted
server path is a 17,984-byte wrapper. `readelf -d` names
`libllama-server-impl.so` as DT_NEEDED; that implementation names
`libllama-common.so.0`, `libmtmd.so.0`, `libllama.so.0` and ggml libraries.
The previous eight-role execution inventory required none of those four
application libraries. Replaying HEAD's pre-fix `custody()` in memory against
an eight-role private inventory returned success. No native binary was run.

`execution_admission.ROLES` now requires twelve roles: Python, shell, flock,
server, the four ggml libraries, server implementation, llama, llama-common
and mtmd. Old incomplete execution inventories refuse before driver import.
After retained `read_back()` succeeds, the current Server startup additionally
requires all eight application DSOs in the captured child's `/proc/PID/maps`.
Each role must have a distinct device/inode, the expected resolved path and
sealed SHA-256. Missing, deleted, replaced, aliased, drifted and extra
application mappings refuse. Birth ticks bracket the read; zombies refuse.
The readback records the proved paths, hashes, devices and inodes. A mapping
failure latches native-context Abort before client exposure or residency
continuation and leaves the captured server registered for existing cleanup.

Seven new model-free tests cover the complete closure and duplicate mapping
segments, each of eight missing mappings and content mutations, replacement
inode, deleted and extra application mapping, aliased roles, absent pin,
changed birth and legacy inventory rejection. Installed startup controls now
include mapping refusal in both admission modes (18 isolated startup controls);
24 existing native-context controls and actual-input read-only preflight also
pass. Native peers and mapping callback in those installed startup tests are
explicit private fixtures; the seven mapping tests exercise the real verifier
against synthetic proc files and distinct artifacts.

Validation: `python3 -B -m unittest discover -s
 docs/reports/kv-cache/kpf18-supervisor-compose-20261119 -p 'test_native*.py' -v`
(10 tests); the other scoped test files excluding historical
`test_supervisor.py` pass (83 tests), 93 total. The historical exclusion remains
its documented unavailable R9 source, not a claimed pass. No model content was
hashed or loaded. System/ROCm library custody is outside this application DSO
closure; no persistent installation, native cleanup, GPU residency, publisher
smoke, cancellation or layout verdict is established. Parent KPF-18.0d remains
open and no row was published. Next seal actual provider/artifact inputs using
the twelve-role contract, install the R7 successor, implement its lifecycle
launcher and publish through `publish_row.py`.

Actual ELF identities, existing files under
`/mnt/raid0/llm/kernels/builds/gpu-20261020-a1f0c8cf9/bin/` (SHA-256):

- `llama-server`: `2be7a16ed6d3712d82a36c668417b4dcec8d9cadd13a682e069cb4d57b9d0635`
- `libllama-server-impl.so`: `58e8905f269b9e6f6f38354f826ea83cbaf9b7f9a9d76e502ec54840394f9269`
- `libllama.so.0`: `33bf73eaedfee5a52aa07312d0d12431133e23c54d411744e7bd51bccf375f64`
- `libllama-common.so.0`: `c02f4c9f8c051c7ec314179d52436d13f97dd873d6a0316f616f8789f16d3989`
- `libmtmd.so.0`: `e823b5ec2bb280e2fb74d68acbcfb5a19c2ba530e9af9292e3cf9b0fc0ee92e2`

Source identities (SHA-256):

- `execution_admission.py`: `4911a561b6eaaece01d3eeec1276d78850bd25d7fa23e5802e9c397a2d5653eb`
- `execution_binding.py`: `87ed7b50b9ebe0453cb74c8fd6ac76f38b697e098b0839f48721434c06757aea`
- `test_native_custody.py`: `88e0b08f8bde6edb7bcf42f999e73175b90fb412d649056abdc38c50fa3916b4`
- `test_native_context.py`: `86b53074044a7ead996e35870bfd125db0b717630a4e5a290bc43b3bce8ce1db`

GitNexus status and upstream impact both refused in this unindexed sparse lane;
manual review bounds changes to current execution custody, opt-in native
startup and tests. Session-bus drain refused unregistered roster id `kvu`;
no other outbox was used. [no-belief: model-free software regression tests]

### 2026-11-19 — deployed publisher lock pair and native lifecycle publication

The deployed `filler_run15.sh` deliberately changes publisher GPU smoke to a
**shared** GPU-quiet claim (lines 124–131 and 558–560), then its inner shell
holds the exclusive `gpu_device.mi210_0.lock` through fd9 (lines 426–432).
The existing preparation required an exclusive GPU-quiet writer in both modes.
A negative control passes the actual shared observation shape to the unchanged
retained validator and reproduces `exclusive canonical GPU lock absent`.
No shared claim was acquired on the official host for that control.

New `publisher_provider.py` is selected only in the publisher-smoke successor;
the official successor retains the original exclusive provider unchanged.
Smoke requires its real inherited namespace and row identity, exactly one
kernel-attributed shared GPU-quiet owner, the same-UID ancestor's matching
role/tag/birth record, and a closer ancestor running this row's exact inner
engine invocation with the canonical exclusive device lock on fd9. It reads
fdinfo ownership, rather than treating the exited `flock(1)` PID as the live
owner. Device numbers, inode, descriptor target and WRITE-lock record must
agree across the capture. Source, process-birth and lock-file identities are
rechecked, and subsequent boundaries must retain the same pair. It acquires,
upgrades, releases and signals nothing. Shared ownership is recorded as shared.

Twelve provider tests PASS: actual old-provider refusal, correct pair/recheck,
mode and namespace refusal, ambiguous/foreign/unattributed holder refusal,
wrong inner engine/row/birth, missing/READ/waiter/wrong-device/wrong-inode locks,
descriptor replacement during capture, quiet-file replacement and source drift.
Private proc and attribution fixtures exercise the capture; two real temporary
lock controls check the kernel fdinfo format and inherited lock after
`flock(1)` exits. Those temporary locks are test-owned and do not touch either
canonical host lock. These tests establish software behavior, not live keeper
admission or native GPU execution.

`prepare_lifecycle.py` verifies the retained R7 and canonical projection pins,
accepted preload receipt and both current model stat tuples without reading
model bytes. It seals twelve actual execution artifacts, the five current
orchestrator provider sources, prepared argv/prompts and prerequisite paths,
then installs separate official and publisher successors. Sources remain
referenced at their existing paths. The publisher prohibits sealing its
redeployed engine; its PASS record will bind that engine identity instead.
The installed successors' own direct launch scripts remain disabled; only the
current rowflow launcher reaches their admitted supervisor.

`lifecycle.py` chooses the sealed mode, calls the actual supervisor, and writes
its progress result only after owned-child drain has returned and native work
exists. Smoke additionally requires a returned token and own-VRAM samples;
full execution preserves the existing group-3 conformance record, including
an INVALID verdict. It never translates that verdict into parent completion.
Four inert-supervisor wrapper tests PASS for ordering, failed native work,
refusal, cleanup exception, mode drift and existing-result refusal. The existing
93 scoped tests also PASS (103-test suite with the initial ten provider tests;
the expanded twelve provider and four wrapper tests pass separately).
Historical `test_supervisor.py` remains excluded for its documented missing R9
inputs. `git diff --check` PASS.

Publication: `publish_row.py` initially refused the handoff's absent stop rule;
the owned parent now states its lifecycle question and answer/futility rules.
The second preflight refused an engine digest in the execution seal; the
superseded private attempt was removed and recreated without engine pins.
Neither refusal ran a smoke. Final publish accepted
`kvu-kpf18-native-lifecycle-r1-20261119` and queued its GPU smoke because the GPU
was busy. **No smoke PASS, ready GPU row, native cleanup, GPU residency,
cancellation/release or layout verdict is claimed.** There is no in-turn wait.
The accepted spec requests the existing full group-3 recipe in a 9000-second
window, on `mi210_0,184-191`; publisher smoke uses its four assigned CPUs and
one native request. Parent KPF-18.0d stays open.

[Source, installed-manifest, launcher and spec SHA-256 identities](lifecycle-qualification.json)
bind the existing files without copying logs, binary bytes or source trees.
The publisher warned about lane-relative code; these committed files retain
fixed paths and their seals refuse drift. Consume the smoke PASS/FAIL event
when dispatched; independently advance the remaining CPU inference tasks.
GitNexus status/upstream impact were unavailable in this unindexed sparse lane;
manual review bounds changes to new opt-in provider/launcher code and tests.
The session bus rejected the unregistered kvu slug; no other outbox was used.
[no-belief: model-free software regression tests; GPU smoke queued]
