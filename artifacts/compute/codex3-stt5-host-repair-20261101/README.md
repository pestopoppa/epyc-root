# STT5 turbo-auto validation: host region-lock repair

The prepared 100-unexposed-chunk Whisper validation successor previously invoked `scripts/region-lock`, whose virtualenv Python was absent in the host mount namespace. Its same-entry launcher now invokes `region-lock-host.sh`: the wrapper verifies the recorded host Python and actual orchestrator-lane modules, then runs the same region-lock CLI via host Python. `LOCK-MODULES.sha256` binds that nested runtime catalog; the main source catalog binds both it and the wrapper.

The host qualifier's `load_manifest`, `bound_files`, and observed-rate feasibility checks passed with source catalog SHA-256 `946e6e07080e8e6ef7f167bc7fca1a0a054782d4776480337dd958d367fd856a`; the isolated queue validator accepted one row without warnings. Nine model-free tests passed, including owned stub cutoff and legacy-lock refusal. The archived launcher and wrapper are evidence copies, not ready manifests.

No target fixture or cohort inference was run; no keeper qualification, receipt, grant, selection, or completion is claimed. The predecessor launcher was still live at review, and its state-dependent locks require a verified single-writer cutover before this draft can be submitted. The historical RTF projection is an observation, not a guaranteed finish bound. The draft remains in `/mnt/raid0/llm/tmp/codex3-g1b-successor-20261101/baseline-batch/`.
