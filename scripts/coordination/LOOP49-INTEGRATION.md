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
Inference-profile complete fixtures write `first-request.json` with real `ok`,
`n_ctx`, `prompt_tokens`, `measured_tok_s`, `job_floor_gib`, plus `result.json`
(or manifest `qual_result_file`). Native-diagnostic complete fixtures write a
result only; they do not need inference metrics. Deadline fixture writes
`partial.json` with `partial:true`
and itself exits 75. Engine checks the actual completion predicate and actual
return codes; a killed process alone does not prove resumability. Result dirs
are separate nonce destinations; the native results directory is untouched.

`qualification_profile` defaults to `inference`, preserving the real first-request,
`n_ctx`, prompt-token and throughput-window checks. `native-diagnostic` is a
control-only profile: it never accepts fixture rates as feasibility evidence. It
requires `qual_complete_cmd_sha256` to pin the completion predicate and
`qual_fixture_items` to bind the fixture's declared item count, the pinned
fixture identity, successful COMPLETE_CMD execution, a hashed result inside the
nonce's results directory, and a second fixture run that itself exits 75 with a
hashed partial marker inside that nonce's partial-results directory. This proves
launcher/control behavior only. Its disk-floor record is explicitly a diagnostic
policy control receipt, not a measured workload disk result. `tokens_per_item`
and `n_ctx_required` are inference-profile requirements; diagnostic `items`
counts fixture work units and may be 28 without inventing token/rate fields. It
cannot qualify C6's missing 28 workload cells or establish production
throughput; C6 remains held pending honest full-run measurements.

Inference manifests pin `qualification_model.id`, an absolute `path`, and the
model file's SHA-256. Static qualification verifies the file bytes; the issued
binding and pass receipt carry the resolved model path and actual bytes hash, so
model replacement or path drift invalidates qualification.

Both profiles bind the fixture rc75 marker at `<nonce>/grants/<id>.deadline.ended`
and the outer launcher's final `<nonce>/grants/<id>.ended`. The receipt records
each path and SHA-256. Verification requires the first marker to say rc 75,
partial true, qualification phase, granted true, and the final marker to say rc
0, partial false, qualification phase, granted true. The final marker is
captured after the launcher exits and writes it.

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

The D2 consumer is `science_quota.py`; it reads filing records, never READY/hour
counters. Collect directly from retained artifacts and score in one command:

```bash
python3 scripts/coordination/science_quota.py \
  --collect-filed-dir "$FLAGS_DIR/filing-done" \
  --ended-dir "$FILLER_GRANTS_DIR" \
  --manifest-dir "$READY_MANIFEST_DIR" \
  --nonce-store "$WS58_NONCE_STORE" \
  --allowlist "$WS58_ENGINE_ALLOWLIST" \
  --policy "$WS58_POLICY" \
  --flags-dir "$FLAGS_DIR" \
  --normalized-out "$RETAINED_ROOT/science-quota-input.jsonl" \
  --as-of 2026-11-01T00:00:00Z
```

`--ended-dir` and `--manifest-dir` are searched recursively; duplicate
manifests for one id are treated as absent. Collection derives identity,
outcome, verdict, and event time from each `.FILED`, then binds any matching
terminal and canonical `QUAL-<id>.json` receipt. The verifier inputs are needed
for qualification credit. Omit `--normalized-out` to score without retaining
an intermediate JSONL, or use positional `<normalized.jsonl>` for a later
score-only replay. The collector accepts no caller-supplied score flags.

The scorer reads each `source_receipt.path` and requires exact
bytes/SHA equality with the embedded retained receipt, matching id, outcome,
verdict and filing time. A score also requires the retained production `.ended`
and `.grant` bytes; a positive verdict additionally calls the canonical
qualifier verifier against the actual `epyc.qual.pass.v1` receipt, nonce store,
manifest and deployment policy. Caller booleans alone cannot create science
credit. Missing provenance scores zero with an explicit `unscored_reasons`
count. The three real legacy receipts in
`tests/coordination/fixtures/loop49/science-receipts.jsonl` currently yield
**0/3 scorable**: their old terminal records do not retain LOOP49 production
phase/grant proof. No qualification or verdict is inferred retroactively.
Qualified production `DIAGNOSTIC-RESULT` with a verdict counts +1; a granted
production `FAILED-RUN` counts −1.

Tests: the source suite (including historical receipt regressions) is offline
and uses local fixtures: it runs no model inference and consumes no production
compute grants. Qualification fixtures exercise synthetic local grant records
only. Export `LOOP49_TEST_ARTIFACTS=<retained root>` so generated artifacts remain
available. Run under the CPU region lock on one quarter (for example CPUs 0–23,
q0) with an indefinite acquisition timeout (`--timeout-s 0`). The lock resets
its child's working directory, so explicitly change to the exported source root:

```bash
export WS58_ROOT=/mnt/raid0/llm/worktrees/mains/codex-refactor-01a16fc3
export LOOP49_TEST_ARTIFACTS=/mnt/raid0/llm/tmp/refactor-01a16fc3/loop49-source-tests
CPU_LIST=0-23
/workspace/repos/epyc-orchestrator/scripts/region-lock run --cpu-list "$CPU_LIST" --timeout-s 0 --role build --tag loop49-qualification-tests -- \
  bash -c 'cd "$WS58_ROOT" && /workspace/repos/epyc-orchestrator/.venv/bin/python3 -m pytest -q tests/coordination/test_loop49*.py tests/coordination/test_science_quota.py'
```

No test cleanup deletes or renames fixtures. These component regressions are not
the report's full keeper dry-run acceptance matrix.

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

`failed_run_rollup.py` only classifies forensic outcomes. Its output is non-authoritative for science quota; score fields are stripped, including caller-provided values. Use `science_quota.py` to verify retained evidence and emit scores. Production terminal ownership is passed from the verified manifest explicitly; ambient `WS58_OWNER` cannot supply ownership. Recovery re-verifies the retained manifest before passing its owner.
