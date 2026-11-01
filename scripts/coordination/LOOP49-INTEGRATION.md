# LOOP-49 candidate integration contract

Operator rulings: **D1 hard gate**, **D2 science quota**, **D3 one canonical
allowlisted engine**, **D4 READY-WAIT-DISK parked and uncounted**. No candidate is
installed or pinned by this change. `docs/reports/failed-run-audit-20261031.md`
is the unchanged forensic source; its suggested deletion and D4 recommendation
are superseded by the operator's retention rule and D4 ruling.

All qualification artifacts are retained in `qual/<nonce>`. Exclusive artifact
creation rejects reused nonces, row receipts and `.ended`; no cleanup removes or
renames fixtures. Qualification `.ended` records say `phase=qualification` and
`granted=true` only for their synthetic grant: filers must also require a
production phase before attributing consumed science compute. An engine refusal
before any grant records `granted=false`. SIGKILL needs keeper recovery through
`failed_run_rollup.record_launcher_dead`: it verifies PID **and** `/proc` birth,
then exclusively creates the receipt; it never signals a reused PID. The
launcher's immutable `<id>.launcher.json` records id, PID/birth, phase, and
grants directory; recovery refuses path/id mismatches and files the stored
phase. The v7f keeper candidate checks `ps` plus birth on each tick and invokes
recovery as soon as the original launcher is absent or PID birth changes,
rather than waiting for the ordinary terminal grace period.

Keeper calls `qualify_launcher.py run` with `--manifest`, `--nonce` (32+ hex),
`--regions` (two allowed SMT sibling CPUs), `--flags-dir`, `--nonce-store`,
`--allowlist`, `--policy`, with `WS58_ROOT` supplied by keeper configuration as
the canonical deployment root. The canonical engine path is always
`$WS58_ROOT/scripts/coordination/filler_run14.sh`; an imported copy of the
qualifier cannot nominate its own adjacent engine. Nonce store must be protected by a separate keeper OS
identity; same-UID workers are **not** a security boundary. `run` creates immutable
issued and sealed records. `verify --fingerprint-now` is mandatory immediately
before starting a launcher; `verify` without it provides the cheap per-tick
check. The receipt is read from `<scratch_root>/qualification/QUAL-<id>.json`.
Do not pass `--out` except that exact canonical path.

The allowlist is exactly
`{"kind":"epyc.engine-allowlist.v1","engines":["<canonical-shell-sha256>"]}`.
Engine must resolve to this lane/deployed root's `scripts/coordination/filler_run14.sh`.
The receipt also binds the Python runtime and checker hashes, disk policy,
launcher/job/fixture/source manifest and namespace. Changes require a fresh
qualification under a fresh row id, never a forked packet engine.

Launchers must forward `WS58_*`, `FILLER_GRANTS_DIR`, `FILLER_*` through their
actual chroot/env line. They call the same canonical engine for both production
and qualification. Add repeated `--requires-tool` arguments for every manifest
`requires_tools`. Fingerprint mode runs that same launcher and prints exactly
one engine namespace JSON record without grant polling. Host chroot launchers
set `WS58_EXEC_MODE=host-chroot` inside the chroot.

Fixture job receives `FILLER_QUAL_FIXTURE`, `FILLER_QUAL_PHASE=complete|deadline`,
`FILLER_RESULTS_DIR`, `FILLER_CPUS`, `FILLER_DEADLINE`, `FILLER_END`, `FILLER_ID`.
Complete fixture writes `first-request.json` with real `ok`, `n_ctx`,
`prompt_tokens`, `measured_tok_s`, `job_floor_gib`, plus `result.json` (or manifest
`qual_result_file`). Deadline fixture writes `partial.json` with `partial:true`
and itself exits 75. Engine checks the actual completion predicate and actual
return codes; a killed process alone does not prove resumability. Result dirs
are separate nonce destinations; the native results directory is untouched.

