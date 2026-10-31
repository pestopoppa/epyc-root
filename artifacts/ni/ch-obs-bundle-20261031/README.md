# CH-OBS-BUNDLE — native process identity preflight

## Source and task custody

- Original task: `handoffs/active/autokernel-champion-aggregate.md:1061` (ROOT task text reproduced below unchanged; source checkbox remains MAIN-owned).
- Research producer source: commit `4b4207f3b2b0` (`Record AutoKernel loop process identity`), published in Research `origin/main` at `ae68d27a9063ed96ae0c0d86a50000ac3ef0ba6b`.
- ROOT consumer source: commit `20fe66dc30508150083514aa8ca104af2b96d335` (`Guard champion bundle preflight with process identity`), integrated first with ROOT `origin/main` at `b88fccd3118c6195106949e3b217a1784479bfae` (merge `7d67fb84a301d384a8ba9807a5ce48da60ea3ffb`), then with fresh `origin/main` at `b4d4739f1092caf1ca33e973547d1feb522b08b5` (merge `e51583891f8b702bd6c8046255d6984986d2a0a4`).
- Exact-byte C5 reference fixture remains SHA-256 `86095a308ff4834bc37b4b23190b6eeee8f37c24bebd96a2af1c66d38bc15327`.
- The reviewed C3/C4/C5 verdict helpers are preserved. The existing C5 Q38FN sign-only acceptance remains unchanged.

Original checkbox/task text:

> - [ ] **CH-OBS-BUNDLE — make the runnable C3/C4/C5 bundle preflight three-valued before its next operational use.** `scripts/champion/fold_gates/bundle_gate_c{3,4,5}.sh` currently treat an empty or failed `ps -eo args= | awk ...` pipeline as no DS41/Q38FN AutoKernel loop. A missing/unreadable process channel or argv drift must instead refuse launch (`unobservable` means busy for this exclusion check). Adopt `scripts/coordination/observer_guard.sh` with two independent identity channels and an `observe` entrypoint; validate present/absent/blind/disagreement with synthetic stand-ins and prove preflight never launches while blind. Determine the authoritative second channel from the actual loop lifecycle before choosing it; do not invent a heartbeat relationship. Preserve the reviewed verdict helpers and Q38FN sign-only semantics, do not run a real inference gate, and do not rewrite historical/adopted TMP scripts. Register the tracked runnable copies as `v1` only when the behavioural proof passes, then close this task. The exact-byte original C5 fixture stays an exempt reference input. This task records the existing exclusion-observer gap discovered by the normal publication hook; portable verdict regressions already passed, and that passing proof is not a claim about this preflight's liveness observation.

## Implementation

The Research status writer now adds an atomic `process_identity` tuple to native loop status: positive PID, `/proc` start ticks, boot ID, writer source identity, and canonical store path. `run.py` supplies the native writer identity through its existing lifecycle publication call. This tuple is operational process-generation dependency metadata; it is not measurement evidence or a scientific warrant.

ROOT `observer_guard.sh` folds two channels: checked `ps -eo pid=,args=` output and the native status identity checked against the current boot and `/proc/<pid>/stat`. The observer does not infer absence from heartbeat age or terminal status. Missing/legacy/malformed records, an unreadable or unenumerable process channel, a missing/unreadable proc root, permission/parse failures, or channel disagreement are `unobservable`. A missing individual PID under a successfully enumerated proc root proves that recorded generation exited. Preflight treats every state other than agreed absence as busy.

C3/C4/C5 `--execute` region-lock handoff now invokes `/bin/bash` on the resolved absolute path of the same tracked script, passing `--inside` after the lock. This closes the stale-TMP-copy bypass. C5 applies the loop exclusion only to item `b`, preserving its reviewed scope.

The three runnable tracked gates are registered as observer contract `v1` only after the synthetic shell suite passed. The exact-byte original C5 fixture remains exempt and was not edited. No historical/adopted TMP script was edited.

## Validation

Commands ran against the actual checked-out source; no live inference, gate, kernel, store, API, or shared process was launched or changed.

- Research: `python3 -m pytest scripts/kernel_rnd/autokernel/loop/test_status.py -q` — **39 passed, 2 subtests passed**.
- ROOT: `bash scripts/champion/fold_gates/regression/test_bundle_gate_observer.sh` — **3 gate entrypoints × 10 observation cases plus 3 top-level `--execute` region-lock handoffs per gate passed**. The private lock shim verified the resolved tracked script path. Both disagreement directions, empty process channel, legacy/missing identity, missing/non-directory proc root all refused before the instrument marker. Only synthetic fully observed absence reached the stub instrument.
- ROOT: `python3 -m pytest tests/test_observer_contract.py -k champion_bundle -q` — **6 passed, 29 deselected**.
- ROOT: `python3 scripts/coordination/observer_census.py` — **25 observers registered; OK**.
- ROOT: `bash scripts/champion/fold_gates/regression/test_bundle_gate_verdict.sh` and `.../test_bundle_gate_verdict_c5.sh` — **PASS**, including the C5 Q38FN negative-sign case.
- Commit hooks: observer census passed; one test file checked with zero blocking or advisory findings.
- `git diff --check`, shell syntax checks, and registry JSON parsing passed before commit.

## Host limitation

A read-only `bundle_gate_c3.sh observe` returned `state=unobservable` (exit 3): argv/`ps` channel was absent; the native status channel was unknown. The conservative target enumeration found 3 DS41/Q38FN campaign directories and 8 direct `store*` directories: 7 legacy identities, 1 missing status, 0 native identities. Old statuses remain UNKNOWN; no timestamp or terminal-state retirement was inferred, and no active-target registry was invented. This means the observer correctly refuses on this host until a native loop writes the generation-bound identity. It does not establish actual-host absence or authorize a gate.

## Belief and source-registration boundary

No measurement or verified scientific finding was produced, and no belief checkbox/result tick is claimed. The new tuple is an existing document/artifact dependency identity only. It must not project to `ClaimTuple`, introduce a grading ladder, or claim that the canonical planning-context loop is wired. A concise MAIN-only source-table row draft and the existing-task search result are in `SOURCE-REGISTRATION-DRAFT.md`.

## Exact task text

See the unchanged task paragraph reproduced above. MAIN applies the semantic checkbox and index/source-table edits after reviewing the published native source SHAs.
