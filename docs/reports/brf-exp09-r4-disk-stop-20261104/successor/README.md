R5 preserves the byte-exact 24-control R3 seed separately from its future treatment result. Its original R4 corpus manifest is pinned unchanged; the runner resolves its historical file names to the R5-owned corpus before checking each input hash. The continuation’s preflight and terminal records live in `out/run-events.r5.jsonl`; future filing must require a matching non-dry-run execution ID, valid preflight and `pass_complete`, plus reconcile the seed and treatment records.

The owner exercised the actual resume loader, duplicate-control detection, and treatment-only smoke predicate using synthetic records without inference. R5 keeps the engine’s 150 GiB long-run floor and uses rowflow’s standard smoke policy. Controls and treatments remain separate executions and their scratch-path pointers differ.

The R5 precondition refuses a nonempty R5 native results file. If a later run is partial, preserve its captured treatment cells and prepare a new explicit continuation rather than restarting this scratch in place.

Published as `brf-exp09-resume-r5-20261104` after a four-CPU smoke produced one fresh dry-run verified-quote cell. The normal 150 GiB long-run disk guard remains unchanged; publication does not guarantee capacity recovery.
