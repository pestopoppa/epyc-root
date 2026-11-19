# KPF-19.1 drafter state source-impact preparation

UNQUALIFIED: no smoke, graph run, tests or publication performed.

Scope is `common_prompt_checkpoint::update_dft` and `common_prompt_checkpoint::load_dft`, both in `common/common.cpp`, detached integrated candidate `8952a0f693fb923918157eb25117641b74766230`. This is distinct from KPF-18.2 component observer impacts (`find_fork_source`/`do_slot_fork`) and studies explicit drafter save/restore flag semantics before the #30514 rebase. The source uses update_dft, not a save_dft function. Native graph target binding must resolve each exact symbol and file or refuse.

Full launcher requests CPUs 0-95, no GPU, 7200s, 48 GiB RAM and unchanged 150 GiB disk floor. Native verbose skipped-file lists, registry/worktree/meta commit binding, full nonpartial impact schema and HIGH/CRITICAL warning-before-stop are mandatory. Skipped files remain unknown. PID-birth plus pidfd captured descendants/subreaper cleanup is inherited from the reviewed preparation template.

Owner must review and recheck duplicates. Run separate four-CPU smoke through the same launcher with FILLER_SMOKE=1 and FILLER_DRYRUN_RESULT_PATH set to an absolute separate smoke results JSONL. Smoke is partial source-reference only and exits 75; it cannot clear edits. Do not replace or publish normal out/results.jsonl using smoke output. Full completion requires both native upstream results and coverage, not the reference smoke.