Before grant creation, the writer must invoke
`loop49_keeper_gate.py before-grant --manifest <current-manifest> --row-id <id> --regions <actual-grant-regions>`
and require exit 0 immediately before its exclusive `.grant` creation. Both
`--row-id` and `--regions` are mandatory and bound to the exact writer row and
allocation. This re-verifies the receipt, launcher fingerprint, manifest
bindings, conflicts, and free space on the manifest's actual `scratch_root`
filesystem at the issuance boundary. Re-run after any wait; an earlier
`before-arm` result is not a grant authorization. Legacy/rearm/carry-over
manifest markers are refused; retries use a new qualified id and manifest.
Before arming, keeper applies `scheduling_state` against all READY, queued and
live manifests for port conflicts, and live/queued manifests for exclusive
classes/shared state. Current helper's `active` list is caller-owned; keeper
must refresh it after each accepted arm. Disk uses policy floor plus output
estimate plus 2 GiB; WAIT-DISK writes no grant and never counts toward READY
depth, science quota or failed-24h.

Export `WS58_READY_MANIFEST`, `WS58_NONCE_STORE`, `WS58_ENGINE_ALLOWLIST` to
production launcher. Engine cheaply re-verifies the qualified receipt before
polling (no synthetic admission at grant time). Keeper must retain old ready
manifest paths or update forwarding after moving them to armed. It must verify
namespace again at the actual writer grant boundary, not only queue enrollment.

Outside-root changes still required: ws58_arm-v2 / grant_ok_launcher must parse
canonical Python-engine argv and verify its PID birth, and every installed queue
writer must call the `before-grant` command above (the checked-in helper does not
intercept external writers by itself). Existing queued legacy rows and
`carry_over`/`rearm_rc75` paths cannot bypass D1: disable those paths or migrate
rows to fresh qualified ids. `.ended` is never overwritten or removed; resume is
always a new id. After SIGKILL, invoke
`loop49_keeper_gate.py recover-dead --identity <pid-birth.json> --ended <path>`;
it creates the terminal record only after PID and `/proc` birth mismatch proves
the original launcher is gone, and never signals a PID. Class-specific GPU claim
semantics and cross-role disjoint placement must be exercised under a granted
integration fixture before use.

Filer reads structured native/validator records with explicit forensic
`root_cause_family` A..I. Validator replay uses `failed_run_rollup.py --workdir
<retained-output-dir> --validate-only <argv...>`; only the validator runs. A
native complete result with validator failure is `VALIDATOR-FAILED`, retained
for repair without compute retry. Owner retirement is WITHDRAWN; job diagnostic
results are DIAGNOSTIC-RESULT. Science score counts qualified production grants
ending 0/75 with verdict; failed production grants subtract, publishes score 0.

Tests: 20 retained receipt regressions in `test_loop49_qualification.py`; these
are component regressions, not the report's full keeper dry-run acceptance
matrix. They have not been executed without an explicit compute grant. Run only
with `LOOP49_TEST_GRANT=<issued grant>` and `LOOP49_TEST_ARTIFACTS=<retained root>`.
No test cleanup deletes or renames fixtures.

Manifest includes `row:{"path":"<ready/<id>.row.md>"}` (or a string path).
Before qualification, the pinned row's id, region expression, booking class
when declared, requested and minimum windows, reserved RAM, process limit,
output estimate, scratch root, and CPU claim must agree with the manifest.
A relocatable claim must use the same `any-*` value in both; the synthetic
copy substitutes the exact qualified CPU scope for real admission. The row
hash is bound, then a retained nonce-bound row copy changes only the synthetic
window and CPU scope; `dryrun_check admit` runs on that copy under the real row
id before fixture side effects. This preserves the real admission
implementation without calling the retired T1 grant-time proof gate. Native
row custody and source paths are unchanged.

Belief source wiring is tracked as `VB-LOOP49-QUALIFICATION-WIRE` in
`handoffs/active/vidya-belief-substrate-program.md`. The row is intentionally open:
registration and qualification-receipt production do not establish a reader or
planning-context canary.
