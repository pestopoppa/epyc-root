# Filler run10 native overrun producer candidate

PROPOSED: this is a new launcher version, derived from the captured native filler_run9.sh, not an instruction to replace a running launcher. Adoption belongs to the calendar/launcher owner at each job's own boundary. No peer poller is rearmed by this change.

Source provenance: scripts/coordination/filler_run10.native.txt is the full native /mnt/raid0/llm/tmp/fillers-3c4ca599/filler_run9.sh read for this proposal; SHA256 dedaccb7d7874dd2c709c7e9eacd734fb62740a914ac72c982bfc9135107e1cb. filler_run10.delta.patch is applied to that captured native text to produce filler_run10.sh. filler_lib.sh is the unchanged adjacent native library, required by the launcher's FILLER_LIB contract.

The unique matching FILLERS row supplies owner and a simple positive duration estimate at launch. The launcher appends job_id, owner, step=job-run, estimated_wall_s, started and regions in the same temporary record that receives the existing first line, then renames once. First line retains rc/time/reason compatibility with grant writers. The estimate snapshot is consumed before write_ended I/O so a later signal/unstarted repeat cannot reuse it.

The duration grammar accepts a decimal with seconds/minutes/hours units, optional leading '~', and optional parenthesized explanation. Ranges, composite sums, remaining durations, zero, missing estimates, duplicate IDs and numeric overflow leave the record unchecked. Min-window and grant length never substitute for an estimate. FILLERS column positions follow the current canonical header; a schema reorder requires updating this producer. A row author may normalize a complex duration to an explicit simple estimate prospectively.

Wall scope is launcher-group start through end-record publication preparation, including region-lock wait, teardown and completion checking. This is not a payload-only timing result. Optional np/ctx/co-residents are absent unless a future producer captures them natively. Ratios and all grading stay with the existing calendar-overrun adapter and claim_tuple.grade(); no warrant is invented on read and no historical records are backfilled.

Model-free regression fixtures run with fake FLAGS, GRANTS, STATE, FILLERS, PID and lock paths beneath their own temporary directory and use stub payloads. They cover finite conversion and overflow, complete/expired/unstarted cases, metadata consumption on later TERM, repeat isolation, start-time row mutation, hard end and launcher TERM, atomic rename, current first-line rc parsing, existing adapter projection/grading and actual CLI ingestion into a private ledger. No model, host endpoint or canonical runtime state is used.

VB-CAL-OVERRUN-WRITE remains unchecked until the owner adopts a reviewed version and a real finished filler .ended ingests as one tuple. Synthetic success is a code validation receipt, not the real-job acceptance witness. Existing source-table/task wiring drafts must be applied by the owning main.
