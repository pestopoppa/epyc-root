# HSF-1 next15: pre-launch receipt writer preparation

**Classification:** source preparation only. No model, no launch, no production edit, no GPU reservation, no result claim.

## Current source and custody boundary

- Orchestrator repository: `/mnt/raid0/llm/epyc-orchestrator`
- Existing branch/commit at inspection: `main` / `326f50275986c9846027f8187972969139c0089`
- Launch integration site: `scripts/server/orchestrator_stack.py`, `start_server()`; launch occurs at the `subprocess.Popen` block around lines 2511+, followed by `wait_for_health()` and `ProcessInfo` return. The launch already writes a launch banner/PID to the role log.
- That checkout has unrelated pre-existing dirty/untracked files (`orchestration/model_registry.yaml`, `coordination/`, `data/bep_sandbox/KEEP`, `data/embedder_placement/`, `epyc_local_raw_replies.jsonl`, `orchestration/KEEP`). No files there were changed.
- Source digest for the inspected integration file is recorded in `source.sha256`.

## Prepared source

`receipt.py` defines the source-bound receipt shape and an atomic, no-overwrite writer. It consumes events and custody values; it never hashes weights/binaries, invokes `fincore`, starts a server, or reads the model. HSF-1 integration must collect these phase timestamps from the existing server log/lifecycle and pass pre-grant hashes plus pre-exec fincore data. Required phases: process start, `load_model`, `model loaded`, health, first token. Receipt retains argv and its digest, kernel-store/server/GGUF digests, page-cache fraction, hot/cold/unknown label, and outcome class.

## Remaining review/integration work

This packet does **not** claim the HSF-1 producer is wired. Before any measurement series: review how the live `start_server()` log exposes exact load/loaded/first-token markers; integrate the writer only in the existing orchestrator worktree; add offline lifecycle/parser tests; have the owning orchestrator session review and land the source; then collect ordinary production GPU launches. Do not launch standalone models to manufacture receipts. When the 30-day trigger is evaluated, the request is for five launches per model only if the existing receipt count is below five hot receipts/model.

## Measurement boundary

No weight hash inside a grant. Hash GGUF, server, and kernel-store inputs before admission and pin their paths/digests in the reservation/spec. Every launched process needs its own outcome receipt, including failures; missing phase timestamps remain null and are not imputed. Hot-fit eligibility is page-cache fraction >=0.99. At least three model sizes with five hot receipts each are needed before fitting `C = a + size/b`; cold launches remain separately labelled.
