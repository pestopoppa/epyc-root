# SCG-TEST-ORDER accepted partial source — 2026-10-31

APP main `2f5c05013ccc80d549635878f260bddf0c172452` adds one23line fixture. Normal hooks and serialized nonforcing main push passed. The original SCG checkbox remains OPEN because full-unit validation is incomplete; no quota tick or deployment claim.

Actual leak: `test_autopilot_sequential_wiring._run_loop_inner_seq_harness` invokes real loop startup, which leaves the global promotion provider capturing its FakeJournal after the test monkeypatches unwind. A following baseline median test seeds rawquality2.95 instead of promoting its representative2.8. Private `MonkeyPatch.context()` now restores incoming provider and warning state after producer-test teardown. Production semantics/assertions stay unchanged.

Evidence (all relative to this packet):

- Original badorder: `validation-20261031T105601Z.log` (1pass/1fail,2.95!=2.8); reverse: `validation-20261031T105651Z.log` (2pass). Matching provider trace shows the native `_install_promotion_guard_scope` closure with FakeJournal.
- New bad/reverse: `validation-20261031T105728Z.log` / `validation-20261031T105757Z.log` (each2pass); trace shows provider removed.
- New root-conftest bad/reverse: `validation-20261031T110129Z.log` / `validation-20261031T110226Z.log` (each2pass).
- Bothcomplete modules: `validation-20261031T105829Z.log` (71pass).
- Incomingnativeprovider/warning preservation: `preserved-provider-20261031T105923Z.json` and matching validation log (1pass).
- `make gates`: `validation-20261031T105950Z.log` PASS; finalruffcheck PASS. MAIN directed dropping unrelated formatter hunks: original/finalformatdiff logs each show the same2preexistinghunks; no addedfixtureformatdefect.
- Fullunit: `validation-20261031T110019Z.log` (19,818collected,374pass/8skip/1fail). FirstAP54 fake-request lacks `.headers` now read by `_request_with_source_header` in chat.py218, before the changedproducerfixtureexecutes. C3 separately notified for owningfixture repair; no full-suite-green claim.
- Normalhookscommit: `validation-20261031T110340Z.log`; serializedpushverified: `validation-20261031T110402Z.log`.

`REVIEW.json` binds exact source/proof; `ADMISSION.json` binds currentgrants and validator7ddfaa6b. All timestamped runner receipts preserve PID,birth,RSS,exit and confirmedabsence. R6physical34-35mutex/SMT130-131,OMP1,8GiB/900s sampledlimits. EarlierFAIL/stoppedlogs retained separately. ROOT progress/agentlog/handoffpartial draft is `ROOT-FILING-DRAFT.md`; only owningMAIN applies it. C3notification and ownSUCCESSflag retained.
