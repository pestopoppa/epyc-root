# VB-RUNNER-PATHS-3 engineering review, 2026-10-31

Private CODE lane only: `/mnt/raid0/llm/worktrees/mains/codex-ni-research-code`.
Original base e95a9d2e25c3eeedc7a6f997e608d9bd338cbc31; fetched/fast-forwarded without overlap to 85bf75960 (HR3 prospective archive writer plus R18 replay preserved). No deployment, reload, live capture, kernel operation, or edit in pinned measurement lane. Commit requires main approval.

## Per-site audit

| Original site | Role / concrete disposition |
| --- | --- |
| serving_beliefs.py | Belief feedback writer/reader bridge. Resolve through belief_context -> existing belief_capture.root_checkout, lazily inside diagnostic fault trap. Unnamed/invalid ROOT returns unavailable diagnostics and never aborts measurements. Exact selected adapter path check retained. |
| claim.py | Orchestrator CPU-lock bootstrap import only; no belief writes/reader/decision ledger. Leave unchanged, including compatibility EPYC_ROOT_REPO/worktree-common-dir discovery. Earlier mandatory-root proposal reverted; exact diff confirms unchanged. |
| serial_run.py | Decision diagnostic reopens original serving receipt via selected adapter. Already uses belief_context.resolve_root_repo; it now gets shared resolver transitively, within existing exception-to-errors boundary. No independent hardcoded ROOT remains. No mutation. |
| k35_vision_matrix_runner.py | EPYC_ROOT constant had no uses (rg source check). Delete dead constant; no new unused helper. |
| run_batch_entry.py | B4 topology attestation and autopilot decision gates. Root defaults now lazy through root_checkout; explicit attestation directory remains authoritative. Missing ROOT is verified=false/ok=false with reason. Cached foreign checker/signal modules are refused by exact selected module-file identity. Default dry-run/no-execute behavior retained. |
| laguna_pgpu1_dflash_runner.py | Human promotion proof decision. Resolve selected governance repository using root_checkout; preserve exact canonical relative path, nonsymlink regular file, git tracked/clean HEAD blob checks and all human attestation validation. Existing test overrides still accepted; no human trust relaxation. |
| op2_quiet_window_prep.py | Prep bundle ROOT and measurement-policy source. Explicit --root-repo wins, else EPYC_ROOT; validate via shared helper. Measurement default is selected ROOT/MEASUREMENT.md; explicit --measurement-path unchanged. No inference or policy changes. |
| check_evidence_durability.py | Durability decision candidate-root classification. Replace guessed ROOT candidates with validated named ROOT; absent/invalid ROOT omits guessed candidate and retains absolute artifact-tree scope rule. Existing orchestrator scope unchanged. |

## Compatibility fixes after rejected proposal

1. CPU bootstrap claim.py is restored byte-for-byte to baseline.
2. PlannerFeedback constructor no longer resolves/raises; _load resolution stays inside existing context/exported try traps; run.py passes raw CLI option.
3. Missing/invalid ROOT during prepare no longer throws a second resolver exception from alarm fallback or refused receipt sealing. Critical alarm is explicitly printed UNDELIVERABLE; consumer still raises BeliefContextRefused; sealed receipt is refused with null root_reader and explicit locator error. No guessed fallback, no ready verdict.
4. AutoKernel standalone import works with only scripts/kernel_rnd on PYTHONPATH from arbitrary cwd; source-relative research helper import finds shared resolver.
5. A cached autopilot checker or signal reader from a different ROOT cannot satisfy the selected ROOT's decision gate.

GitNexus status is stale (indexed a0a3df0 vs starting e95); scoped impact outputs: resolve_root_repo LOW/6, raise_alarm LOW/2, seal_receipt LOW/0. Existing prior claim impact LOW/5. This is limited graph evidence; manual full-source and concrete caller review covers run.py/actors.py/serial_run.py, bridge, gate callers and proof consumers. Full reindex not admitted under current live quarter grants; no guard bypass or metadata removal. No rename/refactor.

## Retained validation and incident honesty

All fresh test executions used actual flock prep-locks/32-33.lock, SMT siblings 128–129, OMP_NUM_THREADS=1, 8 GiB address-space cap plus sampled process-tree RSS limit, Python 900 s timeout, OS PID/birth record and absence-after-wait. Admission receipts retain live start/end/non-ended grants and authoritative derived booking classes; GPU host 184–191/disjoint q0 timing do not block R6 CPU prep. No quarter lease claimed. Every run has timestamped log, JUnit, source hashes and process receipt; none overwrites prior evidence.

The earlier worker's 39 failed/190 passed raw log was overwritten. It is unrecoverable and cannot be certified as fixture-only. Its later 240-pass log is preserved at the old handover path. We do not claim to recover the 39 identities.

Controlled reconstruction with *baseline e95 test files* against reviewed source produced 37 failed/199 passed, retained `20261031T104620.301951Z-basefixtures.*`. `base-fixture-classification.json` lists each of the 37 individually. Five failures patch removed DEFAULT_ROOT/FALLBACK_ROOT fixture internals and express obsolete fallback behavior. Remaining 32 fail because synthetic ROOT fixtures lacked the shared resolver's required scripts/vidya/adapters directory, preventing mocked children from being called. Fixture adjustments add that directory and preserve existing scientific/consumer assertions; replacement root tests explicitly prove named-root precedence, refusal and no fallback. This controlled reproduction is not the lost 39-failure run.

