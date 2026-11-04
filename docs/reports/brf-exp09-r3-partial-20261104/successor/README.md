R4 continues the preserved R3 control seed (SHA-256 `59b4358cfdb709bf3b14a0781803d6595080b3045c8c0133b830b3e836ba7266`) with the 72 missing treatment cells. The frozen 24-case aggregate and each control item SHA are checked before execution. R4 treatment output and the immutable seed are separate files; a future verdict must reconcile both and identify the different execution IDs and CPU regions. R3 control views and R4 treatment views contain different scratch pointers.

The publisher smoke uses its standard policy and must observe a newly generated dry-run verified-quote cell, not a seeded control. The production rowflow engine retains its normal 150 GiB long-run disk floor. The launcher uses the original Python virtual-environment entry point; invoking the underlying CPython executable directly would omit its dependencies. No statistical significance, served-latency or production conclusion follows from qualification.

The owner-tested check_resume_seed.py exercises R4’s actual seed loader, duplicate-control refusal, and treatment-only smoke predicate without inference. check_summary_flags.py is inherited from R3 and tests the unchanged completion helper.

R4 routes preflight, terminal validity, and other events to out/run-events.r4.jsonl, separate from treatment-only results.jsonl. At filing, filter out smoke events, bind the real execution ID, and check its preflight and valid completion alongside the seed-plus-treatment grid.

`brf-exp09-resume-r4-20261104` was published after a fresh four-CPU smoke observed a newly generated dry-run verified-quote cell. Its first qualification failure is retained under failed-qualification-1; the corrected dry-run exit passed on retry. The 150 GiB long-run disk floor was not changed.
