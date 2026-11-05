# KPF-17 source-bound impact prerequisite

Request native upstream impact of test_partial_restore_busy_source_one in tests/test-save-load-state.cpp, exact integrated candidate 8952a0f693fb923918157eb25117641b74766230. Its retained test-only patch changes this function and adds a new helper; the helper does not exist in the unpatched graph. The include and new header require separate manual review. Native graph target must match name and file unambiguously.

Whole-host CPU, 7200 s, 48 GiB and 150 GiB disk floor; stop on source drift, missing or ambiguous target, HIGH/CRITICAL, incomplete impact or skip coverage, STOP or deadline. Retain native impact and full verbose skipped-file coverage. Skipped files remain unknown. HIGH/CRITICAL produces owner warning and stops. The reference smoke is partial and cannot clear edits. No model, native oracle, historical rejudgment or automatic edit clearance follows.

Unpublished preparation; separately run the four-CPU source-only smoke before considering publication. Full output and smoke output are separate. Source is an isolated detached worktree; this packet leaves production kernels untouched.