Reviewed source with updated fixtures and seven additional negative controls: **247 passed**, `20261031T105013.792605Z-current.*`, 5.31 s pytest, 5.65 s elapsed, peak tree RSS 161337344 B; PID 3590800 absent after wait.

Extended concrete callers: **313 passed/4 failed**, `20261031T104645.874770Z-extended.*`. Four serial-run source-history cases fail at missing original serving export, with `prospective serving capture does not rederive`. Controlled comparison restoring *every patch source file to e95* reproduces all four identically: `20261031T104919.138593Z-baseline4.*`, 4 failed/9.07 s. Automatic finally restored all private patch bytes. `baseline4-source-git-manifest.json` separately identifies baseline source via git objects. This is a real preexisting capture defect; native capture/finish semantics are unchanged here. Main informed for scope decision. Do not report the extended suite green or dismiss these as fixtures.

Integrated validation after peer HR3 fast-forward: pending final receipt appended below.

Integrated run `20261031T105047.265820Z-integrated.*` proves focused 247 still pass atop peer 85bf75960; total 251 passed/1 failed. The added HR3 test defaulted AK_HISTORY_ROOT=/workspace, where ak_history.py lacks new append_belief_measurement. Isolated HR3 rerun with explicit AK_HISTORY_ROOT=/mnt/raid0/llm/views/epyc-root-main: **5 passed**, `20261031T105213.612670Z-hr3.*`; retained PID 3607768 absent, peak tree RSS 68362240 B. This is not permission to activate HR3 on any long-lived loop.

New peer archive.py also introduces `_VIDYA_ROOT = Path('/workspace')`, a ninth ROOT belief-writer site outside the original eight. Main notified immediately; scope guidance pending. No source change made to peer archive writer yet. `review-integrated.patch` is exact pending-review patch atop 85bf75960.

## Ninth writer scope ruling and correction

Main ruled the newly integrated archive writer is part of the original audit. Published C3 coordination notice in `/mnt/raid0/llm/tmp/compute-flags/codex-channels/codex3.md` and own `hr3-root-coordination.SENT.flag` BEFORE editing. `_publish_ak_history` now resolves lazily through existing belief_context/root_checkout, retaining explicit `_VIDYA_ROOT` test/embedding override, then AK_HISTORY_ROOT, then existing EPYC_ROOT_REPO / EPYC_ROOT precedence. Invalid explicit ROOT refuses without fallback. Existing selected adapter-file identity and original HR3 fields/counters/producer/append contract are unchanged. All failures remain inside the already-existing `record` diagnostic try after durable experiment commit.

New tests prove actual record commit survives missing/invalid ROOT with explicit warning; explicit AK_HISTORY_ROOT wins and passes original payload unchanged; foreign cached adapter is refused before append. Peer HR3 test uses explicit AK_HISTORY_ROOT when supplied, otherwise the new named-root path (removed test's own /workspace fallback). Qualified current-adapter integration: **272 passed**, `20261031T105454.963428Z-ninth.*`, 3.65 s pytest, PID 3633825 absent after wait, peak process-tree RSS 106323968 B. Includes all original focused tests, real HR3 exporter/record path, history field tests and new writer controls. This supersedes the earlier pending-scope paragraph; no reload or live activation occurred. Ninth delta is `ninth-writer.patch`.

## Exact serial capture rederivation diagnostic

Diagnostic-only pytest plugin wraps original `finish`/`export` without changing any result/refusal. It snapshots original native body and compares at export; raw evidence appends to `native-capture-mismatches.jsonl` (first hash-only probe20 records, then native-snapshot probe20). `20261031T105610.473823Z-mismatchone.*` retains four failing test executions and process receipt. All20 new native diffs are exclusively `/same_code_tripwire`: absent when capture was sealed, present at export with schema `epyc.autokernel.same_code_tripwire.v1`, status `unavailable`, null anchor/candidate code digests and work_key, reason `code digest or measured work identity unavailable`. That post-seal metadata changes native_sha256 and cascades capture_id/capture_sha256 and the six derived row hash/ID fields; no measurement values or original capture inputs change. This identifies the concrete mismatch without inferring a kernel bug or dismissing dirty-worktree identity uncertainty. No broader capture fix made under main ruling; full extended suite remains honestly non-green.

Source corroboration: same_code_tripwire.py:38 `ObservedComparison.to_dict()` merges `same_code_tripwire` into the already-sealed original comparison; serving_beliefs.native_body excludes only belief_capture/surface/baseline_scope. This explains the exact post-seal native-hash mismatch without relying on private checkout cleanliness as evidence.


Main approved final 18-file source delta; normal hooks passed and serialized nonforce push published research 4ede8b2fa8233984705c550c0e7fdc36a9e98433 to origin/main. Private CODE lane clean. See CLOSEOUT.md, publication-receipt.json, ROOT-CAPSULE-DRAFT.md and publication-success.SENT.flag. No ROOT edits or runtime activation.
