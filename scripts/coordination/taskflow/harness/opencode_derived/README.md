# A3B candidate dispatch with OpenCode

Use this driver for an approved A3B case on a C22 slot the caller already owns. It uses OpenCode 2.2.5's Build agent, normal tool schemas and Code Mode, private subagents, supported question forms, compaction, and the configured local provider. It returns candidate and evidence files for the caller's independent acceptance. The caller selects and claims the backlog row, owns the model server, and handles any accepted patch.

Run from the root repository with Python 3.12.

```bash
PYTHONPATH=scripts/coordination python3 -B -m taskflow.harness.opencode_derived \
    /absolute/private/job.json --approved-sha256 APPROVED_DIGEST --verify-only
PYTHONPATH=scripts/coordination python3 -B -m taskflow.harness.opencode_derived \
    /absolute/private/job.json --approved-sha256 APPROVED_DIGEST --out /absolute/private/new-attempt
```

## Job and case evidence

A job lists the case directory in `case`, the frozen `case_sha256` and `prompt_sha256`, the explicit `backend`, `port`, `slot`, `thinking`, `context`, `request_cap`, `generated_ceiling`, `wall_s`, `control_cpus`, and `sampling`. Bind the owned server's JSON receipt in `serving_receipt` and `serving_receipt_sha256` and the running binary in `server_executable_sha256`. Use the owned server's live receipt with its PID, port, slot count and context, split-KV flag and resolved library maps. Bind the kernel command's model path in `model_path`. The driver checks that process, native library mappings, current KFD residency and slot geometry before dispatch. Use a slot exclusively allotted to this job. Start C22 with explicit `--cache-ram 0` to disable the shared RAM snapshot cache. C22's ordinary in-slot reuse remains available.

`case.json` provides the task ID, original application revision as `repo_base_sha`, original task hash as `task_packet_sha256`, allowed `editable_paths`, `oracle_sha256`, and a `baseline_files` map. Each entry in that map records SHA-256, bytes and executable status. Place source files under `baseline/`, including controller-supplied `.taskflow-refs/` reference copies. Supply the owner-approved prompt at `prompt.md` and the pinned independent acceptor at `oracle.py`. The acceptor stays outside the worker mount. Create the enclosing run directory through the scratch lease workflow and keep the owner receipt.

`assets` names the published OpenCode executable at `opencode`, its `opencode_sha256`, the frozen local OCI `image` ID, staged Python 3.12 packages at `python_packages`, and a short private `socket_root`. These paths must be visible to the local Docker daemon. The optional `skills` path and `skills_state_sha256` bind a read-only skill directory. Compute the digest with `state_digest` in this package. The qualification used OpenCode SHA-256 `8d060e1d2fbb9bb44cf09ae6ed1f3f6a7cff070b5227e2f90970132b23a92050` and image `sha256:9c429a17180a9b3ce2bce942d1bb05a7b7dfbf8218edbc267d190c35fe2b7635`. Stage exact downloaded packages and record their hashes. Set `public_web` when the approved task uses public source retrieval. The case web proxy rejects nonpublic routes. HTTPS uses a public CONNECT tunnel.

## Same-task continuation

A continuation job supplies a new approved `prompt` path and its exact `prompt_sha256`, plus `resume` containing `prior_run`, `receipt_sha256`, `session_sha256`, and `workspace_session_sha256` from the saved run. Keep the same case ID, original task and application revision, slot, context, mode, sampling, provider configuration and output cap. The new attempt copies the prior writable workspace and session database, restages original read-only inputs, and addresses the existing OpenCode session ID. Its receipt meters only newly forwarded requests. Keep the prior artifacts for comparison.

## Verification

Outputs include the full stock session export, question dispositions, adapter request bodies and native timing/usage records, locally rejected adapter requests, candidate patch, and receipt. Answer-free runs explicitly decline operator questions and record their requests. The proxy translates SDK token limits to the C22 alias, uses the assigned slot and enforces the wall and output envelope independently of the tool catalog. Reasoning is preserved for thinking sessions. Stock sidecalls use the same metered path. The local case can use tools and create scratch files. The candidate checker captures changed paths and standard cache artifacts separately, then rebuilds the patch from regular, scope-checked files in an independent private worktree.

Inspect the session and scope receipt, run the task's independent acceptance in its required environment, and retain those results alongside the exact patch. Apply the normal Taskflow owner review and checkbox workflow after acceptance.

C22 can copy a RAM-cached prompt into a busy pinned slot before it defers the second request. This driver also serializes upstream sends to each physical slot within its process. The owner wall includes queue wait. A request cancelled or expired in the queue is recorded separately and consumes no generation reservation. The request ledger separates queue wait from upstream timing.
